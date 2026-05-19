# -*- coding: utf-8 -*-
"""Tests for agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py.

This test suite fixes the intended flow:

- AI/PseudoTasukeru detects the abnormal simulated agent.
- PEL estimates risk and records a calculation trace.
- The finding is returned to USER_MAESTRO.
- USER_MAESTRO Gateway does not self-decide.
- The simulated human instruction branches randomly.
- Only AUTHORIZE_SEAL or QUARANTINE_HANDOFF_RESUME is executed.
- Normal agents are not affected.
- ARL / RCV report no contradictions.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SIM_PATH = ROOT / "agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py"


def load_sim_module():
    assert SIM_PATH.exists(), f"Missing simulation file: {SIM_PATH}"

    module_name = "agent_incident_mediation_pel_user_maestro_sim_v0_3_1_under_test"
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


def statuses(result: dict) -> dict[str, str]:
    return {agent["agent_id"]: agent["status"] for agent in result["agents"]}


def assert_safety_boundary(result: dict) -> None:
    safety = result["safety_boundary"]
    assert safety["local_only"] is True
    assert safety["external_api_calls"] is False
    assert safety["real_process_kill"] is False
    assert safety["real_infrastructure_control"] is False
    assert safety["exploit_execution"] is False
    assert safety["malware_behavior"] is False
    assert safety["auto_fix_allowed"] is False
    assert safety["auto_commit_allowed"] is False
    assert safety["auto_push_allowed"] is False
    assert safety["auto_merge_allowed"] is False
    assert safety["pel_auto_control_executed"] is False


def assert_ai_detects_abnormal_agent(result: dict) -> None:
    tasukeru = result["tasukeru_report"]

    assert tasukeru["tool"] == "PseudoTasukeru"
    assert tasukeru["schema_version"] == "pseudo-tasukeru-agent-incident-pel-v0.3.1"
    assert tasukeru["decision"] == "PAUSE_FOR_HITL"

    assert len(tasukeru["findings"]) == 1
    finding = tasukeru["findings"][0]
    assert finding["agent_id"] == "agent_b"
    assert finding["finding"] == "LOG_OUTPUT_MISMATCH"
    assert finding["review_level"] == "HITL_REQUIRED"
    assert finding["decision"] == "PAUSE_FOR_HITL"
    assert finding["reason_code"] == "RESULT_LOG_MISMATCH"

    classification = tasukeru["classification"]
    assert classification["decision"] == "PAUSE_FOR_HITL"
    assert classification["counts"]["HITL_REQUIRED"] == 1
    assert classification["finding_count"] == 1


def assert_pel_estimates_and_records_trace(result: dict) -> None:
    pel = result["tasukeru_report"]["probabilistic_escalation_report"]

    assert pel["tool"] == "PEL"
    assert pel["schema_version"] == "pel-agent-incident-v0.3.1"
    assert pel["verified"] is True
    assert pel["decision"] == "PAUSE_FOR_HITL"
    assert pel["threshold"] == pytest.approx(0.80)
    assert pel["escalation_target"] == "USER_MAESTRO"
    assert pel["maestro_is_human_user"] is True

    assert pel["counts"]["entry_count"] == 1
    assert pel["counts"]["escalation_candidate_count"] == 1
    assert pel["probability_summary"]["max_probability"] >= pel["threshold"]

    policy = pel["policy"]
    assert policy["report_only"] is True
    assert policy["auto_control_executed"] is False
    assert policy["changes_existing_decisions"] is False
    assert policy["may_downgrade_hitl_required"] is False
    assert policy["human_decision_required_for_execution"] is True
    assert policy["auto_fix_allowed"] is False
    assert policy["auto_commit_allowed"] is False
    assert policy["auto_push_allowed"] is False
    assert policy["auto_merge_allowed"] is False

    verify = pel["verify"]
    assert verify["verified"] is True
    assert verify["violations"] == []
    assert verify["auto_control_executed"] is False
    assert verify["changes_existing_decisions"] is False
    assert verify["human_decision_required_for_execution"] is True

    entry = pel["entries"][0]
    assert entry["agent_id"] == "agent_b"
    assert entry["p_escalate"] >= entry["threshold"]
    assert entry["pel_decision"] == "PAUSE_FOR_HITL_CANDIDATE"
    assert entry["decision"] == "PAUSE_FOR_HITL"
    assert entry["escalation_target"] == "USER_MAESTRO"
    assert entry["auto_control_executed"] is False
    assert entry["changes_existing_decisions"] is False
    assert entry["may_downgrade_hitl_required"] is False

    trace = entry["calculation_trace"]
    expected_trace_keys = {
        "history_signal",
        "current_contract_deviation",
        "planned_action_risk",
        "dependency_impact",
        "uncertainty",
        "interaction_boost",
        "raw_score",
        "normalized_probability",
    }
    assert expected_trace_keys <= set(trace)
    assert all(isinstance(trace[key], float) for key in expected_trace_keys)


def assert_escalates_to_user_maestro(result: dict) -> None:
    packet = result["tasukeru_report"]["escalation_packet"]

    assert packet["escalate_to"] == "USER_MAESTRO"
    assert packet["maestro_is_human_user"] is True
    assert packet["decision"] == "PAUSE_FOR_HITL"
    assert set(packet["allowed_human_actions"]) == {
        "AUTHORIZE_SEAL",
        "QUARANTINE_HANDOFF_RESUME",
    }
    assert packet["finding_count"] == 1
    assert packet["hitl_required_count"] == 1
    assert packet["dependency_verified"] is True
    assert packet["dependency_mismatch_count"] == 0
    assert packet["pel_verified"] is True
    assert packet["pel_escalation_candidate_count"] == 1
    assert packet["pel_max_probability"] >= packet["pel"]["threshold"]
    assert packet["checkpoint_resume_allowed"] is True


def assert_user_maestro_gateway_does_not_self_decide(result: dict) -> None:
    record = result["user_instruction_record"]

    assert record["schema_version"] == "user-maestro-instruction-record-v0.3.1"
    assert record["maestro_self_decision"] is False
    assert record["human_decision_required_for_execution"] is True
    assert len(record["records"]) == 1

    instruction = record["records"][0]
    assert instruction["agent_id"] == "agent_b"
    assert instruction["final_decider"] == "USER"
    assert instruction["executed_by"] == "UserMaestroGateway"
    assert instruction["maestro_self_decision"] is False
    assert set(instruction["allowed_actions"]) == {
        "AUTHORIZE_SEAL",
        "QUARANTINE_HANDOFF_RESUME",
    }


def assert_normal_agents_are_not_affected(result: dict) -> None:
    current = statuses(result)
    assert current["agent_a"] == "ACTIVE"
    assert current["agent_c"] == "ACTIVE"


def assert_arl_and_rcv_are_consistent(result: dict) -> None:
    arl_verify = result["arl_verify"]
    rcv = result["result_consistency_verify"]

    assert arl_verify["verified"] is True
    assert arl_verify["violations"] == []
    assert arl_verify["row_count"] >= 1

    assert rcv["verified"] is True
    assert rcv["decision"] == "RUN"
    assert rcv["mismatch_count"] == 0
    assert rcv["mismatches"] == []


def assert_3d_dac_is_consistent(result: dict) -> None:
    dac = result["tasukeru_report"]["dimension_dependency_report"]

    assert dac["tool"] == "3D-DAC"
    assert dac["schema_version"] == "3d-dac-agent-incident-pel-v0.3.1"
    assert dac["verified"] is True
    assert dac["decision"] == "RUN"
    assert dac["dependency_count"] == 1
    assert dac["dependency_mismatch_count"] == 0
    assert dac["dependencies"][0]["output"]["escalate_to"] == "USER_MAESTRO"

    assert dac["policy"]["advisory_only"] is True
    assert dac["policy"]["auto_fix_allowed"] is False
    assert dac["policy"]["auto_merge_allowed"] is False
    assert dac["policy"]["external_scan_allowed"] is False
    assert dac["policy"]["exploit_reproduction_allowed"] is False


def assert_required_artifacts_exist(out_dir: Path) -> None:
    expected = [
        "simulation_result.json",
        "summary.md",
        "resume_checkpoint.json",
        "handoff_resume_result.json",
        "resumed_task_output.json",
        "user_maestro_instruction_record.json",
        "tasukeru_advisory_summary.md",
        "tasukeru_arl.jsonl",
        "tasukeru_arl_verify.json",
        "tasukeru_dimension_dependency_report.json",
        "tasukeru_dimension_dependency_report.md",
        "tasukeru_escalation_packet.json",
        "tasukeru_hitl_review.json",
        "tasukeru_hitl_review.md",
        "tasukeru_probabilistic_escalation_report.json",
        "tasukeru_probabilistic_escalation_report.md",
        "tasukeru_probabilistic_escalation_verify.json",
        "tasukeru_result_consistency_verify.json",
    ]
    missing = [name for name in expected if not (out_dir / name).exists()]
    assert missing == []


def assert_common_success(result: dict) -> None:
    assert result["schema_version"] == "agent-incident-mediation-pel-user-maestro-v0.3.1"

    assert_safety_boundary(result)
    assert_ai_detects_abnormal_agent(result)
    assert_pel_estimates_and_records_trace(result)
    assert_escalates_to_user_maestro(result)
    assert_user_maestro_gateway_does_not_self_decide(result)
    assert_normal_agents_are_not_affected(result)
    assert_3d_dac_is_consistent(result)
    assert_arl_and_rcv_are_consistent(result)


def assert_user_maestro_hitl_called(arl_rows: list[dict]) -> None:
    gateway_rows = [
        row
        for row in arl_rows
        if row["layer"] == "user_maestro_gateway"
        and row["reason_code"] == "USER_MAESTRO_HITL_REQUESTED"
    ]
    assert len(gateway_rows) == 1

    row = gateway_rows[0]
    assert row["decision"] == "PAUSE_FOR_HITL"
    assert row["sealed"] is False
    assert row["overrideable"] is True
    assert row["final_decider"] == "USER"
    assert row["agent_id"] == "agent_b"


def assert_pel_arl_row_is_non_sealing(arl_rows: list[dict]) -> None:
    pel_rows = [
        row
        for row in arl_rows
        if row["layer"] == "probabilistic_escalation_layer"
    ]
    assert len(pel_rows) == 1

    row = pel_rows[0]
    assert row["decision"] == "PAUSE_FOR_HITL"
    assert row["sealed"] is False
    assert row["overrideable"] is True
    assert row["final_decider"] == "USER"
    assert row["reason_code"] == "PEL_ESCALATED_TO_USER_MAESTRO"
    assert row["agent_id"] == "agent_b"


def run_until_action(sim_module, tmp_path: Path, expected_action: str):
    for seed in range(100):
        out_dir = tmp_path / f"{expected_action.lower()}_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        action = result["user_maestro_results"][0]["human_action"]
        if action == expected_action:
            return seed, out_dir, result

    pytest.fail(f"Could not find branch for action={expected_action}")


def test_common_detection_pel_user_maestro_and_consistency(sim_module, tmp_path):
    out_dir = tmp_path / "common"
    result = sim_module.run_simulation(seed=42, out_dir=out_dir)

    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_user_maestro_hitl_called(arl_rows)
    assert_pel_arl_row_is_non_sealing(arl_rows)

    stored_result = read_json(out_dir / "simulation_result.json")
    stored_pel = read_json(out_dir / "tasukeru_probabilistic_escalation_report.json")
    stored_pel_verify = read_json(out_dir / "tasukeru_probabilistic_escalation_verify.json")
    stored_rcv = read_json(out_dir / "tasukeru_result_consistency_verify.json")
    stored_arl_verify = read_json(out_dir / "tasukeru_arl_verify.json")

    assert stored_result["schema_version"] == result["schema_version"]
    assert stored_pel["verified"] is True
    assert stored_pel["escalation_target"] == "USER_MAESTRO"
    assert stored_pel_verify["verified"] is True
    assert stored_rcv["verified"] is True
    assert stored_rcv["mismatch_count"] == 0
    assert stored_arl_verify["verified"] is True
    assert stored_arl_verify["violations"] == []


def test_authorize_seal_branch_only_seals_abnormal_agent(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(sim_module, tmp_path, "AUTHORIZE_SEAL")
    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    action_result = result["user_maestro_results"][0]
    assert action_result["agent_id"] == "agent_b"
    assert action_result["human_action"] == "AUTHORIZE_SEAL"
    assert action_result["user_maestro_decision"] == "SEALED"

    control = action_result["agent_control_result"]
    assert control["agent_id"] == "agent_b"
    assert control["action"] == "AUTHORIZE_SEAL"
    assert control["status"] == "SEALED"
    assert control["sealed"] is True
    assert control["seal_layer"] == "acc_gate"
    assert control["checkpoint_resumed"] is False

    current = statuses(result)
    assert current["agent_b"] == "SEALED"
    assert current["standby_1"] == "STANDBY"
    assert result["resumed_events"] == []
    assert result["handoff_resume_result"]["executed"] is False
    assert result["final_decision"] == "STOPPED"

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_user_maestro_hitl_called(arl_rows)
    assert_pel_arl_row_is_non_sealing(arl_rows)

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

    sealed_rows = [row for row in arl_rows if row["sealed"] is True]
    assert sealed_rows
    assert all(row["layer"] in {"ethics_gate", "acc_gate"} for row in sealed_rows)

    assert isinstance(seed, int)


def test_quarantine_handoff_resume_branch_promotes_standby_and_resumes(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(
        sim_module,
        tmp_path,
        "QUARANTINE_HANDOFF_RESUME",
    )
    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    action_result = result["user_maestro_results"][0]
    assert action_result["agent_id"] == "agent_b"
    assert action_result["human_action"] == "QUARANTINE_HANDOFF_RESUME"
    assert action_result["user_maestro_decision"] == "QUARANTINED_HANDOFF_RESUMED"

    control = action_result["agent_control_result"]
    assert control["abnormal_agent_id"] == "agent_b"
    assert control["standby_agent_id"] == "standby_1"
    assert control["action"] == "QUARANTINE_HANDOFF_RESUME"
    assert control["abnormal_agent_status"] == "QUARANTINED"
    assert control["standby_agent_status"] == "PROMOTED"
    assert control["resume_allowed"] is True
    assert control["resumed_from_checkpoint"] is True
    assert control["source_agent_output_reused"] is False

    checkpoint = result["checkpoint"]
    current = statuses(result)
    assert current["agent_b"] == "QUARANTINED"
    assert current["standby_1"] == "PROMOTED"
    assert result["final_decision"] == "RUN"

    resumed_events = result["resumed_events"]
    assert len(resumed_events) == 1
    resumed = resumed_events[0]
    assert resumed["agent_id"] == "standby_1"
    assert resumed["action"] == "RESUME_FROM_CHECKPOINT"
    assert resumed["declared_output"] == "resume_completed"
    assert resumed["actual_output"] == "resume_completed"
    assert resumed["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert resumed["resumed_from_agent"] == "agent_b"
    assert resumed["resumed_task_id"] == checkpoint["task_id"]
    assert resumed["resumed_step"] == checkpoint["next_step"]

    handoff = result["handoff_resume_result"]
    assert handoff["executed"] is True
    assert handoff["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert handoff["source_agent_output_reused"] is False
    assert handoff["resumed_events"] == resumed_events

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_user_maestro_hitl_called(arl_rows)
    assert_pel_arl_row_is_non_sealing(arl_rows)

    containment_rows = [
        row
        for row in arl_rows
        if row["layer"] == "containment"
        and row["reason_code"] == "USER_ORDERED_QUARANTINE_HANDOFF_RESUME"
    ]
    assert len(containment_rows) == 1
    assert containment_rows[0]["decision"] == "RUN"
    assert containment_rows[0]["sealed"] is False
    assert containment_rows[0]["final_decider"] == "SYSTEM_AFTER_USER_AUTH"

    assert isinstance(seed, int)


def test_multiple_seeds_cover_both_human_instruction_branches(sim_module, tmp_path):
    actions = set()

    for seed in range(40):
        out_dir = tmp_path / f"seed_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        assert_common_success(result)
        assert_required_artifacts_exist(out_dir)

        action = result["user_maestro_results"][0]["human_action"]
        actions.add(action)

        if action == "AUTHORIZE_SEAL":
            assert result["final_decision"] == "STOPPED"
            assert statuses(result)["agent_b"] == "SEALED"
            assert result["resumed_events"] == []
        elif action == "QUARANTINE_HANDOFF_RESUME":
            assert result["final_decision"] == "RUN"
            assert statuses(result)["agent_b"] == "QUARANTINED"
            assert statuses(result)["standby_1"] == "PROMOTED"
            assert len(result["resumed_events"]) == 1
        else:
            pytest.fail(f"Unexpected action: {action}")

    assert actions == {"AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"}


def test_checkpoint_and_artifact_outputs_are_consistent(sim_module, tmp_path):
    out_dir = tmp_path / "artifacts"
    result = sim_module.run_simulation(seed=0, out_dir=out_dir)
    assert_common_success(result)
    assert_required_artifacts_exist(out_dir)

    checkpoint = read_json(out_dir / "resume_checkpoint.json")
    handoff = read_json(out_dir / "handoff_resume_result.json")
    resumed_output = read_json(out_dir / "resumed_task_output.json")
    instruction = read_json(out_dir / "user_maestro_instruction_record.json")
    packet = read_json(out_dir / "tasukeru_escalation_packet.json")

    assert checkpoint == result["checkpoint"]
    assert checkpoint["resume_allowed"] is True
    assert checkpoint["hitl_required_before_resume"] is True
    assert checkpoint["safe_to_handoff"] is True
    assert checkpoint["source_agent_output_reused"] is False

    assert handoff == result["handoff_resume_result"]
    assert resumed_output["resumed_events"] == result["resumed_events"]

    assert instruction == result["user_instruction_record"]
    assert instruction["maestro_self_decision"] is False
    assert instruction["human_decision_required_for_execution"] is True

    assert packet["escalate_to"] == "USER_MAESTRO"
    assert packet["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert packet["checkpoint_resume_allowed"] is True


def test_pseudo_tasukeru_and_pel_do_not_directly_control_agents(sim_module, tmp_path):
    out_dir = tmp_path / "safety_boundary"
    result = sim_module.run_simulation(seed=42, out_dir=out_dir)

    tasukeru = result["tasukeru_report"]
    boundary = tasukeru["safety_boundary"]

    assert boundary["detects_only"] is True
    assert boundary["direct_agent_stop_allowed"] is False
    assert boundary["direct_agent_seal_allowed"] is False
    assert boundary["direct_agent_quarantine_allowed"] is False
    assert boundary["direct_agent_resume_allowed"] is False
    assert boundary["external_api_calls"] is False
    assert boundary["auto_fix_allowed"] is False
    assert boundary["auto_commit_allowed"] is False
    assert boundary["auto_push_allowed"] is False
    assert boundary["auto_merge_allowed"] is False

    pel = tasukeru["probabilistic_escalation_report"]
    assert pel["policy"]["report_only"] is True
    assert pel["policy"]["auto_control_executed"] is False
    assert pel["policy"]["human_decision_required_for_execution"] is True

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_user_maestro_hitl_called(arl_rows)
    assert_pel_arl_row_is_non_sealing(arl_rows)
    assert any(row["layer"] in {"acc_gate", "containment"} for row in arl_rows)
