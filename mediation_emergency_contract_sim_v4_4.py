# mediation_emergency_contract_sim_v4_3.py
# -*- coding: utf-8 -*-
# Version: 4.4
"""
v4.3 delta (from v4.2):
- Add "HITL Queue" post-processing: extract pause/stop items from ARL into a compact queue payload.
- Optional queue outputs (JSON / CSV) for ops handoff.
- Define POLICY_PACK_HASH (stable stub) to avoid NameError.
- Fix fabricated-evidence log row: decision is STOPPED (sealed), not RUN.
  (Behavior remains fail-closed: fabrication -> sealed STOP.)
"""
from __future__ import annotations

import argparse
import csv
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

DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOP = "STOPPED"

DECIDER_SYSTEM = "SYSTEM"
DECIDER_USER = "USER"
DECIDER_ADMIN = "ADMIN"

LAYER_MEANING = "meaning_gate"
LAYER_CONSISTENCY = "consistency_gate"
LAYER_RFL = "relativity_gate"
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
LAYER_BLACKLIST = "blacklist_gate"

RC_OK = "OK"
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
RC_REL_REF_MISSING = "REL_REF_MISSING"

RC_EVIDENCE_OK = "EVIDENCE_OK"
RC_EVIDENCE_MISSING = "EVIDENCE_MISSING"
RC_EVIDENCE_SCHEMA_INVALID = "EVIDENCE_SCHEMA_INVALID"
RC_EVIDENCE_FABRICATION = "EVIDENCE_FABRICATION"

RC_TRUST_SCORE_LOW = "TRUST_SCORE_LOW"
RC_TRUST_COOLDOWN_ACTIVE = "TRUST_COOLDOWN_ACTIVE"
RC_TRUST_AUTO_AUTH = "AUTO_AUTH_BY_TRUST_AND_GRANT"
RC_TRUST_NO_GRANT = "NO_VALID_GRANT"

RC_HITL_AUTH_APPROVE = "AUTH_APPROVE"
RC_HITL_AUTH_REJECT = "AUTH_REJECT"
RC_HITL_AUTH_REVISE = "AUTH_REVISE"
RC_AUTH_EXPIRED = "AUTH_EXPIRED"
RC_INVALID_EVENT = "INVALID_EVENT"

RC_CRIT_MISSING_REQUIRED_KEYS = "CRIT_MISSING_REQUIRED_KEYS"
RC_SAFETY_LEGAL_BINDING_CLAIM = "SAFETY_LEGAL_BINDING_CLAIM"
RC_SAFETY_DISCRIMINATION_TERM = "SAFETY_DISCRIMINATION_TERM"

RC_DRAFT_GENERATED = "DRAFT_GENERATED"
RC_DRAFT_LINT_OK = "DRAFT_LINT_OK"
RC_DRAFT_OUT_OF_SCOPE = "DRAFT_OUT_OF_SCOPE"
RC_DRAFT_ILLEGAL_BINDING = "DRAFT_ILLEGAL_BINDING"

RC_FINALIZE_APPROVE = "FINALIZE_APPROVE"
RC_FINALIZE_REVISE = "FINALIZE_REVISE"
RC_FINALIZE_STOP = "FINALIZE_STOP"

RC_CONTRACT_EFFECTIVE = "CONTRACT_EFFECTIVE"
RC_NON_OVERRIDABLE_SAFETY = "NON_OVERRIDABLE_SAFETY"

# Stable stub: treat as policy-pack fingerprint placeholder for demo.
# In real ops, hash your versioned policy pack file(s) and inject here.
POLICY_PACK_HASH = "POLICY_PACK#SIM#V4_3"

POLICY_PRIORITY = "LIFE > PEDESTRIAN > VEHICLE"
POLICY_CASE_B = "CASE_B_PED_IN_CROSSWALK_EMERGENCY_PRESENT"

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

    def to_jsonl(self) -> str:
        return "\\n".join(json.dumps(r, ensure_ascii=False) for r in self.rows)

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

def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

AuthEventType = Literal["AUTH_APPROVE", "AUTH_REVISE", "AUTH_REJECT"]
FinalizeEventType = Literal["FINALIZE_APPROVE", "FINALIZE_REVISE", "FINALIZE_STOP"]

