# -*- coding: utf-8 -*-
"""
emergency_contract_kage_orchestrator_v1_0.py

Minimal integrated simulator:
- Scenario: Emergency Contract / Case B
- Control system: KAGE-style orchestration gates
- Audit: tamper-evident ARL rows with HMAC chaining
- HITL: auth and admin-finalize decision points
- Dispatch: simulated contract draft artifact only

Design goal:
- Do not merge or modify existing simulator lines directly.
- Keep this as a small integration adapter / proof-of-concept.
- No real legal effect.
- No real signal control.
- No external submission, upload, send, API call, or deployment.

Canonical flow:
Meaning
→ Consistency
→ RFL
→ Evidence
→ Ethics
→ ACC
→ HITL auth
→ Draft
→ Draft lint
→ Admin finalize
→ Dispatch simulated artifact

Core invariants:
- RFL must never seal.
- sealed=True may only be emitted by ethics_gate or acc_gate.
- PAUSE_FOR_HITL must remain sealed=False and overrideable=True.
- Real external effects are not executed.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple


# ============================================================
# Version / constants
# ============================================================

__version__ = "1.0.0-minimal"

JST = timezone(timedelta(hours=9))
GENESIS_HASH = "0" * 64

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER", "ADMIN"]

DECISION_RUN: Decision = "RUN"
DECISION_PAUSE: Decision = "PAUSE_FOR_HITL"
DECISION_STOP: Decision = "STOPPED"

DECIDER_SYSTEM: FinalDecider = "SYSTEM"
DECIDER_USER: FinalDecider = "USER"
DECIDER_ADMIN: FinalDecider = "ADMIN"

LAYER_MEANING = "meaning_gate"
LAYER_CONSISTENCY = "consistency_gate"
LAYER_RFL = "relativity_gate"
LAYER_EVIDENCE = "evidence_gate"
LAYER_ETHICS = "ethics_gate"
LAYER_ACC = "acc_gate"
LAYER_HITL_AUTH = "hitl_auth"
LAYER_DOC_DRAFT = "doc_draft"
LAYER_DRAFT_LINT = "draft_lint_gate"
LAYER_HITL_FINALIZE = "hitl_finalize_admin"
LAYER_DISPATCH = "dispatch"
LAYER_CONTRACT_EFFECT = "contract_effect"

RC_OK = "OK"
RC_MEANING_OK = "MEANING_OK"
RC_MEANING_MISSING_SCENARIO = "MEANING_MISSING_SCENARIO"
RC_MEANING_NOT_EMERGENCY_CONTRACT = "MEANING_NOT_EMERGENCY_CONTRACT"

RC_CONSISTENCY_OK = "CONSISTENCY_OK"
RC_CONSISTENCY_BREAK = "CONSISTENCY_BREAK"

RC_REL_OK = "REL_OK"
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
RC_REL_REF_MISSING = "REL_REF_MISSING"

RC_EVIDENCE_OK = "EVIDENCE_OK"
RC_EVIDENCE_MISSING = "EVIDENCE_MISSING"
RC_EVIDENCE_SCHEMA_INVALID = "EVIDENCE_SCHEMA_INVALID"
RC_EVIDENCE_FABRICATION = "EVIDENCE_FABRICATION"

RC_ETHICS_OK = "ETHICS_OK"
RC_ETHICS_LEGAL_BINDING_CLAIM = "ETHICS_LEGAL_BINDING_CLAIM"
RC_ETHICS_DISCRIMINATION_TERM = "ETHICS_DISCRIMINATION_TERM"

RC_ACC_OK = "ACC_OK"
RC_ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL = (
    "ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL"
)
RC_ACC_REAL_WORLD_CONTROL_BLOCKED = "ACC_REAL_WORLD_CONTROL_BLOCKED"

RC_HITL_AUTH_REQUIRED = "AUTH_REQUIRED"
RC_HITL_AUTH_APPROVE = "AUTH_APPROVE"
RC_HITL_AUTH_REJECT = "AUTH_REJECT"

RC_DRAFT_GENERATED = "DRAFT_GENERATED"
RC_DRAFT_LINT_OK = "DRAFT_LINT_OK"
RC_DRAFT_OUT_OF_SCOPE = "DRAFT_OUT_OF_SCOPE"

RC_FINALIZE_REQUIRED = "ADMIN_FINALIZE_REQUIRED"
RC_FINALIZE_APPROVE = "FINALIZE_APPROVE"
RC_FINALIZE_STOP = "FINALIZE_STOP"

RC_CONTRACT_EFFECTIVE_SIMULATED = "CONTRACT_EFFECTIVE_SIMULATED"
RC_NON_OVERRIDABLE_SAFETY = "NON_OVERRIDABLE_SAFETY"

POLICY_CASE_B = "CASE_B_PED_IN_CROSSWALK_EMERGENCY_PRESENT"
POLICY_PRIORITY = "LIFE > PEDESTRIAN > VEHICLE"
POLICY_PACK_HASH = "POLICY_PACK#EMERGENCY_CONTRACT_KAGE#V1_0"

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
ISO_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")


# ============================================================
# Utility
# ============================================================

def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.#-]+", "_", value)
    return cleaned.strip("_") or "run"


def redact_sensitive_text(text: str) -> str:
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def deep_redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_sensitive_text(obj)
    if isinstance(obj, list):
        return [deep_redact(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): deep_redact(value) for key, value in obj.items()}
    return obj


def require_key(data: Dict[str, Any], key: str) -> Any:
    if key not in data:
        raise KeyError(f"missing required key: {key}")
    return data[key]


def validate_iso_string(value: Any, *, field_name: str) -> None:
    if not isinstance(value, str) or not ISO_PREFIX_RE.match(value):
        raise ValueError(f"{field_name} must be an ISO-8601 string")


def default_demo_key() -> bytes:
    """
    Demo key for local simulation only.

    Do not use this for production or real tamper-evidence requirements.
    """
    return hashlib.sha256(b"emergency-contract-kage-demo-key").digest()


# ============================================================
# Audit log / ARL
# ============================================================

@dataclass
class AuditRow:
    ts: str
    run_id: str
    layer: str
    decision: str
    sealed: bool
    overrideable: bool
    final_decider: str
    reason_code: str
    event: str = "GATE"
    detail: Optional[str] = None
    artifact_path: Optional[str] = None


@dataclass
class AuditLog:
    """
    Minimal tamper-evident ARL.

    This keeps rows in memory and can optionally export JSONL.
    Each persisted row contains prev_hash / row_hash.
    """

    key: bytes
    key_id: str = "demo-key"
    chain_id: str = field(default_factory=lambda: f"chain-{uuid.uuid4().hex[:12]}")
    _prev_hash: str = GENESIS_HASH
    _rows: List[Dict[str, Any]] = field(default_factory=list)

    def _validate_invariants(
        self,
        *,
        layer: str,
        decision: str,
        sealed: bool,
        overrideable: bool,
        final_decider: str,
    ) -> None:
        if sealed and layer not in {LAYER_ETHICS, LAYER_ACC}:
            raise RuntimeError(
                f"sealed=True may only be emitted by ethics/acc, got layer={layer}"
            )

        if layer == LAYER_RFL and sealed:
            raise RuntimeError("RFL / relativity_gate must never be sealed")

        if sealed and overrideable:
            raise RuntimeError("sealed=True implies overrideable=False")

        if sealed and final_decider != DECIDER_SYSTEM:
            raise RuntimeError("sealed=True implies final_decider=SYSTEM")

        if decision == DECISION_PAUSE and sealed:
            raise RuntimeError("PAUSE_FOR_HITL must not be sealed")

    def emit(
        self,
        *,
        run_id: str,
        layer: str,
        decision: Decision,
        sealed: bool,
        overrideable: bool,
        final_decider: FinalDecider,
        reason_code: str,
        event: str = "GATE",
        detail: Optional[str] = None,
        artifact_path: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_invariants(
            layer=layer,
            decision=decision,
            sealed=sealed,
            overrideable=overrideable,
            final_decider=final_decider,
        )

        body = asdict(
            AuditRow(
                ts=now_iso(),
                run_id=run_id,
                layer=layer,
                decision=decision,
                sealed=sealed,
                overrideable=overrideable,
                final_decider=final_decider,
                reason_code=reason_code,
                event=event,
                detail=detail,
                artifact_path=artifact_path,
            )
        )

        if extra:
            body.update(extra)

        body = deep_redact(body)

        row_hash = hmac_sha256_hex(
            self.key,
            (self._prev_hash + "\n").encode("utf-8") + canonical_json_bytes(body),
        )

        row = dict(body)
        row["prev_hash"] = self._prev_hash
        row["row_hash"] = row_hash
        row["key_id"] = self.key_id
        row["chain_id"] = self.chain_id

        self._rows.append(row)
        self._prev_hash = row_hash
        return row

    def rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(row, ensure_ascii=False) for row in self._rows)

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = self.to_jsonl()
        path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def verify_arl_rows(*, key: bytes, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
    prev = GENESIS_HASH

    for index, row in enumerate(rows):
        row_body = dict(row)
        got_prev = str(row_body.pop("prev_hash", ""))
        got_hash = str(row_body.pop("row_hash", ""))
        row_body.pop("key_id", None)
        row_body.pop("chain_id", None)

        if got_prev != prev:
            return False, f"prev_hash mismatch at row {index}"

        expected = hmac_sha256_hex(
            key,
            (prev + "\n").encode("utf-8") + canonical_json_bytes(row_body),
        )
        if not hmac.compare_digest(got_hash, expected):
            return False, f"row_hash mismatch at row {index}"

        prev = got_hash

    return True, "OK"


# ============================================================
# Scenario data
# ============================================================

@dataclass
class EmergencyContractInput:
    scenario: str = POLICY_CASE_B
    location_id: str = "INT-042"
    emergency_vehicle_state: str = "WAITING_AT_SIGNAL"
    ped_in_crosswalk: bool = True
    requested_external_effect: bool = False
    requested_real_signal_control: bool = False
    priority_policy: str = POLICY_PRIORITY


@dataclass
class OrchestratorState:
    run_id: str
    state: str = "INIT"
    sealed: bool = False
    auth_request: Optional[Dict[str, Any]] = None
    evidence_bundle: Optional[Dict[str, Any]] = None
    draft: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    artifact_path: Optional[str] = None


@dataclass
class RunResult:
    run_id: str
    decision: Decision
    final_state: str
    reason_code: str
    sealed: bool
    artifact_path: Optional[str]
    arl_rows: List[Dict[str, Any]]
    arl_verified: bool
    arl_verify_reason: str


def build_auth_request(
    *,
    scenario_input: EmergencyContractInput,
    auth_request_id: str,
    auth_id: str,
    ttl_seconds: int = 180,
) -> Dict[str, Any]:
    expires_at = (
        datetime.now(JST) + timedelta(seconds=int(ttl_seconds))
    ).isoformat(timespec="seconds")

    req = {
        "schema_version": "1.0",
        "auth_request_id": auth_request_id,
        "auth_id": auth_id,
        "context": {
            "scenario": scenario_input.scenario,
            "location_id": scenario_input.location_id,
            "emergency_vehicle_state": scenario_input.emergency_vehicle_state,
            "ped_in_crosswalk": scenario_input.ped_in_crosswalk,
            "priority_policy": scenario_input.priority_policy,
        },
        "expires_at": expires_at,
    }

    validate_auth_request(req)
    return req


def validate_auth_request(auth_request: Dict[str, Any]) -> None:
    if not isinstance(auth_request, dict):
        raise ValueError("auth_request must be object")

    if auth_request.get("schema_version") != "1.0":
        raise ValueError("auth_request.schema_version must be '1.0'")

    require_key(auth_request, "auth_request_id")
    require_key(auth_request, "auth_id")

    auth_id = str(auth_request["auth_id"])
    if not re.match(r"^EMG-[A-Z0-9]{6,20}$", auth_id):
        raise ValueError("auth_id must match ^EMG-[A-Z0-9]{6,20}$")

    ctx = require_key(auth_request, "context")
    if not isinstance(ctx, dict):
        raise ValueError("auth_request.context must be object")

    for key in [
        "scenario",
        "location_id",
        "emergency_vehicle_state",
        "ped_in_crosswalk",
        "priority_policy",
    ]:
        require_key(ctx, key)

    validate_iso_string(auth_request.get("expires_at"), field_name="expires_at")


def auth_request_expired(auth_request: Dict[str, Any]) -> bool:
    return datetime.now(JST) > parse_iso(str(auth_request["expires_at"]))


def build_evidence_bundle_case_b(
    *,
    scenario_input: EmergencyContractInput,
    fabricated: bool = False,
) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "scenario": scenario_input.scenario,
        "location_id": scenario_input.location_id,
        "evidence_items": [
            {
                "evidence_id": "EV#CASE_B#001",
                "source_id": "SIM_SOURCE",
                "locator": {
                    "kind": "SIM",
                    "location_id": scenario_input.location_id,
                },
                "retrieved_at": now_iso(),
                "hash": {
                    "algo": "sha256",
                    "value": "SIMULATED",
                },
                "supports": [
                    {
                        "claim": "emergency_vehicle_present",
                        "value": scenario_input.emergency_vehicle_state,
                    },
                    {
                        "claim": "ped_in_crosswalk",
                        "value": scenario_input.ped_in_crosswalk,
                    },
                    {
                        "claim": "priority_policy",
                        "value": scenario_input.priority_policy,
                    },
                ],
                "fabricated": bool(fabricated),
                "relevance": "high",
            }
        ],
    }


def validate_evidence_bundle(bundle: Dict[str, Any]) -> None:
    if not isinstance(bundle, dict):
        raise ValueError("evidence bundle must be object")

    if bundle.get("schema_version") != "1.0":
        raise ValueError("evidence bundle schema_version must be '1.0'")

    for key in ["scenario", "location_id", "evidence_items"]:
        require_key(bundle, key)

    items = bundle["evidence_items"]
    if not isinstance(items, list) or not items:
        raise ValueError("evidence_items must be non-empty list")

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be object")

        for key in [
            "evidence_id",
            "source_id",
            "locator",
            "retrieved_at",
            "hash",
            "supports",
            "fabricated",
        ]:
            require_key(item, key)

        validate_iso_string(item["retrieved_at"], field_name="retrieved_at")

        if not isinstance(item["locator"], dict):
            raise ValueError("locator must be object")

        if not isinstance(item["hash"], dict):
            raise ValueError("hash must be object")

        if not isinstance(item["supports"], list):
            raise ValueError("supports must be list")


# ============================================================
# Gates
# ============================================================

def meaning_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
) -> bool:
    if not scenario_input.scenario:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_MEANING,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_MEANING_MISSING_SCENARIO,
        )
        return False

    if scenario_input.scenario != POLICY_CASE_B:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_MEANING,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_MEANING_NOT_EMERGENCY_CONTRACT,
            detail=f"scenario={scenario_input.scenario}",
        )
        return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_MEANING,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_MEANING_OK,
    )
    return True


def consistency_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
) -> bool:
    if st.auth_request is None:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_CONSISTENCY,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_CONSISTENCY_BREAK,
            detail="auth_request missing",
        )
        return False

    ctx = st.auth_request.get("context", {})
    checks = {
        "scenario": ctx.get("scenario") == scenario_input.scenario,
        "location_id": ctx.get("location_id") == scenario_input.location_id,
        "emergency_vehicle_state": (
            ctx.get("emergency_vehicle_state")
            == scenario_input.emergency_vehicle_state
        ),
        "ped_in_crosswalk": ctx.get("ped_in_crosswalk")
        == scenario_input.ped_in_crosswalk,
    }

    failed = [key for key, ok in checks.items() if not ok]
    if failed:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_CONSISTENCY,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_CONSISTENCY_BREAK,
            detail=f"failed={failed}",
        )
        return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_CONSISTENCY,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_CONSISTENCY_OK,
    )
    return True


def rfl_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
    hitl_continue_on_rfl: bool,
) -> bool:
    """
    RFL handles relative / priority-boundary questions.

    In this minimal scenario, the policy must explicitly define:
    LIFE > PEDESTRIAN > VEHICLE

    If not present, RFL pauses for HITL and never seals.
    """
    policy = scenario_input.priority_policy or ""

    if "LIFE" not in policy or "PEDESTRIAN" not in policy or "VEHICLE" not in policy:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_RFL,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_REL_REF_MISSING,
            detail="priority policy reference missing",
        )

        return finalize_hitl_user(
            audit,
            st=st,
            approved=hitl_continue_on_rfl,
            source_layer=LAYER_RFL,
            approve_reason=RC_REL_OK,
            reject_reason=RC_REL_BOUNDARY_UNSTABLE,
        )

    if scenario_input.emergency_vehicle_state and scenario_input.ped_in_crosswalk:
        # This is a relative-priority situation, but the explicit policy is present.
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_RFL,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_REL_OK,
            detail=f"policy={policy}",
        )
        return True

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_RFL,
        decision=DECISION_PAUSE,
        sealed=False,
        overrideable=True,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_REL_BOUNDARY_UNSTABLE,
        detail="relative boundary requires HITL",
    )

    return finalize_hitl_user(
        audit,
        st=st,
        approved=hitl_continue_on_rfl,
        source_layer=LAYER_RFL,
        approve_reason=RC_REL_OK,
        reject_reason=RC_REL_BOUNDARY_UNSTABLE,
    )


def evidence_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
) -> bool:
    bundle = st.evidence_bundle
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
        return False

    try:
        validate_evidence_bundle(bundle)
    except Exception as err:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_SCHEMA_INVALID,
            detail=str(err),
        )
        return False

    if bundle.get("scenario") != scenario_input.scenario:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_CONSISTENCY_BREAK,
            detail="evidence scenario mismatch",
        )
        return False

    if bundle.get("location_id") != scenario_input.location_id:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_CONSISTENCY_BREAK,
            detail="evidence location mismatch",
        )
        return False

    fabricated = any(
        bool(item.get("fabricated", False))
        for item in bundle.get("evidence_items", [])
        if isinstance(item, dict)
    )
    if fabricated:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_EVIDENCE,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_EVIDENCE_FABRICATION,
        )
        return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_EVIDENCE,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_EVIDENCE_OK,
        extra={"policy_pack_hash": POLICY_PACK_HASH},
    )
    return True


_NEG_WORDS = ("not", "no", "cannot", "can't", "without", "lacks", "lack", "never")
_LEGAL_BINDING_PATTERNS = [
    re.compile(r"\blegally binding\b", re.IGNORECASE),
    re.compile(r"\bthis contract is binding\b", re.IGNORECASE),
    re.compile(r"\bwe guarantee\b", re.IGNORECASE),
    re.compile(r"\bhas legal authority\b", re.IGNORECASE),
    re.compile(r"\bgrants? legal authority\b", re.IGNORECASE),
]
_DISCRIMINATION_PATTERNS = [
    re.compile(r"\b(discriminat(?:e|ion)|racist|racial slur)\b", re.IGNORECASE),
]


def _window_before(text: str, idx: int, n: int = 40) -> str:
    lo = max(0, idx - n)
    return text[lo:idx].lower()


def _is_negated(text: str, match_start: int) -> bool:
    window = _window_before(text, match_start)
    parts = set(window.split())
    return any(word in parts or word in window for word in _NEG_WORDS)


def ethics_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    draft_md: str,
) -> bool:
    text = draft_md or ""

    for pattern in _LEGAL_BINDING_PATTERNS:
        match = pattern.search(text)
        if match and not _is_negated(text, match.start()):
            st.sealed = True
            audit.emit(
                run_id=st.run_id,
                layer=LAYER_ETHICS,
                decision=DECISION_STOP,
                sealed=True,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_ETHICS_LEGAL_BINDING_CLAIM,
                detail=pattern.pattern,
            )
            return False

    for pattern in _DISCRIMINATION_PATTERNS:
        match = pattern.search(text)
        if match and not _is_negated(text, match.start()):
            st.sealed = True
            audit.emit(
                run_id=st.run_id,
                layer=LAYER_ETHICS,
                decision=DECISION_STOP,
                sealed=True,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_ETHICS_DISCRIMINATION_TERM,
                detail=pattern.pattern,
            )
            return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_ETHICS,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_ETHICS_OK,
    )
    return True


def acc_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
    allow_external_effects: bool,
) -> bool:
    if scenario_input.requested_real_signal_control:
        st.sealed = True
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_ACC,
            decision=DECISION_STOP,
            sealed=True,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_ACC_REAL_WORLD_CONTROL_BLOCKED,
            detail="real signal control is blocked in this simulator",
        )
        return False

    if scenario_input.requested_external_effect and not allow_external_effects:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_ACC,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL,
            detail="external effect requested but not allowed",
        )
        return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_ACC,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_ACC_OK,
    )
    return True


# ============================================================
# HITL / draft / dispatch
# ============================================================

def finalize_hitl_user(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    approved: bool,
    source_layer: str,
    approve_reason: str,
    reject_reason: str,
) -> bool:
    if approved:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_HITL_AUTH,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_USER,
            reason_code=approve_reason,
            detail=f"continue from {source_layer}",
        )
        return True

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_HITL_AUTH,
        decision=DECISION_STOP,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_USER,
        reason_code=reject_reason,
        detail=f"stopped from {source_layer}",
    )
    return False


def hitl_auth_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    auth_approved: bool,
) -> bool:
    audit.emit(
        run_id=st.run_id,
        layer=LAYER_HITL_AUTH,
        decision=DECISION_PAUSE,
        sealed=False,
        overrideable=True,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_HITL_AUTH_REQUIRED,
    )

    if auth_approved:
        st.state = "AUTH_VERIFIED"
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_HITL_AUTH,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_USER,
            reason_code=RC_HITL_AUTH_APPROVE,
        )
        return True

    st.state = "STOPPED"
    audit.emit(
        run_id=st.run_id,
        layer=LAYER_HITL_AUTH,
        decision=DECISION_STOP,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_USER,
        reason_code=RC_HITL_AUTH_REJECT,
    )
    return False


def generate_contract_draft(
    *,
    st: OrchestratorState,
    scenario_input: EmergencyContractInput,
) -> Dict[str, Any]:
    if st.auth_request is None:
        raise RuntimeError("auth_request is required before draft generation")

    draft_id = f"DRAFT#{st.run_id}"
    ctx = st.auth_request["context"]

    draft_md = f"""# Agreement Draft — Emergency Signal Priority

