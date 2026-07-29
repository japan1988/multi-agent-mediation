from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tasukeru_arl_hash_chain_stress as hash_chain_stress  # noqa: E402


FIXTURES_DIR = PROJECT_ROOT / "tests" / "stress" / "fixtures" / "arl_hash_chain"
EXPECTED_OUTPUT_FILES = {
    hash_chain_stress.RESULT_FILENAME,
    hash_chain_stress.REPORT_FILENAME,
    hash_chain_stress.VERIFY_FILENAME,
}
CANONICAL_HEAD_HASH = (
    "4d7a836b8a1683f3dcc29c8f7d554503e8e5612aa0d13dec1ce702035d46cd4c"
)
EXPECTED_CASE_IDS = (
    "valid_chain",
    "middle_row_content_tampered",
    "middle_row_chain_hash_tampered",
    "middle_row_prev_hash_tampered",
    "final_row_content_tampered",
    "rows_reordered",
    "row_deleted",
)
EXPECTED_PHASE_2_FIXTURE_HASHES = {
    "final_row_content_tampered.jsonl": (
        "f2f8c09a0a0738167a23b3b3c8b3e018ecf4084ad10b666b2a89f9bc1cf6d5b0"
    ),
    "rows_reordered.jsonl": (
        "f3c48fb80c491a2522b3e62d95e20a777bb195982fe857816574392c302f259f"
    ),
    "row_deleted.jsonl": (
        "4e30d08c4e555527c97f27cc13487d9b842e6a56c450b0553db38db1d90afe5d"
    ),
}
EXPECTED_MANIFEST_HASH = (
    "35fc86d602cb8e7943c673499b4ed51b51a12516c2fb653d59d154485de53983"
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def case_by_id(
    manifest: dict[str, object],
    case_id: str,
) -> dict[str, object]:
    cases = manifest["cases"]
    assert isinstance(cases, list)
    return next(case for case in cases if case["case_id"] == case_id)


class TasukeruArlHashChainStressTests(unittest.TestCase):
    def test_canonical_json_serialization_excludes_only_hash_outputs(self) -> None:
        row = read_jsonl(FIXTURES_DIR / "valid_chain.jsonl")[0]
        canonical = hash_chain_stress.canonical_json(row)
        decoded = json.loads(canonical)

        self.assertNotIn("row_hash", decoded)
        self.assertNotIn("chain_hash", decoded)
        self.assertEqual(decoded["prev_hash"], "GENESIS")
        self.assertEqual(
            canonical,
            json.dumps(
                decoded,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def test_row_hash_recomputation_matches_valid_fixture(self) -> None:
        for row in read_jsonl(FIXTURES_DIR / "valid_chain.jsonl"):
            self.assertEqual(
                hash_chain_stress.compute_row_hash(row),
                row["row_hash"],
            )

    def test_chain_hash_recomputation_matches_valid_fixture(self) -> None:
        for row in read_jsonl(FIXTURES_DIR / "valid_chain.jsonl"):
            self.assertEqual(
                hash_chain_stress.compute_chain_hash(
                    str(row["prev_hash"]),
                    str(row["row_hash"]),
                ),
                row["chain_hash"],
            )

    def test_valid_chain_passes(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        valid_case = next(
            case for case in result["cases"] if case["case_id"] == "valid_chain"
        )

        self.assertTrue(valid_case["passed"])
        self.assertEqual(valid_case["actual_outcome"], "CHAIN_VALID")
        self.assertEqual(valid_case["reason_codes"], ["ARL_CHAIN_VALID"])
        self.assertEqual(valid_case["parsed_row_count"], 4)

    def test_middle_row_content_tamper_is_detected(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case
            for case in result["cases"]
            if case["case_id"] == "middle_row_content_tampered"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(case["actual_outcome"], "TAMPER_DETECTED")
        self.assertEqual(
            case["reason_codes"],
            [
                "ARL_ROW_HASH_MISMATCH",
                "ARL_CHAIN_HASH_MISMATCH",
                "ARL_PREV_HASH_MISMATCH",
            ],
        )
        self.assertEqual(case["first_error_line"], 2)

    def test_middle_row_chain_hash_tamper_has_no_false_prev_mismatch(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case
            for case in result["cases"]
            if case["case_id"] == "middle_row_chain_hash_tampered"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(case["reason_codes"], ["ARL_CHAIN_HASH_MISMATCH"])
        self.assertNotIn("ARL_PREV_HASH_MISMATCH", case["reason_codes"])
        self.assertEqual(case["first_error_line"], 2)

    def test_middle_row_prev_hash_tamper_is_detected(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case
            for case in result["cases"]
            if case["case_id"] == "middle_row_prev_hash_tampered"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(
            case["reason_codes"],
            [
                "ARL_PREV_HASH_MISMATCH",
                "ARL_ROW_HASH_MISMATCH",
                "ARL_CHAIN_HASH_MISMATCH",
            ],
        )
        self.assertEqual(case["first_error_line"], 2)

    def test_manifest_contains_canonical_seven_case_contract(self) -> None:
        manifest = hash_chain_stress.load_manifest(FIXTURES_DIR)
        cases = manifest["cases"]

        self.assertEqual(
            tuple(case["case_id"] for case in cases),
            EXPECTED_CASE_IDS,
        )
        self.assertEqual(hash_chain_stress.PATCH_13_CASE_IDS, EXPECTED_CASE_IDS)
        expected_phase_2 = (
            (
                "final_row_content_tampered",
                "final_row_content_tampered.jsonl",
                "ARL_ROW_HASH_MISMATCH",
                ["ARL_CHAIN_HASH_MISMATCH", "ARL_HEAD_HASH_MISMATCH"],
                4,
            ),
            (
                "rows_reordered",
                "rows_reordered.jsonl",
                "ARL_SEQUENCE_MISMATCH",
                ["ARL_PREV_HASH_MISMATCH"],
                4,
            ),
            (
                "row_deleted",
                "row_deleted.jsonl",
                "ARL_SEQUENCE_MISMATCH",
                ["ARL_PREV_HASH_MISMATCH"],
                3,
            ),
        )
        for case, expected in zip(cases[4:], expected_phase_2, strict=True):
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(
                    (
                        case["case_id"],
                        case["fixture_name"],
                        case["expected_primary_reason_code"],
                        case["expected_additional_reason_codes"],
                        case["expected_row_count"],
                    ),
                    expected,
                )
                self.assertEqual(case["expected_outcome"], "TAMPER_DETECTED")

    def test_final_row_content_tamper_is_detected(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case
            for case in result["cases"]
            if case["case_id"] == "final_row_content_tampered"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(case["actual_outcome"], "TAMPER_DETECTED")
        self.assertEqual(
            case["reason_codes"],
            [
                "ARL_ROW_HASH_MISMATCH",
                "ARL_CHAIN_HASH_MISMATCH",
                "ARL_HEAD_HASH_MISMATCH",
            ],
        )
        self.assertNotIn("ARL_PREV_HASH_MISMATCH", case["reason_codes"])
        self.assertEqual(case["first_error_line"], 4)
        self.assertEqual(case["parsed_row_count"], 4)
        self.assertEqual(case["expected_row_count"], 4)
        self.assertEqual(case["stored_head_hash"], CANONICAL_HEAD_HASH)
        self.assertNotEqual(case["recomputed_head_hash"], CANONICAL_HEAD_HASH)
        self.assertEqual(case["integrity_error_count"], 3)

    def test_rows_reordered_are_detected(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case for case in result["cases"] if case["case_id"] == "rows_reordered"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(case["actual_outcome"], "TAMPER_DETECTED")
        self.assertEqual(
            case["reason_codes"],
            ["ARL_SEQUENCE_MISMATCH", "ARL_PREV_HASH_MISMATCH"],
        )
        self.assertEqual(case["first_error_line"], 2)
        self.assertEqual(case["parsed_row_count"], 4)
        self.assertEqual(case["expected_row_count"], 4)
        self.assertEqual(case["stored_head_hash"], CANONICAL_HEAD_HASH)
        self.assertEqual(case["recomputed_head_hash"], CANONICAL_HEAD_HASH)
        self.assertEqual(case["integrity_error_count"], 5)

    def test_deleted_middle_row_is_detected_without_head_mismatch(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        case = next(
            case for case in result["cases"] if case["case_id"] == "row_deleted"
        )

        self.assertTrue(case["passed"])
        self.assertEqual(case["actual_outcome"], "TAMPER_DETECTED")
        self.assertEqual(
            case["reason_codes"],
            ["ARL_SEQUENCE_MISMATCH", "ARL_PREV_HASH_MISMATCH"],
        )
        self.assertNotIn("ARL_HEAD_HASH_MISMATCH", case["reason_codes"])
        self.assertEqual(case["first_error_line"], 2)
        self.assertEqual(case["parsed_row_count"], 3)
        self.assertEqual(case["expected_row_count"], 3)
        self.assertEqual(case["stored_head_hash"], CANONICAL_HEAD_HASH)
        self.assertEqual(case["recomputed_head_hash"], CANONICAL_HEAD_HASH)
        self.assertEqual(case["integrity_error_count"], 3)

    def test_undetected_expected_tamper_is_blocked(self) -> None:
        manifest = hash_chain_stress.load_manifest(FIXTURES_DIR)
        case_contract = dict(
            case_by_id(manifest, "middle_row_content_tampered")
        )
        case_contract["fixture_name"] = "valid_chain.jsonl"

        case = hash_chain_stress.verify_case(FIXTURES_DIR, case_contract)

        self.assertEqual(case["actual_outcome"], "BLOCKED")
        self.assertEqual(
            case["reason_codes"],
            ["ARL_CHAIN_VALID", "ARL_EXPECTED_DETECTION_MISSING"],
        )
        self.assertFalse(case["passed"])

    def test_failed_canonical_validation_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[1]["decision"] = "TAMPERED"
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertEqual(case["actual_outcome"], "BLOCKED")
        self.assertIn("ARL_ROW_HASH_MISMATCH", case["reason_codes"])
        self.assertIn("ARL_EXPECTED_VALIDATION_FAILED", case["reason_codes"])
        self.assertFalse(case["passed"])

    def test_genesis_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[0]["prev_hash"] = "0" * 64
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertIn("ARL_GENESIS_MISMATCH", case["reason_codes"])

    def test_previous_link_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[2]["prev_hash"] = "0" * 64
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertIn("ARL_PREV_HASH_MISMATCH", case["reason_codes"])

    def test_sequence_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[2]["seq"] = 4
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertEqual(case["reason_codes"][0], "ARL_SEQUENCE_MISMATCH")

    def test_run_id_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[2]["run_id"] = "different-run"
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertEqual(case["reason_codes"][0], "ARL_RUN_ID_MISMATCH")

    def test_hash_format_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            rows = read_jsonl(copied_dir / "valid_chain.jsonl")
            rows[1]["row_hash"] = "not-a-hash"
            write_jsonl(copied_dir / "valid_chain.jsonl", rows)
            manifest = hash_chain_stress.load_manifest(copied_dir)

            case = hash_chain_stress.verify_case(
                copied_dir,
                case_by_id(manifest, "valid_chain"),
            )

        self.assertEqual(case["reason_codes"][0], "ARL_HASH_FORMAT_INVALID")

    def test_manifest_allow_list_accepts_only_expected_ordered_reasons(self) -> None:
        self.assertTrue(
            hash_chain_stress.validate_reason_code_sequence(
                [
                    "ARL_ROW_HASH_MISMATCH",
                    "ARL_CHAIN_HASH_MISMATCH",
                    "ARL_PREV_HASH_MISMATCH",
                ],
                "ARL_ROW_HASH_MISMATCH",
                ["ARL_CHAIN_HASH_MISMATCH", "ARL_PREV_HASH_MISMATCH"],
            )
        )
        self.assertFalse(
            hash_chain_stress.validate_reason_code_sequence(
                ["ARL_CHAIN_HASH_MISMATCH", "ARL_ROW_HASH_MISMATCH"],
                "ARL_ROW_HASH_MISMATCH",
                ["ARL_CHAIN_HASH_MISMATCH"],
            )
        )
        self.assertFalse(
            hash_chain_stress.validate_reason_code_sequence(
                ["ARL_ROW_HASH_MISMATCH", "ARL_HEAD_HASH_MISMATCH"],
                "ARL_ROW_HASH_MISMATCH",
                ["ARL_CHAIN_HASH_MISMATCH"],
            )
        )

    def test_phase_two_allow_lists_reject_unauthorized_reasons(self) -> None:
        self.assertFalse(
            hash_chain_stress.validate_reason_code_sequence(
                [
                    "ARL_ROW_HASH_MISMATCH",
                    "ARL_CHAIN_HASH_MISMATCH",
                    "ARL_HEAD_HASH_MISMATCH",
                    "ARL_PREV_HASH_MISMATCH",
                ],
                "ARL_ROW_HASH_MISMATCH",
                ["ARL_CHAIN_HASH_MISMATCH", "ARL_HEAD_HASH_MISMATCH"],
            )
        )
        self.assertFalse(
            hash_chain_stress.validate_reason_code_sequence(
                [
                    "ARL_SEQUENCE_MISMATCH",
                    "ARL_PREV_HASH_MISMATCH",
                    "ARL_HEAD_HASH_MISMATCH",
                ],
                "ARL_SEQUENCE_MISMATCH",
                ["ARL_PREV_HASH_MISMATCH"],
            )
        )

    def test_manifest_duplicate_allow_list_reason_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            manifest_path = copied_dir / hash_chain_stress.MANIFEST_FILENAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["cases"][1]["expected_additional_reason_codes"] = [
                "ARL_CHAIN_HASH_MISMATCH",
                "ARL_CHAIN_HASH_MISMATCH",
            ]
            manifest_path.write_text(
                hash_chain_stress.json_dump(manifest),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(hash_chain_stress.ManifestError):
                hash_chain_stress.load_manifest(copied_dir)

    def test_manifest_rejects_swapped_t2_and_t3_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            copied_dir = Path(tmp_dir_name) / "fixtures"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            manifest_path = copied_dir / hash_chain_stress.MANIFEST_FILENAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            t2 = manifest["cases"][1]
            t3 = manifest["cases"][2]
            semantic_fields = [
                field
                for field in hash_chain_stress.REQUIRED_CASE_FIELDS
                if field != "case_id"
            ]
            t2_values = {field: t2[field] for field in semantic_fields}
            t3_values = {field: t3[field] for field in semantic_fields}
            t2.update(t3_values)
            t3.update(t2_values)
            manifest_path.write_text(
                hash_chain_stress.json_dump(manifest),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(hash_chain_stress.ManifestError):
                hash_chain_stress.load_manifest(copied_dir)

    def test_manifest_rejects_altered_or_reordered_phase_two_contracts(self) -> None:
        for mutation in ("altered", "reordered"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as name:
                copied_dir = Path(name) / "fixtures"
                shutil.copytree(FIXTURES_DIR, copied_dir)
                manifest_path = copied_dir / hash_chain_stress.MANIFEST_FILENAME
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if mutation == "altered":
                    manifest["cases"][4]["target"] = "row:3"
                else:
                    manifest["cases"][4], manifest["cases"][6] = (
                        manifest["cases"][6],
                        manifest["cases"][4],
                    )
                manifest_path.write_text(
                    hash_chain_stress.json_dump(manifest),
                    encoding="utf-8",
                    newline="\n",
                )

                with self.assertRaises(hash_chain_stress.ManifestError):
                    hash_chain_stress.load_manifest(copied_dir)

    def test_manifest_read_error_does_not_leak_physical_path(self) -> None:
        physical_path = r"C:\private\fixture_manifest.json"
        with mock.patch.object(
            Path,
            "read_bytes",
            side_effect=OSError(f"Access denied: {physical_path}"),
        ):
            result = hash_chain_stress.run_stress(FIXTURES_DIR)

        self.assertEqual(
            result["failure_detail"],
            "Fixture manifest cannot be read.",
        )
        self.assertNotIn(physical_path, json.dumps(result))

    def test_aggregate_counts_are_consistent(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)

        self.assertTrue(result["verified"])
        self.assertEqual(result["counts"]["total_cases"], 7)
        self.assertEqual(result["counts"]["passed_cases"], 7)
        self.assertEqual(result["counts"]["failed_cases"], 0)
        self.assertEqual(result["counts"]["valid_cases"], 1)
        self.assertEqual(result["counts"]["expected_tamper_cases"], 6)
        self.assertEqual(result["counts"]["tamper_cases_detected"], 6)
        self.assertEqual(result["counts"]["unexpected_valid_cases"], 0)
        self.assertEqual(result["counts"]["input_invalid_cases"], 0)
        self.assertEqual(result["counts"]["total_rows_read"], 27)
        self.assertTrue(
            hash_chain_stress.counts_consistent(
                result["cases"],
                result["counts"],
            )
        )

    def test_each_aggregate_count_is_required_for_consistency(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        required_count_names = (
            "total_cases",
            "passed_cases",
            "failed_cases",
            "valid_cases",
            "expected_tamper_cases",
            "tamper_cases_detected",
            "unexpected_valid_cases",
            "input_invalid_cases",
            "total_rows_read",
            "total_integrity_errors",
        )

        self.assertEqual(set(result["counts"]), set(required_count_names))
        self.assertTrue(
            hash_chain_stress.counts_consistent(
                result["cases"],
                result["counts"],
            )
        )
        for count_name in required_count_names:
            with self.subTest(count_name=count_name):
                inconsistent_counts = dict(result["counts"])
                inconsistent_counts[count_name] += 1
                self.assertFalse(
                    hash_chain_stress.counts_consistent(
                        result["cases"],
                        inconsistent_counts,
                    )
                )

    def test_writer_creates_exactly_three_verified_artifacts(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            output_dir = Path(tmp_dir_name)
            artifacts = hash_chain_stress.write_artifacts(result, output_dir)
            verify = json.loads(
                (output_dir / hash_chain_stress.VERIFY_FILENAME).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                EXPECTED_OUTPUT_FILES,
            )
            self.assertTrue(artifacts["verify"]["verified"])
            self.assertTrue(verify["verified"])
            self.assertFalse(verify["hmac_enabled"])
            self.assertFalse(verify["authenticity_claimed"])
            self.assertEqual(
                verify["result_sha256"],
                file_hash(output_dir / hash_chain_stress.RESULT_FILENAME),
            )
            self.assertEqual(
                verify["report_sha256"],
                file_hash(output_dir / hash_chain_stress.REPORT_FILENAME),
            )
            self.assertEqual(
                verify["manifest_sha256"],
                file_hash(FIXTURES_DIR / hash_chain_stress.MANIFEST_FILENAME),
            )

    def test_artifacts_are_byte_deterministic_across_output_directories(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        with (
            tempfile.TemporaryDirectory() as first_name,
            tempfile.TemporaryDirectory() as second_name,
        ):
            first_dir = Path(first_name)
            second_dir = Path(second_name)
            hash_chain_stress.write_artifacts(result, first_dir)
            hash_chain_stress.write_artifacts(result, second_dir)

            for filename in EXPECTED_OUTPUT_FILES:
                self.assertEqual(
                    (first_dir / filename).read_bytes(),
                    (second_dir / filename).read_bytes(),
                )

    def test_outputs_do_not_contain_absolute_fixture_path(self) -> None:
        result = hash_chain_stress.run_stress(FIXTURES_DIR.resolve())
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            output_dir = Path(tmp_dir_name)
            hash_chain_stress.write_artifacts(result, output_dir)
            combined = b"".join(
                (output_dir / filename).read_bytes()
                for filename in sorted(EXPECTED_OUTPUT_FILES)
            )

        self.assertNotIn(str(FIXTURES_DIR.resolve()).encode("utf-8"), combined)
        self.assertEqual(result["fixture_directory"], "arl_hash_chain")

    def test_fixture_bytes_are_not_modified(self) -> None:
        fixture_paths = sorted(FIXTURES_DIR.rglob("*"))
        fixture_files = [path for path in fixture_paths if path.is_file()]
        before = {path.relative_to(FIXTURES_DIR): file_hash(path) for path in fixture_files}

        result = hash_chain_stress.run_stress(FIXTURES_DIR)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            hash_chain_stress.write_artifacts(result, Path(tmp_dir_name))

        after = {path.relative_to(FIXTURES_DIR): file_hash(path) for path in fixture_files}
        self.assertEqual(before, after)

    def test_phase_two_fixture_and_manifest_hashes_are_fixed(self) -> None:
        for filename, expected_hash in EXPECTED_PHASE_2_FIXTURE_HASHES.items():
            with self.subTest(filename=filename):
                self.assertEqual(file_hash(FIXTURES_DIR / filename), expected_hash)
        self.assertEqual(
            file_hash(FIXTURES_DIR / hash_chain_stress.MANIFEST_FILENAME),
            EXPECTED_MANIFEST_HASH,
        )

    def test_cli_exits_zero_for_expected_tamper_detections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            output_dir = Path(tmp_dir_name)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(hash_chain_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(FIXTURES_DIR),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("verified: True", completed.stdout)
            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                EXPECTED_OUTPUT_FILES,
            )

    def test_cli_exits_one_when_manifest_expectation_is_not_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_root = Path(tmp_dir_name)
            copied_dir = temp_root / "fixtures"
            output_dir = temp_root / "outputs"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            shutil.copyfile(
                copied_dir / "valid_chain.jsonl",
                copied_dir / "middle_row_content_tampered.jsonl",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(hash_chain_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(copied_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 1, completed.stderr)
            result = json.loads(
                (output_dir / hash_chain_stress.RESULT_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            verify = json.loads(
                (output_dir / hash_chain_stress.VERIFY_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            case = next(
                case
                for case in result["cases"]
                if case["case_id"] == "middle_row_content_tampered"
            )
            self.assertEqual(case["actual_outcome"], "BLOCKED")
            self.assertIn(
                "ARL_EXPECTED_DETECTION_MISSING",
                case["reason_codes"],
            )
            self.assertFalse(case["passed"])
            self.assertFalse(verify["verified"])

    def test_cli_exits_one_for_unmet_phase_two_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_root = Path(tmp_dir_name)
            copied_dir = temp_root / "fixtures"
            output_dir = temp_root / "outputs"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            shutil.copyfile(
                copied_dir / "valid_chain.jsonl",
                copied_dir / "final_row_content_tampered.jsonl",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(hash_chain_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(copied_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 1, completed.stderr)
            result = json.loads(
                (output_dir / hash_chain_stress.RESULT_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            case = next(
                case
                for case in result["cases"]
                if case["case_id"] == "final_row_content_tampered"
            )
            self.assertEqual(case["actual_outcome"], "BLOCKED")
            self.assertIn(
                "ARL_EXPECTED_DETECTION_MISSING",
                case["reason_codes"],
            )
            self.assertFalse(case["passed"])

    def test_cli_missing_manifest_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_root = Path(tmp_dir_name)
            copied_dir = temp_root / "fixtures"
            output_dir = temp_root / "outputs"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            (copied_dir / hash_chain_stress.MANIFEST_FILENAME).unlink()

            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(hash_chain_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(copied_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            result = json.loads(
                (output_dir / hash_chain_stress.RESULT_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                result["overall_reason_codes"],
                ["ARL_MANIFEST_INVALID"],
            )

    def test_cli_invalid_phase_one_manifest_contract_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_root = Path(tmp_dir_name)
            copied_dir = temp_root / "fixtures"
            output_dir = temp_root / "outputs"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            manifest_path = copied_dir / hash_chain_stress.MANIFEST_FILENAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["cases"][1]["fixture_name"] = "valid_chain.jsonl"
            manifest_path.write_text(
                hash_chain_stress.json_dump(manifest),
                encoding="utf-8",
                newline="\n",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(hash_chain_stress.__file__).resolve()),
                    "--fixtures-dir",
                    str(copied_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            result = json.loads(
                (output_dir / hash_chain_stress.RESULT_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                result["overall_reason_codes"],
                ["ARL_MANIFEST_INVALID"],
            )

    def test_cli_invalid_usage_exits_two(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(hash_chain_stress.__file__).resolve()),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)

    def test_safety_boundary_is_explicit_and_advisory_only(self) -> None:
        boundary = hash_chain_stress.SAFETY_BOUNDARY

        self.assertTrue(boundary["advisory_only"])
        self.assertTrue(boundary["human_review_required"])
        for key, value in boundary.items():
            if key not in {"advisory_only", "human_review_required"}:
                self.assertFalse(value, key)
        self.assertTrue(hash_chain_stress.safety_boundary_verified(boundary))

    def test_fixture_copy_produces_identical_result_and_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_root = Path(tmp_dir_name)
            copied_dir = temp_root / "different" / "fixture-location"
            shutil.copytree(FIXTURES_DIR, copied_dir)
            original_result = hash_chain_stress.run_stress(FIXTURES_DIR)
            copied_result = hash_chain_stress.run_stress(copied_dir)
            original_out = temp_root / "original-output"
            copied_out = temp_root / "copied-output"
            hash_chain_stress.write_artifacts(original_result, original_out)
            hash_chain_stress.write_artifacts(copied_result, copied_out)

            self.assertEqual(original_result, copied_result)
            for filename in EXPECTED_OUTPUT_FILES:
                self.assertEqual(
                    (original_out / filename).read_bytes(),
                    (copied_out / filename).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
