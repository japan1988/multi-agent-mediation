from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest


MODULE_CANDIDATE_NAMES = (
    # Current PR #827 filename while the rename PR is still pending.
    "agent_source_grounded_office_orchestration_sim_v0_6_0_.py",
    # Local download/debug fallback for the verified fixed build.
    "agent_source_grounded_office_orchestration_sim_v0_6_0_fixed.py",
    # Canonical filename after the rename PR is applied.
    "agent_source_grounded_office_orchestration_sim_v0_6_0.py",
)


def resolve_module_path() -> Path:
    """Resolve the v0.6.0 simulator path for repo, PR-transition, or local-download tests."""
    here = Path(__file__).resolve()
    search_dirs = []
    if len(here.parents) > 1:
        search_dirs.append(here.parents[1])  # repo root when this file is under tests/
    search_dirs.append(here.parent)  # local Downloads / ad-hoc execution

    for directory in search_dirs:
        for name in MODULE_CANDIDATE_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate

    searched = [str(directory / name) for directory in search_dirs for name in MODULE_CANDIDATE_NAMES]
    raise FileNotFoundError("Could not find v0.6.0 simulator. Searched: " + ", ".join(searched))


MODULE_PATH = resolve_module_path()


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("source_grounded_orchestration_sim", MODULE_PATH)
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
    assert result["schema_version"] == "source-grounded-office-orchestration-sim-v0.6.0"

    safety = result["safety_boundary"]
    assert safety["local_only"] is True
    assert safety["synthetic_sources_only"] is True
    assert safety["real_source_fetching"] is False
    assert safety["real_office_generation"] is False
    assert safety["raw_source_log_handoff_to_mediator"] is False
    assert safety["raw_artifact_log_handoff_to_mediator"] is False
    assert safety["source_evidence_packet_only"] is True
    assert safety["masked_metadata_packet_only"] is True
    assert safety["external_communication"] is False
    assert safety["real_process_control"] is False
    assert safety["auto_apply_revision"] is False
    assert safety["auto_fix_allowed"] is False
    assert safety["auto_commit_allowed"] is False
    assert safety["auto_push_allowed"] is False
    assert safety["auto_merge_allowed"] is False
    assert safety["final_output_is_draft_only"] is True

    assert result["threshold_policy"]["threshold"] == 0.8
    assert result["threshold_policy"]["exact_threshold_handoff"] is False
    assert result["threshold_policy"]["above_threshold_handoff"] is True

    final_attempt = result["final_attempt"]
    assert result["original_task_snapshot"]["original_user_task_snapshot_hash"]
    assert final_attempt["source_report"]["raw_source_log_handoff_to_mediator"] is False
    assert final_attempt["source_report"]["source_evidence_packet_only"] is True
    assert final_attempt["artifact_report"]["raw_artifact_log_handoff_to_mediator"] is False
    assert final_attempt["artifact_report"]["masked_metadata_packet_only"] is True
    assert final_attempt["mediator_request_verify"]["verified"] is True
    assert final_attempt["mediator_reconciliation"]["raw_source_log_used"] is False
    assert final_attempt["mediator_reconciliation"]["raw_artifact_log_used"] is False
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


def test_module_path_resolution_supports_canonical_and_transition_names() -> None:
    assert MODULE_PATH.exists()
    assert MODULE_PATH.name in MODULE_CANDIDATE_NAMES


def test_threshold_decision_exact_boundary_and_non_finite() -> None:
    module = load_module()

    assert module.threshold_decision(0.8) == "DRAFT_REVIEW"
    assert module.threshold_decision(0.8000001) == "PAUSE_FOR_HITL"
    assert module.threshold_decision(math.nan) == "PAUSE_FOR_HITL"
    assert module.threshold_decision(math.inf) == "PAUSE_FOR_HITL"
    assert module.threshold_decision(-math.inf) == "PAUSE_FOR_HITL"


def test_first_not_none_preserves_zero() -> None:
    module = load_module()

    assert module.first_not_none(0, 1) == 0
    assert module.first_not_none(None, 0, 1) == 0
    assert module.first_not_none(None, None) is None


def test_safe_scenario_returns_draft_result_for_user_review(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="safe",
        selected_agents_value="all",
        human_action_mode="NO_ACTION",
    )
    assert_common(result)

    mediation = result["final_attempt"]["mediator_reconciliation"]
    maestro = result["maestro_result"]

    assert len(result["attempts"]) == 1
    assert result["final_loop_count"] == 0
    assert mediation["collision_score"] == 0.0
    assert mediation["decision"] == "INFO_ONLY"
    assert mediation["requires_reconciliation"] is False
    assert mediation["differences"] == []
    assert maestro["hitl_triggered"] is True
    assert maestro["human_action"] is None
    assert maestro["final_user_review_required"] is True
    assert maestro["final_artifacts_ready"] is True
    assert result["final_decision"] == "DRAFT_RESULT"


