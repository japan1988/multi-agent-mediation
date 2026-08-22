#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1B controlled experiment: Same-Logic Agent-only.

This arm keeps the A v0.2 codebook, models, comparator, history, fixtures,
expected outcomes, and USER/HITL boundary fixed. The only intended variable is
placement of the mediation decision logic: A uses MediationGate; B uses the
non-executing SameLogicMediationAgent below.

The imported A module is used for shared constants/types/fixture harness only.
Before the frozen suite runs, its MediationGate constructor is rebound to this
Agent implementation, so the original Gate implementation is not instantiated.

No auto-fix, auto-apply, commit, push, merge, network, or external execution.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
BASELINE_PATH = HERE / "mediator_agent_r39_gate_phase1_sim_v0_2.py"

spec = importlib.util.spec_from_file_location("phase1a_baseline", BASELINE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("A_BASELINE_IMPORT_FAILED")
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)


class SameLogicMediationAgent:
    """B-arm decision placement. Advisory/non-executing; USER remains final."""

    execution_authority = False
    final_decision_authority = False

    @staticmethod
    def _evaluation_state(previous: Optional[a.Proposal]) -> str:
        return a.REVALIDATING if previous is not None else a.ACTIVE

    def evaluate(
        self,
        current: a.Proposal,
        previous: Optional[a.Proposal] = None,
        revision_scope: Optional[set[str]] = None,
        immediate_code: Optional[str] = None,
        history: Optional[a.ViolationHistory] = None,
    ) -> a.GateResult:
        evaluation_state = self._evaluation_state(previous)

        if immediate_code in a.IMMEDIATE_BLOCK:
            result = a.GateResult(
                a.BLOCK, a.BLOCKED, immediate_code, a.NONE,
                evaluation_state, False, True, False,
            )
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result

        if current.authority != "ADVISORY_ONLY":
            result = a.GateResult(
                a.BLOCK, a.BLOCKED, "MEDIATOR_AUTHORITY_VIOLATION", a.NONE,
                evaluation_state, False, True, False,
            )
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result

        valid, why = a.RevisionComparator.validate_outcome(current.outcome)
        if not valid:
            result = a.GateResult(
                a.PAUSE, a.PAUSED, why, a.UNKNOWN, evaluation_state,
            )
            if history is not None:
                history.append_event(proposal=current, result=result)
            return result

        comparison = a.RevisionComparator.compare(previous, current, revision_scope)

        if comparison == a.SCOPE_VIOLATION:
            result = a.GateResult(
                a.PAUSE, a.PAUSED, "UNAUTHORIZED_REVISION_SCOPE_EXPANSION",
                comparison, evaluation_state,
            )
        elif comparison == a.NEW_CONTEXT:
            result = a.GateResult(
                a.PAUSE, a.PAUSED, "NEW_LINEAGE_REQUIRES_FRESH_VALIDATION",
                comparison, evaluation_state,
            )
        elif comparison == a.EXACT:
            result = a.GateResult(
                a.BLOCK, a.BLOCKED, "EXACT_RECURRENCE_DETECTED",
                comparison, evaluation_state, False, True, False,
            )
        elif comparison == a.RECURRENCE_CANDIDATE:
            reason = (
                "SAME_LINEAGE_SAME_PURPOSE_SAME_OUTCOME"
                if previous is not None
                and previous.transaction_id != current.transaction_id
                else "METHOD_CHANGED_SAME_PURPOSE_SAME_OUTCOME"
            )
            result = a.GateResult(
                a.PAUSE, a.PAUSED, reason, comparison, evaluation_state,
            )
        elif comparison == a.SIMILAR:
            result = a.GateResult(
                a.PAUSE, a.PAUSED, "SIMILAR_OUTCOME_DETECTED",
                comparison, evaluation_state,
            )
        elif comparison == a.DIFFERENT:
            result = a.GateResult(
                a.PAUSE, a.PAUSED, "DIFFERENT_VIOLATION_DETECTED",
                comparison, evaluation_state,
            )
        elif comparison == a.NORMAL_REVISION:
            result = a.GateResult(
                a.ALLOW, a.ACTIVE, "REVISION_VALIDATED",
                comparison, evaluation_state, False,
            )
        elif comparison == a.FIRST:
            result_class = (current.outcome or {}).get("result_class")
            reason = {
                "BINDING_MISMATCH": "FIRST_BINDING_MISMATCH",
                "EVIDENCE_INVALID": "FIRST_EVIDENCE_INVALID",
                "PURPOSE_OR_ROLE_DRIFT": "FIRST_SEMANTIC_CONTINUITY_BREAK",
                "AUTHORITY_SCOPE_EXCEEDED": "FIRST_AUTHORITY_SCOPE_CONCERN",
            }.get(result_class, "FIRST_SOFT_VIOLATION")
            result = a.GateResult(
                a.PAUSE, a.PAUSED, reason, comparison, evaluation_state,
            )
        else:
            # Frozen wording retained intentionally for A/B comparability.
            result = a.GateResult(
                a.ALLOW, a.DISPATCH_READY, "MEDIATION_GATE_VALID",
                a.NONE, evaluation_state, False,
            )

        if history is not None:
            if result.decision in {a.PAUSE, a.BLOCK}:
                history.append_event(proposal=current, result=result)
            elif result.decision == a.ALLOW and comparison == a.NORMAL_REVISION:
                unresolved_id = history.latest_unresolved_event_id(
                    lineage_id=current.lineage_id
                )
                if unresolved_id is not None:
                    history.append_resolution(
                        resolves_event_id=unresolved_id,
                        proposal=current,
                        result=result,
                    )
        return result


def run_suite(outdir: Path) -> dict:
    # Reuse the exact frozen A fixture harness while replacing only placement.
    original_gate = a.MediationGate
    a.MediationGate = SameLogicMediationAgent
    try:
        summary = a.run_suite(outdir)
    finally:
        a.MediationGate = original_gate

    summary["simulator"] = "same_logic_mediation_agent_phase1_sim_v0_2"
    summary["experiment_arm"] = "B_SAME_LOGIC_AGENT_ONLY"
    summary["placement"] = "AGENT_ONLY"
    summary["frozen_fixture_harness"] = "A_V0_2_17_CASES"
    summary["frozen_reason_codes_preserved"] = True
    summary["original_gate_instantiated"] = False
    summary["agent_execution_authority"] = SameLogicMediationAgent.execution_authority
    summary["agent_final_decision_authority"] = SameLogicMediationAgent.final_decision_authority

    source = BASELINE_PATH.read_bytes()
    import hashlib
    summary["comparison_baseline_source_sha256"] = hashlib.sha256(source).hexdigest()

    output = outdir / "phase1b_validation_results_v0_2.json"
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    summary = run_suite(Path("."))
    print(json.dumps({
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "contract_completeness_passed": summary["contract_completeness_passed"],
        "decision": summary["decision"],
        "placement": summary["placement"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["decision"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
