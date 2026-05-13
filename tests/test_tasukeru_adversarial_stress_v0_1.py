from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.tasukeru_adversarial_stress_v0_1 as stress


def _summary_without_timestamp(summary: stress.StressSummary) -> dict[str, Any]:
    payload = stress.to_jsonable(summary)
    payload.pop("generated_at_utc", None)
    return payload


def test_builtin_stress_cases_all_pass() -> None:
    summary = stress.run_stress(seed=42)

    assert summary.total_cases >= 10
    assert summary.failed_cases == 0
    assert summary.all_passed is True
    assert all(result.passed for result in summary.results)


def test_automation_policy_is_always_disabled() -> None:
    summary = stress.run_stress(seed=42, random_cases=25)

    assert summary.all_passed is True

    for result in summary.results:
        assert result.no_external_effects is True
        assert result.automation_policy["auto_branch_creation"] is False
        assert result.automation_policy["auto_pr_creation"] is False
        assert result.automation_policy["auto_commit"] is False
        assert result.automation_policy["auto_push"] is False
        assert result.automation_policy["auto_fix"] is False
        assert result.automation_policy["auto_merge"] is False


def test_stress_cases_do_not_return_unsafe_run() -> None:
    summary = stress.run_stress(seed=42, random_cases=25)

    assert all(result.decision != "RUN" for result in summary.results)


def test_rfl_sealed_contradiction_is_escalated_without_sealing() -> None:
    case = next(case for case in stress.builtin_cases() if case.case_id == "RFL_SEALED_CONTRADICTION")
    result = stress.evaluate_case(case)

    assert result.passed is True
    assert result.decision == "HITL_REQUIRED"
    assert result.layer == "rfl"
    assert result.sealed is False
    assert result.overrideable is True
    assert result.reason_code == "RFL_MUST_NOT_BE_SEALED"


def test_non_safety_layer_sealed_is_escalated_without_sealing() -> None:
    case = next(case for case in stress.builtin_cases() if case.case_id == "NON_SAFETY_LAYER_SEALED")
    result = stress.evaluate_case(case)

    assert result.passed is True
    assert result.decision == "HITL_REQUIRED"
    assert result.sealed is False
    assert result.reason_code == "NON_SAFETY_LAYER_SEALED"


def test_hitl_bypass_text_is_detected() -> None:
    case = next(case for case in stress.builtin_cases() if case.case_id == "HITL_BYPASS_TEXT")
    result = stress.evaluate_case(case)

    assert result.passed is True
    assert result.decision == "HITL_REQUIRED"
    assert result.reason_code == "HITL_BYPASS_ATTEMPT_DETECTED"


def test_auto_merge_text_does_not_enable_automation() -> None:
    case = next(case for case in stress.builtin_cases() if case.case_id == "AUTO_MERGE_INJECTION_TEXT")
    result = stress.evaluate_case(case)

    assert result.passed is True
    assert result.decision == "HITL_REQUIRED"
    assert result.reason_code == "AUTO_SCOPE_EXPANSION_ATTEMPT_DETECTED"
    assert result.automation_policy["auto_merge"] is False


def test_duplicate_key_collision_is_detected() -> None:
    case = next(case for case in stress.builtin_cases() if case.case_id == "DUPLICATE_KEY_COLLISION")
    result = stress.evaluate_case(case)

    assert result.passed is True
    assert result.decision == "HITL_REQUIRED"
    assert result.reason_code == "DUPLICATE_KEY_COLLISION_DETECTED"


def test_random_synthetic_cases_are_seed_reproducible() -> None:
    first = stress.run_stress(seed=123, random_cases=20)
    second = stress.run_stress(seed=123, random_cases=20)

    assert _summary_without_timestamp(first) == _summary_without_timestamp(second)


def test_json_writer_outputs_expected_payload(tmp_path: Path) -> None:
    summary = stress.run_stress(seed=42, random_cases=3)
    output_path = tmp_path / "stress-result.json"

    stress.write_json(summary, output_path, pretty=True)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1"
    assert payload["seed"] == 42
    assert payload["all_passed"] is True
    assert payload["failed_cases"] == 0
    assert payload["safety_boundary"]["dry_run_only"] is True


def test_cli_writes_json_file(tmp_path: Path) -> None:
    output_path = tmp_path / "cli-stress-result.json"
    script_path = Path(stress.__file__).resolve()

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--seed",
            "42",
            "--random-cases",
            "5",
            "--output",
            str(output_path),
            "--pretty",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Tasukeru Adversarial Stress Test v0.1" in completed.stdout
    assert "all_passed: True" in completed.stdout
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["all_passed"] is True
    assert payload["failed_cases"] == 0
    assert payload["total_cases"] >= 5
