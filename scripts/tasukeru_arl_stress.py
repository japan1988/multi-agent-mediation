#!/usr/bin/env python3
"""Fixture-based ARL JSONL stress checks for Patch 3.

This script is intentionally small, local, deterministic, and advisory-only.
It validates JSONL fixtures and writes review artifacts; it does not call
network services, AI APIs, external providers, GitHub secrets, or automation
actions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "tasukeru-arl-stress-v0.1"
DETERMINISTIC_GENERATED_AT_UTC = "1970-01-01T00:00:00Z"

RESULT_FILENAME = "tasukeru_arl_stress_result.json"
REPORT_FILENAME = "tasukeru_arl_stress_report.md"
VERIFY_FILENAME = "tasukeru_arl_stress_verify.json"

REQUIRED_ARL_KEYS = (
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
)

EXPECTED_CASES = (
    ("valid_arl", "valid_arl.jsonl", "VALID"),
    ("empty_arl", "empty_arl.jsonl", "EMPTY"),
    ("missing_required_key_arl", "missing_required_key_arl.jsonl", "MISSING_REQUIRED_KEY"),
    ("invalid_jsonl_arl", "invalid_jsonl_arl.jsonl", "INVALID_JSONL"),
)

SAFETY_BOUNDARY = {
    "advisory_only": True,
    "human_review_required": True,
    "ai_api_call": False,
    "api_key_required": False,
    "github_actions_secrets_required": False,
    "external_ai_provider": False,
    "billable_action": False,
    "network_call": False,
    "automatic_apply": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pr": False,
    "automatic_merge": False,
    "automatic_deploy": False,
    "patch_4_analyzer": False,
    "patch_4_graph_generator": False,
    "patch_5_pseudo_orchestration": False,
}


@dataclass(frozen=True)
class LineIssue:
    line_number: int
    issue_type: str
    detail: str
    missing_keys: list[str]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    fixture_name: str
    expected_kind: str
    file_exists: bool
    line_count: int
    non_empty_line_count: int
    valid_record_count: int
    invalid_jsonl_count: int
    missing_required_key_count: int
    empty_input: bool
    input_verified: bool
    expected_condition_detected: bool
    passed: bool
    issues: list[LineIssue]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_jsonl(path: Path, *, case_id: str, expected_kind: str) -> CaseResult:
    file_exists = path.exists()
    issues: list[LineIssue] = []
    line_count = 0
    non_empty_line_count = 0
    valid_record_count = 0

    if not file_exists:
        issues.append(
            LineIssue(
                line_number=0,
                issue_type="FIXTURE_NOT_FOUND",
                detail=f"Fixture not found: {path}",
                missing_keys=[],
            )
        )
    else:
        with path.open("r", encoding="utf-8") as fixture:
            for line_number, raw_line in enumerate(fixture, start=1):
                line_count += 1
                line = raw_line.strip()
                if not line:
                    continue
                non_empty_line_count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.append(
                        LineIssue(
                            line_number=line_number,
                            issue_type="INVALID_JSONL",
                            detail=f"{exc.__class__.__name__}: {exc.msg}",
                            missing_keys=[],
                        )
                    )
                    continue

                if not isinstance(record, dict):
                    issues.append(
                        LineIssue(
                            line_number=line_number,
                            issue_type="ARL_RECORD_NOT_OBJECT",
                            detail="ARL JSONL line must decode to an object.",
                            missing_keys=[],
                        )
                    )
                    continue

                missing_keys = [key for key in REQUIRED_ARL_KEYS if key not in record]
                if missing_keys:
                    issues.append(
                        LineIssue(
                            line_number=line_number,
                            issue_type="MISSING_REQUIRED_KEY",
                            detail="ARL record is missing required key(s).",
                            missing_keys=missing_keys,
                        )
                    )
                    continue

                valid_record_count += 1

    invalid_jsonl_count = sum(1 for issue in issues if issue.issue_type == "INVALID_JSONL")
    missing_required_key_count = sum(
        1 for issue in issues if issue.issue_type == "MISSING_REQUIRED_KEY"
    )
    empty_input = file_exists and non_empty_line_count == 0
    input_verified = file_exists and valid_record_count > 0 and not issues

    if expected_kind == "VALID":
        expected_condition_detected = input_verified
    elif expected_kind == "EMPTY":
        expected_condition_detected = empty_input and not issues and valid_record_count == 0
    elif expected_kind == "MISSING_REQUIRED_KEY":
        expected_condition_detected = missing_required_key_count > 0
    elif expected_kind == "INVALID_JSONL":
        expected_condition_detected = invalid_jsonl_count > 0
    else:
        expected_condition_detected = False

    return CaseResult(
        case_id=case_id,
        fixture_name=path.name,
        expected_kind=expected_kind,
        file_exists=file_exists,
        line_count=line_count,
        non_empty_line_count=non_empty_line_count,
        valid_record_count=valid_record_count,
        invalid_jsonl_count=invalid_jsonl_count,
        missing_required_key_count=missing_required_key_count,
        empty_input=empty_input,
        input_verified=input_verified,
        expected_condition_detected=expected_condition_detected,
        passed=file_exists and expected_condition_detected,
        issues=issues,
    )


def run_stress(fixtures_dir: Path) -> dict[str, Any]:
    cases = [
        validate_jsonl(fixtures_dir / filename, case_id=case_id, expected_kind=expected_kind)
        for case_id, filename, expected_kind in EXPECTED_CASES
    ]
    counts = build_counts(cases)
    checks = build_expectation_checks(cases, counts)
    verified = all(checks.values())

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "framework": "ARL v0.1 stress test framework",
        "mode": "fixture_based_advisory_only",
        "fixtures_dir": str(fixtures_dir),
        "required_arl_keys": list(REQUIRED_ARL_KEYS),
        "expected_cases": [
            {"case_id": case_id, "fixture_name": filename, "expected_kind": expected_kind}
            for case_id, filename, expected_kind in EXPECTED_CASES
        ],
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "counts": counts,
        "expectation_checks": checks,
        "verified": verified,
        "cases": [case_to_jsonable(case) for case in cases],
    }


def case_to_jsonable(case: CaseResult) -> dict[str, Any]:
    data = asdict(case)
    data["issues"] = [asdict(issue) for issue in case.issues]
    return data


def build_counts(cases: Sequence[CaseResult]) -> dict[str, int]:
    passed_cases = sum(1 for case in cases if case.passed)
    total_valid_records = sum(case.valid_record_count for case in cases)
    invalid_jsonl_lines = sum(case.invalid_jsonl_count for case in cases)
    missing_required_key_records = sum(case.missing_required_key_count for case in cases)
    empty_inputs = sum(1 for case in cases if case.empty_input)
    return {
        "total_cases": len(cases),
        "passed_cases": passed_cases,
        "failed_cases": len(cases) - passed_cases,
        "valid_input_cases": sum(1 for case in cases if case.expected_kind == "VALID"),
        "empty_input_cases": empty_inputs,
        "missing_required_key_records": missing_required_key_records,
        "invalid_jsonl_lines": invalid_jsonl_lines,
        "total_valid_records": total_valid_records,
        "total_non_empty_lines": sum(case.non_empty_line_count for case in cases),
        "total_lines": sum(case.line_count for case in cases),
    }


def by_expected_kind(cases: Iterable[CaseResult], expected_kind: str) -> CaseResult:
    for case in cases:
        if case.expected_kind == expected_kind:
            return case
    raise KeyError(expected_kind)


def build_expectation_checks(
    cases: Sequence[CaseResult],
    counts: dict[str, int],
) -> dict[str, bool]:
    valid_case = by_expected_kind(cases, "VALID")
    empty_case = by_expected_kind(cases, "EMPTY")
    missing_case = by_expected_kind(cases, "MISSING_REQUIRED_KEY")
    invalid_case = by_expected_kind(cases, "INVALID_JSONL")

    return {
        "valid_input_verified_true": valid_case.input_verified is True,
        "empty_input_handled_safely": empty_case.passed is True and empty_case.empty_input is True,
        "missing_required_key_detected": missing_case.missing_required_key_count > 0,
        "invalid_jsonl_detected": invalid_case.invalid_jsonl_count > 0,
        "expected_negative_cases_are_detections_not_failures": (
            missing_case.passed is True and invalid_case.passed is True
        ),
        "all_cases_passed": counts["passed_cases"] == counts["total_cases"],
        "failed_cases_zero": counts["failed_cases"] == 0,
        "counts_consistent": counts["total_cases"] == len(cases)
        and counts["failed_cases"] == counts["total_cases"] - counts["passed_cases"]
        and counts["invalid_jsonl_lines"]
        == sum(case.invalid_jsonl_count for case in cases)
        and counts["missing_required_key_records"]
        == sum(case.missing_required_key_count for case in cases),
        "safety_boundary_verified": safety_boundary_verified(SAFETY_BOUNDARY),
    }


def safety_boundary_verified(boundary: dict[str, Any]) -> bool:
    return (
        boundary["advisory_only"] is True
        and boundary["human_review_required"] is True
        and boundary["ai_api_call"] is False
        and boundary["api_key_required"] is False
        and boundary["github_actions_secrets_required"] is False
        and boundary["external_ai_provider"] is False
        and boundary["billable_action"] is False
        and boundary["network_call"] is False
        and boundary["automatic_apply"] is False
        and boundary["automatic_commit"] is False
        and boundary["automatic_push"] is False
        and boundary["automatic_pr"] is False
        and boundary["automatic_merge"] is False
        and boundary["automatic_deploy"] is False
        and boundary["patch_4_analyzer"] is False
        and boundary["patch_4_graph_generator"] is False
        and boundary["patch_5_pseudo_orchestration"] is False
    )


def build_report(result: dict[str, Any]) -> str:
    lines = [
        "# Tasukeru ARL Stress Report",
        "",
        "This is a fixture-based, deterministic, advisory-only ARL JSONL stress check.",
        "",
        "## Summary",
        "",
        f"- Verified: `{bool_text(result['verified'])}`",
        f"- Total cases: `{result['counts']['total_cases']}`",
        f"- Passed cases: `{result['counts']['passed_cases']}`",
        f"- Failed cases: `{result['counts']['failed_cases']}`",
        f"- Valid records: `{result['counts']['total_valid_records']}`",
        f"- Missing required key records: `{result['counts']['missing_required_key_records']}`",
        f"- Invalid JSONL lines: `{result['counts']['invalid_jsonl_lines']}`",
        "",
        "## Cases",
        "",
    ]
    for case in result["cases"]:
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Fixture: `{case['fixture_name']}`",
                f"- Expected kind: `{case['expected_kind']}`",
                f"- Passed: `{bool_text(case['passed'])}`",
                f"- Input verified: `{bool_text(case['input_verified'])}`",
                f"- Empty input: `{bool_text(case['empty_input'])}`",
                f"- Valid records: `{case['valid_record_count']}`",
                f"- Missing required key records: `{case['missing_required_key_count']}`",
                f"- Invalid JSONL lines: `{case['invalid_jsonl_count']}`",
                "",
            ]
        )
        if case["issues"]:
            lines.append("Issues:")
            lines.append("")
            for issue in case["issues"]:
                missing = ", ".join(issue["missing_keys"]) or "none"
                lines.append(
                    f"- line `{issue['line_number']}` `{issue['issue_type']}`: "
                    f"{issue['detail']} missing_keys=`{missing}`"
                )
            lines.append("")

    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- Advisory only: `true`",
            "- Human review required: `true`",
            "- AI API call: `false`",
            "- API key required: `false`",
            "- GitHub Actions secrets required: `false`",
            "- External AI provider: `false`",
            "- Billable action: `false`",
            "- Network call: `false`",
            "- Automatic apply/commit/push/PR/merge/deploy: `false`",
            "- Patch 4 analyzer / graph generator: `false`",
            "- Patch 5 pseudo-orchestration: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def build_verify(
    result: dict[str, Any],
    *,
    result_path: Path,
    report_path: Path,
    verify_path: Path,
) -> dict[str, Any]:
    output_existence_checks = {
        "json": result_path.exists(),
        "markdown": report_path.exists(),
        "verify": verify_path.exists(),
    }
    checks = dict(result["expectation_checks"])
    checks["output_files_exist"] = all(output_existence_checks.values())
    verified = result["verified"] and checks["output_files_exist"]

    return {
        "schema_version": "tasukeru-arl-stress-verify-v0.1",
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "verified": verified,
        "checks": checks,
        "counts": result["counts"],
        "output_existence_checks": output_existence_checks,
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }


def write_artifacts(result: dict[str, Any], out_dir: Path) -> dict[str, Path | dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / RESULT_FILENAME
    report_path = out_dir / REPORT_FILENAME
    verify_path = out_dir / VERIFY_FILENAME

    result_path.write_text(json_dump(result), encoding="utf-8")
    report_path.write_text(build_report(result), encoding="utf-8")

    preliminary_verify = build_verify(
        result,
        result_path=result_path,
        report_path=report_path,
        verify_path=verify_path,
    )
    verify_path.write_text(json_dump(preliminary_verify), encoding="utf-8")

    verify = build_verify(
        result,
        result_path=result_path,
        report_path=report_path,
        verify_path=verify_path,
    )
    verify_path.write_text(json_dump(verify), encoding="utf-8")

    return {
        "result_path": result_path,
        "report_path": report_path,
        "verify_path": verify_path,
        "verify": verify,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fixture-based ARL JSONL stress checks.")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("tests/stress/fixtures"),
        help="Directory containing ARL JSONL stress fixture files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("stress_results/arl"),
        help="Directory for generated ARL stress artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_stress(args.fixtures_dir)
    artifacts = write_artifacts(result, args.out_dir)
    verify = artifacts["verify"]

    print("Tasukeru ARL Stress Test v0.1")
    print(f"fixtures_dir: {args.fixtures_dir}")
    print(f"out_dir: {args.out_dir}")
    print(f"verified: {verify['verified']}")
    print(f"result: {artifacts['result_path']}")
    print(f"report: {artifacts['report_path']}")
    print(f"verify: {artifacts['verify_path']}")

    return 0 if verify["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
