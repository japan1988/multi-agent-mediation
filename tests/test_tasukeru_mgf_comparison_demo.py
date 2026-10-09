"""Integration regressions for the report-only MGF side experiment.

Test the late-stop repair, bounded mock feedback and evidence handoff. These
checks exercise local fixtures; they do not certify real AI or live approval.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts/tasukeru_mediation_demo/run_mgf_comparison_demo.py"
SPEC = importlib.util.spec_from_file_location("mgf_comparison_test_entry", RUNNER)
SIM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SIM)


class MGFIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_path = RUNNER.with_name("mgf_comparison_baseline.json")
        cls.manifest = SIM.read_manifest(cls.manifest_path)
        cls.sources_before = SIM.verify_sources(REPO, cls.manifest)
        cls.boundary = SIM.load(RUNNER.with_name("run_mediator_boundary_demo.py"), "mgf_test_boundary")
        _, cls.demo, cls.gate, cls.controller = cls.boundary.load_baseline(REPO)
        cls.packet = SIM.synthetic_packet(cls.demo)
        cls.cases = SIM.make_cases(cls.boundary, cls.gate, cls.packet)
        cls.before = [SIM.run_case(c, v, False, cls.boundary, cls.gate, cls.controller)
                      for c in cls.cases for v in SIM.VARIANTS]
        cls.after = [SIM.run_case(c, v, True, cls.boundary, cls.gate, cls.controller)
                     for c in cls.cases for v in SIM.VARIANTS]

    def fixture(self, name="FINALIZATION"):
        ctx = self.boundary.host_fixture(self.packet, name)
        plan = self.boundary.plan_fixture(ctx, self.packet, self.gate)
        fw = SIM.FrameworkFixture(ctx, self.packet)
        return fw, fw.snapshot(), plan

    def finish(self, fw, initial, plan):
        return fw.finalize_once(initial, self.boundary, self.gate, plan)[0]

    def rows(self, name, after=True):
        return {r["variant"]: r for r in (self.after if after else self.before) if r["case"] == name}

    def test_repaired_profiles_match_the_predeclared_oracle(self):
        self.assertEqual(len(self.cases), 83)
        self.assertEqual(len(self.after), 332)
        for row in self.after:
            with self.subTest(variant=row["variant"], case=row["case"]):
                self.assertTrue(row["contract_pass"])

    def test_unprotected_late_stop_and_rejection_remain_regression_controls(self):
        failures = [r for r in self.before if not r["contract_pass"]]
        self.assertEqual({(r["variant"], r["case"]) for r in failures}, {
            ("D", "stop_after_observer_before_commit"),
            ("D", "reject_after_observer_before_commit"),
        })
        for name, expected in (("stop_after_observer_before_commit", "STOPPED"),
                               ("reject_after_observer_before_commit", "REJECTED")):
            self.assertEqual(self.rows(name, False)["D"]["actual_state"], "HUMAN_REVIEW")
            self.assertEqual(self.rows(name)["D"]["actual_state"], expected)

    def test_repaired_d_withholds_invalid_reports_without_blocking_controls(self):
        summary = SIM.summarize(self.after)
        self.assertEqual(summary["D"]["invalid_or_stale_reports_forwarded"], 0)
        self.assertEqual(summary["D"]["healthy_controls"], 19)
        for variant in SIM.VARIANTS:
            self.assertEqual(summary[variant]["healthy_false_blocks"], 0)
        # Deliberately incomplete paths expose the value of the added controls.
        self.assertEqual(summary["A"]["invalid_or_stale_reports_forwarded"], 26)
        self.assertEqual(summary["C"]["invalid_or_stale_reports_forwarded"], 11)

    def test_fresh_stop_prevents_finalization(self):
        fw, initial, plan = self.fixture()
        fw.change(lambda c, p: c.update(stopped=True))
        self.assertEqual(self.finish(fw, initial, plan), "STOPPED")
        self.assertFalse(fw.finalized)

    def test_fresh_rejection_prevents_finalization(self):
        fw, initial, plan = self.fixture()
        fw.change(lambda c, p: c.update(rejected=True))
        self.assertEqual(self.finish(fw, initial, plan), "REJECTED")
        self.assertFalse(fw.finalized)

    def test_unknown_state_prevents_finalization(self):
        fw, initial, plan = self.fixture()
        fw.change(lambda c, p: c.update(snapshot_state="UNKNOWN"))
        self.assertEqual(self.finish(fw, initial, plan), "UNKNOWN_HITL")
        self.assertFalse(fw.finalized)

    def test_a_changed_then_restored_state_invalidates_the_snapshot(self):
        fw, initial, plan = self.fixture()
        fw.change(lambda c, p: c["history"].append("WRITE_DRAFT"))
        fw.change(lambda c, p: c["history"].pop())
        self.assertEqual(fw.context, initial[0])
        self.assertEqual(self.finish(fw, initial, plan), "STOPPED_CONTEXT_CHANGED")

    def test_a_report_slot_cannot_be_finalized_twice(self):
        fw, initial, plan = self.fixture()
        self.assertEqual(self.finish(fw, initial, plan), "HUMAN_REVIEW")
        self.assertEqual(self.finish(fw, initial, plan), "BLOCKED_LINK")

    def test_stop_after_finalization_is_recorded_without_claiming_undo(self):
        fw, initial, plan = self.fixture()
        self.assertEqual(self.finish(fw, initial, plan), "HUMAN_REVIEW")
        fw.change(lambda c, p: c.update(stopped=True))
        self.assertTrue(fw.finalized)
        self.assertEqual(self.finish(fw, initial, plan), "STOPPED")

    def test_actual_threads_respect_stop_rejection_unknown_and_one_use(self):
        checks = SIM.concurrency_checks(self.boundary, self.gate, self.controller, self.packet)
        self.assertEqual(len(checks), 13)
        self.assertTrue(all(c["passed"] for c in checks), checks)

    def test_feedback_is_bounded_and_never_grants_execution(self):
        row = self.rows("approved_correction")["D"]
        self.assertEqual(row["actual_state"], "HUMAN_REVIEW")
        self.assertEqual(row["mock_resubmissions"], 1)
        self.assertFalse(row["execution_allowed"])
        self.assertTrue(all(r["mock_resubmissions"] <= 1 for r in self.after))

    def test_absent_forged_and_expired_grants_do_not_regenerate(self):
        for name, expected in (("no_approval", "WAITING_FOR_APPROVAL"),
                               ("forged_approval", "STOPPED_APPROVAL"),
                               ("expired_approval", "STOPPED_APPROVAL")):
            with self.subTest(name=name):
                row = self.rows(name)["D"]
                self.assertEqual(row["actual_state"], expected)
                self.assertEqual(row["mock_resubmissions"], 0)

    def test_replayed_grants_do_not_create_a_second_submission(self):
        row = self.rows("replay_approval")["D"]
        self.assertTrue(row["invariants_pass"])
        self.assertEqual(row["mock_resubmissions"], 1)

    def test_unknown_generation_and_changed_context_cannot_become_review(self):
        for name, state in (("generation_result_unknown", "STOPPED_RESULT_UNKNOWN"),
                            ("context_changes_during_generation", "STOPPED_CONTEXT_CHANGED")):
            self.assertEqual(self.rows(name)["D"]["actual_state"], state)

    def test_changed_report_facts_authority_or_warnings_are_withheld(self):
        names = [c["name"] for c in self.cases if c["group"] == "render"]
        self.assertEqual(len(names), 8)
        for name in names:
            self.assertEqual(self.rows(name)["D"]["actual_state"], "BLOCKED_REPORT")

    def test_changed_message_bindings_or_writer_roles_are_withheld(self):
        names = [c["name"] for c in self.cases if c["group"] == "link"]
        self.assertEqual(len(names), 8)
        for name in names:
            self.assertEqual(self.rows(name)["D"]["actual_state"], "BLOCKED_LINK")

    def test_original_packets_cases_and_sources_are_preserved(self):
        original = SIM.enc(self.cases)
        case = next(c for c in self.cases if c["name"] == "approved_correction")
        SIM.run_case(case, "D", True, self.boundary, self.gate, self.controller)
        self.assertEqual(SIM.enc(self.cases), original)
        self.assertEqual(SIM.verify_sources(REPO, self.manifest), self.sources_before)

    def test_all_variants_are_inert_even_when_incomplete(self):
        for row in self.before + self.after:
            self.assertEqual(row["real_AI_calls"], 0)
            self.assertEqual(row["external_actions"], 0)
            self.assertFalse(row["execution_allowed"])


class MGFEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "report"

    def invoke(self, *extra):
        return subprocess.run([sys.executable, "-I", "-B", str(RUNNER),
                               "--output", str(self.output), *map(str, extra)],
                              capture_output=True, text=True, timeout=30)

    def test_synthetic_entry_produces_complete_limited_reports(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.output / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "EXPECTED_MOCK_BEHAVIOR_AFTER_DRAFT_FIX")
        self.assertEqual(report["input"], "SYNTHETIC_TEST_FIXTURE")
        self.assertIsNone(report["input_zip_sha256"])
        self.assertEqual(report["source_files_checked"], 20)
        self.assertTrue(report["source_unchanged"])
        self.assertEqual(report["cases_per_variant"], 83)
        self.assertEqual(report["after_fix_failures"], [])
        self.assertEqual(report["concurrency_passed"], 13)
        self.assertEqual(report["baseline_regressions"]["tests_passed"], 20)
        self.assertEqual(report["oracle_sha256"], SIM.sha((self.output / "cases.json").read_bytes()))
        self.assertFalse(report["real_approval_verified"])
        self.assertFalse(report["durable_cross_run_state_verified"])
        self.assertEqual(report["final_adoption"], "NOT_DETERMINED")
        summary = (self.output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("SYNTHETIC_TEST_FIXTURE", summary)
        self.assertIn("whole-system safety", summary)
        self.assertIn("not a durable transaction", summary)
        self.assertEqual(set(p.name for p in self.output.iterdir()),
                         {"cases.json", "comparison.csv", "report.json", "summary.md"})

    def test_existing_output_is_preserved_and_execution_is_refused(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OUTPUT_ALREADY_EXISTS", result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual(list(self.output.iterdir()), [sentinel])

    def test_rewritten_manifest_cannot_remove_baseline_checks(self):
        manifest = self.root / "shortened.json"
        manifest.write_text(json.dumps({"pin": {"sha": SIM.PIN}, "files": []}), encoding="utf-8")
        result = self.invoke("--source-manifest", manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SOURCE_MANIFEST_PIN_MISMATCH", result.stderr)
        self.assertFalse(self.output.exists())

    def test_changed_baseline_stops_before_comparison(self):
        repo = self.root / "repo"
        manifest = SIM.read_manifest(RUNNER.with_name("mgf_comparison_baseline.json"))
        for item in manifest["files"]:
            dest = repo / item["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / item["path"], dest)
        target = repo / "scripts/tasukeru_mediation_demo/mediation_gate_draft.py"
        target.write_bytes(target.read_bytes() + b"\n# Changed baseline\n")
        result = self.invoke("--repo-root", repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SOURCE_PIN_MISMATCH", result.stderr)
        self.assertFalse(self.output.exists())

    def test_invalid_local_archive_never_becomes_a_passing_report(self):
        bad = self.root / "invalid.zip"
        bad.write_bytes(b"not an observer archive")
        result = self.invoke("--observer-zip", bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("EXPECTED_MOCK_BEHAVIOR_AFTER_DRAFT_FIX", result.stdout)
        self.assertFalse((self.output / "report.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
