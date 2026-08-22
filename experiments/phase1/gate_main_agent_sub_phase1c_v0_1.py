#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1C contract simulator: Gate-main + Agent-sub.

Purpose:
- Keep the released A Gate logic as the main validation authority.
- Add a non-executing Agent sub-layer before the Gate to detect upstream gaps
  that A/B do not model directly.
- Verify A/B frozen regressions, shared blind-spot probes, C-specific fixtures,
  and Gate > Agent decision precedence.

This is a deterministic local-only simulator. It does not claim real NLP/semantic
understanding; semantic conditions are represented as explicit fixture metadata.

No automatic correction or external action is permitted.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
A_PATH = HERE / "mediator_agent_r39_gate_phase1_sim_v0_2.py"
B_PATH = HERE / "same_logic_mediation_agent_phase1_sim_v0_2.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"IMPORT_FAILED:{path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


a = _load("phase1a_for_c", A_PATH)
b = _load("phase1b_for_c", B_PATH)

CLEAR = "CLEAR"
CONCERN = "CONCERN"
HITL_REQUIRED = "HITL_REQUIRED"

PASS_THROUGH = "PASS_THROUGH"
AUTO_NORMALIZE = "AUTO_NORMALIZE"
GATE_REVIEW = "GATE_REVIEW"

SEMANTIC_AMBIGUITY = "SEMANTIC_AMBIGUITY"
MISSING_REQUIRED_INFORMATION = "MISSING_REQUIRED_INFORMATION"
PROVENANCE_MISSING = "PROVENANCE_MISSING"
BINDING_UNRESOLVED = "BINDING_UNRESOLVED"
PURPOSE_OR_INTENT_UNRESOLVED = "PURPOSE_OR_INTENT_UNRESOLVED"
UNDECLARED_SEMANTIC_CHANGE = "UNDECLARED_SEMANTIC_CHANGE"
SEVERE_EVENT_CANDIDATE = "SEVERE_EVENT_CANDIDATE"
REPAIR_LOOP_LIMIT_REACHED = "REPAIR_LOOP_LIMIT_REACHED"

NORMALIZATION_VALIDATED = "NORMALIZATION_VALIDATED"
USER_REPAIR_VALIDATED = "USER_REPAIR_VALIDATED"
UNDECLARED_AGENT_TRANSFORMATION = "UNDECLARED_AGENT_TRANSFORMATION"
AGENT_PROVENANCE_INVALID = "AGENT_PROVENANCE_INVALID"
GATE_REJECTED_AGENT_COMPLETION = "GATE_REJECTED_AGENT_COMPLETION"
AGENT_CONCERN_GATE_ALLOW = "AGENT_CONCERN_GATE_ALLOW"

MAX_REPAIR_ROUNDS = 3

AUTO_FIX_ALLOWED = False
AUTO_APPLY_REVISION = False
AUTO_COMMIT = False
AUTO_PUSH = False
AUTO_MERGE = False
NETWORK_ACCESS_ALLOWED = False
EXTERNAL_EXECUTION_ALLOWED = False


@dataclass(frozen=True)
class RawInput:
    proposal_id: str = "C-REQ"
    request_record_id: str = "REQ-001"
    transaction_id: str = "TX-001"
    lineage_id: str = "LIN-001"
    method: dict[str, Any] = field(
        default_factory=lambda: a.method("ADVISORY_PROPOSAL", scope="none")
    )
    purpose: dict[str, Any] = field(default_factory=a.purpose)
    outcome: Optional[dict[str, Any]] = None
    authority: str = "ADVISORY_ONLY"

    semantic_candidates: tuple[str, ...] = ()
    required_information_complete: bool = True
    provenance_ok: bool = True
    binding_resolved: bool = True
    purpose_intent_resolved: bool = True
    risk_assessment_complete: bool = True

    declared_changed_fields: tuple[str, ...] = ()
    actual_changed_fields: tuple[str, ...] = ()
    agent_unlogged_transformation: bool = False
    agent_inferred_user_decision: Optional[str] = None
    invalid_agent_provenance: bool = False
    agent_purpose_drift: bool = False

    severe_candidate_code: Optional[str] = None
    severe_evidence_verified: bool = False
    soft_concern: bool = False

    repair_round: int = 0
    user_repaired: bool = False


@dataclass(frozen=True)
class GapReport:
    gap_type: str
    affected_field: str
    reason: str
    evidence_ref: str
    confidence: float
    proposed_action: str
    user_action_required: bool


@dataclass(frozen=True)
class AgentAssessment:
    status: str
    action: str
    reason_code: str
    gap_report: Optional[GapReport]
    normalization_log: tuple[dict[str, str], ...] = ()


class GapCompletionAgent:
    """SUB layer: detect/describe gaps. No final decision or execution authority."""

    execution_authority = False
    final_decision_authority = False
    gate_override_authority = False

    @staticmethod
    def _gap(
        gap_type: str,
        affected_field: str,
        reason: str,
        action: str,
        *,
        evidence_ref: str = "ORIGINAL_INPUT",
        confidence: float = 1.0,
        user_action_required: bool = True,
    ) -> AgentAssessment:
        return AgentAssessment(
            status=HITL_REQUIRED if action == HITL_REQUIRED else CONCERN,
            action=action,
            reason_code=gap_type,
            gap_report=GapReport(
                gap_type=gap_type,
                affected_field=affected_field,
                reason=reason,
                evidence_ref=evidence_ref,
                confidence=confidence,
                proposed_action=action,
                user_action_required=user_action_required,
            ),
        )

    @staticmethod
    def _normalization_log(raw: RawInput) -> tuple[dict[str, str], ...]:
        normalized = a.Mediator().propose(
            proposal_id=raw.proposal_id,
            request_record_id=raw.request_record_id,
            transaction_id=raw.transaction_id,
            lineage_id=raw.lineage_id,
            method=raw.method,
            purpose=raw.purpose,
            outcome=raw.outcome,
            authority=raw.authority,
            changed_fields=raw.declared_changed_fields,
        )
        rows: list[dict[str, str]] = []
        identity_pairs = (
            ("request_record_id", raw.request_record_id, normalized.request_record_id),
            ("transaction_id", raw.transaction_id, normalized.transaction_id),
            ("lineage_id", raw.lineage_id, normalized.lineage_id),
            ("authority", raw.authority, normalized.authority),
        )
        for field_name, before, after in identity_pairs:
            if before != after:
                rows.append(
                    {
                        "field": field_name,
                        "before": str(before),
                        "after": str(after),
                        "normalization_type": "FORMAT_ONLY",
                    }
                )
        for key, before in raw.purpose.items():
            after = normalized.purpose.get(key, "")
            if str(before) != str(after):
                rows.append(
                    {
                        "field": f"purpose.{key}",
                        "before": str(before),
                        "after": str(after),
                        "normalization_type": "CANONICAL_VOCABULARY",
                    }
                )
        return tuple(rows)

    def assess(self, raw: RawInput) -> AgentAssessment:
        # Concerns are surfaced, not decided by the Agent.
        if raw.agent_inferred_user_decision is not None:
            return self._gap(
                SEVERE_EVENT_CANDIDATE,
                "USER_DECISION",
                "Agent-originated USER decision candidate requires Gate validation.",
                GATE_REVIEW,
                user_action_required=False,
            )
        if raw.severe_candidate_code is not None:
            return self._gap(
                SEVERE_EVENT_CANDIDATE,
                "severe_event",
                "Potential severe event requires independent Gate validation.",
                GATE_REVIEW,
                evidence_ref=raw.severe_candidate_code,
                user_action_required=False,
            )
        if raw.invalid_agent_provenance:
            return self._gap(
                PROVENANCE_MISSING,
                "evidence_ref",
                "Agent-supplied provenance cannot be verified.",
                GATE_REVIEW,
                user_action_required=False,
            )
        if raw.agent_purpose_drift:
            return self._gap(
                UNDECLARED_SEMANTIC_CHANGE,
                "purpose",
                "Agent completion appears to change purpose.",
                GATE_REVIEW,
                user_action_required=False,
            )
        if raw.agent_unlogged_transformation:
            return self._gap(
                UNDECLARED_SEMANTIC_CHANGE,
                "canonical_candidate",
                "Agent transformed data without a normalization log.",
                GATE_REVIEW,
                user_action_required=False,
            )
        if set(raw.actual_changed_fields) - set(raw.declared_changed_fields):
            return self._gap(
                UNDECLARED_SEMANTIC_CHANGE,
                "changed_fields",
                "Observed semantic changes exceed declared changes.",
                GATE_REVIEW,
                user_action_required=False,
            )
        if raw.soft_concern:
            return self._gap(
                "AGENT_SOFT_CONCERN",
                "semantic_context",
                "Agent detected a concern not represented by the base Gate schema.",
                GATE_REVIEW,
                user_action_required=False,
            )

        # Unknown/ambiguous/missing meaning is routed to HITL.
        if len(raw.semantic_candidates) > 1:
            if raw.repair_round > MAX_REPAIR_ROUNDS:
                return self._gap(
                    REPAIR_LOOP_LIMIT_REACHED,
                    "semantic_candidates",
                    "Repair limit reached while ambiguity remains.",
                    HITL_REQUIRED,
                )
            return self._gap(
                SEMANTIC_AMBIGUITY,
                "semantic_candidates",
                "More than one plausible semantic target remains.",
                HITL_REQUIRED,
            )
        if not raw.required_information_complete or not raw.risk_assessment_complete:
            return self._gap(
                MISSING_REQUIRED_INFORMATION,
                "required_information",
                "Gate validation inputs are incomplete.",
                HITL_REQUIRED,
            )
        if not raw.provenance_ok:
            return self._gap(
                PROVENANCE_MISSING,
                "provenance",
                "Required provenance is missing.",
                HITL_REQUIRED,
            )
        if not raw.binding_resolved:
            return self._gap(
                BINDING_UNRESOLVED,
                "identity_binding",
                "Request/transaction/lineage binding is unresolved.",
                HITL_REQUIRED,
            )
        if not raw.purpose_intent_resolved:
            return self._gap(
                PURPOSE_OR_INTENT_UNRESOLVED,
                "purpose",
                "Purpose or execution intent is unresolved.",
                HITL_REQUIRED,
            )

        log = self._normalization_log(raw)
        if log:
            return AgentAssessment(
                status=CLEAR,
                action=AUTO_NORMALIZE,
                reason_code=NORMALIZATION_VALIDATED,
                gap_report=None,
                normalization_log=log,
            )
        return AgentAssessment(
            status=CLEAR,
            action=PASS_THROUGH,
            reason_code="AGENT_CLEAR",
            gap_report=None,
            normalization_log=(),
        )


class MainMediationGate:
    """MAIN layer: all externally visible ALLOW/PAUSE/BLOCK decisions originate here."""

    execution_authority = False
    final_decision_authority = False

    def __init__(self) -> None:
        self._base = a.MediationGate()
        self._mediator = a.Mediator()

    @staticmethod
    def _result(
        decision: str,
        next_state: str,
        reason_code: str,
        *,
        comparison: str = a.NONE,
        evaluation_state: str = a.ACTIVE,
        final: bool = False,
        retry_allowed: bool = True,
    ):
        return a.GateResult(
            decision,
            next_state,
            reason_code,
            comparison,
            evaluation_state,
            False,
            final,
            retry_allowed,
        )

    def _proposal(self, raw: RawInput):
        return self._mediator.propose(
            proposal_id=raw.proposal_id,
            request_record_id=raw.request_record_id,
            transaction_id=raw.transaction_id,
            lineage_id=raw.lineage_id,
            method=raw.method,
            purpose=raw.purpose,
            outcome=raw.outcome,
            authority=raw.authority,
            changed_fields=raw.declared_changed_fields,
        )

    @staticmethod
    def _verified_hitl_reason(raw: RawInput, assessment: AgentAssessment) -> Optional[str]:
        reason = assessment.reason_code
        if reason == REPAIR_LOOP_LIMIT_REACHED:
            if raw.repair_round > MAX_REPAIR_ROUNDS and len(raw.semantic_candidates) > 1:
                return reason
            return None
        if reason == SEMANTIC_AMBIGUITY and len(raw.semantic_candidates) > 1:
            return reason
        if reason == MISSING_REQUIRED_INFORMATION and (
            not raw.required_information_complete or not raw.risk_assessment_complete
        ):
            return reason
        if reason == PROVENANCE_MISSING and not raw.provenance_ok:
            return reason
        if reason == BINDING_UNRESOLVED and not raw.binding_resolved:
            return reason
        if reason == PURPOSE_OR_INTENT_UNRESOLVED and not raw.purpose_intent_resolved:
            return reason
        return None

    def evaluate(
        self,
        raw: RawInput,
        assessment: AgentAssessment,
        *,
        previous: Optional[Any] = None,
        revision_scope: Optional[set[str]] = None,
    ):
        current = self._proposal(raw)

        # Gate independently verifies hard authority/integrity conditions first.
        if raw.agent_inferred_user_decision is not None:
            return self._base.evaluate(
                current,
                previous,
                revision_scope,
                immediate_code="FORGED_USER_DECISION",
            )

        if (
            raw.severe_candidate_code in a.IMMEDIATE_BLOCK
            and raw.severe_evidence_verified
        ):
            return self._base.evaluate(
                current,
                previous,
                revision_scope,
                immediate_code=raw.severe_candidate_code,
            )

        if raw.invalid_agent_provenance:
            return self._result(
                a.PAUSE,
                a.PAUSED,
                AGENT_PROVENANCE_INVALID,
                evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
            )

        if raw.agent_purpose_drift:
            return self._result(
                a.PAUSE,
                a.PAUSED,
                GATE_REJECTED_AGENT_COMPLETION,
                evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
            )

        if raw.agent_unlogged_transformation:
            return self._result(
                a.PAUSE,
                a.PAUSED,
                UNDECLARED_AGENT_TRANSFORMATION,
                evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
            )

        if set(raw.actual_changed_fields) - set(raw.declared_changed_fields):
            return self._result(
                a.PAUSE,
                a.PAUSED,
                UNDECLARED_SEMANTIC_CHANGE,
                evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
            )

        if assessment.action == HITL_REQUIRED:
            verified = self._verified_hitl_reason(raw, assessment)
            if verified is None:
                return self._result(
                    a.PAUSE,
                    a.PAUSED,
                    "AGENT_COMPLETION_NOT_VERIFIABLE",
                    evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
                )
            return self._result(
                a.PAUSE,
                a.PAUSED,
                verified,
                evaluation_state=a.REVALIDATING if previous is not None else a.ACTIVE,
            )

        # MAIN Gate keeps the released A logic authoritative.
        base_result = self._base.evaluate(
            current,
            previous,
            revision_scope,
        )
        if base_result.decision in {a.BLOCK, a.PAUSE}:
            return base_result

        # Agent concern may only make an ALLOW stricter, never weaker.
        if assessment.status == CONCERN:
            return replace(
                base_result,
                decision=a.PAUSE,
                next_state=a.PAUSED,
                reason_code=AGENT_CONCERN_GATE_ALLOW,
                dispatch_allowed=False,
                final=False,
                retry_allowed=True,
            )

        if raw.user_repaired:
            return replace(base_result, reason_code=USER_REPAIR_VALIDATED)

        if assessment.action == AUTO_NORMALIZE:
            return replace(base_result, reason_code=NORMALIZATION_VALIDATED)

        return base_result


def _run_one(
    test_id: str,
    raw: RawInput,
    *,
    expected_agent_action: str,
    expected_gate_decision: str,
    expected_reason: str,
    previous: Optional[Any] = None,
    revision_scope: Optional[set[str]] = None,
) -> dict[str, Any]:
    agent = GapCompletionAgent()
    gate = MainMediationGate()
    assessment = agent.assess(raw)
    result = gate.evaluate(
        raw,
        assessment,
        previous=previous,
        revision_scope=revision_scope,
    )
    passed = (
        assessment.action == expected_agent_action
        and result.decision == expected_gate_decision
        and result.reason_code == expected_reason
    )
    return {
        "test_id": test_id,
        "expected": {
            "agent_action": expected_agent_action,
            "gate_decision": expected_gate_decision,
            "reason_code": expected_reason,
        },
        "actual": {
            "agent": asdict(assessment),
            "gate": asdict(result),
        },
        "passed": passed,
    }


def run_c_specific_suite() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    cases.append(
        _run_one(
            "C-001-NORMAL-COMPLETE",
            RawInput(),
            expected_agent_action=PASS_THROUGH,
            expected_gate_decision=a.ALLOW,
            expected_reason="MEDIATION_GATE_VALID",
        )
    )
    cases.append(
        _run_one(
            "C-002-NORMALIZE-CASE-FORMAT",
            RawInput(
                proposal_id="C-002",
                request_record_id=" req-001 ",
                transaction_id=" tx-001 ",
                lineage_id=" lin-001 ",
            ),
            expected_agent_action=AUTO_NORMALIZE,
            expected_gate_decision=a.ALLOW,
            expected_reason=NORMALIZATION_VALIDATED,
        )
    )
    cases.append(
        _run_one(
            "C-003-NORMALIZE-EXPLICIT-VALUE",
            RawInput(
                proposal_id="C-003",
                purpose={
                    "task_purpose": " process_request ",
                    "authority_purpose": " obtain_explicit_user_approval ",
                    "execution_intent": " dispatch_only_after_approval ",
                },
            ),
            expected_agent_action=AUTO_NORMALIZE,
            expected_gate_decision=a.ALLOW,
            expected_reason=NORMALIZATION_VALIDATED,
        )
    )
    cases.append(
        _run_one(
            "C-004-SEMANTIC-AMBIGUITY",
            RawInput(proposal_id="C-004", semantic_candidates=("DOC-1", "DOC-2")),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=SEMANTIC_AMBIGUITY,
        )
    )
    cases.append(
        _run_one(
            "C-005-MISSING-REQUIRED-INFORMATION",
            RawInput(proposal_id="C-005", required_information_complete=False),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=MISSING_REQUIRED_INFORMATION,
        )
    )
    cases.append(
        _run_one(
            "C-006-PROVENANCE-MISSING",
            RawInput(proposal_id="C-006", provenance_ok=False),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=PROVENANCE_MISSING,
        )
    )
    cases.append(
        _run_one(
            "C-007-BINDING-UNRESOLVED",
            RawInput(proposal_id="C-007", binding_resolved=False),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=BINDING_UNRESOLVED,
        )
    )
    cases.append(
        _run_one(
            "C-008-PURPOSE-OR-INTENT-UNRESOLVED",
            RawInput(proposal_id="C-008", purpose_intent_resolved=False),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=PURPOSE_OR_INTENT_UNRESOLVED,
        )
    )
    cases.append(
        _run_one(
            "C-009-HITL-REPAIR-SUCCESS",
            RawInput(proposal_id="C-009", user_repaired=True, repair_round=1),
            expected_agent_action=PASS_THROUGH,
            expected_gate_decision=a.ALLOW,
            expected_reason=USER_REPAIR_VALIDATED,
        )
    )
    cases.append(
        _run_one(
            "C-010-HITL-REPAIR-LIMIT",
            RawInput(
                proposal_id="C-010",
                semantic_candidates=("DOC-1", "DOC-2"),
                repair_round=4,
            ),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=REPAIR_LOOP_LIMIT_REACHED,
        )
    )
    cases.append(
        _run_one(
            "C-011-UNDECLARED-AGENT-TRANSFORMATION",
            RawInput(proposal_id="C-011", agent_unlogged_transformation=True),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.PAUSE,
            expected_reason=UNDECLARED_AGENT_TRANSFORMATION,
        )
    )
    cases.append(
        _run_one(
            "C-012-AGENT-INFERRED-USER-APPROVAL",
            RawInput(proposal_id="C-012", agent_inferred_user_decision="APPROVE"),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.BLOCK,
            expected_reason="FORGED_USER_DECISION",
        )
    )
    cases.append(
        _run_one(
            "C-013-INVALID-AGENT-PROVENANCE",
            RawInput(proposal_id="C-013", invalid_agent_provenance=True),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.PAUSE,
            expected_reason=AGENT_PROVENANCE_INVALID,
        )
    )
    cases.append(
        _run_one(
            "C-014-AGENT-PURPOSE-DRIFT",
            RawInput(proposal_id="C-014", agent_purpose_drift=True),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.PAUSE,
            expected_reason=GATE_REJECTED_AGENT_COMPLETION,
        )
    )
    cases.append(
        _run_one(
            "C-015-UNDECLARED-SEMANTIC-CHANGE",
            RawInput(
                proposal_id="C-015",
                actual_changed_fields=("purpose.task_purpose",),
                declared_changed_fields=(),
            ),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.PAUSE,
            expected_reason=UNDECLARED_SEMANTIC_CHANGE,
        )
    )
    cases.append(
        _run_one(
            "C-016-INCOMPLETE-RISK-ASSESSMENT",
            RawInput(proposal_id="C-016", risk_assessment_complete=False),
            expected_agent_action=HITL_REQUIRED,
            expected_gate_decision=a.PAUSE,
            expected_reason=MISSING_REQUIRED_INFORMATION,
        )
    )
    cases.append(
        _run_one(
            "C-017-SEVERE-EVENT-WITHOUT-IMMEDIATE-CODE",
            RawInput(
                proposal_id="C-017",
                severe_candidate_code="GATE_BYPASS_ATTEMPT",
                severe_evidence_verified=True,
            ),
            expected_agent_action=GATE_REVIEW,
            expected_gate_decision=a.BLOCK,
            expected_reason="GATE_BYPASS_ATTEMPT",
        )
    )

    passed = sum(1 for row in cases if row["passed"])
    return {
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "results": cases,
    }


def _arm_gap_probes(base_module: Any, evaluator_factory: Any) -> dict[str, Any]:
    med = base_module.Mediator()
    evaluator = evaluator_factory()

    blank_identity = base_module.proposal(
        med,
        "GAP-1",
        req="",
        tx="",
        lin="",
        o=None,
    )
    r1 = evaluator.evaluate(blank_identity)

    blank_purpose = base_module.proposal(
        med,
        "GAP-2",
        pu=base_module.purpose(task="", authority="", execution=""),
        o=None,
    )
    r2 = evaluator.evaluate(blank_purpose)

    clean_none = base_module.proposal(med, "GAP-3", o=None)
    r3 = evaluator.evaluate(clean_none)

    before = base_module.proposal(
        med,
        "GAP-4B",
        pu=base_module.purpose(task="PROCESS_REQUEST"),
        o=base_module.outcome(
            "TRANSACTION_BINDING",
            "BINDING_MISMATCH",
            "REQUEST_DECISION_MISBOUND",
        ),
    )
    after = base_module.proposal(
        med,
        "GAP-4A",
        pu=base_module.purpose(task="DIFFERENT_PURPOSE"),
        o=None,
        changed=(),
    )
    r4 = evaluator.evaluate(
        after,
        before,
        {"mediator_proposal.authority_path"},
    )

    return {
        "blank_identity_not_rejected": r1.decision == base_module.ALLOW,
        "blank_purpose_not_rejected": r2.decision == base_module.ALLOW,
        "outcome_none_treated_as_non_violation": (
            base_module.RevisionComparator.validate_outcome(None)
            == (True, "NO_VIOLATION")
            and r3.decision == base_module.ALLOW
        ),
        "undeclared_semantic_revision_can_validate": (
            r4.decision == base_module.ALLOW
            and r4.reason_code == "REVISION_VALIDATED"
        ),
        "provenance_not_in_proposal_schema": (
            "provenance" not in getattr(base_module.Proposal, "__dataclass_fields__", {})
        ),
    }


def run_ab_shared_gap_probes() -> dict[str, Any]:
    a_probe = _arm_gap_probes(a, a.MediationGate)
    b_probe = _arm_gap_probes(b.a, b.SameLogicMediationAgent)
    same = a_probe == b_probe
    all_exposed = all(a_probe.values()) and all(b_probe.values())
    return {
        "a": a_probe,
        "b": b_probe,
        "same_logic_gap_behavior": same,
        "all_targeted_shared_gaps_exposed": all_exposed,
        "a_b_are_complementary": False,
        "interpretation": (
            "A and B intentionally share the same decision logic; the probes confirm "
            "shared upstream/schema blind spots rather than complementary coverage."
        ),
    }


def run_precedence_checks() -> dict[str, bool]:
    agent = GapCompletionAgent()
    gate = MainMediationGate()

    # Gate PAUSE over Agent CLEAR.
    pause_raw = RawInput(
        proposal_id="PREC-1",
        outcome=a.outcome(
            "TRANSACTION_BINDING",
            "BINDING_MISMATCH",
            "REQUEST_DECISION_MISBOUND",
        ),
    )
    pause_assessment = agent.assess(pause_raw)
    pause_result = gate.evaluate(pause_raw, pause_assessment)

    # Gate BLOCK over Agent CLEAR (authority boundary).
    block_raw = RawInput(proposal_id="PREC-2", authority="FINAL_AUTHORITY")
    block_assessment = agent.assess(block_raw)
    block_result = gate.evaluate(block_raw, block_assessment)

    # Agent concern can only make Gate ALLOW stricter.
    concern_raw = RawInput(proposal_id="PREC-3", soft_concern=True)
    concern_assessment = agent.assess(concern_raw)
    concern_result = gate.evaluate(concern_raw, concern_assessment)

    return {
        "gate_pause_over_agent_clear": (
            pause_assessment.status == CLEAR and pause_result.decision == a.PAUSE
        ),
        "gate_block_over_agent_clear": (
            block_assessment.status == CLEAR and block_result.decision == a.BLOCK
        ),
        "agent_concern_cannot_force_allow": (
            concern_assessment.status == CONCERN
            and concern_result.decision == a.PAUSE
            and concern_result.reason_code == AGENT_CONCERN_GATE_ALLOW
        ),
    }


def run_full_simulation(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    a_summary = a.run_suite(outdir / "a")
    b_summary = b.run_suite(outdir / "b")
    ab_gaps = run_ab_shared_gap_probes()
    c_specific = run_c_specific_suite()
    precedence = run_precedence_checks()

    safety = {
        "auto_fix_disabled": AUTO_FIX_ALLOWED is False,
        "auto_apply_revision_disabled": AUTO_APPLY_REVISION is False,
        "auto_commit_disabled": AUTO_COMMIT is False,
        "auto_push_disabled": AUTO_PUSH is False,
        "auto_merge_disabled": AUTO_MERGE is False,
        "network_disabled": NETWORK_ACCESS_ALLOWED is False,
        "external_execution_disabled": EXTERNAL_EXECUTION_ALLOWED is False,
        "agent_execution_authority_false": GapCompletionAgent.execution_authority is False,
        "agent_final_decision_authority_false": GapCompletionAgent.final_decision_authority is False,
        "agent_gate_override_authority_false": GapCompletionAgent.gate_override_authority is False,
        "gate_execution_authority_false": MainMediationGate.execution_authority is False,
        "gate_final_decision_authority_false": MainMediationGate.final_decision_authority is False,
    }

    c_complements_gate = (
        a_summary["total"] == 17
        and a_summary["passed"] == 17
        and b_summary["total"] == 17
        and b_summary["passed"] == 17
        and ab_gaps["same_logic_gap_behavior"]
        and ab_gaps["all_targeted_shared_gaps_exposed"]
        and c_specific["total"] == 17
        and c_specific["passed"] == 17
        and all(precedence.values())
        and all(safety.values())
    )

    summary = {
        "simulator": "gate_main_agent_sub_phase1c_v0_1",
        "architecture": {
            "processing_order": ["INPUT", "AGENT_SUB", "GATE_MAIN", "USER_HITL"],
            "decision_priority": ["GATE", "AGENT"],
            "final_decision_authority": "USER",
            "gate_main": True,
            "agent_sub": True,
        },
        "a_regression": {
            "total": a_summary["total"],
            "passed": a_summary["passed"],
            "failed": a_summary["failed"],
            "decision": a_summary["decision"],
        },
        "b_regression": {
            "total": b_summary["total"],
            "passed": b_summary["passed"],
            "failed": b_summary["failed"],
            "decision": b_summary["decision"],
        },
        "ab_gap_analysis": ab_gaps,
        "c_specific": c_specific,
        "precedence_checks": precedence,
        "safety_checks": safety,
        "complementarity": {
            "a_b_complementary": False,
            "c_agent_gate_complementarity_established": c_complements_gate,
            "scope": (
                "Contract-level simulation only. It validates deterministic wiring, "
                "decision precedence, and targeted gap handling; it does not validate "
                "real-world semantic inference quality."
            ),
        },
        "decision": "ALLOW" if c_complements_gate else "BLOCK",
    }
    (outdir / "phase1c_complementarity_results_v0_1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    summary = run_full_simulation(Path("."))
    print(
        json.dumps(
            {
                "a": summary["a_regression"],
                "b": summary["b_regression"],
                "ab_shared_gaps": summary["ab_gap_analysis"],
                "c_specific": {
                    "total": summary["c_specific"]["total"],
                    "passed": summary["c_specific"]["passed"],
                    "failed": summary["c_specific"]["failed"],
                },
                "precedence": summary["precedence_checks"],
                "complementarity": summary["complementarity"],
                "decision": summary["decision"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if summary["decision"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
