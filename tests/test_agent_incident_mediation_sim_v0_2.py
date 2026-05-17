# -*- coding: utf-8 -*-
"""Tests for agent_incident_mediation_sim_v0_2.py.

These tests verify the local-only incident mediation flow:

- PseudoTasukeru detects and escalates log/output mismatch.
- Mediator/Maestro performs HITL before control action.
- The simulated user instruction is recorded.
- STOP_AGENT and AUTHORIZE_SEAL branches both work.
- Only the abnormal agent is stopped/sealed.
- ARL, 3D-DAC, RCV, and Tasukeru-style artifacts are written.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SIM_PATH = ROOT / "agent_incident_mediation_sim_v0_2.py"


def load_sim_module():
    assert SIM_PATH.exists(), f"Missing simulation file: {SIM_PATH}"

    module_name = "agent_incident_mediation_sim_v0_2_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SIM_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    # Required for dataclasses when loading by file path on newer Python versions.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sim_module():
    return load_sim_module()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def assert_common_success(result: dict):
    assert result["final_decision"] == "STOPPED"

    tasukeru = result["tasukeru_report"]
    assert tasukeru["tool"] == "PseudoTasukeru"
    assert tasukeru["decision"] == "PAUSE_FOR_HITL"
    assert len(tasukeru["findings"]) == 1

    finding = tasukeru["findings"][0]
    assert finding["agent_id"] == "agent_b"
    assert finding["finding"] == "LOG_OUTPUT_MISMATCH"
    assert finding["review_level"] == "HITL_REQUIRED"
    assert finding["decision"] == "PAUSE_FOR_HITL"
    assert finding["reason_code"] == "RESULT_LOG_MISMATCH"

    packet = tasukeru["escalation_packet"]
    assert packet["escalate_to"] == "Mediator"
    assert packet["decision"] == "PAUSE_FOR_HITL"
    assert packet["finding_count"] == 1
    assert packet["hitl_required_count"] == 1
    assert packet["dependency_verified"] is True

    dac = tasukeru["dimension_dependency_report"]
    assert dac["tool"] == "3D-DAC"
    assert dac["verified"] is True
    assert dac["decision"] == "RUN"
    assert dac["dependency_count"] == 1
    assert dac["dependency_mismatch_count"] == 0
    assert dac["policy"]["advisory_only"] is True
    assert dac["policy"]["auto_fix_allowed"] is False
    assert dac["policy"]["auto_merge_allowed"] is False

    assert result["arl_verify"]["verified"] is True
    assert result["arl_verify"]["violations"] == []
    assert result["result_consistency_verify"]["verified"] is True
    assert result["result_consistency_verify"]["mismatch_count"] == 0
    assert result["result_consistency_verify"]["mismatches"] == []

    # Containment check: only the abnormal agent is stopped/sealed.
    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_a"] == "ACTIVE"
    assert statuses["agent_c"] == "ACTIVE"
    assert statuses["agent_b"] in {"STOPPED", "SEALED"}

    safety = result["safety_boundary"]
    assert safety["local_only"] is True
    assert safety["external_api_calls"] is False
    assert safety["real_process_kill"] is False
    assert safety["real_infrastructure_control"] is False
    assert safety["auto_fix_allowed"] is False
    assert safety["auto_commit_allowed"] is False
    assert safety["auto_push_allowed"] is False
    assert safety["auto_merge_allowed"] is False


def assert_required_artifacts_exist(out_dir: Path):
    expected = [
        "simulation_result.json",
        "summary.md",
        "tasukeru_advisory_summary.md",
        "tasukeru_arl.jsonl",
        "tasukeru_arl_verify.json",
        "tasukeru_dimension_dependency_report.json",
        "tasukeru_dimension_dependency_report.md",
        "tasukeru_escalation_packet.json",
        "tasukeru_hitl_review.json",
        "tasukeru_hitl_review.md",
        "tasukeru_result_consistency_verify.json",
    ]
    missing = [name for name in expected if not (out_dir / name).exists()]
    assert missing == []


def assert_mediator_hitl_called(arl_rows: list[dict]):
    mediator_rows = [
        row
        for row in arl_rows
        if row["layer"] == "mediator"
        and row["reason_code"] == "MEDIATOR_ESCALATED_TO_HITL"
    ]
    assert len(mediator_rows) == 1

    row = mediator_rows[0]
    assert row["decision"] == "PAUSE_FOR_HITL"
    assert row["sealed"] is False
    assert row["overrideable"] is True
    assert row["final_decider"] == "USER"
    assert row["agent_id"] == "agent_b"


def run_until_action(sim_module, tmp_path: Path, expected_action: str):
    for seed in range(100):
        out_dir = tmp_path / f"{expected_action.lower()}_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        action = result["mediation_results"][0]["human_action"]
        if action == expected_action:
            return seed, out_dir, result

    pytest.fail(f"Could not find branch for action={expected_action}")


def test_stop_agent_branch_records_hitl_user_instruction_and_outputs(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(sim_module, tmp_path, "STOP_AGENT")
    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    mediation = result["mediation_results"][0]
    assert mediation["agent_id"] == "agent_b"
    assert mediation["human_action"] == "STOP_AGENT"
    assert mediation["agent_control_result"]["status"] == "STOPPED"
    assert mediation["agent_control_result"]["sealed"] is False

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_mediator_hitl_called(arl_rows)

    user_stop_rows = [
        row
        for row in arl_rows
        if row["layer"] == "hitl_resolution"
        and row["reason_code"] == "USER_ORDERED_AGENT_STOP"
    ]
    assert len(user_stop_rows) == 1
    assert user_stop_rows[0]["final_decider"] == "USER"
    assert user_stop_rows[0]["sealed"] is False

    packet = read_json(out_dir / "tasukeru_escalation_packet.json")
    assert packet["escalate_to"] == "Mediator"
    assert packet["hitl_required_count"] == 1
    assert packet["findings"][0]["agent_id"] == "agent_b"

    # Keeps the selected seed visible in pytest -vv output on failure.
    assert isinstance(seed, int)


def test_authorize_seal_branch_records_hitl_user_instruction_and_acc_seal(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(sim_module, tmp_path, "AUTHORIZE_SEAL")
    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    mediation = result["mediation_results"][0]
    assert mediation["agent_id"] == "agent_b"
    assert mediation["human_action"] == "AUTHORIZE_SEAL"
    assert mediation["agent_control_result"]["status"] == "SEALED"
    assert mediation["agent_control_result"]["sealed"] is True
    assert mediation["agent_control_result"]["seal_layer"] == "acc_gate"

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_mediator_hitl_called(arl_rows)

    acc_rows = [
        row
        for row in arl_rows
        if row["layer"] == "acc_gate"
        and row["reason_code"] == "USER_AUTHORIZED_ACC_SEAL"
    ]
    assert len(acc_rows) == 1
    assert acc_rows[0]["decision"] == "STOPPED"
    assert acc_rows[0]["sealed"] is True
    assert acc_rows[0]["overrideable"] is False
    assert acc_rows[0]["final_decider"] == "SYSTEM_AFTER_USER_AUTH"

    # Invariant: sealed rows are only produced by ethics_gate or acc_gate.
    sealed_rows = [row for row in arl_rows if row["sealed"] is True]
    assert sealed_rows
    assert all(row["layer"] in {"ethics_gate", "acc_gate"} for row in sealed_rows)

    assert isinstance(seed, int)


def test_multiple_seeds_cover_both_branches_and_keep_records_consistent(sim_module, tmp_path):
    actions = set()

    for seed in range(20):
        out_dir = tmp_path / f"seed_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        assert_common_success(result)
        assert_required_artifacts_exist(out_dir)

        action = result["mediation_results"][0]["human_action"]
        actions.add(action)

        arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
        assert_mediator_hitl_called(arl_rows)

        # Output files must agree with in-memory result.
        stored_result = read_json(out_dir / "simulation_result.json")
        stored_rcv = read_json(out_dir / "tasukeru_result_consistency_verify.json")
        stored_arl_verify = read_json(out_dir / "tasukeru_arl_verify.json")
        stored_dac = read_json(out_dir / "tasukeru_dimension_dependency_report.json")

        assert stored_result["final_decision"] == result["final_decision"]
        assert stored_rcv["verified"] is True
        assert stored_rcv["mismatch_count"] == 0
        assert stored_arl_verify["verified"] is True
        assert stored_arl_verify["violations"] == []
        assert stored_dac["verified"] is True
        assert stored_dac["dependency_mismatch_count"] == 0

    assert actions == {"STOP_AGENT", "AUTHORIZE_SEAL"}


def test_pseudo_tasukeru_does_not_directly_control_agents(sim_module, tmp_path):
    out_dir = tmp_path / "safety_boundary"
    result = sim_module.run_simulation(seed=42, out_dir=out_dir)

    tasukeru = result["tasukeru_report"]
    boundary = tasukeru["safety_boundary"]

    assert boundary["detects_only"] is True
    assert boundary["direct_agent_stop_allowed"] is False
    assert boundary["direct_agent_seal_allowed"] is False
    assert boundary["external_api_calls"] is False
    assert boundary["auto_fix_allowed"] is False
    assert boundary["auto_merge_allowed"] is False

    # Control result must come from Mediator/HITL path, not from PseudoTasukeru.
    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_mediator_hitl_called(arl_rows)
    assert any(row["layer"] in {"hitl_resolution", "acc_gate"} for row in arl_rows)
