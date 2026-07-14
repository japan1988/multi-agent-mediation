# Patch 10: Mediation checkpoint handoff

## Status

Patch 10 is specification-only.

It does not implement runtime behavior.

It does not add tests.

It does not integrate with workflow.

It does not execute agents.

It does not call AI APIs.

It does not repair files.

It does not create or modify pull requests.

It does not merge.

It does not deploy.

It only defines checkpoint and handoff semantics for future implementation.

## Core sentence

Patch 10は「エージェントを引き継ぐ」のではなく、  
「未解決の調停状態をcheckpointとして保存し、次のlogical roleへ渡す」。

Checkpoint means preservation of mediation state.

Handoff means passing that preserved state to the next logical role.

## Purpose

Patch 10 exists to:

- preserve where mediation stopped
- preserve why mediation stopped
- preserve unresolved reason codes
- preserve completed checks
- preserve failed checks
- preserve loop evidence
- preserve role-rotation evidence
- preserve supporting evidence hashes
- recommend the next logical role
- prevent repeated re-checking of already completed work
- prevent loss of unresolved state
- provide human-readable and machine-readable handoff material
- keep human final decision authority

Patch 10 is a checkpoint and handoff specification.

Patch 10 is not an executor.

Patch 10 is not a repair mechanism.

Patch 10 is not an automatic resume mechanism.

Patch 10 does not launch the next logical role.

Patch 10 does not apply any checkpoint automatically.

Patch 10 does not authorize merge, deploy, or external action.

## Checkpoint

Checkpoint means:

- saved mediation state
- record of completed checks
- record of unresolved issues
- record of why processing stopped
- record of evidence hashes
- record of previous and recommended next logical role
- record of prohibited next actions

## Handoff

Handoff means:

- the next logical role may read the checkpoint
- previously completed checks should not be repeated unnecessarily
- unresolved reason codes remain visible
- evidence remains traceable
- human review remains required
- no real agent is launched

チェックポイント = 調停状態の保存  
引き継ぎ = チェックポイントを次のロールへ渡すこと

## Relationship to Patch 6, Patch 7, Patch 8, and Patch 9

Patch 6:

- detects contradiction
- assigns reason code
- returns to a logical role
- stops

Patch 7:

- verifies revised submissions
- does not repair

Patch 8:

- detects mediation loops
- blocks or escalates unresolved loop states

Patch 9:

- recommends logical role rotation
- escalates to review agent, policy owner, or human reviewer
- does not execute the recommended role

Patch 10:

- preserves unresolved mediation state
- records the current checkpoint
- records the recommended next role
- creates handoff material for human review
- does not launch or execute the next role

Patch 10 closes the initial pseudo-orchestration specification sequence.

Patch 10 does not implement external verification, provenance attestation, or a verifier library.

Those remain future work.

## Logical roles

| Logical role | Meaning |
|---|---|
| `implementation_agent` | Logical role that prepares or revises candidate material |
| `review_agent` | Logical role that independently reviews unresolved issues |
| `policy_owner` | Logical role that decides policy or boundary questions |
| `human_reviewer` | Final human decision role |

These are labels only.

They do not launch real agents.

They do not call Codex.

They do not call OpenAI.

They do not trigger workflow jobs.

They do not post GitHub comments.

They do not create issues or pull requests.

## Inputs

Patch 10 may use these future logical inputs:

| Input | Meaning |
|---|---|
| `patch_6_return_artifact` | Patch 6 reasoned return state |
| `patch_7_verification_artifact` | Patch 7 revised-submission verification state |
| `patch_8_loop_guard_artifact` | Patch 8 loop-detection state |
| `patch_9_rotation_artifact` | Patch 9 logical role-rotation recommendation |
| `mediation_history` | Ordered mediation events |
| `current_patch_stage` | Current mediation stage |
| `previous_agent_role` | Prior logical role |
| `next_recommended_agent_role` | Advisory next logical role |
| `decision` | Current mediation decision |
| `reason_code` | Primary reason code |
| `unresolved_reason_codes` | Reasons still unresolved |
| `completed_checks` | Checks already completed |
| `failed_checks` | Checks that failed |
| `attempt_count` | Total attempts |
| `role_attempt_counts` | Attempts by logical role |
| `loop_detected` | Whether a mediation loop was detected |
| `loop_type` | Detected loop type |
| `candidate_hashes` | Stable hashes of candidate artifacts |
| `evidence_hashes` | Stable hashes of supporting evidence |
| `checkpoint_parent_id` | Prior checkpoint identifier, if any |
| `handoff_reason` | Reason for creating a handoff |
| `max_attempts` | Maximum allowed attempts |

