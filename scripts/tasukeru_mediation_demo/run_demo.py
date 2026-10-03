#!/usr/bin/env python3
"""UNADOPTED EXPERIMENT: read an observer ZIP and exercise fixture mediation.

AI output and approval are ALWAYS simulated. No AI API, automatic repair,
repository change, workflow dispatch, or final adoption is implemented.
Only separate report files are written to a fresh, caller-selected directory.
"""
from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import threading
import zipfile

VERSION = "tasukeru-mediation-actions-demo-v0.1"
REPOSITORY = "japan1988/multi-agent-mediation"
OBSERVER_PATH = ".github/workflows/tasukeru-artifact-observer.yml"
OBSERVER_BLOB = "4913f7409f7994808fb86970ad763cd92be98f82"
BASELINES = {
    ".github/workflows/tasukeru-analysis.yml": "13ff21a87b74e1f5461a25f5810d6fe90452f6d109296decfd16a9131e3f3f13",
    OBSERVER_PATH: "fd9a8e01c21187db3c2b8eae216d8270f31fef075c273abaa1d3ac9b10bfbb5f",
}
MODULE_HASHES = {
    "mediation_gate_draft": "779948bb83f7f2c2ec9c0732c7473e39a5ff1591ef697d36a1556a52d6848657",
    "resubmission_controller_draft": "390fbfc7830c2145ab55328edb14486ebeec52b9c6e35908c542921ebec888b1",
}
MAX_ZIP = 2 * 1024 * 1024
MAX_JSON = 512 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_ID = 2**53 - 1
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SCENARIOS = {
    "consistent": ("HUMAN_REVIEW", 0),
    "corrected": ("HUMAN_REVIEW", 1),
    "no_approval": ("WAITING_FOR_APPROVAL", 0),
    "still_inconsistent": ("STOPPED_BUDGET", 1),
    "expired_approval": ("STOPPED_APPROVAL", 0),
    "result_unknown": ("STOPPED_RESULT_UNKNOWN", 1),
    "human_stop": ("STOPPED_BY_HUMAN", 1),
    "unsupported_cause": ("STOPPED_BUDGET", 1),
    "replay_approval": ("HUMAN_REVIEW", 1),
    "double_request": ("HUMAN_REVIEW", 1),
}


class Unresolved(ValueError):
    pass


class OutputUnresolved(OSError):
    pass


def require(condition, reason):
    if not condition:
        raise Unresolved(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(path, raw):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f:
            f.write(raw)
    except OSError as exc:
        raise OutputUnresolved("REPORT_WRITE_UNRESOLVED") from exc


def integer(value, low=0, high=MAX_ID):
    return type(value) is int and low <= value <= high


def hex_value(value, regex):
    return isinstance(value, str) and regex.fullmatch(value) is not None


def strict_document(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_JSON, "JSON_SIZE_UNRESOLVED")
    require(not raw.startswith(b"\xef\xbb\xbf"), "JSON_BOM_REJECTED")
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, "JSON_DUPLICATE_KEY")
            out[k] = v
        return out
    def constant(_):
        raise Unresolved("JSON_NONFINITE")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                           parse_float=Decimal, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Unresolved("JSON_SYNTAX_UNRESOLVED") from exc
    def inspect(item, depth=0):
        require(depth <= 32, "JSON_DEPTH_UNRESOLVED")
        if isinstance(item, str):
            require(not any(0xD800 <= ord(c) <= 0xDFFF for c in item), "JSON_SURROGATE_REJECTED")
        elif isinstance(item, dict):
            for k, v in item.items():
                inspect(k, depth + 1)
                inspect(v, depth + 1)
        elif isinstance(item, list):
            for v in item:
                inspect(v, depth + 1)
    inspect(value)
    return value


def read_bounded(path, limit):
    require(path.is_file() and not path.is_symlink(), "INPUT_FILE_UNRESOLVED")
    with path.open("rb") as f:
        raw = f.read(limit + 1)
    require(0 < len(raw) <= limit, "INPUT_SIZE_UNRESOLVED")
    return raw


def modules():
    parent = Path(__file__).resolve().parent
    loaded = []
    for name, expected in MODULE_HASHES.items():
        path = parent / (name + ".py")
        raw = read_bounded(path, MAX_JSON)
        require(sha(raw) == expected, "DEMO_CODE_BINDING_MISMATCH")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        exec(compile(raw, str(path), "exec"), module.__dict__)
        loaded.append(module)
    return loaded


