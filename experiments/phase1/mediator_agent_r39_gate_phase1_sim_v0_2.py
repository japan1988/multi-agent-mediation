#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mediator_agent_r39_gate_phase1_sim_v0_2.py

Phase 1 local-only simulator:
Agent -> Mediator -> MediationGate -> USER/HITL -> Orchestrator

v0.2 closes the four DRAFT v1.4/v1.5 review gaps:
1. append-only ViolationHistory
2. method/outcome SHA-256 fingerprints persisted in history
3. HumanDecision.decide() enum validation
4. explicit REVALIDATING evaluation state

No automatic correction or external action is permitted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Fixed safety boundary
# ---------------------------------------------------------------------------

AUTO_FIX_ALLOWED = False
AUTO_APPLY_REVISION = False
AUTO_COMMIT = False
AUTO_PUSH = False
AUTO_MERGE = False
NETWORK_ACCESS_ALLOWED = False
EXTERNAL_EXECUTION_ALLOWED = False

ALLOW = "ALLOW"
PAUSE = "PAUSE_FOR_HITL"
BLOCK = "BLOCK"
STOPPED = "STOPPED"

ACTIVE = "ACTIVE"
PAUSED = "PAUSED_FOR_HITL"
REVALIDATING = "REVALIDATING"
BLOCKED = "BLOCKED"
DISPATCH_READY = "DISPATCH_READY"
DISPATCHED = "DISPATCHED_SIMULATED"
STOPPED_BY_USER = "STOPPED_BY_USER"

NONE = "NONE"
FIRST = "FIRST_OCCURRENCE"
NORMAL_REVISION = "NORMAL_REVISION"
EXACT = "EXACT_RECURRENCE"
RECURRENCE_CANDIDATE = "RECURRENCE_CANDIDATE"
SIMILAR = "SIMILAR"
DIFFERENT = "DIFFERENT"
SCOPE_VIOLATION = "REVISION_SCOPE_VIOLATION"
NEW_CONTEXT = "NEW_CONTEXT"
UNKNOWN = "UNKNOWN"

USER_APPROVE = "APPROVE"
USER_REJECT = "REJECT"
USER_REQUEST_REVISION = "REQUEST_REVISION"
USER_STOP = "STOP"
USER_DECISIONS = {
    USER_APPROVE,
    USER_REJECT,
    USER_REQUEST_REVISION,
    USER_STOP,
}

PROTECTED_INVARIANTS = {
    "USER_DECIDES",
    "AUTHORITY_BOUNDARY",
    "SEMANTIC_CONTINUITY",
    "TRANSACTION_BINDING",
    "EVIDENCE_INTEGRITY",
    "AUDIT_INTEGRITY",
    "EXECUTION_BOUNDARY",
}

RESULT_CLASSES = {
    "UNAUTHORIZED_DECISION_SUBSTITUTION",
    "AUTHORITY_SCOPE_EXCEEDED",
    "PURPOSE_OR_ROLE_DRIFT",
    "BINDING_MISMATCH",
    "EVIDENCE_INVALID",
    "AUDIT_STATE_INVALID",
    "UNAUTHORIZED_EXECUTION",
    "UNKNOWN_OR_UNRESOLVED_STATE",
}

EFFECTS = {
    "USER_APPROVAL_BYPASSED",
    "USER_DECISION_REPLACED",
    "ROLE_BOUNDARY_EXCEEDED",
    "ORIGINAL_PURPOSE_CHANGED",
    "REQUEST_DECISION_MISBOUND",
    "TRANSACTION_SCOPE_CHANGED",
    "EVIDENCE_MISSING",
    "EVIDENCE_HASH_MISMATCH",
    "AUDIT_CHAIN_BROKEN",
    "AUDIT_RECORD_TAMPERED",
    "UNAPPROVED_DISPATCH_ATTEMPT",
    "UNAPPROVED_COMMIT_ATTEMPT",
    "STATE_UNRESOLVED",
}

SCOPE_TYPES = {
    "REQUEST",
    "TRANSACTION",
    "PROPOSAL",
    "USER_DECISION",
    "AGENT",
    "ORCHESTRATION_RUN",
    "AUDIT_CHAIN",
}

