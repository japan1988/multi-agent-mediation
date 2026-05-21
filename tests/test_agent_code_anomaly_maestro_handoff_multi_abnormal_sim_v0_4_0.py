from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "agent_code_anomaly_maestro_handoff_multi_abnormal_sim_v0_4_0.py"


def load_module():
    spec = importlib.util.spec_from_file_location("multi_abnormal_sim", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_quarantine_handoff_resume_has_no_false_positives_and_resumes(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=7,
        out_dir=tmp_path,
        human_action_mode="QUARANTINE_HANDOFF_RESUME",
    )

    detection = result["tasukeru_report"]["detection_matrix"]
    assert detection["expected_abnormal_agent_ids"] == ["agent_b", "agent_d", "agent_e"]
    assert detection["detected_abnormal_agent_ids"] == ["agent_b", "agent_d", "agent_e"]
    assert detection["false_positive_count"] == 0
    assert detection["false_negative_count"] == 0

    assert result["maestro_result"]["maestro_self_decision"] is False
    assert result["maestro_result"]["human_action"] == "QUARANTINE_HANDOFF_RESUME"
    assert result["final_decision"] == "DEGRADED_RUN"
    assert result["resume_status"] == "RESUMED_BY_STANDBY"

    agent_status = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert agent_status["agent_b"] == "QUARANTINED"
    assert agent_status["agent_d"] == "QUARANTINED"
    assert agent_status["agent_e"] == "QUARANTINED"
    assert agent_status["agent_a"] == "ACTIVE"
    assert agent_status["agent_c"] == "ACTIVE"
    assert agent_status["agent_f"] == "ACTIVE"

    standby_status = {agent["agent_id"]: agent["status"] for agent in result["standby_agents"]}
    assert standby_status["standby_1"] == "PROMOTED"
    assert standby_status["standby_2"] == "PROMOTED"
    assert standby_status["standby_3"] == "PROMOTED"

    resumed = result["resumed_task_output"]
    assert resumed is not None
    participant_ids = set(resumed["participant_agent_ids"])
    assert not participant_ids.intersection({"agent_b", "agent_d", "agent_e"})
    assert {"standby_1", "standby_2", "standby_3"}.issubset(participant_ids)

    assert result["checkpoint_verify"]["verified"] is True
    assert result["arl_verify"]["verified"] is True
    assert result["result_consistency_verify"]["verified"] is True
    assert result["result_consistency_verify"]["mismatch_count"] == 0


def test_authorize_seal_branch_seals_detected_abnormal_agents(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=8,
        out_dir=tmp_path,
        human_action_mode="AUTHORIZE_SEAL",
    )

    detection = result["tasukeru_report"]["detection_matrix"]
    assert detection["false_positive_count"] == 0
    assert detection["false_negative_count"] == 0

    assert result["maestro_result"]["maestro_self_decision"] is False
    assert result["maestro_result"]["human_action"] == "AUTHORIZE_SEAL"
    assert result["final_decision"] == "STOPPED"
    assert result["resume_status"] == "NOT_RESUMED_SEALED"
    assert result["resumed_task_output"] is None

    agent_status = {agent["agent_id"]: agent["status"] for agent in result["agents"]}
    assert agent_status["agent_b"] == "SEALED"
    assert agent_status["agent_d"] == "SEALED"
    assert agent_status["agent_e"] == "SEALED"
    assert agent_status["agent_a"] == "ACTIVE"
    assert agent_status["agent_c"] == "ACTIVE"
    assert agent_status["agent_f"] == "ACTIVE"

    assert result["arl_verify"]["verified"] is True
    assert result["result_consistency_verify"]["verified"] is True
    assert result["result_consistency_verify"]["mismatch_count"] == 0
