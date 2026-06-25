from __future__ import annotations

import py_compile
import tempfile
import unittest
from pathlib import Path

from evaluator_pseudocode_v0_8_explainable_patch_gate import (
    Decision,
    Level,
    Observation,
    build_human_review_stub,
    classify,
)


TEST_PATH = Path(__file__).resolve()
PROJECT_ROOT = TEST_PATH.parents[1]
EVALUATOR_PATH = PROJECT_ROOT / "evaluator_pseudocode_v0_8_explainable_patch_gate.py"
if not EVALUATOR_PATH.exists():
    EVALUATOR_PATH = TEST_PATH.parent / "evaluator_pseudocode_v0_8_explainable_patch_gate.py"


class PatchAccountabilityTests(unittest.TestCase):
    def classify(self, **kwargs):
        obs = Observation(
            declared_purpose="patch accountability validation",
            **kwargs,
        )
        return classify(obs)

    def test_patch_accountability_fields_default_to_false(self):
        obs = Observation(declared_purpose="default field validation")

        self.assertFalse(obs.patch_generated)
        self.assertFalse(obs.patch_applied)
        self.assertFalse(obs.security_related_patch)
        self.assertFalse(obs.has_human_readable_explanation)
        self.assertFalse(obs.has_evidence)
        self.assertFalse(obs.has_impact_analysis)
        self.assertFalse(obs.has_validation_results)
        self.assertFalse(obs.explanation_matches_diff)
        self.assertFalse(obs.auto_patch_application_requested)
        self.assertFalse(obs.auto_commit_requested)
        self.assertFalse(obs.auto_push_requested)
        self.assertFalse(obs.auto_pr_requested)
        self.assertFalse(obs.auto_merge_requested)
        self.assertFalse(obs.auto_deploy_requested)

    def test_generated_patch_without_explanation_requires_human_review(self):
        result = self.classify(
            patch_generated=True,
            has_evidence=True,
            has_impact_analysis=True,
            has_validation_results=True,
            explanation_matches_diff=True,
        )

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "patch_explanation_missing",
            result.patch_accountability_reason_codes,
        )

    def test_applied_patch_without_support_requires_human_review(self):
        result = self.classify(
            patch_applied=True,
            has_human_readable_explanation=True,
        )

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)

    def test_security_patch_missing_support_requires_human_review(self):
        result = self.classify(
            security_related_patch=True,
            has_human_readable_explanation=True,
            explanation_matches_diff=True,
        )

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertTrue(
            {
                "patch_evidence_missing",
                "patch_impact_analysis_missing",
                "patch_validation_results_missing",
                "security_patch_requires_human_review",
            }.issubset(result.patch_accountability_reason_codes)
        )

    def test_supported_security_patch_still_requires_human_review(self):
        result = self.classify(
            security_related_patch=True,
            has_human_readable_explanation=True,
            has_evidence=True,
            has_impact_analysis=True,
            has_validation_results=True,
            explanation_matches_diff=True,
        )

        self.assertEqual(result.level, Level.L0)
        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "security_patch_requires_human_review",
            result.patch_accountability_reason_codes,
        )

    def test_supported_applied_patch_still_requires_human_review(self):
        result = self.classify(
            patch_applied=True,
            has_human_readable_explanation=True,
            has_evidence=True,
            has_impact_analysis=True,
            has_validation_results=True,
            explanation_matches_diff=True,
        )

        self.assertEqual(result.level, Level.L0)
        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "already_applied_patch_requires_human_review",
            result.patch_accountability_reason_codes,
        )

    def test_explanation_mismatch_requires_human_review(self):
        result = self.classify(
            patch_generated=True,
            has_human_readable_explanation=True,
            has_evidence=True,
            has_impact_analysis=True,
            has_validation_results=True,
            explanation_matches_diff=False,
        )

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "patch_explanation_diff_mismatch",
            result.patch_accountability_reason_codes,
        )

    def test_patch_rationale_entries_are_full_strings(self):
        result = self.classify(patch_generated=True)

        self.assertIn("patch explanation missing", result.rationale)
        self.assertNotIn("p", result.rationale)

    def test_supported_patch_can_continue_when_base_route_allows(self):
        result = self.classify(
            patch_generated=True,
            has_human_readable_explanation=True,
            has_evidence=True,
            has_impact_analysis=True,
            has_validation_results=True,
            explanation_matches_diff=True,
        )

        self.assertEqual(result.level, Level.L0)
        self.assertEqual(result.decision, Decision.CONTINUE)
        self.assertEqual(result.patch_accountability_reason_codes, ())

    def test_auto_patch_application_requires_human_review(self):
        result = self.classify(auto_patch_application_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_patch_application_requested",
            result.patch_accountability_reason_codes,
        )

    def test_auto_commit_requires_human_review(self):
        result = self.classify(auto_commit_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_commit_requested",
            result.patch_accountability_reason_codes,
        )

    def test_auto_push_requires_human_review(self):
        result = self.classify(auto_push_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_push_requested",
            result.patch_accountability_reason_codes,
        )

    def test_auto_pr_requires_human_review(self):
        result = self.classify(auto_pr_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_pr_requested",
            result.patch_accountability_reason_codes,
        )

    def test_auto_merge_requires_human_review(self):
        result = self.classify(auto_merge_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_merge_requested",
            result.patch_accountability_reason_codes,
        )

    def test_auto_deploy_requires_human_review(self):
        result = self.classify(auto_deploy_requested=True)

        self.assertEqual(result.decision, Decision.HUMAN_REVIEW_REQUIRED)
        self.assertIn(
            "automatic_deploy_requested",
            result.patch_accountability_reason_codes,
        )

    def test_existing_l4_l5_l6_routes_are_unchanged(self):
        l4 = self.classify(requested_actions=("file_write",))
        l5 = self.classify(requested_actions=("own_evaluator_change",))
        l6 = self.classify(
            capability_signals=("iterative_generate_evaluate_select_improve",)
        )

        self.assertEqual(
            (l4.level, l4.decision),
            (
                Level.L4,
                Decision.HUMAN_REVIEW_REQUIRED,
            ),
        )
        self.assertEqual(
            (l5.level, l5.decision),
            (
                Level.L5,
                Decision.ISOLATED_REVIEW_REQUIRED,
            ),
        )
        self.assertEqual(
            (l6.level, l6.decision),
            (
                Level.L6,
                Decision.STOP_AND_PRESERVE,
            ),
        )

    def test_patch_overlay_does_not_weaken_l5_or_l6(self):
        l5 = self.classify(
            requested_actions=("own_evaluator_change",),
            auto_commit_requested=True,
        )
        l6 = self.classify(
            capability_signals=("iterative_generate_evaluate_select_improve",),
            patch_generated=True,
        )

        self.assertEqual(l5.decision, Decision.ISOLATED_REVIEW_REQUIRED)
        self.assertEqual(l6.decision, Decision.STOP_AND_PRESERVE)

    def test_blocked_actions_include_automatic_patch_actions(self):
        result = self.classify()

        self.assertTrue(
            {
                "automatic_patch_application",
                "automatic_commit",
                "automatic_push",
                "automatic_pr",
                "automatic_merge",
                "automatic_deploy",
            }.issubset(result.blocked_actions)
        )

    def test_human_review_stub_includes_patch_accountability_fields_and_reason_codes(self):
        obs = Observation(
            declared_purpose="patch accountability validation",
            patch_generated=True,
            auto_patch_application_requested=True,
            auto_commit_requested=True,
            auto_push_requested=True,
            auto_pr_requested=True,
            auto_merge_requested=True,
            auto_deploy_requested=True,
        )
        classification = classify(obs)
        stub = build_human_review_stub(obs, classification)

        self.assertIn("patch_accountability_reason_codes", stub)
        self.assertIn("patch_accountability", stub)
        self.assertIn(
            "patch_explanation_missing",
            stub["patch_accountability_reason_codes"],
        )
        self.assertIn(
            "automatic_patch_application_requested",
            stub["patch_accountability_reason_codes"],
        )
        self.assertTrue(stub["patch_accountability"]["patch_generated"])
        self.assertTrue(
            stub["patch_accountability"]["auto_patch_application_requested"]
        )
        self.assertTrue(stub["patch_accountability"]["auto_commit_requested"])
        self.assertTrue(stub["patch_accountability"]["auto_push_requested"])
        self.assertTrue(stub["patch_accountability"]["auto_pr_requested"])
        self.assertTrue(stub["patch_accountability"]["auto_merge_requested"])
        self.assertTrue(stub["patch_accountability"]["auto_deploy_requested"])

    def test_py_compile_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pyc_path = Path(tmpdir) / "evaluator_pseudocode_v0_8_explainable_patch_gate.pyc"
            py_compile.compile(
                str(EVALUATOR_PATH),
                cfile=str(pyc_path),
                doraise=True,
            )


if __name__ == "__main__":
    unittest.main()
