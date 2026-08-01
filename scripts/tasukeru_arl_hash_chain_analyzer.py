#!/usr/bin/env python3
"""Deterministic, advisory-only analyzer for Patch 13 hash-chain artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Sequence


RESULT_SCHEMA_VERSION = "tasukeru-arl-hash-chain-analyzer-v0.1"
GRAPH_SCHEMA_VERSION = "tasukeru-arl-hash-chain-graph-v0.1"
VERIFY_SCHEMA_VERSION = "tasukeru-arl-hash-chain-analyzer-verify-v0.1"
SOURCE_RESULT_SCHEMA_VERSION = "tasukeru-arl-hash-chain-stress-v0.1"
SOURCE_VERIFY_SCHEMA_VERSION = "tasukeru-arl-hash-chain-stress-verify-v0.1"
SOURCE_MANIFEST_SCHEMA_VERSION = "tasukeru-arl-hash-chain-fixture-manifest-v0.1"
DETERMINISTIC_GENERATED_AT_UTC = "1970-01-01T00:00:00Z"

RESULT_FILENAME = "tasukeru_arl_hash_chain_analyzer_result.json"
GRAPH_FILENAME = "tasukeru_arl_hash_chain_graph.json"
REPORT_FILENAME = "tasukeru_arl_hash_chain_analyzer_report.md"
VERIFY_FILENAME = "tasukeru_arl_hash_chain_analyzer_verify.json"

SOURCE_RESULT_FILENAME = "tasukeru_arl_hash_chain_stress_result.json"
SOURCE_REPORT_FILENAME = "tasukeru_arl_hash_chain_stress_report.md"
SOURCE_VERIFY_FILENAME = "tasukeru_arl_hash_chain_stress_verify.json"
LOGICAL_SOURCE_ROOT = "stress_results/arl_hash_chain"
LOGICAL_SOURCE_ID = "patch_13_arl_hash_chain_stress_results"
ROOT_NODE_ID = f"hash_chain_artifacts:{LOGICAL_SOURCE_ID}"

EXPECTED_SOURCE_FILES = frozenset(
    {
        SOURCE_RESULT_FILENAME,
        SOURCE_REPORT_FILENAME,
        SOURCE_VERIFY_FILENAME,
    }
)
EXPECTED_OUTPUT_FILES = frozenset(
    {
        RESULT_FILENAME,
        GRAPH_FILENAME,
        REPORT_FILENAME,
        VERIFY_FILENAME,
    }
)

CANONICAL_HEAD_HASH = (
    "4d7a836b8a1683f3dcc29c8f7d554503e8e5612aa0d13dec1ce702035d46cd4c"
)
CANONICAL_MANIFEST_SHA256 = (
    "35fc86d602cb8e7943c673499b4ed51b51a12516c2fb653d59d154485de53983"
)
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

SOURCE_HASH_CONTRACT = {
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

SOURCE_SAFETY_BOUNDARY = MappingProxyType(
    {
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
)

SAFETY_BOUNDARY = MappingProxyType(
    {
        "advisory_only": True,
        "human_review_required": True,
        "ai_api_call": False,
        "api_key_required": False,
        "github_actions_secrets_required": False,
        "external_ai_provider": False,
        "billable_action": False,
        "network_call": False,
        "automatic_repair": False,
        "automatic_retry": False,
        "automatic_apply": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pr": False,
        "automatic_merge": False,
        "automatic_deploy": False,
        "runtime_arl_modified": False,
        "existing_patch_4_analyzer_modified": False,
        "authenticity_claimed": False,
    }
)

INTEGRITY_REASON_CODES = frozenset(
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

CANONICAL_COUNTS = MappingProxyType(
    {
        "total_cases": 7,
        "passed_cases": 7,
        "failed_cases": 0,
        "valid_cases": 1,
        "expected_tamper_cases": 6,
        "tamper_cases_detected": 6,
        "unexpected_valid_cases": 0,
        "input_invalid_cases": 0,
        "total_rows_read": 27,
        "total_integrity_errors": 19,
    }
)


def _issue_contract(
    issue_ordinal: int,
    line_number: int,
    reason_code: str,
    detail: str,
    stored_value: Any,
    recomputed_value: Any,
) -> MappingProxyType:
    return MappingProxyType(
        {
            "issue_ordinal": issue_ordinal,
            "line_number": line_number,
            "reason_code": reason_code,
            "detail": detail,
            "stored_value": stored_value,
            "recomputed_value": recomputed_value,
        }
    )


def _head_hash_contract(
    stored_head_hash: str,
    recomputed_head_hash: str,
) -> MappingProxyType:
    return MappingProxyType(
        {
            "stored_head_hash": stored_head_hash,
            "recomputed_head_hash": recomputed_head_hash,
        }
    )


def _case_contract(
    case_id: str,
    fixture_name: str,
    expected_outcome: str,
    primary: str,
    additional: Sequence[str],
    reasons: Sequence[str],
    row_count: int,
    integrity_issue_count: int,
    source_issue_count: int,
    first_error_line: int | None,
) -> MappingProxyType:
    return MappingProxyType(
        {
            "case_id": case_id,
            "fixture_name": fixture_name,
            "expected_outcome": expected_outcome,
            "actual_outcome": expected_outcome,
            "classification": (
                "EXPECTED_CANONICAL_VALIDATION"
                if expected_outcome == "CHAIN_VALID"
                else "EXPECTED_TAMPER_DETECTION"
            ),
            "expected_primary_reason_code": primary,
            "expected_additional_reason_codes": tuple(additional),
            "reason_codes": tuple(reasons),
            "expected_row_count": row_count,
            "integrity_error_count": integrity_issue_count,
            "source_issue_count": source_issue_count,
            "first_error_line": first_error_line,
        }
    )


CANONICAL_CASE_CONTRACTS = (
    _case_contract(
        "valid_chain",
        "valid_chain.jsonl",
        "CHAIN_VALID",
        "ARL_CHAIN_VALID",
        (),
        ("ARL_CHAIN_VALID",),
        4,
        0,
        1,
        None,
    ),
    _case_contract(
        "middle_row_content_tampered",
        "middle_row_content_tampered.jsonl",
        "TAMPER_DETECTED",
        "ARL_ROW_HASH_MISMATCH",
        ("ARL_CHAIN_HASH_MISMATCH", "ARL_PREV_HASH_MISMATCH"),
        (
            "ARL_ROW_HASH_MISMATCH",
            "ARL_CHAIN_HASH_MISMATCH",
            "ARL_PREV_HASH_MISMATCH",
        ),
        4,
        3,
        3,
        2,
    ),
    _case_contract(
        "middle_row_chain_hash_tampered",
        "middle_row_chain_hash_tampered.jsonl",
        "TAMPER_DETECTED",
        "ARL_CHAIN_HASH_MISMATCH",
        (),
        ("ARL_CHAIN_HASH_MISMATCH",),
        4,
        1,
        1,
        2,
    ),
    _case_contract(
        "middle_row_prev_hash_tampered",
        "middle_row_prev_hash_tampered.jsonl",
        "TAMPER_DETECTED",
        "ARL_PREV_HASH_MISMATCH",
        ("ARL_ROW_HASH_MISMATCH", "ARL_CHAIN_HASH_MISMATCH"),
        (
            "ARL_PREV_HASH_MISMATCH",
            "ARL_ROW_HASH_MISMATCH",
            "ARL_CHAIN_HASH_MISMATCH",
        ),
        4,
        4,
        4,
        2,
    ),
    _case_contract(
        "final_row_content_tampered",
        "final_row_content_tampered.jsonl",
        "TAMPER_DETECTED",
        "ARL_ROW_HASH_MISMATCH",
        ("ARL_CHAIN_HASH_MISMATCH", "ARL_HEAD_HASH_MISMATCH"),
        (
            "ARL_ROW_HASH_MISMATCH",
            "ARL_CHAIN_HASH_MISMATCH",
            "ARL_HEAD_HASH_MISMATCH",
        ),
        4,
        3,
        3,
        4,
    ),
    _case_contract(
        "rows_reordered",
        "rows_reordered.jsonl",
        "TAMPER_DETECTED",
        "ARL_SEQUENCE_MISMATCH",
        ("ARL_PREV_HASH_MISMATCH",),
        ("ARL_SEQUENCE_MISMATCH", "ARL_PREV_HASH_MISMATCH"),
        4,
        5,
        5,
        2,
    ),
    _case_contract(
        "row_deleted",
        "row_deleted.jsonl",
        "TAMPER_DETECTED",
        "ARL_SEQUENCE_MISMATCH",
        ("ARL_PREV_HASH_MISMATCH",),
        ("ARL_SEQUENCE_MISMATCH", "ARL_PREV_HASH_MISMATCH"),
        3,
        3,
        3,
        2,
    ),
)
CANONICAL_CASE_IDS = tuple(case["case_id"] for case in CANONICAL_CASE_CONTRACTS)

CANONICAL_ISSUE_CONTRACTS = MappingProxyType(
    {
        "valid_chain": (
            _issue_contract(
                1,
                0,
                "ARL_CHAIN_VALID",
                "The ARL hash chain is valid.",
                None,
                None,
            ),
        ),
        "middle_row_content_tampered": (
            _issue_contract(
                1,
                2,
                "ARL_ROW_HASH_MISMATCH",
                "Stored row_hash does not match the recomputed row hash.",
                "a757c406baaaaeaaed21ed667246faa1599754f5d0920f0d4964e0d36df52cfd",
                "cbc982de9d36116d463020133d9462703c5e5a7909a211913b9af48c97b4fa7c",
            ),
            _issue_contract(
                2,
                2,
                "ARL_CHAIN_HASH_MISMATCH",
                "Stored chain_hash does not match the recomputed chain hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "2afe493a93164c4c67746ed6d85cb4f1860813013df0d9af36b16c88fc2da036",
            ),
            _issue_contract(
                3,
                3,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "2afe493a93164c4c67746ed6d85cb4f1860813013df0d9af36b16c88fc2da036",
            ),
        ),
        "middle_row_chain_hash_tampered": (
            _issue_contract(
                1,
                2,
                "ARL_CHAIN_HASH_MISMATCH",
                "Stored chain_hash does not match the recomputed chain hash.",
                "047c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
            ),
        ),
        "middle_row_prev_hash_tampered": (
            _issue_contract(
                1,
                2,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "0ea9862ab6eb2d9bbc900ba7e796a70c3d80df357a1061cae2c7e7dd20c23ef3",
                "cea9862ab6eb2d9bbc900ba7e796a70c3d80df357a1061cae2c7e7dd20c23ef3",
            ),
            _issue_contract(
                2,
                2,
                "ARL_ROW_HASH_MISMATCH",
                "Stored row_hash does not match the recomputed row hash.",
                "a757c406baaaaeaaed21ed667246faa1599754f5d0920f0d4964e0d36df52cfd",
                "3d2dfa51c59c9243c60c877d53e49417fb918d4c1096c86d959e94b6281b0eeb",
            ),
            _issue_contract(
                3,
                2,
                "ARL_CHAIN_HASH_MISMATCH",
                "Stored chain_hash does not match the recomputed chain hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "c9e49bf26b36a5459b5f2e56f57698757aa6462f5f8cf5cd7cac97fbfbd2fa6b",
            ),
            _issue_contract(
                4,
                3,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "c9e49bf26b36a5459b5f2e56f57698757aa6462f5f8cf5cd7cac97fbfbd2fa6b",
            ),
        ),
        "final_row_content_tampered": (
            _issue_contract(
                1,
                4,
                "ARL_ROW_HASH_MISMATCH",
                "Stored row_hash does not match the recomputed row hash.",
                "42af5bd70a472767a02c26a4ac92cfc23cea9514ee092081ca123d08c2cbcb92",
                "8cf02f9e3025871ed75ba96058e51b589ef6d4bca0c515d3aa25be3fb9d12280",
            ),
            _issue_contract(
                2,
                4,
                "ARL_CHAIN_HASH_MISMATCH",
                "Stored chain_hash does not match the recomputed chain hash.",
                "4d7a836b8a1683f3dcc29c8f7d554503e8e5612aa0d13dec1ce702035d46cd4c",
                "19ea9312e2c0c50f536f29681027579d9cfd8461bd39fee35eaa1e623229baa3",
            ),
            _issue_contract(
                3,
                4,
                "ARL_HEAD_HASH_MISMATCH",
                "Recomputed head hash does not match the fixture manifest.",
                "19ea9312e2c0c50f536f29681027579d9cfd8461bd39fee35eaa1e623229baa3",
                "4d7a836b8a1683f3dcc29c8f7d554503e8e5612aa0d13dec1ce702035d46cd4c",
            ),
        ),
        "rows_reordered": (
            _issue_contract(
                1,
                2,
                "ARL_SEQUENCE_MISMATCH",
                "seq must begin at 1 and increase by exactly 1.",
                3,
                2,
            ),
            _issue_contract(
                2,
                2,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "cea9862ab6eb2d9bbc900ba7e796a70c3d80df357a1061cae2c7e7dd20c23ef3",
            ),
            _issue_contract(
                3,
                3,
                "ARL_SEQUENCE_MISMATCH",
                "seq must begin at 1 and increase by exactly 1.",
                2,
                3,
            ),
            _issue_contract(
                4,
                3,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "cea9862ab6eb2d9bbc900ba7e796a70c3d80df357a1061cae2c7e7dd20c23ef3",
                "a94f54864eff401cd740c05844d0145145f5a1c47b183bbcffb5bcbebe940f3c",
            ),
            _issue_contract(
                5,
                4,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "a94f54864eff401cd740c05844d0145145f5a1c47b183bbcffb5bcbebe940f3c",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
            ),
        ),
        "row_deleted": (
            _issue_contract(
                1,
                2,
                "ARL_SEQUENCE_MISMATCH",
                "seq must begin at 1 and increase by exactly 1.",
                3,
                2,
            ),
            _issue_contract(
                2,
                2,
                "ARL_PREV_HASH_MISMATCH",
                "prev_hash does not match the previous recomputed chain_hash.",
                "e47c7072dc9e57d7eed535d2dba00b149d448c74a2531f4abf63726a57616e17",
                "cea9862ab6eb2d9bbc900ba7e796a70c3d80df357a1061cae2c7e7dd20c23ef3",
            ),
            _issue_contract(
                3,
                3,
                "ARL_SEQUENCE_MISMATCH",
                "seq must begin at 1 and increase by exactly 1.",
                4,
                3,
            ),
        ),
    }
)

CANONICAL_HEAD_HASH_CONTRACTS = MappingProxyType(
    {
        "valid_chain": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
        "middle_row_content_tampered": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
        "middle_row_chain_hash_tampered": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
        "middle_row_prev_hash_tampered": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
        "final_row_content_tampered": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            "19ea9312e2c0c50f536f29681027579d9cfd8461bd39fee35eaa1e623229baa3",
        ),
        "rows_reordered": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
        "row_deleted": _head_hash_contract(
            CANONICAL_HEAD_HASH,
            CANONICAL_HEAD_HASH,
        ),
    }
)

SOURCE_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "generated_at_utc",
        "mode",
        "hash_contract",
        "fixture_directory",
        "manifest_path",
        "manifest_schema_version",
        "manifest_sha256",
        "safety_boundary",
        "cases",
        "counts",
        "checks",
        "overall_outcome",
        "overall_reason_codes",
        "failure_detail",
        "verified",
    }
)
SOURCE_VERIFY_FIELDS = frozenset(
    {
        "schema_version",
        "generated_at_utc",
        "verified",
        "checks",
        "counts",
        "result_sha256",
        "report_sha256",
        "manifest_sha256",
        "safety_boundary",
        "hmac_enabled",
        "authenticity_claimed",
    }
)
SOURCE_CASE_FIELDS = frozenset(
    {
        "case_id",
        "fixture_name",
        "expected_outcome",
        "actual_outcome",
        "expected_primary_reason_code",
        "expected_additional_reason_codes",
        "reason_codes",
        "file_exists",
        "line_count",
        "parsed_row_count",
        "expected_row_count",
        "stored_head_hash",
        "recomputed_head_hash",
        "first_error_line",
        "integrity_error_count",
        "expected_condition_detected",
        "reason_code_sequence_valid",
        "passed",
        "issues",
    }
)
SOURCE_ISSUE_FIELDS = frozenset(
    {
        "line_number",
        "reason_code",
        "detail",
        "stored_value",
        "recomputed_value",
    }
)
SOURCE_RESULT_CHECK_KEYS = frozenset(
    {
        "manifest_valid",
        "required_cases_present",
        "canonical_valid_chain_passed",
        "expected_tamper_cases_detected",
        "reason_code_contract_valid",
        "counts_consistent",
        "safety_boundary_verified",
    }
)
SOURCE_VERIFY_CHECK_KEYS = SOURCE_RESULT_CHECK_KEYS | {
    "output_files_exist",
    "output_filename_set_exact",
}


class AnalyzerOperationalError(RuntimeError):
    """Stable, path-free operational failure."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class SourceDocuments:
    result: dict[str, Any]
    verify: dict[str, Any]
    report_text: str
    raw_bytes: dict[str, bytes]
    sha256: dict[str, str]


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_token(value: Any) -> str:
    text = str(value if value is not None else "unknown").strip().lower()
    token = "_".join(
        part
        for part in "".join(char if char.isalnum() else "_" for char in text).split("_")
        if part
    )
    return token[:80] or "unknown"


