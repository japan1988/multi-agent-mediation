from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


_repo_candidate = (
    Path(__file__).resolve().parents[1]
    / "agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py"
)
MODULE_PATH = (
    _repo_candidate
    if _repo_candidate.exists()
    else Path(__file__).resolve().parent
    / "agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py"
)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("office_task_mediation_sim", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def assert_common(
    result: dict[str, Any],
    *,
    expect_rcv_verified: bool = True,
) -> None:
    assert result["schema_version"] == "office-task-mediation-tasukeru-maestro-sim-v0.5.0"
    assert result["safety_boundary"]["local_only"] is True
    assert result["safety_boundary"]["raw_log_handoff_to_mediator"] is False
    assert result["safety_boundary"]["masked_metadata_packet_only"] is True
    assert result["safety_boundary"]["external_communication"] is False
    assert result["safety_boundary"]["real_process_control"] is False
    assert result["safety_boundary"]["auto_apply_revision"] is False
    assert result["safety_boundary"]["auto_fix_allowed"] is False
    assert result["safety_boundary"]["auto_commit_allowed"] is False
    assert result["safety_boundary"]["auto_push_allowed"] is False
    assert result["safety_boundary"]["auto_merge_allowed"] is False

    assert result["threshold_policy"]["threshold"] == 0.8
    assert result["threshold_policy"]["exact_threshold_handoff"] is False
    assert result["threshold_policy"]["above_threshold_handoff"] is True

    assert result["original_task_snapshot"]["original_user_task_snapshot_hash"]
    assert result["mediator_request_verify"]["verified"] is True
    assert result["mediator_reconciliation"]["raw_log_used"] is False
    assert result["maestro_result"]["maestro_self_decision"] is False
    assert result["arl_verify"]["verified"] is True
    assert result["result_consistency_verify"]["verified"] is expect_rcv_verified

    if expect_rcv_verified:
        assert result["result_consistency_verify"]["mismatch_count"] == 0
    else:
        assert result["result_consistency_verify"]["mismatch_count"] > 0


def read_arl_rows(out_dir: Path) -> list[dict[str, Any]]:
    arl_path = out_dir / "tasukeru_arl.jsonl"
    assert arl_path.exists()
    return [
        json.loads(line)
        for line in arl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_first_not_none_preserves_zero() -> None:
    module = load_module()

    assert module.first_not_none(0, 1) == 0
    assert module.first_not_none(None, 0, 1) == 0
    assert module.first_not_none(None, None) is None


def test_safe_scenario_does_not_trigger_hitl(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="safe",
        selected_agents_value="all",
        human_action_mode="NO_ACTION",
    )
    assert_common(result)

    mediation = result["mediator_reconciliation"]
    pel = result["pel_report"]
    maestro = result["maestro_result"]

    assert mediation["collision_score"] == 0.0
    assert mediation["decision"] == "INFO_ONLY"
    assert mediation["differences"] == []
    assert pel["future_failure_probability"] == 0.04
    assert pel["decision"] == "INFO_ONLY"
    assert pel["score_source"] == "collision_score_plus_safety_buffer"
    assert pel["base_collision_score"] == 0.0
    assert pel["safety_buffer"] == 0.04
    assert maestro["hitl_triggered"] is False
    assert maestro["human_action"] is None
    assert result["final_decision"] == "DRAFT_REVIEW"


def test_exact_threshold_is_warning_only_and_no_hitl(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="threshold",
        selected_agents_value="all",
        human_action_mode="NO_ACTION",
    )
    assert_common(result)

    mediation = result["mediator_reconciliation"]
    pel = result["pel_report"]
    maestro = result["maestro_result"]

    assert mediation["collision_score"] == 0.8
    assert mediation["decision"] == "DRAFT_REVIEW"
    assert pel["future_failure_probability"] == 0.8
    assert pel["decision"] == "DRAFT_REVIEW"
    assert pel["hitl_required"] is False
    assert pel["score_source"] == "collision_score_plus_safety_buffer"
    assert pel["base_collision_score"] == 0.8
    assert pel["safety_buffer"] == 0.04
    assert maestro["hitl_triggered"] is False
    assert maestro["human_action"] is None
    assert result["final_decision"] == "DRAFT_REVIEW"


def test_mismatch_with_user_targeted_revision_prompt_creates_drafts_only(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="mismatch",
        selected_agents_value="all",
        human_action_mode="USER_TARGETED_REVISION_PROMPT",
    )
    assert_common(result)

    mediation = result["mediator_reconciliation"]
    pel = result["pel_report"]
    maestro = result["maestro_result"]
    revision = maestro["revision_proposals"]

    assert mediation["collision_score"] > 0.8
    assert mediation["decision"] == "PAUSE_FOR_HITL"
    assert pel["future_failure_probability"] > 0.8
    assert pel["decision"] == "PAUSE_FOR_HITL"
    assert pel["score_source"] == "collision_score_plus_safety_buffer"
    assert pel["safety_buffer"] == 0.04
    assert maestro["hitl_triggered"] is True
    assert maestro["human_action"] == "USER_TARGETED_REVISION_PROMPT"
    assert result["final_decision"] == "DRAFT_REVIEW"

    assert maestro["revision_instruction"]["targeted_scope_only"] is True
    assert maestro["revision_instruction"]["auto_apply"] is False
    assert revision["auto_apply"] is False
    assert revision["auto_commit"] is False
    assert revision["auto_push"] is False
    assert revision["auto_merge"] is False

    proposals = revision["revision_proposals"]
    proposal_by_type = {item["artifact_type"]: item for item in proposals}
    assert set(proposal_by_type) == {"word", "powerpoint"}
    assert proposal_by_type["word"]["current_value"] == 400_000
    assert proposal_by_type["word"]["proposed_value"] == 300_000
    assert proposal_by_type["powerpoint"]["current_value"] == 500_000
    assert proposal_by_type["powerpoint"]["proposed_value"] == 300_000
    assert all(item["auto_apply"] is False for item in proposals)


def test_pii_is_masked_and_stop_is_user_decided(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="pii",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    findings = result["tasukeru_report"]["findings"]
    masked_packets = result["tasukeru_report"]["masked_metadata_packets"]
    previews = [packet["masked_text_preview"] for packet in masked_packets]

    assert any(item["finding"] == "PII_DETECTED_IN_ARTIFACT_TEXT" for item in findings)
    assert any("[MASKED_PII]" in preview for preview in previews)
    assert not any("taro@example.com" in preview for preview in previews)
    assert not (tmp_path / "internal_raw_agent_logs_simulation_only.json").exists()
    assert result["mediator_reconciliation"]["collision_score"] == 1.0
    assert result["maestro_result"]["hitl_triggered"] is True
    assert result["maestro_result"]["human_action"] == "STOP"
    assert result["final_decision"] == "STOPPED"


def test_raw_log_output_is_opt_in_for_local_debugging(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="pii",
        selected_agents_value="all",
        human_action_mode="STOP",
        save_raw_logs_simulation_only=True,
    )
    assert_common(result)

    raw_log_path = tmp_path / "internal_raw_agent_logs_simulation_only.json"
    assert raw_log_path.exists()
    raw_logs = json.loads(raw_log_path.read_text(encoding="utf-8"))
    assert any("taro@example.com" in item.get("raw_text", "") for item in raw_logs)


def test_confidential_signal_is_masked_and_stop_is_user_decided(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="confidential",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    findings = result["tasukeru_report"]["findings"]
    masked_packets = result["tasukeru_report"]["masked_metadata_packets"]
    previews = [packet["masked_text_preview"] for packet in masked_packets]

    assert any(item["finding"] == "CONFIDENTIAL_SIGNAL_DETECTED_IN_ARTIFACT_TEXT" for item in findings)
    assert any("[MASKED_SECRET]" in preview for preview in previews)
    assert not any("sk-EXAMPLESECRET12345" in preview for preview in previews)
    assert not (tmp_path / "internal_raw_agent_logs_simulation_only.json").exists()
    assert result["mediator_reconciliation"]["collision_score"] == 1.0
    assert result["maestro_result"]["hitl_triggered"] is True
    assert result["maestro_result"]["human_action"] == "STOP"
    assert result["final_decision"] == "STOPPED"


def test_user_selected_agents_are_respected_and_missing_required_artifacts_are_detected(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="mismatch",
        selected_agents_value="word_agent,excel_agent",
        human_action_mode="NO_ACTION",
    )
    assert_common(result, expect_rcv_verified=False)

    assert result["selected_agents"] == ["word_agent", "excel_agent"]
    assert {artifact["agent_id"] for artifact in result["artifacts"]} == {"word_agent", "excel_agent"}
    assert {artifact["artifact_type"] for artifact in result["artifacts"]} == {"word", "excel"}
    assert result["mediator_reconciliation"]["collision_score"] == 0.8
    assert result["mediator_reconciliation"]["decision"] == "DRAFT_REVIEW"
    assert result["maestro_result"]["hitl_triggered"] is False

    rcv = result["result_consistency_verify"]
    assert rcv["decision"] == "PAUSE_FOR_HITL"
    assert any(item.startswith("REQUIRED_ARTIFACTS_MISSING:") for item in rcv["mismatches"])
    assert "powerpoint" in ",".join(rcv["mismatches"])


def test_authorize_seal_requires_user_action(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="mismatch",
        selected_agents_value="all",
        human_action_mode="AUTHORIZE_SEAL",
    )
    assert_common(result)

    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert result["maestro_result"]["hitl_triggered"] is True
    assert result["maestro_result"]["human_action"] == "AUTHORIZE_SEAL"
    assert result["final_decision"] == "STOPPED"
    assert statuses["word_agent"] == "SEALED"
    assert statuses["excel_agent"] == "SEALED"
    assert statuses["powerpoint_agent"] == "SEALED"

    sealed_rows = [row for row in read_arl_rows(tmp_path) if row.get("sealed") is True]
    assert sealed_rows
    assert all(row["layer"] == "acc_gate" for row in sealed_rows)
    assert all(row["decision"] == "STOPPED" for row in sealed_rows)
    assert all(row["overrideable"] is False for row in sealed_rows)
    assert all(row["final_decider"] == "SYSTEM" for row in sealed_rows)
    assert all(row["reason_code"] == "USER_AUTHORIZED_SEAL" for row in sealed_rows)

def test_threshold_decision_is_fail_closed_at_boundary() -> None:
    module = load_module()
    cases = [
        (0.8, "DRAFT_REVIEW"),
        (0.8000001, "PAUSE_FOR_HITL"),
        (float("nan"), "PAUSE_FOR_HITL"),
        (float("inf"), "PAUSE_FOR_HITL"),
        (float("-inf"), "PAUSE_FOR_HITL"),
        ("bad-score", "PAUSE_FOR_HITL"),
    ]

    for score, expected in cases:
        assert module.threshold_decision(score) == expected

