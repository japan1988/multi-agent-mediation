# tests/test_ai_doc_orchestrator_kage3_v1_2_3.py
# -*- coding: utf-8 -*-

import json
import os
import stat
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

# Ensure repository root is importable under pytest/CI cwd differences.
_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests/.. (repo root)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import ai_doc_orchestrator_kage3_v1_2_3 as mod


class TestAiDocOrchestratorKage3V123(unittest.TestCase):
    def _read_jsonl(self, p: Path):
        lines = p.read_text(encoding="utf-8").splitlines()
        return [json.loads(ln) for ln in lines if ln.strip()]

    def _file_contains_email_like(self, p: Path) -> bool:
        if not p.exists():
            return False
        return bool(mod.EMAIL_RE.search(p.read_text(encoding="utf-8")))

    def test_leak_email_fault_stops_at_ethics_no_artifact_and_no_raw_email_in_audit(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            artifact_dir = td / "artifacts"

            res = mod.run_simulation(
                prompt="Please generate a Word document outline (docx).",
                run_id="run_leak_email",
                audit_path=str(audit_path),
                artifact_dir=str(artifact_dir),
                faults={"word": {"leak_email": True}},
                truncate_audit_on_start=True,
            )

            self.assertEqual(res.run_id, "run_leak_email")
            self.assertEqual(res.decision, "HITL")
            self.assertEqual(res.artifacts_written_task_ids, [])
            self.assertFalse(artifact_dir.exists() and any(artifact_dir.iterdir()))

            self.assertTrue(audit_path.exists())
            self.assertFalse(self._file_contains_email_like(audit_path))
            self.assertNotIn(
                "test.user+demo@example.com", audit_path.read_text(encoding="utf-8")
            )

    def test_break_contract_fault_hits_consistency_no_artifact_and_regen_events_in_audit(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            artifact_dir = td / "artifacts"

            res = mod.run_simulation(
                prompt="Create a Word document outline (docx) with headings.",
                run_id="run_break_contract",
                audit_path=str(audit_path),
                artifact_dir=str(artifact_dir),
                faults={"word": {"break_contract": True}},
                truncate_audit_on_start=True,
            )

            self.assertEqual(res.decision, "HITL")
            self.assertEqual(res.artifacts_written_task_ids, [])
            self.assertFalse(artifact_dir.exists() and any(artifact_dir.iterdir()))

            rows = self._read_jsonl(audit_path)
            events = [r.get("event") for r in rows]
            self.assertIn("REGEN_REQUESTED", events)
            self.assertIn("REGEN_INSTRUCTIONS", events)

            word_consistency = [
                r
                for r in rows
                if r.get("task_id") == "task_word"
                and r.get("event") == "GATE_CONSISTENCY"
            ]
            self.assertTrue(word_consistency)
            self.assertEqual(word_consistency[-1].get("decision"), "HITL")
            self.assertFalse(self._file_contains_email_like(audit_path))

    def test_emit_accepts_non_json_types_and_produces_parseable_json(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            alog = mod.AuditLog(audit_path)
            alog.start_run(truncate=True)

            row = {
                "event": "NON_JSON_TYPES",
                "when": datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
                "path": Path("/tmp/somewhere"),
                "err": ValueError("boom"),
            }
            alog.emit(row)

            rows = self._read_jsonl(audit_path)
            self.assertEqual(len(rows), 1)
            r0 = rows[0]
            self.assertIn("ts", r0)
            self.assertEqual(r0.get("event"), "NON_JSON_TYPES")
            self.assertIsInstance(r0.get("when"), str)
            self.assertIsInstance(r0.get("path"), str)
            self.assertIsInstance(r0.get("err"), str)

    def test_start_run_truncate_resets_file_and_ts_monotonic_per_run(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            alog = mod.AuditLog(audit_path)

            alog.start_run(truncate=True)
            alog.emit({"event": "RUN1"})
            self.assertEqual(len(self._read_jsonl(audit_path)), 1)

            alog.start_run(truncate=True)
            alog.emit({"event": "RUN2_A"})
            alog.emit({"event": "RUN2_B"})
            run2_rows = self._read_jsonl(audit_path)
            self.assertEqual(len(run2_rows), 2)

            t0 = datetime.fromisoformat(run2_rows[0]["ts"])
            t1 = datetime.fromisoformat(run2_rows[1]["ts"])
            self.assertLess(t0, t1)

    def test_emit_accepts_circular_refs_and_still_writes_one_json_line(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            alog = mod.AuditLog(audit_path)
            alog.start_run(truncate=True)

            a = {}
            a["self"] = a  # circular ref
            alog.emit({"event": "CIRCULAR", "payload": a})

            rows = self._read_jsonl(audit_path)
            self.assertEqual(len(rows), 1)
            self.assertIn("ts", rows[0])
            self.assertIn(
                rows[0].get("event"),
                ["AUDIT_EMIT_ERROR", "AUDIT_LINE_TRUNCATED", "CIRCULAR"],
            )
            self.assertFalse(self._file_contains_email_like(audit_path))

    # ---- Stage4 fixation: PRESERVE_ALL (DUP starts at 2) ----
    def test_deep_redact_preserve_all_suffixes_dup2_on_first_collision(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            alog = mod.AuditLog(audit_path)
            alog.start_run(truncate=True)

            alog.emit(
                {
                    "event": "KEY_COLLISION",
                    "a@b.com": 1,  # -> <REDACTED_EMAIL>
                    "<REDACTED_EMAIL>": 2,  # -> <REDACTED_EMAIL> (collision)
                }
            )

            r0 = self._read_jsonl(audit_path)[0]
            self.assertIn("<REDACTED_EMAIL>", r0)
            self.assertIn("<REDACTED_EMAIL>__DUP2", r0)  # spec: first collision -> DUP2
            self.assertFalse(self._file_contains_email_like(audit_path))

    # ---- Stage4 fixation: KEEP_MIN_FIELDS ----
    def test_audit_line_truncated_keeps_min_fields(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            audit_path = td / "audit.jsonl"
            alog = mod.AuditLog(audit_path)
            alog.start_run(truncate=True)

            big = "X" * (mod._AUDIT_MAX_LINE_BYTES * 2)
            alog.emit(
                {
                    "run_id": "run_trunc",
                    "task_id": "task_x",
                    "layer": "orchestrator",
                    "event": "BIG_PAYLOAD",
                    "payload": big,
                }
            )

            r0 = self._read_jsonl(audit_path)[0]
            self.assertEqual(r0.get("event"), "AUDIT_LINE_TRUNCATED")
            self.assertEqual(r0.get("run_id"), "run_trunc")
            self.assertEqual(r0.get("task_id"), "task_x")
            self.assertEqual(r0.get("layer"), "orchestrator")

    # ---- Stage4 fixation: start_run()/emit never raise on I/O failure (POSIX; flake-safe) ----
    def test_start_run_and_emit_do_not_raise_on_io_failure_posix(self):
        if os.name != "posix":
            self.skipTest("chmod-based permission test is POSIX-only")

        with TemporaryDirectory() as td:
            td = Path(td)
            ro_dir = td / "ro"
            ro_dir.mkdir()
            ro_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
            try:
                audit_path = ro_dir / "audit.jsonl"
                alog = mod.AuditLog(audit_path)

                # 前提確認（環境によっては書けてしまうことがある）
                try:
                    with audit_path.open("a", encoding="utf-8") as f:
                        f.write("x\n")
                    self.skipTest(
                        "environment allowed writing despite chmod; skip to avoid flake"
                    )
                except Exception:
                    pass

                alog.start_run(truncate=True)
                alog.emit({"event": "IO_FAIL_TEST"})
                self.assertTrue(True)
            finally:
                ro_dir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


if __name__ == "__main__":
    unittest.main()