def stable_id(kind: str, *parts: Any) -> str:
    raw_parts = [str(part) for part in parts]
    payload = json.dumps([kind, *raw_parts], ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    label = stable_token(raw_parts[0] if raw_parts else kind)
    return f"{kind}:{label}:{digest}"


def write_text_lf(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(normalized)


def _decode_utf8(data: bytes, reason_code: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AnalyzerOperationalError(
            reason_code,
            "A required source document is not valid UTF-8.",
        ) from exc


def _parse_json_object(text: str, reason_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnalyzerOperationalError(
            reason_code,
            "A required source JSON document is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise AnalyzerOperationalError(
            reason_code,
            "A required source JSON document must be an object.",
        )
    return payload


def validate_input_directory(input_dir: Path) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_INPUT_DIRECTORY_INVALID",
            "The input directory is missing or is not a directory.",
        )
    try:
        entries = list(input_dir.iterdir())
    except OSError as exc:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_INPUT_DIRECTORY_UNREADABLE",
            "The input directory cannot be read.",
        ) from exc
    actual_names = {entry.name for entry in entries}
    if actual_names != EXPECTED_SOURCE_FILES or any(not entry.is_file() for entry in entries):
        missing = EXPECTED_SOURCE_FILES - actual_names
        extra = actual_names - EXPECTED_SOURCE_FILES
        reason = (
            "ARL_ANALYZER_SOURCE_FILE_MISSING"
            if missing
            else "ARL_ANALYZER_UNEXPECTED_SOURCE_ENTRY"
        )
        raise AnalyzerOperationalError(
            reason,
            "The input directory must contain exactly the three required source files.",
        )


def validate_output_directory(input_dir: Path, output_dir: Path) -> None:
    try:
        input_resolved = input_dir.resolve()
        output_resolved = output_dir.resolve()
    except OSError as exc:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_PATH_RESOLUTION_FAILED",
            "Input and output paths cannot be resolved.",
        ) from exc
    if output_resolved == input_resolved or input_resolved in output_resolved.parents:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_INPUT_OUTPUT_OVERLAP",
            "The output directory must be separate from the input directory.",
        )
    if output_dir.exists():
        if not output_dir.is_dir():
            raise AnalyzerOperationalError(
                "ARL_ANALYZER_OUTPUT_DIRECTORY_INVALID",
                "The output path exists and is not a directory.",
            )
        try:
            if any(output_dir.iterdir()):
                raise AnalyzerOperationalError(
                    "ARL_ANALYZER_OUTPUT_DIRECTORY_NOT_EMPTY",
                    "The output directory must be empty before generation.",
                )
        except OSError as exc:
            raise AnalyzerOperationalError(
                "ARL_ANALYZER_OUTPUT_DIRECTORY_UNREADABLE",
                "The output directory cannot be inspected.",
            ) from exc


