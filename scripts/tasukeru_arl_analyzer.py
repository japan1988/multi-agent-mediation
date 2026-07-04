#!/usr/bin/env python3
"""Deterministic ARL artifact analyzer and graph generator for Patch 4.

This script reads local Tasukeru ARL/advisory artifacts and writes advisory-only
analysis artifacts. It does not call network services, AI APIs, external
providers, GitHub secrets, or automation actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "tasukeru-arl-analyzer-v0.1"
GRAPH_SCHEMA_VERSION = "tasukeru-arl-graph-v0.1"
VERIFY_SCHEMA_VERSION = "tasukeru-arl-analyzer-verify-v0.1"
DETERMINISTIC_GENERATED_AT_UTC = "1970-01-01T00:00:00Z"

RESULT_FILENAME = "tasukeru_arl_analyzer_result.json"
GRAPH_FILENAME = "tasukeru_arl_graph.json"
REPORT_FILENAME = "tasukeru_arl_analyzer_report.md"
VERIFY_FILENAME = "tasukeru_arl_analyzer_verify.json"

RUNTIME_ARL_FILENAME = "tasukeru_arl.jsonl"
RUNTIME_ARL_VERIFY_FILENAME = "tasukeru_arl_verify.json"
HITL_REVIEW_FILENAME = "tasukeru_hitl_review.json"
FINDING_VALIDATION_FILENAME = "tasukeru_finding_validation_report.json"
RESULT_CONSISTENCY_FILENAME = "tasukeru_result_consistency_report.json"
LOGIC_REVIEW_PATH = Path("tasukeru_logs") / "logic-review.json"

STRESS_RESULT_FILENAME = "tasukeru_arl_stress_result.json"
STRESS_VERIFY_FILENAME = "tasukeru_arl_stress_verify.json"
LOGICAL_INPUT_ROOT = "artifact_input_root"
LOGICAL_STRESS_ROOT = "patch_3_arl_stress_results"
LOGICAL_STRESS_DIR = "stress_results/arl"

RUNTIME_REQUIRED_KEYS = (
    "run_id",
    "layer",
    "decision",
    "sealed",
    "overrideable",
    "final_decider",
    "reason_code",
)

EXPECTED_NEGATIVE_STRESS_KINDS = frozenset({"MISSING_REQUIRED_KEY", "INVALID_JSONL"})

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
    "auto_fix": False,
    "patch_5_pseudo_orchestration": False,
}


@dataclass(frozen=True)
class JsonDocument:
    name: str
    path: Path
    exists: bool
    parsed: bool
    sha256: str
    error: str
    payload: Any


@dataclass(frozen=True)
class JsonlParseResult:
    path: Path
    exists: bool
    sha256: str
    line_count: int
    non_empty_line_count: int
    rows: list[dict[str, Any]]
    issues: list[dict[str, Any]]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_token(value: Any) -> str:
    text = str(value if value is not None else "unknown").strip().lower()
    chars = [char if char.isalnum() else "_" for char in text]
    compact = "_".join(part for part in "".join(chars).split("_") if part)
    return compact[:80] or "unknown"


def stable_node_id(kind: str, *parts: Any) -> str:
    raw_parts = [str(part) for part in parts if part not in (None, "")]
    raw = "|".join(raw_parts) if raw_parts else kind
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    label = safe_token(raw_parts[0] if raw_parts else kind)
    return f"{kind}:{label}:{digest}"


def runtime_row_node_id(row: dict[str, Any], index: int) -> str:
    seq = row.get("seq", index)
    hash_value = (
        row.get("chain_hash")
        or row.get("row_hash")
        or stable_hash({"index": index, "row": row})
    )
    return f"runtime_arl_row:{safe_token(seq)}:{str(hash_value)[:12]}"


def read_json_document(path: Path, *, name: str) -> JsonDocument:
    exists = path.exists()
    sha256 = file_sha256(path)
    if not exists:
        return JsonDocument(
            name=name,
            path=path,
            exists=False,
            parsed=False,
            sha256="",
            error="FILE_NOT_FOUND",
            payload=None,
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return JsonDocument(
            name=name,
            path=path,
            exists=True,
            parsed=False,
            sha256=sha256,
            error=f"{type(exc).__name__}: {exc}",
            payload=None,
        )

    return JsonDocument(
        name=name,
        path=path,
        exists=True,
        parsed=True,
        sha256=sha256,
        error="",
        payload=payload,
    )


def document_summary(document: JsonDocument, root: Path) -> dict[str, Any]:
    return {
        "name": document.name,
        "path": relative_path(document.path, root),
        "exists": document.exists,
        "parsed": document.parsed,
        "sha256": document.sha256,
        "error": document.error,
    }


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return f"outside_artifact_root/{path.name}"


def parse_runtime_arl_jsonl(path: Path) -> JsonlParseResult:
    issues: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    line_count = 0
    non_empty_line_count = 0
    exists = path.exists()

    if not exists:
        issues.append(
            {
                "issue_type": "RUNTIME_ARL_NOT_FOUND",
                "line_number": 0,
                "detail": f"Runtime ARL JSONL not found: {path}",
                "missing_keys": [],
            }
        )
        return JsonlParseResult(path, False, "", 0, 0, rows, issues)

    with path.open("r", encoding="utf-8") as file_obj:
        for line_number, raw_line in enumerate(file_obj, start=1):
            line_count += 1
            line = raw_line.strip()
            if not line:
                continue
            non_empty_line_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    {
                        "issue_type": "INVALID_RUNTIME_ARL_JSONL",
                        "line_number": line_number,
                        "detail": f"{exc.__class__.__name__}: {exc.msg}",
                        "missing_keys": [],
                    }
                )
                continue

            if not isinstance(record, dict):
                issues.append(
                    {
                        "issue_type": "RUNTIME_ARL_ROW_NOT_OBJECT",
                        "line_number": line_number,
                        "detail": "Runtime ARL JSONL line must decode to an object.",
                        "missing_keys": [],
                    }
                )
                continue

            missing_keys = [key for key in RUNTIME_REQUIRED_KEYS if key not in record]
            if missing_keys:
                issues.append(
                    {
                        "issue_type": "RUNTIME_ARL_REQUIRED_KEYS_MISSING",
                        "line_number": line_number,
                        "detail": "Runtime ARL row is missing required key(s).",
                        "missing_keys": missing_keys,
                    }
                )
            rows.append(record)

    return JsonlParseResult(
        path=path,
        exists=True,
        sha256=file_sha256(path),
        line_count=line_count,
        non_empty_line_count=non_empty_line_count,
        rows=rows,
        issues=issues,
    )


def count_by(rows: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "UNKNOWN"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def dict_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_runtime_analysis(
    parsed_arl: JsonlParseResult,
    verify_document: JsonDocument,
    input_dir: Path,
) -> dict[str, Any]:
    verify_payload = dict_payload(verify_document.payload)
    verify_row_count = verify_payload.get("row_count")
    parsed_row_count = len(parsed_arl.rows)
    row_count_matches_verify = (
        isinstance(verify_row_count, int) and verify_row_count == parsed_row_count
    )
    hmac_enabled = verify_payload.get("hmac_enabled")
    hmac_enabled_explicit = isinstance(hmac_enabled, bool)

    return {
        "source_type": "runtime_arl",
        "arl_path": relative_path(parsed_arl.path, input_dir),
        "verify_path": relative_path(verify_document.path, input_dir),
        "exists": parsed_arl.exists,
        "sha256": parsed_arl.sha256,
        "line_count": parsed_arl.line_count,
        "non_empty_line_count": parsed_arl.non_empty_line_count,
        "parsed_row_count": parsed_row_count,
        "verify_row_count": verify_row_count,
        "row_count_authority": "tasukeru_arl.jsonl + tasukeru_arl_verify.json",
        "clean_run_arl_rows_authoritative": False,
        "row_count_matches_verify": row_count_matches_verify,
        "verify_report_verified": verify_payload.get("verified") is True,
        "hmac_enabled": hmac_enabled if hmac_enabled_explicit else None,
        "hmac_enabled_explicit": hmac_enabled_explicit,
        "hmac_protection_claimed": hmac_enabled is True,
        "head_hash": verify_payload.get("head_hash", ""),
        "layer_counts": count_by(parsed_arl.rows, "layer"),
        "decision_counts": count_by(parsed_arl.rows, "decision"),
        "reason_code_counts": count_by(parsed_arl.rows, "reason_code"),
        "final_decider_counts": count_by(parsed_arl.rows, "final_decider"),
        "issues": parsed_arl.issues,
    }


def build_stress_analysis(stress_dir: Path) -> dict[str, Any]:
    result_document = read_json_document(stress_dir / STRESS_RESULT_FILENAME, name=STRESS_RESULT_FILENAME)
    verify_document = read_json_document(stress_dir / STRESS_VERIFY_FILENAME, name=STRESS_VERIFY_FILENAME)
    result_payload = dict_payload(result_document.payload)
    verify_payload = dict_payload(verify_document.payload)

    cases = []
    for case in list_payload(result_payload.get("cases")):
        case_dict = dict_payload(case)
        expected_kind = str(case_dict.get("expected_kind", "UNKNOWN"))
        issue_types = [
            str(dict_payload(issue).get("issue_type", "UNKNOWN"))
            for issue in list_payload(case_dict.get("issues"))
        ]
        expected_negative = expected_kind in EXPECTED_NEGATIVE_STRESS_KINDS
        cases.append(
            {
                "case_id": case_dict.get("case_id", ""),
                "fixture_name": case_dict.get("fixture_name", ""),
                "source_type": "stress_fixture_arl",
                "expected_kind": expected_kind,
                "expected_negative": expected_negative,
                "expected_detection": expected_negative and case_dict.get("passed") is True,
                "passed": case_dict.get("passed") is True,
                "input_verified": case_dict.get("input_verified") is True,
                "valid_record_count": case_dict.get("valid_record_count", 0),
                "missing_required_key_count": case_dict.get("missing_required_key_count", 0),
                "invalid_jsonl_count": case_dict.get("invalid_jsonl_count", 0),
                "issue_types": sorted(issue_types),
            }
        )

    expected_negative_cases = [case for case in cases if case["expected_negative"]]
    expected_negative_all_labeled = bool(expected_negative_cases) and all(
        case["expected_detection"] for case in expected_negative_cases
    )

    return {
        "source_type": "stress_artifacts",
        "logical_id": LOGICAL_STRESS_ROOT,
        "stress_dir": LOGICAL_STRESS_DIR,
        "documents": [
            document_summary(result_document, stress_dir),
            document_summary(verify_document, stress_dir),
        ],
        "verified": verify_payload.get("verified") is True,
        "result_verified": result_payload.get("verified") is True,
        "counts": result_payload.get("counts", {}),
        "verify_checks": verify_payload.get("checks", {}),
        "cases": sorted(cases, key=lambda case: str(case.get("case_id", ""))),
        "expected_negative_case_count": len(expected_negative_cases),
        "expected_negative_cases_labeled": expected_negative_all_labeled,
    }


def summarize_advisory_documents(input_dir: Path) -> dict[str, Any]:
    documents = {
        "hitl_review": read_json_document(input_dir / HITL_REVIEW_FILENAME, name=HITL_REVIEW_FILENAME),
        "finding_validation": read_json_document(
            input_dir / FINDING_VALIDATION_FILENAME,
            name=FINDING_VALIDATION_FILENAME,
        ),
        "result_consistency": read_json_document(
            input_dir / RESULT_CONSISTENCY_FILENAME,
            name=RESULT_CONSISTENCY_FILENAME,
        ),
        "logic_review": read_json_document(input_dir / LOGIC_REVIEW_PATH, name=LOGIC_REVIEW_PATH.as_posix()),
    }

    hitl_payload = dict_payload(documents["hitl_review"].payload)
    finding_validation_payload = dict_payload(documents["finding_validation"].payload)
    result_consistency_payload = dict_payload(documents["result_consistency"].payload)
    logic_review_payload = dict_payload(documents["logic_review"].payload)

    return {
        "documents": {
            key: document_summary(document, input_dir) for key, document in sorted(documents.items())
        },
        "hitl_counts": hitl_payload.get("counts", {}),
        "hitl_entry_count": len(list_payload(hitl_payload.get("entries"))),
        "finding_validation": {
            "verified": finding_validation_payload.get("verified"),
            "finding_count": finding_validation_payload.get("finding_count"),
            "policy_violation_count": finding_validation_payload.get("policy_violation_count"),
            "validation_counts": finding_validation_payload.get("validation_counts", {}),
        },
        "result_consistency": {
            "verified": result_consistency_payload.get("verified"),
            "mismatch_count": result_consistency_payload.get("mismatch_count"),
            "decision": result_consistency_payload.get("decision"),
        },
        "logic_review": {
            "findings_count": logic_review_payload.get("findings_count"),
            "category_counts": logic_review_payload.get("category_counts", {}),
            "severity_counts": logic_review_payload.get("severity_counts", {}),
        },
    }


def add_node(nodes: dict[str, dict[str, Any]], node_id: str, node_type: str, label: str, **properties: Any) -> None:
    existing = nodes.get(node_id)
    payload = {
        "id": node_id,
        "type": node_type,
        "label": label,
        "properties": dict(sorted(properties.items())),
    }
    if existing is None:
        nodes[node_id] = payload
    else:
        merged = dict(existing["properties"])
        merged.update(payload["properties"])
        existing["properties"] = dict(sorted(merged.items()))


def add_edge(
    edges: dict[str, dict[str, Any]],
    source: str,
    target: str,
    edge_type: str,
    **properties: Any,
) -> None:
    edge_id = stable_node_id("edge", source, edge_type, target)
    edges[edge_id] = {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "properties": dict(sorted(properties.items())),
    }


def build_graph(
    *,
    runtime_rows: Sequence[dict[str, Any]],
    runtime_analysis: dict[str, Any],
    stress_analysis: dict[str, Any],
    advisory_analysis: dict[str, Any],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    run_id = str(runtime_rows[0].get("run_id", "unknown_run")) if runtime_rows else "unknown_run"
    run_node = stable_node_id("run", run_id)
    add_node(nodes, run_node, "Run", run_id, source_type="runtime_arl")

    previous_row_node = ""
    for index, row in enumerate(runtime_rows, start=1):
        row_node = runtime_row_node_id(row, index)
        add_node(
            nodes,
            row_node,
            "RuntimeArlRow",
            f"runtime row {row.get('seq', index)}",
            seq=row.get("seq", index),
            source_type="runtime_arl",
            sealed=row.get("sealed"),
            overrideable=row.get("overrideable"),
        )
        add_edge(edges, run_node, row_node, "HAS_ROW", order=index)
        if previous_row_node:
            add_edge(edges, previous_row_node, row_node, "PREVIOUS_ROW")
        previous_row_node = row_node

        for node_type, key, edge_type in (
            ("Layer", "layer", "HAS_LAYER"),
            ("Decision", "decision", "HAS_DECISION"),
            ("ReasonCode", "reason_code", "HAS_REASON"),
            ("FinalDecider", "final_decider", "DECIDED_BY"),
        ):
            value = row.get(key, "UNKNOWN")
            node_id = stable_node_id(node_type.lower(), value)
            add_node(nodes, node_id, node_type, str(value))
            add_edge(edges, row_node, node_id, edge_type)

        evidence = dict_payload(row.get("evidence"))
        artifact = evidence.get("artifact")
        artifact_sha = evidence.get("artifact_sha256")
        if artifact:
            artifact_node = stable_node_id("artifact", artifact, artifact_sha or "")
            add_node(
                nodes,
                artifact_node,
                "Artifact",
                str(artifact),
                sha256=artifact_sha or "",
                size_bytes=evidence.get("size_bytes", 0),
            )
            add_edge(edges, row_node, artifact_node, "HAS_EVIDENCE_ARTIFACT")

        file_path = evidence.get("file")
        rule_id = evidence.get("rule_id")
        fingerprint = evidence.get("fingerprint_hash")
        if file_path or rule_id or fingerprint:
            finding_node = stable_node_id("finding", fingerprint or rule_id or file_path, file_path or "")
            add_node(
                nodes,
                finding_node,
                "Finding",
                str(rule_id or row.get("reason_code", "finding")),
                rule_id=rule_id or "",
                fingerprint_hash=fingerprint or "",
                source=evidence.get("source", ""),
                severity=evidence.get("severity", ""),
            )
            add_edge(edges, row_node, finding_node, "HAS_EVIDENCE_FINDING")
            if file_path:
                file_node = stable_node_id("file", file_path)
                add_node(nodes, file_node, "File", str(file_path))
                add_edge(edges, finding_node, file_node, "LOCATED_IN", line=evidence.get("line"))

    runtime_verify_node = stable_node_id("verify_report", RUNTIME_ARL_VERIFY_FILENAME)
    add_node(
        nodes,
        runtime_verify_node,
        "VerifyReport",
        RUNTIME_ARL_VERIFY_FILENAME,
        verified=runtime_analysis.get("verify_report_verified"),
        hmac_enabled=runtime_analysis.get("hmac_enabled"),
    )
    add_edge(edges, runtime_verify_node, run_node, "VERIFIES")

    stress_root = f"stress_artifacts:{LOGICAL_STRESS_ROOT}"
    add_node(
        nodes,
        stress_root,
        "StressArtifactSet",
        "ARL stress artifacts",
        logical_id=LOGICAL_STRESS_ROOT,
        source_path=LOGICAL_STRESS_DIR,
        verified=stress_analysis.get("verified"),
    )
    add_edge(edges, run_node, stress_root, "HAS_STRESS_CONTEXT")

    for case in stress_analysis.get("cases", []):
        case_id = str(case.get("case_id", "unknown_case"))
        case_node = stable_node_id("stress_case", case_id)
        add_node(
            nodes,
            case_node,
            "StressCase",
            case_id,
            expected_kind=case.get("expected_kind"),
            expected_negative=case.get("expected_negative"),
            expected_detection=case.get("expected_detection"),
            source_type="stress_fixture_arl",
        )
        add_edge(edges, stress_root, case_node, "HAS_STRESS_CASE")
        expected_kind_node = stable_node_id("expected_kind", case.get("expected_kind", "UNKNOWN"))
        add_node(nodes, expected_kind_node, "ExpectedKind", str(case.get("expected_kind", "UNKNOWN")))
        add_edge(edges, case_node, expected_kind_node, "EXPECTS")
        for issue_type in case.get("issue_types", []):
            issue_node = stable_node_id("IssueType", issue_type)
            add_node(nodes, issue_node, "IssueType", str(issue_type))
            add_edge(edges, case_node, issue_node, "DETECTED_AS")

    for document_key, document in advisory_analysis.get("documents", {}).items():
        doc_node = stable_node_id("advisory_document", document_key)
        add_node(
            nodes,
            doc_node,
            "AdvisoryDocument",
            document_key,
            exists=document.get("exists"),
            parsed=document.get("parsed"),
            path=document.get("path", ""),
        )
        add_edge(edges, run_node, doc_node, "HAS_ADVISORY_CONTEXT")

    graph = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "advisory_only_deterministic_graph",
        "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "edges": sorted(edges.values(), key=lambda edge: edge["id"]),
    }
    graph["counts"] = {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
    }
    graph["graph_hash"] = stable_hash(
        {
            "schema_version": graph["schema_version"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        }
    )
    return graph


def build_checks(
    runtime_analysis: dict[str, Any],
    stress_analysis: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, bool]:
    hmac_enabled = runtime_analysis.get("hmac_enabled")
    return {
        "runtime_arl_exists": runtime_analysis.get("exists") is True,
        "runtime_arl_parse_errors_zero": not runtime_analysis.get("issues"),
        "runtime_row_count_uses_arl_verify": runtime_analysis.get("row_count_authority")
        == "tasukeru_arl.jsonl + tasukeru_arl_verify.json",
        "runtime_row_count_matches_verify": runtime_analysis.get("row_count_matches_verify") is True,
        "runtime_verify_report_verified": runtime_analysis.get("verify_report_verified") is True,
        "hmac_false_does_not_claim_protection": not (
            hmac_enabled is False and runtime_analysis.get("hmac_protection_claimed") is True
        ),
        "stress_verify_true": stress_analysis.get("verified") is True,
        "expected_negative_stress_cases_labeled": stress_analysis.get("expected_negative_cases_labeled")
        is True,
        "graph_has_nodes_and_edges": graph.get("counts", {}).get("nodes", 0) > 0
        and graph.get("counts", {}).get("edges", 0) > 0,
        "safety_boundary_verified": safety_boundary_verified(SAFETY_BOUNDARY),
    }


def safety_boundary_verified(boundary: dict[str, Any]) -> bool:
    required_false = (
        "ai_api_call",
        "api_key_required",
        "github_actions_secrets_required",
        "external_ai_provider",
        "billable_action",
        "network_call",
        "automatic_apply",
        "automatic_commit",
        "automatic_push",
        "automatic_pr",
        "automatic_merge",
        "automatic_deploy",
        "auto_fix",
        "patch_5_pseudo_orchestration",
    )
    return (
        boundary.get("advisory_only") is True
        and boundary.get("human_review_required") is True
        and all(boundary.get(key) is False for key in required_false)
    )


def run_analysis(input_dir: Path, stress_dir: Path) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    stress_dir = stress_dir.resolve()

    parsed_arl = parse_runtime_arl_jsonl(input_dir / RUNTIME_ARL_FILENAME)
    verify_document = read_json_document(input_dir / RUNTIME_ARL_VERIFY_FILENAME, name=RUNTIME_ARL_VERIFY_FILENAME)
    runtime_analysis = build_runtime_analysis(parsed_arl, verify_document, input_dir)
    stress_analysis = build_stress_analysis(stress_dir)
    advisory_analysis = summarize_advisory_documents(input_dir)
    graph = build_graph(
        runtime_rows=parsed_arl.rows,
        runtime_analysis=runtime_analysis,
        stress_analysis=stress_analysis,
        advisory_analysis=advisory_analysis,
    )
    checks = build_checks(runtime_analysis, stress_analysis, graph)

    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "mode": "advisory_only_deterministic_analyzer",
        "input_dir": LOGICAL_INPUT_ROOT,
        "stress_dir": LOGICAL_STRESS_DIR,
        "input_root_logical_id": LOGICAL_INPUT_ROOT,
        "stress_root_logical_id": LOGICAL_STRESS_ROOT,
        "safety_boundary": dict(SAFETY_BOUNDARY),
        "input_documents": {
            RUNTIME_ARL_FILENAME: {
                "path": relative_path(parsed_arl.path, input_dir),
                "exists": parsed_arl.exists,
                "sha256": parsed_arl.sha256,
                "parsed": not any(
                    issue["issue_type"] == "INVALID_RUNTIME_ARL_JSONL"
                    for issue in parsed_arl.issues
                ),
            },
            RUNTIME_ARL_VERIFY_FILENAME: document_summary(verify_document, input_dir),
        },
        "runtime_arl": runtime_analysis,
        "stress_artifacts": stress_analysis,
        "advisory_artifacts": advisory_analysis,
        "graph_summary": {
            "schema_version": graph["schema_version"],
            "node_count": graph["counts"]["nodes"],
            "edge_count": graph["counts"]["edges"],
            "graph_hash": graph["graph_hash"],
        },
        "checks": checks,
        "verified": all(checks.values()),
    }

    return {
        "result": result,
        "graph": graph,
    }


def build_report(result: dict[str, Any], graph: dict[str, Any]) -> str:
    runtime = result["runtime_arl"]
    stress = result["stress_artifacts"]
    advisory = result["advisory_artifacts"]
    hmac_enabled = runtime.get("hmac_enabled")
    lines = [
        "# Tasukeru ARL Analyzer Report",
        "",
        "This report is deterministic, local, advisory-only, and graph-oriented.",
        "",
        "## Summary",
        "",
        f"- Analyzer verified: `{bool_text(result['verified'])}`",
        f"- Runtime ARL rows parsed: `{runtime['parsed_row_count']}`",
        f"- Runtime ARL verify row count: `{runtime['verify_row_count']}`",
        f"- Runtime row count authority: `{runtime['row_count_authority']}`",
        f"- Graph nodes: `{graph['counts']['nodes']}`",
        f"- Graph edges: `{graph['counts']['edges']}`",
        f"- Stress verified: `{bool_text(stress['verified'])}`",
        "",
        "## HMAC",
        "",
        f"- HMAC enabled: `{bool_text(hmac_enabled is True)}`",
        f"- HMAC protection claimed: `{bool_text(runtime['hmac_protection_claimed'])}`",
    ]
    if hmac_enabled is False:
        lines.append("- Note: `hmac_enabled` is false, so this analyzer does not describe the ARL as HMAC-protected.")
    lines.extend(
        [
            "",
            "## Runtime ARL Counts",
            "",
            "### Decisions",
            "",
        ]
    )
    for key, value in runtime.get("decision_counts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "### Layers", ""])
    for key, value in runtime.get("layer_counts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Stress Cases", ""])
    for case in stress.get("cases", []):
        lines.append(
            f"- `{case['case_id']}` kind=`{case['expected_kind']}` "
            f"passed=`{bool_text(case['passed'])}` "
            f"expected_negative=`{bool_text(case['expected_negative'])}` "
            f"expected_detection=`{bool_text(case['expected_detection'])}`"
        )
    lines.extend(["", "## Advisory Context", ""])
    lines.append(f"- HITL counts: `{advisory.get('hitl_counts', {})}`")
    lines.append(
        "- Finding validation policy violations: "
        f"`{advisory.get('finding_validation', {}).get('policy_violation_count')}`"
    )
    lines.append(
        "- Result consistency mismatches: "
        f"`{advisory.get('result_consistency', {}).get('mismatch_count')}`"
    )
    lines.extend(["", "## Checks", ""])
    for key, value in result.get("checks", {}).items():
        lines.append(f"- {key}: `{bool_text(value)}`")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "- Advisory only: `true`",
            "- Human review required: `true`",
            "- AI API call: `false`",
            "- API key required: `false`",
            "- External AI provider: `false`",
            "- Network call: `false`",
            "- Billable action: `false`",
            "- Auto-fix / auto-commit / auto-push / auto-PR / auto-merge / deploy: `false`",
            "- Patch 5 pseudo-orchestration: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def build_verify(
    result: dict[str, Any],
    graph: dict[str, Any],
    *,
    result_path: Path,
    graph_path: Path,
    report_path: Path,
    verify_path: Path,
) -> dict[str, Any]:
    output_existence_checks = {
        "result_json": result_path.exists(),
        "graph_json": graph_path.exists(),
        "report_markdown": report_path.exists(),
        "verify_json": verify_path.exists(),
    }
    checks = dict(result["checks"])
    checks["output_files_exist"] = all(output_existence_checks.values())
    checks["graph_hash_matches"] = result["graph_summary"]["graph_hash"] == graph["graph_hash"]

    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "generated_at_utc": DETERMINISTIC_GENERATED_AT_UTC,
        "verified": all(checks.values()),
        "checks": checks,
        "output_existence_checks": output_existence_checks,
        "runtime_row_count_authority": result["runtime_arl"]["row_count_authority"],
        "hmac_enabled": result["runtime_arl"]["hmac_enabled"],
        "hmac_protection_claimed": result["runtime_arl"]["hmac_protection_claimed"],
        "graph_hash": graph["graph_hash"],
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }


def write_artifacts(analysis: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = analysis["result"]
    graph = analysis["graph"]

    result_path = out_dir / RESULT_FILENAME
    graph_path = out_dir / GRAPH_FILENAME
    report_path = out_dir / REPORT_FILENAME
    verify_path = out_dir / VERIFY_FILENAME

    result_path.write_text(json_dump(result), encoding="utf-8")
    graph_path.write_text(json_dump(graph), encoding="utf-8")
    report_path.write_text(build_report(result, graph), encoding="utf-8")

    preliminary_verify = build_verify(
        result,
        graph,
        result_path=result_path,
        graph_path=graph_path,
        report_path=report_path,
        verify_path=verify_path,
    )
    verify_path.write_text(json_dump(preliminary_verify), encoding="utf-8")
    verify = build_verify(
        result,
        graph,
        result_path=result_path,
        graph_path=graph_path,
        report_path=report_path,
        verify_path=verify_path,
    )
    verify_path.write_text(json_dump(verify), encoding="utf-8")

    return {
        "result_path": result_path,
        "graph_path": graph_path,
        "report_path": report_path,
        "verify_path": verify_path,
        "verify": verify,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic ARL analyzer and graph generator.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("."),
        help="Directory containing runtime ARL and advisory artifacts.",
    )
    parser.add_argument(
        "--stress-dir",
        type=Path,
        default=Path("stress_results/arl"),
        help="Directory containing Patch 3 ARL stress artifacts.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("analysis_results/arl"),
        help="Directory for generated ARL analyzer artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    analysis = run_analysis(args.input_dir, args.stress_dir)
    artifacts = write_artifacts(analysis, args.out_dir)
    verify = artifacts["verify"]

    print("Tasukeru ARL Analyzer v0.1")
    print(f"input_dir: {args.input_dir}")
    print(f"stress_dir: {args.stress_dir}")
    print(f"out_dir: {args.out_dir}")
    print(f"verified: {verify['verified']}")
    print(f"result: {artifacts['result_path']}")
    print(f"graph: {artifacts['graph_path']}")
    print(f"report: {artifacts['report_path']}")
    print(f"verify: {artifacts['verify_path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
