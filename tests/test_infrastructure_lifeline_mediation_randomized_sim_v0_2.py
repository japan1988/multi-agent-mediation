from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import infrastructure_lifeline_mediation_randomized_sim_v0_2 as sim


def _jsonable_without_timestamp(result: sim.SimulationRun) -> dict[str, Any]:
    payload = sim.to_jsonable(result)
    payload.pop("timestamp_utc", None)
    return payload


def _assert_proposal_within_resource_limit(
    proposal: sim.MediationProposal,
    tolerance: float = 0.001,
) -> None:
    row_sum = sum(row.allocated for row in proposal.allocation)

    assert proposal.total_allocated <= proposal.total_resource + tolerance
    assert row_sum <= proposal.total_resource + tolerance
    assert proposal.total_allocated >= 0.0

    for row in proposal.allocation:
        assert row.allocated >= 0.0
        assert row.requested >= row.allocated - tolerance
        assert 0.0 <= row.shortage_rate <= 1.0
        assert 0.0 <= row.life_risk <= 1.0


def test_version_and_run_id_are_aligned_to_v0_2() -> None:
    result = sim.run_simulation(seed=42)

    assert sim.VERSION == "0.2"
    assert result.version == "0.2"
    assert result.run_id == "infra-lifeline-v0-2-seed-42"
    assert "v0.2" in sim.render_stdout_summary(result)


def test_seed_reproducibility_ignoring_timestamp() -> None:
    first = sim.run_simulation(seed=42)
    second = sim.run_simulation(seed=42)

    assert _jsonable_without_timestamp(first) == _jsonable_without_timestamp(second)


def test_failure_resource_range_and_agent_count() -> None:
    result = sim.run_simulation(seed=42)

    assert sim.FAILURE_TOTAL_RESOURCE_MIN <= result.mediator_proposal.total_resource <= sim.FAILURE_TOTAL_RESOURCE_MAX
    assert result.scenario["actual_total_resource"] == result.mediator_proposal.total_resource
    assert [request.name for request in result.requests] == list(sim.INFRA_NAMES)
    assert len(result.mediator_proposal.allocation) == 3


def test_allocations_never_exceed_resource_limit_across_seed_range() -> None:
    for seed in range(500):
        result = sim.run_simulation(seed=seed)

        _assert_proposal_within_resource_limit(result.mediator_proposal)

        for alternative in result.alternatives:
            _assert_proposal_within_resource_limit(alternative)


def test_all_hitl_branches_are_observed_in_seed_range() -> None:
    observed = {
        sim.run_simulation(seed=seed).human_operator_decision.decision
        for seed in range(50)
    }

    assert observed == set(sim.HITL_DECISIONS)


def test_request_alternatives_creates_two_proposal_only_alternatives() -> None:
    result = sim.run_simulation(seed=0)

    assert result.human_operator_decision.decision == "REQUEST_ALTERNATIVES"
    assert [proposal.proposal_id for proposal in result.alternatives] == [
        "alternative-risk-first",
        "alternative-equal-shortage",
    ]

    for proposal in result.alternatives:
        assert "Proposal only" in proposal.mediator_note
        assert "No external API" in proposal.mediator_note
        _assert_proposal_within_resource_limit(proposal)


def test_non_alternative_hitl_branches_do_not_create_alternatives() -> None:
    for seed in (1, 2, 3):
        result = sim.run_simulation(seed=seed)

        assert result.human_operator_decision.decision != "REQUEST_ALTERNATIVES"
        assert result.alternatives == []


def test_redefine_branch_contains_redefined_constraints() -> None:
    result = sim.run_simulation(seed=3)

    assert result.human_operator_decision.decision == "REDEFINE"
    assert result.human_operator_decision.redefined_constraints is not None
    assert result.human_operator_decision.redefined_constraints["require_new_proposal_only"] is True


def test_safety_boundary_disallows_external_or_real_world_effects() -> None:
    result = sim.run_simulation(seed=42)

    assert result.no_external_effects is True
    assert result.safety_boundary["simulation_only"] is True
    assert result.safety_boundary["external_api_connection_allowed"] is False
    assert result.safety_boundary["real_infrastructure_control_allowed"] is False
    assert result.safety_boundary["automatic_recovery_allowed"] is False
    assert result.safety_boundary["automatic_shutdown_allowed"] is False
    assert result.safety_boundary["automatic_disconnection_allowed"] is False


def test_json_writer_outputs_expected_payload(tmp_path: Path) -> None:
    result = sim.run_simulation(seed=42)
    output_path = tmp_path / "result.json"

    sim.write_json(result, output_path, pretty=True)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["seed"] == 42
    assert payload["version"] == "0.2"
    assert payload["run_id"] == "infra-lifeline-v0-2-seed-42"
    assert payload["no_external_effects"] is True
    assert payload["mediator_proposal"]["total_allocated"] <= payload["mediator_proposal"]["total_resource"] + 0.001


def test_cli_writes_json_file(tmp_path: Path) -> None:
    output_path = tmp_path / "cli-result.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(Path(sim.__file__).resolve()),
            "--seed",
            "42",
            "--output",
            str(output_path),
            "--pretty",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Infrastructure Lifeline Mediation Randomized Simulation v0.2" in completed.stdout
    assert "infra-lifeline-v0-2-seed-42" in completed.stdout
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["seed"] == 42
    assert payload["version"] == "0.2"
    assert payload["no_external_effects"] is True