**Draft ID**: {draft_id}
**Run ID**: {st.run_id}
**Scenario**: {ctx.get("scenario")}
**Location**: {ctx.get("location_id")}
**Policy**: {scenario_input.priority_policy}
**Generated At**: {now_iso()}

---

## 1. Purpose

This is a research simulation draft for emergency signal priority reasoning.

## 2. Priority Order

1. LIFE: emergency vehicle safety
2. PEDESTRIAN: pedestrian protection in crosswalk
3. VEHICLE: general vehicle flow

## 3. Case B Rule

When an emergency vehicle is present and a pedestrian is already in the
crosswalk, pedestrian protection remains active while emergency priority is
prepared.

## 4. Safety and Scope

- This is a draft only.
- This has no operational effect.
- AI is used for drafting only.
- ADMIN approval is required before any simulated contract effect is recorded.
- This does not control real signals.
- This does not create legal authority.
- This is not legally binding.

## 5. Evidence

Evidence bundle is required and must pass schema and fabrication checks.

## 6. Simulated Outcome

If ADMIN approves, this simulator may record a simulated contract effect only.
"""

    return {
        "draft_id": draft_id,
        "draft_md": draft_md,
        "schema_version": "1.0",
    }


def draft_lint_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    draft: Dict[str, Any],
) -> bool:
    text = str(draft.get("draft_md", ""))
    normalized = re.sub(r"[*_]", "", text).lower()

    required = [
        "draft only",
        "no operational effect",
        "ai is used for drafting only",
        "admin approval",
        "not legally binding",
    ]
    missing = [item for item in required if item not in normalized]

    if missing:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_DRAFT_LINT,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_DRAFT_OUT_OF_SCOPE,
            detail=f"missing={missing}",
        )
        return False

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_DRAFT_LINT,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_DRAFT_LINT_OK,
    )
    return True


def admin_finalize_gate(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    admin_approved: bool,
) -> bool:
    audit.emit(
        run_id=st.run_id,
        layer=LAYER_HITL_FINALIZE,
        decision=DECISION_PAUSE,
        sealed=False,
        overrideable=True,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_FINALIZE_REQUIRED,
    )

    if admin_approved:
        audit.emit(
            run_id=st.run_id,
            layer=LAYER_HITL_FINALIZE,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_ADMIN,
            reason_code=RC_FINALIZE_APPROVE,
        )
        return True

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_HITL_FINALIZE,
        decision=DECISION_STOP,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_ADMIN,
        reason_code=RC_FINALIZE_STOP,
    )
    return False


def dispatch_simulated_artifact(
    audit: AuditLog,
    *,
    st: OrchestratorState,
    out_dir: Path,
    hmac_key: bytes,
) -> str:
    if st.draft is None:
        raise RuntimeError("draft is required before dispatch")

    out_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = out_dir / f"{safe_filename(st.run_id)}__contract_draft.md"
    artifact_bytes = str(st.draft["draft_md"]).encode("utf-8")

    artifact_path.write_bytes(artifact_bytes)

    artifact_sha256 = sha256_hex_bytes(artifact_bytes)
    artifact_hmac = hmac_sha256_hex(
        hmac_key,
        canonical_json_bytes(
            {
                "run_id": st.run_id,
                "artifact_path": str(artifact_path),
                "artifact_sha256": artifact_sha256,
            }
        ),
    )

    st.artifact_path = str(artifact_path)
    st.contract = {
        "contract_id": f"CONTRACT#SIM#{st.run_id}",
        "simulated_effect": True,
        "real_world_effect": False,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "artifact_hmac": artifact_hmac,
    }

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_DISPATCH,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_DRAFT_GENERATED,
        event="ARTIFACT_WRITTEN",
        artifact_path=str(artifact_path),
        extra={
            "artifact_sha256": artifact_sha256,
            "artifact_hmac": artifact_hmac,
        },
    )

    audit.emit(
        run_id=st.run_id,
        layer=LAYER_CONTRACT_EFFECT,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_ADMIN,
        reason_code=RC_CONTRACT_EFFECTIVE_SIMULATED,
        event="CONTRACT_EFFECT_SIMULATED",
        artifact_path=str(artifact_path),
    )

    return str(artifact_path)


# ============================================================
# Main integrated run
# ============================================================

def run_emergency_contract_kage_orchestration(
    *,
    run_id: str,
    scenario_input: EmergencyContractInput,
    evidence_bundle: Optional[Dict[str, Any]] = None,
    hmac_key: Optional[bytes] = None,
    out_dir: str = "out/emergency_contract_kage",
    auth_approved: bool = True,
    admin_finalize_approved: bool = True,
    hitl_continue_on_rfl: bool = True,
    allow_external_effects: bool = False,
    fabricated_evidence: bool = False,
) -> RunResult:
    key = hmac_key or default_demo_key()
    audit = AuditLog(key=key, key_id="demo-key")

    st = OrchestratorState(run_id=run_id)

    try:
        st.auth_request = build_auth_request(
            scenario_input=scenario_input,
            auth_request_id=f"AUTHREQ#{run_id}",
            auth_id="EMG-DEMO001",
            ttl_seconds=180,
        )
    except Exception as err:
        audit.emit(
            run_id=run_id,
            layer=LAYER_CONSISTENCY,
            decision=DECISION_PAUSE,
            sealed=False,
            overrideable=True,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_CONSISTENCY_BREAK,
            detail=f"auth_request build failed: {err}",
        )
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_PAUSE,
            final_state="PAUSE_FOR_HITL",
            reason_code=RC_CONSISTENCY_BREAK,
            sealed=False,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    st.evidence_bundle = (
        evidence_bundle
        if evidence_bundle is not None
        else build_evidence_bundle_case_b(
            scenario_input=scenario_input,
            fabricated=fabricated_evidence,
        )
    )

    gates = [
        (
            LAYER_MEANING,
            lambda: meaning_gate(
                audit,
                st=st,
                scenario_input=scenario_input,
            ),
            RC_MEANING_MISSING_SCENARIO,
        ),
        (
            LAYER_CONSISTENCY,
            lambda: consistency_gate(
                audit,
                st=st,
                scenario_input=scenario_input,
            ),
            RC_CONSISTENCY_BREAK,
        ),
        (
            LAYER_RFL,
            lambda: rfl_gate(
                audit,
                st=st,
                scenario_input=scenario_input,
                hitl_continue_on_rfl=hitl_continue_on_rfl,
            ),
            RC_REL_BOUNDARY_UNSTABLE,
        ),
        (
            LAYER_EVIDENCE,
            lambda: evidence_gate(
                audit,
                st=st,
                scenario_input=scenario_input,
            ),
            RC_EVIDENCE_MISSING,
        ),
    ]

    for _layer, gate_fn, fallback_reason in gates:
        if not gate_fn():
            ok, reason = verify_arl_rows(key=key, rows=audit.rows())
            return RunResult(
                run_id=run_id,
                decision=DECISION_PAUSE,
                final_state="PAUSE_FOR_HITL",
                reason_code=fallback_reason,
                sealed=st.sealed,
                artifact_path=st.artifact_path,
                arl_rows=audit.rows(),
                arl_verified=ok,
                arl_verify_reason=reason,
            )

    if not hitl_auth_gate(audit, st=st, auth_approved=auth_approved):
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_STOP,
            final_state="STOPPED",
            reason_code=RC_HITL_AUTH_REJECT,
            sealed=st.sealed,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    st.draft = generate_contract_draft(st=st, scenario_input=scenario_input)
    audit.emit(
        run_id=run_id,
        layer=LAYER_DOC_DRAFT,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_DRAFT_GENERATED,
        event="DRAFT_GENERATED",
        detail=str(st.draft.get("draft_id")),
    )

    if not ethics_gate(audit, st=st, draft_md=str(st.draft.get("draft_md", ""))):
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_STOP,
            final_state="STOPPED",
            reason_code=RC_ETHICS_LEGAL_BINDING_CLAIM,
            sealed=st.sealed,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    if not draft_lint_gate(audit, st=st, draft=st.draft):
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_PAUSE,
            final_state="PAUSE_FOR_HITL",
            reason_code=RC_DRAFT_OUT_OF_SCOPE,
            sealed=st.sealed,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    if not acc_gate(
        audit,
        st=st,
        scenario_input=scenario_input,
        allow_external_effects=allow_external_effects,
    ):
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_STOP if st.sealed else DECISION_PAUSE,
            final_state="STOPPED" if st.sealed else "PAUSE_FOR_HITL",
            reason_code=(
                RC_ACC_REAL_WORLD_CONTROL_BLOCKED
                if st.sealed
                else RC_ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL
            ),
            sealed=st.sealed,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    if not admin_finalize_gate(
        audit,
        st=st,
        admin_approved=admin_finalize_approved,
    ):
        ok, reason = verify_arl_rows(key=key, rows=audit.rows())
        return RunResult(
            run_id=run_id,
            decision=DECISION_STOP,
            final_state="STOPPED",
            reason_code=RC_FINALIZE_STOP,
            sealed=st.sealed,
            artifact_path=None,
            arl_rows=audit.rows(),
            arl_verified=ok,
            arl_verify_reason=reason,
        )

    artifact_path = dispatch_simulated_artifact(
        audit,
        st=st,
        out_dir=Path(out_dir),
        hmac_key=key,
    )

    ok, reason = verify_arl_rows(key=key, rows=audit.rows())

    return RunResult(
        run_id=run_id,
        decision=DECISION_RUN,
        final_state="CONTRACT_EFFECTIVE_SIMULATED",
        reason_code=RC_CONTRACT_EFFECTIVE_SIMULATED,
        sealed=st.sealed,
        artifact_path=artifact_path,
        arl_rows=audit.rows(),
        arl_verified=ok,
        arl_verify_reason=reason,
    )


# ============================================================
# CLI
# ============================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Minimal Emergency Contract × KAGE orchestration simulator."
    )
    parser.add_argument("--run-id", default="RUN#EMG-KAGE-001")
    parser.add_argument("--out-dir", default="out/emergency_contract_kage")
    parser.add_argument("--arl-out", default="")
    parser.add_argument("--fabricated-evidence", action="store_true")
    parser.add_argument("--auth-reject", action="store_true")
    parser.add_argument("--finalize-stop", action="store_true")
    parser.add_argument("--rfl-stop", action="store_true")
    parser.add_argument("--request-external-effect", action="store_true")
    parser.add_argument("--request-real-signal-control", action="store_true")
    parser.add_argument("--allow-external-effects", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    scenario = EmergencyContractInput(
        requested_external_effect=bool(args.request_external_effect),
        requested_real_signal_control=bool(args.request_real_signal_control),
    )

    key = default_demo_key()

    result = run_emergency_contract_kage_orchestration(
        run_id=str(args.run_id),
        scenario_input=scenario,
        hmac_key=key,
        out_dir=str(args.out_dir),
        auth_approved=not bool(args.auth_reject),
        admin_finalize_approved=not bool(args.finalize_stop),
        hitl_continue_on_rfl=not bool(args.rfl_stop),
        allow_external_effects=bool(args.allow_external_effects),
        fabricated_evidence=bool(args.fabricated_evidence),
    )

    if args.arl_out:
        arl_path = Path(str(args.arl_out))
        arl_path.parent.mkdir(parents=True, exist_ok=True)
        arl_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in result.arl_rows)
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "decision": result.decision,
                "final_state": result.final_state,
                "reason_code": result.reason_code,
                "sealed": result.sealed,
                "artifact_path": result.artifact_path,
                "arl_rows": len(result.arl_rows),
                "arl_verified": result.arl_verified,
                "arl_verify_reason": result.arl_verify_reason,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if result.decision == DECISION_RUN else 1


if __name__ == "__main__":
    raise SystemExit(main())