Inputs are logical artifact concepts only.

No live service, real agent, external AI provider, or AI API is required.

## Checkpoint fields

Patch 10 defines this future checkpoint shape:

| Field | Requirement |
|---|---|
| `checkpoint_id` | Required stable identifier |
| `checkpoint_parent_id` | Optional prior checkpoint identifier |
| `patch` | Must be `10` |
| `mode` | Must be `mediation_checkpoint_handoff` |
| `current_patch_stage` | Required |
| `previous_agent_role` | Required when available |
| `next_recommended_agent_role` | Advisory-only |
| `decision` | Required |
| `reason_code` | Required |
| `unresolved_reason_codes` | Required list |
| `completed_checks` | Required list |
| `failed_checks` | Required list |
| `attempt_count` | Required non-negative integer |
| `role_attempt_counts` | Required object |
| `loop_detected` | Required boolean |
| `loop_type` | Required when a loop is detected |
| `candidate_hashes` | Required list or object |
| `evidence_hashes` | Required list or object |
| `handoff_required` | Required boolean |
| `handoff_reason` | Required when handoff is true |
| `requires_human_review` | Must be true for unresolved states |
| `final_decider` | Must be `human` |
| `auto_corrected` | Must be false |
| `source_files_modified` | Must be false |
| `normalized_to_safe_result` | Must be false |
| `real_agent_executed` | Must be false |
| `github_comment_posted` | Must be false |
| `pull_request_created` | Must be false |
| `checkpoint_applied_automatically` | Must be false |
| `handoff_executed_automatically` | Must be false |

## Decisions

Patch 10 defines these decisions:

| Decision | Meaning |
|---|---|
| `CHECKPOINT_CREATED` | A valid checkpoint was created for review |
| `HANDOFF_RECOMMENDED` | The checkpoint should be reviewed by the recommended logical role |
| `NEEDS_HUMAN_DECISION` | Human decision is required before any continuation |
| `BLOCK` | Unsafe, contradictory, incomplete, or prohibited handoff state must stop |

Rules:

- `CHECKPOINT_CREATED` does not mean processing resumed.
- `HANDOFF_RECOMMENDED` is advisory-only.
- `NEEDS_HUMAN_DECISION` must be used when final human judgment is required.
- `BLOCK` must be used when checkpoint integrity is invalid, required evidence is missing, or prohibited automation is observed.
- No decision may authorize automatic resume.
- No decision may authorize source modification.
- No decision may authorize real agent execution.
- No decision may authorize PR creation, merge, deploy, or external action.

## Initial reason codes

| Reason code | Decision | Meaning |
|---|---|---|
| `CHECKPOINT_STATE_PRESERVED` | `CHECKPOINT_CREATED` | Mediation state was preserved successfully |
| `HANDOFF_TO_REVIEW_AGENT_RECOMMENDED` | `HANDOFF_RECOMMENDED` | Unresolved state should be reviewed by `review_agent` |
| `HANDOFF_TO_POLICY_OWNER_RECOMMENDED` | `HANDOFF_RECOMMENDED` | Policy or boundary issue should be reviewed by `policy_owner` |
| `HANDOFF_TO_HUMAN_REVIEWER_REQUIRED` | `NEEDS_HUMAN_DECISION` | Final human review is required |
| `UNRESOLVED_REASON_CODES_PRESENT` | `NEEDS_HUMAN_DECISION` | One or more reason codes remain unresolved |
| `CHECKPOINT_EVIDENCE_INCOMPLETE` | `BLOCK` | Required evidence is missing or incomplete |
| `CHECKPOINT_HASH_MISMATCH` | `BLOCK` | Recorded hashes do not match available evidence |
| `CHECKPOINT_PARENT_MISMATCH` | `BLOCK` | Parent checkpoint lineage is inconsistent |
| `PROHIBITED_HANDOFF_BEHAVIOR_OBSERVED` | `BLOCK` | Handoff attempted prohibited automation |
| `AUTOMATIC_RESUME_ATTEMPTED` | `BLOCK` | A checkpoint was used to resume automatically |
| `REAL_AGENT_EXECUTION_ATTEMPTED` | `BLOCK` | A real agent launch was attempted |
| `HUMAN_FINAL_DECISION_REQUIRED` | `NEEDS_HUMAN_DECISION` | Human final decision remains required |

