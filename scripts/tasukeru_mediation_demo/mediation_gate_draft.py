"""DRAFT_FEATURE_PROPOSAL: offline, narrowly structured mediation verification.

This is a simulation component, not deployed Tasukeru code. It makes no AI/API
calls and does not apply proposals. JSON/schema and evidence binding checks do
not establish causality, source authenticity, or whole-system safety.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal

VERSION = "tasukeru-mediation-simulation-v0"
MAX_OUTPUT_BYTES = 65536
BINDING_KEYS = ("repository", "workflow_path", "run_id", "run_attempt", "head_sha",
                "artifact_id", "artifact_name", "bundle_sha256")
ALLOWED_HYPOTHESES = {"SNAPSHOT_TIMING_DIFFERENCE_POSSIBLE", "REPORTING_BUG_POSSIBLE"}
ALLOWED_CHECKS = {"REQUEST_SNAPSHOT_PROVENANCE", "COMPARE_RECORDED_AND_FINAL_BYTES"}
TOP_KEYS = {"schema_version", "source", "facts", "hypotheses", "requested_checks",
            "cause", "actor", "same_snapshot_relationship", "approval",
            "human_review_required", "automatic_apply", "automatic_retry"}


class InvalidInput(ValueError):
    pass


def strict_json(raw: bytes):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_OUTPUT_BYTES:
        raise InvalidInput("OUTPUT_SIZE_INVALID")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise InvalidInput("JSON_BOM_REJECTED")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidInput("JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    def constant(_):
        raise InvalidInput("JSON_NONFINITE")

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs, parse_constant=constant,
                           parse_float=Decimal)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidInput("JSON_SYNTAX_INVALID") from exc
    except RecursionError as exc:
        raise InvalidInput("JSON_DEPTH_EXCEEDED") from exc

    def unicode_check(item, depth=0):
        if depth > 32:
            raise InvalidInput("JSON_DEPTH_EXCEEDED")
        if isinstance(item, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in item):
            raise InvalidInput("JSON_SURROGATE_REJECTED")
        if isinstance(item, dict):
            for key, val in item.items():
                unicode_check(key, depth + 1)
                unicode_check(val, depth + 1)
        elif isinstance(item, list):
            for val in item:
                unicode_check(val, depth + 1)
    unicode_check(value)
    return value


def exact_value(a, b):
    """No coercion: JSON booleans must not equal integer counts."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(exact_value(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact_value(x, y) for x, y in zip(a, b))
    return a == b


def packet_from_observation(report: dict, observation_raw: bytes):
    manifest = report.get("github_source", {})
    if (manifest.get("retrieval_status") != "READY_FOR_OBSERVATION"
            or report.get("arl_run_id_value_check") != "MATCHED_LITERAL_RUN_ID"
            or report.get("unknowns")
            or report.get("observation_status") not in {"DIFFERENCES_OBSERVED", "VALUES_MATCH_IN_CHECKED_SCOPE"}):
        raise InvalidInput("SOURCE_NOT_READY")
    source = {k: manifest[k] for k in BINDING_KEYS}
    source["observation_sha256"] = hashlib.sha256(observation_raw).hexdigest()
    facts = []
    for item in report["arl_row_count_checks"]:
        if item["values_match"] is False:
            facts.append({"fact_id": "ROW:" + item["source"] + ":" + item["field"],
                          "evidence_class": "RUNTIME_OBSERVATION",
                          "kind": "ARL_ROW_COUNT", **item})
    for item in report["artifact_hash_checks"]:
        if item["values_match"] is False:
            facts.append({"fact_id": "BYTES:" + item["artifact"],
                          "evidence_class": "RUNTIME_OBSERVATION",
                          "kind": "ARTIFACT_BYTES", **item})
    if len(facts) != report["observed_difference_count"]:
        raise InvalidInput("DIFFERENCE_INVENTORY_INCOMPLETE")
    return {"source": source, "facts": facts, "evidence_class": "RUNTIME_OBSERVATION"}


def make_fixture_proposal(packet: dict):
    """A handwritten deterministic fixture, never represented as real AI output."""
    return {"schema_version": VERSION, "source": packet["source"],
            "facts": packet["facts"], "hypotheses": [],
            "requested_checks": ["REQUEST_SNAPSHOT_PROVENANCE"],
            "cause": "UNKNOWN", "actor": "UNKNOWN",
            "same_snapshot_relationship": "UNKNOWN", "approval": "NOT_DETERMINED",
            "human_review_required": True, "automatic_apply": False,
            "automatic_retry": False}


def verify_proposal(raw: bytes, packet: dict | None, model_state="OUTPUT_READY"):
    def result(status, reason):
        return {"status": status, "reason": reason, "human_review_required": True,
                "automatic_apply": False, "automatic_retry": False,
                "causality_verified": False, "whole_system_safety_verified": False}
    if packet is None:
        return result("UNKNOWN", "SOURCE_NOT_READY")
    if model_state != "OUTPUT_READY":
        return result("UNKNOWN", "MEDIATOR_OUTPUT_UNAVAILABLE")
    try:
        p = strict_json(raw)
        if not isinstance(p, dict) or set(p) != TOP_KEYS:
            return result("BLOCKED_INVALID", "OUTPUT_SCHEMA_MISMATCH")
        if p["schema_version"] != VERSION:
            return result("BLOCKED_INVALID", "OUTPUT_SCHEMA_MISMATCH")
        if not exact_value(p["source"], packet["source"]):
            return result("BLOCKED_INVALID", "SOURCE_BINDING_MISMATCH")
        facts = p["facts"]
        if not isinstance(facts, list) or len(facts) > 16:
            return result("BLOCKED_INVALID", "FACT_INVENTORY_MISMATCH")
        trusted = {f["fact_id"]: f for f in packet["facts"]}
        seen = set()
        for f in facts:
            if not isinstance(f, dict) or not isinstance(f.get("fact_id"), str):
                return result("BLOCKED_INVALID", "FACT_INVENTORY_MISMATCH")
            key = f["fact_id"]
            if key in seen or key not in trusted:
                return result("BLOCKED_INVALID", "FACT_INVENTORY_MISMATCH")
            seen.add(key)
            if not exact_value(f, trusted[key]):
                return result("BLOCKED_INVALID", "FACT_VALUE_MISMATCH")
        if seen != set(trusted):
            return result("BLOCKED_INVALID", "FACT_INVENTORY_MISMATCH")
        if (p["cause"] != "UNKNOWN" or p["actor"] != "UNKNOWN"
                or p["same_snapshot_relationship"] != "UNKNOWN"
                or p["approval"] != "NOT_DETERMINED"):
            return result("BLOCKED_INVALID", "UNSUPPORTED_CONCLUSION")
        if (p["human_review_required"] is not True or p["automatic_apply"] is not False
                or p["automatic_retry"] is not False):
            return result("BLOCKED_INVALID", "AUTHORITY_EXPANSION")
        for field, allowed in [("hypotheses", ALLOWED_HYPOTHESES),
                               ("requested_checks", ALLOWED_CHECKS)]:
            vals = p[field]
            if (not isinstance(vals, list) or len(vals) > 4
                    or any(not isinstance(v, str) or v not in allowed for v in vals)
                    or len(set(vals)) != len(vals)):
                return result("BLOCKED_INVALID", "UNSUPPORTED_HYPOTHESIS_OR_CHECK")
        return result("REVIEWABLE_DRAFT", "DECLARED_CHECKS_PASSED")
    except InvalidInput as exc:
        return result("BLOCKED_INVALID", str(exc))
