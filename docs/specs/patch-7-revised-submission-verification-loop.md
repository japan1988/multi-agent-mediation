# Patch 7: Revised submission verification loop

## Status

Patch 7 is specification-only.

It defines a revised submission verification loop for candidates that return after a Patch 6 reasoned return.

It does not implement runtime behavior.

It does not add tests.

It does not integrate with workflow.

It does not execute agents.

It does not repair files.

It does not create pull requests.

It does not merge pull requests.

## Core sentence

Patch 7は「修正する」ではなく、
「修正されたことになっている入力を検証する」。

Patch 7 verifies a revised candidate.

It does not perform the revision.

## Purpose

Patch 7 defines how a pseudo-orchestration mediation layer should verify a revised submission after Patch 6 has returned a case with a `reason_code` and `return_to` target.

Patch 7 exists to:

- verify revised submissions after Patch 6 reasoned return
- confirm whether the previous return reason was resolved
- detect unresolved or partially resolved resubmissions
- preserve unresolved reasons
- avoid false pass-through
- keep final decision authority with a human reviewer

Patch 7 does not perform repair.

Patch 7 does not modify source files.

Patch 7 does not normalize unsafe or contradictory results into safe-looking results.

## Relationship to Patch 6

Patch 6:

- detects contradiction
- assigns `reason_code`
- returns to a logical agent role
- stops

Patch 7:

- receives the Patch 6 return artifact
- receives a revised candidate fixture or artifact
- verifies whether the previous `reason_code` has been resolved
- preserves unresolved reasons
- decides whether the revised candidate may proceed to human review or must remain blocked
- keeps final decision authority with a human reviewer

Patch 7 is a verification loop, not a repair loop.

## Non-goals

Patch 7 does not:

- perform repair
- auto-correct
- modify source files
- commit changes
- push changes
- create pull requests
- merge pull requests
- deploy
- call AI APIs
- call Codex APIs
- call OpenAI APIs
- call Anthropic APIs
- call Gemini APIs
- call Copilot APIs
- call external AI providers
- use API keys
- use GitHub Actions secrets
- launch real agents
- post GitHub comments automatically
- apply fixes automatically
- implement Patch 8
- implement Patch 9
- implement Patch 10

## Inputs

Patch 7 may use these future logical inputs:

| Input | Meaning |
|---|---|
| `patch_6_return_artifact` | The reasoned return artifact produced by Patch 6 |
| `revised_candidate` | A revised candidate fixture or artifact submitted for verification |
| `previous_reason_code` | The Patch 6 reason code that must be resolved |
| `previous_decision` | The Patch 6 decision, such as `BLOCK` or `NEEDS_REVIEW` |
| `previous_return_to` | The Patch 6 logical return target |
| `expected_resolution_evidence` | Evidence that should demonstrate resolution |
| `changed_files_evidence` | Evidence about changed files, if applicable |
| `test_artifact_evidence` | Test or artifact evidence, if applicable |

These inputs are logical artifact concepts only.

Patch 7 does not require live services, external providers, or AI APIs.

## Outputs

Patch 7 may define these future logical outputs:

| Output | Meaning |
|---|---|
| `resolved` | Whether the previous reason was demonstrably resolved |
| `unresolved_reason_codes` | Reasons that remain unresolved |
| `previous_reason_code` | The Patch 6 reason code under verification |
| `verification_result` | Human-readable verification summary |
| `decision` | The Patch 7 decision |
| `reason_code` | The Patch 7 reason code |
| `requires_human_review` | Always true for reviewable outcomes |
| `final_decider` | Must be `human` |
| `performed_repair` | Must be false |
| `source_files_modified` | Must be false |
| `auto_corrected` | Must be false |
| `normalized_to_safe_result` | Must be false |

Patch 7 output is advisory-only.

It must not be treated as automatic approval, automatic application, or permission to merge.

## Decisions

Patch 7 defines these mediation decisions:

| Decision | Meaning |
|---|---|
| `PROCEED_TO_REVIEW` | The previous reason is demonstrably resolved and no new contradiction is introduced; material may proceed to human review |
| `NEEDS_REVIEW` | Evidence is incomplete, ambiguous, or cannot be verified |
| `BLOCK` | The previous reason remains unresolved, a contradiction remains, a new contradiction appears, or prohibited behavior is observed |

Decision rules:

- `PROCEED_TO_REVIEW` may be used only if the previous reason is demonstrably resolved and no new contradiction is introduced.
- `PROCEED_TO_REVIEW` means proceed to human review only; it does not authorize automatic application.
- `NEEDS_REVIEW` must be used if evidence is incomplete, ambiguous, or cannot be verified.
- `BLOCK` must be used if the previous reason remains unresolved.
- `BLOCK` must be used if a contradiction remains.
- `BLOCK` must be used if a new contradiction appears.
- `BLOCK` must be used if prohibited behavior is observed.

## Reason codes

Patch 7 defines these initial reason codes:

