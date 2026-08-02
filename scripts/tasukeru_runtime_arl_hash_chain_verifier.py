#!/usr/bin/env python3
"""Detached, deterministic verification of runtime Tasukeru ARL hash chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


TOOL_NAME = "tasukeru_runtime_arl_hash_chain_verifier"
RESULT_SCHEMA_VERSION = "tasukeru-runtime-arl-hash-chain-result-v0.1"
SOURCE_BINDING_SCHEMA_VERSION = (
    "tasukeru-runtime-arl-hash-chain-source-binding-v0.1"
)
VERIFY_SCHEMA_VERSION = "tasukeru-runtime-arl-hash-chain-verify-v0.1"

ARL_FILENAME = "tasukeru_arl.jsonl"
SOURCE_VERIFY_FILENAME = "tasukeru_arl_verify.json"
RESULT_FILENAME = "tasukeru_runtime_arl_hash_chain_result.json"
SOURCE_BINDING_FILENAME = "tasukeru_runtime_arl_hash_chain_source_binding.json"
REPORT_FILENAME = "tasukeru_runtime_arl_hash_chain_report.md"
VERIFY_FILENAME = "tasukeru_runtime_arl_hash_chain_verify.json"

EXPECTED_OUTPUT_FILES = tuple(
    sorted(
        (
            RESULT_FILENAME,
            SOURCE_BINDING_FILENAME,
            REPORT_FILENAME,
            VERIFY_FILENAME,
        )
    )
)
HASHED_OUTPUT_FILES = tuple(
    sorted((RESULT_FILENAME, SOURCE_BINDING_FILENAME, REPORT_FILENAME))
)

REASON_CODES = (
    "RUNTIME_ARL_NOT_FOUND",
    "RUNTIME_ARL_UTF8_INVALID",
    "RUNTIME_ARL_JSONL_INVALID",
    "RUNTIME_ARL_ROW_NOT_OBJECT",
    "RUNTIME_ARL_EMPTY",
    "RUNTIME_ARL_REQUIRED_FIELD_MISSING",
    "RUNTIME_ARL_FIELD_TYPE_INVALID",
    "RUNTIME_ARL_SCHEMA_VERSION_MISMATCH",
    "RUNTIME_ARL_POLICY_MISMATCH",
    "RUNTIME_ARL_SEQUENCE_MISMATCH",
    "RUNTIME_ARL_RUN_ID_MISMATCH",
    "RUNTIME_ARL_HASH_FORMAT_INVALID",
    "RUNTIME_ARL_GENESIS_MISMATCH",
    "RUNTIME_ARL_PREV_HASH_MISMATCH",
    "RUNTIME_ARL_ROW_HASH_MISMATCH",
    "RUNTIME_ARL_CHAIN_HASH_MISMATCH",
    "RUNTIME_ARL_HMAC_UNSUPPORTED",
    "SOURCE_VERIFY_NOT_FOUND",
    "SOURCE_VERIFY_UTF8_INVALID",
    "SOURCE_VERIFY_JSON_INVALID",
    "SOURCE_VERIFY_SCHEMA_INVALID",
    "SOURCE_VERIFY_TOOL_MISMATCH",
    "SOURCE_VERIFY_POLICY_MISMATCH",
    "SOURCE_VERIFY_HMAC_UNSUPPORTED",
    "SOURCE_VERIFY_REPORTED_FAILURE",
    "SOURCE_VERIFY_ERRORS_PRESENT",
    "SOURCE_VERIFY_ROW_COUNT_MISMATCH",
    "SOURCE_VERIFY_HEAD_HASH_MISMATCH",
    "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
    "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
    "RUNTIME_ARL_UNEXPECTED_ERROR",
)
REASON_CODE_SET = frozenset(REASON_CODES)

REQUIRED_ROW_FIELDS = (
    "schema_version",
    "seq",
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
    "prev_hash",
    "evidence",
    "modifies_repository",
    "auto_apply_allowed",
    "auto_branch_allowed",
    "auto_pr_creation_allowed",
    "auto_commit_allowed",
    "auto_push_allowed",
    "autofix_allowed",
    "auto_merge_allowed",
    "human_decision_required",
    "row_hash",
    "chain_hash",
)

SOURCE_POLICY = {
    "modifies_repository": False,
    "auto_apply_allowed": False,
    "auto_branch_allowed": False,
    "auto_pr_creation_allowed": False,
    "auto_commit_allowed": False,
    "auto_push_allowed": False,
    "autofix_allowed": False,
    "auto_merge_allowed": False,
    "human_decision_required": True,
}

SAFETY_BOUNDARY = {
    "advisory_only": True,
    "human_review_required": True,
    "modifies_repository": False,
    "network_call": False,
    "ai_api_call": False,
    "external_ai_provider": False,
    "api_key_required": False,
    "secret_required": False,
    "hmac_claimed": False,
    "authenticity_claimed": False,
    "automatic_repair": False,
    "automatic_retry": False,
    "automatic_apply": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pr": False,
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
    "row_body_excluded_fields": ["row_hash", "chain_hash", "hmac_sha256"],
}

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class VerifierOperationalError(RuntimeError):
    """An input or IO failure that prevents trustworthy artifacts."""

    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in REASON_CODE_SET:
            raise ValueError(f"Unknown operational reason code: {reason_code}")
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class VerificationIssue:
    line_number: int
    reason_code: str
    detail: str
    stored_value: str | int | bool | None = None
    recomputed_value: str | int | bool | None = None


class IssueCollector:
    def __init__(self) -> None:
        self.issues: list[VerificationIssue] = []
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
        if reason_code not in REASON_CODE_SET:
            raise ValueError(f"Unknown verification reason code: {reason_code}")
        self.issues.append(
            VerificationIssue(
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
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def safe_hash(value: Any, *, allow_genesis: bool = False) -> str | None:
    if allow_genesis and value == "GENESIS":
        return "GENESIS"
    return value if is_lower_sha256(value) else None


def safe_integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def canonical_json(row: dict[str, Any]) -> str:
    row_body = {
        key: value
        for key, value in row.items()
        if key not in {"row_hash", "chain_hash", "hmac_sha256"}
    }
    return json.dumps(
        row_body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_row_hash(row: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(row).encode("utf-8"))


def compute_chain_hash(prev_hash: str, row_hash: str) -> str:
    return sha256_bytes(f"{prev_hash}:{row_hash}".encode("utf-8"))


def _read_source(path: Path, not_found_code: str, label: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise VerifierOperationalError(
            not_found_code,
            f"{label} was not found.",
        ) from exc
    except OSError as exc:
        raise VerifierOperationalError(
            not_found_code,
            f"{label} cannot be read.",
        ) from exc


def _decode_source(data: bytes, utf8_code: str, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerifierOperationalError(
            utf8_code,
            f"{label} is not valid UTF-8.",
        ) from exc


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _row_types_valid(row: dict[str, Any]) -> bool:
    return (
        isinstance(row["seq"], int)
        and not isinstance(row["seq"], bool)
        and row["seq"] > 0
        and _nonempty_string(row["run_id"])
        and _nonempty_string(row["layer"])
        and _nonempty_string(row["decision"])
        and isinstance(row["sealed"], bool)
        and isinstance(row["overrideable"], bool)
        and _nonempty_string(row["final_decider"])
        and _nonempty_string(row["reason_code"])
        and _nonempty_string(row["prev_hash"])
        and isinstance(row["evidence"], dict)
        and _nonempty_string(row["row_hash"])
        and _nonempty_string(row["chain_hash"])
        and all(isinstance(row[field], bool) for field in SOURCE_POLICY)
    )


def _parse_runtime_rows(text: str, collector: IssueCollector) -> dict[str, Any]:
    parsed_rows: list[tuple[int, dict[str, Any]]] = []
    hmac_present = False
    nonblank_line_count = 0

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        nonblank_line_count += 1
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError:
            collector.add(
                line_number,
                "RUNTIME_ARL_JSONL_INVALID",
                "Runtime ARL line is invalid JSON.",
            )
            continue
        if not isinstance(row, dict):
            collector.add(
                line_number,
                "RUNTIME_ARL_ROW_NOT_OBJECT",
                "Runtime ARL line must decode to an object.",
            )
            continue
        if "hmac_sha256" in row:
            hmac_present = True
            collector.add(
                line_number,
                "RUNTIME_ARL_HMAC_UNSUPPORTED",
                "HMAC fields are outside the Phase 5A contract.",
            )
        missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
        if missing:
            collector.add(
                line_number,
                "RUNTIME_ARL_REQUIRED_FIELD_MISSING",
                "One or more required runtime ARL fields are missing.",
            )
            continue
        if not _row_types_valid(row):
            collector.add(
                line_number,
                "RUNTIME_ARL_FIELD_TYPE_INVALID",
                "One or more runtime ARL fields have an invalid type.",
            )
            continue
        if row["schema_version"] != "1.0":
            collector.add(
                line_number,
                "RUNTIME_ARL_SCHEMA_VERSION_MISMATCH",
                "Runtime ARL row schema_version must be 1.0.",
            )
        if any(row[field] != expected for field, expected in SOURCE_POLICY.items()):
            collector.add(
                line_number,
                "RUNTIME_ARL_POLICY_MISMATCH",
                "Runtime ARL row policy fields violate the advisory-only contract.",
            )
        parsed_rows.append((line_number, row))

    if nonblank_line_count == 0:
        collector.add(
            0,
            "RUNTIME_ARL_EMPTY",
            "Runtime ARL contains no non-blank rows.",
        )

    first_run_id: str | None = None
    previous_recomputed_hash = "GENESIS"
    stored_head_hash: str | None = None
    recomputed_head_hash: str | None = None

    for ordinal, (line_number, row) in enumerate(parsed_rows, start=1):
        if row["seq"] != ordinal:
            collector.add(
                line_number,
                "RUNTIME_ARL_SEQUENCE_MISMATCH",
                "Runtime ARL sequence must be one-based and contiguous.",
                stored_value=row["seq"],
                recomputed_value=ordinal,
            )
        if first_run_id is None:
            first_run_id = row["run_id"]
        elif row["run_id"] != first_run_id:
            collector.add(
                line_number,
                "RUNTIME_ARL_RUN_ID_MISMATCH",
                "All runtime ARL rows must use one run identifier.",
            )

        stored_prev_hash = row["prev_hash"]
        stored_row_hash = row["row_hash"]
        stored_chain_hash = row["chain_hash"]
        hash_format_valid = (
            (
                stored_prev_hash == "GENESIS"
                if ordinal == 1
                else is_lower_sha256(stored_prev_hash)
            )
            and is_lower_sha256(stored_row_hash)
            and is_lower_sha256(stored_chain_hash)
        )
        if not hash_format_valid:
            collector.add(
                line_number,
                "RUNTIME_ARL_HASH_FORMAT_INVALID",
                "Runtime ARL hashes must use GENESIS or lowercase SHA-256.",
            )
        if ordinal == 1 and stored_prev_hash != "GENESIS":
            collector.add(
                line_number,
                "RUNTIME_ARL_GENESIS_MISMATCH",
                "The first runtime ARL row must use GENESIS.",
                stored_value=safe_hash(stored_prev_hash, allow_genesis=True),
                recomputed_value="GENESIS",
            )
        if stored_prev_hash != previous_recomputed_hash:
            collector.add(
                line_number,
                "RUNTIME_ARL_PREV_HASH_MISMATCH",
                "Runtime ARL prev_hash does not match the preceding recomputed chain.",
                stored_value=safe_hash(stored_prev_hash, allow_genesis=True),
                recomputed_value=previous_recomputed_hash,
            )

        recomputed_row_hash = compute_row_hash(row)
        recomputed_chain_hash = compute_chain_hash(
            previous_recomputed_hash, recomputed_row_hash
        )
        if stored_row_hash != recomputed_row_hash:
            collector.add(
                line_number,
                "RUNTIME_ARL_ROW_HASH_MISMATCH",
                "Runtime ARL row hash does not match the canonical row body.",
                stored_value=safe_hash(stored_row_hash),
                recomputed_value=recomputed_row_hash,
            )
        if stored_chain_hash != recomputed_chain_hash:
            collector.add(
                line_number,
                "RUNTIME_ARL_CHAIN_HASH_MISMATCH",
                "Runtime ARL chain hash does not match the recomputed chain.",
                stored_value=safe_hash(stored_chain_hash),
                recomputed_value=recomputed_chain_hash,
            )

        stored_head_hash = safe_hash(stored_chain_hash)
        recomputed_head_hash = recomputed_chain_hash
        previous_recomputed_hash = recomputed_chain_hash

    return {
        "row_count": len(parsed_rows),
        "run_id": first_run_id,
        "stored_head_hash": stored_head_hash,
        "recomputed_head_hash": recomputed_head_hash,
        "hmac_present": hmac_present,
    }


def _source_verify_schema_issue(
    collector: IssueCollector,
    detail: str,
) -> None:
    collector.add(0, "SOURCE_VERIFY_SCHEMA_INVALID", detail)


def _parse_source_verify(text: str, collector: IssueCollector) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        collector.add(
            0,
            "SOURCE_VERIFY_JSON_INVALID",
            "Source verify artifact is invalid JSON.",
        )
        return {}
    if not isinstance(payload, dict):
        _source_verify_schema_issue(
            collector,
            "Source verify artifact must be a JSON object.",
        )
        return {}

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or schema_version != "1.0":
        _source_verify_schema_issue(
            collector,
            "Source verify schema_version must be the string 1.0.",
        )

    tool = payload.get("tool")
    if not isinstance(tool, str):
        _source_verify_schema_issue(
            collector,
            "Source verify tool must be a string.",
        )
    elif tool != "tasukeru_arl_hash_chain_verify":
        collector.add(
            0,
            "SOURCE_VERIFY_TOOL_MISMATCH",
            "Source verify tool identifier is invalid.",
        )

    reported_verified = payload.get("verified")
    if not isinstance(reported_verified, bool):
        _source_verify_schema_issue(
            collector,
            "Source verify verified must be a boolean.",
        )
    elif not reported_verified:
        collector.add(
            0,
            "SOURCE_VERIFY_REPORTED_FAILURE",
            "Source verify artifact reports a failed verification.",
            stored_value=False,
            recomputed_value=True,
        )

    row_count = payload.get("row_count")
    if (
        not isinstance(row_count, int)
        or isinstance(row_count, bool)
        or row_count < 0
    ):
        _source_verify_schema_issue(
            collector,
            "Source verify row_count must be a non-negative integer.",
        )

    head_hash = payload.get("head_hash")
    row_count_is_valid = (
        isinstance(row_count, int)
        and not isinstance(row_count, bool)
        and row_count >= 0
    )
    if row_count_is_valid:
        if row_count == 0 and head_hash != "":
            _source_verify_schema_issue(
                collector,
                "Source verify head_hash must be empty when row_count is zero.",
            )
        elif row_count > 0 and not is_lower_sha256(head_hash):
            _source_verify_schema_issue(
                collector,
                "Source verify head_hash must be lowercase SHA-256 when rows exist.",
            )
    elif not isinstance(head_hash, str):
        _source_verify_schema_issue(
            collector,
            "Source verify head_hash must be a string.",
        )

    hmac_enabled = payload.get("hmac_enabled")
    if not isinstance(hmac_enabled, bool):
        _source_verify_schema_issue(
            collector,
            "Source verify hmac_enabled must be a boolean.",
        )
    elif hmac_enabled:
        collector.add(
            0,
            "SOURCE_VERIFY_HMAC_UNSUPPORTED",
            "HMAC-enabled source verification is outside the Phase 5A contract.",
            stored_value=True,
            recomputed_value=False,
        )

    errors = payload.get("errors")
    if not isinstance(errors, list):
        _source_verify_schema_issue(
            collector,
            "Source verify errors must be an array.",
        )
    elif errors:
        collector.add(
            0,
            "SOURCE_VERIFY_ERRORS_PRESENT",
            "Source verify errors must be empty.",
        )

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        _source_verify_schema_issue(
            collector,
            "Source verify policy must be an object.",
        )
    elif policy != SOURCE_POLICY:
        collector.add(
            0,
            "SOURCE_VERIFY_POLICY_MISMATCH",
            "Source verify policy does not match the advisory-only contract.",
        )

    return payload


def evaluate_sources(arl_text: str, source_verify_text: str) -> dict[str, Any]:
    collector = IssueCollector()
    runtime = _parse_runtime_rows(arl_text, collector)
    source_verify = _parse_source_verify(source_verify_text, collector)

    source_row_count = source_verify.get("row_count")
    if (
        isinstance(source_row_count, int)
        and not isinstance(source_row_count, bool)
        and source_row_count >= 0
        and source_row_count != runtime["row_count"]
    ):
        collector.add(
            0,
            "SOURCE_VERIFY_ROW_COUNT_MISMATCH",
            "Source verify row count does not match runtime ARL rows.",
            stored_value=source_row_count,
            recomputed_value=runtime["row_count"],
        )

    source_head_hash = source_verify.get("head_hash")
    if is_lower_sha256(source_head_hash) and not (
        source_head_hash == runtime["stored_head_hash"]
        and source_head_hash == runtime["recomputed_head_hash"]
    ):
        collector.add(
            0,
            "SOURCE_VERIFY_HEAD_HASH_MISMATCH",
            "Source verify head hash does not match stored and recomputed heads.",
            stored_value=source_head_hash,
            recomputed_value=runtime["recomputed_head_hash"],
        )

    verified = not collector.issues
    return {
        **runtime,
        "source_verify_head_hash": safe_hash(source_head_hash),
        "source_verify_verified": source_verify.get("verified") is True,
        "hmac_enabled": source_verify.get("hmac_enabled") is True,
        "verified": verified,
        "issues": [asdict(issue) for issue in collector.issues],
        "reason_codes": collector.reason_codes,
    }


def build_result(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "verified": evaluation["verified"],
        "decision": (
            "VERIFIED" if evaluation["verified"] else "INTEGRITY_CHECK_FAILED"
        ),
        "summary": {
            "rows_read": evaluation["row_count"],
            "run_id": evaluation["run_id"],
            "issue_count": len(evaluation["issues"]),
            "reason_codes": evaluation["reason_codes"],
            "stored_head_hash": evaluation["stored_head_hash"],
            "recomputed_head_hash": evaluation["recomputed_head_hash"],
            "source_verify_head_hash": evaluation["source_verify_head_hash"],
            "source_verify_verified": evaluation["source_verify_verified"],
            "hmac_present": evaluation["hmac_present"],
            "hmac_enabled": evaluation["hmac_enabled"],
            "authenticity_claimed": False,
            "human_review_required": True,
        },
        "issues": evaluation["issues"],
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }


def build_source_binding(
    evaluation: dict[str, Any],
    source_arl_sha256: str,
    source_verify_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_BINDING_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "source_arl_filename": ARL_FILENAME,
        "source_verify_filename": SOURCE_VERIFY_FILENAME,
        "source_arl_sha256": source_arl_sha256,
        "source_verify_sha256": source_verify_sha256,
        "row_count": evaluation["row_count"],
        "run_id": evaluation["run_id"],
        "stored_head_hash": evaluation["stored_head_hash"],
        "recomputed_head_hash": evaluation["recomputed_head_hash"],
        "source_verify_head_hash": evaluation["source_verify_head_hash"],
        "hmac_present": evaluation["hmac_present"],
        "hmac_enabled": evaluation["hmac_enabled"],
        "authenticity_claimed": False,
    }


def build_report(result: dict[str, Any], source_binding: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Tasukeru Runtime ARL Hash-Chain Verification Report",
        "",
        "## Verification Result",
        "",
        f"- Verified: `{'true' if result['verified'] else 'false'}`",
        f"- Decision: `{result['decision']}`",
        "",
        "## Summary",
        "",
        f"- Tool: `{result['tool']}`",
        f"- Rows read: `{summary['rows_read']}`",
        f"- Issue count: `{summary['issue_count']}`",
        f"- Stored head hash: `{summary['stored_head_hash']}`",
        f"- Recomputed head hash: `{summary['recomputed_head_hash']}`",
        f"- Source verify head hash: `{summary['source_verify_head_hash']}`",
        "",
        "## Source Binding",
        "",
        f"- `{ARL_FILENAME}` SHA-256: `{source_binding['source_arl_sha256']}`",
        (
            f"- `{SOURCE_VERIFY_FILENAME}` SHA-256: "
            f"`{source_binding['source_verify_sha256']}`"
        ),
        "",
        "## Reason Codes",
        "",
    ]
    if summary["reason_codes"]:
        for reason_code in summary["reason_codes"]:
            lines.append(f"- `{reason_code}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in SAFETY_BOUNDARY.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"- {name}: `{rendered}`")
    lines.extend(
        [
            "",
            "## Human Review",
            "",
            "This verifier is advisory-only and does not modify runtime ARL source files.",
            "HMAC input is unsupported, authenticity is not claimed, and final review remains human-controlled.",
            "",
        ]
    )
    return "\n".join(lines)


def source_binding_is_consistent(
    result: dict[str, Any],
    source_binding: dict[str, Any],
) -> bool:
    expected_keys = (
        "schema_version",
        "tool",
        "source_arl_filename",
        "source_verify_filename",
        "source_arl_sha256",
        "source_verify_sha256",
        "row_count",
        "run_id",
        "stored_head_hash",
        "recomputed_head_hash",
        "source_verify_head_hash",
        "hmac_present",
        "hmac_enabled",
        "authenticity_claimed",
    )
    summary = result.get("summary")
    return (
        tuple(source_binding) == expected_keys
        and isinstance(summary, dict)
        and source_binding.get("schema_version") == SOURCE_BINDING_SCHEMA_VERSION
        and source_binding.get("tool") == TOOL_NAME
        and source_binding.get("source_arl_filename") == ARL_FILENAME
        and source_binding.get("source_verify_filename") == SOURCE_VERIFY_FILENAME
        and is_lower_sha256(source_binding.get("source_arl_sha256"))
        and is_lower_sha256(source_binding.get("source_verify_sha256"))
        and source_binding.get("row_count") == summary.get("rows_read")
        and source_binding.get("run_id") == summary.get("run_id")
        and source_binding.get("stored_head_hash")
        == summary.get("stored_head_hash")
        and source_binding.get("recomputed_head_hash")
        == summary.get("recomputed_head_hash")
        and source_binding.get("source_verify_head_hash")
        == summary.get("source_verify_head_hash")
        and source_binding.get("hmac_present") == summary.get("hmac_present")
        and source_binding.get("hmac_enabled") == summary.get("hmac_enabled")
        and source_binding.get("authenticity_claimed") is False
    )


def validate_output_directory(output_dir: Path) -> None:
    try:
        if output_dir.is_symlink():
            raise VerifierOperationalError(
                "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
                "Output directory must not be a symbolic link.",
            )
        if output_dir.exists() and not output_dir.is_dir():
            raise VerifierOperationalError(
                "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
                "Output path must be a directory.",
            )
        if not output_dir.exists():
            return
        for entry in output_dir.iterdir():
            if (
                entry.name not in EXPECTED_OUTPUT_FILES
                or not entry.is_file()
                or entry.is_symlink()
            ):
                raise VerifierOperationalError(
                    "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
                    "Output directory contains an unknown entry.",
                )
    except VerifierOperationalError:
        raise
    except OSError as exc:
        raise VerifierOperationalError(
            "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
            "Output directory cannot be inspected.",
        ) from exc


def atomic_write_text(path: Path, value: str) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_created = False
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as handle:
            temporary_created = True
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except OSError as exc:
        if temporary_created:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise VerifierOperationalError(
            "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
            "Runtime ARL verification artifact cannot be written safely.",
        ) from exc


def build_output_verify(
    result: dict[str, Any],
    source_binding: dict[str, Any],
    report: str,
    output_dir: Path,
) -> dict[str, Any]:
    try:
        existing_entries = list(output_dir.iterdir())
        actual_output_files = sorted(
            {entry.name for entry in existing_entries} | {VERIFY_FILENAME}
        )
        files_consistent = (
            actual_output_files == list(EXPECTED_OUTPUT_FILES)
            and all(
                entry.is_file() and not entry.is_symlink()
                for entry in existing_entries
            )
        )
        if not files_consistent:
            raise VerifierOperationalError(
                "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
                "Runtime ARL verification output inventory is inconsistent.",
            )

        output_sha256 = {
            filename: file_sha256(output_dir / filename)
            for filename in HASHED_OUTPUT_FILES
        }
        result_consistent = (
            (output_dir / RESULT_FILENAME).read_bytes()
            == json_dump(result).encode("utf-8")
        )
        source_binding_consistent = (
            source_binding_is_consistent(result, source_binding)
            and (output_dir / SOURCE_BINDING_FILENAME).read_bytes()
            == json_dump(source_binding).encode("utf-8")
        )
        report_consistent = (
            (output_dir / REPORT_FILENAME).read_bytes() == report.encode("utf-8")
        )
        safety_boundary_consistent = result.get("safety_boundary") == SAFETY_BOUNDARY
        if not (
            result_consistent
            and source_binding_consistent
            and report_consistent
            and safety_boundary_consistent
        ):
            raise VerifierOperationalError(
                "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
                "Runtime ARL verification output consistency cannot be established.",
            )
    except VerifierOperationalError:
        raise
    except Exception as exc:
        raise VerifierOperationalError(
            "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
            "Runtime ARL verification outputs cannot be verified after writing.",
        ) from exc

    result_verified = result.get("verified") is True
    errors = list(result["summary"]["reason_codes"])
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "verified": (
            result_verified
            and source_binding_consistent
            and report_consistent
            and safety_boundary_consistent
            and files_consistent
            and not errors
        ),
        "expected_output_files": list(EXPECTED_OUTPUT_FILES),
        "actual_output_files": actual_output_files,
        "output_sha256": output_sha256,
        "result_verified": result_verified,
        "source_binding_consistent": source_binding_consistent,
        "report_consistent": report_consistent,
        "safety_boundary_consistent": safety_boundary_consistent,
        "errors": errors,
    }


def write_artifacts(
    result: dict[str, Any],
    source_binding: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = build_report(result, source_binding)
        atomic_write_text(output_dir / RESULT_FILENAME, json_dump(result))
        atomic_write_text(
            output_dir / SOURCE_BINDING_FILENAME,
            json_dump(source_binding),
        )
        atomic_write_text(output_dir / REPORT_FILENAME, report)
        verify = build_output_verify(
            result,
            source_binding,
            report,
            output_dir,
        )
        atomic_write_text(output_dir / VERIFY_FILENAME, json_dump(verify))
        return verify
    except VerifierOperationalError:
        raise
    except OSError as exc:
        raise VerifierOperationalError(
            "RUNTIME_ARL_OUTPUT_WRITE_FAILED",
            "Runtime ARL verification artifacts cannot be written.",
        ) from exc


def run_verifier(arl_path: Path, source_verify_path: Path, output_dir: Path) -> dict[str, Any]:
    validate_output_directory(output_dir)
    arl_bytes = _read_source(arl_path, "RUNTIME_ARL_NOT_FOUND", "Runtime ARL")
    source_verify_bytes = _read_source(
        source_verify_path,
        "SOURCE_VERIFY_NOT_FOUND",
        "Source verify artifact",
    )
    arl_text = _decode_source(
        arl_bytes,
        "RUNTIME_ARL_UTF8_INVALID",
        "Runtime ARL",
    )
    source_verify_text = _decode_source(
        source_verify_bytes,
        "SOURCE_VERIFY_UTF8_INVALID",
        "Source verify artifact",
    )
    evaluation = evaluate_sources(arl_text, source_verify_text)
    result = build_result(evaluation)
    source_binding = build_source_binding(
        evaluation,
        sha256_bytes(arl_bytes),
        sha256_bytes(source_verify_bytes),
    )
    verify = write_artifacts(result, source_binding, output_dir)
    return {
        "result": result,
        "source_binding": source_binding,
        "verify": verify,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a runtime Tasukeru ARL hash chain without modifying it."
    )
    parser.add_argument("--arl", type=Path, required=True)
    parser.add_argument("--source-verify", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run = run_verifier(args.arl, args.source_verify, args.out_dir)
    except VerifierOperationalError as exc:
        print(f"{exc.reason_code}: {exc.message}", file=sys.stderr)
        return 2
    except Exception:
        print(
            "RUNTIME_ARL_UNEXPECTED_ERROR: An unexpected operational error occurred.",
            file=sys.stderr,
        )
        return 2

    verify = run["verify"]
    print("Tasukeru Runtime ARL Hash-Chain Verifier v0.1")
    print(f"verified: {verify['verified']}")
    print(f"result: {RESULT_FILENAME}")
    print(f"source_binding: {SOURCE_BINDING_FILENAME}")
    print(f"report: {REPORT_FILENAME}")
    print(f"verify: {VERIFY_FILENAME}")
    return 0 if verify["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
