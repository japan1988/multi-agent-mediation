# -*- coding: utf-8 -*-
"""
kage_definition_hitl_gate_v1.py

Definition-Strict Gate + HITL + Accountability Logging (v1)

Purpose
- Determine whether a candidate spec/behavior qualifies as an "orchestrator" by a fixed definition pack.
- If the mapping is ambiguous (GRAY), fail-closed into HITL (PAUSE_FOR_HITL).
- Record final decider (SYSTEM/USER) and final choice into JSONL-like audit records.

Key properties
- 3-valued definition result: IN / OUT / GRAY
- Safety is non-overridable: if safety_red_flags hit -> STOPPED regardless of user choice.
- HITL decisions are appended as a separate audit event for traceability.

Run (demo):
  python kage_definition_hitl_gate_v1.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from typing import Any, Dict, List, Literal, Tuple


JST = timezone(timedelta(hours=9))

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
DefinitionTri = Literal["IN", "OUT", "GRAY"]
HitlChoice = Literal["APPROVE", "REJECT", "REVISE_DEF", "STOP"]


def _sha256_text(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(JST).isoformat()


class DefinitionPack:
    """
    Strict definition pack (tunable, but fixed as a single source of truth).
    """

    PACK_VERSION = "definition_hitl_gate_v1"

    # Minimum orchestrator features (must-have signals)
    MUST_FEATURES = [
        "task_decomposition",
        "routing",
        "guardrails_fail_closed",
        "audit_reason_codes",
        "hitl_escalation",
    ]

    # Non-overridable safety red flags (misuse boundary)
    SAFETY_RED_FLAGS = [
        "autonomous_external_actions",  # uncontrolled network/charge/contacts access etc.
        "pii_seeking_behavior",
        "manipulation_or_reeducation_intent",
    ]

    # Strict thresholds:
    # - IN: must_met >= 5
    # - OUT: must_met <= 2
    # - GRAY: otherwise
    IN_THRESHOLD = 5
    OUT_THRESHOLD = 2

    REQUIRED_AUDIT_FIELDS = [
        "run_id",
        "timestamp",
        "event",
        "layer",
        "decision",
        "reason_code",
        "evidence",
        "pack_version",
        "pack_hash",
    ]

    @classmethod
    def pack_hash(cls) -> str:
        blob = json.dumps(
            {
                "pack_version": cls.PACK_VERSION,
                "must_features": cls.MUST_FEATURES,
                "safety_red_flags": cls.SAFETY_RED_FLAGS,
                "in_threshold": cls.IN_THRESHOLD,
                "out_threshold": cls.OUT_THRESHOLD,
                "required_audit_fields": cls.REQUIRED_AUDIT_FIELDS,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return "sha256:" + sha256(blob).hexdigest()


@dataclass
class GateResult:
    decision: Decision
    reason_code: str
    evidence: Dict[str, Any]


class AuditLog:
    """
    Append-only audit log records (in-memory). You can write to JSONL if needed.
    """

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def emit(self, *, run_id: str, layer: str, decision: Decision, reason_code: str, evidence: Dict[str, Any]) -> None:
        rec = {
            "run_id": run_id,
            "timestamp": _now_iso(),
            "event": "DECISION",
            "layer": layer,
            "decision": decision,
            "reason_code": reason_code,
            "evidence": evidence,
            "pack_version": DefinitionPack.PACK_VERSION,
            "pack_hash": DefinitionPack.pack_hash(),
        }
        for k in DefinitionPack.REQUIRED_AUDIT_FIELDS:
            if k not in rec:
                raise AssertionError(f"audit log missing required field: {k}")
        self.records.append(rec)

    def write_jsonl(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def assess_definition(candidate: Dict[str, Any]) -> Tuple[DefinitionTri, float, Dict[str, Any]]:
    """
    Strict definition assessment:
    - Count MUST_FEATURES met
    - Determine tri-state IN/OUT/GRAY
    - Produce confidence (simple normalized score; conservative for GRAY)
    """
    must_met: List[str] = []
    must_missing: List[str] = []

    for k in DefinitionPack.MUST_FEATURES:
        if bool(candidate.get(k, False)):
            must_met.append(k)
        else:
            must_missing.append(k)

    met_count = len(must_met)

    if met_count >= DefinitionPack.IN_THRESHOLD:
        tri: DefinitionTri = "IN"
    elif met_count <= DefinitionPack.OUT_THRESHOLD:
        tri = "OUT"
    else:
        tri = "GRAY"

    denom = max(1, len(DefinitionPack.MUST_FEATURES))
    in_score = met_count / denom
    out_score = 1.0 - in_score
    confidence = in_score if tri == "IN" else (out_score if tri == "OUT" else 0.5)

    details = {
        "tri_state": tri,
        "must_met": must_met,
        "must_missing": must_missing,
        "must_met_count": met_count,
        "confidence": round(float(confidence), 3),
    }
    return tri, float(confidence), details


def assess_safety(candidate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Non-overridable safety assessment:
    If any safety red flag is true => STOPPED.
    """
    fired: List[str] = []
    for k in DefinitionPack.SAFETY_RED_FLAGS:
        if bool(candidate.get(k, False)):
            fired.append(k)
    return (len(fired) > 0), fired