def load_source_documents(input_dir: Path) -> SourceDocuments:
    validate_input_directory(input_dir)
    raw_bytes: dict[str, bytes] = {}
    for filename in sorted(EXPECTED_SOURCE_FILES):
        try:
            raw_bytes[filename] = (input_dir / filename).read_bytes()
        except OSError as exc:
            raise AnalyzerOperationalError(
                "ARL_ANALYZER_SOURCE_READ_FAILED",
                "A required source document cannot be read.",
            ) from exc

    result_text = _decode_utf8(
        raw_bytes[SOURCE_RESULT_FILENAME],
        "ARL_ANALYZER_RESULT_UTF8_INVALID",
    )
    report_text = _decode_utf8(
        raw_bytes[SOURCE_REPORT_FILENAME],
        "ARL_ANALYZER_REPORT_UTF8_INVALID",
    )
    verify_text = _decode_utf8(
        raw_bytes[SOURCE_VERIFY_FILENAME],
        "ARL_ANALYZER_VERIFY_UTF8_INVALID",
    )
    result = _parse_json_object(result_text, "ARL_ANALYZER_RESULT_JSON_INVALID")
    verify = _parse_json_object(verify_text, "ARL_ANALYZER_VERIFY_JSON_INVALID")
    if result.get("schema_version") != SOURCE_RESULT_SCHEMA_VERSION:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_RESULT_SCHEMA_UNSUPPORTED",
            "The source result schema version is unsupported.",
        )
    if verify.get("schema_version") != SOURCE_VERIFY_SCHEMA_VERSION:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_VERIFY_SCHEMA_UNSUPPORTED",
            "The source verify schema version is unsupported.",
        )
    return SourceDocuments(
        result=result,
        verify=verify,
        report_text=report_text,
        raw_bytes=raw_bytes,
        sha256={
            filename: sha256_bytes(data)
            for filename, data in sorted(raw_bytes.items())
        },
    )