def baseline_check(repo_root):
    for name, expected in BASELINES.items():
        raw = read_bounded(repo_root / name, MAX_JSON)
        require(sha(raw) == expected, "EXISTING_WORKFLOW_BASELINE_CHANGED")


def validate_download(m, raw):
    expected_keys = {"read_status", "repository", "workflow_path", "observer_run_id", "run_attempt",
                     "head_sha", "conclusion", "artifact_id", "artifact_name", "sha256", "bytes",
                     "workflow_blob_sha", "authenticity_or_approval"}
    require(isinstance(m, dict), "DOWNLOAD_MANIFEST_UNRESOLVED")
    require(m.get("read_status") == "READY_FOR_DEMO", "OBSERVER_RETRIEVAL_NOT_READY")
    require(set(m) == expected_keys, "DOWNLOAD_MANIFEST_SCHEMA_MISMATCH")
    require(m["repository"] == REPOSITORY and m["workflow_path"] == OBSERVER_PATH
            and m["workflow_blob_sha"] == OBSERVER_BLOB, "OBSERVER_SOURCE_BINDING_MISMATCH")
    require(integer(m["observer_run_id"], 1) and integer(m["run_attempt"], 1)
            and integer(m["artifact_id"], 1) and hex_value(m["head_sha"], HEX40), "OBSERVER_SOURCE_BINDING_MISMATCH")
    require(m["conclusion"] == "success" and m["artifact_name"] == "tasukeru-artifact-observer-report"
            and m["authenticity_or_approval"] == "NOT_DETERMINED", "OBSERVER_SOURCE_BINDING_MISMATCH")
    require(integer(m["bytes"], 1, MAX_ZIP) and m["bytes"] == len(raw)
            and hex_value(m["sha256"], HEX64) and m["sha256"] == sha(raw), "OBSERVER_ZIP_DIGEST_OR_SIZE_MISMATCH")


def read_archive(raw):
    expected = {"retrieval.json", "observation.json", "self-test.json"}
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        require(len(infos) == 3 and {i.filename for i in infos} == expected, "OBSERVER_ZIP_MEMBER_INVENTORY_MISMATCH")
        require(sum(i.file_size for i in infos) <= MAX_TOTAL, "OBSERVER_ZIP_TOTAL_LIMIT")
        for i in infos:
            kind = stat.S_IFMT(i.external_attr >> 16)
            require(kind in (0, stat.S_IFREG) and not i.is_dir() and not (i.flag_bits & 1)
                    and i.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "OBSERVER_ZIP_MEMBER_TYPE_UNRESOLVED")
            require(0 < i.file_size <= MAX_JSON, "OBSERVER_ZIP_MEMBER_SIZE_LIMIT")
            with z.open(i) as f:
                data = f.read(MAX_JSON + 1)
            require(len(data) == i.file_size and len(data) <= MAX_JSON, "OBSERVER_ZIP_MEMBER_SIZE_LIMIT")
            members[i.filename] = data
    return members