| Reason code | Decision | Meaning |
|---|---|---|
| `REVISED_SUBMISSION_RESOLVED` | `PROCEED_TO_REVIEW` | The revised candidate resolves the previous reason and introduces no new contradiction |
| `PREVIOUS_REASON_UNRESOLVED` | `BLOCK` | The previous Patch 6 reason remains unresolved |
| `PARTIAL_RESOLUTION_ONLY` | `NEEDS_REVIEW` | The revised candidate resolves part of the issue but not enough to proceed |
| `RESOLUTION_EVIDENCE_MISSING` | `NEEDS_REVIEW` | Required resolution evidence is missing |
| `NEW_CONTRADICTION_INTRODUCED` | `BLOCK` | The revised candidate introduces a new contradiction |
| `PROHIBITED_REPAIR_BEHAVIOR_OBSERVED` | `BLOCK` | The revised candidate or verifier indicates prohibited repair behavior |
| `SOURCE_MODIFICATION_BY_VERIFIER` | `BLOCK` | The verifier modified source files, which is prohibited |
| `HUMAN_REVIEW_STILL_REQUIRED` | `NEEDS_REVIEW` | Human review remains required even though some evidence is present |

## Future artifact shape

Patch 7 does not implement artifacts yet.

A future implementation may produce a local review artifact with this shape for a resolved candidate:

```json
{
  "patch": 7,
  "mode": "revised_submission_verification",
  "previous_patch": 6,
  "previous_reason_code": "HUMAN_REVIEW_BYPASS",
  "previous_decision": "BLOCK",
  "previous_return_to": {
    "agent_role": "implementation_agent",
    "return_type": "REJECT_AND_REVISE"
  },
  "revised_candidate_id": "candidate-0001",
  "resolved": true,
  "decision": "PROCEED_TO_REVIEW",
  "reason_code": "REVISED_SUBMISSION_RESOLVED",
  "requires_human_review": true,
  "final_decider": "human",
  "performed_repair": false,
  "source_files_modified": false,
  "auto_corrected": false,
  "normalized_to_safe_result": false,
  "prohibited_next_actions": [
    "auto_apply",
    "auto_commit",
    "auto_pr",
    "auto_merge",
    "deploy"
  ],
  "required_next_actions": [
    "preserve evidence",
    "send to human review"
  ]
}
```

A future implementation may produce this shape for an unresolved candidate:

```json
{
  "patch": 7,
  "mode": "revised_submission_verification",
  "previous_patch": 6,
  "previous_reason_code": "HUMAN_REVIEW_BYPASS",
  "resolved": false,
  "decision": "BLOCK",
  "reason_code": "PREVIOUS_REASON_UNRESOLVED",
  "requires_human_review": true,
  "final_decider": "human",
  "performed_repair": false,
  "source_files_modified": false,
  "auto_corrected": false,
  "normalized_to_safe_result": false
}
```

## Future assertion expectations

When Patch 7 is implemented later, tests should assert:

- `performed_repair` must be false
- `source_files_modified` must be false
- `auto_corrected` must be false
- `normalized_to_safe_result` must be false
- `final_decider` must be `human`
- unresolved previous reason must not proceed to review
- missing evidence must not proceed to review
- new contradiction must block
- resolved candidate may proceed only to human review, not automatic application
- verifier must not modify source files
- `PROCEED_TO_REVIEW` must never authorize auto-apply, auto-commit, auto-PR, auto-merge, or deploy

## Future fixture ideas

Patch 7 may use future fixtures such as:

```text
tests/stress/fixtures/revised_submission/
  resolved_human_review_bypass.json
  unresolved_human_review_bypass.json
  partial_resolution_only.json
  missing_resolution_evidence.json
  new_contradiction_introduced.json
  prohibited_repair_behavior_observed.json
  source_modification_by_verifier.json
```

These fixture paths are examples only.

Patch 7 does not create them.

## Relationship to other patches

Patch 6 returns with `reason_code` and `return_to`.

Patch 7 verifies revised submission candidates.

Patch 8 will detect mediation loops.

Patch 9 may recommend logical role rotation.

Patch 10 may checkpoint and hand off unresolved state.

Patch 7 does not implement Patch 8, Patch 9, or Patch 10.

## Safety boundary

Patch 7 remains inside a strict documentation/specification-only boundary.

Allowed:

- documentation/specification only
- define revised submission verification semantics
- define logical artifact shape
- define future assertions
- define future fixtures as text only

Prohibited:

- runtime behavior
- workflow changes
- scripts
- tests
- generated output commits
- AI API calls
- external AI provider calls
- API keys
- secrets
- actual agent execution
- automatic repair
- source file modification by verifier
- auto-fix
- auto-commit-to-main
- auto-PR
- auto-merge
- deploy

## Review checklist

- [ ] Docs/spec-only change
- [ ] Exactly one file added
- [ ] No workflow changes
- [ ] No script changes
- [ ] No test changes
- [ ] No release note changes
- [ ] No generated outputs committed
- [ ] No `analysis_results/` files added
- [ ] No `stress_results/` files added
- [ ] No AI API calls
- [ ] No API keys or secrets
- [ ] No external AI provider calls
- [ ] No runtime external network calls
- [ ] No actual agent execution
- [ ] No auto-fix / auto-commit / auto-PR / auto-merge / deploy
- [ ] Human final decision boundary preserved
