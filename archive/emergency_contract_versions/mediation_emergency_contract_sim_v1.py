# mediation_emergency_contract_sim_v1.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
import re


# =========================================================
# Time
# =========================================================
JST = timezone(timedelta(hours=9))

def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")

def parse_iso(ts: str) -> datetime:
    # Python 3.11+: fromisoformat supports timezone offset like +09:00
    return datetime.fromisoformat(ts)

ISO_MIN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")


# =========================================================
# KAGE vocab (minimal)
# =========================================================
DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOP = "STOPPED"

DECIDER_SYSTEM = "SYSTEM"
DECIDER_USER = "USER"          # use for human actor in general
DECIDER_ADMIN = "ADMIN"        # explicit admin role (you can collapse to USER if desired)

# Layers (subset aligned to your structure)
LAYER_MEANING = "meaning_gate"
LAYER_CONSISTENCY = "consistency_gate"
LAYER_RFL = "relativity_gate"
LAYER_ETHICS = "ethics_gate"
LAYER_ACC = "acc_gate"
LAYER_HITL_AUTH = "hitl_auth"
LAYER_DOC_DRAFT = "doc_draft"
LAYER_HITL_FINALIZE = "hitl_finalize_admin"
LAYER_CONTRACT_EFFECT = "contract_effect"

# Reason codes
RC_OK = "OK"
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
RC_REL_REF_MISSING = "REL_REF_MISSING"
RC_HITL_AUTH_APPROVE = "AUTH_APPROVE"
RC_HITL_AUTH_REJECT = "AUTH_REJECT"
RC_HITL_AUTH_REVISE = "AUTH_REVISE"
RC_AUTH_EXPIRED = "AUTH_EXPIRED"
RC_AUTH_BAD_ACTOR = "AUTH_BAD_ACTOR"
RC_INVALID_EVENT = "INVALID_EVENT"
RC_FINALIZE_APPROVE = "FINALIZE_APPROVE"
RC_FINALIZE_REVISE = "FINALIZE_REVISE"
RC_FINALIZE_STOP = "FINALIZE_STOP"
RC_NON_OVERRIDABLE_SAFETY = "NON_OVERRIDABLE_SAFETY"

# Policy labels (for traceability)
POLICY_PRIORITY = "LIFE > PEDESTRIAN > VEHICLE"
POLICY_CASE_B = "CASE_B_PED_IN_CROSSWALK_EMERGENCY_PRESENT"


# =========================================================
# ARL (Audit Row Log) minimal keys
# =========================================================
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
            # Keep it small; avoid PII in real use.
            row.update(extra)
        self.rows.append(row)
        return row

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in self.rows)


# =========================================================
# Events (inputs)
# =========================================================
AuthEventType = Literal["AUTH_APPROVE", "AUTH_REVISE", "AUTH_REJECT"]
FinalizeEventType = Literal["FINALIZE_APPROVE", "FINALIZE_REVISE", "FINALIZE_STOP"]

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

def validate_auth_request(auth_request: Dict[str, Any]) -> None:
    _require(auth_request, "schema_version")
    if auth_request["schema_version"] != "1.0":
        raise ValueError("schema_version must be '1.0'")
    _require(auth_request, "auth_request_id")
    auth_id = _require(auth_request, "auth_id")
    _validate_dummy_auth_id(str(auth_id))
    ctx = _require(auth_request, "context")
    if not isinstance(ctx, dict):
        raise ValueError("context must be object")
    for k in ["scenario", "location_id", "emergency_vehicle_state"]:
        _require(ctx, k)
    _validate_iso(_require(auth_request, "expires_at"))

def validate_auth_event(event: Dict[str, Any]) -> None:
    _require(event, "schema_version")
    if event["schema_version"] != "1.0":
        raise ValueError("schema_version must be '1.0'")
    ev = _require(event, "event_type")
    if ev not in ("AUTH_APPROVE", "AUTH_REVISE", "AUTH_REJECT"):
        raise ValueError("invalid event_type for auth")
    _validate_iso(_require(event, "ts"))
    actor = _require(event, "actor")
    if not isinstance(actor, dict):
        raise ValueError("actor must be object")
    if actor.get("type") != "USER" or not actor.get("id"):
        raise ValueError("auth actor must be USER with id")
    target = _require(event, "target")
    if not isinstance(target, dict):
        raise ValueError("target must be object")
    if target.get("kind") != "AUTH_REQUEST":
        raise ValueError("target.kind must be AUTH_REQUEST")
    if not target.get("auth_request_id"):
        raise ValueError("target.auth_request_id required")

