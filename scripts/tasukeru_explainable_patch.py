from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


VALID_STATUS = "EVIDENCE_BACKED_DRAFT_FIX"
INVALID_STATUS = "INVALID_DRAFT_FIX_ERROR"
MANUAL_OUTLINE = "MANUAL_REMEDIATION_OUTLINE"
DIFF_BACKED = "DIFF_BACKED_DRAFT_FIX"

EVIDENCE_BACKED_DRAFT_FIX = "evidence_backed_draft_fix"
INVALID_DRAFT_FIX_ERROR = "invalid_draft_fix_error"
FIX_EXPLANATION_MISSING = "fix_explanation_missing"
FIX_EVIDENCE_MISSING = "fix_evidence_missing"
FIX_IMPACT_ANALYSIS_MISSING = "fix_impact_analysis_missing"
FIX_VALIDATION_RESULTS_MISSING = "fix_validation_results_missing"
FIX_REASONING_CHAIN_BROKEN = "fix_reasoning_chain_broken"
FIX_EXPLANATION_PROPOSAL_MISMATCH = "fix_explanation_proposal_mismatch"
FIX_EXPLANATION_DIFF_MISMATCH = "fix_explanation_diff_mismatch"
CANDIDATE_DIFF_NOT_GENERATED_ADVISORY_ONLY = (
    "candidate_diff_not_generated_advisory_only"
)
SECURITY_PATCH_REQUIRES_HUMAN_REVIEW = "security_patch_requires_human_review"
AUTOMATIC_PATCH_APPLICATION_BLOCKED = "automatic_patch_application_blocked"
AUTOMATIC_COMMIT_BLOCKED = "automatic_commit_blocked"
AUTOMATIC_PUSH_BLOCKED = "automatic_push_blocked"
AUTOMATIC_PR_CREATION_BLOCKED = "automatic_pr_creation_blocked"
AUTOMATIC_MERGE_BLOCKED = "automatic_merge_blocked"
AUTOMATIC_DEPLOY_BLOCKED = "automatic_deploy_blocked"

AUTO_POLICY_FLAGS = (
    "auto_apply_allowed",
    "auto_commit_allowed",
    "auto_push_allowed",
    "auto_pr_creation_allowed",
    "auto_merge_allowed",
    "auto_deploy_allowed",
)

BLOCKED_AUTOMATION_REASON_CODES = (
    AUTOMATIC_PATCH_APPLICATION_BLOCKED,
    AUTOMATIC_COMMIT_BLOCKED,
    AUTOMATIC_PUSH_BLOCKED,
    AUTOMATIC_PR_CREATION_BLOCKED,
    AUTOMATIC_MERGE_BLOCKED,
    AUTOMATIC_DEPLOY_BLOCKED,
)

PROJECT_BOUNDARY_SAFETY_METADATA = {
    "human_review_required": True,
    "automatic_apply": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pr": False,
    "automatic_merge": False,
    "automatic_deploy": False,
    "ai_api_call": False,
    "api_key_required": False,
    "external_ai_provider": None,
    "billable_action": False,
}