IMMEDIATE_BLOCK = {
    "FORGED_USER_DECISION",
    "MEDIATOR_COMMIT_ATTEMPT",
    "GATE_BYPASS_ATTEMPT",
    "AUDIT_RECORD_TAMPER",
    "UNAPPROVED_EXTERNAL_EXECUTION",
}


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def norm_method(method: Optional[dict[str, Any]]) -> dict[str, str]:
    method = method or {}
    return {
        "reason_code": str(method.get("reason_code", "")).strip().upper(),
        "violation_scope": str(method.get("violation_scope", "")).strip().lower(),
        "mechanism": str(method.get("mechanism", "")).strip().upper(),
    }


def norm_purpose(purpose: Optional[dict[str, Any]]) -> dict[str, str]:
    purpose = purpose or {}
    return {
        "task_purpose": str(purpose.get("task_purpose", "")).strip().upper(),
        "authority_purpose": str(purpose.get("authority_purpose", "")).strip().upper(),
        "execution_intent": str(purpose.get("execution_intent", "")).strip().upper(),
    }


def norm_outcome(outcome: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if outcome is None:
        return None
    scope = outcome.get("target_scope") or {}
    return {
        "protected_invariant": str(outcome.get("protected_invariant", "")).strip().upper(),
        "result_class": str(outcome.get("result_class", "")).strip().upper(),
        "target_scope": {
            "scope_type": str(scope.get("scope_type", "")).strip().upper(),
            "scope_id": str(scope.get("scope_id", "")).strip().upper(),
        },
        "effect": str(outcome.get("effect", "")).strip().upper(),
    }


def method_fingerprint(method: dict[str, Any]) -> str:
    return sha256_obj(norm_method(method))


def outcome_fingerprint(outcome: Optional[dict[str, Any]]) -> Optional[str]:
    normalized = norm_outcome(outcome)
    return None if normalized is None else sha256_obj(normalized)


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    request_record_id: str
    transaction_id: str
    lineage_id: str
    method: dict[str, Any]
    purpose: dict[str, Any]
    outcome: Optional[dict[str, Any]]
    authority: str = "ADVISORY_ONLY"
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    decision: str
    next_state: str
    reason_code: str
    comparison: str
    evaluation_state: str
    dispatch_allowed: bool = False
    final: bool = False
    retry_allowed: bool = True


@dataclass(frozen=True)
class ViolationHistoryRecord:
    record_id: str
    record_type: str
    lineage_id: str
    request_record_id: str
    transaction_id: str
    method_fingerprint: str
    outcome_fingerprint: Optional[str]
    method: dict[str, Any]
    purpose: dict[str, Any]
    outcome: Optional[dict[str, Any]]
    decision: str
    reason_code: str
    resolution_state: str
    evaluation_state: str
    resolves_event_id: Optional[str] = None


class AuditLog:
    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def append(self, payload: dict[str, Any]) -> None:
        prev_hash = self._rows[-1]["record_hash"] if self._rows else ""
        row = {
            "seq": len(self._rows) + 1,
            "prev_hash": prev_hash,
            "payload": payload,
        }
        row["record_hash"] = sha256_obj(row)
        self._rows.append(row)

    def verify(self) -> bool:
        prev = ""
        for index, row in enumerate(self._rows, start=1):
            if row.get("seq") != index or row.get("prev_hash") != prev:
                return False
            expected = sha256_obj({"seq": row["seq"], "prev_hash": row["prev_hash"], "payload": row["payload"]})
            if row.get("record_hash") != expected:
                return False
            prev = row["record_hash"]
        return True

    def rows(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self._rows))

    def tamper_for_test(self) -> None:
        if self._rows:
            self._rows[0]["payload"] = {"probe": "tampered"}