def validate_finalize_event(event: Dict[str, Any]) -> None:
    _require(event, "schema_version")
    if event["schema_version"] != "1.0":
        raise ValueError("schema_version must be '1.0'")
    ev = _require(event, "event_type")
    if ev not in ("FINALIZE_APPROVE", "FINALIZE_REVISE", "FINALIZE_STOP"):
        raise ValueError("invalid event_type for finalize")
    _validate_iso(_require(event, "ts"))
    actor = _require(event, "actor")
    if not isinstance(actor, dict):
        raise ValueError("actor must be object")
    # ADMIN is required here (as per your design)
    if actor.get("type") != "ADMIN" or not actor.get("id"):
        raise ValueError("finalize actor must be ADMIN with id")
    target = _require(event, "target")
    if not isinstance(target, dict):
        raise ValueError("target must be object")
    if target.get("kind") != "DRAFT_DOCUMENT":
        raise ValueError("target.kind must be DRAFT_DOCUMENT")
    if not target.get("draft_id"):
        raise ValueError("target.draft_id required")


# =========================================================
# Orchestrator state (FSM)
# =========================================================
State = Literal[
    "INIT",
    "PAUSE_FOR_HITL_AUTH",
    "AUTH_VERIFIED",
    "DRAFT_READY",
    "PAUSE_FOR_HITL_FINALIZE",
    "CONTRACT_EFFECTIVE",
    "STOPPED",
]

@dataclass
class OrchestratorState:
    run_id: str
    state: State = "INIT"
    sealed: bool = False  # sealed only by Ethics/ACC
    # Artifacts / refs
    auth_request: Optional[Dict[str, Any]] = None
    draft: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None


