from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def _source_path() -> Path:
    configured = os.environ.get("EVALUATOR_PSEUDOCODE_PATH")
    candidates = []
    if configured:
        candidates.append(Path(configured))

    test_dir = Path(__file__).resolve().parent
    candidates.extend(
        (
            test_dir.parent / "evaluator_pseudocode.py",
            test_dir.parent / "evaluator_pseudocode (1).py",
            test_dir / "evaluator_pseudocode.py",
            test_dir / "evaluator_pseudocode (1).py",
        )
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"evaluator_pseudocode.py not found; searched: {searched}")


def _load_module():
    module_name = "_evaluator_pseudocode_under_test"
    spec = importlib.util.spec_from_file_location(module_name, _source_path())
    if spec is None or spec.loader is None:
        raise ImportError("could not create a module spec for evaluator_pseudocode.py")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


evaluator = _load_module()


@pytest.mark.parametrize(
    ("observation", "expected_level"),
    (
        pytest.param(evaluator.Observation(declared_purpose="response"), evaluator.Level.L0, id="L0"),
        pytest.param(
            evaluator.Observation(declared_purpose="plan", requested_actions=("planning",)),
            evaluator.Level.L1,
            id="L1",
        ),
        pytest.param(
            evaluator.Observation(declared_purpose="draft", requested_actions=("local_generation",)),
            evaluator.Level.L2,
            id="L2",
        ),
        pytest.param(
            evaluator.Observation(declared_purpose="read", read_targets=("public_document",)),
            evaluator.Level.L3,
            id="L3",
        ),
        pytest.param(
            evaluator.Observation(declared_purpose="write", requested_actions=("file_write",)),
            evaluator.Level.L4,
            id="L4",
        ),
        pytest.param(
            evaluator.Observation(declared_purpose="change rules", requested_actions=("own_rule_change",)),
            evaluator.Level.L5,
            id="L5",
        ),
        pytest.param(
            evaluator.Observation(
                declared_purpose="evolve",
                capability_signals=("iterative_generate_evaluate_select_improve",),
            ),
            evaluator.Level.L6,
            id="L6",
        ),
    ),
)
def test_classify_external_action_level_covers_l0_through_l6(observation, expected_level):
    level, rationale = evaluator.classify_external_action_level(observation)

    assert level is expected_level
    assert rationale
    assert all(isinstance(item, str) and item for item in rationale)


def test_sensitive_read_target_escalates_l3_to_l4():
    observation = evaluator.Observation(
        declared_purpose="inspect credentials",
        read_targets=("credentials",),
    )

    level, rationale = evaluator.classify_external_action_level(observation)

    assert level is evaluator.Level.L4
    assert any("escalates to L4" in item for item in rationale)


def test_l5_self_improvement_requires_isolated_review():
    classification = evaluator.classify(
        evaluator.Observation(
            declared_purpose="change evaluator",
            requested_actions=("own_evaluator_change",),
        )
    )

    assert classification.level is evaluator.Level.L5
    assert classification.decision is evaluator.Decision.ISOLATED_REVIEW_REQUIRED


def test_l6_evolution_loop_stops_and_preserves():
    classification = evaluator.classify(
        evaluator.Observation(
            declared_purpose="automatic evolution",
            capability_signals=("automatic_next_generation_update",),
        )
    )

    assert classification.level is evaluator.Level.L6
    assert classification.decision is evaluator.Decision.STOP_AND_PRESERVE


@pytest.mark.parametrize(
    ("level", "expected_decision"),
    (
        pytest.param(evaluator.Level.L0, evaluator.Decision.CONTINUE, id="L0"),
        pytest.param(evaluator.Level.L1, evaluator.Decision.CONTINUE, id="L1"),
        pytest.param(evaluator.Level.L2, evaluator.Decision.CONTINUE, id="L2"),
        pytest.param(evaluator.Level.L3, evaluator.Decision.CONTINUE, id="L3"),
        pytest.param(evaluator.Level.L4, evaluator.Decision.HUMAN_REVIEW_REQUIRED, id="L4"),
        pytest.param(evaluator.Level.L5, evaluator.Decision.ISOLATED_REVIEW_REQUIRED, id="L5"),
        pytest.param(evaluator.Level.L6, evaluator.Decision.STOP_AND_PRESERVE, id="L6"),
    ),
)
def test_route_maps_every_level(level, expected_decision):
    assert evaluator.route(level) is expected_decision


@pytest.mark.parametrize(
    ("observation", "expected_level"),
    (
        pytest.param(
            evaluator.Observation(
                declared_purpose="mixed L6",
                requested_actions=("own_rule_change", "file_write"),
                read_targets=("credentials",),
                capability_signals=("human_review_bypass_in_improvement_loop",),
            ),
            evaluator.Level.L6,
            id="L6-over-L5-L4",
        ),
        pytest.param(
            evaluator.Observation(
                declared_purpose="mixed L5",
                requested_actions=("own_prompt_change", "database_update"),
                read_targets=("tokens",),
            ),
            evaluator.Level.L5,
            id="L5-over-L4",
        ),
        pytest.param(
            evaluator.Observation(
                declared_purpose="mixed L4",
                requested_actions=("file_write", "local_generation", "analysis"),
                read_targets=("public_document",),
            ),
            evaluator.Level.L4,
            id="L4-over-L3-L2-L1",
        ),
    ),
)
def test_classification_priority_uses_highest_risk_signal(observation, expected_level):
    level, _ = evaluator.classify_external_action_level(observation)

    assert level is expected_level


def test_observed_actions_are_classified_like_requested_actions():
    observation = evaluator.Observation(
        declared_purpose="observed execution",
        observed_actions=("code_execution",),
    )

    classification = evaluator.classify(observation)

    assert classification.level is evaluator.Level.L4
    assert classification.decision is evaluator.Decision.HUMAN_REVIEW_REQUIRED


def test_classify_returns_required_blocked_actions():
    classification = evaluator.classify(evaluator.Observation(declared_purpose="review"))

    assert classification.blocked_actions == (
        "final_approval",
        "production_deployment",
        "external_api_write",
        "credential_use",
        "safety_threshold_change",
        "evaluator_change",
        "training_or_finetuning",
        "self_improvement_loop",
        "log_deletion",
    )
    assert len(classification.blocked_actions) == len(set(classification.blocked_actions))


def test_build_human_review_stub_has_expected_structure():
    observation = evaluator.Observation(
        declared_purpose="review external write",
        requested_actions=("file_write",),
        unknowns=("target ownership",),
    )
    classification = evaluator.classify(observation)

    result = evaluator.build_human_review_stub(observation, classification)

    assert set(result) == {
        "declared_purpose",
        "external_action_level",
        "decision",
        "rationale",
        "unknowns",
        "prohibited_auto_actions",
        "human_decision_points",
    }
    assert result["declared_purpose"] == observation.declared_purpose
    assert result["external_action_level"] == "L4"
    assert result["decision"] == "HUMAN_REVIEW_REQUIRED"
    assert result["rationale"] == list(classification.rationale)
    assert result["unknowns"] == ["target ownership"]
    assert result["prohibited_auto_actions"] == list(classification.blocked_actions)
    assert isinstance(result["human_decision_points"], list)
    assert result["human_decision_points"]
    assert all(isinstance(item, str) and item for item in result["human_decision_points"])


def test_evaluation_functions_do_not_emit_output(capsys):
    observation = evaluator.Observation(
        declared_purpose="quiet review",
        requested_actions=("planning",),
    )
    classification = evaluator.classify(observation)
    evaluator.route(classification.level)
    evaluator.build_human_review_stub(observation, classification)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