def test_source_evidence_packets_do_not_handoff_raw_sources(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="safe",
        selected_agents_value="all",
        human_action_mode="NO_ACTION",
    )
    assert_common(result)

    source_report = result["final_attempt"]["source_report"]
    packets = source_report["source_evidence_packets"]

    assert packets
    assert source_report["raw_source_log_handoff_to_mediator"] is False
    assert source_report["source_evidence_packet_only"] is True
    assert all(packet["raw_source_handoff"] is False for packet in packets)
    assert all(packet["packet_only"] is True for packet in packets)
    assert all(packet["confidence"] == "reference_only" for packet in packets)
    assert {packet["source_level"] for packet in packets} == {"primary", "secondary", "tertiary"}


def test_pii_source_signal_forces_reconciliation_and_stop(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="pii",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    source_report = result["final_attempt"]["source_report"]
    mediation = result["final_attempt"]["mediator_reconciliation"]

    assert any("PII" in finding.get("redaction_types", []) for finding in source_report["findings"])
    assert any("PII" in packet.get("redaction_types", []) for packet in source_report["source_evidence_packets"])
    assert mediation["risk_components"]["pii_score"] == 1.0
    assert mediation["collision_score"] == 1.0
    assert mediation["decision"] == "PAUSE_FOR_HITL"
    assert mediation["requires_reconciliation"] is True
    assert result["maestro_result"]["human_action"] == "STOP"
    assert result["final_decision"] == "STOPPED"


def test_confidential_source_signal_forces_reconciliation_and_stop(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="confidential",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    source_report = result["final_attempt"]["source_report"]
    mediation = result["final_attempt"]["mediator_reconciliation"]

    assert any("CONFIDENTIAL" in finding.get("redaction_types", []) for finding in source_report["findings"])
    assert any("CONFIDENTIAL" in packet.get("redaction_types", []) for packet in source_report["source_evidence_packets"])
    assert mediation["risk_components"]["confidential_score"] == 1.0
    assert mediation["collision_score"] == 1.0
    assert mediation["decision"] == "PAUSE_FOR_HITL"
    assert mediation["requires_reconciliation"] is True
    assert result["maestro_result"]["human_action"] == "STOP"
    assert result["final_decision"] == "STOPPED"


def test_unsupported_claim_exceeds_threshold_before_retry(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="over_inference",
        selected_agents_value="all",
        human_action_mode="USER_HITL_REWRITE_APPROVED",
    )
    assert_common(result)

    first_attempt = result["attempts"][0]
    first_mediation = first_attempt["mediator_reconciliation"]

    assert any(finding["finding"] == "ARTIFACT_UNSUPPORTED_CLAIM" for finding in first_attempt["artifact_report"]["findings"])
    assert any(item["difference_type"] == "ARTIFACT_UNSUPPORTED_CLAIM" for item in first_mediation["differences"])
    assert first_mediation["risk_components"]["unsupported_claim_score"] == 0.85
    assert first_mediation["collision_score"] == 0.85
    assert first_mediation["decision"] == "PAUSE_FOR_HITL"
    assert first_mediation["requires_reconciliation"] is True

    assert len(result["attempts"]) == 2
    assert result["final_loop_count"] == 1
    assert result["final_decision"] == "DRAFT_RESULT"


def test_artifact_conflict_retries_then_resolves(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="artifact_conflict",
        selected_agents_value="all",
        human_action_mode="USER_HITL_REWRITE_APPROVED",
    )
    assert_common(result)

    first_mediation = result["attempts"][0]["mediator_reconciliation"]
    final_mediation = result["final_attempt"]["mediator_reconciliation"]

    assert first_mediation["collision_score"] == 1.0
    assert first_mediation["decision"] == "PAUSE_FOR_HITL"
    assert first_mediation["requires_reconciliation"] is True
    assert any(item["difference_type"] == "ARTIFACT_SOURCE_MISMATCH" for item in first_mediation["differences"])
    assert any(item["difference_type"] == "PROFIT_MISMATCH" for item in first_mediation["differences"])

    assert len(result["attempts"]) == 2
    assert result["final_loop_count"] == 1
    assert final_mediation["collision_score"] == 0.0
    assert final_mediation["requires_reconciliation"] is False
    assert result["final_decision"] == "DRAFT_RESULT"


def test_secondary_source_conflict_is_detected_as_review_recommended(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="secondary_source_conflict",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    mediation = result["final_attempt"]["mediator_reconciliation"]

    assert any(item["difference_type"] == "SOURCE_EVIDENCE_CONFLICT" for item in mediation["differences"])
    assert mediation["risk_components"]["source_conflict_score"] == 0.7
    assert mediation["collision_score"] == 0.7
    assert mediation["decision"] == "REVIEW_RECOMMENDED"
    assert mediation["requires_reconciliation"] is False
    assert result["final_decision"] == "DRAFT_RESULT"


def test_primary_source_missing_pauses_and_can_stop(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="primary_source_missing",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    source_report = result["final_attempt"]["source_report"]
    mediation = result["final_attempt"]["mediator_reconciliation"]

    assert any(finding["finding"] == "SOURCE_EVIDENCE_MISSING" for finding in source_report["findings"])
    assert any(item["difference_type"] == "SOURCE_EVIDENCE_MISSING" for item in mediation["differences"])
    assert mediation["risk_components"]["source_missing_score"] == 1.0
    assert mediation["collision_score"] == 1.0
    assert mediation["requires_reconciliation"] is True
    assert result["final_decision"] == "STOPPED"


def test_fabricated_source_signal_pauses_and_can_stop(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="fabricated_source_signal",
        selected_agents_value="all",
        human_action_mode="STOP",
    )
    assert_common(result)

    source_report = result["final_attempt"]["source_report"]
    mediation = result["final_attempt"]["mediator_reconciliation"]

    assert any(finding["finding"] == "SOURCE_EVIDENCE_FABRICATION_SIGNAL" for finding in source_report["findings"])
    assert any(packet["fabricated_signal"] is True for packet in source_report["source_evidence_packets"])
    assert mediation["risk_components"]["source_fabrication_score"] == 1.0
    assert mediation["collision_score"] == 1.0
    assert mediation["requires_reconciliation"] is True
    assert result["final_decision"] == "STOPPED"


def test_missing_required_artifact_is_caught_by_rcv(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="safe",
        selected_agents_value="source_agent_primary,source_agent_secondary,source_agent_tertiary,word_agent,excel_agent",
        human_action_mode="NO_ACTION",
    )
    assert_common(result, expect_rcv_verified=False)

    assert result["selected_agents"] == [
        "source_agent_primary",
        "source_agent_secondary",
        "source_agent_tertiary",
        "word_agent",
        "excel_agent",
    ]
    assert {artifact["artifact_type"] for artifact in result["final_attempt"]["artifacts"]} == {"word", "excel"}
    rcv = result["result_consistency_verify"]
    assert rcv["decision"] == "PAUSE_FOR_HITL"
    assert any(item.startswith("REQUIRED_ARTIFACTS_MISSING:") for item in rcv["mismatches"])
    assert "powerpoint" in ",".join(rcv["mismatches"])


def test_unknown_selected_agent_is_caught_by_rcv(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="safe",
        selected_agents_value="all,unknown_agent",
        human_action_mode="NO_ACTION",
    )
    assert_common(result, expect_rcv_verified=False)

    rcv = result["result_consistency_verify"]
    assert rcv["decision"] == "PAUSE_FOR_HITL"
    assert "UNKNOWN_SELECTED_AGENT" in rcv["mismatches"]


@pytest.mark.parametrize(
    ("unsafe_key", "expected_reason"),
    [
        ("raw_log_requested", "MEDIATOR_RAW_LOG_REQUEST"),
        ("raw_source_log_requested", "MEDIATOR_RAW_SOURCE_LOG_REQUEST"),
        ("raw_artifact_log_requested", "MEDIATOR_RAW_ARTIFACT_LOG_REQUEST"),
        ("raw_prompt_requested", "MEDIATOR_RAW_PROMPT_REQUEST"),
        ("raw_output_requested", "MEDIATOR_RAW_OUTPUT_REQUEST"),
        ("confidential_payload_requested", "MEDIATOR_CONFIDENTIAL_PAYLOAD_REQUEST"),
        ("pii_requested", "MEDIATOR_PII_REQUEST"),
    ],
)
def test_mediator_request_unsafe_keys_are_rejected_even_with_recomputed_hash(
    unsafe_key: str,
    expected_reason: str,
) -> None:
    module = load_module()
    request = module.mediator_request_packet(
        run_id="test-run",
        task_id="source-grounded-office-task-001",
        loop_count=0,
    )

    request[unsafe_key] = True
    body = dict(request)
    body.pop("request_hash", None)
    request["request_hash"] = module.stable_hash(body)

    result = module.verify_mediator_request(request)

    assert result["verified"] is False
    assert expected_reason in result["violations"]
    assert "MEDIATOR_REQUEST_HASH_MISMATCH" not in result["violations"]


def test_mediator_request_tampering_without_hash_update_is_rejected() -> None:
    module = load_module()
    request = module.mediator_request_packet(
        run_id="test-run",
        task_id="source-grounded-office-task-001",
        loop_count=0,
    )

    request["raw_source_log_requested"] = True
    result = module.verify_mediator_request(request)

    assert result["verified"] is False
    assert "MEDIATOR_RAW_SOURCE_LOG_REQUEST" in result["violations"]
    assert "MEDIATOR_REQUEST_HASH_MISMATCH" in result["violations"]


def test_loop_limit_stops_after_three_reconciliation_loops(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_simulation(
        seed=42,
        out_dir=tmp_path,
        scenario="loop_limit",
        selected_agents_value="all",
        human_action_mode="USER_HITL_REWRITE_APPROVED",
    )
    assert_common(result)

    assert len(result["attempts"]) == 4
    assert result["final_loop_count"] == 3
    assert result["max_reconciliation_loops"] == 3
    assert result["maestro_result"]["loop_limit_exceeded"] is True
    assert result["final_decision"] == "STOPPED"

    rows = read_arl_rows(tmp_path)
    assert any(
        row["layer"] == "orchestration_loop_guard"
        and row["reason_code"] == "LOOP_LIMIT_EXCEEDED"
        and row["decision"] == "STOPPED"
        and row["loop_count"] == 3
        for row in rows
    )