def _is_boolean_map(value: Any, expected_keys: frozenset[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == expected_keys
        and all(isinstance(item, bool) for item in value.values())
        and all(value.values())
    )


def _is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _reason_role(
    reason_code: str,
    order: int,
    primary: str,
    allowed_additional: Sequence[str],
) -> str:
    if order == 1 and reason_code == primary:
        return "primary"
    if order > 1 and reason_code in allowed_additional:
        return "additional"
    return "unexpected"


def normalize_case(source_case: Any) -> dict[str, Any]:
    case = _dict_value(source_case)
    primary = str(case.get("expected_primary_reason_code", ""))
    additional = [
        str(value) for value in _list_value(case.get("expected_additional_reason_codes"))
    ]
    reasons = []
    for order, value in enumerate(_list_value(case.get("reason_codes")), start=1):
        reason_code = str(value)
        reasons.append(
            {
                "reason_code": reason_code,
                "order": order,
                "role": _reason_role(reason_code, order, primary, additional),
            }
        )

    issues = []
    for ordinal, value in enumerate(_list_value(case.get("issues")), start=1):
        issue = _dict_value(value)
        reason_code = str(issue.get("reason_code", ""))
        issues.append(
            {
                "issue_ordinal": ordinal,
                "line_number": issue.get("line_number"),
                "reason_code": reason_code,
                "detail": issue.get("detail"),
                "stored_value": issue.get("stored_value"),
                "recomputed_value": issue.get("recomputed_value"),
                "is_integrity_issue": reason_code in INTEGRITY_REASON_CODES,
            }
        )

    case_id = str(case.get("case_id", ""))
    classification = next(
        (
            contract["classification"]
            for contract in CANONICAL_CASE_CONTRACTS
            if contract["case_id"] == case_id
        ),
        "UNRECOGNIZED_CASE",
    )
    return {
        "case_id": case_id,
        "fixture_name": case.get("fixture_name"),
        "classification": classification,
        "expected_outcome": case.get("expected_outcome"),
        "actual_outcome": case.get("actual_outcome"),
        "expected_primary_reason_code": primary,
        "expected_additional_reason_codes": additional,
        "reasons": reasons,
        "reason_code_sequence_valid": case.get("reason_code_sequence_valid") is True,
        "file_exists": case.get("file_exists") is True,
        "line_count": case.get("line_count"),
        "parsed_row_count": case.get("parsed_row_count"),
        "expected_row_count": case.get("expected_row_count"),
        "expected_canonical_head_hash": CANONICAL_HEAD_HASH,
        "stored_head_hash": case.get("stored_head_hash"),
        "recomputed_head_hash": case.get("recomputed_head_hash"),
        "first_error_line": case.get("first_error_line"),
        "integrity_error_count": case.get("integrity_error_count"),
        "expected_condition_detected": case.get("expected_condition_detected") is True,
        "passed": case.get("passed") is True,
        "issues": issues,
    }


def compute_counts_from_cases(cases: Sequence[Any]) -> dict[str, int]:
    case_dicts = [_dict_value(case) for case in cases]
    return {
        "total_cases": len(case_dicts),
        "passed_cases": sum(case.get("passed") is True for case in case_dicts),
        "failed_cases": sum(case.get("passed") is not True for case in case_dicts),
        "valid_cases": sum(
            case.get("actual_outcome") == "CHAIN_VALID" for case in case_dicts
        ),
        "expected_tamper_cases": sum(
            case.get("expected_outcome") == "TAMPER_DETECTED"
            for case in case_dicts
        ),
        "tamper_cases_detected": sum(
            case.get("expected_outcome") == "TAMPER_DETECTED"
            and case.get("actual_outcome") == "TAMPER_DETECTED"
            for case in case_dicts
        ),
        "unexpected_valid_cases": sum(
            "ARL_EXPECTED_DETECTION_MISSING"
            in _list_value(case.get("reason_codes"))
            for case in case_dicts
        ),
        "input_invalid_cases": sum(
            case.get("actual_outcome") == "INPUT_INVALID" for case in case_dicts
        ),
        "total_rows_read": sum(
            value
            for case in case_dicts
            if isinstance((value := case.get("parsed_row_count")), int)
            and not isinstance(value, bool)
        ),
        "total_integrity_errors": sum(
            value
            for case in case_dicts
            if isinstance((value := case.get("integrity_error_count")), int)
            and not isinstance(value, bool)
        ),
    }


def validate_case_contract(cases: Sequence[Any]) -> dict[str, bool]:
    case_dicts = [_dict_value(case) for case in cases]
    exact_count_and_order = (
        len(case_dicts) == len(CANONICAL_CASE_CONTRACTS)
        and tuple(case.get("case_id") for case in case_dicts) == CANONICAL_CASE_IDS
    )
    exact_fields = all(set(case) == SOURCE_CASE_FIELDS for case in case_dicts)
    semantics_valid = exact_count_and_order and exact_fields
    reasons_valid = exact_count_and_order and exact_fields
    issues_valid = exact_count_and_order and exact_fields
    head_hashes_valid = exact_count_and_order and exact_fields

    if exact_count_and_order and exact_fields:
        for case, contract in zip(
            case_dicts,
            CANONICAL_CASE_CONTRACTS,
            strict=True,
        ):
            semantics_valid = semantics_valid and all(
                (
                    case.get("fixture_name") == contract["fixture_name"],
                    case.get("expected_outcome") == contract["expected_outcome"],
                    case.get("actual_outcome") == contract["actual_outcome"],
                    case.get("expected_primary_reason_code")
                    == contract["expected_primary_reason_code"],
                    tuple(_list_value(case.get("expected_additional_reason_codes")))
                    == contract["expected_additional_reason_codes"],
                    case.get("file_exists") is True,
                    case.get("line_count") == contract["expected_row_count"],
                    case.get("parsed_row_count") == contract["expected_row_count"],
                    case.get("expected_row_count") == contract["expected_row_count"],
                    case.get("first_error_line") == contract["first_error_line"],
                    case.get("integrity_error_count")
                    == contract["integrity_error_count"],
                    case.get("expected_condition_detected") is True,
                    case.get("reason_code_sequence_valid") is True,
                    case.get("passed") is True,
                )
            )
            reason_codes = _list_value(case.get("reason_codes"))
            reasons_valid = reasons_valid and (
                tuple(reason_codes) == contract["reason_codes"]
                and len(reason_codes) == len(set(reason_codes))
                and reason_codes[0] == contract["expected_primary_reason_code"]
            )
            source_issues = _list_value(case.get("issues"))
            issue_fields_valid = all(
                isinstance(issue, dict) and set(issue) == SOURCE_ISSUE_FIELDS
                for issue in source_issues
            )
            integrity_count = sum(
                isinstance(issue, dict)
                and issue.get("reason_code") in INTEGRITY_REASON_CODES
                for issue in source_issues
            )
            expected_issues = CANONICAL_ISSUE_CONTRACTS[case["case_id"]]
            exact_issue_evidence = (
                len(source_issues) == len(expected_issues)
                and all(
                    isinstance(issue, dict)
                    and {
                        "issue_ordinal": ordinal,
                        "line_number": issue.get("line_number"),
                        "reason_code": issue.get("reason_code"),
                        "detail": issue.get("detail"),
                        "stored_value": issue.get("stored_value"),
                        "recomputed_value": issue.get("recomputed_value"),
                    }
                    == dict(expected_issue)
                    for ordinal, (issue, expected_issue) in enumerate(
                        zip(source_issues, expected_issues, strict=True),
                        start=1,
                    )
                )
            )
            issues_valid = issues_valid and (
                len(source_issues) == contract["source_issue_count"]
                and issue_fields_valid
                and integrity_count == contract["integrity_error_count"]
                and exact_issue_evidence
            )
            head_hash_contract = CANONICAL_HEAD_HASH_CONTRACTS[case["case_id"]]
            head_hashes_valid = head_hashes_valid and (
                case.get("stored_head_hash")
                == head_hash_contract["stored_head_hash"]
                and case.get("recomputed_head_hash")
                == head_hash_contract["recomputed_head_hash"]
            )

    return {
        "canonical_case_order_valid": exact_count_and_order,
        "canonical_case_fields_valid": exact_fields,
        "canonical_case_semantics_valid": semantics_valid,
        "reason_code_order_valid": reasons_valid,
        "source_issue_contract_valid": issues_valid,
        "head_hash_evidence_valid": head_hashes_valid,
    }


def build_source_checks(source: SourceDocuments) -> dict[str, bool]:
    result = source.result
    verify = source.verify
    cases = _list_value(result.get("cases"))
    case_checks = validate_case_contract(cases)
    computed_counts = compute_counts_from_cases(cases)
    source_counts = result.get("counts")
    verify_counts = verify.get("counts")
    result_manifest = result.get("manifest_sha256")
    verify_manifest = verify.get("manifest_sha256")

    checks = {
        "source_result_fields_exact": set(result) == SOURCE_RESULT_FIELDS,
        "source_verify_fields_exact": set(verify) == SOURCE_VERIFY_FIELDS,
        "source_result_verified": result.get("verified") is True,
        "source_verify_verified": verify.get("verified") is True,
        "source_hmac_disabled": verify.get("hmac_enabled") is False,
        "source_authenticity_not_claimed": verify.get("authenticity_claimed")
        is False,
        "source_result_safety_boundary_valid": result.get("safety_boundary")
        == dict(SOURCE_SAFETY_BOUNDARY),
        "source_verify_safety_boundary_valid": verify.get("safety_boundary")
        == dict(SOURCE_SAFETY_BOUNDARY),
        "source_result_hash_matches": verify.get("result_sha256")
        == source.sha256[SOURCE_RESULT_FILENAME],
        "source_report_hash_matches": verify.get("report_sha256")
        == source.sha256[SOURCE_REPORT_FILENAME],
        "source_manifest_hash_bound": (
            _is_lower_sha256(result_manifest)
            and result_manifest == verify_manifest
            and result_manifest == CANONICAL_MANIFEST_SHA256
        ),
        "source_result_checks_valid": _is_boolean_map(
            result.get("checks"),
            SOURCE_RESULT_CHECK_KEYS,
        ),
        "source_verify_checks_valid": _is_boolean_map(
            verify.get("checks"),
            SOURCE_VERIFY_CHECK_KEYS,
        ),
        "source_counts_match_cases": source_counts == computed_counts,
        "source_counts_match_verify": source_counts == verify_counts,
        "canonical_counts_valid": source_counts == dict(CANONICAL_COUNTS),
        "source_result_metadata_valid": (
            result.get("generated_at_utc") == DETERMINISTIC_GENERATED_AT_UTC
            and result.get("mode") == "fixture_based_advisory_only"
            and result.get("hash_contract") == SOURCE_HASH_CONTRACT
            and result.get("fixture_directory") == "arl_hash_chain"
            and result.get("manifest_path") == "arl_hash_chain/fixture_manifest.json"
            and result.get("manifest_schema_version")
            == SOURCE_MANIFEST_SCHEMA_VERSION
            and result.get("overall_outcome") == "CHAIN_VALID"
            and result.get("overall_reason_codes") == ["ARL_CHAIN_VALID"]
            and result.get("failure_detail") is None
        ),
        "source_verify_metadata_valid": verify.get("generated_at_utc")
        == DETERMINISTIC_GENERATED_AT_UTC,
        "analyzer_safety_boundary_valid": dict(SAFETY_BOUNDARY)
        == {
            "advisory_only": True,
            "human_review_required": True,
            "ai_api_call": False,
            "api_key_required": False,
            "github_actions_secrets_required": False,
            "external_ai_provider": False,
            "billable_action": False,
            "network_call": False,
            "automatic_repair": False,
            "automatic_retry": False,
            "automatic_apply": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pr": False,
            "automatic_merge": False,
            "automatic_deploy": False,
            "runtime_arl_modified": False,
            "existing_patch_4_analyzer_modified": False,
            "authenticity_claimed": False,
        },
    }
    checks.update(case_checks)
    normalized = [normalize_case(case) for case in cases]
    checks["all_source_issues_preserved"] = sum(
        len(case["issues"]) for case in normalized
    ) == sum(
        len(_list_value(_dict_value(case).get("issues"))) for case in cases
    )
    checks["nineteen_integrity_issues_preserved"] = sum(
        issue["is_integrity_issue"]
        for case in normalized
        for issue in case["issues"]
    ) == CANONICAL_COUNTS["total_integrity_errors"]
    return dict(sorted(checks.items()))


def add_node(
    nodes: dict[str, dict[str, Any]],
    node_id: str,
    node_type: str,
    label: str,
    **properties: Any,
) -> None:
    nodes[node_id] = {
        "id": node_id,
        "type": node_type,
        "label": label,
        "properties": dict(sorted(properties.items())),
    }


def add_edge(
    edges: dict[str, dict[str, Any]],
    source: str,
    target: str,
    edge_type: str,
    **properties: Any,
) -> None:
    ordered_properties = dict(sorted(properties.items()))
    edge_id = stable_id(
        "edge",
        source,
        edge_type,
        target,
        canonical_hash(ordered_properties),
    )
    edges[edge_id] = {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "properties": ordered_properties,
    }


def build_graph(
    cases: Sequence[dict[str, Any]],
    source: SourceDocuments,
    checks: dict[str, bool],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    add_node(
        nodes,
        ROOT_NODE_ID,
        "HashChainArtifactSet",
        "Patch 13 ARL hash-chain stress results",
        logical_id=LOGICAL_SOURCE_ID,
        source_path=LOGICAL_SOURCE_ROOT,
        verified=all(checks.values()),
    )

    for filename in sorted(EXPECTED_SOURCE_FILES):
        source_node = stable_id("source_document", filename)
        add_node(
            nodes,
            source_node,
            "SourceDocument",
            filename,
            logical_path=f"{LOGICAL_SOURCE_ROOT}/{filename}",
            sha256=source.sha256[filename],
        )
        add_edge(edges, ROOT_NODE_ID, source_node, "HAS_SOURCE")

    verify_node = stable_id("verify_report", SOURCE_VERIFY_FILENAME)
    add_node(
        nodes,
        verify_node,
        "VerifyReport",
        SOURCE_VERIFY_FILENAME,
        verified=source.verify.get("verified") is True,
        hmac_enabled=source.verify.get("hmac_enabled"),
        authenticity_claimed=source.verify.get("authenticity_claimed"),
    )
    add_edge(edges, verify_node, ROOT_NODE_ID, "VERIFIES")

    for case in cases:
        case_id = case["case_id"]
        case_node = stable_id("hash_chain_case", case_id)
        add_node(
            nodes,
            case_node,
            "HashChainCase",
            case_id,
            classification=case["classification"],
            fixture_name=case["fixture_name"],
            passed=case["passed"],
            expected_canonical_head_hash=case["expected_canonical_head_hash"],
            stored_head_hash=case["stored_head_hash"],
            recomputed_head_hash=case["recomputed_head_hash"],
            integrity_error_count=case["integrity_error_count"],
        )
        add_edge(edges, ROOT_NODE_ID, case_node, "HAS_CASE")

        expected_value = str(case["expected_outcome"])
        expected_node = stable_id("expected_outcome", expected_value)
        add_node(
            nodes,
            expected_node,
            "ExpectedOutcome",
            expected_value,
        )
        add_edge(edges, case_node, expected_node, "EXPECTED_OUTCOME")

        observed_value = str(case["actual_outcome"])
        observed_node = stable_id("observed_outcome", observed_value)
        add_node(
            nodes,
            observed_node,
            "ObservedOutcome",
            observed_value,
        )
        add_edge(edges, case_node, observed_node, "OBSERVED_OUTCOME")

        for reason in case["reasons"]:
            reason_code = reason["reason_code"]
            reason_node = stable_id("reason_code", reason_code)
            add_node(nodes, reason_node, "ReasonCode", reason_code)
            add_edge(
                edges,
                case_node,
                reason_node,
                "HAS_REASON",
                order=reason["order"],
                role=reason["role"],
            )

        for issue in case["issues"]:
            if not issue["is_integrity_issue"]:
                continue
            issue_node = stable_id(
                "integrity_issue",
                case_id,
                issue["issue_ordinal"],
                issue["line_number"],
                issue["reason_code"],
            )
            add_node(
                nodes,
                issue_node,
                "IntegrityIssue",
                f"{case_id} issue {issue['issue_ordinal']}",
                issue_ordinal=issue["issue_ordinal"],
                line_number=issue["line_number"],
                reason_code=issue["reason_code"],
                detail=issue["detail"],
                stored_value=issue["stored_value"],
                recomputed_value=issue["recomputed_value"],
            )
            add_edge(
                edges,
                case_node,
                issue_node,
                "HAS_ISSUE",
                issue_ordinal=issue["issue_ordinal"],
            )

    node_values = sorted(nodes.values(), key=lambda node: node["id"])
    edge_values = sorted(edges.values(), key=lambda edge: edge["id"])
    graph = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "advisory_only_deterministic_hash_chain_graph",
        "logical_root": LOGICAL_SOURCE_ID,
        "nodes": node_values,
        "edges": edge_values,
        "counts": {
            "nodes": len(node_values),
            "edges": len(edge_values),
            "cases": sum(node["type"] == "HashChainCase" for node in node_values),
            "integrity_issues": sum(
                node["type"] == "IntegrityIssue" for node in node_values
            ),
        },
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }
    graph["graph_hash"] = canonical_hash(
        {
            "schema_version": graph["schema_version"],
            "logical_root": graph["logical_root"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        }
    )
    return graph


def build_analysis(source: SourceDocuments) -> dict[str, Any]:
    checks = build_source_checks(source)
    normalized_cases = [
        normalize_case(case) for case in _list_value(source.result.get("cases"))
    ]
    graph = build_graph(normalized_cases, source, checks)
    checks["graph_case_count_valid"] = graph["counts"]["cases"] == 7
    checks["graph_integrity_issue_count_valid"] = (
        graph["counts"]["integrity_issues"] == 19
    )
    checks = dict(sorted(checks.items()))

    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "advisory_only_deterministic_hash_chain_analyzer",
        "source_contract": {
            "logical_root": LOGICAL_SOURCE_ID,
            "logical_path": LOGICAL_SOURCE_ROOT,
            "required_files": sorted(EXPECTED_SOURCE_FILES),
            "result_schema_version": SOURCE_RESULT_SCHEMA_VERSION,
            "verify_schema_version": SOURCE_VERIFY_SCHEMA_VERSION,
            "manifest_schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        },
        "source_documents": {
            filename: {
                "logical_path": f"{LOGICAL_SOURCE_ROOT}/{filename}",
                "sha256": source.sha256[filename],
            }
            for filename in sorted(EXPECTED_SOURCE_FILES)
        },
        "source_manifest_sha256": source.result.get("manifest_sha256"),
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "cases": normalized_cases,
        "counts": source.result.get("counts", {}),
        "checks": checks,
        "graph_summary": {
            "schema_version": graph["schema_version"],
            "node_count": graph["counts"]["nodes"],
            "edge_count": graph["counts"]["edges"],
            "case_count": graph["counts"]["cases"],
            "integrity_issue_count": graph["counts"]["integrity_issues"],
            "graph_hash": graph["graph_hash"],
        },
        "verified": all(checks.values()),
    }
    return {"result": result, "graph": graph}


def build_report(result: dict[str, Any], graph: dict[str, Any]) -> str:
    source_docs = result["source_documents"]
    lines = [
        "# Tasukeru ARL Hash-Chain Analyzer Report",
        "",
        "## Summary",
        "",
        f"- Verified: `{'true' if result['verified'] else 'false'}`",
        f"- Cases: `{result['counts'].get('total_cases')}`",
        f"- Expected tamper detections: `{result['counts'].get('tamper_cases_detected')}`",
        f"- Integrity issues: `{result['counts'].get('total_integrity_errors')}`",
        "",
        "## Source Binding Verification",
        "",
    ]
    for filename in sorted(source_docs):
        lines.append(f"- `{filename}` SHA-256: `{source_docs[filename]['sha256']}`")
    lines.extend(["", "## Case Classifications", ""])
    for case in result["cases"]:
        lines.append(
            f"- `{case['case_id']}`: `{case['classification']}`; "
            f"expected=`{case['expected_outcome']}`; "
            f"observed=`{case['actual_outcome']}`; "
            f"passed=`{'true' if case['passed'] else 'false'}`"
        )
    lines.extend(["", "## Reason-Code Ordering", ""])
    for case in result["cases"]:
        rendered = ", ".join(
            f"{reason['order']}:{reason['reason_code']}({reason['role']})"
            for reason in case["reasons"]
        )
        lines.append(f"- `{case['case_id']}`: {rendered}")
    lines.extend(["", "## Integrity Issue Counts", ""])
    for case in result["cases"]:
        lines.append(
            f"- `{case['case_id']}`: `{case['integrity_error_count']}`"
        )
    lines.extend(["", "## Head-Hash Evidence", ""])
    for case in result["cases"]:
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Expected canonical head hash: `{case['expected_canonical_head_hash']}`",
                f"- Stored head hash: `{case['stored_head_hash']}`",
                f"- Recomputed head hash: `{case['recomputed_head_hash']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Graph Summary",
            "",
            f"- Nodes: `{graph['counts']['nodes']}`",
            f"- Edges: `{graph['counts']['edges']}`",
            f"- Integrity issue nodes: `{graph['counts']['integrity_issues']}`",
            f"- Graph hash: `{graph['graph_hash']}`",
            "",
            "## Checks",
            "",
        ]
    )
    for name, passed in sorted(result["checks"].items()):
        lines.append(f"- {name}: `{'true' if passed else 'false'}`")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in sorted(result["safety_boundary"].items()):
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"- {name}: `{rendered}`")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- HMAC is not enabled.",
            "- Authenticity is not claimed.",
            "- Hash consistency is not an external identity proof.",
            "- This artifact is advisory-only.",
            "- Final review remains human-controlled.",
            "",
        ]
    )
    return "\n".join(lines)


