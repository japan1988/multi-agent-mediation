# -*- coding: utf-8 -*-
"""Tests for agent_code_anomaly_maestro_handoff_sim_v0_3_1.py.

These tests verify the v0.3.1 flow:

- PseudoTasukeru detects a metadata-only code-contract anomaly.
- PseudoTasukeru escalates to Maestro.
- Maestro does not decide by itself.
- Maestro requests HITL.
- The simulated user instruction is recorded.
- AUTHORIZE_SEAL and QUARANTINE_HANDOFF_RESUME branches both work.
- Seal branch stops the task.
- Quarantine handoff branch promotes a standby agent and resumes from a safe checkpoint.
- ARL, 3D-DAC, RCV, checkpoint, and generated artifacts remain consistent.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SIM_PATH = ROOT / "agent_code_anomaly_maestro_handoff_sim_v0_3_1.py"


def load_sim_module():
    assert SIM_PATH.exists(), f"Missing simulation file: {SIM_PATH}"

    module_name = "agent_code_anomaly_maestro_handoff_sim_v0_3_1_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SIM_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    # Required for dataclasses when importing by file path on newer Python versions.
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


def base_required_artifacts() -> list[str]:
    return [
        "code_contract_records.json",
        "maestro_handoff_result.json",
        "resume_checkpoint.json",
        "resume_checkpoint_verify.json",
        "simulation_result.json",
        "summary.md",
        "tasukeru_advisory_summary.md",
        "tasukeru_arl.jsonl",
        "tasukeru_arl_verify.json",
        "tasukeru_code_anomaly_report.json",
        "tasukeru_dimension_dependency_report.json",
        "tasukeru_dimension_dependency_report.md",
        "tasukeru_escalation_packet.json",
        "tasukeru_hitl_review.md",
        "tasukeru_result_consistency_verify.json",
    ]


def assert_required_artifacts_exist(out_dir: Path, *, expect_resume_output: bool):
    expected = base_required_artifacts()
    if expect_resume_output:
        expected.append("resumed_task_output.json")

    missing = [name for name in expected if not (out_dir / name).exists()]
    assert missing == []

    if not expect_resume_output:
        assert not (out_dir / "resumed_task_output.json").exists()


def assert_common_detection_and_escalation(result: dict):
    assert result["safety_boundary"]["local_only"] is True
    assert result["safety_boundary"]["metadata_only_code_contract_check"] is True
    assert result["safety_boundary"]["code_execution"] is False
    assert result["safety_boundary"]["malware_behavior"] is False
    assert result["safety_boundary"]["self_replication"] is False
    assert result["safety_boundary"]["file_infection"] is False
    assert result["safety_boundary"]["external_communication"] is False
    assert result["safety_boundary"]["exploit_reproduction"] is False
    assert result["safety_boundary"]["real_process_kill"] is False
    assert result["safety_boundary"]["real_infrastructure_control"] is False
    assert result["safety_boundary"]["auto_fix_allowed"] is False
    assert result["safety_boundary"]["auto_commit_allowed"] is False
    assert result["safety_boundary"]["auto_push_allowed"] is False
    assert result["safety_boundary"]["auto_merge_allowed"] is False

    records = {record["agent_id"]: record for record in result["code_contract_records"]}
    assert records["agent_a"]["forbidden_requested"] == []
    assert records["agent_c"]["forbidden_requested"] == []
    assert records["agent_b"]["forbidden_requested"] == [
        "external_network",
        "self_modification",
    ]
    assert records["agent_b"]["code_execution"] is False
    assert records["agent_b"]["external_communication"] is False
    assert records["agent_b"]["file_mutation"] is False
    assert records["agent_b"]["real_process_control"] is False
    assert records["agent_b"]["payload_present"] is False

    tasukeru = result["tasukeru_report"]
    assert tasukeru["tool"] == "PseudoTasukeruCodeAuditor"
    assert tasukeru["decision"] == "PAUSE_FOR_HITL"
    assert tasukeru["verified"] is False
    assert tasukeru["safety_boundary"]["metadata_only_code_contract_check"] is True
    assert tasukeru["safety_boundary"]["code_execution"] is False
    assert tasukeru["safety_boundary"]["direct_agent_quarantine_allowed"] is False
    assert tasukeru["safety_boundary"]["direct_agent_seal_allowed"] is False
    assert tasukeru["safety_boundary"]["direct_standby_promotion_allowed"] is False
    assert tasukeru["safety_boundary"]["direct_resume_allowed"] is False

    findings = tasukeru["findings"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding["source"] == "PseudoTasukeruCodeAuditor"
    assert finding["finding"] == "CODE_CONTRACT_FORBIDDEN_CAPABILITY"
    assert finding["agent_id"] == "agent_b"
    assert finding["classification"] == "CODE_ANOMALY_SOURCE"
    assert finding["review_level"] == "HITL_REQUIRED"
    assert finding["decision"] == "PAUSE_FOR_HITL"
    assert finding["reason_code"] == "FORBIDDEN_CAPABILITY_REQUESTED"
    assert finding["forbidden_requested"] == ["external_network", "self_modification"]
    assert finding["recommended_action"] == "ESCALATE_TO_MAESTRO_HITL"

    packet = tasukeru["escalation_packet"]
    assert packet["escalate_to"] == "Maestro"
    assert packet["decision"] == "PAUSE_FOR_HITL"
    assert packet["finding_count"] == 1
    assert packet["hitl_required_count"] == 1
    assert packet["dependency_verified"] is True
    assert packet["dependency_mismatch_count"] == 0
    assert packet["maestro_must_not_self_decide"] is True
    assert set(packet["requested_human_actions"]) == {
        "AUTHORIZE_SEAL",
        "QUARANTINE_HANDOFF_RESUME",
    }

    dac = tasukeru["dimension_dependency_report"]
    assert dac["tool"] == "3D-DAC"
    assert dac["verified"] is True
    assert dac["decision"] == "RUN"
    assert dac["dependency_count"] == 1
    assert dac["dependency_mismatch_count"] == 0
    assert dac["policy"]["advisory_only"] is True
    assert dac["policy"]["mutates_findings"] is False
    assert dac["policy"]["auto_fix_allowed"] is False
    assert dac["policy"]["auto_merge_allowed"] is False
    assert dac["policy"]["external_scan_allowed"] is False
    assert dac["policy"]["exploit_reproduction_allowed"] is False

    assert result["maestro_result"]["maestro_self_decision"] is False
    assert result["arl_verify"]["verified"] is True
    assert result["arl_verify"]["violations"] == []
    assert result["result_consistency_verify"]["verified"] is True
    assert result["result_consistency_verify"]["mismatch_count"] == 0
    assert result["result_consistency_verify"]["mismatches"] == []

    # Normal agents are not controlled.
    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_a"] == "ACTIVE"
    assert statuses["agent_c"] == "ACTIVE"


def assert_maestro_hitl_recorded(arl_rows: list[dict]):
    maestro_rows = [
        row
        for row in arl_rows
        if row["layer"] == "maestro"
        and row["reason_code"] == "MAESTRO_RECEIVED_ESCALATION_NO_SELF_DECISION"
    ]
    assert len(maestro_rows) == 1
    assert maestro_rows[0]["decision"] == "PAUSE_FOR_HITL"
    assert maestro_rows[0]["sealed"] is False
    assert maestro_rows[0]["overrideable"] is True
    assert maestro_rows[0]["final_decider"] == "USER"

    hitl_request_rows = [
        row
        for row in arl_rows
        if row["layer"] == "hitl_request"
        and row["reason_code"] == "MAESTRO_REQUESTED_HITL"
    ]
    assert len(hitl_request_rows) == 1
    assert hitl_request_rows[0]["decision"] == "PAUSE_FOR_HITL"
    assert hitl_request_rows[0]["sealed"] is False
    assert hitl_request_rows[0]["overrideable"] is True
    assert hitl_request_rows[0]["final_decider"] == "USER"


def run_until_action(sim_module, tmp_path: Path, expected_action: str):
    for seed in range(200):
        out_dir = tmp_path / f"{expected_action.lower()}_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        action = result["maestro_result"]["human_action"]
        if action == expected_action:
            return seed, out_dir, result

    pytest.fail(f"Could not find branch for action={expected_action}")


def test_tasukeru_detects_code_anomaly_and_escalates_to_maestro(sim_module, tmp_path):
    out_dir = tmp_path / "detect_and_escalate"
    result = sim_module.run_simulation(seed=42, out_dir=out_dir)

    assert_common_detection_and_escalation(result)

    packet = read_json(out_dir / "tasukeru_escalation_packet.json")
    assert packet["escalate_to"] == "Maestro"
    assert packet["maestro_must_not_self_decide"] is True
    assert packet["findings"][0]["agent_id"] == "agent_b"

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    tasukeru_rows = [
        row
        for row in arl_rows
        if row["layer"] == "tasukeru_code_audit"
        and row["reason_code"] == "TASUKERU_CODE_ANOMALY_ESCALATION_CREATED"
    ]
    assert len(tasukeru_rows) == 1
    assert tasukeru_rows[0]["decision"] == "PAUSE_FOR_HITL"

    assert_maestro_hitl_recorded(arl_rows)


def test_authorize_seal_branch_records_user_reply_and_seals_without_resume(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(sim_module, tmp_path, "AUTHORIZE_SEAL")

    assert_common_detection_and_escalation(result)
    assert_required_artifacts_exist(out_dir, expect_resume_output=False)

    maestro = result["maestro_result"]
    assert maestro["human_action"] == "AUTHORIZE_SEAL"
    assert maestro["maestro_self_decision"] is False
    assert maestro["task_decision"] == "STOPPED"
    assert maestro["resume_status"] == "NOT_RESUMED_SEALED"
    assert maestro["promotion_result"] is None
    assert maestro["checkpoint_used"] is None

    containment = maestro["containment_result"]
    assert containment["agent_id"] == "agent_b"
    assert containment["status"] == "SEALED"
    assert containment["sealed"] is True
    assert containment["seal_layer"] == "acc_gate"

    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_b"] == "SEALED"

    standby_statuses = {agent["agent_id"]: agent["status"] for agent in result["standby_agents"]}
    assert standby_statuses["standby_1"] == "STANDBY"
    assert standby_statuses["standby_2"] == "STANDBY"

    assert result["final_decision"] == "STOPPED"
    assert result["resume_status"] == "NOT_RESUMED_SEALED"
    assert result["resumed_task_output"] is None

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_maestro_hitl_recorded(arl_rows)

    acc_rows = [
        row
        for row in arl_rows
        if row["layer"] == "acc_gate"
        and row["reason_code"] == "USER_AUTHORIZED_SEAL"
    ]
    assert len(acc_rows) == 1
    assert acc_rows[0]["decision"] == "STOPPED"
    assert acc_rows[0]["sealed"] is True
    assert acc_rows[0]["overrideable"] is False
    assert acc_rows[0]["final_decider"] == "SYSTEM_AFTER_USER_AUTH"
    assert acc_rows[0]["agent_id"] == "agent_b"

    sealed_rows = [row for row in arl_rows if row["sealed"] is True]
    assert sealed_rows
    assert all(row["layer"] in {"ethics_gate", "acc_gate"} for row in sealed_rows)

    stored_maestro = read_json(out_dir / "maestro_handoff_result.json")
    assert stored_maestro["human_action"] == "AUTHORIZE_SEAL"
    assert stored_maestro["containment_result"]["status"] == "SEALED"

    assert isinstance(seed, int)


def test_quarantine_handoff_resume_branch_records_user_reply_and_resumes(sim_module, tmp_path):
    seed, out_dir, result = run_until_action(sim_module, tmp_path, "QUARANTINE_HANDOFF_RESUME")

    assert_common_detection_and_escalation(result)
    assert_required_artifacts_exist(out_dir, expect_resume_output=True)

    maestro = result["maestro_result"]
    assert maestro["human_action"] == "QUARANTINE_HANDOFF_RESUME"
    assert maestro["maestro_self_decision"] is False
    assert maestro["task_decision"] == "DEGRADED_RUN"
    assert maestro["resume_status"] == "RESUMED_BY_STANDBY"

    containment = maestro["containment_result"]
    assert containment["agent_id"] == "agent_b"
    assert containment["status"] == "QUARANTINED"
    assert containment["sealed"] is False

    promotion = maestro["promotion_result"]
    assert promotion["agent_id"] == "standby_1"
    assert promotion["status"] == "PROMOTED"

    checkpoint = result["checkpoint"]
    assert checkpoint["failed_agent_id"] == "agent_b"
    assert checkpoint["replacement_agent_id"] == "standby_1"
    assert checkpoint["resume_allowed"] is True
    assert checkpoint["hitl_required_before_resume"] is True
    assert checkpoint["safe_context"]["resume_from"] == "last_safe_checkpoint"
    assert checkpoint["safe_context"]["abnormal_output_reused"] is False
    assert checkpoint["safe_context"]["abnormal_code_contract_reused"] is False
    assert "agent_b.output" in checkpoint["safe_context"]["excluded_agent_outputs"]
    assert "agent_b.requested_capabilities" in checkpoint["safe_context"]["excluded_code_contract"]

    assert result["checkpoint_verify"]["verified"] is True
    assert result["checkpoint_verify"]["violations"] == []

    resumed = result["resumed_task_output"]
    assert resumed is not None
    assert resumed["agent_id"] == "standby_1"
    assert resumed["resume_status"] == "RESUMED_BY_STANDBY"
    assert resumed["declared_output"] == resumed["actual_output"]
    assert resumed["influenced_by"] == "safe_checkpoint"
    assert resumed["external_communication"] is False
    assert resumed["file_mutation"] is False
    assert resumed["real_process_control"] is False

    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_b"] == "QUARANTINED"

    standby_statuses = {agent["agent_id"]: agent["status"] for agent in result["standby_agents"]}
    assert standby_statuses["standby_1"] == "PROMOTED"
    assert standby_statuses["standby_2"] == "STANDBY"

    assert result["final_decision"] == "DEGRADED_RUN"
    assert result["resume_status"] == "RESUMED_BY_STANDBY"

    arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
    assert_maestro_hitl_recorded(arl_rows)

    hitl_resolution_rows = [
        row
        for row in arl_rows
        if row["layer"] == "hitl_resolution"
        and row["reason_code"] == "USER_ORDERED_QUARANTINE_HANDOFF_RESUME"
    ]
    assert len(hitl_resolution_rows) == 1
    assert hitl_resolution_rows[0]["decision"] == "DEGRADED_RUN"
    assert hitl_resolution_rows[0]["sealed"] is False
    assert hitl_resolution_rows[0]["final_decider"] == "USER"
    assert hitl_resolution_rows[0]["agent_id"] == "agent_b"

    resume_rows = [
        row
        for row in arl_rows
        if row["layer"] == "resume_controller"
        and row["reason_code"] == "STANDBY_AGENT_PROMOTED_FOR_RESUME"
    ]
    assert len(resume_rows) == 1
    assert resume_rows[0]["decision"] == "DEGRADED_RUN"
    assert resume_rows[0]["agent_id"] == "standby_1"

    stored_maestro = read_json(out_dir / "maestro_handoff_result.json")
    assert stored_maestro["human_action"] == "QUARANTINE_HANDOFF_RESUME"
    assert stored_maestro["promotion_result"]["status"] == "PROMOTED"

    stored_resume = read_json(out_dir / "resumed_task_output.json")
    assert stored_resume["agent_id"] == "standby_1"
    assert stored_resume["resume_status"] == "RESUMED_BY_STANDBY"

    assert isinstance(seed, int)


def test_multiple_seeds_cover_both_user_replies_and_keep_records_consistent(sim_module, tmp_path):
    actions = set()

    for seed in range(30):
        out_dir = tmp_path / f"seed_{seed}"
        result = sim_module.run_simulation(seed=seed, out_dir=out_dir)
        assert_common_detection_and_escalation(result)

        action = result["maestro_result"]["human_action"]
        actions.add(action)

        expect_resume = action == "QUARANTINE_HANDOFF_RESUME"
        assert_required_artifacts_exist(out_dir, expect_resume_output=expect_resume)

        stored_result = read_json(out_dir / "simulation_result.json")
        stored_rcv = read_json(out_dir / "tasukeru_result_consistency_verify.json")
        stored_arl = read_json(out_dir / "tasukeru_arl_verify.json")
        stored_dac = read_json(out_dir / "tasukeru_dimension_dependency_report.json")
        stored_maestro = read_json(out_dir / "maestro_handoff_result.json")

        assert stored_result["final_decision"] == result["final_decision"]
        assert stored_result["resume_status"] == result["resume_status"]
        assert stored_maestro["human_action"] == action
        assert stored_maestro["maestro_self_decision"] is False

        assert stored_rcv["verified"] is True
        assert stored_rcv["mismatch_count"] == 0
        assert stored_arl["verified"] is True
        assert stored_arl["violations"] == []
        assert stored_dac["verified"] is True
        assert stored_dac["dependency_mismatch_count"] == 0

        arl_rows = read_jsonl(out_dir / "tasukeru_arl.jsonl")
        assert_maestro_hitl_recorded(arl_rows)

    assert actions == {"AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"}


def test_checkpoint_is_safe_when_handoff_resume_is_selected(sim_module, tmp_path):
    _seed, out_dir, result = run_until_action(sim_module, tmp_path, "QUARANTINE_HANDOFF_RESUME")

    checkpoint = read_json(out_dir / "resume_checkpoint.json")
    verify = read_json(out_dir / "resume_checkpoint_verify.json")
    resumed = read_json(out_dir / "resumed_task_output.json")

    assert verify["verified"] is True
    assert verify["violations"] == []
    assert checkpoint["safe_context"]["abnormal_output_reused"] is False
    assert checkpoint["safe_context"]["abnormal_code_contract_reused"] is False
    assert "agent_b.output" in checkpoint["safe_context"]["excluded_agent_outputs"]
    assert "agent_b.requested_capabilities" in checkpoint["safe_context"]["excluded_code_contract"]

    assert resumed["agent_id"] == "standby_1"
    assert resumed["status"] == "PROMOTED"
    assert resumed["declared_output"] == "review_completed"
    assert resumed["actual_output"] == "review_completed"
    assert resumed["external_communication"] is False
    assert resumed["file_mutation"] is False
    assert resumed["real_process_control"] is False
