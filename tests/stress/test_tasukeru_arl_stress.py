from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tasukeru_arl_stress as arl_stress  # noqa: E402


FIXTURES_DIR = PROJECT_ROOT / "tests" / "stress" / "fixtures"
EXPECTED_OUTPUT_FILES = {
    arl_stress.RESULT_FILENAME,
    arl_stress.REPORT_FILENAME,
    arl_stress.VERIFY_FILENAME,
}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TasukeruArlStressTests(unittest.TestCase):
    def test_valid_fixture_verifies_true(self) -> None:
        result = arl_stress.run_stress(FIXTURES_DIR)
        valid_case = next(case for case in result["cases"] if case["expected_kind"] == "VALID")

        self.assertTrue(valid_case["input_verified"])
        self.assertTrue(valid_case["passed"])
        self.assertEqual(valid_case["valid_record_count"], 2)
        self.assertEqual(valid_case["invalid_jsonl_count"], 0)
        self.assertEqual(valid_case["missing_required_key_count"], 0)

    def test_empty_fixture_is_handled_safely_and_deterministically(self) -> None:
        first = arl_stress.run_stress(FIXTURES_DIR)
        second = arl_stress.run_stress(FIXTURES_DIR)
        empty_case = next(case for case in first["cases"] if case["expected_kind"] == "EMPTY")

        self.assertEqual(first, second)
        self.assertTrue(empty_case["passed"])
        self.assertTrue(empty_case["empty_input"])
        self.assertFalse(empty_case["input_verified"])
        self.assertEqual(empty_case["valid_record_count"], 0)
        self.assertEqual(empty_case["issues"], [])

    def test_missing_required_key_is_detected(self) -> None:
        result = arl_stress.run_stress(FIXTURES_DIR)
        missing_case = next(
            case for case in result["cases"] if case["expected_kind"] == "MISSING_REQUIRED_KEY"
        )

        self.assertTrue(missing_case["passed"])
        self.assertEqual(missing_case["missing_required_key_count"], 1)
        self.assertEqual(missing_case["issues"][0]["issue_type"], "MISSING_REQUIRED_KEY")
        self.assertEqual(missing_case["issues"][0]["missing_keys"], ["reason_code"])

    def test_invalid_jsonl_is_detected(self) -> None:
        result = arl_stress.run_stress(FIXTURES_DIR)
        invalid_case = next(
            case for case in result["cases"] if case["expected_kind"] == "INVALID_JSONL"
        )

        self.assertTrue(invalid_case["passed"])
        self.assertEqual(invalid_case["invalid_jsonl_count"], 1)
        self.assertEqual(invalid_case["issues"][0]["issue_type"], "INVALID_JSONL")

    def test_aggregate_counts_and_verify_status_are_consistent(self) -> None:
        result = arl_stress.run_stress(FIXTURES_DIR)

        self.assertTrue(result["verified"])
        self.assertTrue(all(result["expectation_checks"].values()))
        self.assertEqual(result["counts"]["total_cases"], 4)
        self.assertEqual(result["counts"]["passed_cases"], 4)
        self.assertEqual(result["counts"]["failed_cases"], 0)
        self.assertEqual(result["counts"]["total_valid_records"], 2)
        self.assertEqual(result["counts"]["missing_required_key_records"], 1)
        self.assertEqual(result["counts"]["invalid_jsonl_lines"], 1)

    def test_writer_creates_only_expected_artifacts(self) -> None:
        result = arl_stress.run_stress(FIXTURES_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            out_dir = Path(tmp_dir_name)
            artifact_result = arl_stress.write_artifacts(result, out_dir)

            self.assertEqual({path.name for path in out_dir.iterdir()}, EXPECTED_OUTPUT_FILES)
            self.assertTrue(artifact_result["verify"]["verified"])

            verify_payload = json.loads(
                (out_dir / arl_stress.VERIFY_FILENAME).read_text(encoding="utf-8")
            )
            self.assertTrue(verify_payload["verified"])
            self.assertEqual(
                verify_payload["output_existence_checks"],
                {"json": True, "markdown": True, "verify": True},
            )

    def test_stress_script_does_not_modify_fixture_files(self) -> None:
        fixture_paths = sorted(FIXTURES_DIR.glob("*.jsonl"))
        before = {path.name: file_hash(path) for path in fixture_paths}

        result = arl_stress.run_stress(FIXTURES_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            arl_stress.write_artifacts(result, Path(tmp_dir_name))

        after = {path.name: file_hash(path) for path in fixture_paths}
        self.assertEqual(before, after)

    def test_cli_writes_artifacts_and_exits_zero_for_expected_detections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(arl_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(FIXTURES_DIR),
                    "--out-dir",
                    tmp_dir_name,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Tasukeru ARL Stress Test v0.1", completed.stdout)
            self.assertIn("verified: True", completed.stdout)
            self.assertEqual({path.name for path in Path(tmp_dir_name).iterdir()}, EXPECTED_OUTPUT_FILES)


if __name__ == "__main__":
    unittest.main()