def validate_reports(members, gate):
    retrieval = strict_document(members["retrieval.json"])
    report = strict_document(members["observation.json"])
    tests = strict_document(members["self-test.json"])
    keys = {"retrieval_status", "repository", "workflow_path", "run_id", "run_attempt", "head_sha",
            "source_run_conclusion", "artifact_id", "artifact_name", "bundle_sha256", "compressed_bytes",
            "digest_check", "authenticity_or_approval"}
    require(isinstance(retrieval, dict) and set(retrieval) == keys, "SOURCE_MANIFEST_SCHEMA_MISMATCH")
    require(retrieval["retrieval_status"] == "READY_FOR_OBSERVATION"
            and retrieval["repository"] == REPOSITORY
            and retrieval["workflow_path"] == ".github/workflows/tasukeru-analysis.yml"
            and retrieval["artifact_name"] == "tasukeru-advisory-logs"
            and retrieval["digest_check"] == "MATCHED_GITHUB_RECORDED_DIGEST"
            and retrieval["authenticity_or_approval"] == "NOT_DETERMINED", "SOURCE_MANIFEST_NOT_READY")
    require(all(integer(retrieval[k], 1) for k in ("run_id", "run_attempt", "artifact_id"))
            and integer(retrieval["compressed_bytes"], 1, 64 * 1024 * 1024)
            and hex_value(retrieval["head_sha"], HEX40) and hex_value(retrieval["bundle_sha256"], HEX64)
            and retrieval["source_run_conclusion"] in ("success", "failure", "cancelled", "timed_out", "neutral", "skipped", "action_required", "stale"),
            "SOURCE_MANIFEST_VALUE_UNRESOLVED")
    require(isinstance(report, dict) and report.get("schema_version") == "tasukeru-artifact-observation-draft-v1",
            "OBSERVER_REPORT_SCHEMA_MISMATCH")
    require(gate.exact_value(report.get("github_source"), retrieval)
            and report.get("bundle_sha256") == retrieval["bundle_sha256"], "OBSERVATION_RETRIEVAL_BINDING_MISMATCH")
    require(report.get("unknowns") == [] and type(report.get("unknowns")) is list
            and report.get("arl_run_id_value_check") == "MATCHED_LITERAL_RUN_ID", "OBSERVATION_UNRESOLVED")
    require(report.get("same_snapshot_relationship") == "UNKNOWN" and report.get("cause_or_actor") == "UNKNOWN"
            and report.get("safety_approval_or_authenticity") == "NOT_DETERMINED", "OBSERVATION_UNSUPPORTED_CONCLUSION")
    policy = report.get("policy", {})
    require(isinstance(policy, dict) and policy.get("report_only") is True
            and policy.get("automatic_repair") is False and policy.get("human_review_required") is True,
            "OBSERVER_POLICY_UNRESOLVED")
    require(isinstance(tests, dict) and tests.get("status") == "PASSED"
            and type(tests.get("tests_total")) is int and tests["tests_total"] == 25
            and type(tests.get("tests_passed")) is int and tests["tests_passed"] == 25 and tests.get("failed") == []
            and isinstance(tests.get("tests"), list) and len(tests["tests"]) == 25
            and all(isinstance(t, dict) and t.get("passed") is True for t in tests["tests"]), "OBSERVER_SELF_TEST_REPORT_UNRESOLVED")
    rows = report.get("actual_parsed_arl_rows")
    require(integer(rows, 0, 10000), "ARL_ROW_COUNT_UNRESOLVED")
    row_checks, hash_checks = report.get("arl_row_count_checks"), report.get("artifact_hash_checks")
    require(isinstance(row_checks, list) and len(row_checks) == 3
            and isinstance(hash_checks, list) and 1 <= len(hash_checks) <= 100, "OBSERVATION_CHECK_INVENTORY_UNRESOLVED")
    row_inventory = {("tasukeru_arl_verify.json", "row_count"), ("tasukeru_announcement.json", "arl.row_count"),
                     ("tasukeru_clean_run_draft.json", "summary.arl_rows")}
    seen = set()
    for item in row_checks:
        require(isinstance(item, dict) and set(item) == {"source", "field", "reported_rows", "actual_parsed_rows",
                    "values_match", "signal", "same_generation"}, "ROW_CHECK_SCHEMA_MISMATCH")
        pair = (item["source"], item["field"])
        require(pair in row_inventory and pair not in seen, "ROW_CHECK_INVENTORY_MISMATCH")
        seen.add(pair)
        require(integer(item["reported_rows"], 0, 10000) and type(item["actual_parsed_rows"]) is int
                and item["actual_parsed_rows"] == rows and item["same_generation"] == "UNKNOWN", "ROW_CHECK_VALUE_UNRESOLVED")
        match = item["reported_rows"] == rows
        require(item["values_match"] is match and item["signal"] == ("ARL_ROW_COUNT_VALUE_MATCH" if match else "ARL_ROW_COUNT_VALUE_DIFFERS"),
                "ROW_CHECK_INTERNAL_INCONSISTENCY")
    seen = set()
    for item in hash_checks:
        require(isinstance(item, dict) and set(item) == {"artifact", "recorded_sha256", "actual_sha256",
                    "recorded_bytes", "actual_bytes", "values_match", "signal"}, "HASH_CHECK_SCHEMA_MISMATCH")
        name = item["artifact"]
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.\-/]{1,300}", name) is not None
                and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and name not in seen,
                "HASH_CHECK_INVENTORY_MISMATCH")
        seen.add(name)
        require(all(hex_value(item[k], HEX64) for k in ("recorded_sha256", "actual_sha256"))
                and all(integer(item[k], 0, 64 * 1024 * 1024) for k in ("recorded_bytes", "actual_bytes")),
                "HASH_CHECK_VALUE_UNRESOLVED")
        match = item["recorded_sha256"] == item["actual_sha256"] and item["recorded_bytes"] == item["actual_bytes"]
        require(item["values_match"] is match and item["signal"] == ("ARTIFACT_BYTES_MATCH" if match else "ARTIFACT_BYTES_DIFFER"),
                "HASH_CHECK_INTERNAL_INCONSISTENCY")
    count = sum(x["values_match"] is False for x in row_checks + hash_checks)
    require(integer(report.get("observed_difference_count"), 0, 16) and report["observed_difference_count"] == count,
            "DIFFERENCE_INVENTORY_INCOMPLETE")
    require(report.get("observation_status") == ("DIFFERENCES_OBSERVED" if count else "VALUES_MATCH_IN_CHECKED_SCOPE"),
            "OBSERVATION_STATUS_INCONSISTENT")
    return gate.packet_from_observation(report, members["observation.json"]), count