REASONING_CHAIN_FIELDS = (
    "observed_issue",
    "evidence",
    "why_this_matters",
    "proposed_fix",
    "why_this_fix",
    "impact_analysis",
    "validation",
    "human_review_required",
    "hash_chain_entry",
)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def has_support_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(has_support_content(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(has_support_content(item) for item in value)
    return True


def support_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(support_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(support_text(item) for item in value)
    return str(value)


def unique_reason_codes(reason_codes: list[str]) -> list[str]:
    return list(dict.fromkeys(reason_codes))


def safety_metadata() -> dict[str, Any]:
    return dict(PROJECT_BOUNDARY_SAFETY_METADATA)


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off", ""}:
            return False
        return default
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return default
    return default


def default_policy() -> dict[str, Any]:
    return {
        "auto_apply_allowed": False,
        "auto_commit_allowed": False,
        "auto_push_allowed": False,
        "auto_pr_creation_allowed": False,
        "auto_merge_allowed": False,
        "auto_deploy_allowed": False,
        "human_decision_required": True,
        "suggestion_only": True,
        "advisory_only": True,
    }


def normalize_policy(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = default_policy()
    if isinstance(policy, dict):
        normalized.update(policy)
    for flag in AUTO_POLICY_FLAGS:
        normalized[flag] = as_bool(normalized.get(flag), default=False)
    normalized["human_decision_required"] = as_bool(
        normalized.get("human_decision_required"),
        default=True,
    )
    normalized["suggestion_only"] = as_bool(
        normalized.get("suggestion_only"),
        default=True,
    )
    normalized["advisory_only"] = as_bool(
        normalized.get("advisory_only"),
        default=True,
    )
    return normalized


def explanation_matches_proposed_fix(
    explanation: dict[str, Any],
    proposed_fix: dict[str, Any],
) -> bool:
    explanation_blob = support_text(explanation).strip().lower()
    proposed_blob = support_text(proposed_fix).strip().lower()
    if not explanation_blob or not proposed_blob:
        return False

    summary = str(explanation.get("summary") or explanation.get("summary_ja") or "")
    why_fix = str(explanation.get("why_fix") or explanation.get("why_fix_ja") or "")
    for direct in (summary.strip().lower(), why_fix.strip().lower()):
        if direct and direct in proposed_blob:
            return True

    explanation_tokens = {
        token
        for token in re.findall(r"[a-z0-9_]{4,}", explanation_blob)
        if token
        not in {
            "this",
            "that",
            "with",
            "from",
            "candidate",
            "proposal",
            "evidence",
            "because",
        }
    }
    proposed_tokens = set(re.findall(r"[a-z0-9_]{4,}", proposed_blob))
    if not explanation_tokens or not proposed_tokens:
        return False

    overlap = len(explanation_tokens & proposed_tokens)
    return overlap / max(1, min(len(explanation_tokens), len(proposed_tokens))) >= 0.2


def build_reasoning_chain(
    *,
    observed_issue: Any,
    evidence: dict[str, Any],
    explanation: dict[str, Any],
    proposed_fix: dict[str, Any],
    impact_analysis: dict[str, Any],
    validation_plan: list[Any],
    validation_results: list[Any],
) -> dict[str, Any]:
    return {
        "observed_issue": observed_issue,
        "evidence": evidence,
        "why_this_matters": explanation.get("why_problematic")
        or explanation.get("why_problematic_ja")
        or explanation.get("why_this_matters")
        or "",
        "proposed_fix": proposed_fix,
        "why_this_fix": explanation.get("why_fix")
        or explanation.get("why_fix_ja")
        or "",
        "impact_analysis": impact_analysis,
        "validation": {
            "validation_plan": validation_plan,
            "validation_results": validation_results,
        },
        "human_review_required": True,
        "hash_chain_entry": "integrity.chain_hash",
    }


def reasoning_chain_complete(reasoning_chain: dict[str, Any]) -> bool:
    if not isinstance(reasoning_chain, dict):
        return False
    if reasoning_chain.get("human_review_required") is not True:
        return False
    return all(has_support_content(reasoning_chain.get(field)) for field in REASONING_CHAIN_FIELDS)


def build_validation_plan(candidate: dict[str, Any]) -> list[str]:
    existing = candidate.get("validation_plan")
    if has_support_content(existing):
        return list(existing) if isinstance(existing, list) else [str(existing)]
    return []


def normalize_candidate(raw_candidate: dict[str, Any], index: int) -> dict[str, Any]:
    evidence = raw_candidate.get("evidence") or {}
    if not isinstance(evidence, dict):
        evidence = {"value": evidence}

    explanation = (
        raw_candidate.get("human_readable_explanation")
        or raw_candidate.get("explanation")
        or {}
    )
    if not isinstance(explanation, dict):
        explanation = {"summary": str(explanation)}

    impact_analysis = raw_candidate.get("impact_analysis") or {}
    if not isinstance(impact_analysis, dict):
        impact_analysis = {"value": impact_analysis}

    candidate_patch = raw_candidate.get("candidate_patch") or {}
    if not isinstance(candidate_patch, dict):
        candidate_patch = {"proposed_fix": str(candidate_patch)}

    proposed_fix = (
        raw_candidate.get("proposed_fix")
        or raw_candidate.get("suggestion")
        or candidate_patch.get("proposed_fix")
        or candidate_patch.get("manual_remediation_outline")
        or ""
    )
    manual_outline = (
        raw_candidate.get("manual_remediation_outline")
        or candidate_patch.get("manual_remediation_outline")
        or proposed_fix
    )
    candidate_diff_generated_value = raw_candidate.get("candidate_diff_generated")
    if candidate_diff_generated_value is None:
        candidate_diff_generated_value = candidate_patch.get("candidate_diff_generated")
    candidate_diff_generated = as_bool(candidate_diff_generated_value)
    unified_diff = str(raw_candidate.get("unified_diff") or candidate_patch.get("unified_diff") or "")
    if not candidate_diff_generated:
        unified_diff = ""
    candidate_patch = {
        **candidate_patch,
        "kind": DIFF_BACKED if candidate_diff_generated else MANUAL_OUTLINE,
        "proposed_fix": proposed_fix,
        "manual_remediation_outline": manual_outline,
        "candidate_diff_generated": candidate_diff_generated,
        "unified_diff": unified_diff,
    }

    validation_plan = build_validation_plan(raw_candidate)
    validation_results = raw_candidate.get("validation_results") or []
    if not isinstance(validation_results, list):
        validation_results = [validation_results]

    observed_issue = (
        raw_candidate.get("observed_issue")
        or evidence.get("observed_issue")
        or evidence.get("message")
        or raw_candidate.get("message")
        or ""
    )
    reasoning_chain = raw_candidate.get("reasoning_chain")
    if not isinstance(reasoning_chain, dict):
        reasoning_chain = build_reasoning_chain(
            observed_issue=observed_issue,
            evidence=evidence,
            explanation=explanation,
            proposed_fix=candidate_patch,
            impact_analysis=impact_analysis,
            validation_plan=validation_plan,
            validation_results=validation_results,
        )

    policy = normalize_policy(raw_candidate.get("policy"))
    explicit_diff_match = raw_candidate.get("explanation_matches_diff")
    explanation_matches_diff = (
        as_bool(explicit_diff_match) if candidate_diff_generated else None
    )
    explicit_proposal_match = raw_candidate.get("explanation_matches_proposal")
    explanation_matches_proposal = (
        as_bool(explicit_proposal_match)
        if explicit_proposal_match is not None
        else explanation_matches_proposed_fix(explanation, candidate_patch)
    )

    source_entry = raw_candidate.get("source_entry")
    if not isinstance(source_entry, dict):
        source_entry = {
            "candidate_index": index,
            "source": raw_candidate.get("source", "tasukeru_explainable_patch"),
            "reason_code": raw_candidate.get("reason_code", ""),
            "rule_id": raw_candidate.get("rule_id", ""),
            "file": raw_candidate.get("file", ""),
            "line": raw_candidate.get("line"),
        }

    return {
        "proposal_id": raw_candidate.get("proposal_id") or f"EPP-{index:04d}",
        "source_entry": source_entry,
        "evidence": evidence,
        "human_readable_explanation": explanation,
        "impact_analysis": impact_analysis,
        "candidate_patch": candidate_patch,
        "validation_plan": validation_plan,
        "validation_results": validation_results,
        "reasoning_chain": reasoning_chain,
        "policy": policy,
        "candidate_diff_generated": candidate_diff_generated,
        "explanation_matches_diff": explanation_matches_diff,
        "explanation_matches_proposal": explanation_matches_proposal,
        "security_related_patch": as_bool(raw_candidate.get("security_related_patch")),
        "patch_applied": as_bool(raw_candidate.get("patch_applied")),
    }


def check_candidate_support(candidate: dict[str, Any]) -> dict[str, Any]:
    has_human_readable_explanation = has_support_content(
        candidate["human_readable_explanation"]
    )
    has_evidence = has_support_content(candidate["evidence"])
    has_impact_analysis = has_support_content(candidate["impact_analysis"])
    has_validation_plan = has_support_content(candidate["validation_plan"])
    has_validation_results = has_support_content(candidate["validation_results"])
    has_validation_support = has_validation_plan or has_validation_results
    chain_complete = reasoning_chain_complete(candidate["reasoning_chain"])
    proposal_match = as_bool(candidate["explanation_matches_proposal"])

    candidate_diff_generated = as_bool(candidate["candidate_diff_generated"])
    explanation_matches_diff = candidate["explanation_matches_diff"]
    diff_support_ok = (
        explanation_matches_diff is True
        if candidate_diff_generated
        else explanation_matches_diff is None
    )

    policy = candidate["policy"]
    external_state_changes_blocked = all(
        policy.get(flag) is False for flag in AUTO_POLICY_FLAGS
    )
    human_decision_required = policy.get("human_decision_required") is True
    patch_applied = as_bool(candidate["patch_applied"])

    supported = all(
        [
            has_human_readable_explanation,
            has_evidence,
            has_impact_analysis,
            has_validation_support,
            chain_complete,
            proposal_match,
            diff_support_ok,
            external_state_changes_blocked,
            human_decision_required,
            not patch_applied,
        ]
    )

    reason_codes = [
        EVIDENCE_BACKED_DRAFT_FIX if supported else INVALID_DRAFT_FIX_ERROR,
    ]
    if not has_human_readable_explanation:
        reason_codes.append(FIX_EXPLANATION_MISSING)
    if not has_evidence:
        reason_codes.append(FIX_EVIDENCE_MISSING)
    if not has_impact_analysis:
        reason_codes.append(FIX_IMPACT_ANALYSIS_MISSING)
    if not has_validation_support:
        reason_codes.append(FIX_VALIDATION_RESULTS_MISSING)
    if not chain_complete:
        reason_codes.append(FIX_REASONING_CHAIN_BROKEN)
    if not proposal_match:
        reason_codes.append(FIX_EXPLANATION_PROPOSAL_MISMATCH)
    if candidate_diff_generated and explanation_matches_diff is not True:
        reason_codes.append(FIX_EXPLANATION_DIFF_MISMATCH)
    if not candidate_diff_generated:
        reason_codes.append(CANDIDATE_DIFF_NOT_GENERATED_ADVISORY_ONLY)
    if candidate["security_related_patch"]:
        reason_codes.append(SECURITY_PATCH_REQUIRES_HUMAN_REVIEW)
    reason_codes.extend(BLOCKED_AUTOMATION_REASON_CODES)
    reason_codes = unique_reason_codes(reason_codes)

    return {
        "is_supported": supported,
        "proposal_status": VALID_STATUS if supported else INVALID_STATUS,
        "proposal_kind": DIFF_BACKED if candidate_diff_generated else MANUAL_OUTLINE,
        "has_human_readable_explanation": has_human_readable_explanation,
        "has_evidence": has_evidence,
        "has_impact_analysis": has_impact_analysis,
        "has_validation_plan": has_validation_plan,
        "has_validation_results": has_validation_results,
        "has_validation_support": has_validation_support,
        "reasoning_chain_complete": chain_complete,
        "explanation_matches_proposal": proposal_match,
        "explanation_matches_diff": explanation_matches_diff,
        "diff_match_status": "matched"
        if candidate_diff_generated and explanation_matches_diff is True
        else "mismatch"
        if candidate_diff_generated
        else "not_applicable",
        "diff_support_ok": diff_support_ok,
        "external_state_changes_blocked": external_state_changes_blocked,
        "human_decision_required": human_decision_required,
        "reason_codes": reason_codes,
        "invalid_reason_codes": [
            code
            for code in reason_codes
            if code == INVALID_DRAFT_FIX_ERROR or code.startswith("fix_")
        ],
    }


def build_proposal_record(raw_candidate: dict[str, Any], index: int) -> dict[str, Any]:
    candidate = normalize_candidate(raw_candidate, index)
    support = check_candidate_support(candidate)
    record = {
        "proposal_id": candidate["proposal_id"],
        "proposal_status": support["proposal_status"],
        "status": support["proposal_status"],
        "proposal_kind": support["proposal_kind"],
        "review_route": "HUMAN_REVIEW_REQUIRED",
        "source_entry": candidate["source_entry"],
        "evidence": candidate["evidence"],
        "human_readable_explanation": candidate["human_readable_explanation"],
        "impact_analysis": candidate["impact_analysis"],
        "candidate_patch": candidate["candidate_patch"],
        "validation_plan": candidate["validation_plan"],
        "validation_results": candidate["validation_results"],
        "reasoning_chain": candidate["reasoning_chain"],
        "policy": candidate["policy"],
        "patch_accountability": {
            "security_related_patch": candidate["security_related_patch"],
            "patch_applied": candidate["patch_applied"],
            **support,
        },
    }
    return record


def attach_hash_chain(records: list[dict[str, Any]]) -> dict[str, Any]:
    previous_hash = ""
    for record in records:
        validation = {
            "validation_plan": record.get("validation_plan", []),
            "validation_results": record.get("validation_results", []),
        }
        core_record = {
            key: value
            for key, value in record.items()
            if key not in {"integrity", "proposal_hash"}
        }
        proposal_hash = canonical_hash(core_record)
        integrity = {
            "source_entry_hash": canonical_hash(record.get("source_entry", {})),
            "evidence_hash": canonical_hash(record.get("evidence", {})),
            "explanation_hash": canonical_hash(
                record.get("human_readable_explanation", {})
            ),
            "proposed_fix_hash": canonical_hash(record.get("candidate_patch", {})),
            "impact_analysis_hash": canonical_hash(record.get("impact_analysis", {})),
            "validation_hash": canonical_hash(validation),
            "policy_hash": canonical_hash(record.get("policy", {})),
            "proposal_hash": proposal_hash,
            "previous_hash": previous_hash,
            "chain_hash": canonical_hash(
                {
                    "previous_hash": previous_hash,
                    "proposal_hash": proposal_hash,
                }
            ),
        }
        record["proposal_hash"] = proposal_hash
        record["integrity"] = integrity
        previous_hash = integrity["chain_hash"]
    return {
        "hash_chain_verified": True,
        "head_hash": previous_hash,
        "record_count": len(records),
    }


def verify_hash_chain(records: list[dict[str, Any]]) -> dict[str, Any]:
    previous_hash = ""
    errors: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        integrity = record.get("integrity", {})
        if not isinstance(integrity, dict):
            errors.append({"index": index, "reason": "integrity_missing"})
            integrity = {}
        validation = {
            "validation_plan": record.get("validation_plan", []),
            "validation_results": record.get("validation_results", []),
        }
        core_record = {
            key: value
            for key, value in record.items()
            if key not in {"integrity", "proposal_hash"}
        }
        expected = {
            "source_entry_hash": canonical_hash(record.get("source_entry", {})),
            "evidence_hash": canonical_hash(record.get("evidence", {})),
            "explanation_hash": canonical_hash(
                record.get("human_readable_explanation", {})
            ),
            "proposed_fix_hash": canonical_hash(record.get("candidate_patch", {})),
            "impact_analysis_hash": canonical_hash(record.get("impact_analysis", {})),
            "validation_hash": canonical_hash(validation),
            "policy_hash": canonical_hash(record.get("policy", {})),
            "proposal_hash": canonical_hash(core_record),
            "previous_hash": previous_hash,
        }
        expected["chain_hash"] = canonical_hash(
            {
                "previous_hash": previous_hash,
                "proposal_hash": expected["proposal_hash"],
            }
        )
        for field, expected_value in expected.items():
            if integrity.get(field) != expected_value:
                errors.append(
                    {
                        "index": index,
                        "proposal_id": record.get("proposal_id"),
                        "field": field,
                        "reason": "hash_chain_mismatch",
                        "expected": expected_value,
                        "actual": integrity.get(field),
                    }
                )
        if record.get("proposal_hash") != expected["proposal_hash"]:
            errors.append(
                {
                    "index": index,
                    "proposal_id": record.get("proposal_id"),
                    "field": "proposal_hash",
                    "reason": "proposal_hash_field_mismatch",
                    "expected": expected["proposal_hash"],
                    "actual": record.get("proposal_hash"),
                }
            )
        previous_hash = str(integrity.get("chain_hash") or expected["chain_hash"])
    return {
        "hash_chain_verified": not errors,
        "head_hash": previous_hash,
        "record_count": len(records),
        "errors": errors,
    }


def build_payload(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    records = [
        build_proposal_record(candidate, index)
        for index, candidate in enumerate(candidates, start=1)
    ]
    chain_summary = attach_hash_chain(records)
    chain_verification = verify_hash_chain(records)
    valid = [record for record in records if record["proposal_status"] == VALID_STATUS]
    invalid = [
        record for record in records if record["proposal_status"] == INVALID_STATUS
    ]
    invalid_in_valid_count = sum(
        1 for record in valid if record.get("proposal_status") != VALID_STATUS
    )
    invalid_reason_code_counts: dict[str, int] = {}
    for record in invalid:
        for code in record["patch_accountability"].get("invalid_reason_codes", []):
            invalid_reason_code_counts[code] = invalid_reason_code_counts.get(code, 0) + 1

    auto_policy = {
        f"{flag}_all_false": all(
            record["policy"].get(flag) is False for record in records
        )
        for flag in AUTO_POLICY_FLAGS
    }
    human_decision_required_all_true = all(
        record["policy"].get("human_decision_required") is True for record in records
    )
    policy_verified = all(auto_policy.values()) and human_decision_required_all_true

    return {
        "schema_version": "tasukeru-explainable-patch-v1",
        "status": "ADVISORY_ONLY_DRAFT",
        "policy_rule": (
            "A fix proposal that cannot explain why this fix follows from this "
            "evidence is not a valid proposal."
        ),
        "safety_metadata": safety_metadata(),
        "counts": {
            "total_candidates": len(records),
            "proposal_count": len(valid),
            "valid_proposal_count": len(valid),
            "invalid_draft_fix_error_count": len(invalid),
            "invalid_in_valid_count": invalid_in_valid_count,
            "support_complete_count": len(valid),
            "support_incomplete_count": len(invalid),
            "invalid_reason_code_counts": invalid_reason_code_counts,
        },
        "hash_chain": chain_summary
        | {
            "hash_chain_verified": chain_verification["hash_chain_verified"],
            "verification_error_count": len(chain_verification["errors"]),
        },
        "policy": {
            "advisory_only": True,
            "auto_apply_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_pr_creation_allowed": False,
            "auto_merge_allowed": False,
            "auto_deploy_allowed": False,
            "human_decision_required": True,
            "policy_verified": policy_verified,
            **auto_policy,
            "human_decision_required_all_true": human_decision_required_all_true,
        },
        "proposals": valid,
        "invalid_draft_fix_errors": invalid,
        "all_candidate_records": records,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    safety = payload["safety_metadata"]
    lines = [
        "# Tasukeru Explainable Patch Proposals",
        "",
        "This artifact is advisory-only. It does not apply fixes, commit, push, create PRs, merge, or deploy.",
        "",
        "## Safety Boundary",
        "",
        f"- Human review required: `{json.dumps(safety['human_review_required'])}`",
        f"- Automatic apply: `{json.dumps(safety['automatic_apply'])}`",
        f"- Automatic commit: `{json.dumps(safety['automatic_commit'])}`",
        f"- Automatic push: `{json.dumps(safety['automatic_push'])}`",
        f"- Automatic PR: `{json.dumps(safety['automatic_pr'])}`",
        f"- Automatic merge: `{json.dumps(safety['automatic_merge'])}`",
        f"- Automatic deploy: `{json.dumps(safety['automatic_deploy'])}`",
        f"- AI API call: `{json.dumps(safety['ai_api_call'])}`",
        f"- API key required: `{json.dumps(safety['api_key_required'])}`",
        f"- External AI provider: `{json.dumps(safety['external_ai_provider'])}`",
        f"- Billable action: `{json.dumps(safety['billable_action'])}`",
        "",
        "## Counts",
        "",
        f"- Total candidates: `{payload['counts']['total_candidates']}`",
        f"- Valid evidence-backed draft fixes: `{payload['counts']['valid_proposal_count']}`",
        f"- Invalid draft fix errors: `{payload['counts']['invalid_draft_fix_error_count']}`",
        f"- Hash chain verified: `{payload['hash_chain']['hash_chain_verified']}`",
        "- Auto apply / commit / push / PR / merge / deploy: `false`",
        "- Human decision required: `true`",
        "",
        "## Valid Evidence-Backed Draft Fixes",
        "",
    ]
    if not payload["proposals"]:
        lines.append("No valid evidence-backed draft fixes were generated.")
    for proposal in payload["proposals"]:
        lines.extend(
            [
                f"- **{proposal['proposal_status']}** `{proposal['proposal_id']}`",
                f"  - Kind: `{proposal['proposal_kind']}`",
                f"  - Reason codes: `{proposal['patch_accountability']['reason_codes']}`",
                f"  - Chain hash: `{proposal['integrity']['chain_hash']}`",
            ]
        )

    lines.extend(["", "## Invalid Draft Fix Errors", ""])
    if not payload["invalid_draft_fix_errors"]:
        lines.append("No invalid draft fix errors were produced.")
    for proposal in payload["invalid_draft_fix_errors"]:
        lines.extend(
            [
                f"- **{proposal['proposal_status']}** `{proposal['proposal_id']}`",
                f"  - Rejected reason codes: `{proposal['patch_accountability']['invalid_reason_codes']}`",
                f"  - All reason codes: `{proposal['patch_accountability']['reason_codes']}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifacts(candidates: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(candidates)
    json_path = output_dir / "tasukeru_explainable_patch_proposals.json"
    md_path = output_dir / "tasukeru_explainable_patch_proposals.md"
    verify_path = output_dir / "tasukeru_explainable_patch_proposals_verify.json"

    write_json(json_path, payload)
    write_markdown(md_path, payload)

    output_existence_checks = {
        "json": json_path.exists(),
        "markdown": md_path.exists(),
        "verify": False,
    }
    base_verified = (
        payload["policy"]["policy_verified"]
        and payload["hash_chain"]["hash_chain_verified"]
        and payload["counts"]["invalid_in_valid_count"] == 0
    )
    verify_payload = {
        "schema_version": "tasukeru-explainable-patch-verify-v1",
        "verified": False,
        "valid_proposal_count": payload["counts"]["valid_proposal_count"],
        "invalid_candidate_count": payload["counts"]["invalid_draft_fix_error_count"],
        "invalid_draft_fix_error_count": payload["counts"]["invalid_draft_fix_error_count"],
        "invalid_in_valid_count": payload["counts"]["invalid_in_valid_count"],
        "policy_verification": payload["policy"],
        "hash_chain_verification": payload["hash_chain"],
        "safety_metadata": payload["safety_metadata"],
        "hash_chain_note": (
            "Verifies internal chain consistency. Authenticity requires preserving "
            "or comparing the head hash externally."
        ),
        "output_existence_checks": output_existence_checks,
        "artifacts": {
            "json": str(json_path),
            "markdown": str(md_path),
            "verify": str(verify_path),
        },
    }
    write_json(verify_path, verify_payload)
    output_existence_checks["verify"] = verify_path.exists()
    verify_payload["output_existence_checks"] = output_existence_checks
    verify_payload["verified"] = base_verified and all(output_existence_checks.values())
    write_json(verify_path, verify_payload)
    return {
        "payload": payload,
        "verify": verify_payload,
        "json_path": json_path,
        "markdown_path": md_path,
        "verify_path": verify_path,
    }


def load_candidates(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("candidates", "entries", "all_candidate_records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("Input JSON must contain a list of proposal candidates.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Tasukeru explainable patch proposal artifacts.")
    parser.add_argument("--input", type=Path, required=True, help="JSON file containing proposal candidates.")
    parser.add_argument("--out-dir", type=Path, default=Path("."), help="Directory for generated artifacts.")
    args = parser.parse_args(argv)
    write_artifacts(load_candidates(args.input), args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