def critical_missing_gate(
    audit: "AuditLog",
    st: "OrchestratorState",
    *,
    layer: str,
    data: Optional[Dict[str, Any]],
    essentials: List[str],
    reason_code: str = RC_CRIT_MISSING_REQUIRED_KEYS,
    kind: str = "payload",
) -> bool:
    """Fail-closed missing-key detector.
    Missing keys are fixable, so we PAUSE_FOR_HITL (overrideable=True) and include missing_keys.
    """
    data = data or {}
    missing = [k for k in essentials if k not in data]
    if missing:
        audit.emit(
            run_id=st.run_id,
            layer=layer,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=reason_code,
            extra={"kind": kind, "missing_keys": missing},
        )
        return False
    return True


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
    if actor.get("type") != "ADMIN" or not actor.get("id"):
        raise ValueError("finalize actor must be ADMIN with id")
    target = _require(event, "target")
    if not isinstance(target, dict):
        raise ValueError("target must be object")
    if target.get("kind") != "DRAFT_DOCUMENT":
        raise ValueError("target.kind must be DRAFT_DOCUMENT")
    if not target.get("draft_id"):
        raise ValueError("target.draft_id required")

EVIDENCE_SCHEMA_VERSION = "1.0"

def build_evidence_bundle_case_b(
    *,
    scenario: str,
    location_id: str,
    fabricated: bool = False,
) -> Dict[str, Any]:
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
    if not isinstance(bundle["evidence_items"], list):
        raise ValueError("evidence_items must be list")
    if len(bundle["evidence_items"]) == 0:
        raise ValueError("evidence_items must not be empty")
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

def evidence_gate(audit: AuditLog, st: "OrchestratorState", bundle: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    if bundle is None:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_MISSING,
        )
        return False, RC_EVIDENCE_MISSING

    try:
        validate_evidence_bundle(bundle)
    except Exception as e:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_SCHEMA_INVALID,
            extra={"error": str(e)},
        )
        return False, RC_EVIDENCE_SCHEMA_INVALID

    fabricated_any = any(bool(it.get("fabricated", False)) for it in bundle["evidence_items"])
    if fabricated_any:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_FABRICATION,
            extra={"scenario": bundle.get("scenario"), "location_id": bundle.get("location_id")},
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
        extra={
            "scenario": bundle.get("scenario"),
            "location_id": bundle.get("location_id"),
            "policy_pack_hash": POLICY_PACK_HASH,
        },
    )
    return True, RC_EVIDENCE_OK

_NEG_WORDS = ("not", "no", "cannot", "can't", "without", "lacks", "lack", "never")
_PATTERNS_POSITIVE = [
    re.compile(r"\\blegally binding\\b", re.IGNORECASE),
    re.compile(r"\\bthis contract is binding\\b", re.IGNORECASE),
    re.compile(r"\\bwe guarantee\\b", re.IGNORECASE),
    re.compile(r"\\bhas legal authority\\b", re.IGNORECASE),
    re.compile(r"\\bgrants? legal authority\\b", re.IGNORECASE),
    re.compile(r"\\bis a legal authority\\b", re.IGNORECASE),
]

_PATTERNS_DISCRIMINATION = [
    re.compile(r"\\b(discriminat(?:e|ion)|racist|racial slur)\\b", re.IGNORECASE),
]

def _window_before(text: str, idx: int, n: int = 30) -> str:
    lo = max(0, idx - n)
    return text[lo:idx].lower()

def _is_negated(text: str, match_start: int) -> bool:
    w = _window_before(text, match_start, n=40)
    return any(neg in w.split() or neg in w for neg in _NEG_WORDS)

def draft_lint_gate(audit: AuditLog, st: "OrchestratorState", draft_md: str) -> Tuple[bool, str]:
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
            reason_code=RC_SAFETY_LEGAL_BINDING_CLAIM,
            extra={"pattern": pat.pattern},
        )
        return False, RC_SAFETY_LEGAL_BINDING_CLAIM

    for pat in _PATTERNS_DISCRIMINATION:
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
            reason_code=RC_SAFETY_DISCRIMINATION_TERM,
            extra={"pattern": pat.pattern},
        )
        return False, RC_SAFETY_DISCRIMINATION_TERM

    required_lines = [
        "draft",
        "no operational effect",
        "AI is used for drafting only",
        "ADMIN approval",
    ]
    normalized = re.sub(r"[`*_]", "", text)
    lower = normalized.lower()
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
DELTA_AUTH_REJECT = -0.03
DELTA_LINT_FAIL = -0.015
DELTA_INVALID_EVENT = -0.03

