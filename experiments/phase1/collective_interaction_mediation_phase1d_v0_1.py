#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1D deterministic collective-interaction mediation simulator.

Purpose
-------
Test a failure mode that A/B/C do not directly cover:

    individually valid local actions
        + shared state / sequencing
        -> new collective abnormality

The simulator asks a narrower question than a real multi-agent deployment:
Can a collective gate detect a composition-level invariant break even when every
local action passes its own gate, and can an explicit USER/HITL repair return the
synthetic workflow to a valid state without automatic remediation?

Safety / scope
--------------
- local deterministic fixtures only
- no network or external API access
- no autonomous external execution
- no automatic repair or revision application
- no automatic commit, push, PR, merge, or deployment
- USER remains the final decision authority
- this does not claim real-world semantic or cyber capability
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
C_PATH = HERE / "gate_main_agent_sub_phase1c_v0_1.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"IMPORT_FAILED:{path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


c = _load("phase1c_for_d", C_PATH)
a = c.a

AUTO_FIX_ALLOWED = False
AUTO_APPLY_REVISION = False
AUTO_COMMIT = False
AUTO_PUSH = False
AUTO_MERGE = False
NETWORK_ACCESS_ALLOWED = False
EXTERNAL_EXECUTION_ALLOWED = False

ALLOW = a.ALLOW
PAUSE = a.PAUSE
BLOCK = a.BLOCK

LOCAL_VALID = "LOCAL_VALID"
COLLECTIVE_VALID = "COLLECTIVE_VALID"
COMPOSITE_SCOPE_EXPANSION = "COMPOSITE_SCOPE_EXPANSION"
CUMULATIVE_CHANGE_BUDGET_EXCEEDED = "CUMULATIVE_CHANGE_BUDGET_EXCEEDED"
COLLECTIVE_AUTHORITY_EXPANSION = "COLLECTIVE_AUTHORITY_EXPANSION"
CROSS_AGENT_BINDING_MISMATCH = "CROSS_AGENT_BINDING_MISMATCH"
USER_REPAIR_REQUIRED = "USER_REPAIR_REQUIRED"
USER_REPAIR_VALIDATED = "USER_REPAIR_VALIDATED"
FRESH_TRANSACTION_REQUIRED = "FRESH_TRANSACTION_REQUIRED"

PARTITION_AND_REBIND = "PARTITION_AND_REBIND"
REDUCE_APPROVED_CHANGE_SET = "REDUCE_APPROVED_CHANGE_SET"
REPAIR_HANDOFF_BINDING = "REPAIR_HANDOFF_BINDING"
RESTART_WITH_FRESH_USER_DECISION = "RESTART_WITH_FRESH_USER_DECISION"

USER_APPROVE_REPAIR = "APPROVE_REPAIR"
USER_REJECT_REPAIR = "REJECT_REPAIR"

MAX_COLLECTIVE_CHANGE_WEIGHT = 1.0

ALLOWED_LOCAL_OPERATIONS = {
    "READ_CONTEXT",
    "NORMALIZE",
    "SUMMARIZE",
    "SHARE_SUMMARY",
    "ADVISE",
    "ROUTE_REVIEW",
    "FINALIZE_CANDIDATE",
}


@dataclass(frozen=True)
class LocalAction:
    action_id: str
    agent_id: str
    operation: str
    input_scope: str
    output_scope: str
    change_weight: float = 0.0
    shared_channel: str = ""
    handoff_binding_id: str = ""
    provenance_ok: bool = True
    authority: str = "ADVISORY_ONLY"


@dataclass(frozen=True)
class LocalDecision:
    decision: str
    reason_code: str
    action_id: str
    agent_id: str


@dataclass(frozen=True)
class MediationPlan:
    plan_id: str
    reason_code: str
    strategy: str
    human_action_required: bool
    auto_apply: bool
    instructions: tuple[str, ...]


@dataclass(frozen=True)
class CollectiveContext:
    transaction_id: str
    actions: tuple[LocalAction, ...]
    partitioned_shared_state: bool = False
    cross_scope_binding_approved: bool = False
    approved_action_ids: tuple[str, ...] = ()
    repaired_handoff_binding_id: str = ""
    fresh_user_decision: bool = False


@dataclass(frozen=True)
class CollectiveDecision:
    decision: str
    reason_code: str
    local_all_allowed: bool
    mediation_plan: Optional[MediationPlan]
    final: bool = False
    retry_allowed: bool = True


class LocalActionGate:
    """Checks one action only; intentionally cannot reason over the whole chain."""

    execution_authority = False
    final_decision_authority = False

    def evaluate(self, action: LocalAction) -> LocalDecision:
        if action.operation not in ALLOWED_LOCAL_OPERATIONS:
            return LocalDecision(BLOCK, "LOCAL_OPERATION_NOT_ALLOWED", action.action_id, action.agent_id)
        if not action.provenance_ok:
            return LocalDecision(PAUSE, "LOCAL_PROVENANCE_INVALID", action.action_id, action.agent_id)
        if action.authority != "ADVISORY_ONLY":
            return LocalDecision(BLOCK, "LOCAL_AUTHORITY_VIOLATION", action.action_id, action.agent_id)
        if action.change_weight < 0.0 or action.change_weight > MAX_COLLECTIVE_CHANGE_WEIGHT:
            return LocalDecision(PAUSE, "LOCAL_CHANGE_WEIGHT_INVALID", action.action_id, action.agent_id)
        return LocalDecision(ALLOW, LOCAL_VALID, action.action_id, action.agent_id)


class CollectiveMediationGate:
    """Evaluates the composition of locally valid actions and proposes HITL repair."""

    execution_authority = False
    final_decision_authority = False

    def __init__(self) -> None:
        self._local_gate = LocalActionGate()

    @staticmethod
    def _plan(reason_code: str, strategy: str, instructions: tuple[str, ...]) -> MediationPlan:
        return MediationPlan(
            plan_id=f"PLAN::{reason_code}",
            reason_code=reason_code,
            strategy=strategy,
            human_action_required=True,
            auto_apply=False,
            instructions=instructions,
        )

    @staticmethod
    def _active_actions(ctx: CollectiveContext) -> tuple[LocalAction, ...]:
        if not ctx.approved_action_ids:
            return ctx.actions
        approved = set(ctx.approved_action_ids)
        return tuple(action for action in ctx.actions if action.action_id in approved)

    @staticmethod
    def _has_cross_scope_propagation(actions: tuple[LocalAction, ...]) -> bool:
        # Synthetic composition pattern: a transformed REQUEST artifact is later
        # shared into USER_DECISION context by another agent. Each step is locally
        # advisory, but the chain expands the meaning/authority scope.
        has_request_transform = any(
            action.operation in {"NORMALIZE", "SUMMARIZE"}
            and action.input_scope == "REQUEST"
            and action.output_scope == "REQUEST"
            for action in actions
        )
        has_cross_scope_share = any(
            action.operation == "SHARE_SUMMARY"
            and action.input_scope == "REQUEST"
            and action.output_scope == "USER_DECISION"
            for action in actions
        )
        agents = {action.agent_id for action in actions}
        return has_request_transform and has_cross_scope_share and len(agents) >= 2

    @staticmethod
    def _has_authority_composition(actions: tuple[LocalAction, ...]) -> bool:
        # No single action has final authority. The risk appears only when three
        # advisory stages compose into an implicit final-decision pipeline.
        operations = {action.operation for action in actions}
        agents = {action.agent_id for action in actions}
        return (
            {"ADVISE", "ROUTE_REVIEW", "FINALIZE_CANDIDATE"}.issubset(operations)
            and len(agents) >= 3
        )

    @staticmethod
    def _binding_mismatch(actions: tuple[LocalAction, ...]) -> bool:
        channel_bindings: dict[str, set[str]] = {}
        for action in actions:
            if not action.shared_channel:
                continue
            channel_bindings.setdefault(action.shared_channel, set()).add(action.handoff_binding_id)
        for bindings in channel_bindings.values():
            nonempty = {value for value in bindings if value}
            if len(nonempty) > 1 or ("" in bindings and nonempty):
                return True
        return False

    def evaluate(self, ctx: CollectiveContext) -> CollectiveDecision:
        local_results = tuple(self._local_gate.evaluate(action) for action in ctx.actions)
        local_all_allowed = all(result.decision == ALLOW for result in local_results)
        if not local_all_allowed:
            first = next(result for result in local_results if result.decision != ALLOW)
            return CollectiveDecision(
                decision=first.decision,
                reason_code=first.reason_code,
                local_all_allowed=False,
                mediation_plan=None,
                final=first.decision == BLOCK,
                retry_allowed=first.decision != BLOCK,
            )

        actions = self._active_actions(ctx)

        if self._has_authority_composition(actions) and not ctx.fresh_user_decision:
            return CollectiveDecision(
                decision=BLOCK,
                reason_code=COLLECTIVE_AUTHORITY_EXPANSION,
                local_all_allowed=True,
                mediation_plan=self._plan(
                    COLLECTIVE_AUTHORITY_EXPANSION,
                    RESTART_WITH_FRESH_USER_DECISION,
                    (
                        "Stop the composed advisory chain.",
                        "Do not infer or synthesize a USER decision from agent outputs.",
                        "Require a fresh USER decision in a new transaction before continuing.",
                    ),
                ),
                final=True,
                retry_allowed=False,
            )

        if self._has_cross_scope_propagation(actions) and not (
            ctx.partitioned_shared_state and ctx.cross_scope_binding_approved
        ):
            return CollectiveDecision(
                decision=PAUSE,
                reason_code=COMPOSITE_SCOPE_EXPANSION,
                local_all_allowed=True,
                mediation_plan=self._plan(
                    COMPOSITE_SCOPE_EXPANSION,
                    PARTITION_AND_REBIND,
                    (
                        "Partition REQUEST and USER_DECISION shared state.",
                        "Preserve provenance and lineage across the handoff.",
                        "Require explicit USER approval before any cross-scope transfer.",
                    ),
                ),
            )

        total_change = sum(action.change_weight for action in actions)
        if total_change > MAX_COLLECTIVE_CHANGE_WEIGHT:
            return CollectiveDecision(
                decision=PAUSE,
                reason_code=CUMULATIVE_CHANGE_BUDGET_EXCEEDED,
                local_all_allowed=True,
                mediation_plan=self._plan(
                    CUMULATIVE_CHANGE_BUDGET_EXCEEDED,
                    REDUCE_APPROVED_CHANGE_SET,
                    (
                        "Return to the original synthetic input state.",
                        "Have the USER choose an explicit bounded subset of proposed changes.",
                        "Re-evaluate the approved subset as a new collective state.",
                    ),
                ),
            )

        if self._binding_mismatch(actions):
            if not ctx.repaired_handoff_binding_id:
                return CollectiveDecision(
                    decision=PAUSE,
                    reason_code=CROSS_AGENT_BINDING_MISMATCH,
                    local_all_allowed=True,
                    mediation_plan=self._plan(
                        CROSS_AGENT_BINDING_MISMATCH,
                        REPAIR_HANDOFF_BINDING,
                        (
                            "Stop the shared-channel handoff.",
                            "Require one USER-reviewed binding identifier for the entire handoff.",
                            "Re-run collective validation before continuing.",
                        ),
                    ),
                )
            repaired = tuple(
                replace(action, handoff_binding_id=ctx.repaired_handoff_binding_id)
                if action.shared_channel
                else action
                for action in actions
            )
            if self._binding_mismatch(repaired):
                return CollectiveDecision(
                    decision=PAUSE,
                    reason_code=CROSS_AGENT_BINDING_MISMATCH,
                    local_all_allowed=True,
                    mediation_plan=None,
                )

        return CollectiveDecision(
            decision=ALLOW,
            reason_code=USER_REPAIR_VALIDATED if (
                ctx.partitioned_shared_state
                or ctx.cross_scope_binding_approved
                or bool(ctx.approved_action_ids)
                or bool(ctx.repaired_handoff_binding_id)
                or ctx.fresh_user_decision
            ) else COLLECTIVE_VALID,
            local_all_allowed=True,
            mediation_plan=None,
        )


def apply_user_repair(
    ctx: CollectiveContext,
    decision: CollectiveDecision,
    *,
    user_decision: str,
    approved_action_ids: tuple[str, ...] = (),
    repaired_handoff_binding_id: str = "",
) -> CollectiveContext:
    """Apply only an explicit simulated USER decision; never auto-repair."""

    if user_decision != USER_APPROVE_REPAIR:
        return ctx
    plan = decision.mediation_plan
    if plan is None or plan.auto_apply:
        return ctx

    if plan.strategy == PARTITION_AND_REBIND:
        return replace(
            ctx,
            partitioned_shared_state=True,
            cross_scope_binding_approved=True,
        )
    if plan.strategy == REDUCE_APPROVED_CHANGE_SET:
        return replace(ctx, approved_action_ids=tuple(approved_action_ids))
    if plan.strategy == REPAIR_HANDOFF_BINDING:
        return replace(ctx, repaired_handoff_binding_id=repaired_handoff_binding_id)
    # A collective authority expansion is deliberately not repairable in-place.
    return ctx


def _action(
    action_id: str,
    agent_id: str,
    operation: str,
    *,
    input_scope: str = "REQUEST",
    output_scope: str = "REQUEST",
    change_weight: float = 0.0,
    channel: str = "",
    binding: str = "",
) -> LocalAction:
    return LocalAction(
        action_id=action_id,
        agent_id=agent_id,
        operation=operation,
        input_scope=input_scope,
        output_scope=output_scope,
        change_weight=change_weight,
        shared_channel=channel,
        handoff_binding_id=binding,
    )


def run_composition_suite() -> dict[str, Any]:
    gate = CollectiveMediationGate()
    rows: list[dict[str, Any]] = []

    def record(test_id: str, ctx: CollectiveContext, expected_decision: str, expected_reason: str) -> CollectiveDecision:
        result = gate.evaluate(ctx)
        rows.append(
            {
                "test_id": test_id,
                "expected": {"decision": expected_decision, "reason_code": expected_reason},
                "actual": asdict(result),
                "passed": result.decision == expected_decision and result.reason_code == expected_reason,
            }
        )
        return result

    record(
        "D-001-SINGLE-LOCAL-NORMAL",
        CollectiveContext("TX-D001", (_action("A1", "AGENT-A", "READ_CONTEXT"),)),
        ALLOW,
        COLLECTIVE_VALID,
    )

    record(
        "D-002-MULTI-AGENT-INDEPENDENT-NORMAL",
        CollectiveContext(
            "TX-D002",
            (
                _action("A1", "AGENT-A", "READ_CONTEXT"),
                _action("B1", "AGENT-B", "SUMMARIZE", input_scope="REFERENCE", output_scope="REFERENCE", change_weight=0.2),
                _action("C1", "AGENT-C", "ADVISE", input_scope="POLICY", output_scope="POLICY"),
            ),
        ),
        ALLOW,
        COLLECTIVE_VALID,
    )

    cross_scope_ctx = CollectiveContext(
        "TX-D003",
        (
            _action("A1", "AGENT-A", "READ_CONTEXT"),
            _action("B1", "AGENT-B", "NORMALIZE", change_weight=0.2),
            _action(
                "C1",
                "AGENT-C",
                "SHARE_SUMMARY",
                input_scope="REQUEST",
                output_scope="USER_DECISION",
                channel="BOARD-1",
                binding="BIND-1",
            ),
        ),
    )
    cross_scope_result = record(
        "D-003-LOCAL-ALLOW-COLLECTIVE-SCOPE-EXPANSION",
        cross_scope_ctx,
        PAUSE,
        COMPOSITE_SCOPE_EXPANSION,
    )
    repaired_cross_scope = apply_user_repair(
        cross_scope_ctx,
        cross_scope_result,
        user_decision=USER_APPROVE_REPAIR,
    )
    record(
        "D-004-USER-PARTITION-AND-REBIND-RECOVERY",
        repaired_cross_scope,
        ALLOW,
        USER_REPAIR_VALIDATED,
    )

    budget_ctx = CollectiveContext(
        "TX-D005",
        (
            _action("A1", "AGENT-A", "NORMALIZE", change_weight=0.30),
            _action("B1", "AGENT-B", "SUMMARIZE", change_weight=0.30),
            _action("C1", "AGENT-C", "NORMALIZE", change_weight=0.30),
            _action("D1", "AGENT-D", "SUMMARIZE", change_weight=0.30),
        ),
    )
    budget_result = record(
        "D-005-LOCAL-ALLOW-CUMULATIVE-BUDGET-EXCEEDED",
        budget_ctx,
        PAUSE,
        CUMULATIVE_CHANGE_BUDGET_EXCEEDED,
    )
    repaired_budget = apply_user_repair(
        budget_ctx,
        budget_result,
        user_decision=USER_APPROVE_REPAIR,
        approved_action_ids=("A1", "B1", "C1"),
    )
    record(
        "D-006-USER-BOUNDED-SUBSET-RECOVERY",
        repaired_budget,
        ALLOW,
        USER_REPAIR_VALIDATED,
    )

    authority_ctx = CollectiveContext(
        "TX-D007",
        (
            _action("A1", "AGENT-A", "ADVISE", input_scope="POLICY", output_scope="POLICY"),
            _action("B1", "AGENT-B", "ROUTE_REVIEW", input_scope="POLICY", output_scope="REVIEW"),
            _action("C1", "AGENT-C", "FINALIZE_CANDIDATE", input_scope="REVIEW", output_scope="USER_DECISION"),
        ),
    )
    record(
        "D-007-LOCAL-ALLOW-COLLECTIVE-AUTHORITY-EXPANSION",
        authority_ctx,
        BLOCK,
        COLLECTIVE_AUTHORITY_EXPANSION,
    )

    record(
        "D-008-FRESH-USER-TRANSACTION-AFTER-BLOCK",
        CollectiveContext(
            "TX-D008-FRESH",
            (_action("A1", "AGENT-A", "ADVISE", input_scope="POLICY", output_scope="POLICY"),),
            fresh_user_decision=True,
        ),
        ALLOW,
        USER_REPAIR_VALIDATED,
    )

    binding_ctx = CollectiveContext(
        "TX-D009",
        (
            _action("A1", "AGENT-A", "SHARE_SUMMARY", channel="BOARD-2", binding="REQ-001"),
            _action("B1", "AGENT-B", "READ_CONTEXT", channel="BOARD-2", binding="REQ-002"),
        ),
    )
    binding_result = record(
        "D-009-LOCAL-ALLOW-CROSS-AGENT-BINDING-MISMATCH",
        binding_ctx,
        PAUSE,
        CROSS_AGENT_BINDING_MISMATCH,
    )
    repaired_binding = apply_user_repair(
        binding_ctx,
        binding_result,
        user_decision=USER_APPROVE_REPAIR,
        repaired_handoff_binding_id="REQ-001-USER-VERIFIED",
    )
    record(
        "D-010-USER-REBINDS-HANDOFF-RECOVERY",
        repaired_binding,
        ALLOW,
        USER_REPAIR_VALIDATED,
    )

    passed = sum(1 for row in rows if row["passed"])
    emergent_cases = [rows[2], rows[4], rows[6], rows[8]]
    return {
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "results": rows,
        "emergent_checks": {
            "local_allow_can_compose_into_pause_or_block": all(
                row["actual"]["local_all_allowed"] is True
                and row["actual"]["decision"] in {PAUSE, BLOCK}
                for row in emergent_cases
            ),
            "recoverable_cases_require_user_repair": all(
                row["actual"]["mediation_plan"] is not None
                and row["actual"]["mediation_plan"]["human_action_required"] is True
                and row["actual"]["mediation_plan"]["auto_apply"] is False
                for row in (rows[2], rows[4], rows[8])
            ),
            "authority_expansion_is_not_repaired_in_place": (
                rows[6]["actual"]["decision"] == BLOCK
                and rows[6]["actual"]["final"] is True
                and rows[6]["actual"]["retry_allowed"] is False
            ),
        },
    }


def run_full_simulation(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)

    c_summary = c.run_full_simulation(outdir / "c_regression")
    composition = run_composition_suite()

    safety = {
        "auto_fix_disabled": AUTO_FIX_ALLOWED is False,
        "auto_apply_revision_disabled": AUTO_APPLY_REVISION is False,
        "auto_commit_disabled": AUTO_COMMIT is False,
        "auto_push_disabled": AUTO_PUSH is False,
        "auto_merge_disabled": AUTO_MERGE is False,
        "network_disabled": NETWORK_ACCESS_ALLOWED is False,
        "external_execution_disabled": EXTERNAL_EXECUTION_ALLOWED is False,
        "local_gate_execution_authority_false": LocalActionGate.execution_authority is False,
        "local_gate_final_authority_false": LocalActionGate.final_decision_authority is False,
        "collective_gate_execution_authority_false": CollectiveMediationGate.execution_authority is False,
        "collective_gate_final_authority_false": CollectiveMediationGate.final_decision_authority is False,
    }

    success = (
        c_summary["decision"] == "ALLOW"
        and composition["total"] == 10
        and composition["passed"] == 10
        and composition["failed"] == 0
        and all(composition["emergent_checks"].values())
        and all(safety.values())
    )

    summary = {
        "simulator": "collective_interaction_mediation_phase1d_v0_1",
        "architecture": {
            "processing_order": [
                "LOCAL_ACTIONS",
                "LOCAL_ACTION_GATE",
                "COLLECTIVE_STATE",
                "COLLECTIVE_MEDIATION_GATE",
                "USER_HITL",
                "REVALIDATE",
            ],
            "final_decision_authority": "USER",
            "collective_state_required": True,
            "automatic_repair": False,
        },
        "c_regression": {
            "decision": c_summary["decision"],
            "c_specific_total": c_summary["c_specific"]["total"],
            "c_specific_passed": c_summary["c_specific"]["passed"],
            "c_specific_failed": c_summary["c_specific"]["failed"],
        },
        "composition": composition,
        "safety_checks": safety,
        "interpretation": {
            "claim": (
                "Contract-level deterministic evidence that individually ALLOWed synthetic actions can "
                "compose into a PAUSE/BLOCK condition, and that bounded USER/HITL mediation can recover "
                "selected repairable cases."
            ),
            "non_claim": (
                "This does not demonstrate real-world emergent agent behavior, semantic understanding, "
                "cyber capability, or production safety."
            ),
        },
        "decision": "ALLOW" if success else "BLOCK",
    }

    (outdir / "phase1d_collective_interaction_results_v0_1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    summary = run_full_simulation(Path("."))
    print(
        json.dumps(
            {
                "c_regression": summary["c_regression"],
                "composition": {
                    "total": summary["composition"]["total"],
                    "passed": summary["composition"]["passed"],
                    "failed": summary["composition"]["failed"],
                    "emergent_checks": summary["composition"]["emergent_checks"],
                },
                "safety_checks": summary["safety_checks"],
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