def definition_gate(*, run_id: str, candidate: Dict[str, Any], audit: AuditLog) -> GateResult:
    """
    Main gate:
    - Safety red flags => STOPPED (non-overridable)
    - Else assess definition tri-state:
        IN  => RUN
        OUT => STOPPED (not an orchestrator by definition)
        GRAY=> PAUSE_FOR_HITL (ask user to decide)
    """
    safety_hit, safety_fired = assess_safety(candidate)
    tri, _, details = assess_definition(candidate)

    candidate_digest = _sha256_text(json.dumps(candidate, sort_keys=True, ensure_ascii=False))

    if safety_hit:
        evidence = {
            "candidate_hash": candidate_digest,
            "safety_red_flags": safety_fired,
            "non_overridable": True,
            "definition": details,
        }
        audit.emit(
            run_id=run_id,
            layer="definition_gate",
            decision="STOPPED",
            reason_code="SAFETY_RED_FLAG",
            evidence=evidence,
        )
        return GateResult("STOPPED", "SAFETY_RED_FLAG", evidence)

    if tri == "IN":
        evidence = {"candidate_hash": candidate_digest, "definition": details}
        audit.emit(run_id=run_id, layer="definition_gate", decision="RUN", reason_code="DEF_IN", evidence=evidence)
        return GateResult("RUN", "DEF_IN", evidence)

    if tri == "OUT":
        evidence = {"candidate_hash": candidate_digest, "definition": details}
        audit.emit(run_id=run_id, layer="definition_gate", decision="STOPPED", reason_code="DEF_OUT", evidence=evidence)
        return GateResult("STOPPED", "DEF_OUT", evidence)

    # GRAY -> HITL (fail-closed)
    evidence = {
        "candidate_hash": candidate_digest,
        "definition": details,
        "hitl_required": True,
        "suggested_choices": ["APPROVE", "REJECT", "REVISE_DEF", "STOP"],
        "note": "Ambiguous mapping to orchestrator definition. Escalate to user.",
    }
    audit.emit(
        run_id=run_id,
        layer="definition_gate",
        decision="PAUSE_FOR_HITL",
        reason_code="DEFINITION_AMBIGUOUS",
        evidence=evidence,
    )
    return GateResult("PAUSE_FOR_HITL", "DEFINITION_AMBIGUOUS", evidence)


def apply_hitl_choice(
    *,
    run_id: str,
    gate_result: GateResult,
    choice: HitlChoice,
    audit: AuditLog,
    user_id: str = "user",
) -> GateResult:
    """
    Apply user's final choice and append a separate audit event.

    Rules:
    - Safety is non-overridable: keep STOPPED regardless of user choice.
    - If original was GRAY (PAUSE_FOR_HITL):
        APPROVE => RUN
        REJECT  => STOPPED
        REVISE_DEF => STOPPED (signals definition update needed)
        STOP => STOPPED
    - If original was already RUN/STOPPED, log user's input but do not alter the prior decision.
    """
    # Non-overridable safety
    if gate_result.reason_code == "SAFETY_RED_FLAG":
        evidence = {
            "final_decider": "SYSTEM",
            "final_choice": "STOP",
            "authority_basis": "safety_non_overridable",
            "user_choice_received": choice,
            "user_id": user_id,
        }
        audit.emit(
            run_id=run_id,
            layer="hitl_finalize",
            decision="STOPPED",
            reason_code="NON_OVERRIDABLE_SAFETY",
            evidence=evidence,
        )
        return GateResult("STOPPED", "NON_OVERRIDABLE_SAFETY", evidence)

    # Only meaningful if it was HITL
    if gate_result.decision != "PAUSE_FOR_HITL":
        evidence = {
            "final_decider": "SYSTEM",
            "final_choice": "NOOP",
            "authority_basis": "not_in_hitl_state",
            "user_choice_received": choice,
            "user_id": user_id,
        }
        audit.emit(
            run_id=run_id,
            layer="hitl_finalize",
            decision=gate_result.decision,
            reason_code="HITL_NOOP",
            evidence=evidence,
        )
        return gate_result

    # HITL resolution
    if choice == "APPROVE":
        final_decision: Decision = "RUN"
        reason_code = "HITL_APPROVED"
    elif choice == "REJECT":
        final_decision = "STOPPED"
        reason_code = "HITL_REJECTED"
    elif choice == "REVISE_DEF":
        final_decision = "STOPPED"
        reason_code = "HITL_REVISE_DEF"
    else:  # STOP
        final_decision = "STOPPED"
        reason_code = "HITL_STOP"

    evidence = {
        "final_decider": "USER",
        "final_choice": choice,
        "authority_basis": "definition_ambiguous->hitl",
        "user_id": user_id,
        "original_reason_code": gate_result.reason_code,
    }
    audit.emit(run_id=run_id, layer="hitl_finalize", decision=final_decision, reason_code=reason_code, evidence=evidence)
    return GateResult(final_decision, reason_code, evidence)


def _demo() -> int:
    audit = AuditLog()
    run_id = _now_iso() + "#DEMO"

    # Example: GRAY candidate (3/5 must features)
    candidate = {
        "task_decomposition": True,
        "routing": True,
        "guardrails_fail_closed": True,
        "audit_reason_codes": False,
        "hitl_escalation": False,
        "autonomous_external_actions": False,
        "pii_seeking_behavior": False,
        "manipulation_or_reeducation_intent": False,
    }

    g = definition_gate(run_id=run_id, candidate=candidate, audit=audit)
    if g.decision == "PAUSE_FOR_HITL":
        # Simulate user decision
        g2 = apply_hitl_choice(run_id=run_id, gate_result=g, choice="REVISE_DEF", audit=audit, user_id="creator")
        print("HITL result:", g2.decision, g2.reason_code)

    audit.write_jsonl("kage_definition_hitl_log.jsonl")
    print("Wrote: kage_definition_hitl_log.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