## Checkpoint integrity

Checkpoint integrity requires:

- checkpoint IDs must be stable and deterministic when possible
- evidence hashes must be preserved
- candidate hashes must not be silently changed
- unresolved reasons must not be removed without evidence
- failed checks must not be converted to passed checks automatically
- prior checkpoint lineage must remain traceable
- contradictory state must remain contradictory
- incomplete state must not be normalized into a safe-looking checkpoint
- checkpoint creation must not modify source files
- checkpoint creation must not trigger execution

矛盾をcheckpointで隠してはならない。  
未解決状態を「解決済み」に変換してはならない。

## Handoff policy

Patch 10 defines this initial advisory handoff policy:

| Condition | Recommended next role | Reason code |
|---|---|---|
| Implementation issue remains unresolved | `review_agent` | `HANDOFF_TO_REVIEW_AGENT_RECOMMENDED` |
| Review cannot resolve policy or boundary issue | `policy_owner` | `HANDOFF_TO_POLICY_OWNER_RECOMMENDED` |
| Policy owner cannot resolve issue | `human_reviewer` | `HANDOFF_TO_HUMAN_REVIEWER_REQUIRED` |
| Maximum attempts reached | `human_reviewer` | `HUMAN_FINAL_DECISION_REQUIRED` |
| Evidence is incomplete | none | `CHECKPOINT_EVIDENCE_INCOMPLETE` |
| Hash or lineage mismatch exists | none | `CHECKPOINT_HASH_MISMATCH` or `CHECKPOINT_PARENT_MISMATCH` |
| Prohibited automation is observed | none | `PROHIBITED_HANDOFF_BEHAVIOR_OBSERVED` |

`human_reviewer` is terminal.

Handoff recommendations do not dispatch work.

Handoff recommendations do not start agents.

Handoff recommendations do not authorize continuation.

Handoff recommendations require human review.

## Future artifact shape

Patch 10 does not implement artifacts yet.

A future implementation may produce this advisory-only example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "checkpoint_id": "checkpoint-0003",
  "checkpoint_parent_id": "checkpoint-0002",
  "handoff_required": true,
  "handoff_reason": "AGENT_ROTATION_REQUIRED",
  "current_patch_stage": "Patch_9",
  "previous_agent_role": "implementation_agent",
  "next_recommended_agent_role": "review_agent",
  "decision": "HANDOFF_RECOMMENDED",
  "reason_code": "HANDOFF_TO_REVIEW_AGENT_RECOMMENDED",
  "unresolved_reason_codes": [
    "HUMAN_REVIEW_BYPASS"
  ],
  "completed_checks": [
    "contradiction_detection",
    "reasoned_return",
    "revised_submission_verification",
    "mediation_loop_guard",
    "agent_rotation_escalation"
  ],
  "failed_checks": [
    "revised_submission_resolution"
  ],
  "attempt_count": 3,
  "role_attempt_counts": {
    "implementation_agent": 3
  },
  "loop_detected": true,
  "loop_type": "SAME_AGENT_RETURN_LOOP",
  "candidate_hashes": {
    "revised_candidate": "sha256:example-candidate-hash"
  },
  "evidence_hashes": {
    "patch_6_return": "sha256:example-patch6-hash",
    "patch_7_verification": "sha256:example-patch7-hash",
    "patch_8_loop_guard": "sha256:example-patch8-hash",
    "patch_9_rotation": "sha256:example-patch9-hash"
  },
  "requires_human_review": true,
  "final_decider": "human",
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false,
  "real_agent_executed": false,
  "github_comment_posted": false,
  "pull_request_created": false,
  "checkpoint_applied_automatically": false,
  "handoff_executed_automatically": false,
  "prohibited_next_actions": [
    "launch_real_agent",
    "call_ai_api",
    "auto_resume",
    "auto_fix",
    "auto_commit",
    "auto_pr",
    "auto_merge",
    "deploy"
  ],
  "recommended_human_next_actions": [
    "review checkpoint integrity",
    "review unresolved reason codes",
    "review evidence hashes",
    "decide whether to continue with review_agent"
  ]
}
```

Checkpoint created without handoff example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "checkpoint_id": "checkpoint-0001",
  "checkpoint_parent_id": null,
  "handoff_required": false,
  "decision": "CHECKPOINT_CREATED",
  "reason_code": "CHECKPOINT_STATE_PRESERVED",
  "requires_human_review": true,
  "final_decider": "human",
  "checkpoint_applied_automatically": false,
  "handoff_executed_automatically": false
}
```

