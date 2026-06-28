from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tasukeru_explainable_patch as epp  # noqa: E402


def valid_candidate(**overrides):
    candidate = {
        "observed_issue": "Ruff F401 observed an unused import.",
        "evidence": {
            "source": "ruff",
            "rule_id": "F401",
            "message": "Unused import os",
        },
        "human_readable_explanation": {
            "summary": "Remove unused import",
            "why_problematic": "Unused imports add noise and can hide real dependencies.",
            "why_fix": "Remove unused import follows from the Ruff F401 evidence.",
        },
        "proposed_fix": "Remove unused import from the affected module.",
        "impact_analysis": {
            "expected_effect": "Reduces lint noise without changing runtime behavior.",
            "side_effects_to_check": ["import was not used for side effects"],
        },
        "validation_plan": [
            "Human reviewer checks the import is unused.",
            "Run ruff or targeted lint before adopting the change.",
        ],
    }
    candidate.update(overrides)
    return candidate


def build_one(candidate):
    payload = epp.build_payload([candidate])
    return payload, payload["all_candidate_records"][0]


def test_as_bool_parses_string_booleans():
    assert epp.as_bool("false") is False
    assert epp.as_bool("true") is True


def test_as_bool_unknown_string_returns_default():
    assert epp.as_bool("maybe") is False
    assert epp.as_bool("maybe", default=True) is True


def test_valid_manual_outline_is_evidence_backed_but_not_diff_validated():
    payload, record = build_one(valid_candidate())

    assert payload["counts"]["valid_proposal_count"] == 1
    assert payload["counts"]["invalid_draft_fix_error_count"] == 0
    assert record["proposal_status"] == epp.VALID_STATUS
    assert record["proposal_kind"] == epp.MANUAL_OUTLINE
    assert record["candidate_patch"]["candidate_diff_generated"] is False
    assert record["candidate_patch"]["unified_diff"] == ""
    assert record["patch_accountability"]["explanation_matches_diff"] is None
    assert record["patch_accountability"]["diff_match_status"] == "not_applicable"
    assert epp.CANDIDATE_DIFF_NOT_GENERATED_ADVISORY_ONLY in record["patch_accountability"]["reason_codes"]
    assert epp.EVIDENCE_BACKED_DRAFT_FIX in record["patch_accountability"]["reason_codes"]


def test_string_false_candidate_diff_generated_uses_manual_outline():
    _, record = build_one(
        valid_candidate(
            candidate_diff_generated="false",
            unified_diff="--- a/example.py\n+++ b/example.py\n@@\n-import os\n",
            explanation_matches_diff="true",
        )
    )

    assert record["proposal_status"] == epp.VALID_STATUS
    assert record["proposal_kind"] == epp.MANUAL_OUTLINE
    assert record["candidate_patch"]["candidate_diff_generated"] is False
    assert record["candidate_patch"]["unified_diff"] == ""
    assert record["patch_accountability"]["explanation_matches_diff"] is None
    assert record["patch_accountability"]["diff_match_status"] == "not_applicable"
    assert epp.FIX_EXPLANATION_DIFF_MISMATCH not in record["patch_accountability"]["reason_codes"]


def test_missing_explanation_invalidates_candidate():
    payload, record = build_one(valid_candidate(human_readable_explanation={}))

    assert payload["counts"]["valid_proposal_count"] == 0
    assert payload["counts"]["invalid_draft_fix_error_count"] == 1
    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_EXPLANATION_MISSING in record["patch_accountability"]["invalid_reason_codes"]


def test_missing_evidence_invalidates_candidate():
    _, record = build_one(valid_candidate(evidence={}))

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_EVIDENCE_MISSING in record["patch_accountability"]["invalid_reason_codes"]


def test_missing_impact_analysis_invalidates_candidate():
    _, record = build_one(valid_candidate(impact_analysis={}))

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_IMPACT_ANALYSIS_MISSING in record["patch_accountability"]["invalid_reason_codes"]


def test_missing_validation_support_invalidates_candidate():
    _, record = build_one(valid_candidate(validation_plan=[], validation_results=[]))

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_VALIDATION_RESULTS_MISSING in record["patch_accountability"]["invalid_reason_codes"]


def test_broken_reasoning_chain_invalidates_candidate():
    _, record = build_one(valid_candidate(reasoning_chain={"observed_issue": "only one link"}))

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_REASONING_CHAIN_BROKEN in record["patch_accountability"]["invalid_reason_codes"]


def test_explanation_proposal_mismatch_invalidates_candidate():
    _, record = build_one(
        valid_candidate(
            human_readable_explanation={
                "summary": "Rotate signing keys",
                "why_problematic": "Key rotation is unrelated here.",
                "why_fix": "Rotate signing keys.",
            },
            proposed_fix="Remove unused import from the affected module.",
            explanation_matches_proposal=False,
        )
    )

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert epp.FIX_EXPLANATION_PROPOSAL_MISMATCH in record["patch_accountability"]["invalid_reason_codes"]


