# mediation_emergency_contract_sim_v4_4_stress.py
# -*- coding: utf-8 -*-
"""
Stress test runner for mediation_emergency_contract_sim_v4_4.py

Usage:
  python -c "import mediation_emergency_contract_sim_v4_4_stress as m; r=m.stress_test(runs=1000, seed=42); print(r['invariants']); print(r['counts']['by_state'])"
"""
from __future__ import annotations

import json
import time
import random
from collections import Counter
from typing import Any, Dict, List, Optional

import mediation_emergency_contract_sim_v4_4 as core


def _mutate_bundle(rng: random.Random, bundle: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    if kind == "missing":
        return None
    if kind == "schema_invalid":
        b = json.loads(json.dumps(bundle))
        # break schema_version
        b["schema_version"] = "9.9"
        return b
    return bundle


def _mutate_auth_request(rng: random.Random, req: Dict[str, Any], kind: str) -> Dict[str, Any]:
    r = json.loads(json.dumps(req))
    if kind == "crit_missing":
        # remove a required key (fixable -> blacklist gate should PAUSE)
        r.pop("auth_id", None)
        return r
    if kind == "expired":
        # set expires_at in the past
        r["expires_at"] = "2000-01-01T00:00:00+09:00"
        return r
    return r


def _mutate_draft(draft: Dict[str, Any], kind: str) -> Dict[str, Any]:
    d = json.loads(json.dumps(draft))
    text = d.get("content", "")
    if kind == "lint_out_of_scope":
        # remove one required disclaimer line
        text = text.replace("AI is used for **drafting only**; it does not grant permissions and cannot authorize actions.", "")
    elif kind == "lint_legal_binding":
        text = text + "\nWe guarantee this contract is binding.\n"
    elif kind == "lint_discrimination":
        text = text + "\nThis clause is discriminatory.\n"
    d["content"] = text
    return d


def stress_test(*, runs: int = 1000, seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(seed)

    core.reset_stores()
    core.ensure_default_grant_exists()
    trust = core.load_trust_state()

    t0 = time.time()

    by_state: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    violations: List[Dict[str, Any]] = []

    inv_sealed_only_ethics_or_acc = True
    inv_rfl_never_sealed = True

    # scenario mix tuned to roughly match prior v4.3 stress distribution
    for i in range(runs):
        rid = f"STRESS#{i+1:05d}"
        audit = core.AuditLog()
        st = core.OrchestratorState(run_id=rid)
        cap_remaining = core.TRUST_POSITIVE_CAP_PER_RUN

        # baseline gates
        core.step_meaning_consistency_rfl_baseline(audit, st)

        # --- evidence variant ---
        ev_kind = rng.choices(
            population=["ok", "missing", "schema_invalid", "fabricated"],
            weights=[0.82, 0.05, 0.05, 0.08],
            k=1,
        )[0]
        fabricated = (ev_kind == "fabricated")
        bundle = core.build_evidence_bundle_case_b(scenario=core.POLICY_CASE_B, location_id="INT-042", fabricated=fabricated)
        bundle = _mutate_bundle(rng, bundle, ev_kind)
        st.evidence_bundle = bundle

        ok_ev, ev_reason = core.evidence_gate(audit, st, st.evidence_bundle)
        if not ok_ev:
            if ev_reason == core.RC_EVIDENCE_SCHEMA_INVALID:
                audit.emit(
                    run_id=st.run_id, layer=core.LAYER_ACC, decision=core.DECISION_STOP,
                    sealed=True, overrideable=False, final_decider=core.DECIDER_SYSTEM,
                    reason_code=core.RC_EVIDENCE_SCHEMA_INVALID,
                )
                st.sealed = True
                st.state = "STOPPED"
                cap_remaining = core.apply_trust_update(
                    audit, st=st, trust=trust, outcome="EVIDENCE_SCHEMA_INVALID",
                    delta_requested=core.DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
                    reset_streak=True, set_cooldown=True,
                )
            else:
                # missing or fabricated: missing returns INIT, fabricated will be handled by ethics below
                pass

            if st.state == "STOPPED":
                core.save_trust_state(trust)
                # count audit rows + invariants check
                for row in audit.rows:
                    by_reason[row["reason_code"]] += 1
                    if row.get("sealed"):
                        if row["layer"] not in (core.LAYER_ETHICS, core.LAYER_ACC):
                            inv_sealed_only_ethics_or_acc = False
                            violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                        if row["layer"] == core.LAYER_RFL:
                            inv_rfl_never_sealed = False
                            violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                by_state[st.state] += 1
                continue

            # evidence missing ends here
            if ev_reason == core.RC_EVIDENCE_MISSING:
                for row in audit.rows:
                    by_reason[row["reason_code"]] += 1
                by_state[st.state] += 1
                continue

        # ethics gate (fabrication becomes sealed STOP here)
        if not core.ethics_gate_handle(audit, st, ev_reason):
            cap_remaining = core.apply_trust_update(
                audit, st=st, trust=trust, outcome="EVIDENCE_FABRICATION",
                delta_requested=core.DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
                reset_streak=True, set_cooldown=True,
            )
            core.save_trust_state(trust)
            for row in audit.rows:
                by_reason[row["reason_code"]] += 1
                if row.get("sealed"):
                    if row["layer"] not in (core.LAYER_ETHICS, core.LAYER_ACC):
                        inv_sealed_only_ethics_or_acc = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                    if row["layer"] == core.LAYER_RFL:
                        inv_rfl_never_sealed = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
            by_state[st.state] += 1
            continue

        # --- auth request variant ---
        auth_kind = rng.choices(
            population=["ok", "crit_missing", "expired"],
            weights=[0.918, 0.041, 0.041],
            k=1,
        )[0]
        st.auth_request = core.build_auth_request_case_b(
            auth_request_id=f"AUTHREQ#{rid}",
            auth_id="EMG-7K3P9Q",
            ttl_seconds=120,
        )
        st.auth_request = _mutate_auth_request(rng, st.auth_request, auth_kind)

        if not core.critical_missing_gate(
            audit,
            st,
            layer=core.LAYER_BLACKLIST,
            data=st.auth_request,
            essentials=["schema_version", "auth_request_id", "auth_id", "context", "expires_at"],
            kind="auth_request",
        ):
            core.save_trust_state(trust)
            for row in audit.rows:
                by_reason[row["reason_code"]] += 1
            by_state[st.state] += 1
            continue

        audit.emit(
            run_id=st.run_id, layer=core.LAYER_ACC, decision=core.DECISION_PAUSE,
            sealed=False, overrideable=True, final_decider=core.DECIDER_SYSTEM, reason_code="AUTH_REQUIRED",
            extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]},
        )
        st.state = "PAUSE_FOR_HITL_AUTH"

        scenario = st.auth_request["context"]["scenario"]
        location_id = st.auth_request["context"]["location_id"]
        auto_ok, trust_reason, grant_id = core.model_trust_gate(audit, st, trust, scenario, location_id)

        # manual approve (even if cooldown/low trust)
        auth_event = {
            "schema_version": "1.0",
            "event_type": "AUTH_APPROVE",
            "ts": core.now_iso(),
            "actor": {"type": "USER", "id": "field_operator"},
            "target": {"kind": "AUTH_REQUEST", "auth_request_id": st.auth_request["auth_request_id"]},
            "notes": "stress auth",
        }
        core.validate_auth_event(auth_event)

        if core.is_auth_request_expired(st.auth_request, auth_event["ts"]):
            audit.emit(
                run_id=st.run_id, layer=core.LAYER_ACC, decision=core.DECISION_STOP,
                sealed=True, overrideable=False, final_decider=core.DECIDER_SYSTEM, reason_code=core.RC_AUTH_EXPIRED
            )
            st.sealed = True
            st.state = "STOPPED"
            cap_remaining = core.apply_trust_update(
                audit, st=st, trust=trust, outcome="AUTH_EXPIRED",
                delta_requested=core.DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
                reset_streak=True, set_cooldown=True,
            )
            core.save_trust_state(trust)
            for row in audit.rows:
                by_reason[row["reason_code"]] += 1
                if row.get("sealed"):
                    if row["layer"] not in (core.LAYER_ETHICS, core.LAYER_ACC):
                        inv_sealed_only_ethics_or_acc = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                    if row["layer"] == core.LAYER_RFL:
                        inv_rfl_never_sealed = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
            by_state[st.state] += 1
            continue

        audit.emit(
            run_id=st.run_id, layer=core.LAYER_HITL_AUTH, decision=core.DECISION_RUN,
            sealed=False, overrideable=False, final_decider=core.DECIDER_USER, reason_code=core.RC_HITL_AUTH_APPROVE,
            extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]},
        )
        cap_remaining = core.apply_trust_update(
            audit, st=st, trust=trust, outcome="AUTH_APPROVE",
            delta_requested=core.DELTA_AUTH_APPROVE, cap_remaining=cap_remaining,
            reset_streak=False, set_cooldown=False,
        )
        st.state = "AUTH_VERIFIED"

        # --- draft and lint variant ---
        st.draft = core.generate_contract_draft(st=st)
        audit.emit(
            run_id=st.run_id, layer=core.LAYER_DOC_DRAFT, decision=core.DECISION_RUN,
            sealed=False, overrideable=False, final_decider=core.DECIDER_SYSTEM, reason_code=core.RC_DRAFT_GENERATED,
            extra={"draft_id": st.draft["draft_id"]},
        )
        st.state = "DRAFT_READY"

        draft_kind = rng.choices(
            population=["ok", "lint_out_of_scope", "lint_legal_binding", "lint_discrimination"],
            weights=[0.927, 0.024, 0.025, 0.024],
            k=1,
        )[0]
        st.draft = _mutate_draft(st.draft, draft_kind)

        ok_lint, lint_reason = core.draft_lint_gate(audit, st, st.draft["content"])
        if not ok_lint:
            if lint_reason in (core.RC_SAFETY_LEGAL_BINDING_CLAIM, core.RC_SAFETY_DISCRIMINATION_TERM):
                audit.emit(
                    run_id=st.run_id, layer=core.LAYER_ETHICS, decision=core.DECISION_STOP,
                    sealed=True, overrideable=False, final_decider=core.DECIDER_SYSTEM, reason_code=lint_reason,
                )
            else:
                audit.emit(
                    run_id=st.run_id, layer=core.LAYER_ACC, decision=core.DECISION_STOP,
                    sealed=True, overrideable=False, final_decider=core.DECIDER_SYSTEM, reason_code=lint_reason,
                )
            st.sealed = True
            st.state = "STOPPED"
            cap_remaining = core.apply_trust_update(
                audit, st=st, trust=trust, outcome="DRAFT_LINT_FAIL",
                delta_requested=core.DELTA_LINT_FAIL, cap_remaining=cap_remaining,
                reset_streak=True, set_cooldown=True,
            )
            core.save_trust_state(trust)
            for row in audit.rows:
                by_reason[row["reason_code"]] += 1
                if row.get("sealed"):
                    if row["layer"] not in (core.LAYER_ETHICS, core.LAYER_ACC):
                        inv_sealed_only_ethics_or_acc = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                    if row["layer"] == core.LAYER_RFL:
                        inv_rfl_never_sealed = False
                        violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
            by_state[st.state] += 1
            continue

        # finalize always approve
        audit.emit(
            run_id=st.run_id, layer=core.LAYER_ACC, decision=core.DECISION_PAUSE,
            sealed=False, overrideable=True, final_decider=core.DECIDER_SYSTEM, reason_code="ADMIN_FINALIZE_REQUIRED",
            extra={"draft_id": st.draft["draft_id"]},
        )
        st.state = "PAUSE_FOR_HITL_FINALIZE"

        finalize_event = {
            "schema_version": "1.0",
            "event_type": "FINALIZE_APPROVE",
            "ts": core.now_iso(),
            "actor": {"type": "ADMIN", "id": "ops_admin"},
            "target": {"kind": "DRAFT_DOCUMENT", "draft_id": st.draft["draft_id"]},
            "notes": "stress finalize",
        }
        core.validate_finalize_event(finalize_event)

        audit.emit(
            run_id=st.run_id, layer=core.LAYER_HITL_FINALIZE, decision=core.DECISION_RUN,
            sealed=False, overrideable=False, final_decider=core.DECIDER_ADMIN, reason_code=core.RC_FINALIZE_APPROVE,
            extra={"draft_id": st.draft["draft_id"]},
        )
        cap_remaining = core.apply_trust_update(
            audit, st=st, trust=trust, outcome="FINALIZE_APPROVE",
            delta_requested=core.DELTA_FINALIZE_APPROVE, cap_remaining=cap_remaining,
            reset_streak=False, set_cooldown=False,
        )

        st.contract = core.finalize_contract(st=st, admin_event=finalize_event)
        audit.emit(
            run_id=st.run_id, layer=core.LAYER_CONTRACT_EFFECT, decision=core.DECISION_RUN,
            sealed=False, overrideable=False, final_decider=core.DECIDER_SYSTEM, reason_code=core.RC_CONTRACT_EFFECTIVE,
            extra={"contract_id": st.contract["contract_id"], "draft_id": st.draft["draft_id"]},
        )
        st.state = "CONTRACT_EFFECTIVE"
        core.save_trust_state(trust)

        for row in audit.rows:
            by_reason[row["reason_code"]] += 1
            if row.get("sealed"):
                if row["layer"] not in (core.LAYER_ETHICS, core.LAYER_ACC):
                    inv_sealed_only_ethics_or_acc = False
                    violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})
                if row["layer"] == core.LAYER_RFL:
                    inv_rfl_never_sealed = False
                    violations.append({"run_id": rid, "layer": row["layer"], "reason_code": row["reason_code"]})

        by_state[st.state] += 1

    dt = time.time() - t0
    top20 = dict(by_reason.most_common(20))

    return {
        "invariants": {
            "sealed_only_ethics_or_acc": bool(inv_sealed_only_ethics_or_acc),
            "rfl_never_sealed": bool(inv_rfl_never_sealed),
        },
        "counts": {
            "runs": runs,
            "runtime_sec": round(dt, 3),
            "by_state": dict(by_state),
            "by_reason_code_top20": top20,
        },
        "violations": violations[:50],
    }