Handoff to `policy_owner` example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "handoff_required": true,
  "next_recommended_agent_role": "policy_owner",
  "decision": "HANDOFF_RECOMMENDED",
  "reason_code": "HANDOFF_TO_POLICY_OWNER_RECOMMENDED",
  "requires_human_review": true,
  "final_decider": "human",
  "handoff_executed_automatically": false
}
```

Handoff to `human_reviewer` example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "handoff_required": true,
  "next_recommended_agent_role": "human_reviewer",
  "decision": "NEEDS_HUMAN_DECISION",
  "reason_code": "HANDOFF_TO_HUMAN_REVIEWER_REQUIRED",
  "requires_human_review": true,
  "final_decider": "human",
  "handoff_executed_automatically": false
}
```

Incomplete evidence example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "decision": "BLOCK",
  "reason_code": "CHECKPOINT_EVIDENCE_INCOMPLETE",
  "failed_checks": [
    "evidence_hash_presence"
  ],
  "requires_human_review": true,
  "final_decider": "human"
}
```

Hash mismatch example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "decision": "BLOCK",
  "reason_code": "CHECKPOINT_HASH_MISMATCH",
  "requires_human_review": true,
  "final_decider": "human"
}
```

Prohibited automatic resume attempt example:

```json
{
  "patch": 10,
  "mode": "mediation_checkpoint_handoff",
  "decision": "BLOCK",
  "reason_code": "AUTOMATIC_RESUME_ATTEMPTED",
  "checkpoint_applied_automatically": true,
  "handoff_executed_automatically": true,
  "requires_human_review": true,
  "final_decider": "human"
}
```

These examples are advisory-only.

They do not launch agents, post comments, apply fixes, create pull requests, merge, or deploy.

## Advisory artifact clarification

- `next_recommended_agent_role` is advisory metadata only.
- `recommended_human_next_actions` are advisory labels only.
- `handoff_required` does not trigger a handoff.
- `checkpoint_id` does not create an execution token.
- `current_patch_stage` does not resume processing.
- `decision` does not authorize execution.
- No field dispatches work.
- No field launches agents.
- No field posts comments.
- No field applies fixes.
- No field creates PRs.
- No field merges.
- No field deploys.

## Future assertion expectations

When Patch 10 is implemented later, tests should assert:

- checkpoint preserves unresolved reason codes
- checkpoint preserves completed checks
- checkpoint preserves failed checks
- checkpoint preserves loop evidence
- checkpoint preserves role-rotation evidence
- checkpoint preserves candidate hashes
- checkpoint preserves evidence hashes
- checkpoint lineage is traceable
- missing evidence routes to `BLOCK`
- hash mismatch routes to `BLOCK`
- parent mismatch routes to `BLOCK`
- automatic resume attempt routes to `BLOCK`
- real agent execution attempt routes to `BLOCK`
- contradictory state is not normalized
- unresolved state is not marked resolved automatically
- `final_decider` is `human`
- `auto_corrected` is false
- `source_files_modified` is false
- `normalized_to_safe_result` is false
- `real_agent_executed` is false
- `github_comment_posted` is false
- `pull_request_created` is false
- `checkpoint_applied_automatically` is false
- `handoff_executed_automatically` is false
- no AI API is called
- no PR is created
- no merge occurs
- no deploy occurs