def build_output_verify(
    result: dict[str, Any],
    graph: dict[str, Any],
    *,
    source: SourceDocuments,
    result_path: Path,
    graph_path: Path,
    report_path: Path,
    verify_path: Path,
) -> dict[str, Any]:
    output_existence_checks = {
        "result_json": result_path.is_file(),
        "graph_json": graph_path.is_file(),
        "report_markdown": report_path.is_file(),
        "verify_json": verify_path.is_file(),
    }
    try:
        actual_names = {
            path.name for path in verify_path.parent.iterdir() if path.is_file()
        }
    except OSError:
        actual_names = set()
    output_filename_set_exact = actual_names == EXPECTED_OUTPUT_FILES
    checks = dict(result["checks"])
    checks.update(
        {
            "graph_hash_matches": result["graph_summary"]["graph_hash"]
            == graph["graph_hash"],
            "output_files_exist": all(output_existence_checks.values()),
            "output_filename_set_exact": output_filename_set_exact,
        }
    )
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "verified": result["verified"] and all(checks.values()),
        "checks": dict(sorted(checks.items())),
        "source_document_sha256": dict(sorted(source.sha256.items())),
        "source_schema_versions": {
            "result": source.result.get("schema_version"),
            "verify": source.verify.get("schema_version"),
        },
        "source_manifest_sha256": source.result.get("manifest_sha256"),
        "output_existence_checks": output_existence_checks,
        "output_filename_set_exact": output_filename_set_exact,
        "result_sha256": file_sha256(result_path) if result_path.is_file() else "",
        "graph_sha256": file_sha256(graph_path) if graph_path.is_file() else "",
        "report_sha256": file_sha256(report_path) if report_path.is_file() else "",
        "graph_hash": graph["graph_hash"],
        "counts": result["counts"],
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "hmac_enabled": False,
        "authenticity_claimed": False,
    }


