#!/usr/bin/env python3
"""
Infrastructure Lifeline Mediation Randomized Simulation v0.2

Purpose:
    Simulate mediation among three lifeline infrastructure agents:
    Electricity, Water, and Gas.

Scope boundary:
    This is a randomized, seed-reproducible local simulation only.

Strictly prohibited in this file:
    - External API connections
    - Real infrastructure control
    - Automatic recovery
    - Automatic shutdown / disconnection

The mediator creates allocation proposals only. A simulated human operator
randomly returns APPROVE / REJECT / REDEFINE / REQUEST_ALTERNATIVES.

No real-world side effects are performed.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple


VERSION = "0.2"

NORMAL_REQUIRED_PER_INFRA = 6.0
FAILURE_TOTAL_RESOURCE_MIN = 3.5
FAILURE_TOTAL_RESOURCE_MAX = 5.0

INFRA_NAMES = ("electricity", "water", "gas")

HITL_DECISIONS: Tuple[str, ...] = (
    "APPROVE",
    "REJECT",
    "REDEFINE",
    "REQUEST_ALTERNATIVES",
)

SAFETY_BOUNDARY = {
    "external_api_connection_allowed": False,
    "real_infrastructure_control_allowed": False,
    "automatic_recovery_allowed": False,
    "automatic_shutdown_allowed": False,
    "automatic_disconnection_allowed": False,
    "simulation_only": True,
}


@dataclass(frozen=True)
class AgentProfile:
    name: str
    normal_required: float
    minimum_guarantee: float
    weight: float
    base_life_risk: float


@dataclass(frozen=True)
class AgentRequest:
    name: str
    requested: float
    normal_required: float
    minimum_guarantee: float
    weight: float
    life_risk: float


@dataclass(frozen=True)
class AllocationRow:
    name: str
    requested: float
    allocated: float
    shortage: float
    shortage_rate: float
    minimum_guarantee: float
    weight: float
    life_risk: float


@dataclass(frozen=True)
class MediationProposal:
    proposal_id: str
    total_resource: float
    total_requested: float
    total_allocated: float
    allocation: List[AllocationRow]
    max_shortage_rate: float
    weighted_life_risk_shortage: float
    mediator_note: str


@dataclass(frozen=True)
class HumanOperatorDecision:
    operator_id: str
    decision: Literal["APPROVE", "REJECT", "REDEFINE", "REQUEST_ALTERNATIVES"]
    rationale: str
    redefined_constraints: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SimulationRun:
    run_id: str
    seed: int
    version: str
    timestamp_utc: str
    safety_boundary: Dict[str, bool]
    scenario: Dict[str, Any]
    requests: List[AgentRequest]
    mediator_proposal: MediationProposal
    human_operator_decision: HumanOperatorDecision
    alternatives: List[MediationProposal]
    final_status: str
    no_external_effects: bool


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def round4(value: float) -> float:
    return round(float(value), 4)


def default_profiles() -> List[AgentProfile]:
    """
    Demo profile values.

    Minimum guarantees are intentionally below normal demand because the failure
    scenario limits total available resource to 3.5-5.0 while each infrastructure
    normally requires 6.0.
    """
    return [
        AgentProfile(
            name="electricity",
            normal_required=NORMAL_REQUIRED_PER_INFRA,
            minimum_guarantee=1.10,
            weight=1.10,
            base_life_risk=0.78,
        ),
        AgentProfile(
            name="water",
            normal_required=NORMAL_REQUIRED_PER_INFRA,
            minimum_guarantee=1.20,
            weight=1.25,
            base_life_risk=0.88,
        ),
        AgentProfile(
            name="gas",
            normal_required=NORMAL_REQUIRED_PER_INFRA,
            minimum_guarantee=0.80,
            weight=0.90,
            base_life_risk=0.62,
        ),
    ]


def generate_requests(
    rng: random.Random,
    profiles: Sequence[AgentProfile],
) -> List[AgentRequest]:
    """
    Each agent randomly requests resources around the normal required amount.

    The request range is clipped so the simulation remains readable and avoids
    unrealistic negative or near-zero demand.
    """
    requests: List[AgentRequest] = []

    for profile in profiles:
        requested = clamp(
            rng.gauss(mu=profile.normal_required, sigma=0.75),
            lower=4.5,
            upper=7.5,
        )

        demand_pressure = requested / profile.normal_required
        risk_noise = rng.uniform(-0.10, 0.10)
        life_risk = clamp(
            profile.base_life_risk + risk_noise + 0.08 * (demand_pressure - 1.0),
            lower=0.0,
            upper=1.0,
        )

        requests.append(
            AgentRequest(
                name=profile.name,
                requested=round4(requested),
                normal_required=round4(profile.normal_required),
                minimum_guarantee=round4(profile.minimum_guarantee),
                weight=round4(profile.weight),
                life_risk=round4(life_risk),
            )
        )

    return requests


def allocate_minimum_guarantees(
    total_resource: float,
    requests: Sequence[AgentRequest],
) -> Dict[str, float]:
    """
    Allocate the minimum guarantee first.

    If total resource is ever below the sum of guarantees, this function degrades
    gracefully by distributing the limited resource proportionally to guarantees.
    That branch is still proposal-only and does not perform real control.
    """
    guarantee_sum = sum(item.minimum_guarantee for item in requests)

    if guarantee_sum <= 0:
        equal_share = total_resource / len(requests)
        return {item.name: equal_share for item in requests}

    if total_resource < guarantee_sum:
        return {
            item.name: total_resource * (item.minimum_guarantee / guarantee_sum)
            for item in requests
        }

    return {
        item.name: min(item.minimum_guarantee, item.requested)
        for item in requests
    }


def proposal_priority_score(request: AgentRequest, current_allocation: float) -> float:
    """
    Priority score used for allocating remaining resource.

    Factors:
        - weight
        - life_risk
        - shortage_rate after the minimum guarantee stage

    Higher score receives a larger share of the remaining resource.
    """
    shortage = max(0.0, request.requested - current_allocation)
    shortage_rate = shortage / request.requested if request.requested > 0 else 0.0

    return (
        request.weight
        * (1.0 + request.life_risk)
        * (1.0 + shortage_rate)
    )


def distribute_remaining_resource(
    total_resource: float,
    requests: Sequence[AgentRequest],
    allocations: Dict[str, float],
) -> Dict[str, float]:
    """
    Iteratively distribute remaining resource according to priority score.

    The loop prevents over-allocation by redistributing leftovers when an agent's
    unmet demand is fully satisfied.
    """
    allocated_total = sum(allocations.values())
    remaining = max(0.0, total_resource - allocated_total)

    for _ in range(20):
        if remaining <= 1e-9:
            break

        unmet = {
            item.name: max(0.0, item.requested - allocations[item.name])
            for item in requests
        }
        active = [item for item in requests if unmet[item.name] > 1e-9]

        if not active:
            break

        scores = {
            item.name: proposal_priority_score(item, allocations[item.name])
            for item in active
        }
        score_sum = sum(scores.values())

        if score_sum <= 0:
            share = remaining / len(active)
            for item in active:
                delta = min(share, unmet[item.name])
                allocations[item.name] += delta
                remaining -= delta
            continue

        used_this_round = 0.0
        for item in active:
            raw_delta = remaining * (scores[item.name] / score_sum)
            delta = min(raw_delta, unmet[item.name])
            allocations[item.name] += delta
            used_this_round += delta

        remaining -= used_this_round

        if used_this_round <= 1e-9:
            break

    return allocations


def build_allocation_rows(
    requests: Sequence[AgentRequest],
    allocations: Dict[str, float],
) -> List[AllocationRow]:
    rows: List[AllocationRow] = []

    for item in requests:
        allocated = allocations[item.name]
        shortage = max(0.0, item.requested - allocated)
        shortage_rate = shortage / item.requested if item.requested > 0 else 0.0

        rows.append(
            AllocationRow(
                name=item.name,
                requested=round4(item.requested),
                allocated=round4(allocated),
                shortage=round4(shortage),
                shortage_rate=round4(shortage_rate),
                minimum_guarantee=round4(item.minimum_guarantee),
                weight=round4(item.weight),
                life_risk=round4(item.life_risk),
            )
        )

    return rows


def make_mediation_proposal(
    proposal_id: str,
    total_resource: float,
    requests: Sequence[AgentRequest],
    strategy: Literal["standard", "risk_first", "equal_shortage"] = "standard",
) -> MediationProposal:
    """
    Create a proposal-only allocation plan.

    Strategies:
        standard:
            Minimum guarantee, then weighted distribution using life risk and shortage.
        risk_first:
            Same algorithm, but life-risk-heavy weights are increased.
        equal_shortage:
            Uses flatter weights to reduce disparity in shortage rates.
    """
    adjusted_requests: List[AgentRequest] = []

    for item in requests:
        if strategy == "risk_first":
            adjusted_weight = item.weight * (1.0 + item.life_risk)
        elif strategy == "equal_shortage":
            adjusted_weight = 1.0
        else:
            adjusted_weight = item.weight

        adjusted_requests.append(
            AgentRequest(
                name=item.name,
                requested=item.requested,
                normal_required=item.normal_required,
                minimum_guarantee=item.minimum_guarantee,
                weight=round4(adjusted_weight),
                life_risk=item.life_risk,
            )
        )

    allocations = allocate_minimum_guarantees(total_resource, adjusted_requests)
    allocations = distribute_remaining_resource(total_resource, adjusted_requests, allocations)
    rows = build_allocation_rows(adjusted_requests, allocations)

    max_shortage_rate = max(row.shortage_rate for row in rows)
    weighted_life_risk_shortage = sum(
        row.shortage_rate * row.life_risk * row.weight for row in rows
    )

    mediator_note = (
        "Proposal only. No external API, no real infrastructure control, "
        "no automatic recovery, and no automatic shutdown/disconnection."
    )

    return MediationProposal(
        proposal_id=proposal_id,
        total_resource=round4(total_resource),
        total_requested=round4(sum(item.requested for item in adjusted_requests)),
        total_allocated=round4(sum(row.allocated for row in rows)),
        allocation=rows,
        max_shortage_rate=round4(max_shortage_rate),
        weighted_life_risk_shortage=round4(weighted_life_risk_shortage),
        mediator_note=mediator_note,
    )


def simulated_human_operator(
    rng: random.Random,
    proposal: MediationProposal,
) -> HumanOperatorDecision:
    """
    Simulated HITL decision.

    The decision is randomized by design. The rationale text is generated after
    the random decision, but it does not trigger any real-world action.
    """
    decision = rng.choice(HITL_DECISIONS)

    if decision == "APPROVE":
        rationale = "Simulated operator approved this proposal for simulation logging only."
        constraints = None
    elif decision == "REJECT":
        rationale = "Simulated operator rejected the proposal and requested no execution."
        constraints = None
    elif decision == "REDEFINE":
        rationale = "Simulated operator requested revised constraints before any simulated approval."
        constraints = {
            "max_allowed_shortage_rate": round4(rng.uniform(0.45, 0.65)),
            "prioritize_life_risk_above": round4(rng.uniform(0.75, 0.90)),
            "require_new_proposal_only": True,
        }
    else:
        rationale = "Simulated operator requested alternative allocation proposals."
        constraints = None

    return HumanOperatorDecision(
        operator_id="SimulatedHumanOperator",
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        redefined_constraints=constraints,
    )


def build_alternatives_if_requested(
    decision: HumanOperatorDecision,
    total_resource: float,
    requests: Sequence[AgentRequest],
) -> List[MediationProposal]:
    if decision.decision != "REQUEST_ALTERNATIVES":
        return []

    return [
        make_mediation_proposal(
            proposal_id="alternative-risk-first",
            total_resource=total_resource,
            requests=requests,
            strategy="risk_first",
        ),
        make_mediation_proposal(
            proposal_id="alternative-equal-shortage",
            total_resource=total_resource,
            requests=requests,
            strategy="equal_shortage",
        ),
    ]


def determine_final_status(decision: HumanOperatorDecision) -> str:
    """
    Final status is a simulation status only.

    Even APPROVE does not execute anything. It only marks that the simulated
    operator accepted the proposal inside the simulation.
    """
    if decision.decision == "APPROVE":
        return "SIMULATED_APPROVAL_ONLY_NO_EXECUTION"
    if decision.decision == "REJECT":
        return "SIMULATED_REJECTION_NO_EXECUTION"
    if decision.decision == "REDEFINE":
        return "SIMULATED_REDEFINE_REQUESTED_NO_EXECUTION"
    return "SIMULATED_ALTERNATIVES_REQUESTED_NO_EXECUTION"


def run_simulation(seed: int) -> SimulationRun:
    rng = random.Random(seed)
    profiles = default_profiles()

    total_resource = rng.uniform(
        FAILURE_TOTAL_RESOURCE_MIN,
        FAILURE_TOTAL_RESOURCE_MAX,
    )
    requests = generate_requests(rng, profiles)

    proposal = make_mediation_proposal(
        proposal_id="proposal-standard",
        total_resource=total_resource,
        requests=requests,
        strategy="standard",
    )

    operator_decision = simulated_human_operator(rng, proposal)
    alternatives = build_alternatives_if_requested(
        decision=operator_decision,
        total_resource=total_resource,
        requests=requests,
    )

    run_id = f"infra-lifeline-v0-2-seed-{seed}"

    return SimulationRun(
        run_id=run_id,
        seed=seed,
        version=VERSION,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        safety_boundary=SAFETY_BOUNDARY,
        scenario={
            "mode": "failure_resource_constraint",
            "normal_required_per_infrastructure": NORMAL_REQUIRED_PER_INFRA,
            "failure_total_resource_range": [
                FAILURE_TOTAL_RESOURCE_MIN,
                FAILURE_TOTAL_RESOURCE_MAX,
            ],
            "actual_total_resource": round4(total_resource),
            "agents": list(INFRA_NAMES),
        },
        requests=requests,
        mediator_proposal=proposal,
        human_operator_decision=operator_decision,
        alternatives=alternatives,
        final_status=determine_final_status(operator_decision),
        no_external_effects=True,
    )


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def render_stdout_summary(result: SimulationRun) -> str:
    proposal = result.mediator_proposal

    lines = [
        "Infrastructure Lifeline Mediation Randomized Simulation v0.2",
        "=" * 64,
        f"run_id: {result.run_id}",
        f"seed: {result.seed}",
        f"mode: {result.scenario['mode']}",
        f"total_resource: {proposal.total_resource}",
        f"total_requested: {proposal.total_requested}",
        "",
        "Safety boundary:",
        f"  external_api_connection_allowed: {result.safety_boundary['external_api_connection_allowed']}",
        f"  real_infrastructure_control_allowed: {result.safety_boundary['real_infrastructure_control_allowed']}",
        f"  automatic_recovery_allowed: {result.safety_boundary['automatic_recovery_allowed']}",
        f"  automatic_shutdown_allowed: {result.safety_boundary['automatic_shutdown_allowed']}",
        f"  automatic_disconnection_allowed: {result.safety_boundary['automatic_disconnection_allowed']}",
        "",
        "Mediator proposal:",
        f"  proposal_id: {proposal.proposal_id}",
        f"  max_shortage_rate: {proposal.max_shortage_rate}",
        f"  weighted_life_risk_shortage: {proposal.weighted_life_risk_shortage}",
        "",
        "Allocation:",
        "  agent         requested  allocated  shortage  shortage_rate  life_risk  weight",
    ]

    for row in proposal.allocation:
        lines.append(
            f"  {row.name:<12} "
            f"{row.requested:>9.4f}  "
            f"{row.allocated:>9.4f}  "
            f"{row.shortage:>8.4f}  "
            f"{row.shortage_rate:>13.4f}  "
            f"{row.life_risk:>9.4f}  "
            f"{row.weight:>6.4f}"
        )

    lines.extend(
        [
            "",
            "Simulated HITL:",
            f"  operator_id: {result.human_operator_decision.operator_id}",
            f"  decision: {result.human_operator_decision.decision}",
            f"  rationale: {result.human_operator_decision.rationale}",
            f"  redefined_constraints: {result.human_operator_decision.redefined_constraints}",
            "",
            f"alternatives_count: {len(result.alternatives)}",
            f"final_status: {result.final_status}",
            f"no_external_effects: {result.no_external_effects}",
        ]
    )

    return "\n".join(lines)


def write_json(result: SimulationRun, output_path: Path, pretty: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = to_jsonable(result)

    with output_path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Infrastructure Lifeline Mediation Randomized Simulation v0.2 "
            "as a local, seed-reproducible, proposal-only simulation."
        )
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for reproducible randomization. Default: 42",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("infrastructure_lifeline_mediation_result.json"),
        help="JSON output path. Default: infrastructure_lifeline_mediation_result.json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print full JSON payload to stdout after the human-readable summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_simulation(seed=args.seed)

    print(render_stdout_summary(result))
    write_json(result, args.output, pretty=args.pretty)
    print("")
    print(f"json_output: {args.output}")

    if args.print_json:
        print("")
        print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