## Future fixture ideas

Patch 10 may use future fixtures such as:

```text
tests/stress/fixtures/checkpoint_handoff/
  checkpoint_created_no_handoff.json
  handoff_to_review_agent.json
  handoff_to_policy_owner.json
  handoff_to_human_reviewer.json
  unresolved_reason_codes_present.json
  incomplete_checkpoint_evidence.json
  checkpoint_hash_mismatch.json
  checkpoint_parent_mismatch.json
  automatic_resume_attempted.json
  prohibited_handoff_behavior_observed.json
```

These fixture paths are examples only.

Patch 10 does not create them.

## Network and metadata boundary

Patch 10 must not call AI providers or external AI services.

Prohibited:

- runtime external network calls to AI providers or external AI services
- OpenAI API calls
- Codex API calls
- Anthropic API calls
- Gemini API calls
- Copilot API calls
- external AI provider APIs
- AI API keys
- GitHub Actions secrets for AI APIs

Allowed only under the reviewed advisory boundary:

- read-only GitHub metadata access under read-only permissions
- GitHub Actions artifact upload for human review
- local deterministic artifact generation
- advisory-only review material generation

Read-only GitHub metadata access is not external AI provider access.

Artifact upload is not agent execution.

Checkpoint generation is not automatic resume.

Handoff recommendation is not automatic dispatch.

## Safety boundary

Allowed:

- documentation/specification only
- define checkpoint semantics
- define handoff semantics
- define checkpoint integrity rules
- define logical artifact shape
- define future assertions
- define future fixture ideas as text only
- preserve human final decision authority
- local deterministic artifact generation for human review, if separately approved
- advisory-only review material generation
- read-only GitHub metadata access under read-only permissions, if separately reviewed
- GitHub Actions artifact upload for human review, if separately reviewed

Prohibited:

- runtime behavior
- workflow changes
- scripts
- tests
- generated output commits
- AI API calls
- Codex API calls
- OpenAI API calls
- Anthropic API calls
- Gemini API calls
- Copilot API calls
- external AI provider calls
- external AI provider APIs
- API keys
- AI API keys
- GitHub Actions secrets
- GitHub Actions secrets for AI APIs
- runtime external network calls to AI providers or external AI services
- actual agent execution
- automatic resume
- automatic repair
- source file modification by verifier
- GitHub comment posting
- review comment posting
- issue creation
- PR creation
- auto-fix
- auto-commit-to-main
- auto-PR
- auto-merge
- deploy

## Initial pseudo-orchestration completion note

- Patch 5 defines pseudo-orchestration.
- Patch 6 defines reasoned return.
- Patch 7 defines revised-submission verification.
- Patch 8 defines mediation loop detection.
- Patch 9 defines logical role rotation.
- Patch 10 defines checkpoint handoff.
- Together, Patch 5 through Patch 10 form the initial pseudo-orchestration specification sequence.
- Completion of Patch 10 specification does not mean runtime implementation is complete.
- External verification, attestation, and verifier-library work remain separate future phases.

## Review checklist

- [ ] Exactly one file added
- [ ] File is `docs/specs/patch-10-mediation-checkpoint-handoff.md`
- [ ] No existing spec modified
- [ ] No release note changed
- [ ] No workflow changed
- [ ] No script changed
- [ ] No test changed
- [ ] No README changed
- [ ] No generated outputs committed
- [ ] No `analysis_results/` committed
- [ ] No `stress_results/` committed
- [ ] No AI API calls
- [ ] No API keys or secrets
- [ ] No actual agent execution
- [ ] No automatic resume
- [ ] No GitHub comments posted
- [ ] No PR created automatically
- [ ] No merge performed
- [ ] Human final decision boundary preserved