def write_artifacts(
    analysis: dict[str, Any],
    source: SourceDocuments,
    output_dir: Path,
) -> dict[str, Any]:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / RESULT_FILENAME
        graph_path = output_dir / GRAPH_FILENAME
        report_path = output_dir / REPORT_FILENAME
        verify_path = output_dir / VERIFY_FILENAME
        result = analysis["result"]
        graph = analysis["graph"]
        write_text_lf(result_path, json_dump(result))
        write_text_lf(graph_path, json_dump(graph))
        write_text_lf(report_path, build_report(result, graph))

        preliminary = build_output_verify(
            result,
            graph,
            source=source,
            result_path=result_path,
            graph_path=graph_path,
            report_path=report_path,
            verify_path=verify_path,
        )
        write_text_lf(verify_path, json_dump(preliminary))
        verify = build_output_verify(
            result,
            graph,
            source=source,
            result_path=result_path,
            graph_path=graph_path,
            report_path=report_path,
            verify_path=verify_path,
        )
        write_text_lf(verify_path, json_dump(verify))
    except AnalyzerOperationalError:
        raise
    except OSError as exc:
        raise AnalyzerOperationalError(
            "ARL_ANALYZER_OUTPUT_WRITE_FAILED",
            "Analyzer output files could not be written.",
        ) from exc
    return {
        "result_path": result_path,
        "graph_path": graph_path,
        "report_path": report_path,
        "verify_path": verify_path,
        "verify": verify,
    }


def run_analyzer(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    source = load_source_documents(input_dir)
    validate_output_directory(input_dir, output_dir)
    analysis = build_analysis(source)
    artifacts = write_artifacts(analysis, source, output_dir)
    return {
        "source": source,
        "analysis": analysis,
        "artifacts": artifacts,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze deterministic Patch 13 ARL hash-chain artifacts."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing exactly the three Patch 13 source artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Absent or empty directory for four analyzer review artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run = run_analyzer(args.input_dir, args.output_dir)
    except AnalyzerOperationalError as exc:
        print(f"{exc.reason_code}: {exc.message}", file=sys.stderr)
        return 2
    except Exception:
        print(
            "ARL_ANALYZER_UNEXPECTED_ERROR: An unexpected operational error occurred.",
            file=sys.stderr,
        )
        return 2

    artifacts = run["artifacts"]
    verify = artifacts["verify"]
    print("Tasukeru ARL Hash-Chain Analyzer v0.1")
    print(f"verified: {verify['verified']}")
    print(f"result: {RESULT_FILENAME}")
    print(f"graph: {GRAPH_FILENAME}")
    print(f"report: {REPORT_FILENAME}")
    print(f"verify: {VERIFY_FILENAME}")
    return 0 if verify["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
