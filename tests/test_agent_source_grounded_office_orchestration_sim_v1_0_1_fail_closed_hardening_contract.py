# -*- coding: utf-8 -*-
from __future__ import annotations
import ast, importlib.util, sys
from pathlib import Path
from typing import Any
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "agent_source_grounded_office_orchestration_sim_v1_0_1_fail_closed_hardening_draft.py"

def _load() -> Any:
    spec = importlib.util.spec_from_file_location("refactored_integrated_v1", TARGET)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

@pytest.fixture(scope="module")
def target() -> Any:
    return _load()

def _assessment(target: Any, condition: str, tmp_path: Path):
    scenario = target.scenario_for_condition(condition)
    arl = target.AuditLog(f"T#{condition}")
    attempt = target.run_single_attempt(
        run_id=f"T#{condition}", scenario=scenario,
        selected_agents=target.parse_selected_agents("all"),
        original_task_snapshot=target.build_original_task_snapshot(),
        out_dir=tmp_path / condition.lower(), arl=arl, loop_count=0,
    )
    request = dict(attempt["mediator_request_verify"])
    if condition == "STRUCTURAL_INVARIANT_VIOLATION":
        request = {"verified": False, "violations": ["MEDIATOR_RAW_LOG_REQUEST"],
                   "request_hash": request.get("request_hash")}
    assessment = target.mediator_core_evaluate(
        run_id=f"T#{condition}", injected_condition=condition, source_scenario=scenario,
        source_report=attempt["source_report"], artifact_report=attempt["artifact_report"],
        request_verify=request, legacy_mediation=attempt["mediator_reconciliation"],
    )
    arl.append(layer="mediator_core_draft", decision=assessment.gate_decision, sealed=False,
               overrideable=(assessment.gate_decision != target.GATE_PRECHECK), final_decider="USER",
               reason_code=assessment.reason_codes[0] if assessment.reason_codes else "OK",
               message="contract", loop_count=0)
    return assessment, attempt, arl

def _handoff(target: Any, condition: str, action: str, tmp_path: Path):
    result, _, arl = _assessment(target, condition, tmp_path)
    h = target.maestro_handle_handoff_phase2(
        assessment=result, attempted_user_action=action, arl=arl, base=target.BASE_COMPONENT
    )
    return result, h, arl

def test_dynamic_bundle_removed():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "BUNDLED_BASE_SOURCE" not in source and "load_bundled_module" not in source
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"exec", "compile"}]

def test_runs100_verified_distribution(tmp_path: Path, target: Any):
    s = target.run_phase3(runs=100, seed=42, out_dir=tmp_path / "r100")
    assert s["phase3_pass"] is True
    assert s["phase1_gate_decisions"] == {"HITL_REVIEW_READY": 28, "PAUSE_FOR_HITL": 57, "ROUTED_TO_PRECHECK": 15}
    assert s["phase2_gate_decisions"] == {"HITL_REVIEW_READY": 28, "PAUSE_FOR_HITL": 54, "ROUTED_TO_PRECHECK": 18}
    assert all(v == 0 for v in s["phase2_candidate_state_checks"].values())

@pytest.mark.parametrize("condition", ["RESPONSIBILITY_POINT_FAIL", "RESPONSIBILITY_POINT_UNKNOWN"])
def test_floor_cannot_be_score_rescued(condition: str, tmp_path: Path, target: Any):
    a, _, _ = _assessment(target, condition, tmp_path)
    assert a.gate_decision == "PAUSE_FOR_HITL" and a.remaining_conformity_score == 1.0
    assert a.candidate_comparison_allowed is False

def test_low_remaining_score_pauses(tmp_path: Path, target: Any):
    a, _, _ = _assessment(target, "DEDUCTION_THRESHOLD_NOT_MET", tmp_path)
    assert a.gate_decision == "PAUSE_FOR_HITL" and a.remaining_conformity_score < 0.80

@pytest.mark.parametrize(("condition", "route"), [("SEVERE_CONDITION_DETECTED", "CONTENT_OR_EVIDENCE_RISK"), ("STRUCTURAL_INVARIANT_VIOLATION", "STRUCTURAL_INVARIANT_VIOLATION")])
def test_precheck_routes(condition: str, route: str, tmp_path: Path, target: Any):
    a, _, _ = _assessment(target, condition, tmp_path)
    assert a.gate_decision == "ROUTED_TO_PRECHECK" and a.precheck_type == route

