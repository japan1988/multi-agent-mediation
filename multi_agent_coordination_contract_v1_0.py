# -*- coding: utf-8 -*-
"""
multi_agent_coordination_contract_v1_0.py

Multi-agent coordination contract simulator (research / educational use).

Purpose:
- Detect coordination failures before agent workflows create external side effects.
- Keep multi-agent orchestration advisory and HITL-gated.
- Preserve KAGE / Maestro-style invariants:
  - coordination_gate never seals by itself
  - RFL-style relative or human-load uncertainty pauses for HITL
  - sealed=True remains reserved for higher-risk layers such as ethics_gate / acc_gate
  - external actions are not executed here

This module does not call external APIs, create PRs, push changes, send email,
upload files, delete files, or execute subprocesses. It only evaluates supplied
contract / handoff data and returns ARL-like rows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER", "ADMIN"]

DECISION_RUN: Decision = "RUN"
DECISION_PAUSE: Decision = "PAUSE_FOR_HITL"
DECISION_STOPPED: Decision = "STOPPED"

FINAL_SYSTEM: FinalDecider = "SYSTEM"

LAYER_COORDINATION = "coordination_gate"
LAYER_ACC = "acc_gate"
LAYER_ETHICS = "ethics_gate"

RC_COORD_OK = "COORD_OK"
RC_COORD_AGENT_BUDGET_EXCEEDED = "COORD_AGENT_BUDGET_EXCEEDED"
RC_COORD_HANDOFF_LOOP_DETECTED = "COORD_HANDOFF_LOOP_DETECTED"
RC_COORD_HANDOFF_BUDGET_EXCEEDED = "COORD_HANDOFF_BUDGET_EXCEEDED"
RC_COORD_TOOL_CALL_BUDGET_EXCEEDED = "COORD_TOOL_CALL_BUDGET_EXCEEDED"
RC_COORD_MESSAGE_BUDGET_EXCEEDED = "COORD_MESSAGE_BUDGET_EXCEEDED"
RC_COORD_ROLE_CONTRACT_MISSING = "COORD_ROLE_CONTRACT_MISSING"
RC_COORD_OUTPUT_SCHEMA_MISSING = "COORD_OUTPUT_SCHEMA_MISSING"
RC_COORD_SCOPE_UNCLEAR = "COORD_SCOPE_UNCLEAR"
RC_COORD_UNAPPROVED_TOOL = "COORD_UNAPPROVED_TOOL"
RC_COORD_EXTERNAL_SIDE_EFFECT_ROUTE_TO_ACC = "COORD_EXTERNAL_SIDE_EFFECT_ROUTE_TO_ACC"

EXTERNAL_SIDE_EFFECT_ACTIONS = frozenset(
    {
        "send_email",
        "upload_file",
        "submit_artifact",
        "push",
        "create_pull_request",
        "merge_pull_request",
        "delete_file",
        "post_comment",
        "call_external_api",
    }
)


@dataclass(frozen=True)
class CoordinationBudget:
    """Hard limits for one multi-agent coordination run."""

    max_agents: int = 5
    max_handoffs: int = 8
    max_tool_calls: int = 20
    max_messages: int = 40
    max_handoffs_per_pair: int = 2


@dataclass(frozen=True)
class AgentContract:
    """Declared role and authority boundary for one agent."""

    agent_id: str
    role: str
    allowed_tools: Tuple[str, ...] = ()
    forbidden_actions: Tuple[str, ...] = tuple(sorted(EXTERNAL_SIDE_EFFECT_ACTIONS))
    input_scope: str = "assigned_task_only"
    output_schema: str = ""
    max_handoffs: int = 2


@dataclass(frozen=True)
class HandoffEvent:
    """One handoff from an agent to another agent."""

    handoff_id: str
    source_agent_id: str
    target_agent_id: str
    reason: str = ""


@dataclass(frozen=True)
class ToolUseEvent:
    """One requested or observed tool use."""

    agent_id: str
    tool_name: str
    action: str = ""


@dataclass(frozen=True)
class MessageEvent:
    """One agent message or coordination message."""

    agent_id: str
    message_id: str
    kind: str = "coordination"


@dataclass
class CoordinationARLRow:
    run_id: str
    ts: str
    layer: str
    decision: Decision
    sealed: bool
    overrideable: bool
    final_decider: FinalDecider
    reason_code: str
    agent_id: str = ""
    target_agent_id: str = ""
    handoff_id: str = ""
    detail: str = ""


@dataclass
class CoordinationResult:
    run_id: str
    decision: Decision
    reason_code: str
    rows: List[Dict[str, Any]] = field(default_factory=list)


def utc_ts() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _row(
    *,
    run_id: str,
    decision: Decision,
    reason_code: str,
    agent_id: str = "",
    target_agent_id: str = "",
    handoff_id: str = "",
    detail: str = "",
    layer: str = LAYER_COORDINATION,
    sealed: bool = False,
    overrideable: bool = True,
    final_decider: FinalDecider = FINAL_SYSTEM,
) -> Dict[str, Any]:
    return asdict(
        CoordinationARLRow(
            run_id=run_id,
            ts=utc_ts(),
            layer=layer,
            decision=decision,
            sealed=sealed,
            overrideable=overrideable,
            final_decider=final_decider,
            reason_code=reason_code,
            agent_id=agent_id,
            target_agent_id=target_agent_id,
            handoff_id=handoff_id,
            detail=detail,
        )
    )


def _pause(
    *,
    run_id: str,
    reason_code: str,
    agent_id: str = "",
    target_agent_id: str = "",
    handoff_id: str = "",
    detail: str = "",
) -> CoordinationResult:
    rows = [
        _row(
            run_id=run_id,
            decision=DECISION_PAUSE,
            reason_code=reason_code,
            agent_id=agent_id,
            target_agent_id=target_agent_id,
            handoff_id=handoff_id,
            detail=detail,
        )
    ]
    return CoordinationResult(
        run_id=run_id,
        decision=DECISION_PAUSE,
        reason_code=reason_code,
        rows=rows,
    )


def _agent_ids(contracts: Sequence[AgentContract]) -> List[str]:
    seen: List[str] = []
    for contract in contracts:
        if contract.agent_id and contract.agent_id not in seen:
            seen.append(contract.agent_id)
    return seen


def detect_handoff_loop(
    handoffs: Sequence[HandoffEvent],
    *,
    max_handoffs_per_pair: int,
) -> Optional[HandoffEvent]:
    """Detect repeated A->B handoff pressure beyond the configured pair budget."""

    pair_counts: Dict[Tuple[str, str], int] = {}
    limit = max(1, int(max_handoffs_per_pair))
    for event in handoffs:
        key = (event.source_agent_id, event.target_agent_id)
        pair_counts[key] = pair_counts.get(key, 0) + 1
        if pair_counts[key] > limit:
            return event
    return None


def detect_reciprocal_loop(handoffs: Sequence[HandoffEvent]) -> Optional[HandoffEvent]:
    """Detect A->B followed by B->A as a minimal reciprocal loop signal."""

    seen: set[Tuple[str, str]] = set()
    for event in handoffs:
        key = (event.source_agent_id, event.target_agent_id)
        reverse = (event.target_agent_id, event.source_agent_id)
        if reverse in seen:
            return event
        seen.add(key)
    return None


def _contract_by_agent(
    contracts: Sequence[AgentContract],
) -> Dict[str, AgentContract]:
    return {contract.agent_id: contract for contract in contracts if contract.agent_id}


def _first_missing_contract(
    contracts: Sequence[AgentContract],
    handoffs: Sequence[HandoffEvent],
    tool_uses: Sequence[ToolUseEvent],
    messages: Sequence[MessageEvent],
) -> str:
    known = set(_contract_by_agent(contracts))
    referenced: set[str] = set()

    for handoff in handoffs:
        referenced.add(handoff.source_agent_id)
        referenced.add(handoff.target_agent_id)

    for tool_use in tool_uses:
        referenced.add(tool_use.agent_id)

    for message in messages:
        referenced.add(message.agent_id)

    missing = sorted(agent_id for agent_id in referenced if agent_id and agent_id not in known)
    return missing[0] if missing else ""


def _first_incomplete_contract(contracts: Sequence[AgentContract]) -> Tuple[str, str]:
    for contract in contracts:
        if not contract.role.strip():
            return contract.agent_id, RC_COORD_ROLE_CONTRACT_MISSING

        if not contract.output_schema.strip():
            return contract.agent_id, RC_COORD_OUTPUT_SCHEMA_MISSING

        if not contract.input_scope.strip() or contract.input_scope == "unclear":
            return contract.agent_id, RC_COORD_SCOPE_UNCLEAR

    return "", ""


def _first_unapproved_tool(
    contracts: Sequence[AgentContract],
    tool_uses: Sequence[ToolUseEvent],
) -> Optional[ToolUseEvent]:
    contract_map = _contract_by_agent(contracts)

    for event in tool_uses:
        contract = contract_map.get(event.agent_id)
        if contract is None:
            continue

        if event.tool_name and event.tool_name not in set(contract.allowed_tools):
            return event

    return None


def _first_forbidden_action(
    contracts: Sequence[AgentContract],
    tool_uses: Sequence[ToolUseEvent],
) -> Optional[ToolUseEvent]:
    contract_map = _contract_by_agent(contracts)

    for event in tool_uses:
        contract = contract_map.get(event.agent_id)
        forbidden = set(contract.forbidden_actions) if contract else set(EXTERNAL_SIDE_EFFECT_ACTIONS)
        action = event.action or event.tool_name

        if action in forbidden or action in EXTERNAL_SIDE_EFFECT_ACTIONS:
            return event

    return None


def coordination_gate(
    *,
    run_id: str,
    contracts: Sequence[AgentContract],
    handoffs: Sequence[HandoffEvent] = (),
    tool_uses: Sequence[ToolUseEvent] = (),
    messages: Sequence[MessageEvent] = (),
    budget: CoordinationBudget = CoordinationBudget(),
) -> CoordinationResult:
    """Evaluate multi-agent coordination risk and return ARL-like rows.

    This gate is intentionally conservative. Coordination uncertainty becomes
    PAUSE_FOR_HITL, not automatic execution. It does not seal by itself.
    """

    agent_ids = _agent_ids(contracts)

    if len(agent_ids) > max(1, int(budget.max_agents)):
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_AGENT_BUDGET_EXCEEDED,
            detail=f"agents={len(agent_ids)} max_agents={budget.max_agents}",
        )

    missing_agent = _first_missing_contract(contracts, handoffs, tool_uses, messages)
    if missing_agent:
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_ROLE_CONTRACT_MISSING,
            agent_id=missing_agent,
            detail="Referenced agent has no AgentContract.",
        )

    agent_id, contract_reason = _first_incomplete_contract(contracts)
    if contract_reason:
        return _pause(
            run_id=run_id,
            reason_code=contract_reason,
            agent_id=agent_id,
            detail="AgentContract is incomplete or unclear.",
        )

    if len(handoffs) > max(0, int(budget.max_handoffs)):
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_HANDOFF_BUDGET_EXCEEDED,
            detail=f"handoffs={len(handoffs)} max_handoffs={budget.max_handoffs}",
        )

    reciprocal = detect_reciprocal_loop(handoffs)
    if reciprocal is not None:
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_HANDOFF_LOOP_DETECTED,
            agent_id=reciprocal.source_agent_id,
            target_agent_id=reciprocal.target_agent_id,
            handoff_id=reciprocal.handoff_id,
            detail="Reciprocal handoff loop detected.",
        )

    repeated = detect_handoff_loop(
        handoffs,
        max_handoffs_per_pair=budget.max_handoffs_per_pair,
    )
    if repeated is not None:
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_HANDOFF_LOOP_DETECTED,
            agent_id=repeated.source_agent_id,
            target_agent_id=repeated.target_agent_id,
            handoff_id=repeated.handoff_id,
            detail="Repeated handoff pair exceeded per-pair budget.",
        )

    if len(tool_uses) > max(0, int(budget.max_tool_calls)):
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_TOOL_CALL_BUDGET_EXCEEDED,
            detail=f"tool_calls={len(tool_uses)} max_tool_calls={budget.max_tool_calls}",
        )

    forbidden = _first_forbidden_action(contracts, tool_uses)
    if forbidden is not None:
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_EXTERNAL_SIDE_EFFECT_ROUTE_TO_ACC,
            agent_id=forbidden.agent_id,
            detail=(
                f"action={forbidden.action or forbidden.tool_name}; "
                "route to ACC/HITL before execution."
            ),
        )

    unapproved = _first_unapproved_tool(contracts, tool_uses)
    if unapproved is not None:
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_UNAPPROVED_TOOL,
            agent_id=unapproved.agent_id,
            detail=f"tool={unapproved.tool_name}",
        )

    if len(messages) > max(0, int(budget.max_messages)):
        return _pause(
            run_id=run_id,
            reason_code=RC_COORD_MESSAGE_BUDGET_EXCEEDED,
            detail=f"messages={len(messages)} max_messages={budget.max_messages}",
        )

    rows = [
        _row(
            run_id=run_id,
            decision=DECISION_RUN,
            reason_code=RC_COORD_OK,
            overrideable=False,
            detail=(
                f"agents={len(agent_ids)} handoffs={len(handoffs)} "
                f"tool_calls={len(tool_uses)} messages={len(messages)}"
            ),
        )
    ]

    return CoordinationResult(
        run_id=run_id,
        decision=DECISION_RUN,
        reason_code=RC_COORD_OK,
        rows=rows,
    )


def assert_coordination_invariants(rows: Iterable[Dict[str, Any]]) -> None:
    """Validate core invariants for rows emitted by this module."""

    for row in rows:
        layer = row.get("layer")
        sealed = bool(row.get("sealed"))
        decision = row.get("decision")
        overrideable = bool(row.get("overrideable"))
        final_decider = row.get("final_decider")

        if layer == LAYER_COORDINATION:
            if sealed:
                raise AssertionError("coordination_gate must never emit sealed=True")

            if decision not in {DECISION_RUN, DECISION_PAUSE}:
                raise AssertionError(
                    f"coordination_gate emitted unexpected decision: {decision}"
                )

        if sealed:
            if layer not in {LAYER_ETHICS, LAYER_ACC}:
                raise AssertionError(f"sealed row outside ethics/acc: {layer}")

            if overrideable:
                raise AssertionError("sealed row must not be overrideable")

            if final_decider != FINAL_SYSTEM:
                raise AssertionError("sealed row must have final_decider=SYSTEM")


def demo() -> CoordinationResult:
    """Small deterministic demonstration."""

    contracts = [
        AgentContract(
            agent_id="planner",
            role="task_planner",
            allowed_tools=("read_context",),
            output_schema="plan_v1",
        ),
        AgentContract(
            agent_id="reviewer",
            role="safety_reviewer",
            allowed_tools=("read_context",),
            output_schema="review_v1",
        ),
    ]

    handoffs = [
        HandoffEvent("HND#000001", "planner", "reviewer", "needs safety review"),
        HandoffEvent("HND#000002", "reviewer", "planner", "scope unclear"),
    ]

    result = coordination_gate(
        run_id="DEMO#COORD",
        contracts=contracts,
        handoffs=handoffs,
    )
    assert_coordination_invariants(result.rows)
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(asdict(demo()), ensure_ascii=False, indent=2))