class ViolationHistory:
    def __init__(self) -> None:
        self._records: list[ViolationHistoryRecord] = []

    def append_event(self, *, proposal: Proposal, result: GateResult) -> ViolationHistoryRecord:
        record = ViolationHistoryRecord(
            record_id=f"VIO-{len(self._records)+1:03d}",
            record_type="VIOLATION",
            lineage_id=proposal.lineage_id,
            request_record_id=proposal.request_record_id,
            transaction_id=proposal.transaction_id,
            method_fingerprint=method_fingerprint(proposal.method),
            outcome_fingerprint=outcome_fingerprint(proposal.outcome),
            method=norm_method(proposal.method),
            purpose=norm_purpose(proposal.purpose),
            outcome=norm_outcome(proposal.outcome),
            decision=result.decision,
            reason_code=result.reason_code,
            resolution_state="BLOCKED" if result.decision == BLOCK else "UNRESOLVED",
            evaluation_state=result.evaluation_state,
        )
        self._records.append(record)
        return record

    def append_resolution(self, *, resolves_event_id: str, proposal: Proposal, result: GateResult) -> ViolationHistoryRecord:
        record = ViolationHistoryRecord(
            record_id=f"RES-{len(self._records)+1:03d}",
            record_type="RESOLUTION",
            lineage_id=proposal.lineage_id,
            request_record_id=proposal.request_record_id,
            transaction_id=proposal.transaction_id,
            method_fingerprint=method_fingerprint(proposal.method),
            outcome_fingerprint=outcome_fingerprint(proposal.outcome),
            method=norm_method(proposal.method),
            purpose=norm_purpose(proposal.purpose),
            outcome=norm_outcome(proposal.outcome),
            decision=result.decision,
            reason_code=result.reason_code,
            resolution_state="RESOLVED",
            evaluation_state=result.evaluation_state,
            resolves_event_id=resolves_event_id,
        )
        self._records.append(record)
        return record

    def read_events(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps([asdict(record) for record in self._records]))

    def latest_unresolved_event_id(self, *, lineage_id: str) -> Optional[str]:
        for record in reversed(self._records):
            if record.record_type == "VIOLATION" and record.lineage_id == lineage_id and record.resolution_state == "UNRESOLVED":
                if not any(later.record_type == "RESOLUTION" and later.resolves_event_id == record.record_id for later in self._records):
                    return record.record_id
        return None


class Mediator:
    execution_authority = False
    final_decision_authority = False

    def propose(self, **kwargs: Any) -> Proposal:
        raw = Proposal(**kwargs)
        return Proposal(
            proposal_id=raw.proposal_id,
            request_record_id=raw.request_record_id.strip().upper(),
            transaction_id=raw.transaction_id.strip().upper(),
            lineage_id=raw.lineage_id.strip().upper(),
            method=norm_method(raw.method),
            purpose=norm_purpose(raw.purpose),
            outcome=norm_outcome(raw.outcome),
            authority=raw.authority.strip().upper(),
            changed_fields=tuple(raw.changed_fields),
        )


class RevisionComparator:
    @staticmethod
    def validate_outcome(outcome: Optional[dict[str, Any]]) -> tuple[bool, str]:
        if outcome is None:
            return True, "NO_VIOLATION"
        if outcome["result_class"] not in RESULT_CLASSES:
            return False, "UNKNOWN_RESULT_CLASS"
        if outcome["protected_invariant"] not in PROTECTED_INVARIANTS:
            return False, "UNKNOWN_PROTECTED_INVARIANT"
        if outcome["effect"] not in EFFECTS:
            return False, "UNKNOWN_EFFECT"
        scope = outcome["target_scope"]
        if scope["scope_type"] not in SCOPE_TYPES or not scope["scope_id"]:
            return False, "UNKNOWN_TARGET_SCOPE"
        return True, "VALID"

    @staticmethod
    def compare(before: Optional[Proposal], after: Proposal, revision_scope: Optional[set[str]] = None) -> str:
        if revision_scope is not None and not set(after.changed_fields).issubset(revision_scope):
            return SCOPE_VIOLATION
        valid, _ = RevisionComparator.validate_outcome(after.outcome)
        if not valid:
            return UNKNOWN
        if before is None:
            return NONE if after.outcome is None else FIRST
        if before.lineage_id != after.lineage_id:
            return NEW_CONTEXT
        if before.outcome is not None and after.outcome is None:
            return NORMAL_REVISION
        if before.outcome is None and after.outcome is None:
            return NONE
        before_method = norm_method(before.method)
        after_method = norm_method(after.method)
        before_purpose = norm_purpose(before.purpose)
        after_purpose = norm_purpose(after.purpose)
        before_outcome = norm_outcome(before.outcome)
        after_outcome = norm_outcome(after.outcome)
        if before_method == after_method and before_purpose == after_purpose and before_outcome == after_outcome:
            return EXACT
        if before_purpose == after_purpose and before_outcome == after_outcome:
            return RECURRENCE_CANDIDATE
        if before_outcome and after_outcome and before_outcome["protected_invariant"] == after_outcome["protected_invariant"]:
            return SIMILAR
        return DIFFERENT


