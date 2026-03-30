# mediation_emergency_contract_sim_v4_1.py
# -*- coding: utf-8 -*-
"""
Minimal, runnable simulation skeleton (v4-style flow).

What it demonstrates:
- Meaning -> Consistency -> RFL (PAUSE, non-sealed) -> HITL finalize (USER continue/stop)
- Evidence gate detects fabrication but does not seal (sealing reserved for Ethics/ACC)
- Ethics gate seals on fabrication
- ACC pause for auth; Trust+Grant can auto-skip HITL auth when trust high and streak sufficient
- Draft generation + draft lint
- ACC pause for admin finalize
- Trust updates with per-run positive cap

Run:
  python mediation_emergency_contract_sim_v4_1.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

JST = timezone(timedelta(hours=9))

def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")

def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)

ISO_MIN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")

# ---- ARL constants ----
DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOP = "STOPPED"

DECIDER_SYSTEM = "SYSTEM"
DECIDER_USER = "USER"
DECIDER_ADMIN = "ADMIN"

LAYER_MEANING = "meaning_gate"
LAYER_CONSISTENCY = "consistency_gate"
LAYER_RFL = "relativity_gate"
LAYER_HITL_RFL_FINALIZE = "hitl_finalize_rfl"
LAYER_EVIDENCE = "evidence_gate"
LAYER_ETHICS = "ethics_gate"
LAYER_ACC = "acc_gate"
LAYER_TRUST = "model_trust_gate"
LAYER_TRUST_UPDATE = "trust_update"
LAYER_HITL_AUTH = "hitl_auth"
LAYER_DOC_DRAFT = "doc_draft"
LAYER_DRAFT_LINT = "draft_lint_gate"
LAYER_HITL_FINALIZE = "hitl_finalize_admin"
LAYER_CONTRACT_EFFECT = "contract_effect"

RC_OK = "OK"
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"

RC_EVIDENCE_OK = "EVIDENCE_OK"
RC_EVIDENCE_SCHEMA_INVALID = "EVIDENCE_SCHEMA_INVALID"
RC_EVIDENCE_FABRICATION = "EVIDENCE_FABRICATION"

RC_TRUST_SCORE_LOW = "TRUST_SCORE_LOW"
RC_TRUST_COOLDOWN_ACTIVE = "TRUST_COOLDOWN_ACTIVE"
RC_TRUST_AUTO_AUTH = "AUTO_AUTH_BY_TRUST_AND_GRANT"
RC_TRUST_NO_GRANT = "NO_VALID_GRANT"

RC_DRAFT_GENERATED = "DRAFT_GENERATED"
RC_DRAFT_LINT_OK = "DRAFT_LINT_OK"
RC_DRAFT_OUT_OF_SCOPE = "DRAFT_OUT_OF_SCOPE"
RC_DRAFT_ILLEGAL_BINDING = "DRAFT_ILLEGAL_BINDING"

RC_FINALIZE_APPROVE = "FINALIZE_APPROVE"
RC_CONTRACT_EFFECTIVE = "CONTRACT_EFFECTIVE"
RC_NON_OVERRIDABLE_SAFETY = "NON_OVERRIDABLE_SAFETY"

RC_HITL_CONTINUE = "HITL_CONTINUE"
RC_HITL_STOP = "HITL_STOP"
RC_HITL_AUTH_APPROVE = "AUTH_APPROVE"

POLICY_PRIORITY = "LIFE > PEDESTRIAN > VEHICLE"
POLICY_CASE_B = "CASE_B_PED_IN_CROSSWALK_EMERGENCY_PRESENT"

def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

def _require(d: Dict[str, Any], k: str) -> Any:
    if k not in d:
        raise KeyError(f"missing: {k}")
    return d[k]

def _validate_iso(ts: Any) -> None:
    if not isinstance(ts, str) or not ISO_MIN_RE.match(ts):
        raise ValueError("ts must be ISO-8601 string")

def _validate_dummy_auth_id(auth_id: str) -> None:
    if not re.match(r"^EMG-[A-Z0-9]{6,20}$", auth_id):
        raise ValueError("auth_id must match ^EMG-[A-Z0-9]{6,20}$ (dummy id)")

RflHitlDecision = Literal["continue", "stop"]

State = Literal[
    "INIT",
    "PAUSE_FOR_HITL_RFL",
    "PAUSE_FOR_HITL_AUTH",
    "AUTH_VERIFIED",
    "DRAFT_READY",
    "PAUSE_FOR_HITL_FINALIZE",
    "CONTRACT_EFFECTIVE",
    "STOPPED",
]

@dataclass
class AuditLog:
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def emit(
        self,
        *,
        run_id: str,
        layer: str,
        decision: str,
        sealed: bool,
        overrideable: bool,
        final_decider: str,
        reason_code: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "ts": now_iso(),
            "run_id": run_id,
            "layer": layer,
            "decision": decision,
            "sealed": sealed,
            "overrideable": overrideable,
            "final_decider": final_decider,
            "reason_code": reason_code,
        }
        if extra:
            row.update(extra)
        self.rows.append(row)
        return row

@dataclass
class OrchestratorState:
    run_id: str
    state: State = "INIT"
    sealed: bool = False
    auth_request: Optional[Dict[str, Any]] = None
    draft: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    evidence_bundle: Optional[Dict[str, Any]] = None

# ---- Evidence bundle ----
EVIDENCE_SCHEMA_VERSION = "1.0"

def build_evidence_bundle_case_b(*, scenario: str, location_id: str, fabricated: bool = False) -> Dict[str, Any]:
    retrieved_at = now_iso()
    evidence_item = {
        "evidence_id": "EV#001",
        "source_id": "SIM_SOURCE",
        "locator": {"kind": "SIM", "location_id": location_id},
        "retrieved_at": retrieved_at,
        "hash": {"algo": "sha256", "value": "SIMULATED"},
        "supports": [
            {"claim": "emergency_vehicle_present", "value": True},
            {"claim": "ped_in_crosswalk", "value": True},
        ],
        "fabricated": bool(fabricated),
        "relevance": "high",
    }
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "scenario": scenario,
        "location_id": location_id,
        "evidence_items": [evidence_item],
    }

def validate_evidence_bundle(bundle: Dict[str, Any]) -> None:
    if not isinstance(bundle, dict):
        raise ValueError("bundle must be object")
    if bundle.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ValueError("bundle.schema_version must be '1.0'")
    for k in ["scenario", "location_id", "evidence_items"]:
        _require(bundle, k)
    if not isinstance(bundle["evidence_items"], list) or len(bundle["evidence_items"]) == 0:
        raise ValueError("evidence_items must be non-empty list")
    for it in bundle["evidence_items"]:
        if not isinstance(it, dict):
            raise ValueError("each evidence_item must be object")
        for kk in ["evidence_id", "source_id", "locator", "retrieved_at", "hash", "supports", "fabricated"]:
            _require(it, kk)
        _validate_iso(it["retrieved_at"])
        if not isinstance(it["locator"], dict):
            raise ValueError("locator must be object")
        if not isinstance(it["supports"], list):
            raise ValueError("supports must be list")

def evidence_gate(audit: AuditLog, st: OrchestratorState, bundle: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        validate_evidence_bundle(bundle)
    except Exception as e:
        # In this toy sim, schema invalid is treated as hard sealed stop.
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_STOP,
            sealed=True,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_SCHEMA_INVALID,
            extra={"error": str(e)},
        )
        st.sealed = True
        st.state = "STOPPED"
        return False, RC_EVIDENCE_SCHEMA_INVALID

    fabricated_any = any(bool(it.get("fabricated", False)) for it in bundle["evidence_items"])
    if fabricated_any:
        # Do NOT seal here. Sealing is for ethics/acc only.
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_FABRICATION,
        )
        return False, RC_EVIDENCE_FABRICATION

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_EVIDENCE,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_EVIDENCE_OK,
    )
    return True, RC_EVIDENCE_OK

# ---- Draft lint ----
_NEG_WORDS = ("not", "no", "cannot", "can't", "without", "lacks", "lack", "never")
_PATTERNS_POSITIVE = [
    re.compile(r"\blegally binding\b", re.IGNORECASE),
    re.compile(r"\bthis contract is binding\b", re.IGNORECASE),
    re.compile(r"\bwe guarantee\b", re.IGNORECASE),
]

def _window_before(text: str, idx: int, n: int = 30) -> str:
    lo = max(0, idx - n)
    return text[lo:idx].lower()

def _is_negated(text: str, match_start: int) -> bool:
    w = _window_before(text, match_start, n=40)
    return any(neg in w for neg in _NEG_WORDS)

def draft_lint_gate(audit: AuditLog, st: OrchestratorState, draft_md: str) -> Tuple[bool, str]:
    text = draft_md or ""
    for pat in _PATTERNS_POSITIVE:
        m = pat.search(text)
        if not m:
            continue
        if _is_negated(text, m.start()):
            continue
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_DRAFT_LINT,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_DRAFT_ILLEGAL_BINDING,
            extra={"pattern": pat.pattern},
        )
        return False, RC_DRAFT_ILLEGAL_BINDING

    required_lines = ["draft", "no operational effect", "AI is used for drafting only", "ADMIN approval"]
    lower = re.sub(r"[`*_]", "", text).lower()
    missing = [x for x in required_lines if x.lower() not in lower]
    if missing:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_DRAFT_LINT,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_DRAFT_OUT_OF_SCOPE,
            extra={"missing": missing},
        )
        return False, RC_DRAFT_OUT_OF_SCOPE

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_DRAFT_LINT,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_DRAFT_LINT_OK,
    )
    return True, RC_DRAFT_LINT_OK

# ---- Trust + grant stores ----
TRUST_STORE_PATH = Path("model_trust_store.json")
GRANT_STORE_PATH = Path("model_grants.json")

TRUST_INIT = 0.90
TRUST_MIN = 0.00
TRUST_MAX = 1.00
TRUST_NEED_FOR_AUTO = 0.98
STREAK_NEED_FOR_AUTO = 2
TRUST_POSITIVE_CAP_PER_RUN = 0.03

DELTA_AUTH_APPROVE = +0.01
DELTA_FINALIZE_APPROVE = +0.02
DELTA_LINT_FAIL = -0.015
DELTA_INVALID_EVENT = -0.03

COOLDOWN_SECONDS = 300

@dataclass
class TrustState:
    trust_score: float = TRUST_INIT
    approval_streak: int = 0
    cooldown_until: Optional[str] = None

    def is_cooldown_active(self) -> bool:
        if not self.cooldown_until:
            return False
        return datetime.now(JST) < parse_iso(self.cooldown_until)

    def to_dict(self) -> Dict[str, Any]:
        return {"trust_score": self.trust_score, "approval_streak": self.approval_streak, "cooldown_until": self.cooldown_until}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TrustState":
        ts = TrustState()
        ts.trust_score = float(d.get("trust_score", TRUST_INIT))
        ts.approval_streak = int(d.get("approval_streak", 0))
        ts.cooldown_until = d.get("cooldown_until")
        ts.trust_score = clamp(ts.trust_score, TRUST_MIN, TRUST_MAX)
        return ts

@dataclass
class Grant:
    grant_id: str
    scenario: str
    location_id: str
    expires_at: str
    issued_by: str

    def is_valid(self) -> bool:
        return datetime.now(JST) <= parse_iso(self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        return {"grant_id": self.grant_id, "scenario": self.scenario, "location_id": self.location_id, "expires_at": self.expires_at, "issued_by": self.issued_by}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Grant":
        return Grant(
            grant_id=str(d.get("grant_id", "")),
            scenario=str(d.get("scenario", "")),
            location_id=str(d.get("location_id", "")),
            expires_at=str(d.get("expires_at", "")),
            issued_by=str(d.get("issued_by", "")),
        )

def load_trust_state() -> TrustState:
    if not TRUST_STORE_PATH.exists():
        return TrustState()
    try:
        d = json.loads(TRUST_STORE_PATH.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            return TrustState()
        return TrustState.from_dict(d)
    except Exception:
        return TrustState()

def save_trust_state(ts: TrustState) -> None:
    TRUST_STORE_PATH.write_text(json.dumps(ts.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

def load_grants() -> List[Grant]:
    if not GRANT_STORE_PATH.exists():
        return []
    try:
        d = json.loads(GRANT_STORE_PATH.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "grants" not in d or not isinstance(d["grants"], list):
            return []
        out: List[Grant] = []
        for it in d["grants"]:
            if isinstance(it, dict):
                g = Grant.from_dict(it)
                if g.grant_id and g.scenario and g.location_id and ISO_MIN_RE.match(g.expires_at):
                    out.append(g)
        return out
    except Exception:
        return []

def save_grants(grants: List[Grant]) -> None:
    GRANT_STORE_PATH.write_text(json.dumps({"grants": [g.to_dict() for g in grants]}, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_default_grant_exists() -> None:
    grants = load_grants()
    for g in grants:
        if g.scenario == POLICY_CASE_B and g.location_id == "INT-042" and g.is_valid():
            return
    expires = (datetime.now(JST) + timedelta(days=7)).isoformat(timespec="seconds")
    grants.append(Grant(grant_id="GRANT#CASE_B#INT-042", scenario=POLICY_CASE_B, location_id="INT-042", expires_at=expires, issued_by="ops_admin"))
    save_grants(grants)

def reset_stores() -> None:
    if TRUST_STORE_PATH.exists():
        TRUST_STORE_PATH.unlink()
    if GRANT_STORE_PATH.exists():
        GRANT_STORE_PATH.unlink()

def apply_trust_update(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    trust: TrustState,
    outcome: str,
    delta_requested: float,
    cap_remaining: float,
    reset_streak: bool = False,
    set_cooldown: bool = False,
) -> float:
    before = trust.trust_score
    applied = delta_requested
    if delta_requested > 0:
        applied = min(delta_requested, max(0.0, cap_remaining))
        cap_remaining = max(0.0, cap_remaining - applied)
    trust.trust_score = clamp(trust.trust_score + applied, TRUST_MIN, TRUST_MAX)

    if reset_streak:
        trust.approval_streak = 0
    else:
        if applied > 0:
            trust.approval_streak += 1

    if set_cooldown:
        trust.cooldown_until = (datetime.now(JST) + timedelta(seconds=COOLDOWN_SECONDS)).isoformat(timespec="seconds")

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_TRUST_UPDATE,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code="TRUST_UPDATE",
        extra={
            "outcome": outcome,
            "trust_before": round(before, 6),
            "trust_after": round(trust.trust_score, 6),
            "delta_requested": delta_requested,
            "delta_applied": round(applied, 6),
            "approval_streak": trust.approval_streak,
            "cooldown_until": trust.cooldown_until,
            "cap_remaining": round(cap_remaining, 6),
        },
    )
    return cap_remaining

def model_trust_gate(
    audit: AuditLog,
    st: OrchestratorState,
    trust: TrustState,
    scenario: str,
    location_id: str,
) -> Tuple[bool, str, Optional[str]]:
    if trust.is_cooldown_active():
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_TRUST,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_COOLDOWN_ACTIVE,
        )
        return False, RC_TRUST_COOLDOWN_ACTIVE, None

    grant = None
    for g in load_grants():
        if g.scenario == scenario and g.location_id == location_id and g.is_valid():
            grant = g
            break
    if grant is None:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_TRUST,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_NO_GRANT,
        )
        return False, RC_TRUST_NO_GRANT, None

    if trust.trust_score >= TRUST_NEED_FOR_AUTO and trust.approval_streak >= STREAK_NEED_FOR_AUTO:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_TRUST,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_AUTO_AUTH,
            extra={"grant_id": grant.grant_id, "trust_score": trust.trust_score, "approval_streak": trust.approval_streak},
        )
        return True, RC_TRUST_AUTO_AUTH, grant.grant_id

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_TRUST,
        decision=DECISION_PAUSE,
        sealed=False,
        overrideable=True,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_TRUST_SCORE_LOW,
        extra={"trust_score": trust.trust_score, "need": TRUST_NEED_FOR_AUTO, "approval_streak": trust.approval_streak},
    )
    return False, RC_TRUST_SCORE_LOW, grant.grant_id

# ---- Baseline gates + RFL HITL ----
def step_meaning_consistency_baseline(audit: AuditLog, st: OrchestratorState) -> None:
    audit.emit(run_id=st.run_id, layer=LAYER_MEANING, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK)
    audit.emit(run_id=st.run_id, layer=LAYER_CONSISTENCY, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK)

def rfl_gate(audit: AuditLog, st: OrchestratorState) -> Tuple[bool, str]:
    # demo trigger: SIM#B002 => boundary unstable => pause (non-sealed)
    boundary_unstable = st.run_id.endswith("B002")
    if boundary_unstable:
        audit.emit(run_id=st.run_id, layer=LAYER_RFL, decision=DECISION_PAUSE, sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code=RC_REL_BOUNDARY_UNSTABLE)
        st.state = "PAUSE_FOR_HITL_RFL"
        return False, RC_REL_BOUNDARY_UNSTABLE
    audit.emit(run_id=st.run_id, layer=LAYER_RFL, decision=DECISION_RUN, sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code=RC_OK)
    return True, RC_OK

def hitl_finalize_rfl(audit: AuditLog, st: OrchestratorState, decision: RflHitlDecision) -> bool:
    if st.sealed:
        audit.emit(run_id=st.run_id, layer=LAYER_HITL_RFL_FINALIZE, decision=DECISION_STOP, sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_NON_OVERRIDABLE_SAFETY)
        st.state = "STOPPED"
        return False
    if decision == "continue":
        audit.emit(run_id=st.run_id, layer=LAYER_HITL_RFL_FINALIZE, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_CONTINUE)
        st.state = "INIT"
        return True
    audit.emit(run_id=st.run_id, layer=LAYER_HITL_RFL_FINALIZE, decision=DECISION_STOP, sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_STOP)
    st.state = "STOPPED"
    return False

def ethics_gate_handle(audit: AuditLog, st: OrchestratorState, evidence_reason: str) -> bool:
    # sealing happens here for fabrication
    if evidence_reason == RC_EVIDENCE_FABRICATION:
        audit.emit(run_id=st.run_id, layer=LAYER_ETHICS, decision=DECISION_STOP, sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_EVIDENCE_FABRICATION)
        st.sealed = True
        st.state = "STOPPED"
        return False
    audit.emit(run_id=st.run_id, layer=LAYER_ETHICS, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK)
    return True

# ---- Draft / finalize ----
def build_auth_request_case_b(*, run_id: str, auth_id: str, ttl_seconds: int = 120) -> Dict[str, Any]:
    _validate_dummy_auth_id(auth_id)
    expires = (datetime.now(JST) + timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
    return {
        "schema_version": "1.0",
        "auth_request_id": f"AUTHREQ#{run_id}",
        "auth_id": auth_id,
        "context": {"scenario": POLICY_CASE_B, "location_id": "INT-042"},
        "expires_at": expires,
    }

def generate_contract_draft(*, st: OrchestratorState) -> Dict[str, Any]:
    draft_id = f"DRAFT#{st.run_id}"
    draft_md = f"""# Agreement Draft (Emergency Signal Priority)