COOLDOWN_SECONDS = 300

@dataclass
class TrustState:
    trust_score: float = TRUST_INIT
    approval_streak: int = 0
    cooldown_until: Optional[str] = None

    def is_cooldown_active(self, now_ts: Optional[str] = None) -> bool:
        if not self.cooldown_until:
            return False
        now_dt = parse_iso(now_ts) if now_ts else datetime.now(JST)
        cd_dt = parse_iso(self.cooldown_until)
        return now_dt < cd_dt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trust_score": self.trust_score,
            "approval_streak": self.approval_streak,
            "cooldown_until": self.cooldown_until,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TrustState":
        ts = TrustState()
        ts.trust_score = float(d.get("trust_score", TRUST_INIT))
        ts.approval_streak = int(d.get("approval_streak", 0))
        ts.cooldown_until = d.get("cooldown_until")
        ts.trust_score = clamp(ts.trust_score, TRUST_MIN, TRUST_MAX)
        return ts

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

@dataclass
class Grant:
    grant_id: str
    scenario: str
    location_id: str
    expires_at: str
    issued_by: str

    def is_valid(self, now_ts: Optional[str] = None) -> bool:
        now_dt = parse_iso(now_ts) if now_ts else datetime.now(JST)
        return now_dt <= parse_iso(self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "scenario": self.scenario,
            "location_id": self.location_id,
            "expires_at": self.expires_at,
            "issued_by": self.issued_by,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Grant":
        return Grant(
            grant_id=str(d.get("grant_id", "")),
            scenario=str(d.get("scenario", "")),
            location_id=str(d.get("location_id", "")),
            expires_at=str(d.get("expires_at", "")),
            issued_by=str(d.get("issued_by", "")),
        )

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
    GRANT_STORE_PATH.write_text(
        json.dumps({"grants": [g.to_dict() for g in grants]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def ensure_default_grant_exists() -> None:
    grants = load_grants()
    now_dt = datetime.now(JST)
    for g in grants:
        if g.scenario == POLICY_CASE_B and g.location_id == "INT-042" and g.is_valid(now_dt.isoformat(timespec="seconds")):
            return
    expires = (now_dt + timedelta(days=7)).isoformat(timespec="seconds")
    new_g = Grant(
        grant_id="GRANT#CASE_B#INT-042",
        scenario=POLICY_CASE_B,
        location_id="INT-042",
        expires_at=expires,
        issued_by="ops_admin",
    )
    grants.append(new_g)
    save_grants(grants)

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
    sealed: bool = False
    auth_request: Optional[Dict[str, Any]] = None
    draft: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    evidence_bundle: Optional[Dict[str, Any]] = None

def build_auth_request_case_b(*, auth_request_id: str, auth_id: str, ttl_seconds: int = 180) -> Dict[str, Any]:
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

def generate_contract_draft(*, st: OrchestratorState) -> Dict[str, Any]:
    assert st.auth_request is not None
    ctx = st.auth_request["context"]
    draft_id = f"DRAFT#{st.run_id}"
    draft_md = f"""# Agreement Draft (Emergency Signal Priority)
**Draft ID**: {draft_id}
**Run ID**: {st.run_id}
**Policy**: {POLICY_PRIORITY}
**Scenario**: {ctx.get("scenario")}
**Location**: {ctx.get("location_id")}
**Auth Request ID**: {st.auth_request.get("auth_request_id")}
**Dummy Auth ID**: {st.auth_request.get("auth_id")}
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
- This document is a **draft** and has **no operational effect** until ADMIN final approval.
- AI is used for **drafting only**; it does not grant permissions and cannot authorize actions.

## 5. Effective Condition
This draft becomes effective only after the ADMIN approval event references this Draft ID.

---
**ADMIN Approval Required**: YES
"""
    return {
        "draft_id": draft_id,
        "format": "markdown",
        "content": draft_md,
        "generated_at": now_iso(),
        "refs": {
            "auth_request_id": st.auth_request.get("auth_request_id"),
            "auth_id": st.auth_request.get("auth_id"),
        },
    }

def finalize_contract(*, st: OrchestratorState, admin_event: Dict[str, Any]) -> Dict[str, Any]:
    assert st.draft is not None
    admin = admin_event["actor"]["id"]
    contract_id = f"CONTRACT#{st.run_id}"
    contract_md = st.draft["content"] + f"""
---
# ADMIN Finalization
**Contract ID**: {contract_id}
**Finalized At**: {now_iso()}
**Finalized By (ADMIN)**: {admin}
**Finalize Event TS**: {admin_event.get("ts")}
> This contract is now effective (simulation).
"""
    return {
        "contract_id": contract_id,
        "format": "markdown",
        "content": contract_md,
        "effective_at": now_iso(),
        "refs": {
            "draft_id": st.draft["draft_id"],
            "auth_request_id": st.draft["refs"]["auth_request_id"],
            "auth_id": st.draft["refs"]["auth_id"],
        },
    }

def step_meaning_consistency_rfl_baseline(audit: AuditLog, st: OrchestratorState) -> None:
    audit.emit(
        run_id=st.run_id, layer=LAYER_MEANING, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )
    audit.emit(
        run_id=st.run_id, layer=LAYER_CONSISTENCY, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )
    audit.emit(
        run_id=st.run_id, layer=LAYER_RFL, decision=DECISION_RUN,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )

def ethics_gate_handle(audit: AuditLog, st: OrchestratorState, evidence_reason: str) -> bool:
    if evidence_reason == RC_EVIDENCE_FABRICATION:
        audit.emit(
            run_id=st.run_id, layer=LAYER_ETHICS, decision=DECISION_STOP,
            sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_EVIDENCE_FABRICATION
        )
        st.sealed = True
        st.state = "STOPPED"
        return False
    audit.emit(
        run_id=st.run_id, layer=LAYER_ETHICS, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_OK
    )
    return True

def apply_trust_update(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    trust: "TrustState",
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
        until = (datetime.now(JST) + timedelta(seconds=COOLDOWN_SECONDS)).isoformat(timespec="seconds")
        trust.cooldown_until = until

    audit.emit(
        run_id=st.run_id, layer=LAYER_TRUST_UPDATE, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code="TRUST_UPDATE",
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

def find_valid_grant(*, scenario: str, location_id: str, now_ts: Optional[str] = None) -> Optional["Grant"]:
    grants = load_grants()
    for g in grants:
        if g.scenario == scenario and g.location_id == location_id and g.is_valid(now_ts):
            return g
    return None

def model_trust_gate(
    audit: AuditLog,
    st: OrchestratorState,
    trust: "TrustState",
    scenario: str,
    location_id: str,
) -> Tuple[bool, str, Optional[str]]:
    if trust.is_cooldown_active():
        audit.emit(
            run_id=st.run_id, layer=LAYER_TRUST, decision=DECISION_PAUSE,
            sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_COOLDOWN_ACTIVE,
            extra={"trust_score": trust.trust_score, "cooldown_until": trust.cooldown_until},
        )
        return False, RC_TRUST_COOLDOWN_ACTIVE, None

    g = find_valid_grant(scenario=scenario, location_id=location_id)
    if g is None:
        audit.emit(
            run_id=st.run_id, layer=LAYER_TRUST, decision=DECISION_PAUSE,
            sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_NO_GRANT,
            extra={"scenario": scenario, "location_id": location_id, "trust_score": trust.trust_score},
        )
        return False, RC_TRUST_NO_GRANT, None

    if trust.trust_score >= TRUST_NEED_FOR_AUTO and trust.approval_streak >= STREAK_NEED_FOR_AUTO:
        audit.emit(
            run_id=st.run_id, layer=LAYER_TRUST, decision=DECISION_RUN,
            sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM,
            reason_code=RC_TRUST_AUTO_AUTH,
            extra={
                "trust_score": trust.trust_score,
                "need": TRUST_NEED_FOR_AUTO,
                "approval_streak": trust.approval_streak,
                "grant_id": g.grant_id,
            },
        )
        return True, RC_TRUST_AUTO_AUTH, g.grant_id

    audit.emit(
        run_id=st.run_id, layer=LAYER_TRUST, decision=DECISION_PAUSE,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM,
        reason_code=RC_TRUST_SCORE_LOW,
        extra={"trust_score": trust.trust_score, "need": TRUST_NEED_FOR_AUTO, "approval_streak": trust.approval_streak},
    )
    return False, RC_TRUST_SCORE_LOW, g.grant_id

def simulate_run(
    *,
    run_id: str,
    dummy_auth_id: str,
    trust: "TrustState",
    fabricate_evidence: bool = False,
) -> Tuple["OrchestratorState", AuditLog, "TrustState"]:
    audit = AuditLog()
    st = OrchestratorState(run_id=run_id)
    cap_remaining = TRUST_POSITIVE_CAP_PER_RUN

    step_meaning_consistency_rfl_baseline(audit, st)

    st.evidence_bundle = build_evidence_bundle_case_b(scenario=POLICY_CASE_B, location_id="INT-042", fabricated=fabricate_evidence)
    ok_ev, ev_reason = evidence_gate(audit, st, st.evidence_bundle)
    if not ok_ev:
        # Sealed decisions are centralized: only ethics_gate/acc_gate may set sealed=True.
        if ev_reason == RC_EVIDENCE_SCHEMA_INVALID:
            audit.emit(
                run_id=st.run_id,
                layer=LAYER_ACC,
                decision=DECISION_STOP,
                sealed=True,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_EVIDENCE_SCHEMA_INVALID,
            )
            st.sealed = True
            st.state = "STOPPED"
            cap_remaining = apply_trust_update(
                audit, st=st, trust=trust, outcome="EVIDENCE_SCHEMA_INVALID",
                delta_requested=DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
                reset_streak=True, set_cooldown=True,
            )
        save_trust_state(trust)
        return st, audit, trust
        cap_remaining = apply_trust_update(
            audit, st=st, trust=trust, outcome="EVIDENCE_FABRICATION",
            delta_requested=DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
            reset_streak=True, set_cooldown=True,
        )
        save_trust_state(trust)
        return st, audit, trust

    st.auth_request = build_auth_request_case_b(auth_request_id=f"AUTHREQ#{run_id}", auth_id=dummy_auth_id, ttl_seconds=120)

    if not critical_missing_gate(
        audit,
        st,
        layer=LAYER_BLACKLIST,
        data=st.auth_request,
        essentials=["schema_version", "auth_request_id", "auth_id", "context", "expires_at"],
        kind="auth_request",
    ):
        save_trust_state(trust)
        return st, audit, trust

    audit.emit(
        run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_PAUSE,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code="AUTH_REQUIRED",
        extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]},
    )
    st.state = "PAUSE_FOR_HITL_AUTH"

    scenario = st.auth_request["context"]["scenario"]
    location_id = st.auth_request["context"]["location_id"]
    auto_ok, trust_reason, grant_id = model_trust_gate(audit, st, trust, scenario, location_id)

    if auto_ok:
        audit.emit(
            run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_RUN,
            sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code="AUTH_SKIPPED",
            extra={"mode": "auto", "grant_id": grant_id},
        )
        st.state = "AUTH_VERIFIED"
    else:
        ev_type = "AUTH_APPROVE"
        auth_event = {
            "schema_version": "1.0",
            "event_type": ev_type,
            "ts": now_iso(),
            "actor": {"type": "USER", "id": "field_operator"},
            "target": {"kind": "AUTH_REQUEST", "auth_request_id": st.auth_request["auth_request_id"]},
            "notes": "bench auth",
        }
        validate_auth_event(auth_event)
        if is_auth_request_expired(st.auth_request, auth_event["ts"]):
            audit.emit(
                run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_STOP,
                sealed=True, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_AUTH_EXPIRED
            )
            st.sealed = True
            st.state = "STOPPED"
            cap_remaining = apply_trust_update(
                audit, st=st, trust=trust, outcome="AUTH_EXPIRED",
                delta_requested=DELTA_INVALID_EVENT, cap_remaining=cap_remaining,
                reset_streak=True, set_cooldown=True,
            )
            save_trust_state(trust)
            return st, audit, trust

        audit.emit(
            run_id=st.run_id, layer=LAYER_HITL_AUTH, decision=DECISION_RUN,
            sealed=False, overrideable=False, final_decider=DECIDER_USER, reason_code=RC_HITL_AUTH_APPROVE,
            extra={"auth_request_id": st.auth_request["auth_request_id"], "auth_id": st.auth_request["auth_id"]},
        )
        cap_remaining = apply_trust_update(
            audit, st=st, trust=trust, outcome="AUTH_APPROVE",
            delta_requested=DELTA_AUTH_APPROVE, cap_remaining=cap_remaining,
            reset_streak=False, set_cooldown=False,
        )
        st.state = "AUTH_VERIFIED"

    st.draft = generate_contract_draft(st=st)
    audit.emit(
        run_id=st.run_id, layer=LAYER_DOC_DRAFT, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_DRAFT_GENERATED,
        extra={"draft_id": st.draft["draft_id"]},
    )
    st.state = "DRAFT_READY"

    ok_lint, lint_reason = draft_lint_gate(audit, st, st.draft["content"])
    if not ok_lint:
        # Centralize sealed decision to ethics/acc only.
        if lint_reason in (RC_SAFETY_LEGAL_BINDING_CLAIM, RC_SAFETY_DISCRIMINATION_TERM):
            audit.emit(
                run_id=st.run_id,
                layer=LAYER_ETHICS,
                decision=DECISION_STOP,
                sealed=True,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=lint_reason,
            )
        else:
            audit.emit(
                run_id=st.run_id,
                layer=LAYER_ACC,
                decision=DECISION_STOP,
                sealed=True,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=lint_reason,
            )
        st.sealed = True
        st.state = "STOPPED"
        cap_remaining = apply_trust_update(
            audit, st=st, trust=trust, outcome="DRAFT_LINT_FAIL",
            delta_requested=DELTA_LINT_FAIL, cap_remaining=cap_remaining,
            reset_streak=True, set_cooldown=True,
        )
        save_trust_state(trust)
        return st, audit, trust

    audit.emit(
        run_id=st.run_id, layer=LAYER_ACC, decision=DECISION_PAUSE,
        sealed=False, overrideable=True, final_decider=DECIDER_SYSTEM, reason_code="ADMIN_FINALIZE_REQUIRED",
        extra={"draft_id": st.draft["draft_id"]},
    )
    st.state = "PAUSE_FOR_HITL_FINALIZE"

    finalize_event = {
        "schema_version": "1.0",
        "event_type": "FINALIZE_APPROVE",
        "ts": now_iso(),
        "actor": {"type": "ADMIN", "id": "ops_admin"},
        "target": {"kind": "DRAFT_DOCUMENT", "draft_id": st.draft["draft_id"]},
        "notes": "bench finalize",
    }
    validate_finalize_event(finalize_event)

    audit.emit(
        run_id=st.run_id, layer=LAYER_HITL_FINALIZE, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_ADMIN, reason_code=RC_FINALIZE_APPROVE,
        extra={"draft_id": st.draft["draft_id"]},
    )
    cap_remaining = apply_trust_update(
        audit, st=st, trust=trust, outcome="FINALIZE_APPROVE",
        delta_requested=DELTA_FINALIZE_APPROVE, cap_remaining=cap_remaining,
        reset_streak=False, set_cooldown=False,
    )

    st.contract = finalize_contract(st=st, admin_event=finalize_event)
    audit.emit(
        run_id=st.run_id, layer=LAYER_CONTRACT_EFFECT, decision=DECISION_RUN,
        sealed=False, overrideable=False, final_decider=DECIDER_SYSTEM, reason_code=RC_CONTRACT_EFFECTIVE,
        extra={"contract_id": st.contract["contract_id"], "draft_id": st.draft["draft_id"]},
    )
    st.state = "CONTRACT_EFFECTIVE"
    save_trust_state(trust)
    return st, audit, trust

def reset_stores() -> None:
    if TRUST_STORE_PATH.exists():
        TRUST_STORE_PATH.unlink()
    if GRANT_STORE_PATH.exists():
        GRANT_STORE_PATH.unlink()

# =========================
# HITL Queue (post-process)
# =========================
def _first_non_run_row(arl: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for r in arl:
        if r.get("decision") in (DECISION_PAUSE, DECISION_STOP):
            return r
    return None

def build_hitl_queue(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact "ops queue" from simulation results.
    - Source of truth: ARL rows in results["runs"][i]["arl"]
    - Queue items: only runs that ended in STOPPED or in PAUSE states.
    """
    items: List[Dict[str, Any]] = []
    by_reason: Dict[str, int] = {}
    by_state: Dict[str, int] = {}

    runs = results.get("runs", [])
    for rr in runs:
        run_id = rr.get("run_id", "")
        final_state = rr.get("final_state", "")
        sealed = bool(rr.get("sealed", False))
        arl = rr.get("arl", []) or []

        by_state[final_state] = by_state.get(final_state, 0) + 1

        if final_state not in ("STOPPED", "PAUSE_FOR_HITL_AUTH", "PAUSE_FOR_HITL_FINALIZE"):
            continue

        first_bad = _first_non_run_row(arl) or {}
        rc = str(first_bad.get("reason_code", "UNKNOWN"))
        by_reason[rc] = by_reason.get(rc, 0) + 1

        snapshot_keys = ("layer", "decision", "reason_code", "missing_keys", "kind", "error", "pattern")
        snapshot = {k: first_bad.get(k) for k in snapshot_keys if k in first_bad}

        items.append(
            {
                "run_id": run_id,
                "final_state": final_state,
                "sealed": sealed,
                "primary_reason_code": rc,
                "primary_layer": first_bad.get("layer"),
                "overrideable": first_bad.get("overrideable"),
                "final_decider": first_bad.get("final_decider"),
                "snapshot": snapshot,
            }
        )

    by_reason_top20 = dict(sorted(by_reason.items(), key=lambda kv: kv[1], reverse=True)[:20])

    return {
        "meta": {
            "version": "4.3",
            "generated_at": now_iso(),
            "policy_pack_hash": POLICY_PACK_HASH,
        },
        "counts": {
            "total_runs": len(runs),
            "by_state": dict(sorted(by_state.items(), key=lambda kv: kv[0])),
            "by_reason_code_top20": by_reason_top20,
            "queue_size": len(items),
        },
        "items": items,
    }

def write_queue_csv(queue: Dict[str, Any], path: Path) -> None:
    items = queue.get("items", []) or []
    fieldnames = [
        "run_id",
        "final_state",
        "sealed",
        "primary_reason_code",
        "primary_layer",
        "overrideable",
        "final_decider",
        "snapshot_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for it in items:
            w.writerow(
                {
                    "run_id": it.get("run_id"),
                    "final_state": it.get("final_state"),
                    "sealed": it.get("sealed"),
                    "primary_reason_code": it.get("primary_reason_code"),
                    "primary_layer": it.get("primary_layer"),
                    "overrideable": it.get("overrideable"),
                    "final_decider": it.get("final_decider"),
                    "snapshot_json": json.dumps(it.get("snapshot", {}), ensure_ascii=False),
                }
            )

def run_simulation(runs: int = 4, fabricate: bool = False) -> Dict[str, Any]:
    reset_stores()
    ensure_default_grant_exists()
    trust = load_trust_state()
    results: Dict[str, Any] = {"trust_before": trust.to_dict(), "runs": []}

    for i in range(runs):
        rid = f"SIM#B{(i+1):03d}"
        st, audit, trust = simulate_run(run_id=rid, dummy_auth_id="EMG-7K3P9Q", trust=trust, fabricate_evidence=fabricate)
        results["runs"].append(
            {"run_id": rid, "final_state": st.state, "sealed": st.sealed, "arl": audit.rows, "trust_after": trust.to_dict()}
        )

    results["trust_after"] = trust.to_dict()
    results["grants"] = {"grants": [g.to_dict() for g in load_grants()]}

    results["hitl_queue"] = build_hitl_queue(results)
    return results

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=4)
    p.add_argument("--fabricate", action="store_true")
    p.add_argument("--out", type=str, default="", help="write full results JSON to this path")
    p.add_argument("--queue-out", type=str, default="", help="write HITL queue JSON to this path")
    p.add_argument("--queue-csv", type=str, default="", help="write HITL queue CSV to this path")
    args = p.parse_args()

    results = run_simulation(runs=args.runs, fabricate=args.fabricate)

    s = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(s, encoding="utf-8")
    else:
        print(s)

    if args.queue_out:
        Path(args.queue_out).write_text(json.dumps(results["hitl_queue"], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.queue_csv:
        write_queue_csv(results["hitl_queue"], Path(args.queue_csv))

if __name__ == "__main__":
    main()