# =========================================================
# Simulation core
# =========================================================
def build_auth_request_case_b(*, auth_request_id: str, auth_id: str, ttl_seconds: int = 180) -> Dict[str, Any]:
    # Case B: pedestrian in crosswalk + emergency present
    expires = (datetime.now(JST) + timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
    req = {
        "schema_version": "1.0",
        "auth_request_id": auth_request_id,
        "auth_id": auth_id,
        "context": {
            "scenario": POLICY_CASE_B,
            "location_id": "INT-042",
            "emergency_vehicle_state": "WAITING_AT_SIGNAL",
            "ped_in_crosswalk": True,
        },
        "expires_at": expires,
    }
    validate_auth_request(req)
    return req

def is_auth_request_expired(auth_request: Dict[str, Any], now_ts: Optional[str] = None) -> bool:
    now_dt = parse_iso(now_ts) if now_ts else datetime.now(JST)
    exp_dt = parse_iso(auth_request["expires_at"])
    return now_dt > exp_dt

def generate_contract_draft(*, state: OrchestratorState, admin_required: bool = True) -> Dict[str, Any]:
    """
    AI generates draft only after AUTH_APPROVE.
    Content: describes policy for Case B (do not shorten pedestrian phase, emergency gets next cycle).
    """
    assert state.auth_request is not None
    ctx = state.auth_request["context"]
    draft_id = f"DRAFT#{state.run_id}"
    draft_md = f"""# Agreement Draft (Emergency Signal Priority)

**Draft ID**: {draft_id}  
**Run ID**: {state.run_id}  
**Policy**: {POLICY_PRIORITY}  
**Scenario**: {ctx.get("scenario")}  
**Location**: {ctx.get("location_id")}  
**Auth Request ID**: {state.auth_request.get("auth_request_id")}  
**Dummy Auth ID**: {state.auth_request.get("auth_id")}  
**Generated At**: {now_iso()}

---

## 1. Purpose
Establish an operational priority order for signal control under emergency presence.

## 2. Priority Order
1) LIFE (Emergency vehicle)  
2) PEDESTRIAN (in crosswalk)  
3) VEHICLE (general traffic)

## 3. Case B Rule (Pedestrian in crosswalk + Emergency present)
- While **pedestrian is in the crosswalk**, pedestrian protection remains active.
- Signal phase for pedestrians **must not be shortened**.
- Emergency priority is applied **at the next cycle** immediately after pedestrian clearance is detected.
- Minimum safety clearance (e.g., all-red) is applied before granting emergency green.

## 4. Non-goals / Safety Notes
- This document is a **draft** and has **no legal/operational effect** until ADMIN final approval.
- AI is used for **drafting only**; it is not a decision-making or legal authority.

## 5. Effective Condition
This draft becomes effective only after the ADMIN approval event references this Draft ID.

---

**ADMIN Approval Required**: {"YES" if admin_required else "NO"}
"""
    return {
        "draft_id": draft_id,
        "format": "markdown",
        "content": draft_md,
        "generated_at": now_iso(),
        "refs": {
            "auth_request_id": state.auth_request.get("auth_request_id"),
            "auth_id": state.auth_request.get("auth_id"),
        }
    }

def finalize_contract(*, state: OrchestratorState, admin_event: Dict[str, Any]) -> Dict[str, Any]:
    assert state.draft is not None
    admin = admin_event["actor"]["id"]
    contract_id = f"CONTRACT#{state.run_id}"
    contract_md = state.draft["content"] + f"""

---

# ADMIN Finalization

**Contract ID**: {contract_id}  
**Finalized At**: {now_iso()}  
**Finalized By (ADMIN)**: {admin}  
**Finalize Event TS**: {admin_event.get("ts")}

> This contract is now effective.
"""
    return {
        "contract_id": contract_id,
        "format": "markdown",
        "content": contract_md,
        "effective_at": now_iso(),
        "refs": {
            "draft_id": state.draft["draft_id"],
            "auth_request_id": state.draft["refs"]["auth_request_id"],
            "auth_id": state.draft["refs"]["auth_id"],
        }
    }

def step_meaning_consistency_rfl_baseline(audit: AuditLog, st: OrchestratorState) -> None:
    """
    Minimal placeholder gates for this scenario.
    We keep them PASS to focus on event/HITL/doc pipeline.
    """
    audit.emit(
        run_id=st.run_id, layer=LAYER_MEANING, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )
    audit.emit(
        run_id=st.run_id, layer=LAYER_CONSISTENCY, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )
    # RFL: In this scenario, policy is fixed and boundary is defined (crosswalk-only).
    audit.emit(
        run_id=st.run_id, layer=LAYER_RFL, decision=DECISION_RUN,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )

def simulate_run(
    *,
    run_id: str = "SIM#0001",
    dummy_auth_id: str = "EMG-7K3P9Q",
    interactive: bool = False,
) -> Tuple[OrchestratorState, AuditLog]:
    """
    Full pipeline simulation:
      AUTH_REQUEST (system) -> HITL AUTH (user) -> DRAFT (system) -> HITL FINALIZE (admin) -> CONTRACT_EFFECTIVE

    interactive=False uses fixed decisions:
      AUTH_APPROVE, FINALIZE_APPROVE
    """
    audit = AuditLog()
    st = OrchestratorState(run_id=run_id)

    # ---- Baseline gates pass (placeholders)
    step_meaning_consistency_rfl_baseline(audit, st)

    # ---- Create AUTH_REQUEST (system)
    st.auth_request = build_auth_request_case_b(
        auth_request_id=f"AUTHREQ#{run_id}",
        auth_id=dummy_auth_id,
        ttl_seconds=120
    )
    audit.emit(
        run_id=st.run_id,
        layer=LAYER_ACC,
        decision=DECISION_PAUSE,
        sealed=False,
        overrideable=True,
        final_decider=DECIDER_SYSTEM,
        reason_code="AUTH_REQUIRED",
        extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]},
    )
    st.state = "PAUSE_FOR_HITL_AUTH"

    # ---- HITL AUTH event (USER)
    if interactive:
        print("\n[HITL AUTH] Choose: 1=APPROVE 2=REVISE 3=REJECT")
        c = input(">> ").strip()
        ev_type = "AUTH_APPROVE" if c == "1" else ("AUTH_REVISE" if c == "2" else "AUTH_REJECT")
    else:
        ev_type = "AUTH_APPROVE"

    auth_event = {
        "schema_version": "1.0",
        "event_type": ev_type,
        "ts": now_iso(),
        "actor": {"type": "USER", "id": "field_operator"},
        "target": {"kind": "AUTH_REQUEST", "auth_request_id": st.auth_request["auth_request_id"]},
        "notes": "Dummy auth for bench run",
    }

    # Validate & apply AUTH event
    try:
        validate_auth_event(auth_event)

        # protocol checks
        if st.state != "PAUSE_FOR_HITL_AUTH":
            raise ValueError("state mismatch: not waiting for AUTH HITL")
        if st.sealed:
            # sealed can only come from ethics/acc; treat as non-overrideable safety.
            audit.emit(
                run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
                sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_NON_OVERRIDABLE_SAFETY
            )
            st.state = "STOPPED"
            return st, audit

        if is_auth_request_expired(st.auth_request, auth_event["ts"]):
            audit.emit(
                run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
                sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_AUTH_EXPIRED
            )
            st.sealed = True
            st.state = "STOPPED"
            return st, audit

        if auth_event["event_type"] == "AUTH_REJECT":
            audit.emit(
                run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_STOP,
                sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_AUTH_REJECT
            )
            st.state = "STOPPED"
            return st, audit

        if auth_event["event_type"] == "AUTH_REVISE":
            audit.emit(
                run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_PAUSE,
                sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_AUTH_REVISE
            )
            # stay paused (in real use you'd request more evidence)
            st.state = "PAUSE_FOR_HITL_AUTH"
            return st, audit

        # AUTH_APPROVE
        audit.emit(
            run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_RUN,
            sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_AUTH_APPROVE,
            extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]}
        )
        st.state = "AUTH_VERIFIED"

    except Exception as e:
        # invalid auth event -> ACC seal (fail-closed)
        audit.emit(
            run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
            sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_INVALID_EVENT,
            extra={"error": str(e)}
        )
        st.sealed = True
        st.state = "STOPPED"
        return st, audit

    # ---- Generate DRAFT (system action)
    st.draft = generate_contract_draft(state=st)
    audit.emit(
        run_id=st.run_id, layer=LAYER_DOC_DRAFT, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code="DRAFT_GENERATED",
        extra={"draft_id": st.draft["draft_id"]}
    )
    st.state = "DRAFT_READY"

    # ---- Pause for ADMIN finalize
    audit.emit(
        run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_PAUSE,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code="ADMIN_FINALIZE_REQUIRED",
        extra={"draft_id": st.draft["draft_id"]}
    )
    st.state = "PAUSE_FOR_HITL_FINALIZE"

    # ---- HITL FINALIZE event (ADMIN)
    if interactive:
        print("\n[HITL ADMIN FINALIZE] Choose: 1=APPROVE 2=REVISE 3=STOP")
        c = input(">> ").strip()
        ev_type2 = "FINALIZE_APPROVE" if c == "1" else ("FINALIZE_REVISE" if c == "2" else "FINALIZE_STOP")
    else:
        ev_type2 = "FINALIZE_APPROVE"

    finalize_event = {
        "schema_version": "1.0",
        "event_type": ev_type2,
        "ts": now_iso(),
        "actor": {"type": "ADMIN", "id": "ops_admin"},
        "target": {"kind": "DRAFT_DOCUMENT", "draft_id": st.draft["draft_id"]},
        "notes": "bench finalize",
    }

    # Validate & apply FINALIZE event
    try:
        validate_finalize_event(finalize_event)

        if st.state != "PAUSE_FOR_HITL_FINALIZE":
            raise ValueError("state mismatch: not waiting for FINALIZE HITL")
        if st.sealed:
            audit.emit(
                run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
                sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_NON_OVERRIDABLE_SAFETY
            )
            st.state = "STOPPED"
            return st, audit

        if finalize_event["event_type"] == "FINALIZE_STOP":
            audit.emit(
                run_id=st.run_id, layer=LAYER_HITL_FINALIZE, decision=DECISION_STOP,
                sealed=False, overrideable=False, final_decider=DECIDER_ADMIN, reason_code=RC_FINALIZE_STOP
            )
            st.state = "STOPPED"
            return st, audit

        if finalize_event["event_type"] == "FINALIZE_REVISE":
            audit.emit(
                run_id=st.run_id, layer=LAYER_HITL_FINALIZE, decision=DECISION_PAUSE,
                sealed=False, overrideable=False, final_decider=DECIDER_ADMIN, reason_code=RC_FINALIZE_REVISE
            )
            # In real flow: send back to drafting/mediation; here stop as "needs revision"
            st.state = "PAUSE_FOR_HITL_FINALIZE"
            return st, audit

        # FINALIZE_APPROVE
        audit.emit(
            run_id=st.run_id, layer=LAYER_HITL_FINALIZE, decision=DECISION_RUN,
            sealed=False, overrideable=False, final_decider=DECIDER_ADMIN, reason_code=RC_FINALIZE_APPROVE,
            extra={"draft_id": st.draft["draft_id"]}
        )

    except Exception as e:
        audit.emit(
            run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
            sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_INVALID_EVENT,
            extra={"error": str(e)}
        )
        st.sealed = True
        st.state = "STOPPED"
        return st, audit

    # ---- Contract effective (system action)
    st.contract = finalize_contract(state=st, admin_event=finalize_event)
    audit.emit(
        run_id=st.run_id, layer=LAYER_CONTRACT_EFFECT, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code="CONTRACT_EFFECTIVE",
        extra={"contract_id": st.contract["contract_id"], "draft_id": st.draft["draft_id"]}
    )
    st.state = "CONTRACT_EFFECTIVE"
    return st, audit


# =========================================================
# Entry point
# =========================================================
if __name__ == "__main__":
    # Change interactive=True if you want manual HITL choices in terminal.
    final_state, audit = simulate_run(
        run_id="SIM#B001",
        dummy_auth_id="EMG-7K3P9Q",
        interactive=False,
    )

    print("\n=== FINAL STATE ===")
    print(final_state.state, "sealed=", final_state.sealed)

    print("\n=== ARL (JSONL) ===")
    print(audit.to_jsonl())

    if final_state.draft:
        print("\n=== DRAFT (markdown) ===")
        print(final_state.draft["content"])

    if final_state.contract:
        print("\n=== CONTRACT (markdown) ===")
        print(final_state.contract["content"])
