"""Tests for the deterministic Patch 13 hash-chain analyzer."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "stress" / "fixtures" / "arl_hash_chain"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tasukeru_arl_hash_chain_analyzer as analyzer  # noqa: E402
import tasukeru_arl_hash_chain_stress as stress  # noqa: E402


RESULT_FIELDS = {
    "schema_version",
    "generated_at_utc",
    "mode",
    "source_contract",
    "source_documents",
    "source_manifest_sha256",
    "safety_boundary",
    "cases",
    "counts",
    "checks",
    "graph_summary",
    "verified",
}
GRAPH_FIELDS = {
    "schema_version",
    "generated_at_utc",
    "mode",
    "logical_root",
    "nodes",
    "edges",
    "counts",
    "safety_boundary",
    "graph_hash",
}
VERIFY_FIELDS = {
    "schema_version",
    "generated_at_utc",
    "verified",
    "checks",
    "source_document_sha256",
    "source_schema_versions",
    "source_manifest_sha256",
    "output_existence_checks",
    "output_filename_set_exact",
    "result_sha256",
    "graph_sha256",
    "report_sha256",
    "graph_hash",
    "counts",
    "safety_boundary",
    "hmac_enabled",
    "authenticity_claimed",
}
ISSUE_FIELDS = {
    "issue_ordinal",
    "line_number",
    "reason_code",
    "detail",
    "stored_value",
    "recomputed_value",
    "is_integrity_issue",
}
REPORT_SECTIONS = (
    "## Summary",
    "## Source Binding Verification",
    "## Case Classifications",
    "## Reason-Code Ordering",
    "## Integrity Issue Counts",
    "## Head-Hash Evidence",
    "## Graph Summary",
    "## Checks",
    "## Safety Boundary",
    "## Limitations",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(text)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected object in {path.name}.")
    return payload


class TasukeruArlHashChainAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_dir = self.root / "source"
        self.output_dir = self.root / "output"
        result = stress.run_stress(FIXTURES_DIR)
        self.assertTrue(result["verified"])
        artifacts = stress.write_artifacts(result, self.source_dir)
        self.assertTrue(artifacts["verify"]["verified"])

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_cli(
        self,
        *,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = analyzer.main(
                [
                    "--input-dir",
                    str(input_dir or self.source_dir),
                    "--output-dir",
                    str(output_dir or self.output_dir),
                ]
            )
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def run_canonical(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        exit_code, _, stderr = self.run_cli()
        self.assertEqual(exit_code, 0, stderr)
        return (
            load_json(self.output_dir / analyzer.RESULT_FILENAME),
            load_json(self.output_dir / analyzer.GRAPH_FILENAME),
            load_json(self.output_dir / analyzer.VERIFY_FILENAME),
        )

    def mutate_result(
        self,
        mutation: Callable[[dict[str, Any]], None],
        *,
        rebind: bool = True,
    ) -> None:
        result_path = self.source_dir / analyzer.SOURCE_RESULT_FILENAME
        result = load_json(result_path)
        mutation(result)
        write_json(result_path, result)
        if rebind:
            verify_path = self.source_dir / analyzer.SOURCE_VERIFY_FILENAME
            verify = load_json(verify_path)
            verify["result_sha256"] = sha256_file(result_path)
            write_json(verify_path, verify)

    def mutate_verify(self, mutation: Callable[[dict[str, Any]], None]) -> None:
        verify_path = self.source_dir / analyzer.SOURCE_VERIFY_FILENAME
        verify = load_json(verify_path)
        mutation(verify)
        write_json(verify_path, verify)

    def assert_semantic_failure(self) -> dict[str, Any]:
        exit_code, _, stderr = self.run_cli()
        self.assertEqual(exit_code, 1, stderr)
        verify = load_json(self.output_dir / analyzer.VERIFY_FILENAME)
        self.assertFalse(verify["verified"])
        self.assertEqual(
            {path.name for path in self.output_dir.iterdir()},
            analyzer.EXPECTED_OUTPUT_FILES,
        )
        return verify

    def assert_operational_failure(
        self,
        expected_reason: str,
        *,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        exit_code, _, stderr = self.run_cli(
            input_dir=input_dir,
            output_dir=output_dir,
        )
        self.assertEqual(exit_code, 2)
        self.assertIn(expected_reason, stderr)

    def create_second_source(self, root: Path) -> Path:
        source_dir = root / "different-source-root"
        result = stress.run_stress(FIXTURES_DIR)
        artifacts = stress.write_artifacts(result, source_dir)
        self.assertTrue(artifacts["verify"]["verified"])
        return source_dir

    def test_canonical_analyzer_cli_returns_zero(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "tasukeru_arl_hash_chain_analyzer.py"),
                "--input-dir",
                str(self.source_dir),
                "--output-dir",
                str(self.output_dir),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("verified: True", completed.stdout)

    def test_canonical_output_filename_set_is_exact(self) -> None:
        self.run_canonical()
        self.assertEqual(
            {path.name for path in self.output_dir.iterdir()},
            analyzer.EXPECTED_OUTPUT_FILES,
        )

    def test_result_schema_is_exact(self) -> None:
        result, _, _ = self.run_canonical()
        self.assertEqual(set(result), RESULT_FIELDS)
        self.assertEqual(result["schema_version"], analyzer.RESULT_SCHEMA_VERSION)

    def test_graph_schema_is_exact(self) -> None:
        _, graph, _ = self.run_canonical()
        self.assertEqual(set(graph), GRAPH_FIELDS)
        self.assertEqual(graph["schema_version"], analyzer.GRAPH_SCHEMA_VERSION)

    def test_verify_schema_is_exact(self) -> None:
        _, _, verify = self.run_canonical()
        self.assertEqual(set(verify), VERIFY_FIELDS)
        self.assertEqual(verify["schema_version"], analyzer.VERIFY_SCHEMA_VERSION)

    def test_all_generated_timestamps_are_deterministic(self) -> None:
        result, graph, verify = self.run_canonical()
        self.assertEqual(
            {
                result["generated_at_utc"],
                graph["generated_at_utc"],
                verify["generated_at_utc"],
            },
            {analyzer.DETERMINISTIC_GENERATED_AT_UTC},
        )

    def test_source_result_sha256_binding_is_verified(self) -> None:
        result, _, verify = self.run_canonical()
        expected = sha256_file(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        self.assertEqual(
            result["source_documents"][analyzer.SOURCE_RESULT_FILENAME]["sha256"],
            expected,
        )
        self.assertEqual(
            verify["source_document_sha256"][analyzer.SOURCE_RESULT_FILENAME],
            expected,
        )

    def test_source_report_sha256_binding_is_verified(self) -> None:
        result, _, verify = self.run_canonical()
        expected = sha256_file(self.source_dir / analyzer.SOURCE_REPORT_FILENAME)
        self.assertEqual(
            result["source_documents"][analyzer.SOURCE_REPORT_FILENAME]["sha256"],
            expected,
        )
        self.assertEqual(
            verify["source_document_sha256"][analyzer.SOURCE_REPORT_FILENAME],
            expected,
        )

    def test_manifest_sha256_cross_document_binding_is_verified(self) -> None:
        result, _, verify = self.run_canonical()
        source_result = load_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        source_verify = load_json(self.source_dir / analyzer.SOURCE_VERIFY_FILENAME)
        expected = source_result["manifest_sha256"]
        self.assertEqual(expected, source_verify["manifest_sha256"])
        self.assertEqual(result["source_manifest_sha256"], expected)
        self.assertEqual(verify["source_manifest_sha256"], expected)

    def test_t1_is_expected_canonical_validation(self) -> None:
        result, _, _ = self.run_canonical()
        case = result["cases"][0]
        self.assertEqual(case["case_id"], "valid_chain")
        self.assertEqual(case["classification"], "EXPECTED_CANONICAL_VALIDATION")
        self.assertEqual(case["actual_outcome"], "CHAIN_VALID")
        self.assertTrue(case["passed"])

    def test_t2_through_t7_are_expected_tamper_detections(self) -> None:
        result, _, _ = self.run_canonical()
        for case in result["cases"][1:]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(
                    case["classification"],
                    "EXPECTED_TAMPER_DETECTION",
                )
                self.assertEqual(case["actual_outcome"], "TAMPER_DETECTED")
                self.assertTrue(case["passed"])

    def test_all_cases_preserve_canonical_order(self) -> None:
        result, _, _ = self.run_canonical()
        self.assertEqual(
            [case["case_id"] for case in result["cases"]],
            list(analyzer.CANONICAL_CASE_IDS),
        )

    def test_primary_and_additional_reason_order_is_preserved(self) -> None:
        result, _, _ = self.run_canonical()
        source = load_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        for normalized, original in zip(
            result["cases"],
            source["cases"],
            strict=True,
        ):
            with self.subTest(case_id=normalized["case_id"]):
                self.assertEqual(
                    [reason["reason_code"] for reason in normalized["reasons"]],
                    original["reason_codes"],
                )
                self.assertEqual(normalized["reasons"][0]["role"], "primary")
                self.assertTrue(
                    all(
                        reason["role"] == "additional"
                        for reason in normalized["reasons"][1:]
                    )
                )

    def test_all_nineteen_integrity_issue_occurrences_are_preserved(self) -> None:
        result, _, _ = self.run_canonical()
        integrity_issues = [
            issue
            for case in result["cases"]
            for issue in case["issues"]
            if issue["is_integrity_issue"]
        ]
        self.assertEqual(len(integrity_issues), 19)

    def test_all_source_issue_entries_are_preserved_in_order(self) -> None:
        result, _, _ = self.run_canonical()
        source = load_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        for normalized, original in zip(
            result["cases"],
            source["cases"],
            strict=True,
        ):
            with self.subTest(case_id=normalized["case_id"]):
                self.assertEqual(len(normalized["issues"]), len(original["issues"]))
                self.assertEqual(
                    [issue["issue_ordinal"] for issue in normalized["issues"]],
                    list(range(1, len(original["issues"]) + 1)),
                )

    def test_each_issue_preserves_required_evidence(self) -> None:
        result, _, _ = self.run_canonical()
        source = load_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        for normalized_case, source_case in zip(
            result["cases"],
            source["cases"],
            strict=True,
        ):
            for normalized, original in zip(
                normalized_case["issues"],
                source_case["issues"],
                strict=True,
            ):
                self.assertEqual(set(normalized), ISSUE_FIELDS)
                for field in (
                    "line_number",
                    "reason_code",
                    "detail",
                    "stored_value",
                    "recomputed_value",
                ):
                    self.assertEqual(normalized[field], original[field])

    def test_head_hash_concepts_remain_separate(self) -> None:
        result, _, _ = self.run_canonical()
        source = load_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME)
        for normalized, original in zip(
            result["cases"],
            source["cases"],
            strict=True,
        ):
            self.assertEqual(
                normalized["expected_canonical_head_hash"],
                analyzer.CANONICAL_HEAD_HASH,
            )
            self.assertEqual(
                normalized["stored_head_hash"],
                original["stored_head_hash"],
            )
            self.assertEqual(
                normalized["recomputed_head_hash"],
                original["recomputed_head_hash"],
            )

    def test_graph_node_ids_are_stable_across_roots(self) -> None:
        _, graph_one, _ = self.run_canonical()
        second_root = self.root / "second"
        second_source = self.create_second_source(second_root)
        second_output = second_root / "output"
        exit_code, _, stderr = self.run_cli(
            input_dir=second_source,
            output_dir=second_output,
        )
        self.assertEqual(exit_code, 0, stderr)
        graph_two = load_json(second_output / analyzer.GRAPH_FILENAME)
        self.assertEqual(
            [node["id"] for node in graph_one["nodes"]],
            [node["id"] for node in graph_two["nodes"]],
        )

    def test_graph_edge_ids_are_stable_across_roots(self) -> None:
        _, graph_one, _ = self.run_canonical()
        second_root = self.root / "second"
        second_source = self.create_second_source(second_root)
        second_output = second_root / "output"
        exit_code, _, stderr = self.run_cli(
            input_dir=second_source,
            output_dir=second_output,
        )
        self.assertEqual(exit_code, 0, stderr)
        graph_two = load_json(second_output / analyzer.GRAPH_FILENAME)
        self.assertEqual(
            [edge["id"] for edge in graph_one["edges"]],
            [edge["id"] for edge in graph_two["edges"]],
        )

    def test_graph_reason_edges_preserve_order_and_role(self) -> None:
        result, graph, _ = self.run_canonical()
        for case in result["cases"]:
            case_node = analyzer.stable_id("hash_chain_case", case["case_id"])
            edges = sorted(
                (
                    edge
                    for edge in graph["edges"]
                    if edge["source"] == case_node and edge["type"] == "HAS_REASON"
                ),
                key=lambda edge: edge["properties"]["order"],
            )
            self.assertEqual(
                [edge["properties"]["order"] for edge in edges],
                list(range(1, len(case["reasons"]) + 1)),
            )
            self.assertEqual(
                [edge["properties"]["role"] for edge in edges],
                [reason["role"] for reason in case["reasons"]],
            )

    def test_graph_issue_edges_preserve_ordinal_order(self) -> None:
        result, graph, _ = self.run_canonical()
        for case in result["cases"]:
            case_node = analyzer.stable_id("hash_chain_case", case["case_id"])
            edges = sorted(
                (
                    edge
                    for edge in graph["edges"]
                    if edge["source"] == case_node and edge["type"] == "HAS_ISSUE"
                ),
                key=lambda edge: edge["properties"]["issue_ordinal"],
            )
            expected = [
                issue["issue_ordinal"]
                for issue in case["issues"]
                if issue["is_integrity_issue"]
            ]
            self.assertEqual(
                [edge["properties"]["issue_ordinal"] for edge in edges],
                expected,
            )

    def test_graph_does_not_contain_raw_fixture_rows(self) -> None:
        _, _, _ = self.run_canonical()
        graph_bytes = (self.output_dir / analyzer.GRAPH_FILENAME).read_bytes()
        for fixture_name in sorted(
            name for name in stress.PATCH_13_CASE_IDS if name != "valid_chain"
        ):
            fixture_path = FIXTURES_DIR / f"{fixture_name}.jsonl"
            for line in fixture_path.read_bytes().splitlines():
                self.assertNotIn(line, graph_bytes)
        for line in (FIXTURES_DIR / "valid_chain.jsonl").read_bytes().splitlines():
            self.assertNotIn(line, graph_bytes)

    def test_separate_roots_produce_byte_identical_outputs(self) -> None:
        self.run_canonical()
        second_root = self.root / "determinism-copy"
        second_source = self.create_second_source(second_root)
        second_output = second_root / "output"
        exit_code, _, stderr = self.run_cli(
            input_dir=second_source,
            output_dir=second_output,
        )
        self.assertEqual(exit_code, 0, stderr)
        for filename in analyzer.EXPECTED_OUTPUT_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    (self.output_dir / filename).read_bytes(),
                    (second_output / filename).read_bytes(),
                )

    def test_missing_source_result_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_RESULT_FILENAME).unlink()
        self.assert_operational_failure("ARL_ANALYZER_SOURCE_FILE_MISSING")

    def test_missing_source_report_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_REPORT_FILENAME).unlink()
        self.assert_operational_failure("ARL_ANALYZER_SOURCE_FILE_MISSING")

    def test_missing_source_verify_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_VERIFY_FILENAME).unlink()
        self.assert_operational_failure("ARL_ANALYZER_SOURCE_FILE_MISSING")

    def test_extra_source_file_returns_two(self) -> None:
        (self.source_dir / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
        self.assert_operational_failure("ARL_ANALYZER_UNEXPECTED_SOURCE_ENTRY")

    def test_invalid_result_json_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_RESULT_FILENAME).write_text(
            "{invalid\n",
            encoding="utf-8",
        )
        self.assert_operational_failure("ARL_ANALYZER_RESULT_JSON_INVALID")

    def test_invalid_verify_json_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_VERIFY_FILENAME).write_text(
            "{invalid\n",
            encoding="utf-8",
        )
        self.assert_operational_failure("ARL_ANALYZER_VERIFY_JSON_INVALID")

    def test_unsupported_result_schema_returns_two(self) -> None:
        self.mutate_result(
            lambda result: result.__setitem__("schema_version", "unsupported"),
            rebind=False,
        )
        self.assert_operational_failure("ARL_ANALYZER_RESULT_SCHEMA_UNSUPPORTED")

    def test_unsupported_verify_schema_returns_two(self) -> None:
        self.mutate_verify(
            lambda verify: verify.__setitem__("schema_version", "unsupported")
        )
        self.assert_operational_failure("ARL_ANALYZER_VERIFY_SCHEMA_UNSUPPORTED")

    def test_non_object_result_returns_two(self) -> None:
        write_json(self.source_dir / analyzer.SOURCE_RESULT_FILENAME, [])
        self.assert_operational_failure("ARL_ANALYZER_RESULT_JSON_INVALID")

    def test_non_object_verify_returns_two(self) -> None:
        write_json(self.source_dir / analyzer.SOURCE_VERIFY_FILENAME, [])
        self.assert_operational_failure("ARL_ANALYZER_VERIFY_JSON_INVALID")

    def test_non_empty_output_directory_returns_two(self) -> None:
        self.output_dir.mkdir()
        (self.output_dir / "stale.txt").write_text("stale\n", encoding="utf-8")
        self.assert_operational_failure("ARL_ANALYZER_OUTPUT_DIRECTORY_NOT_EMPTY")

    def test_source_verify_false_produces_exit_one_and_artifacts(self) -> None:
        self.mutate_verify(lambda verify: verify.__setitem__("verified", False))
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_verify_verified"])

    def test_source_result_false_produces_exit_one_and_artifacts(self) -> None:
        self.mutate_result(lambda result: result.__setitem__("verified", False))
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_result_verified"])

    def test_result_sha_mismatch_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result.__setitem__("mode", "changed"),
            rebind=False,
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_result_hash_matches"])

    def test_report_sha_mismatch_produces_exit_one(self) -> None:
        report_path = self.source_dir / analyzer.SOURCE_REPORT_FILENAME
        report_path.write_text(
            report_path.read_text(encoding="utf-8") + "changed\n",
            encoding="utf-8",
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_report_hash_matches"])

    def test_manifest_sha_mismatch_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result.__setitem__("manifest_sha256", "0" * 64)
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_manifest_hash_bound"])

    def test_wrong_canonical_case_order_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"].__setitem__(
                slice(0, 2),
                list(reversed(result["cases"][:2])),
            )
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["canonical_case_order_valid"])

    def test_missing_canonical_case_produces_exit_one(self) -> None:
        self.mutate_result(lambda result: result["cases"].pop())
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["canonical_case_order_valid"])

    def test_extra_case_produces_exit_one(self) -> None:
        def add_extra(result: dict[str, Any]) -> None:
            extra = json.loads(json.dumps(result["cases"][-1]))
            extra["case_id"] = "unexpected_case"
            result["cases"].append(extra)

        self.mutate_result(add_extra)
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["canonical_case_order_valid"])

    def test_wrong_tamper_outcome_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1].__setitem__(
                "actual_outcome",
                "CHAIN_VALID",
            )
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["canonical_case_semantics_valid"])

    def test_wrong_reason_order_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1].__setitem__(
                "reason_codes",
                list(reversed(result["cases"][1]["reason_codes"])),
            )
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["reason_code_order_valid"])

    def test_issue_count_mismatch_produces_exit_one(self) -> None:
        self.mutate_result(lambda result: result["cases"][1]["issues"].pop())
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_reason_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1]["issues"][0].__setitem__(
                "reason_code",
                "ARL_CHAIN_HASH_MISMATCH",
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_order_mutation_produces_exit_one(self) -> None:
        def swap_issues(result: dict[str, Any]) -> None:
            issues = result["cases"][1]["issues"]
            issues[0], issues[1] = issues[1], issues[0]

        self.mutate_result(swap_issues)
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_line_number_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1]["issues"][0].__setitem__(
                "line_number",
                3,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_detail_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1]["issues"][0].__setitem__(
                "detail",
                "Changed canonical detail.",
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_stored_value_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1]["issues"][0].__setitem__(
                "stored_value",
                "0" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_issue_recomputed_value_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][1]["issues"][0].__setitem__(
                "recomputed_value",
                "1" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["source_issue_contract_valid"])

    def test_rebound_valid_chain_stored_head_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["cases"][0].__setitem__(
                "stored_head_hash",
                "2" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["head_hash_evidence_valid"])

    def test_rebound_valid_chain_recomputed_head_mutation_produces_exit_one(
        self,
    ) -> None:
        self.mutate_result(
            lambda result: result["cases"][0].__setitem__(
                "recomputed_head_hash",
                "3" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["head_hash_evidence_valid"])

    def test_rebound_tamper_case_stored_head_mutation_produces_exit_one(
        self,
    ) -> None:
        self.mutate_result(
            lambda result: result["cases"][4].__setitem__(
                "stored_head_hash",
                "4" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["head_hash_evidence_valid"])

    def test_rebound_tamper_case_recomputed_head_mutation_produces_exit_one(
        self,
    ) -> None:
        self.mutate_result(
            lambda result: result["cases"][4].__setitem__(
                "recomputed_head_hash",
                "5" * 64,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertTrue(verify["checks"]["source_result_hash_matches"])
        self.assertFalse(verify["checks"]["head_hash_evidence_valid"])

    def test_hmac_claim_is_rejected(self) -> None:
        self.mutate_verify(lambda verify: verify.__setitem__("hmac_enabled", True))
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_hmac_disabled"])

    def test_authenticity_claim_is_rejected(self) -> None:
        self.mutate_verify(
            lambda verify: verify.__setitem__("authenticity_claimed", True)
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_authenticity_not_claimed"])

    def test_safety_boundary_mutation_produces_exit_one(self) -> None:
        self.mutate_result(
            lambda result: result["safety_boundary"].__setitem__(
                "automatic_repair",
                True,
            )
        )
        verify = self.assert_semantic_failure()
        self.assertFalse(verify["checks"]["source_result_safety_boundary_valid"])

    def test_absolute_temporary_paths_are_absent_from_artifacts(self) -> None:
        self.run_canonical()
        root_text = str(self.root)
        for filename in analyzer.EXPECTED_OUTPUT_FILES:
            with self.subTest(filename=filename):
                self.assertNotIn(
                    root_text,
                    (self.output_dir / filename).read_text(encoding="utf-8"),
                )

    def test_safety_boundary_contains_no_automatic_or_external_authority(self) -> None:
        result, graph, verify = self.run_canonical()
        for boundary in (
            result["safety_boundary"],
            graph["safety_boundary"],
            verify["safety_boundary"],
        ):
            self.assertTrue(boundary["advisory_only"])
            self.assertTrue(boundary["human_review_required"])
            for key, value in boundary.items():
                if key not in {"advisory_only", "human_review_required"}:
                    self.assertFalse(value, key)

    def test_existing_patch_13_source_artifacts_are_not_modified(self) -> None:
        before = {
            path.name: sha256_file(path)
            for path in self.source_dir.iterdir()
            if path.is_file()
        }
        self.run_canonical()
        after = {
            path.name: sha256_file(path)
            for path in self.source_dir.iterdir()
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_existing_patch_4_analyzer_is_not_imported_or_modified(self) -> None:
        patch4_path = SCRIPTS_DIR / "tasukeru_arl_analyzer.py"
        before = sha256_file(patch4_path)
        self.run_canonical()
        after = sha256_file(patch4_path)
        source_text = Path(analyzer.__file__).read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertNotIn("import tasukeru_arl_analyzer", source_text)
        self.assertNotIn("from tasukeru_arl_analyzer", source_text)

    def test_missing_input_directory_returns_two(self) -> None:
        self.assert_operational_failure(
            "ARL_ANALYZER_INPUT_DIRECTORY_INVALID",
            input_dir=self.root / "missing",
        )

    def test_invalid_result_utf8_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_RESULT_FILENAME).write_bytes(b"\xff")
        self.assert_operational_failure("ARL_ANALYZER_RESULT_UTF8_INVALID")

    def test_invalid_report_utf8_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_REPORT_FILENAME).write_bytes(b"\xff")
        self.assert_operational_failure("ARL_ANALYZER_REPORT_UTF8_INVALID")

    def test_invalid_verify_utf8_returns_two(self) -> None:
        (self.source_dir / analyzer.SOURCE_VERIFY_FILENAME).write_bytes(b"\xff")
        self.assert_operational_failure("ARL_ANALYZER_VERIFY_UTF8_INVALID")

    def test_extra_source_directory_returns_two(self) -> None:
        (self.source_dir / "unexpected-directory").mkdir()
        self.assert_operational_failure("ARL_ANALYZER_UNEXPECTED_SOURCE_ENTRY")

    def test_input_output_overlap_returns_two(self) -> None:
        self.assert_operational_failure(
            "ARL_ANALYZER_INPUT_OUTPUT_OVERLAP",
            output_dir=self.source_dir / "nested-output",
        )

    def test_existing_output_file_path_returns_two(self) -> None:
        self.output_dir.write_text("not a directory\n", encoding="utf-8")
        self.assert_operational_failure("ARL_ANALYZER_OUTPUT_DIRECTORY_INVALID")

    def test_invalid_cli_usage_returns_two(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "tasukeru_arl_hash_chain_analyzer.py"),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("required", completed.stderr)

    def test_output_verify_hashes_bind_three_outputs(self) -> None:
        _, _, verify = self.run_canonical()
        self.assertEqual(
            verify["result_sha256"],
            sha256_file(self.output_dir / analyzer.RESULT_FILENAME),
        )
        self.assertEqual(
            verify["graph_sha256"],
            sha256_file(self.output_dir / analyzer.GRAPH_FILENAME),
        )
        self.assertEqual(
            verify["report_sha256"],
            sha256_file(self.output_dir / analyzer.REPORT_FILENAME),
        )

    def test_graph_contains_all_minimum_node_types(self) -> None:
        _, graph, _ = self.run_canonical()
        self.assertTrue(
            {
                "HashChainArtifactSet",
                "SourceDocument",
                "HashChainCase",
                "ExpectedOutcome",
                "ObservedOutcome",
                "ReasonCode",
                "IntegrityIssue",
                "VerifyReport",
            }.issubset({node["type"] for node in graph["nodes"]})
        )

    def test_graph_contains_all_minimum_edge_types(self) -> None:
        _, graph, _ = self.run_canonical()
        self.assertTrue(
            {
                "HAS_SOURCE",
                "HAS_CASE",
                "EXPECTED_OUTCOME",
                "OBSERVED_OUTCOME",
                "HAS_REASON",
                "HAS_ISSUE",
                "VERIFIES",
            }.issubset({edge["type"] for edge in graph["edges"]})
        )

    def test_graph_hash_matches_canonical_graph_content(self) -> None:
        _, graph, _ = self.run_canonical()
        expected = analyzer.canonical_hash(
            {
                "schema_version": graph["schema_version"],
                "logical_root": graph["logical_root"],
                "nodes": graph["nodes"],
                "edges": graph["edges"],
            }
        )
        self.assertEqual(graph["graph_hash"], expected)

    def test_report_contains_all_required_sections(self) -> None:
        self.run_canonical()
        report = (self.output_dir / analyzer.REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
        positions = [report.index(section) for section in REPORT_SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_report_contains_all_required_limitations(self) -> None:
        self.run_canonical()
        report = (self.output_dir / analyzer.REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
        for statement in (
            "HMAC is not enabled.",
            "Authenticity is not claimed.",
            "Hash consistency is not an external identity proof.",
            "This artifact is advisory-only.",
            "Final review remains human-controlled.",
        ):
            self.assertIn(statement, report)

    def test_source_paths_are_logical_only(self) -> None:
        result, graph, _ = self.run_canonical()
        self.assertEqual(
            result["source_contract"]["logical_path"],
            analyzer.LOGICAL_SOURCE_ROOT,
        )
        for document in result["source_documents"].values():
            self.assertTrue(
                document["logical_path"].startswith(
                    f"{analyzer.LOGICAL_SOURCE_ROOT}/"
                )
            )
        root = next(
            node
            for node in graph["nodes"]
            if node["type"] == "HashChainArtifactSet"
        )
        self.assertEqual(
            root["properties"]["source_path"],
            analyzer.LOGICAL_SOURCE_ROOT,
        )

    def test_graph_has_exactly_seven_case_nodes(self) -> None:
        _, graph, _ = self.run_canonical()
        cases = [node for node in graph["nodes"] if node["type"] == "HashChainCase"]
        self.assertEqual(len(cases), 7)
        self.assertEqual(graph["counts"]["cases"], 7)

    def test_graph_has_exactly_nineteen_integrity_issue_nodes(self) -> None:
        _, graph, _ = self.run_canonical()
        issues = [
            node for node in graph["nodes"] if node["type"] == "IntegrityIssue"
        ]
        self.assertEqual(len(issues), 19)
        self.assertEqual(graph["counts"]["integrity_issues"], 19)

    def test_graph_nodes_and_edges_are_sorted_by_id(self) -> None:
        _, graph, _ = self.run_canonical()
        self.assertEqual(
            [node["id"] for node in graph["nodes"]],
            sorted(node["id"] for node in graph["nodes"]),
        )
        self.assertEqual(
            [edge["id"] for edge in graph["edges"]],
            sorted(edge["id"] for edge in graph["edges"]),
        )

    def test_canonical_aggregate_counts_are_exact(self) -> None:
        result, graph, verify = self.run_canonical()
        expected = dict(analyzer.CANONICAL_COUNTS)
        self.assertEqual(result["counts"], expected)
        self.assertEqual(verify["counts"], expected)
        self.assertEqual(graph["counts"]["cases"], expected["total_cases"])
        self.assertEqual(
            graph["counts"]["integrity_issues"],
            expected["total_integrity_errors"],
        )

    def test_canonical_result_and_verify_checks_are_all_true(self) -> None:
        result, _, verify = self.run_canonical()
        self.assertTrue(result["verified"])
        self.assertTrue(verify["verified"])
        self.assertTrue(all(result["checks"].values()))
        self.assertTrue(all(verify["checks"].values()))

    def test_output_existence_checks_are_all_true(self) -> None:
        _, _, verify = self.run_canonical()
        self.assertTrue(all(verify["output_existence_checks"].values()))
        self.assertTrue(verify["output_filename_set_exact"])

    def test_json_and_markdown_outputs_use_lf_and_one_final_newline(self) -> None:
        self.run_canonical()
        for filename in analyzer.EXPECTED_OUTPUT_FILES:
            with self.subTest(filename=filename):
                data = (self.output_dir / filename).read_bytes()
                self.assertNotIn(b"\r\n", data)
                self.assertTrue(data.endswith(b"\n"))
                self.assertFalse(data.endswith(b"\n\n"))

    def test_generated_artifacts_contain_no_temporary_root_name(self) -> None:
        self.run_canonical()
        temporary_name = self.root.name
        for filename in analyzer.EXPECTED_OUTPUT_FILES:
            self.assertNotIn(
                temporary_name,
                (self.output_dir / filename).read_text(encoding="utf-8"),
            )

    def test_source_directory_contains_exactly_three_files(self) -> None:
        self.run_canonical()
        self.assertEqual(
            {path.name for path in self.source_dir.iterdir()},
            analyzer.EXPECTED_SOURCE_FILES,
        )

    def test_verify_explicitly_disables_hmac_and_authenticity_claim(self) -> None:
        _, _, verify = self.run_canonical()
        self.assertIs(verify["hmac_enabled"], False)
        self.assertIs(verify["authenticity_claimed"], False)

    def test_result_mode_is_advisory_only(self) -> None:
        result, graph, _ = self.run_canonical()
        self.assertEqual(
            result["mode"],
            "advisory_only_deterministic_hash_chain_analyzer",
        )
        self.assertEqual(
            graph["mode"],
            "advisory_only_deterministic_hash_chain_graph",
        )

    def test_graph_uses_dedicated_patch_13_schema(self) -> None:
        _, graph, _ = self.run_canonical()
        self.assertEqual(graph["schema_version"], analyzer.GRAPH_SCHEMA_VERSION)
        self.assertNotEqual(
            graph["schema_version"],
            "tasukeru-arl-graph-v0.1",
        )

    def test_reason_nodes_do_not_collapse_issue_nodes(self) -> None:
        _, graph, _ = self.run_canonical()
        reason_nodes = [node for node in graph["nodes"] if node["type"] == "ReasonCode"]
        issue_nodes = [
            node for node in graph["nodes"] if node["type"] == "IntegrityIssue"
        ]
        self.assertEqual(
            len(reason_nodes),
            len(
                {
                    reason
                    for contract in analyzer.CANONICAL_CASE_CONTRACTS
                    for reason in contract["reason_codes"]
                }
            ),
        )
        self.assertEqual(len(issue_nodes), 19)

    def test_issue_nodes_preserve_stored_and_recomputed_values(self) -> None:
        result, graph, _ = self.run_canonical()
        case_by_id = {case["case_id"]: case for case in result["cases"]}
        for node in graph["nodes"]:
            if node["type"] != "IntegrityIssue":
                continue
            case_id = node["label"].split(" issue ", 1)[0]
            ordinal = node["properties"]["issue_ordinal"]
            issue = case_by_id[case_id]["issues"][ordinal - 1]
            self.assertEqual(
                node["properties"]["stored_value"],
                issue["stored_value"],
            )
            self.assertEqual(
                node["properties"]["recomputed_value"],
                issue["recomputed_value"],
            )

    def test_semantic_failure_does_not_normalize_to_verified_true(self) -> None:
        self.mutate_result(
            lambda result: result["counts"].__setitem__("failed_cases", 1)
        )
        verify = self.assert_semantic_failure()
        result = load_json(self.output_dir / analyzer.RESULT_FILENAME)
        self.assertFalse(result["verified"])
        self.assertFalse(verify["verified"])

    def test_output_directory_is_not_created_on_schema_failure(self) -> None:
        self.mutate_verify(
            lambda verify: verify.__setitem__("schema_version", "unsupported")
        )
        self.assert_operational_failure("ARL_ANALYZER_VERIFY_SCHEMA_UNSUPPORTED")
        self.assertFalse(self.output_dir.exists())

    def test_stderr_operational_error_is_path_free(self) -> None:
        missing = self.root / "physical" / "private" / "missing"
        exit_code, _, stderr = self.run_cli(input_dir=missing)
        self.assertEqual(exit_code, 2)
        self.assertNotIn(str(missing), stderr)
        self.assertIn("ARL_ANALYZER_INPUT_DIRECTORY_INVALID", stderr)

    def test_source_verify_schema_versions_are_recorded(self) -> None:
        _, _, verify = self.run_canonical()
        self.assertEqual(
            verify["source_schema_versions"],
            {
                "result": analyzer.SOURCE_RESULT_SCHEMA_VERSION,
                "verify": analyzer.SOURCE_VERIFY_SCHEMA_VERSION,
            },
        )

    def test_source_document_paths_and_hashes_have_fixed_names(self) -> None:
        result, _, _ = self.run_canonical()
        self.assertEqual(
            set(result["source_documents"]),
            analyzer.EXPECTED_SOURCE_FILES,
        )
        for filename, document in result["source_documents"].items():
            self.assertEqual(
                document["logical_path"],
                f"{analyzer.LOGICAL_SOURCE_ROOT}/{filename}",
            )
            self.assertRegex(document["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