class MediationGate:
    execution_authority = False
    final_decision_authority = False

    @staticmethod
    def _evaluation_state(previous: Optional[Proposal]) -> str:
        return REVALIDATING if previous is not None else ACTIVE

    def evaluate(self, current: Proposal, previous: Optional[Proposal] = None, revision_scope: Optional[set[str]] = None, immediate_code: Optional[str] = None, history: Optional[ViolationHistory] = None) -> GateResult:
        evaluation_state = self._evaluation_state(previous)
        if immediate_code in IMMEDIATE_BLOCK:
            result = GateResult(BLOCK, BLOCKED, immediate_code, NONE, evaluation_state, False, True, False)
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result
        if current.authority != "ADVISORY_ONLY":
            result = GateResult(BLOCK, BLOCKED, "MEDIATOR_AUTHORITY_VIOLATION", NONE, evaluation_state, False, True, False)
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result
        valid, why = RevisionComparator.validate_outcome(current.outcome)
        if not valid:
            result = GateResult(PAUSE, PAUSED, why, UNKNOWN, evaluation_state)
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result
        comparison = RevisionComparator.compare(previous, current, revision_scope)
        if comparison == SCOPE_VIOLATION:
            result = GateResult(PAUSE, PAUSED, "UNAUTHORIZED_REVISION_SCOPE_EXPANSION", comparison, evaluation_state)
        elif comparison == NEW_CONTEXT:
            result = GateResult(PAUSE, PAUSED, "NEW_LINEAGE_REQUIRES_FRESH_VALIDATION", comparison, evaluation_state)
        elif comparison == EXACT:
            result = GateResult(BLOCK, BLOCKED, "EXACT_RECURRENCE_DETECTED", comparison, evaluation_state, False, True, False)
        elif comparison == RECURRENCE_CANDIDATE:
            reason = "SAME_LINEAGE_SAME_PURPOSE_SAME_OUTCOME" if previous is not None and previous.transaction_id != current.transaction_id else "METHOD_CHANGED_SAME_PURPOSE_SAME_OUTCOME"
            result = GateResult(PAUSE, PAUSED, reason, comparison, evaluation_state)
        elif comparison == SIMILAR:
            result = GateResult(PAUSE, PAUSED, "SIMILAR_OUTCOME_DETECTED", comparison, evaluation_state)
        elif comparison == DIFFERENT:
            result = GateResult(PAUSE, PAUSED, "DIFFERENT_VIOLATION_DETECTED", comparison, evaluation_state)
        elif comparison == NORMAL_REVISION:
            result = GateResult(ALLOW, ACTIVE, "REVISION_VALIDATED", comparison, evaluation_state, False)
        elif comparison == FIRST:
            result_class = (current.outcome or {}).get("result_class")
            reason = {
                "BINDING_MISMATCH": "FIRST_BINDING_MISMATCH",
                "EVIDENCE_INVALID": "FIRST_EVIDENCE_INVALID",
                "PURPOSE_OR_ROLE_DRIFT": "FIRST_SEMANTIC_CONTINUITY_BREAK",
                "AUTHORITY_SCOPE_EXCEEDED": "FIRST_AUTHORITY_SCOPE_CONCERN",
            }.get(result_class, "FIRST_SOFT_VIOLATION")
            result = GateResult(PAUSE, PAUSED, reason, comparison, evaluation_state)
        else:
            result = GateResult(ALLOW, DISPATCH_READY, "MEDIATION_GATE_VALID", NONE, evaluation_state, False)
        if history is not None:
            if result.decision in {PAUSE, BLOCK}:
                history.append_event(proposal=current, result=result)
            elif result.decision == ALLOW and comparison == NORMAL_REVISION:
                unresolved_id = history.latest_unresolved_event_id(lineage_id=current.lineage_id)
                if unresolved_id is not None:
                    history.append_resolution(resolves_event_id=unresolved_id, proposal=current, result=result)
        return result