def test_diff_mismatch_invalidates_diff_backed_candidate():
    _, record = build_one(
        valid_candidate(
            candidate_diff_generated=True,
            unified_diff="--- a/example.py\n+++ b/example.py\n@@\n-import os\n",
            explanation_matches_diff=False,
        )
    )

    assert record["proposal_status"] == epp.INVALID_STATUS
    assert record["proposal_kind"] == epp.DIFF_BACKED
    assert epp.FIX_EXPLANATION_DIFF_MISMATCH in record["patch_accountability"]["invalid_reason_codes"]


def test_security_related_suggestion_requires_human_review_reason_code():
    _, record = build_one(valid_candidate(security_related_patch=True))

    assert record["proposal_status"] == epp.VALID_STATUS
    assert record["review_route"] == "HUMAN_REVIEW_REQUIRED"
    assert record["policy"]["human_decision_required"] is True
    assert epp.SECURITY_PATCH_REQUIRES_HUMAN_REVIEW in record["patch_accountability"]["reason_codes"]


def test_string_false_security_related_patch_does_not_add_security_reason_code():
    _, record = build_one(valid_candidate(security_related_patch="false"))

    assert record["proposal_status"] == epp.VALID_STATUS
    assert epp.SECURITY_PATCH_REQUIRES_HUMAN_REVIEW not in record["patch_accountability"]["reason_codes"]


def test_string_false_patch_applied_does_not_invalidate_candidate():
    _, record = build_one(valid_candidate(patch_applied="false"))

    assert record["proposal_status"] == epp.VALID_STATUS
    assert epp.INVALID_DRAFT_FIX_ERROR not in record["patch_accountability"]["reason_codes"]


def test_auto_policy_flags_are_blocked_and_verified():
    payload, record = build_one(valid_candidate())

    assert payload["policy"]["policy_verified"] is True
    assert payload["policy"]["auto_apply_allowed_all_false"] is True
    assert payload["policy"]["auto_commit_allowed_all_false"] is True
    assert payload["policy"]["auto_push_allowed_all_false"] is True
    assert payload["policy"]["auto_pr_creation_allowed_all_false"] is True
    assert payload["policy"]["auto_merge_allowed_all_false"] is True
    assert payload["policy"]["auto_deploy_allowed_all_false"] is True
    assert payload["policy"]["human_decision_required_all_true"] is True
    assert epp.AUTOMATIC_PATCH_APPLICATION_BLOCKED in record["patch_accountability"]["reason_codes"]
    assert epp.AUTOMATIC_DEPLOY_BLOCKED in record["patch_accountability"]["reason_codes"]


def test_invalid_candidates_are_not_counted_as_valid():
    payload = epp.build_payload(
        [
            valid_candidate(),
            valid_candidate(evidence={}),
        ]
    )

    assert payload["counts"]["valid_proposal_count"] == 1
    assert payload["counts"]["invalid_draft_fix_error_count"] == 1
    assert payload["counts"]["invalid_in_valid_count"] == 0
    assert len(payload["proposals"]) == 1
    assert len(payload["invalid_draft_fix_errors"]) == 1
    assert len(payload["all_candidate_records"]) == 2


def test_hash_chain_verification_detects_tampering():
    payload = epp.build_payload([valid_candidate(), valid_candidate(proposal_id="EPP-0002")])
    records = payload["all_candidate_records"]

    assert epp.verify_hash_chain(records)["hash_chain_verified"] is True
    records[0]["evidence"]["message"] = "tampered"
    verification = epp.verify_hash_chain(records)
    assert verification["hash_chain_verified"] is False
    assert verification["errors"]


def test_write_artifacts_reports_counts_policy_hash_and_existence(tmp_path):
    result = epp.write_artifacts(
        [
            valid_candidate(),
            valid_candidate(evidence={}),
        ],
        tmp_path,
    )
    verify = result["verify"]

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    assert result["verify_path"].exists()
    assert verify["valid_proposal_count"] == 1
    assert verify["invalid_candidate_count"] == 1
    assert verify["invalid_in_valid_count"] == 0
    assert verify["verified"] is True
    assert verify["policy_verification"]["policy_verified"] is True
    assert verify["hash_chain_verification"]["hash_chain_verified"] is True
    assert verify["hash_chain_note"] == (
        "Verifies internal chain consistency. Authenticity requires preserving "
        "or comparing the head hash externally."
    )
    assert verify["output_existence_checks"] == {
        "json": True,
        "markdown": True,
        "verify": True,
    }

    data = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert data["counts"]["valid_proposal_count"] == 1
    assert data["counts"]["invalid_draft_fix_error_count"] == 1


def test_cli_smoke_writes_artifacts_and_verified_true(tmp_path):
    input_path = tmp_path / "candidates.json"
    input_path.write_text(json.dumps([valid_candidate()]), encoding="utf-8")

    assert epp.main(["--input", str(input_path), "--out-dir", str(tmp_path)]) == 0

    json_path = tmp_path / "tasukeru_explainable_patch_proposals.json"
    markdown_path = tmp_path / "tasukeru_explainable_patch_proposals.md"
    verify_path = tmp_path / "tasukeru_explainable_patch_proposals_verify.json"
    assert json_path.exists()
    assert markdown_path.exists()
    assert verify_path.exists()

    verify = json.loads(verify_path.read_text(encoding="utf-8"))
    assert verify["verified"] is True
    assert verify["output_existence_checks"] == {
        "json": True,
        "markdown": True,
        "verify": True,
    }
