from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tasukeru_arl_analyzer as analyzer  # noqa: E402


FIXTURES_DIR = PROJECT_ROOT / "tests" / "stress" / "fixtures" / "arl_analyzer"
STRESS_DIR = FIXTURES_DIR / "stress_results" / "arl"
EXPECTED_OUTPUT_FILES = {
    analyzer.RESULT_FILENAME,
    analyzer.GRAPH_FILENAME,
    analyzer.REPORT_FILENAME,
    analyzer.VERIFY_FILENAME,
}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TasukeruArlAnalyzerTests(unittest.TestCase):
    def test_runtime_arl_row_count_uses_arl_and_verify_as_authority(self) -> None:
        analysis = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        runtime = analysis["result"]["runtime_arl"]

        self.assertEqual(runtime["parsed_row_count"], 4)
        self.assertEqual(runtime["verify_row_count"], 4)
        self.assertTrue(runtime["row_count_matches_verify"])
        self.assertEqual(
            runtime["row_count_authority"],
            "tasukeru_arl.jsonl + tasukeru_arl_verify.json",
        )
        self.assertFalse(runtime["clean_run_arl_rows_authoritative"])

    def test_hmac_false_remains_explicit_and_not_described_as_protected(self) -> None:
        analysis = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        runtime = analysis["result"]["runtime_arl"]
        report = analyzer.build_report(analysis["result"], analysis["graph"])

        self.assertIs(runtime["hmac_enabled"], False)
        self.assertFalse(runtime["hmac_protection_claimed"])
        self.assertIn("HMAC enabled: `false`", report)
        self.assertIn("HMAC protection claimed: `false`", report)
        self.assertIn("does not describe the ARL as HMAC-protected", report)

    def test_expected_negative_stress_cases_are_labeled_as_expected_detections(self) -> None:
        analysis = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        cases = {
            case["case_id"]: case
            for case in analysis["result"]["stress_artifacts"]["cases"]
        }

        for case_id in ("missing_required_key_arl", "invalid_jsonl_arl"):
            self.assertTrue(cases[case_id]["expected_negative"])
            self.assertTrue(cases[case_id]["expected_detection"])
            self.assertTrue(cases[case_id]["passed"])

        self.assertTrue(
            analysis["result"]["stress_artifacts"]["expected_negative_cases_labeled"]
        )

    def test_graph_generation_is_deterministic_across_repeated_runs(self) -> None:
        first = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        second = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)

        self.assertEqual(first["graph"], second["graph"])
        self.assertEqual(first["result"]["graph_summary"], second["result"]["graph_summary"])

    def test_graph_identity_is_independent_of_local_fixture_path(self) -> None:
        original = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_root = Path(tmp_dir_name) / "different" / "fixture_root"
            shutil.copytree(FIXTURES_DIR, copied_root)
            copied_stress_dir = copied_root / "stress_results" / "arl"
            copied = analyzer.run_analysis(copied_root, copied_stress_dir)

        original_node_ids = [node["id"] for node in original["graph"]["nodes"]]
        copied_node_ids = [node["id"] for node in copied["graph"]["nodes"]]
        self.assertEqual(original_node_ids, copied_node_ids)
        self.assertEqual(original["graph"]["graph_hash"], copied["graph"]["graph_hash"])
        self.assertIn("stress_artifacts:patch_3_arl_stress_results", original_node_ids)

    def test_stable_node_ids_are_unchanged_for_identical_inputs(self) -> None:
        first = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        second = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)

        first_ids = [node["id"] for node in first["graph"]["nodes"]]
        second_ids = [node["id"] for node in second["graph"]["nodes"]]
        self.assertEqual(first_ids, second_ids)
        self.assertIn("runtime_arl_row:1:111111111111", first_ids)

    def test_missing_optional_advisory_files_are_handled_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            shutil.copy(FIXTURES_DIR / analyzer.RUNTIME_ARL_FILENAME, tmp_dir)
            shutil.copy(FIXTURES_DIR / analyzer.RUNTIME_ARL_VERIFY_FILENAME, tmp_dir)

            first = analyzer.run_analysis(tmp_dir, STRESS_DIR)
            second = analyzer.run_analysis(tmp_dir, STRESS_DIR)

        self.assertEqual(first, second)
        advisory_docs = first["result"]["advisory_artifacts"]["documents"]
        self.assertFalse(advisory_docs["hitl_review"]["exists"])
        self.assertFalse(advisory_docs["logic_review"]["exists"])

    def test_malformed_runtime_arl_jsonl_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            (tmp_dir / analyzer.RUNTIME_ARL_FILENAME).write_text(
                '{"run_id":"bad","layer":"meaning_gate"\n',
                encoding="utf-8",
            )
            (tmp_dir / analyzer.RUNTIME_ARL_VERIFY_FILENAME).write_text(
                json.dumps({"verified": True, "row_count": 1, "hmac_enabled": False}),
                encoding="utf-8",
            )
            analysis = analyzer.run_analysis(tmp_dir, STRESS_DIR)

        runtime = analysis["result"]["runtime_arl"]
        self.assertFalse(analysis["result"]["verified"])
        self.assertEqual(runtime["parsed_row_count"], 0)
        self.assertEqual(runtime["issues"][0]["issue_type"], "INVALID_RUNTIME_ARL_JSONL")

    def test_writer_creates_exactly_expected_artifacts(self) -> None:
        analysis = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            out_dir = Path(tmp_dir_name)
            artifacts = analyzer.write_artifacts(analysis, out_dir)

            self.assertEqual({path.name for path in out_dir.iterdir()}, EXPECTED_OUTPUT_FILES)
            self.assertTrue(artifacts["verify"]["verified"])

    def test_analyzer_does_not_modify_fixture_files(self) -> None:
        fixture_paths = sorted(path for path in FIXTURES_DIR.rglob("*") if path.is_file())
        before = {path.relative_to(FIXTURES_DIR).as_posix(): file_hash(path) for path in fixture_paths}

        analysis = analyzer.run_analysis(FIXTURES_DIR, STRESS_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            analyzer.write_artifacts(analysis, Path(tmp_dir_name))

        after = {path.relative_to(FIXTURES_DIR).as_posix(): file_hash(path) for path in fixture_paths}
        self.assertEqual(before, after)

    def test_cli_smoke_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(analyzer.__file__).resolve()),
                    "--input-dir",
                    str(FIXTURES_DIR),
                    "--stress-dir",
                    str(STRESS_DIR),
                    "--out-dir",
                    tmp_dir_name,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Tasukeru ARL Analyzer v0.1", completed.stdout)
            self.assertIn("verified: True", completed.stdout)
            self.assertEqual({path.name for path in Path(tmp_dir_name).iterdir()}, EXPECTED_OUTPUT_FILES)


if __name__ == "__main__":
    unittest.main()