def exercise(packet, scenario, gate, controller, context_reader, activity=None):
    good = gate.make_fixture_proposal(copy.deepcopy(packet))
    bad = copy.deepcopy(good)
    if bad["facts"]:
        fact = bad["facts"][0]
        key = "actual_parsed_rows" if fact["kind"] == "ARL_ROW_COUNT" else "actual_bytes"
        fact[key] += 1
    else:
        bad["cause"] = "UNSUPPORTED_CAUSE_ASSERTION"
    initial = encoded(good if scenario == "consistent" else bad)
    registry = controller.MockApprovalRegistry()
    now = {"value": 1000}
    def bound_context():
        return {**context_reader(), "authority_epoch": registry.epoch}
    ctrl = controller.ResubmissionController("MOCK-DEMO-" + scenario, packet, bound_context, lambda: now["value"])
    ctrl.start(initial)
    calls = []
    entered, release = threading.Event(), threading.Event()
    def generate(_):
        calls.append("DETERMINISTIC_FIXTURE_ONLY")
        if activity is not None:
            activity.append({"scenario": scenario, "kind": "MOCK_FIXTURE_GENERATION"})
        if scenario == "double_request":
            entered.set()
            if not release.wait(timeout=2):
                raise RuntimeError("Fixture barrier timeout")
        if scenario == "result_unknown":
            return {"state": "RESULT_UNKNOWN", "payload": None}
        if scenario == "human_stop":
            ctrl.stop()
        out = copy.deepcopy(good)
        if scenario == "still_inconsistent":
            out = bad
        if scenario == "unsupported_cause":
            out["cause"] = "REPORTING_BUG_CONFIRMED"
        return {"state": "COMPLETED", "payload": encoded(out)}
    operations = []
    if scenario in ("consistent", "no_approval"):
        operations.append(ctrl.regenerate(None, registry, generate))
    else:
        request = ctrl.approval_request()
        grant = registry.issue(request, now=1000, ttl=1 if scenario == "expired_approval" else 60)
        if scenario == "expired_approval":
            now["value"] = 1001
        if scenario == "double_request":
            thread = threading.Thread(target=lambda: operations.append(ctrl.regenerate(grant, registry, generate)))
            thread.start()
            require(entered.wait(timeout=2), "FIXTURE_CONCURRENCY_UNRESOLVED")
            operations.append(ctrl.regenerate(grant, registry, generate))
            release.set()
            thread.join(timeout=2)
            require(not thread.is_alive(), "FIXTURE_CONCURRENCY_UNRESOLVED")
        else:
            operations.append(ctrl.regenerate(grant, registry, generate))
        if scenario == "replay_approval":
            operations.append(ctrl.regenerate(grant, registry, generate))
            require(registry.consume(grant, request, now["value"]) == "APPROVAL_ALREADY_USED", "APPROVAL_REPLAY_NOT_BLOCKED")
    trace = ctrl.snapshot()
    expected_state, expected_calls = SCENARIOS[scenario]
    invariants = {"initial_proposal_preserved": ctrl.proposals[0] == initial,
                  "one_regeneration_per_case": len(calls) <= 1,
                  "no_automatic_application": trace["automatic_apply"] is False,
                  "no_final_adoption": trace["human_final_adoption"] is False,
                  "original_records_not_repaired": trace["original_records_repaired"] is False}
    if trace["state"] == "HUMAN_REVIEW":
        p = gate.strict_json(ctrl.proposals[-1])
        invariants["UNKNOWN_preserved"] = p["cause"] == "UNKNOWN" and p["actor"] == "UNKNOWN" and p["approval"] == "NOT_DETERMINED"
    if scenario == "human_stop":
        invariants["remote_cancel_not_claimed"] = any(e.get("remote_cancellation") == "NOT_CONFIRMED" for e in trace["events"])
    passed = trace["state"] == expected_state and len(calls) == expected_calls and all(invariants.values())
    return {"scenario": scenario, "passed": passed, "expected_state": expected_state,
            "actual_state": trace["state"], "expected_fixture_calls": expected_calls,
            "fixture_calls": len(calls), "invariants": invariants, "trace": trace,
            "operation_results": operations, "ai_output": "DETERMINISTIC_FIXTURE",
            "approval_channel": "SIMULATED_FIXTURE_DRIVER"}, ctrl.proposals


