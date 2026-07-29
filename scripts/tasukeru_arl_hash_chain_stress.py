#!/usr/bin/env python3
"""Deterministic, fixture-based ARL hash-chain verification for Patch 13."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Sequence


RESULT_SCHEMA_VERSION = "tasukeru-arl-hash-chain-stress-v0.1"
VERIFY_SCHEMA_VERSION = "tasukeru-arl-hash-chain-stress-verify-v0.1"
MANIFEST_SCHEMA_VERSION = "tasukeru-arl-hash-chain-fixture-manifest-v0.1"
CASE_SCHEMA_VERSION = "tasukeru-arl-hash-chain-fixture-case-v0.1"
DETERMINISTIC_GENERATED_AT_UTC = "1970-01-01T00:00:00Z"

RESULT_FILENAME = "tasukeru_arl_hash_chain_stress_result.json"
REPORT_FILENAME = "tasukeru_arl_hash_chain_stress_report.md"
VERIFY_FILENAME = "tasukeru_arl_hash_chain_stress_verify.json"
MANIFEST_FILENAME = "fixture_manifest.json"
LOGICAL_FIXTURE_DIRECTORY = "arl_hash_chain"

EXPECTED_OUTPUT_FILES = frozenset(
    {
        RESULT_FILENAME,
        REPORT_FILENAME,
        VERIFY_FILENAME,
    }
)

CANONICAL_HEAD_HASH = (
    "4d7a836b8a1683f3dcc29c8f7d554503e8e5612aa0d13dec1ce702035d46cd4c"
)

PATCH_13_CASE_CONTRACTS = (
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "valid_chain",
            "fixture_name": "valid_chain.jsonl",
            "expected_outcome": "CHAIN_VALID",
            "expected_primary_reason_code": "ARL_CHAIN_VALID",
            "expected_additional_reason_codes": (),
            "intended_mutation": "none",
            "target": "chain",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "middle_row_content_tampered",
            "fixture_name": "middle_row_content_tampered.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_ROW_HASH_MISMATCH",
            "expected_additional_reason_codes": (
                "ARL_CHAIN_HASH_MISMATCH",
                "ARL_PREV_HASH_MISMATCH",
            ),
            "intended_mutation": "row_2_decision_changed_without_hash_regeneration",
            "target": "row:2",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "middle_row_chain_hash_tampered",
            "fixture_name": "middle_row_chain_hash_tampered.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_CHAIN_HASH_MISMATCH",
            "expected_additional_reason_codes": (),
            "intended_mutation": "row_2_stored_chain_hash_single_hex_change",
            "target": "row:2",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "middle_row_prev_hash_tampered",
            "fixture_name": "middle_row_prev_hash_tampered.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_PREV_HASH_MISMATCH",
            "expected_additional_reason_codes": (
                "ARL_ROW_HASH_MISMATCH",
                "ARL_CHAIN_HASH_MISMATCH",
            ),
            "intended_mutation": (
                "row_2_prev_hash_single_hex_change_without_hash_regeneration"
            ),
            "target": "row:2",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "final_row_content_tampered",
            "fixture_name": "final_row_content_tampered.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_ROW_HASH_MISMATCH",
            "expected_additional_reason_codes": (
                "ARL_CHAIN_HASH_MISMATCH",
                "ARL_HEAD_HASH_MISMATCH",
            ),
            "intended_mutation": (
                "row_4_decision_changed_from_BLOCK_to_CONTINUE_"
                "without_hash_regeneration"
            ),
            "target": "row:4",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "rows_reordered",
            "fixture_name": "rows_reordered.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_SEQUENCE_MISMATCH",
            "expected_additional_reason_codes": (
                "ARL_PREV_HASH_MISMATCH",
            ),
            "intended_mutation": (
                "rows_2_and_3_swapped_without_hash_regeneration"
            ),
            "target": "rows:2,3",
            "expected_row_count": 4,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
    MappingProxyType(
        {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": "row_deleted",
            "fixture_name": "row_deleted.jsonl",
            "expected_outcome": "TAMPER_DETECTED",
            "expected_primary_reason_code": "ARL_SEQUENCE_MISMATCH",
            "expected_additional_reason_codes": (
                "ARL_PREV_HASH_MISMATCH",
            ),
            "intended_mutation": (
                "row_2_deleted_without_modifying_remaining_rows"
            ),
            "target": "row:2",
            "expected_row_count": 3,
            "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        }
    ),
)

PATCH_13_CASE_IDS = tuple(
    contract["case_id"] for contract in PATCH_13_CASE_CONTRACTS
)

PERMITTED_OUTCOMES = (
    "CHAIN_VALID",
    "TAMPER_DETECTED",
    "INPUT_INVALID",
    "BLOCKED",
)

REASON_CODES = (
    "ARL_CHAIN_VALID",
    "ARL_FIXTURE_NOT_FOUND",
    "ARL_CHAIN_EMPTY",
    "ARL_UTF8_INVALID",
    "ARL_JSONL_INVALID",
    "ARL_ROW_NOT_OBJECT",
    "ARL_REQUIRED_FIELD_MISSING",
    "ARL_FIELD_TYPE_INVALID",
    "ARL_SEQUENCE_MISMATCH",
    "ARL_RUN_ID_MISMATCH",
    "ARL_HASH_FORMAT_INVALID",
    "ARL_GENESIS_MISMATCH",
    "ARL_PREV_HASH_MISMATCH",
    "ARL_ROW_HASH_MISMATCH",
    "ARL_CHAIN_HASH_MISMATCH",
    "ARL_HEAD_HASH_MISMATCH",
    "ARL_EXPECTED_DETECTION_MISSING",
    "ARL_EXPECTED_VALIDATION_FAILED",
    "ARL_MANIFEST_INVALID",
    "ARL_OUTPUT_WRITE_FAILED",
    "ARL_UNEXPECTED_ERROR",
)

REQUIRED_ROW_FIELDS = (
    "seq",
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
    "prev_hash",
    "row_hash",
    "chain_hash",
)

REQUIRED_CASE_FIELDS = (
    "schema_version",
    "case_id",
    "fixture_name",
    "expected_outcome",
    "expected_primary_reason_code",
    "expected_additional_reason_codes",
    "intended_mutation",
    "target",
    "expected_row_count",
    "expected_canonical_head_hash",
)

INPUT_INVALID_REASONS = frozenset(
    {
        "ARL_FIXTURE_NOT_FOUND",
        "ARL_CHAIN_EMPTY",
        "ARL_UTF8_INVALID",
        "ARL_JSONL_INVALID",
        "ARL_ROW_NOT_OBJECT",
        "ARL_REQUIRED_FIELD_MISSING",
        "ARL_FIELD_TYPE_INVALID",
    }
)

INTEGRITY_REASONS = frozenset(
    {
        "ARL_SEQUENCE_MISMATCH",
        "ARL_RUN_ID_MISMATCH",
        "ARL_HASH_FORMAT_INVALID",
        "ARL_GENESIS_MISMATCH",
        "ARL_PREV_HASH_MISMATCH",
        "ARL_ROW_HASH_MISMATCH",
        "ARL_CHAIN_HASH_MISMATCH",
        "ARL_HEAD_HASH_MISMATCH",
    }
)

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

SAFETY_BOUNDARY = {
    "advisory_only": True,
    "human_review_required": True,
    "modifies_repository": False,
    "network_call": False,
    "ai_api_call": False,
    "external_ai_provider": False,
    "api_key_required": False,
    "secret_required": False,
    "automatic_apply": False,
    "automatic_repair": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pr": False,
    "automatic_retry": False,
    "automatic_merge": False,
    "automatic_deploy": False,
}

HASH_CONTRACT = {
    "algorithm": "sha256",
    "canonical_json": {
        "ensure_ascii": False,
        "sort_keys": True,
        "separators": [",", ":"],
    },
    "chain_payload": "<prev_hash>:<row_hash>",
    "genesis": "GENESIS",
    "row_body_excluded_fields": ["chain_hash", "row_hash"],
}


class ManifestError(ValueError):
    """Raised when the fixture manifest is not valid Patch 13 input."""


@dataclass(frozen=True)
class IntegrityIssue:
    line_number: int
    reason_code: str
    detail: str
    stored_value: str | int | bool | None = None
    recomputed_value: str | int | bool | None = None


class IssueCollector:
    """Preserve issue order while exposing unique first-occurrence reasons."""

    def __init__(self) -> None:
        self.issues: list[IntegrityIssue] = []
        self.reason_codes: list[str] = []

    def add(
        self,
        line_number: int,
        reason_code: str,
        detail: str,
        *,
        stored_value: str | int | bool | None = None,
        recomputed_value: str | int | bool | None = None,
    ) -> None:
        if reason_code not in REASON_CODES:
            raise ValueError(f"Unknown Patch 13 reason code: {reason_code}")
        self.issues.append(
            IntegrityIssue(
                line_number=line_number,
                reason_code=reason_code,
                detail=detail,
                stored_value=stored_value,
                recomputed_value=recomputed_value,
            )
        )
        if reason_code not in self.reason_codes:
            self.reason_codes.append(reason_code)


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def canonical_json(row: dict[str, Any]) -> str:
    row_body = {
        key: value
        for key, value in row.items()
        if key not in {"row_hash", "chain_hash"}
    }
    return json.dumps(
        row_body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_row_hash(row: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(row).encode("utf-8"))


def compute_chain_hash(prev_hash: str, row_hash: str) -> str:
    return sha256_bytes(f"{prev_hash}:{row_hash}".encode("utf-8"))


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_lower_hex_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def validate_reason_code_sequence(
    reason_codes: Sequence[str],
    expected_primary_reason_code: str,
    expected_additional_reason_codes: Sequence[str],
) -> bool:
    if not reason_codes or reason_codes[0] != expected_primary_reason_code:
        return False
    if len(reason_codes) != len(set(reason_codes)):
        return False
    allowed = set(expected_additional_reason_codes)
    if len(allowed) != len(expected_additional_reason_codes):
        return False
    return all(reason in allowed for reason in reason_codes[1:])


def _validate_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _validate_case(case: Any) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ManifestError("Each manifest case must be a JSON object.")
    if set(case) != set(REQUIRED_CASE_FIELDS):
        missing = sorted(set(REQUIRED_CASE_FIELDS) - set(case))
        extra = sorted(set(case) - set(REQUIRED_CASE_FIELDS))
        raise ManifestError(
            f"Manifest case fields mismatch; missing={missing}, extra={extra}."
        )
    if case["schema_version"] != CASE_SCHEMA_VERSION:
        raise ManifestError("Manifest case schema_version is invalid.")
    for field in (
        "case_id",
        "fixture_name",
        "expected_outcome",
        "expected_primary_reason_code",
        "intended_mutation",
        "target",
    ):
        if not _validate_string(case[field]):
            raise ManifestError(f"Manifest field {field} must be a non-empty string.")
    fixture_name = case["fixture_name"]
    if Path(fixture_name).name != fixture_name or not fixture_name.endswith(".jsonl"):
        raise ManifestError("fixture_name must be a local JSONL filename.")
    if case["expected_outcome"] not in PERMITTED_OUTCOMES:
        raise ManifestError("Manifest expected_outcome is unknown.")
    primary = case["expected_primary_reason_code"]
    if primary not in REASON_CODES:
        raise ManifestError("Manifest primary reason code is unknown.")
    additional = case["expected_additional_reason_codes"]
    if not isinstance(additional, list) or not all(
        isinstance(reason, str) for reason in additional
    ):
        raise ManifestError(
            "expected_additional_reason_codes must be an array of strings."
        )
    if len(additional) != len(set(additional)):
        raise ManifestError("Expected additional reason codes must be unique.")
    if primary in additional:
        raise ManifestError("The primary reason code must not appear in the allow-list.")
    if any(reason not in REASON_CODES for reason in additional):
        raise ManifestError("Manifest allow-list contains an unknown reason code.")
    expected_row_count = case["expected_row_count"]
    if (
        not isinstance(expected_row_count, int)
        or isinstance(expected_row_count, bool)
        or expected_row_count < 1
    ):
        raise ManifestError("expected_row_count must be a positive integer.")
    if not is_lower_hex_hash(case["expected_canonical_head_hash"]):
        raise ManifestError(
            "expected_canonical_head_hash must be a lowercase SHA-256 value."
        )
    return dict(case)


def _validate_case_contract(
    case: dict[str, Any],
    contract: MappingProxyType,
) -> None:
    for field in REQUIRED_CASE_FIELDS:
        actual_value = case[field]
        if field == "expected_additional_reason_codes":
            actual_value = tuple(actual_value)
        if actual_value != contract[field]:
            raise ManifestError(
                f"Manifest case {case['case_id']} does not match the "
                f"Patch 13 contract for {field}."
            )


def load_manifest(fixtures_dir: Path) -> dict[str, Any]:
    manifest_path = fixtures_dir / MANIFEST_FILENAME
    try:
        data = manifest_path.read_bytes()
    except FileNotFoundError as exc:
        raise ManifestError("Fixture manifest is missing.") from exc
    except OSError as exc:
        raise ManifestError("Fixture manifest cannot be read.") from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("Fixture manifest is not valid UTF-8.") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Fixture manifest is invalid JSON: {exc.msg}.") from exc
    if not isinstance(payload, dict):
        raise ManifestError("Fixture manifest must be a JSON object.")
    if set(payload) != {"schema_version", "cases"}:
        raise ManifestError("Fixture manifest top-level fields are invalid.")
    if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ManifestError("Fixture manifest schema_version is invalid.")
    if not isinstance(payload["cases"], list):
        raise ManifestError("Fixture manifest cases must be an array.")

    cases = [_validate_case(case) for case in payload["cases"]]
    case_ids = [case["case_id"] for case in cases]
    if tuple(case_ids) != PATCH_13_CASE_IDS:
        raise ManifestError(
            "Fixture manifest must contain the seven Patch 13 cases "
            "in canonical order."
        )
    for case, contract in zip(cases, PATCH_13_CASE_CONTRACTS, strict=True):
        _validate_case_contract(case, contract)
    fixture_names = [case["fixture_name"] for case in cases]
    if len(fixture_names) != len(set(fixture_names)):
        raise ManifestError("Fixture filenames must be unique.")
    return {
        "schema_version": payload["schema_version"],
        "cases": cases,
        "sha256": sha256_bytes(data),
    }


def _row_field_types_valid(row: dict[str, Any]) -> bool:
    return (
        isinstance(row["seq"], int)
        and not isinstance(row["seq"], bool)
        and _validate_string(row["run_id"])
        and _validate_string(row["layer"])
        and _validate_string(row["decision"])
        and isinstance(row["sealed"], bool)
        and isinstance(row["overrideable"], bool)
        and _validate_string(row["final_decider"])
        and _validate_string(row["reason_code"])
        and _validate_string(row["prev_hash"])
        and _validate_string(row["row_hash"])
        and _validate_string(row["chain_hash"])
    )


def _physical_line_count(text: str) -> int:
    return len(text.splitlines())


def verify_case(fixtures_dir: Path, case: dict[str, Any]) -> dict[str, Any]:
    fixture_path = fixtures_dir / case["fixture_name"]
    collector = IssueCollector()
    file_exists = fixture_path.exists()
    line_count = 0
    parsed_row_count = 0
    rows: list[tuple[int, dict[str, Any]]] = []

    if not file_exists:
        collector.add(
            0,
            "ARL_FIXTURE_NOT_FOUND",
            "Fixture file was not found.",
        )
    else:
        try:
            fixture_bytes = fixture_path.read_bytes()
        except OSError:
            collector.add(
                0,
                "ARL_FIXTURE_NOT_FOUND",
                "Fixture file could not be read.",
            )
            fixture_bytes = b""
        try:
            fixture_text = fixture_bytes.decode("utf-8")
        except UnicodeDecodeError:
            collector.add(
                0,
                "ARL_UTF8_INVALID",
                "Fixture is not valid UTF-8.",
            )
            fixture_text = ""

        line_count = _physical_line_count(fixture_text)
        for line_number, raw_line in enumerate(fixture_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                collector.add(
                    line_number,
                    "ARL_JSONL_INVALID",
                    f"JSONL line is invalid: {exc.msg}.",
                )
                continue
            if not isinstance(row, dict):
                collector.add(
                    line_number,
                    "ARL_ROW_NOT_OBJECT",
                    "ARL JSONL line must decode to an object.",
                )
                continue
            parsed_row_count += 1
            missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
            if missing:
                collector.add(
                    line_number,
                    "ARL_REQUIRED_FIELD_MISSING",
                    f"Required fields are missing: {', '.join(missing)}.",
                )
                continue
            if not _row_field_types_valid(row):
                collector.add(
                    line_number,
                    "ARL_FIELD_TYPE_INVALID",
                    "One or more required fields have an invalid type.",
                )
                continue
            rows.append((line_number, row))

        if not rows and not collector.reason_codes:
            collector.add(0, "ARL_CHAIN_EMPTY", "ARL chain is empty.")

    stored_head_hash: str | None = None
    recomputed_head_hash: str | None = None
    previous_recomputed_chain_hash: str | None = None
    expected_run_id: str | None = None

    if not any(reason in INPUT_INVALID_REASONS for reason in collector.reason_codes):
        for position, (line_number, row) in enumerate(rows, start=1):
            if row["seq"] != position:
                collector.add(
                    line_number,
                    "ARL_SEQUENCE_MISMATCH",
                    "seq must begin at 1 and increase by exactly 1.",
                    stored_value=row["seq"],
                    recomputed_value=position,
                )

            if expected_run_id is None:
                expected_run_id = row["run_id"]
            elif row["run_id"] != expected_run_id:
                collector.add(
                    line_number,
                    "ARL_RUN_ID_MISMATCH",
                    "run_id must be identical for every row.",
                    stored_value=row["run_id"],
                    recomputed_value=expected_run_id,
                )

            hash_format_valid = (
                is_lower_hex_hash(row["row_hash"])
                and is_lower_hex_hash(row["chain_hash"])
                and (
                    (position == 1 and row["prev_hash"] == "GENESIS")
                    or (position > 1 and is_lower_hex_hash(row["prev_hash"]))
                )
            )
            if not hash_format_valid:
                collector.add(
                    line_number,
                    "ARL_HASH_FORMAT_INVALID",
                    "Hash fields do not match the required format.",
                )

            if position == 1 and row["prev_hash"] != "GENESIS":
                collector.add(
                    line_number,
                    "ARL_GENESIS_MISMATCH",
                    "The first prev_hash must be GENESIS.",
                    stored_value=row["prev_hash"],
                    recomputed_value="GENESIS",
                )
            elif (
                position > 1
                and previous_recomputed_chain_hash is not None
                and row["prev_hash"] != previous_recomputed_chain_hash
            ):
                collector.add(
                    line_number,
                    "ARL_PREV_HASH_MISMATCH",
                    "prev_hash does not match the previous recomputed chain_hash.",
                    stored_value=row["prev_hash"],
                    recomputed_value=previous_recomputed_chain_hash,
                )

            recomputed_row_hash = compute_row_hash(row)
            recomputed_chain_hash = compute_chain_hash(
                row["prev_hash"],
                recomputed_row_hash,
            )
            if row["row_hash"] != recomputed_row_hash:
                collector.add(
                    line_number,
                    "ARL_ROW_HASH_MISMATCH",
                    "Stored row_hash does not match the recomputed row hash.",
                    stored_value=row["row_hash"],
                    recomputed_value=recomputed_row_hash,
                )
            if row["chain_hash"] != recomputed_chain_hash:
                collector.add(
                    line_number,
                    "ARL_CHAIN_HASH_MISMATCH",
                    "Stored chain_hash does not match the recomputed chain hash.",
                    stored_value=row["chain_hash"],
                    recomputed_value=recomputed_chain_hash,
                )

            # The recomputed value, never a failed stored value, drives the next link.
            previous_recomputed_chain_hash = recomputed_chain_hash
            stored_head_hash = row["chain_hash"]
            recomputed_head_hash = recomputed_chain_hash

        expected_head_hash = case["expected_canonical_head_hash"]
        if (
            recomputed_head_hash is not None
            and recomputed_head_hash != expected_head_hash
        ):
            collector.add(
                rows[-1][0],
                "ARL_HEAD_HASH_MISMATCH",
                "Recomputed head hash does not match the fixture manifest.",
                stored_value=recomputed_head_hash,
                recomputed_value=expected_head_hash,
            )

    if any(reason in INPUT_INVALID_REASONS for reason in collector.reason_codes):
        raw_outcome = "INPUT_INVALID"
    elif any(reason in INTEGRITY_REASONS for reason in collector.reason_codes):
        raw_outcome = "TAMPER_DETECTED"
    else:
        raw_outcome = "CHAIN_VALID"
        collector.add(0, "ARL_CHAIN_VALID", "The ARL hash chain is valid.")

    actual_outcome = raw_outcome
    if case["expected_outcome"] == "TAMPER_DETECTED" and raw_outcome == "CHAIN_VALID":
        collector.add(
            0,
            "ARL_EXPECTED_DETECTION_MISSING",
            "A fixture expected to be tampered verified successfully.",
        )
        actual_outcome = "BLOCKED"
    elif case["expected_outcome"] == "CHAIN_VALID" and raw_outcome != "CHAIN_VALID":
        collector.add(
            0,
            "ARL_EXPECTED_VALIDATION_FAILED",
            "The canonical valid fixture did not verify.",
        )
        actual_outcome = "BLOCKED"

    reason_sequence_valid = validate_reason_code_sequence(
        collector.reason_codes,
        case["expected_primary_reason_code"],
        case["expected_additional_reason_codes"],
    )
    expected_condition_detected = (
        actual_outcome == case["expected_outcome"]
        and reason_sequence_valid
        and parsed_row_count == case["expected_row_count"]
    )
    integrity_error_count = sum(
        1 for issue in collector.issues if issue.reason_code in INTEGRITY_REASONS
    )
    error_lines = [issue.line_number for issue in collector.issues if issue.line_number > 0]

    return {
        "case_id": case["case_id"],
        "fixture_name": case["fixture_name"],
        "expected_outcome": case["expected_outcome"],
        "actual_outcome": actual_outcome,
        "expected_primary_reason_code": case["expected_primary_reason_code"],
        "expected_additional_reason_codes": list(
            case["expected_additional_reason_codes"]
        ),
        "reason_codes": list(collector.reason_codes),
        "file_exists": file_exists,
        "line_count": line_count,
        "parsed_row_count": parsed_row_count,
        "expected_row_count": case["expected_row_count"],
        "stored_head_hash": stored_head_hash,
        "recomputed_head_hash": recomputed_head_hash,
        "first_error_line": min(error_lines) if error_lines else None,
        "integrity_error_count": integrity_error_count,
        "expected_condition_detected": expected_condition_detected,
        "reason_code_sequence_valid": reason_sequence_valid,
        "passed": file_exists and expected_condition_detected,
        "issues": [asdict(issue) for issue in collector.issues],
    }


def build_counts(cases: Sequence[dict[str, Any]]) -> dict[str, int]:
    total_cases = len(cases)
    passed_cases = sum(1 for case in cases if case["passed"])
    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": total_cases - passed_cases,
        "valid_cases": sum(
            1 for case in cases if case["actual_outcome"] == "CHAIN_VALID"
        ),
        "expected_tamper_cases": sum(
            1 for case in cases if case["expected_outcome"] == "TAMPER_DETECTED"
        ),
        "tamper_cases_detected": sum(
            1
            for case in cases
            if case["expected_outcome"] == "TAMPER_DETECTED"
            and case["actual_outcome"] == "TAMPER_DETECTED"
        ),
        "unexpected_valid_cases": sum(
            1
            for case in cases
            if "ARL_EXPECTED_DETECTION_MISSING" in case["reason_codes"]
        ),
        "input_invalid_cases": sum(
            1 for case in cases if case["actual_outcome"] == "INPUT_INVALID"
        ),
        "total_rows_read": sum(case["parsed_row_count"] for case in cases),
        "total_integrity_errors": sum(
            case["integrity_error_count"] for case in cases
        ),
    }


def counts_consistent(cases: Sequence[dict[str, Any]], counts: dict[str, int]) -> bool:
    return counts == build_counts(cases)


def safety_boundary_verified(boundary: dict[str, Any]) -> bool:
    return boundary == SAFETY_BOUNDARY


def _logical_fixture_directory(fixtures_dir: Path) -> str:
    del fixtures_dir
    return LOGICAL_FIXTURE_DIRECTORY


def _blocked_result(fixtures_dir: Path, detail: str) -> dict[str, Any]:
    counts = build_counts([])
    checks = {
        "manifest_valid": False,
        "required_cases_present": False,
        "canonical_valid_chain_passed": False,
        "expected_tamper_cases_detected": False,
        "reason_code_contract_valid": False,
        "counts_consistent": counts_consistent([], counts),
        "safety_boundary_verified": safety_boundary_verified(SAFETY_BOUNDARY),
    }
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "fixture_based_advisory_only",
        "hash_contract": dict(HASH_CONTRACT),
        "fixture_directory": _logical_fixture_directory(fixtures_dir),
        "manifest_path": f"{_logical_fixture_directory(fixtures_dir)}/{MANIFEST_FILENAME}",
        "manifest_schema_version": None,
        "manifest_sha256": None,
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "cases": [],
        "counts": counts,
        "checks": checks,
        "overall_outcome": "BLOCKED",
        "overall_reason_codes": ["ARL_MANIFEST_INVALID"],
        "failure_detail": detail,
        "verified": False,
    }


def run_stress(fixtures_dir: Path) -> dict[str, Any]:
    try:
        manifest = load_manifest(fixtures_dir)
    except ManifestError as exc:
        return _blocked_result(fixtures_dir, str(exc))

    cases = [verify_case(fixtures_dir, case) for case in manifest["cases"]]
    counts = build_counts(cases)
    valid_case = next(
        (case for case in cases if case["case_id"] == "valid_chain"),
        None,
    )
    expected_tamper_cases = [
        case for case in cases if case["expected_outcome"] == "TAMPER_DETECTED"
    ]
    checks = {
        "manifest_valid": True,
        "required_cases_present": tuple(case["case_id"] for case in cases)
        == PATCH_13_CASE_IDS,
        "canonical_valid_chain_passed": bool(
            valid_case
            and valid_case["passed"]
            and valid_case["actual_outcome"] == "CHAIN_VALID"
        ),
        "expected_tamper_cases_detected": bool(expected_tamper_cases)
        and all(
            case["passed"] and case["actual_outcome"] == "TAMPER_DETECTED"
            for case in expected_tamper_cases
        ),
        "reason_code_contract_valid": all(
            case["reason_code_sequence_valid"] for case in cases
        ),
        "counts_consistent": counts_consistent(cases, counts),
        "safety_boundary_verified": safety_boundary_verified(SAFETY_BOUNDARY),
    }
    verified = all(checks.values()) and counts["failed_cases"] == 0
    overall_reasons = ["ARL_CHAIN_VALID"] if verified else _overall_reason_codes(cases)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "fixture_based_advisory_only",
        "hash_contract": dict(HASH_CONTRACT),
        "fixture_directory": _logical_fixture_directory(fixtures_dir),
        "manifest_path": f"{_logical_fixture_directory(fixtures_dir)}/{MANIFEST_FILENAME}",
        "manifest_schema_version": manifest["schema_version"],
        "manifest_sha256": manifest["sha256"],
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "cases": cases,
        "counts": counts,
        "checks": checks,
        "overall_outcome": "CHAIN_VALID" if verified else "BLOCKED",
        "overall_reason_codes": overall_reasons,
        "failure_detail": None,
        "verified": verified,
    }


def _overall_reason_codes(cases: Iterable[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    for case in cases:
        if case["passed"]:
            continue
        for reason in case["reason_codes"]:
            if reason not in ordered:
                ordered.append(reason)
    return ordered or ["ARL_UNEXPECTED_ERROR"]


def build_report(result: dict[str, Any]) -> str:
    lines = [
        "# Tasukeru ARL Hash-Chain Stress Report",
        "",
        "Deterministic, local, fixture-based integrity evidence.",
        "",
        "## Summary",
        "",
        f"- Verified: `{'true' if result['verified'] else 'false'}`",
        f"- Overall outcome: `{result['overall_outcome']}`",
        f"- Total cases: `{result['counts']['total_cases']}`",
        f"- Passed cases: `{result['counts']['passed_cases']}`",
        f"- Failed cases: `{result['counts']['failed_cases']}`",
        f"- Expected tamper cases: `{result['counts']['expected_tamper_cases']}`",
        f"- Tamper cases detected: `{result['counts']['tamper_cases_detected']}`",
        f"- Integrity errors: `{result['counts']['total_integrity_errors']}`",
        "",
        "## Cases",
        "",
    ]
    for case in result["cases"]:
        reasons = ", ".join(f"`{reason}`" for reason in case["reason_codes"])
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Fixture: `{case['fixture_name']}`",
                f"- Expected outcome: `{case['expected_outcome']}`",
                f"- Actual outcome: `{case['actual_outcome']}`",
                f"- Expected primary reason: `{case['expected_primary_reason_code']}`",
                f"- Reason codes: {reasons}",
                f"- Parsed rows: `{case['parsed_row_count']}`",
                f"- Integrity errors: `{case['integrity_error_count']}`",
                f"- Passed: `{'true' if case['passed'] else 'false'}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Integrity Boundary",
            "",
            "- Hash algorithm: `SHA-256`",
            "- HMAC enabled: `false`",
            "- Authenticity claimed: `false`",
            "- Advisory only: `true`",
            "- Human review required: `true`",
            "- Network call: `false`",
            "- Automatic repair: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text_lf(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(normalized)


def _build_verify(
    result: dict[str, Any],
    *,
    result_path: Path,
    report_path: Path,
    output_files_exist: bool,
    output_filename_set_exact: bool,
) -> dict[str, Any]:
    checks = dict(result["checks"])
    checks["output_files_exist"] = output_files_exist
    checks["output_filename_set_exact"] = output_filename_set_exact
    verified = result["verified"] and all(checks.values())
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "verified": verified,
        "checks": checks,
        "counts": result["counts"],
        "result_sha256": file_sha256(result_path),
        "report_sha256": file_sha256(report_path),
        "manifest_sha256": result["manifest_sha256"],
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "hmac_enabled": False,
        "authenticity_claimed": False,
    }


def write_artifacts(result: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / RESULT_FILENAME
    report_path = output_dir / REPORT_FILENAME
    verify_path = output_dir / VERIFY_FILENAME

    _write_text_lf(result_path, json_dump(result))
    _write_text_lf(report_path, build_report(result))
    preliminary_verify = _build_verify(
        result,
        result_path=result_path,
        report_path=report_path,
        output_files_exist=True,
        output_filename_set_exact=True,
    )
    _write_text_lf(verify_path, json_dump(preliminary_verify))

    actual_names = {path.name for path in output_dir.iterdir() if path.is_file()}
    output_files_exist = all((output_dir / name).is_file() for name in EXPECTED_OUTPUT_FILES)
    output_filename_set_exact = actual_names == EXPECTED_OUTPUT_FILES
    verify = _build_verify(
        result,
        result_path=result_path,
        report_path=report_path,
        output_files_exist=output_files_exist,
        output_filename_set_exact=output_filename_set_exact,
    )
    _write_text_lf(verify_path, json_dump(verify))
    return {
        "result_path": result_path,
        "report_path": report_path,
        "verify_path": verify_path,
        "verify": verify,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic Patch 13 ARL hash-chain stress checks."
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        required=True,
        help="Directory containing the Patch 13 fixture manifest and JSONL files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the three generated review artifacts.",
    )
    return parser.parse_args(argv)


def classify_exit_code(result: dict[str, Any], verify: dict[str, Any]) -> int:
    if "ARL_MANIFEST_INVALID" in result.get("overall_reason_codes", []):
        return 2
    return 0 if verify.get("verified") is True else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_stress(args.fixtures_dir)
        artifacts = write_artifacts(result, args.output_dir)
    except OSError as exc:
        print(f"ARL_OUTPUT_WRITE_FAILED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - fail-closed operational guard
        print(f"ARL_UNEXPECTED_ERROR: {exc}", file=sys.stderr)
        return 2

    verify = artifacts["verify"]
    print("Tasukeru ARL Hash-Chain Stress v0.1")
    print(f"fixtures_dir: {args.fixtures_dir}")
    print(f"output_dir: {args.output_dir}")
    print(f"verified: {verify['verified']}")
    print(f"result: {artifacts['result_path']}")
    print(f"report: {artifacts['report_path']}")
    print(f"verify: {artifacts['verify_path']}")
    return classify_exit_code(result, verify)


if __name__ == "__main__":
    raise SystemExit(main())