**Draft ID**: {draft_id}
**Run ID**: {st.run_id}
**Policy**: {POLICY_PRIORITY}
**Generated At**: {now_iso()}

- This document is a **draft** and has **no operational effect** until ADMIN final approval.
- AI is used for **drafting only**; it does not grant permissions and cannot authorize actions.
- **ADMIN approval** required.
"""
    return {"draft_id": draft_id, "format": "markdown", "content": draft_md, "generated_at": now_iso()}

def finalize_contract(*, st: OrchestratorState) -> Dict[str, Any]:
    contract_id = f"CONTRACT#{st.run_id}"
    return {"contract_id": contract_id, "format": "markdown", "content": st.draft["content"], "effective_at": now_iso()}

# ---- Simulation ----
def simulate_run(
    *,
    run_id: str,
    trust: TrustState,
    fabricate_evidence: bool = False,
    hitl_rfl: RflHitlDecision = "continue",
) -> Tuple[OrchestratorState, AuditLog, TrustState]:
    audit = AuditLog()
    st = OrchestratorState(run_id=run_id)
    cap_remaining = TRUST_POSITIVE_CAP_PER_RUN

    step_meaning_consistency_baseline(audit, st)

    ok_rfl, _ = rfl_gate(audit, st)
    if not ok_rfl:
        if not hitl_finalize_rfl(audit, st, hitl_rfl):
            save_trust_state(trust)
            return st, audit, trust

    st.evidence_bundle = build_evidence_bundle_case_b(scenario=POLICY_CASE_B, location_id="INT-042", fabricated=fabricate_evidence)
    _, ev_reason = evidence_gate(audit, st, st.evidence_bundle)
    if st.state == "STOPPED":
        cap_remaining = apply_trust_update(audit, st=st, trust=trust, outcome="EVIDENCE_SCHEMA_INVALID", delta_requested=DELTA_INVALID_EVENT, cap_remaining=cap_remaining, reset_streak=True, set_cooldown=True)
        save_trust_state(trust)
        return st, audit, trust

    if not ethics_gate_handle(audit, st, ev_reason):
        cap_remaining = apply_trust_update(audit, st=st, trust=trust, outcome="EVIDENCE_FABRICATION", delta_requested=DELTA_INVALID_EVENT, cap_remaining=cap_remaining, reset_streak=True, set_cooldown=True)
        save_trust_state(trust)
        return st, audit, trust

    # ACC pause: auth required
    st.auth_request = build_auth_request_case_b(run_id=run_id, auth_id="EMG-7K3P9Q")
    audit.emit(run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_PAUSE, sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code="AUTH_REQUIRED")
    st.state = "PAUSE_FOR_HITL_AUTH"

    auto_ok, _, _ = model_trust_gate(audit, st, trust, st.auth_request["context"]["scenario"], st.auth_request["context"]["location_id"])
    if auto_ok:
        audit.emit(run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code="AUTH_SKIPPED", extra={"mode": "auto"})
    else:
        audit.emit(run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_AUTH_APPROVE)
        cap_remaining = apply_trust_update(audit, st=st, trust=trust, outcome="AUTH_APPROVE", delta_requested=DELTA_AUTH_APPROVE, cap_remaining=cap_remaining)

    st.state = "AUTH_VERIFIED"

    st.draft = generate_contract_draft(st=st)
    audit.emit(run_id=st.run_id, layer=LAYER_DOC_DRAFT, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_DRAFT_GENERATED, extra={"draft_id": st.draft["draft_id"]})
    st.state = "DRAFT_READY"

    ok_lint, _ = draft_lint_gate(audit, st, st.draft["content"])
    if not ok_lint:
        cap_remaining = apply_trust_update(audit, st=st, trust=trust, outcome="DRAFT_LINT_FAIL", delta_requested=DELTA_LINT_FAIL, cap_remaining=cap_remaining, reset_streak=True, set_cooldown=True)
        st.state = "STOPPED"
        save_trust_state(trust)
        return st, audit, trust

    # ACC pause: admin finalize required
    audit.emit(run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_PAUSE, sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code="ADMIN_FINALIZE_REQUIRED")
    st.state = "PAUSE_FOR_HITL_FINALIZE"

    audit.emit(run_id=st.run_id, layer=LAYER_HITL_FINALIZE, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_ADMIN, reason_code=RC_FINALIZE_APPROVE)
    cap_remaining = apply_trust_update(audit, st=st, trust=trust, outcome="FINALIZE_APPROVE", delta_requested=DELTA_FINALIZE_APPROVE, cap_remaining=cap_remaining)

    st.contract = finalize_contract(st=st)
    audit.emit(run_id=st.run_id, layer=LAYER_CONTRACT_EFFECT, decision=DECISION_RUN, sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_CONTRACT_EFFECTIVE, extra={"contract_id": st.contract["contract_id"]})
    st.state = "CONTRACT_EFFECTIVE"
    save_trust_state(trust)
    return st, audit, trust

def run_simulation(runs: int = 4, fabricate: bool = False, hitl_rfl: RflHitlDecision = "continue") -> Dict[str, Any]:
    reset_stores()
    ensure_default_grant_exists()
    trust = load_trust_state()

    results: Dict[str, Any] = {"trust_before": trust.to_dict(), "runs": []}
    for i in range(runs):
        rid = f"SIM#B{(i+1):03d}"
        st, audit, trust = simulate_run(run_id=rid, trust=trust, fabricate_evidence=fabricate, hitl_rfl=hitl_rfl)
        results["runs"].append({"run_id": rid, "final_state": st.state, "sealed": st.sealed, "arl": audit.rows, "trust_after": trust.to_dict()})
    results["trust_after"] = trust.to_dict()
    results["grants"] = {"grants": [g.to_dict() for g in load_grants()]}
    return results

def main() -> int:
    print("=== NORMAL ===")
    print(json.dumps(run_simulation(), ensure_ascii=False, indent=2))
    print("\\n=== FABRICATE (should seal at ethics) ===")
    print(json.dumps(run_simulation(fabricate=True), ensure_ascii=False, indent=2))
    print("\\n=== RFL_STOP (user stops at RFL) ===")
    print(json.dumps(run_simulation(hitl_rfl="stop"), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