def synthetic_packet():
    return {"source": {"repository": REPOSITORY, "workflow_path": ".github/workflows/tasukeru-analysis.yml",
                       "run_id": 1, "run_attempt": 1, "head_sha": "0" * 40, "artifact_id": 2,
                       "artifact_name": "tasukeru-advisory-logs", "bundle_sha256": "0" * 64,
                       "observation_sha256": "1" * 64},
            "facts": [{"fact_id": "ROW:fixture:count", "kind": "ARL_ROW_COUNT",
                       "evidence_class": "SYNTHETIC_TEST_FIXTURE", "actual_parsed_rows": 93,
                       "reported_rows": 87, "values_match": False}], "evidence_class": "SYNTHETIC_TEST_FIXTURE"}


def self_tests(gate, controller):
    rows = []
    for scope in ("one_difference", "zero_differences"):
        packet = synthetic_packet()
        if scope == "zero_differences":
            packet["facts"] = []
        for scenario in SCENARIOS:
            result, _ = exercise(packet, scenario, gate, controller, lambda: {"test_scope": scope})
            rows.append({"name": scope + ":" + scenario, "passed": result["passed"]})
    return {"status": "PASSED" if all(x["passed"] for x in rows) else "FAILED",
            "tests_total": len(rows), "tests_passed": sum(x["passed"] for x in rows),
            "fixture_only": True, "ai_api_calls": 0, "tests": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tasukeru experiment; AI and approval are ALWAYS simulated")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--observer-zip", type=Path)
    parser.add_argument("--retrieval-manifest", type=Path)
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    results, activity = [], []
    try:
        gate, controller = modules()
        if args.repo_root:
            baseline_check(args.repo_root)
        if args.self_test:
            result = self_tests(gate, controller)
            save(args.output / "self-test.json", encoded(result))
            print("Demo self-tests: " + result["status"] + " " + str(result["tests_passed"]) + "/" + str(result["tests_total"]))
            return 0 if result["status"] == "PASSED" else 1
        require(args.observer_zip is not None and args.retrieval_manifest is not None, "INPUT_PATHS_REQUIRED")
        manifest_raw = read_bounded(args.retrieval_manifest, MAX_JSON)
        manifest = strict_document(manifest_raw)
        require(isinstance(manifest, dict) and manifest.get("read_status") == "READY_FOR_DEMO", "OBSERVER_RETRIEVAL_NOT_READY")
        zip_raw = read_bounded(args.observer_zip, MAX_ZIP)
        validate_download(manifest, zip_raw)
        members = read_archive(zip_raw)
        packet, count = validate_reports(members, gate)
        frozen = {"observer_zip_sha256": sha(zip_raw), "download_manifest_sha256": sha(manifest_raw),
                  "packet_sha256": sha(encoded(packet)), "demo_gate_sha256": MODULE_HASHES["mediation_gate_draft"],
                  "demo_controller_sha256": MODULE_HASHES["resubmission_controller_draft"],
                  "demo_entry_sha256": sha(Path(__file__).read_bytes())}
        def context_reader():
            parent = Path(__file__).resolve().parent
            current = {"observer_zip_sha256": sha(read_bounded(args.observer_zip, MAX_ZIP)),
                    "download_manifest_sha256": sha(read_bounded(args.retrieval_manifest, MAX_JSON)),
                    "packet_sha256": frozen["packet_sha256"],
                    "demo_gate_sha256": sha((parent / "mediation_gate_draft.py").read_bytes()),
                    "demo_controller_sha256": sha((parent / "resubmission_controller_draft.py").read_bytes()),
                    "demo_entry_sha256": sha(Path(__file__).read_bytes())}
            require(current == frozen, "DEMO_CONTEXT_CHANGED")
            return current
        require(context_reader() == frozen, "DEMO_PREFLIGHT_CONTEXT_MISMATCH")
        for scenario in SCENARIOS if args.scenario == "all" else [args.scenario]:
            result, proposals = exercise(packet, scenario, gate, controller, context_reader, activity)
            results.append(result)
            save(args.output / "cases" / (scenario + ".json"), encoded(result))
            for index, proposal in enumerate(proposals, start=1):
                save(args.output / "cases" / scenario / ("proposal-v" + str(index) + ".json"), proposal)
        require(context_reader() == frozen, "DEMO_POSTFLIGHT_CONTEXT_MISMATCH")
        passed = all(r["passed"] for r in results)
        report = {"schema_version": VERSION, "draft_status": "UNADOPTED_EXPERIMENT",
                  "status": "EXPECTED_DEMO_BEHAVIOR" if passed else "DEMO_EXPECTATION_FAILED",
                  "ai_output": "DETERMINISTIC_FIXTURES_ONLY", "approval_channel": "SIMULATED_FIXTURE_DRIVER",
                  "human_authentication_tested": False, "real_AI_calls": 0,
                  "automatic_apply": False, "final_adoption": False, "original_records_repaired": False,
                  "observer_download": manifest, "source_analysis": packet["source"],
                  "observed_difference_count": count, "cause": "UNKNOWN", "actor": "UNKNOWN",
                  "same_snapshot_relationship": "UNKNOWN", "approval": "NOT_DETERMINED",
                  "self_test_report": "PRODUCER_REPORTED_25_PASSED_NOT_RERUN_HERE",
                  "cases_total": len(results), "cases_passed": sum(r["passed"] for r in results),
                  "input_and_code_context": frozen, "results": results,
                  "limits": ["Fixture control flow only; actual AI correction ability is unevaluated.",
                             "One regeneration per independent mock case; no real approval service or durable replay store.",
                             "Numerical/schema/source checks do not establish causality, authenticity or whole-system safety.",
                             "Remote cancellation is not attempted or confirmed."]}
        save(args.output / "demo-report.json", encoded(report))
        save(args.output / "evidence-packet.json", encoded(packet))
        text = "# Tasukeru mediation experiment\n\nAI output and approval are simulated. Success is not approval or safety verification.\n\n"
        text += "Status: " + report["status"] + "\n\nObserver run: " + str(manifest["observer_run_id"]) + "\n\nSource analysis run: " + str(packet["source"]["run_id"]) + "\n\nObserved differences retained: " + str(count) + "\n\n"
        text += "| Scenario | State | Mock generations | Expected behavior |\n|---|---|---:|---|\n"
        for r in results:
            text += "| " + r["scenario"] + " | " + r["actual_state"] + " | " + str(r["fixture_calls"]) + " | " + ("PASS" if r["passed"] else "FAIL") + " |\n"
        text += "\nCause, actor and snapshot relationship remain UNKNOWN. Final adoption remains NOT_DETERMINED.\n"
        save(args.output / "summary.md", text.encode("utf-8"))
        print("Demo status: " + report["status"] + " " + str(report["cases_passed"]) + "/" + str(report["cases_total"]))
        return 0 if passed else 1
    except OutputUnresolved:
        print("Report write result is unresolved; no write retry attempted.", file=sys.stderr)
        return 2
    except (Unresolved, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
        reason = str(exc) if isinstance(exc, Unresolved) else "INPUT_OR_EXECUTION_UNRESOLVED"
        report = {"schema_version": VERSION, "draft_status": "UNADOPTED_EXPERIMENT", "status": "STOPPED_UNKNOWN",
                  "reason": reason, "ai_output": "DETERMINISTIC_FIXTURES_ONLY", "approval_channel": "SIMULATED_FIXTURE_DRIVER",
                  "cases_total": len(results), "fixture_generations": len(activity), "real_AI_calls": 0,
                  "completed_cases": results, "activity": activity,
                  "automatic_apply": False, "final_adoption": False, "approval": "NOT_DETERMINED"}
        save(args.output / "demo-report.json", encoded(report))
        save(args.output / "summary.md", ("# Tasukeru mediation experiment\n\nStatus: STOPPED_UNKNOWN\n\nReason: " + reason + "\n\nMock generations recorded: " + str(len(activity)) + ". No final adoption was performed.\n").encode())
        print("Demo status: STOPPED_UNKNOWN (" + reason + ")")
        return 1 if args.self_test else 0


if __name__ == "__main__":
    raise SystemExit(main())