class HumanDecision:
    final_decision_authority = True

    @staticmethod
    def decide(value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in USER_DECISIONS:
            raise ValueError(f"INVALID_USER_DECISION:{normalized}")
        return normalized


class Orchestrator:
    decision_authority = False

    def dispatch(self, gate: GateResult, user_decision: str) -> GateResult:
        decision = HumanDecision.decide(user_decision)
        if gate.decision == ALLOW and gate.next_state == DISPATCH_READY and decision == USER_APPROVE:
            return GateResult(ALLOW, DISPATCHED, "SIMULATED_DISPATCH_ALLOWED", gate.comparison, gate.evaluation_state, True, True, False)
        if decision == USER_STOP:
            return GateResult(STOPPED, STOPPED_BY_USER, "USER_STOPPED", gate.comparison, gate.evaluation_state, False, True, False)
        return GateResult(PAUSE, PAUSED, "SIMULATED_DISPATCH_DENIED", gate.comparison, gate.evaluation_state, False, False, True)


def method(mechanism: str, reason: str = "", scope: str = "mediator_proposal_binding") -> dict[str, str]:
    return {"reason_code": reason, "violation_scope": scope, "mechanism": mechanism}


def purpose(task: str = "PROCESS_REQUEST", authority: str = "OBTAIN_EXPLICIT_USER_APPROVAL", execution: str = "DISPATCH_ONLY_AFTER_APPROVAL") -> dict[str, str]:
    return {"task_purpose": task, "authority_purpose": authority, "execution_intent": execution}


def outcome(invariant: str, result_class: str, effect: str, scope_id: str = "TX-001", scope_type: str = "TRANSACTION") -> dict[str, Any]:
    return {"protected_invariant": invariant, "result_class": result_class, "target_scope": {"scope_type": scope_type, "scope_id": scope_id}, "effect": effect}


def proposal(mediator: Mediator, pid: str, req: str = "REQ-001", tx: str = "TX-001", lin: str = "LIN-001", m: Optional[dict[str, Any]] = None, pu: Optional[dict[str, Any]] = None, o: Optional[dict[str, Any]] = None, authority: str = "ADVISORY_ONLY", changed: tuple[str, ...] = ()) -> Proposal:
    return mediator.propose(proposal_id=pid, request_record_id=req, transaction_id=tx, lineage_id=lin, method=m or method("ADVISORY_PROPOSAL", scope="none"), purpose=pu or purpose(), outcome=o, authority=authority, changed_fields=tuple(changed))


def run_suite(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    mediator = Mediator()
    gate = MediationGate()
    orchestrator = Orchestrator()
    audit = AuditLog()
    results: list[dict[str, Any]] = []
    history_snapshots: dict[str, list[dict[str, Any]]] = {}

    def record(test_id: str, actual: GateResult, expected: dict[str, Any], detail: str = "", extra_ok: bool = True) -> None:
        actual_dict = asdict(actual)
        passed = all(actual_dict.get(key) == value for key, value in expected.items()) and extra_ok
        results.append({"test_id": test_id, "expected": expected, "actual": actual_dict, "passed": passed, "detail": detail})
        audit.append({"test_id": test_id, "passed": passed, "decision": actual.decision, "reason_code": actual.reason_code, "comparison": actual.comparison, "evaluation_state": actual.evaluation_state})

    normal = proposal(mediator, "N1")
    gate_result = gate.evaluate(normal)
    final = orchestrator.dispatch(gate_result, HumanDecision.decide(USER_APPROVE))
    record("TEST-P1-NORMAL-001", final, {"decision": ALLOW, "next_state": DISPATCHED, "reason_code": "SIMULATED_DISPATCH_ALLOWED", "dispatch_allowed": True})

    history = ViolationHistory()
    bad = proposal(mediator, "P2", m=method("WRONG_REQUEST_REFERENCE", "REQUEST_DECISION_BINDING_MISMATCH"), o=outcome("TRANSACTION_BINDING", "BINDING_MISMATCH", "REQUEST_DECISION_MISBOUND"))
    pause_result = gate.evaluate(bad, history=history)
    first_history = history.read_events()
    first_record = first_history[0]
    fingerprint_ok = first_record["method_fingerprint"] == method_fingerprint(bad.method) and first_record["outcome_fingerprint"] == outcome_fingerprint(bad.outcome)
    record("TEST-P1-PAUSE-001", pause_result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "FIRST_BINDING_MISMATCH", "comparison": FIRST, "evaluation_state": ACTIVE, "dispatch_allowed": False}, extra_ok=fingerprint_ok)

    before_snapshot = history.read_events()
    fixed = proposal(mediator, "P3", m=method("CORRECT_REQUEST_REFERENCE"), o=None, changed=("mediator_proposal.authority_path",))
    revised = gate.evaluate(fixed, bad, {"mediator_proposal.authority_path"}, history=history)
    after_snapshot = history.read_events()
    append_only_ok = before_snapshot[0] == after_snapshot[0] and len(after_snapshot) == 2 and after_snapshot[1]["record_type"] == "RESOLUTION" and after_snapshot[1]["resolves_event_id"] == after_snapshot[0]["record_id"] and after_snapshot[1]["resolution_state"] == "RESOLVED"
    history_snapshots["TEST-P1-REVISION-001"] = list(after_snapshot)
    record("TEST-P1-REVISION-001", revised, {"decision": ALLOW, "next_state": ACTIVE, "reason_code": "REVISION_VALIDATED", "comparison": NORMAL_REVISION, "evaluation_state": REVALIDATING, "dispatch_allowed": False}, extra_ok=append_only_ok)

    common_outcome = outcome("USER_DECIDES", "UNAUTHORIZED_DECISION_SUBSTITUTION", "USER_APPROVAL_BYPASSED")
    common_purpose = purpose(authority="BYPASS_USER_DECISION", execution="DISPATCH_WITHOUT_VALID_APPROVAL")

    before = proposal(mediator, "R4B", m=method("WRONG_REQUEST_REFERENCE", "REQUEST_DECISION_BINDING_MISMATCH"), pu=common_purpose, o=common_outcome)
    after = proposal(mediator, "R4A", m=method("WRONG_REQUEST_REFERENCE", "REQUEST_DECISION_BINDING_MISMATCH"), pu=common_purpose, o=common_outcome)
    result = gate.evaluate(after, before)
    record("TEST-P1-REPEAT-001", result, {"decision": BLOCK, "next_state": BLOCKED, "reason_code": "EXACT_RECURRENCE_DETECTED", "comparison": EXACT, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "R5B", m=method("DIRECT_USER_APPROVAL_INJECTION"), pu=common_purpose, o=common_outcome)
    after = proposal(mediator, "R5A", m=method("FALSE_ALREADY_APPROVED_FLAG"), pu=common_purpose, o=common_outcome)
    result = gate.evaluate(after, before)
    record("TEST-P1-REPEAT-002", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "METHOD_CHANGED_SAME_PURPOSE_SAME_OUTCOME", "comparison": RECURRENCE_CANDIDATE, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "S6B", m=method("AUTH_A"), pu=common_purpose, o=outcome("AUTHORITY_BOUNDARY", "AUTHORITY_SCOPE_EXCEEDED", "ROLE_BOUNDARY_EXCEEDED"))
    after = proposal(mediator, "S6A", m=method("AUTH_B"), pu=purpose(authority="MODIFY_WITHIN_USER_REVISION"), o=outcome("AUTHORITY_BOUNDARY", "UNAUTHORIZED_DECISION_SUBSTITUTION", "USER_APPROVAL_BYPASSED"))
    result = gate.evaluate(after, before)
    record("TEST-P1-SIMILAR-001", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "SIMILAR_OUTCOME_DETECTED", "comparison": SIMILAR, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "D7B", o=outcome("EVIDENCE_INTEGRITY", "EVIDENCE_INVALID", "EVIDENCE_MISSING"))
    after = proposal(mediator, "D7A", o=outcome("SEMANTIC_CONTINUITY", "PURPOSE_OR_ROLE_DRIFT", "ORIGINAL_PURPOSE_CHANGED"))
    result = gate.evaluate(after, before)
    record("TEST-P1-DIFFERENT-001", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "DIFFERENT_VIOLATION_DETECTED", "comparison": DIFFERENT, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "SC8B", o=outcome("TRANSACTION_BINDING", "BINDING_MISMATCH", "REQUEST_DECISION_MISBOUND"))
    after = proposal(mediator, "SC8A", o=None, changed=("mediator_proposal.authority_path", "mediator_proposal.task_purpose", "mediator_proposal.output"))
    result = gate.evaluate(after, before, {"mediator_proposal.authority_path"})
    record("TEST-P1-REVISION-002", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "UNAUTHORIZED_REVISION_SCOPE_EXPANSION", "comparison": SCOPE_VIOLATION, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "L9B", tx="TX-001", lin="LIN-001", m=method("METHOD_A"), pu=common_purpose, o=common_outcome)
    after = proposal(mediator, "L9A", tx="TX-002", lin="LIN-001", m=method("METHOD_B"), pu=common_purpose, o=common_outcome)
    result = gate.evaluate(after, before)
    record("TEST-P1-LINEAGE-001", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "SAME_LINEAGE_SAME_PURPOSE_SAME_OUTCOME", "comparison": RECURRENCE_CANDIDATE, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    before = proposal(mediator, "L10B", lin="LIN-001", o=outcome("EVIDENCE_INTEGRITY", "EVIDENCE_INVALID", "EVIDENCE_MISSING"))
    after = proposal(mediator, "L10A", lin="LIN-002", o=None)
    result = gate.evaluate(after, before)
    record("TEST-P1-LINEAGE-002", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "NEW_LINEAGE_REQUIRES_FRESH_VALIDATION", "comparison": NEW_CONTEXT, "evaluation_state": REVALIDATING, "dispatch_allowed": False})

    for index, code in enumerate(["FORGED_USER_DECISION", "MEDIATOR_COMMIT_ATTEMPT", "GATE_BYPASS_ATTEMPT", "AUDIT_RECORD_TAMPER", "UNAPPROVED_EXTERNAL_EXECUTION"], start=1):
        history = ViolationHistory()
        current = proposal(mediator, f"B{index}")
        result = gate.evaluate(current, immediate_code=code, history=history)
        history_recorded = len(history.read_events()) == 1 and history.read_events()[0]["resolution_state"] == "BLOCKED"
        record(f"TEST-P1-BLOCK-{index:03d}", result, {"decision": BLOCK, "next_state": BLOCKED, "reason_code": code, "dispatch_allowed": False, "final": True, "retry_allowed": False}, extra_ok=history_recorded)

    unknown = proposal(mediator, "U16", o=outcome("UNREGISTERED_INVARIANT", "UNREGISTERED_RESULT", "STATE_UNRESOLVED"))
    result = gate.evaluate(unknown)
    record("TEST-P1-UNKNOWN-001", result, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "UNKNOWN_RESULT_CLASS", "comparison": UNKNOWN, "dispatch_allowed": False}, detail="Unknown values pause; they are not auto-classified or auto-blocked.")

    clean = proposal(mediator, "DB17")
    gate_result = gate.evaluate(clean)
    denied = orchestrator.dispatch(gate_result, HumanDecision.decide(USER_REJECT))
    record("TEST-P1-DISPATCH-BOUNDARY-001", denied, {"decision": PAUSE, "next_state": PAUSED, "reason_code": "SIMULATED_DISPATCH_DENIED", "dispatch_allowed": False})

    invalid_human_decision_rejected = False
    try:
        HumanDecision.decide("YES")
    except ValueError:
        invalid_human_decision_rejected = True

    history_api_append_only = hasattr(ViolationHistory, "append_event") and hasattr(ViolationHistory, "append_resolution") and hasattr(ViolationHistory, "read_events") and not hasattr(ViolationHistory, "update_event") and not hasattr(ViolationHistory, "delete_event") and not hasattr(ViolationHistory, "clear_history")
    revision_history = history_snapshots["TEST-P1-REVISION-001"]
    fingerprints_persisted = len(revision_history) == 2 and bool(revision_history[0]["method_fingerprint"]) and bool(revision_history[0]["outcome_fingerprint"]) and bool(revision_history[1]["method_fingerprint"]) and revision_history[1]["outcome_fingerprint"] is None
    revalidating_explicit = revision_history[1]["evaluation_state"] == REVALIDATING

    meta = {
        "auto_fix_disabled": AUTO_FIX_ALLOWED is False,
        "auto_apply_revision_disabled": AUTO_APPLY_REVISION is False,
        "auto_commit_disabled": AUTO_COMMIT is False,
        "auto_push_disabled": AUTO_PUSH is False,
        "auto_merge_disabled": AUTO_MERGE is False,
        "network_disabled": NETWORK_ACCESS_ALLOWED is False,
        "external_execution_disabled": EXTERNAL_EXECUTION_ALLOWED is False,
        "mediator_execution_authority_false": Mediator.execution_authority is False,
        "mediator_final_decision_authority_false": Mediator.final_decision_authority is False,
        "gate_execution_authority_false": MediationGate.execution_authority is False,
        "gate_final_decision_authority_false": MediationGate.final_decision_authority is False,
        "orchestrator_decision_authority_false": Orchestrator.decision_authority is False,
        "user_final_decision_authority_true": HumanDecision.final_decision_authority is True,
        "human_decision_enum_enforced": invalid_human_decision_rejected,
        "violation_history_append_only_api": history_api_append_only,
        "fingerprints_persisted": fingerprints_persisted,
        "revalidating_state_explicit": revalidating_explicit,
        "audit_chain_valid": audit.verify(),
    }

    tamper_probe = AuditLog()
    tamper_probe.append({"probe": "original"})
    tamper_probe.tamper_for_test()
    meta["audit_tamper_detected"] = tamper_probe.verify() is False

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    contract_complete = all(meta.values())
    summary = {
        "simulator": "mediator_agent_r39_gate_phase1_sim_v0_2",
        "draft_contract": "DRAFT_v1.4_v1.5_reviewed",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "contract_completeness_passed": contract_complete,
        "decision": "ALLOW" if failed == 0 and contract_complete else "BLOCK",
        "safety_flags": {
            "AUTO_FIX_ALLOWED": AUTO_FIX_ALLOWED,
            "AUTO_APPLY_REVISION": AUTO_APPLY_REVISION,
            "AUTO_COMMIT": AUTO_COMMIT,
            "AUTO_PUSH": AUTO_PUSH,
            "AUTO_MERGE": AUTO_MERGE,
            "NETWORK_ACCESS_ALLOWED": NETWORK_ACCESS_ALLOWED,
            "EXTERNAL_EXECUTION_ALLOWED": EXTERNAL_EXECUTION_ALLOWED,
        },
        "contract_checks": meta,
        "results": results,
        "history_snapshots": history_snapshots,
    }

    (outdir / "phase1_validation_results_v0_2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (outdir / "phase1_audit_log_v0_2.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in audit.rows()) + "\n", encoding="utf-8")
    (outdir / "phase1_violation_history_v0_2.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in revision_history) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    summary = run_suite(Path("."))
    print(json.dumps({"total": summary["total"], "passed": summary["passed"], "failed": summary["failed"], "contract_completeness_passed": summary["contract_completeness_passed"], "decision": summary["decision"]}, ensure_ascii=False, indent=2))
    return 0 if summary["decision"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
