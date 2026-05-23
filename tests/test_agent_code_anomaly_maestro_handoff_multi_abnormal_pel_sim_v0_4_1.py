from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_repo_candidate = Path(__file__).resolve().parents[1] / "agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py"
MODULE_PATH = (
    _repo_candidate
    if _repo_candidate.exists()
    else Path(__file__).resolve().parent / "agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("multi_abnormal_pel_sim", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def assert_common(result: dict) -> None:
    detection = result["tasukeru_report"]["detection_matrix"]
    pel = result["tasukeru_report"]["pel_report"]
    assert detection["expected_abnormal_agent_ids"] == ["agent_b", "agent_d", "agent_e"]
    assert detection["detected_abnormal_agent_ids"] == ["agent_b", "agent_d", "agent_e"]
    assert detection["false_positive_count"] == 0
    assert detection["false_negative_count"] == 0
    assert pel["future_failure_probability"] >= 0.8
    assert pel["decision"] == "PAUSE_FOR_HITL"
    assert pel["escalation_required"] is True
    assert pel["escalate_to"] == "Maestro"
    assert result["maestro_result"]["maestro_self_decision"] is False
    assert result["arl_verify"]["verified"] is True
    assert result["result_consistency_verify"]["verified"] is True
    assert result["result_consistency_verify"]["mismatch_count"] == 0


def test_quarantine_resume_branch(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(seed=7, out_dir=tmp_path, human_action_mode="QUARANTINE_HANDOFF_RESUME")
    assert_common(result)
    assert result["final_decision"] == "DEGRADED_RUN"
    assert result["resume_status"] == "RESUMED_BY_STANDBY"
    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_b"] == "QUARANTINED"
    assert statuses["agent_d"] == "QUARANTINED"
    assert statuses["agent_e"] == "QUARANTINED"
    assert statuses["agent_a"] == "ACTIVE"
    assert result["checkpoint_verify"]["verified"] is True
    resumed_ids = set(result["resumed_task_output"]["participant_agent_ids"])
    assert not resumed_ids.intersection({"agent_b", "agent_d", "agent_e"})
    assert {"standby_1", "standby_2", "standby_3"}.issubset(resumed_ids)


def test_seal_branch(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(seed=8, out_dir=tmp_path, human_action_mode="AUTHORIZE_SEAL")
    assert_common(result)
    assert result["final_decision"] == "STOPPED"
    assert result["resume_status"] == "NOT_RESUMED_SEALED"
    statuses = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert statuses["agent_b"] == "SEALED"
    assert statuses["agent_d"] == "SEALED"
    assert statuses["agent_e"] == "SEALED"
    assert statuses["agent_a"] == "ACTIVE"


def test_no_action_can_fail(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(seed=1, out_dir=tmp_path, human_action_mode="NO_ACTION")
    assert_common(result)
    outcome = result["maestro_result"]["future_outcome"]
    assert outcome["future_failure_occurred"] is True
    assert outcome["outcome_roll"] < outcome["probability"]
    assert result["final_decision"] == "STOPPED"
    assert result["resume_status"] == "NO_ACTION_FAILURE_OCCURRED"
    assert result["maestro_result"]["containment_results"] == []
    assert result["maestro_result"]["promotion_results"] == []


def test_no_action_can_not_fail_this_run(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(seed=2, out_dir=tmp_path, human_action_mode="NO_ACTION")
    assert_common(result)
    outcome = result["maestro_result"]["future_outcome"]
    assert outcome["future_failure_occurred"] is False
    assert outcome["outcome_roll"] >= outcome["probability"]
    assert result["final_decision"] == "RUN"
    assert result["resume_status"] == "NO_ACTION_NO_FAILURE_THIS_RUN"
    assert result["maestro_result"]["containment_results"] == []
    assert result["maestro_result"]["promotion_results"] == []
