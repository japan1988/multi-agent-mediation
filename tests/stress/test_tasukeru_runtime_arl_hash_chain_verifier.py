from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "tasukeru_runtime_arl_hash_chain_verifier.py"
FIXTURE_DIR = ROOT / "tests" / "stress" / "fixtures" / "arl_hash_chain_runtime"

SPEC = importlib.util.spec_from_file_location("runtime_arl_verifier", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load runtime ARL verifier module.")
VERIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFIER
SPEC.loader.exec_module(VERIFIER)


EXPECTED_OUTPUT_FILES = tuple(
    sorted(
        (
            "tasukeru_runtime_arl_hash_chain_result.json",
            "tasukeru_runtime_arl_hash_chain_source_binding.json",
            "tasukeru_runtime_arl_hash_chain_report.md",
            "tasukeru_runtime_arl_hash_chain_verify.json",
        )
    )
)
EXPECTED_HASHED_OUTPUT_FILES = tuple(
    sorted(
        (
            "tasukeru_runtime_arl_hash_chain_result.json",
            "tasukeru_runtime_arl_hash_chain_source_binding.json",
            "tasukeru_runtime_arl_hash_chain_report.md",
        )
    )
)
EXPECTED_WRITE_ORDER = (
    "tasukeru_runtime_arl_hash_chain_result.json",
    "tasukeru_runtime_arl_hash_chain_source_binding.json",
    "tasukeru_runtime_arl_hash_chain_report.md",
    "tasukeru_runtime_arl_hash_chain_verify.json",
)
EXPECTED_REASON_CODES = (
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
EXPECTED_HEAD_HASH = "0f6e77605533c980e1df111e08fac4ef05d05b4f295702eca05d71ebbe263176"
EXPECTED_FIXTURE_SHA256 = {
    "tasukeru_arl.jsonl": "4b8bb3fc4c944d5024f966399531d22c08387c3a8c2252d34eebb5395e424104",
    "tasukeru_arl_verify.json": "318c2e5d09665e57d98771c14ea3e04d520bfb0914db21ee31484d5ba7c74bc8",
}
EXPECTED_ROW_HASHES = (
    "c5e8aa6b41d72d80e89659b118b0dca84b5618b246fd43529bc9d21937de3c38",
    "75af14f2d596149b4e96a4958c39273bd2a63c1a8106cce1cd34e0db9a0d478a",
    "9ee6dbd479b4a3a0b7e201a30a430c8b574093fc9221d1a1cd11a133d12d171f",
)
EXPECTED_CHAIN_HASHES = (
    "bedead4edf41d9ddc91494e09b48d1fb6b381241367e210463c48e56e58e551f",
    "fe0fc4cd225e27000006c3fa63b86d4620a4c00af1ced949342801361ce301ae",
    EXPECTED_HEAD_HASH,
)
PROHIBITED_FIXTURE_MARKERS = ("fixture-secret-marker", "private/review.txt")
HARMLESS_FIXTURE_MARKERS = ("synthetic-marker", "synthetic-review-label")
RESULT_KEYS = (
    "schema_version",
    "tool",
    "verified",
    "decision",
    "summary",
    "issues",
    "safety_boundary",
)
SUMMARY_KEYS = (
    "rows_read",
    "run_id",
    "issue_count",
    "reason_codes",
    "stored_head_hash",
    "recomputed_head_hash",
    "source_verify_head_hash",
    "source_verify_verified",
    "hmac_present",
    "hmac_enabled",
    "authenticity_claimed",
    "human_review_required",
)
SOURCE_BINDING_KEYS = (
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
VERIFY_KEYS = (
    "schema_version",
    "tool",
    "verified",
    "expected_output_files",
    "actual_output_files",
    "output_sha256",
    "result_verified",
    "source_binding_consistent",
    "report_consistent",
    "safety_boundary_consistent",
    "errors",
)
ISSUE_KEYS = (
    "line_number",
    "reason_code",
    "detail",
    "stored_value",
    "recomputed_value",
)
EXPECTED_SAFETY_BOUNDARY = {
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_row_hash(row: dict[str, Any]) -> str:
    body = {
        key: value
        for key, value in row.items()
        if key not in {"row_hash", "chain_hash", "hmac_sha256"}
    }
    payload = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_chain_hash(prev_hash: str, row_hash: str) -> str:
    return hashlib.sha256(f"{prev_hash}:{row_hash}".encode("utf-8")).hexdigest()


class RuntimeArlVerifierTests(unittest.TestCase):
    maxDiff = None

    def copy_sources(self, root: Path) -> tuple[Path, Path]:
        source_dir = root / "source"
        source_dir.mkdir(parents=True)
        arl_path = source_dir / "tasukeru_arl.jsonl"
        source_verify_path = source_dir / "tasukeru_arl_verify.json"
        shutil.copy2(FIXTURE_DIR / arl_path.name, arl_path)
        shutil.copy2(FIXTURE_DIR / source_verify_path.name, source_verify_path)
        return arl_path, source_verify_path

    def load_rows(self, arl_path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in arl_path.read_text(encoding="utf-8").splitlines()
        ]

    def write_rows(self, arl_path: Path, rows: list[Any]) -> None:
        text = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        )
        arl_path.write_text(text, encoding="utf-8", newline="\n")

    def load_source_verify(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_source_verify(self, path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def rehash_rows(self, rows: list[dict[str, Any]]) -> None:
        previous = "GENESIS"
        for row in rows:
            row["prev_hash"] = previous
            row["row_hash"] = canonical_row_hash(row)
            row["chain_hash"] = canonical_chain_hash(previous, row["row_hash"])
            previous = row["chain_hash"]

    def rebind_source_verify(
        self,
        source_verify_path: Path,
        rows: list[dict[str, Any]],
    ) -> None:
        value = self.load_source_verify(source_verify_path)
        value["row_count"] = len(rows)
        value["head_hash"] = rows[-1]["chain_hash"] if rows else ""
        self.write_source_verify(source_verify_path, value)

    def run_cli(
        self,
        arl_path: Path,
        source_verify_path: Path,
        output_dir: Path,
        *,
        old_argument_names: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        arl_argument = "--arl-path" if old_argument_names else "--arl"
        verify_argument = (
            "--source-verify-path" if old_argument_names else "--source-verify"
        )
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT_PATH),
                arl_argument,
                str(arl_path),
                verify_argument,
                str(source_verify_path),
                "--out-dir",
                str(output_dir),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def load_outputs(self, output_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        result = json.loads(
            (output_dir / VERIFIER.RESULT_FILENAME).read_text(encoding="utf-8")
        )
        source_binding = json.loads(
            (output_dir / VERIFIER.SOURCE_BINDING_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        verify = json.loads(
            (output_dir / VERIFIER.VERIFY_FILENAME).read_text(encoding="utf-8")
        )
        return result, source_binding, verify

    def assert_verification_failure(
        self,
        mutate: Callable[[Path, Path], None],
        expected_reason: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            mutate(arl_path, source_verify_path)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                set(EXPECTED_OUTPUT_FILES),
            )
            result, source_binding, verify = self.load_outputs(output_dir)
            self.assertFalse(result["verified"])
            self.assertEqual(result["decision"], "INTEGRITY_CHECK_FAILED")
            self.assertIn(expected_reason, result["summary"]["reason_codes"])
            self.assertFalse(verify["verified"])
            self.assertIn(expected_reason, verify["errors"])
            return result, source_binding, verify

    def test_reason_code_inventory_is_exact(self) -> None:
        self.assertEqual(VERIFIER.REASON_CODES, EXPECTED_REASON_CODES)

    def test_fixture_hashes_are_fixed_literals(self) -> None:
        self.assertEqual(
            {
                name: sha256_file(FIXTURE_DIR / name)
                for name in EXPECTED_FIXTURE_SHA256
            },
            EXPECTED_FIXTURE_SHA256,
        )

    def test_fixture_markers_are_harmless_fixed_values(self) -> None:
        fixture_bytes = (FIXTURE_DIR / "tasukeru_arl.jsonl").read_bytes()
        for marker in PROHIBITED_FIXTURE_MARKERS:
            self.assertNotIn(marker.encode("utf-8"), fixture_bytes)
        for marker in HARMLESS_FIXTURE_MARKERS:
            self.assertIn(marker.encode("utf-8"), fixture_bytes)

    def test_valid_fixture_has_fixed_head_and_rows(self) -> None:
        rows = self.load_rows(FIXTURE_DIR / "tasukeru_arl.jsonl")
        source_verify = self.load_source_verify(
            FIXTURE_DIR / "tasukeru_arl_verify.json"
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(tuple(row["row_hash"] for row in rows), EXPECTED_ROW_HASHES)
        self.assertEqual(
            tuple(row["chain_hash"] for row in rows), EXPECTED_CHAIN_HASHES
        )
        self.assertEqual(
            tuple(canonical_row_hash(row) for row in rows), EXPECTED_ROW_HASHES
        )
        self.assertEqual(rows[-1]["chain_hash"], EXPECTED_HEAD_HASH)
        self.assertEqual(source_verify["head_hash"], EXPECTED_HEAD_HASH)

    def test_canonical_hash_excludes_all_three_contract_fields(self) -> None:
        row = self.load_rows(FIXTURE_DIR / "tasukeru_arl.jsonl")[0]
        expected = canonical_row_hash(row)
        row["hmac_sha256"] = "b" * 64
        self.assertEqual(VERIFIER.compute_row_hash(row), expected)
        self.assertEqual(
            VERIFIER.HASH_CONTRACT["row_body_excluded_fields"],
            ["row_hash", "chain_hash", "hmac_sha256"],
        )

    def test_valid_cli_writes_exact_four_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                set(EXPECTED_OUTPUT_FILES),
            )
            self.assertFalse((output_dir / "tasukeru_runtime_arl_hash_chain_graph.json").exists())

    def test_result_schema_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            result, _, _ = self.load_outputs(output_dir)
            self.assertEqual(tuple(result), RESULT_KEYS)
            self.assertEqual(tuple(result["summary"]), SUMMARY_KEYS)
            self.assertEqual(result["tool"], VERIFIER.TOOL_NAME)
            self.assertEqual(result["decision"], "VERIFIED")
            self.assertEqual(result["summary"]["run_id"], "fixture-runtime-run")

    def test_source_binding_schema_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            _, binding, _ = self.load_outputs(output_dir)
            self.assertEqual(tuple(binding), SOURCE_BINDING_KEYS)
            self.assertEqual(binding["source_arl_filename"], arl_path.name)
            self.assertEqual(binding["source_verify_filename"], source_verify_path.name)
            self.assertEqual(binding["source_arl_sha256"], sha256_file(arl_path))
            self.assertEqual(binding["source_verify_sha256"], sha256_file(source_verify_path))
            self.assertEqual(binding["run_id"], "fixture-runtime-run")
            self.assertFalse(binding["hmac_present"])
            self.assertFalse(binding["hmac_enabled"])
            self.assertFalse(binding["authenticity_claimed"])

    def test_verify_schema_and_hash_inventory_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            _, _, verify = self.load_outputs(output_dir)
            self.assertEqual(tuple(verify), VERIFY_KEYS)
            self.assertEqual(tuple(verify["output_sha256"]), EXPECTED_HASHED_OUTPUT_FILES)
            self.assertNotIn(VERIFIER.VERIFY_FILENAME, verify["output_sha256"])
            for filename, digest in verify["output_sha256"].items():
                self.assertEqual(digest, sha256_file(output_dir / filename))

    def test_expected_and_actual_output_files_match_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            _, _, verify = self.load_outputs(output_dir)
            self.assertEqual(verify["expected_output_files"], list(EXPECTED_OUTPUT_FILES))
            self.assertEqual(verify["actual_output_files"], list(EXPECTED_OUTPUT_FILES))
            self.assertTrue(verify["source_binding_consistent"])
            self.assertTrue(verify["report_consistent"])
            self.assertTrue(verify["safety_boundary_consistent"])

    def test_report_sections_are_exact_and_run_id_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(
                self.run_cli(arl_path, source_verify_path, output_dir).returncode,
                0,
            )
            report = (output_dir / VERIFIER.REPORT_FILENAME).read_text(
                encoding="utf-8"
            )
            headings = [line for line in report.splitlines() if line.startswith("#")]
            self.assertEqual(
                headings,
                [
                    "# Tasukeru Runtime ARL Hash-Chain Verification Report",
                    "## Verification Result",
                    "## Summary",
                    "## Source Binding",
                    "## Reason Codes",
                    "## Safety Boundary",
                    "## Human Review",
                ],
            )
            self.assertNotIn("Run ID", report)
            self.assertNotIn("fixture-runtime-run", report)

    def test_outputs_have_no_timestamp_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            combined = "\n".join(
                path.read_text(encoding="utf-8") for path in output_dir.iterdir()
            )
            self.assertNotIn("generated_at_utc", combined)
            self.assertNotIn("1970-01-01T00:00:00Z", combined)

    def test_safety_boundary_is_exact(self) -> None:
        self.assertEqual(VERIFIER.SAFETY_BOUNDARY, EXPECTED_SAFETY_BOUNDARY)
        self.assertFalse(VERIFIER.SAFETY_BOUNDARY["automatic_retry"])
        self.assertTrue(VERIFIER.SAFETY_BOUNDARY["human_review_required"])

    def test_source_files_are_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            before = (sha256_file(arl_path), sha256_file(source_verify_path))
            self.assertEqual(self.run_cli(arl_path, source_verify_path, root / "output").returncode, 0)
            self.assertEqual((sha256_file(arl_path), sha256_file(source_verify_path)), before)

    def test_outputs_are_byte_deterministic_across_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generated = []
            for name in ("root-a", "differently-named-root-b"):
                arl_path, source_verify_path = self.copy_sources(root / name)
                output_dir = root / name / "output"
                self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
                generated.append(
                    {path.name: path.read_bytes() for path in output_dir.iterdir()}
                )
            self.assertEqual(generated[0], generated[1])

    def test_outputs_exclude_absolute_paths_and_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            self.assertEqual(self.run_cli(arl_path, source_verify_path, output_dir).returncode, 0)
            combined = "\n".join(
                path.read_text(encoding="utf-8") for path in output_dir.iterdir()
            )
            self.assertNotIn(str(root), combined)
            for marker in (*PROHIBITED_FIXTURE_MARKERS, *HARMLESS_FIXTURE_MARKERS):
                self.assertNotIn(marker, combined)
            self.assertNotIn('"evidence"', combined)
            self.assertNotIn("graph", combined.lower())

    def test_old_cli_argument_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            completed = self.run_cli(
                arl_path,
                source_verify_path,
                root / "output",
                old_argument_names=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse((root / "output").exists())

    def test_invalid_cli_usage_returns_two(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT_PATH)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)

    def test_missing_runtime_arl_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = self.run_cli(
                root / "missing.jsonl",
                FIXTURE_DIR / "tasukeru_arl_verify.json",
                root / "output",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("RUNTIME_ARL_NOT_FOUND", completed.stderr)
            self.assertFalse((root / "output").exists())

    def test_missing_source_verify_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = self.run_cli(
                FIXTURE_DIR / "tasukeru_arl.jsonl",
                root / "missing.json",
                root / "output",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("SOURCE_VERIFY_NOT_FOUND", completed.stderr)
            self.assertFalse((root / "output").exists())

    def test_runtime_arl_invalid_utf8_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            arl_path.write_bytes(b"\xff\xfe")
            completed = self.run_cli(arl_path, source_verify_path, root / "output")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("RUNTIME_ARL_UTF8_INVALID", completed.stderr)
            self.assertFalse((root / "output").exists())

    def test_source_verify_invalid_utf8_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            source_verify_path.write_bytes(b"\xff\xfe")
            completed = self.run_cli(arl_path, source_verify_path, root / "output")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("SOURCE_VERIFY_UTF8_INVALID", completed.stderr)
            self.assertFalse((root / "output").exists())

    def test_invalid_jsonl_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            lines = arl.read_text(encoding="utf-8").splitlines()
            lines[1] = "{invalid"
            arl.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

        self.assert_verification_failure(mutate, "RUNTIME_ARL_JSONL_INVALID")

    def test_nonobject_jsonl_row_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows: list[Any] = self.load_rows(arl)
            rows[1] = []
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_ROW_NOT_OBJECT")

    def test_blank_lines_only_runtime_arl_has_exact_empty_issue(self) -> None:
        def mutate(arl: Path, verify: Path) -> None:
            arl.write_text("\n  \n\t\n", encoding="utf-8", newline="\n")
            value = self.load_source_verify(verify)
            value["row_count"] = 0
            value["head_hash"] = ""
            self.write_source_verify(verify, value)

        result, _, verify = self.assert_verification_failure(
            mutate, "RUNTIME_ARL_EMPTY"
        )
        self.assertEqual(
            result["issues"][0],
            {
                "line_number": 0,
                "reason_code": "RUNTIME_ARL_EMPTY",
                "detail": "Runtime ARL contains no non-blank rows.",
                "stored_value": None,
                "recomputed_value": None,
            },
        )
        self.assertEqual(tuple(result["issues"][0]), ISSUE_KEYS)
        self.assertEqual(
            result["summary"]["reason_codes"], ["RUNTIME_ARL_EMPTY"]
        )
        self.assertIsNone(result["summary"]["source_verify_head_hash"])
        self.assertEqual(verify["errors"], ["RUNTIME_ARL_EMPTY"])
        self.assertFalse(result["verified"])
        self.assertFalse(verify["verified"])

    def test_blank_lines_are_ignored_and_physical_line_numbers_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            lines = arl_path.read_text(encoding="utf-8").splitlines()
            arl_path.write_text(
                "\n" + lines[0] + "\n\n" + lines[1] + "\n" + lines[2] + "\n",
                encoding="utf-8",
                newline="\n",
            )
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result, _, verify = self.load_outputs(output_dir)
            self.assertTrue(result["verified"])
            self.assertTrue(verify["verified"])
            self.assertEqual(result["summary"]["rows_read"], 3)
            self.assertNotIn("RUNTIME_ARL_EMPTY", result["summary"]["reason_codes"])
            self.assertNotIn(
                "RUNTIME_ARL_JSONL_INVALID", result["summary"]["reason_codes"]
            )

    def test_issue_line_number_uses_physical_line_after_blank_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            lines = arl_path.read_text(encoding="utf-8").splitlines()
            arl_path.write_text(
                lines[0] + "\n\n{invalid\n" + lines[2] + "\n",
                encoding="utf-8",
                newline="\n",
            )
            completed = self.run_cli(
                arl_path, source_verify_path, root / "output"
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            result, _, _ = self.load_outputs(root / "output")
            issue = next(
                item
                for item in result["issues"]
                if item["reason_code"] == "RUNTIME_ARL_JSONL_INVALID"
            )
            self.assertEqual(issue["line_number"], 3)

    def test_missing_required_field_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            del rows[0]["reason_code"]
            self.write_rows(arl, rows)

        self.assert_verification_failure(
            mutate, "RUNTIME_ARL_REQUIRED_FIELD_MISSING"
        )

    def test_seq_true_is_rejected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["seq"] = True
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_FIELD_TYPE_INVALID")

    def test_evidence_nonobject_is_rejected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["evidence"] = []
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_FIELD_TYPE_INVALID")

    def test_boolean_field_wrong_type_is_rejected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["sealed"] = 0
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_FIELD_TYPE_INVALID")

    def test_uppercase_sha256_is_rejected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["row_hash"] = rows[0]["row_hash"].upper()
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_HASH_FORMAT_INVALID")

    def test_malformed_sha256_is_rejected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["row_hash"] = "not-a-sha256"
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_HASH_FORMAT_INVALID")

    def test_noncontiguous_sequence_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["seq"] = 4
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_SEQUENCE_MISMATCH")

    def test_duplicate_sequence_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["seq"] = 1
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_SEQUENCE_MISMATCH")

    def test_schema_version_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["schema_version"] = "2.0"
            self.write_rows(arl, rows)

        self.assert_verification_failure(
            mutate, "RUNTIME_ARL_SCHEMA_VERSION_MISMATCH"
        )

    def test_policy_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["auto_commit_allowed"] = True
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_POLICY_MISMATCH")

    def test_run_id_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["run_id"] = "different-run"
            self.write_rows(arl, rows)

        result, _, _ = self.assert_verification_failure(
            mutate, "RUNTIME_ARL_RUN_ID_MISMATCH"
        )
        matching = [
            issue
            for issue in result["issues"]
            if issue["reason_code"] == "RUNTIME_ARL_RUN_ID_MISMATCH"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(tuple(matching[0]), ISSUE_KEYS)
        self.assertEqual(matching[0]["line_number"], 2)
        self.assertIsNone(matching[0]["stored_value"])
        self.assertIsNone(matching[0]["recomputed_value"])

    def test_arbitrary_nonempty_consistent_run_id_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            rows = self.load_rows(arl_path)
            marker = "arbitrary run id / value ? #"
            for row in rows:
                row["run_id"] = marker
            self.rehash_rows(rows)
            self.write_rows(arl_path, rows)
            self.rebind_source_verify(source_verify_path, rows)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result, binding, verify = self.load_outputs(output_dir)
            self.assertTrue(result["verified"])
            self.assertTrue(verify["verified"])
            self.assertEqual(result["summary"]["run_id"], marker)
            self.assertEqual(binding["run_id"], marker)
            report = (output_dir / VERIFIER.REPORT_FILENAME).read_text(
                encoding="utf-8"
            )
            self.assertNotIn(marker, report)

    def test_genesis_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["prev_hash"] = "0" * 64
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_GENESIS_MISMATCH")

    def test_previous_hash_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["prev_hash"] = "0" * 64
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_PREV_HASH_MISMATCH")

    def test_row_hash_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["decision"] = "RUN"
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_ROW_HASH_MISMATCH")

    def test_protected_evidence_content_mutation_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["evidence"]["notification_state_summary"]["critical_count"] = 1
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_ROW_HASH_MISMATCH")

    def test_final_row_content_mutation_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[-1]["reason_code"] = "SYNTHETIC_FINAL_ROW_CHANGE"
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_ROW_HASH_MISMATCH")

    def test_row_reorder_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0], rows[1] = rows[1], rows[0]
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_SEQUENCE_MISMATCH")

    def test_row_deletion_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            del rows[1]
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_SEQUENCE_MISMATCH")

    def test_chain_hash_mismatch_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[1]["chain_hash"] = "0" * 64
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_CHAIN_HASH_MISMATCH")

    def test_noncanonical_hash_generation_is_detected(self) -> None:
        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            row = rows[0]
            body = {
                key: value
                for key, value in row.items()
                if key not in {"row_hash", "chain_hash", "hmac_sha256"}
            }
            noncanonical = json.dumps(body, ensure_ascii=False).encode("utf-8")
            row["row_hash"] = hashlib.sha256(noncanonical).hexdigest()
            row["chain_hash"] = canonical_chain_hash("GENESIS", row["row_hash"])
            self.write_rows(arl, rows)

        self.assert_verification_failure(mutate, "RUNTIME_ARL_ROW_HASH_MISMATCH")

    def test_hmac_field_is_rejected_but_excluded_from_recomputation(self) -> None:
        hmac_marker = "b" * 64

        def mutate(arl: Path, _verify: Path) -> None:
            rows = self.load_rows(arl)
            rows[0]["hmac_sha256"] = hmac_marker
            self.write_rows(arl, rows)

        result, binding, _ = self.assert_verification_failure(
            mutate, "RUNTIME_ARL_HMAC_UNSUPPORTED"
        )
        self.assertEqual(
            result["summary"]["reason_codes"],
            ["RUNTIME_ARL_HMAC_UNSUPPORTED"],
        )
        self.assertTrue(binding["hmac_present"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            mutate(arl_path, source_verify_path)
            output_dir = root / "output"
            self.assertEqual(
                self.run_cli(arl_path, source_verify_path, output_dir).returncode,
                1,
            )
            combined = b"\n".join(path.read_bytes() for path in output_dir.iterdir())
            self.assertNotIn(hmac_marker.encode("ascii"), combined)

    def test_source_verify_malformed_json_is_detected(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            verify.write_text("{invalid\n", encoding="utf-8", newline="\n")

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_JSON_INVALID")

    def test_source_verify_nonobject_json_is_detected(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            self.write_source_verify(verify, [])

        result, _, _ = self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_SCHEMA_INVALID"
        )
        self.assertEqual(
            result["issues"][0],
            {
                "line_number": 0,
                "reason_code": "SOURCE_VERIFY_SCHEMA_INVALID",
                "detail": "Source verify artifact must be a JSON object.",
                "stored_value": None,
                "recomputed_value": None,
            },
        )

    def test_source_verify_all_optional_metadata_absent_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            value = self.load_source_verify(source_verify_path)
            for field in ("arl_path", "verify_path", "purpose"):
                del value[field]
            self.write_source_verify(source_verify_path, value)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result, _, verify = self.load_outputs(output_dir)
            self.assertTrue(result["verified"])
            self.assertTrue(verify["verified"])

    def test_source_verify_each_optional_metadata_field_may_be_absent(self) -> None:
        for field in ("arl_path", "verify_path", "purpose"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                arl_path, source_verify_path = self.copy_sources(root)
                value = self.load_source_verify(source_verify_path)
                del value[field]
                self.write_source_verify(source_verify_path, value)
                completed = self.run_cli(
                    arl_path, source_verify_path, root / "output"
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_source_verify_optional_metadata_values_are_ignored_and_not_emitted(self) -> None:
        markers = (
            "optional-arl-metadata-marker",
            "optional-verify-metadata-marker",
            "optional-purpose-metadata-marker",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            value = self.load_source_verify(source_verify_path)
            value["arl_path"], value["verify_path"], value["purpose"] = markers
            self.write_source_verify(source_verify_path, value)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            combined = b"\n".join(path.read_bytes() for path in output_dir.iterdir())
            for marker in markers:
                self.assertNotIn(marker.encode("utf-8"), combined)

    def test_zero_row_count_with_malformed_nonempty_head_is_schema_invalid(self) -> None:
        def mutate(arl: Path, verify: Path) -> None:
            arl.write_text("\n", encoding="utf-8", newline="\n")
            value = self.load_source_verify(verify)
            value["row_count"] = 0
            value["head_hash"] = "not-a-head-hash"
            self.write_source_verify(verify, value)

        result, _, _ = self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_SCHEMA_INVALID"
        )
        self.assertIn("RUNTIME_ARL_EMPTY", result["summary"]["reason_codes"])

    def test_positive_row_count_with_empty_head_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["head_hash"] = ""
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_SCHEMA_INVALID")

    def test_source_verify_missing_field_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            del value["policy"]
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_SCHEMA_INVALID")

    def test_source_verify_wrong_type_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["verified"] = "true"
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_SCHEMA_INVALID")

    def test_source_verify_wrong_schema_version_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["schema_version"] = "2.0"
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_SCHEMA_INVALID")

    def test_source_verify_row_count_bool_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["row_count"] = True
            self.write_source_verify(verify, value)

        result, _, _ = self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_SCHEMA_INVALID"
        )
        self.assertEqual(
            result["summary"]["reason_codes"],
            ["SOURCE_VERIFY_SCHEMA_INVALID"],
        )

    def test_source_verify_tool_mismatch_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["tool"] = "wrong-tool"
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_TOOL_MISMATCH")

    def test_source_verify_policy_mismatch_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["policy"]["auto_push_allowed"] = True
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_POLICY_MISMATCH")

    def test_source_verify_hmac_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["hmac_enabled"] = True
            self.write_source_verify(verify, value)

        result, binding, _ = self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_HMAC_UNSUPPORTED"
        )
        self.assertTrue(result["summary"]["hmac_enabled"])
        self.assertTrue(binding["hmac_enabled"])
        self.assertFalse(binding["authenticity_claimed"])

    def test_source_verify_reported_failure_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["verified"] = False
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_REPORTED_FAILURE")

    def test_source_verify_errors_have_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["errors"] = [{"reason": "fixture"}]
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_ERRORS_PRESENT")

    def test_source_verify_row_count_mismatch_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["row_count"] = 99
            self.write_source_verify(verify, value)

        self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_ROW_COUNT_MISMATCH"
        )

    def test_source_verify_head_mismatch_has_dedicated_reason(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["head_hash"] = "0" * 64
            self.write_source_verify(verify, value)

        self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_HEAD_HASH_MISMATCH"
        )

    def test_source_verify_uppercase_head_is_schema_invalid(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["head_hash"] = value["head_hash"].upper()
            self.write_source_verify(verify, value)

        self.assert_verification_failure(mutate, "SOURCE_VERIFY_SCHEMA_INVALID")

    def test_issue_order_fields_and_contents_are_exact(self) -> None:
        def mutate(_arl: Path, verify: Path) -> None:
            value = self.load_source_verify(verify)
            value["verified"] = False
            value["errors"] = [{"reason": "fixture"}]
            self.write_source_verify(verify, value)

        result, _, verify = self.assert_verification_failure(
            mutate, "SOURCE_VERIFY_REPORTED_FAILURE"
        )
        self.assertEqual(
            result["issues"],
            [
                {
                    "line_number": 0,
                    "reason_code": "SOURCE_VERIFY_REPORTED_FAILURE",
                    "detail": "Source verify artifact reports a failed verification.",
                    "stored_value": False,
                    "recomputed_value": True,
                },
                {
                    "line_number": 0,
                    "reason_code": "SOURCE_VERIFY_ERRORS_PRESENT",
                    "detail": "Source verify errors must be empty.",
                    "stored_value": None,
                    "recomputed_value": None,
                },
            ],
        )
        self.assertEqual(tuple(result["issues"][0]), ISSUE_KEYS)
        self.assertEqual(
            verify["errors"],
            ["SOURCE_VERIFY_REPORTED_FAILURE", "SOURCE_VERIFY_ERRORS_PRESENT"],
        )

    def test_unknown_output_file_stops_without_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            output_dir.mkdir()
            marker = output_dir / "unknown.txt"
            marker.write_text("preserve", encoding="utf-8")
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID", completed.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(tuple(path.name for path in output_dir.iterdir()), ("unknown.txt",))

    def test_unknown_output_directory_entry_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            (output_dir / "nested").mkdir(parents=True)
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID", completed.stderr)

    def test_symlink_output_entry_is_rejected_without_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output_dir = root / "output"
            output_dir.mkdir()
            known = output_dir / VERIFIER.RESULT_FILENAME
            known.write_text("preserve", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(path: Path) -> bool:
                if path == known:
                    return True
                return original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", simulated_is_symlink):
                with self.assertRaises(VERIFIER.VerifierOperationalError) as caught:
                    VERIFIER.validate_output_directory(output_dir)
            self.assertEqual(
                caught.exception.reason_code,
                "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID",
            )
            self.assertEqual(known.read_text(encoding="utf-8"), "preserve")

    def test_output_directory_symlink_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            target = root / "target"
            target.mkdir()
            output_link = root / "output-link"
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(path: Path) -> bool:
                if path == output_link:
                    return True
                return original_is_symlink(path)

            stderr = io.StringIO()
            with (
                mock.patch.object(Path, "is_symlink", simulated_is_symlink),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_link),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn(
                "RUNTIME_ARL_OUTPUT_DIRECTORY_INVALID", stderr.getvalue()
            )
            self.assertFalse(output_link.exists())
            self.assertEqual(tuple(target.iterdir()), ())

    def test_known_output_files_are_replaced_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            output_dir.mkdir()
            for filename in EXPECTED_OUTPUT_FILES:
                (output_dir / filename).write_text("stale", encoding="utf-8")
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                set(EXPECTED_OUTPUT_FILES),
            )
            self.assertTrue(all((output_dir / name).read_text(encoding="utf-8") != "stale" for name in EXPECTED_OUTPUT_FILES))

    def test_safe_write_uses_replace_for_all_four_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            replace_calls: list[tuple[str, str]] = []
            original_replace = Path.replace

            def tracked_replace(path: Path, target: Path) -> Path:
                replace_calls.append((path.name, Path(target).name))
                return original_replace(path, target)

            with mock.patch.object(Path, "replace", tracked_replace):
                run = VERIFIER.run_verifier(arl_path, source_verify_path, output_dir)
            self.assertTrue(run["verify"]["verified"])
            self.assertEqual(len(replace_calls), 4)
            self.assertEqual(
                [target for _temporary, target in replace_calls],
                list(EXPECTED_WRITE_ORDER),
            )
            self.assertTrue(all(name.startswith(".") and name.endswith(".tmp") for name, _target in replace_calls))
            self.assertFalse(
                any(path.name.endswith(".tmp") for path in output_dir.iterdir())
            )

    def test_fsync_failure_cleans_temp_and_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            stderr = io.StringIO()
            with (
                mock.patch.object(
                    VERIFIER.os,
                    "fsync",
                    side_effect=OSError("simulated fsync failure"),
                ),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_dir),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", stderr.getvalue())
            self.assertTrue(output_dir.is_dir())
            self.assertEqual(tuple(output_dir.iterdir()), ())

    def test_replace_failure_cleans_temp_preserves_destination_and_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            output_dir.mkdir()
            destination = output_dir / VERIFIER.RESULT_FILENAME
            destination.write_text("stable-destination", encoding="utf-8")
            stderr = io.StringIO()
            with (
                mock.patch.object(
                    Path,
                    "replace",
                    side_effect=OSError("simulated replace failure"),
                ),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_dir),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", stderr.getvalue())
            self.assertEqual(
                destination.read_text(encoding="utf-8"), "stable-destination"
            )
            self.assertFalse(
                any(path.name.endswith(".tmp") for path in output_dir.iterdir())
            )

    def test_result_bytes_mismatch_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            original_read_bytes = Path.read_bytes

            def mismatched_read_bytes(path: Path) -> bytes:
                value = original_read_bytes(path)
                if path.name == VERIFIER.RESULT_FILENAME:
                    return value + b"mismatch"
                return value

            stderr = io.StringIO()
            with (
                mock.patch.object(Path, "read_bytes", mismatched_read_bytes),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_dir),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", stderr.getvalue())
            self.assertFalse((output_dir / VERIFIER.VERIFY_FILENAME).exists())

    def test_source_binding_bytes_mismatch_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            original_read_bytes = Path.read_bytes

            def mismatched_read_bytes(path: Path) -> bytes:
                value = original_read_bytes(path)
                if path.name == VERIFIER.SOURCE_BINDING_FILENAME:
                    return value + b"mismatch"
                return value

            stderr = io.StringIO()
            with (
                mock.patch.object(Path, "read_bytes", mismatched_read_bytes),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_dir),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", stderr.getvalue())
            self.assertFalse((output_dir / VERIFIER.VERIFY_FILENAME).exists())

    def test_output_hash_failure_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            output_dir = root / "output"
            stderr = io.StringIO()
            with (
                mock.patch.object(
                    VERIFIER,
                    "file_sha256",
                    side_effect=OSError("simulated output read failure"),
                ),
                mock.patch.object(sys, "stderr", stderr),
            ):
                exit_code = VERIFIER.main(
                    [
                        "--arl",
                        str(arl_path),
                        "--source-verify",
                        str(source_verify_path),
                        "--out-dir",
                        str(output_dir),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", stderr.getvalue())
            self.assertFalse((output_dir / VERIFIER.VERIFY_FILENAME).exists())

    def test_integrity_failure_returns_one_without_output_write_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            rows = self.load_rows(arl_path)
            rows[1]["decision"] = "RUN"
            self.write_rows(arl_path, rows)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            result, _, verify = self.load_outputs(output_dir)
            self.assertIn(
                "RUNTIME_ARL_ROW_HASH_MISMATCH",
                result["summary"]["reason_codes"],
            )
            self.assertNotIn("RUNTIME_ARL_OUTPUT_WRITE_FAILED", verify["errors"])

    def test_unknown_internal_reason_code_returns_two(self) -> None:
        def unknown_reason(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            collector = VERIFIER.IssueCollector()
            collector.add(0, "UNKNOWN_REASON_CODE", "not permitted")
            raise AssertionError("unreachable")

        with mock.patch.object(VERIFIER, "run_verifier", unknown_reason):
            exit_code = VERIFIER.main(
                [
                    "--arl",
                    "unused.jsonl",
                    "--source-verify",
                    "unused.json",
                    "--out-dir",
                    "unused-output",
                ]
            )
        self.assertEqual(exit_code, 2)

    def test_fully_rehashed_source_is_consistent_without_authenticity_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arl_path, source_verify_path = self.copy_sources(root)
            rows = self.load_rows(arl_path)
            rows[1]["decision"] = "RUN"
            self.rehash_rows(rows)
            self.write_rows(arl_path, rows)
            self.rebind_source_verify(source_verify_path, rows)
            output_dir = root / "output"
            completed = self.run_cli(arl_path, source_verify_path, output_dir)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result, binding, verify = self.load_outputs(output_dir)
            self.assertTrue(result["verified"])
            self.assertTrue(verify["verified"])
            self.assertFalse(result["summary"]["authenticity_claimed"])
            self.assertFalse(binding["authenticity_claimed"])


if __name__ == "__main__":
    unittest.main()