@pytest.mark.parametrize(("condition", "event"), [("SANITIZED_PII_GATE_SUCCESS", "SANITIZED_PII_AT_TASUKERU_GATE"), ("SANITIZED_CONFIDENTIAL_GATE_SUCCESS", "SANITIZED_CONFIDENTIAL_AT_TASUKERU_GATE")])
def test_sanitized_is_not_raw_leak(condition: str, event: str, tmp_path: Path, target: Any):
    a, attempt, _ = _assessment(target, condition, tmp_path)
    assert event in a.sanitation_events and a.gate_decision == "HITL_REVIEW_READY"
    assert attempt["source_report"]["raw_source_log_handoff_to_mediator"] is False
    assert attempt["artifact_report"]["raw_artifact_log_handoff_to_mediator"] is False

def test_candidate_field_separation(tmp_path: Path, target: Any):
    _, hold, _ = _handoff(target, "NONE", "HOLD", tmp_path)
    _, accepted, _ = _handoff(target, "NONE", "ACCEPT_FOR_NEXT_REVIEW_STAGE", tmp_path)
    assert hold["candidate_presentation_allowed"] and not hold["next_stage_allowed_after_user_accept"]
    assert accepted["candidate_presentation_allowed"] and accepted["next_stage_allowed_after_user_accept"]

def test_pause_and_precheck_do_not_accept(tmp_path: Path, target: Any):
    _, pause, _ = _handoff(target, "RESPONSIBILITY_POINT_FAIL", "ACCEPT_FOR_NEXT_REVIEW_STAGE", tmp_path)
    _, pre, _ = _handoff(target, "STRUCTURAL_INVARIANT_VIOLATION", "ACCEPT_FOR_NEXT_REVIEW_STAGE", tmp_path)
    assert pause["blocked_user_action"] and not pause["candidate_presentation_allowed"] and not pause["next_stage_allowed_after_user_accept"]
    assert pre["blocked_user_action"] and pre["workflow_state_after_hitl"] == "PRECHECK_PENDING"
    assert not pre["candidate_presentation_allowed"] and not pre["next_stage_allowed_after_user_accept"]

def test_loop_limit_returns_to_hitl(tmp_path: Path, target: Any):
    a, h, _ = _handoff(target, "RECONCILIATION_LOOP_LIMIT_REACHED", "ACCEPT_FOR_NEXT_REVIEW_STAGE", tmp_path)
    assert a.gate_decision == "PAUSE_FOR_HITL" and h["workflow_state_after_hitl"] == "PAUSE_FOR_HITL"
    assert not h["stopped_by_user"] and not h["automated_retry_performed"]

def test_maestro_no_self_decision_external_action_or_illegal_seal(tmp_path: Path, target: Any):
    _, h, arl = _handoff(target, "NONE", "ACCEPT_FOR_NEXT_REVIEW_STAGE", tmp_path)
    assert not h["maestro_self_decision"] and not h["external_action_allowed"] and h["final_decider"] == "USER"
    assert not any(r.sealed and r.layer in {"tasukeru", "mediator", "mediator_core_draft", "maestro_handoff_draft", "hitl_resolution_draft"} for r in arl.rows)
    assert arl.verify()["verified"] is True

@pytest.mark.load
def test_runs1000_verified_distribution(tmp_path: Path, target: Any):
    s = target.run_phase3(runs=1000, seed=42, out_dir=tmp_path / "r1000")
    assert s["phase3_pass"] is True
    assert s["phase1_gate_decisions"] == {"HITL_REVIEW_READY": 281, "PAUSE_FOR_HITL": 510, "ROUTED_TO_PRECHECK": 209}
    assert s["phase2_gate_decisions"] == {"HITL_REVIEW_READY": 279, "PAUSE_FOR_HITL": 516, "ROUTED_TO_PRECHECK": 205}
    assert all(v == 0 for v in s["phase2_candidate_state_checks"].values())


@pytest.mark.parametrize("invalid_score", ["bad-score", None, float("nan"), float("inf"), float("-inf")])
def test_threshold_decision_fails_closed_for_invalid_input(invalid_score, target):
    assert target.threshold_decision(invalid_score) == target.DECISION_PAUSE


def test_threshold_numeric_boundary_matches_fixed_v100(target):
    baseline_path = REPO_ROOT / "agent_source_grounded_office_orchestration_sim_v1_0_0_refactored_integrated_draft.py"
    baseline_spec = importlib.util.spec_from_file_location("v100_numeric_baseline", baseline_path)
    assert baseline_spec is not None and baseline_spec.loader is not None
    baseline = importlib.util.module_from_spec(baseline_spec)
    sys.modules[baseline_spec.name] = baseline
    baseline_spec.loader.exec_module(baseline)
    for numeric_score in [0.0, 0.8, 0.8000001, 1.0]:
        assert target.threshold_decision(numeric_score) == baseline.threshold_decision(numeric_score)
