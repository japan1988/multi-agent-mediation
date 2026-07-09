# Patch 9: Agent rotation escalation gate

## Status

Patch 9 is specification-only.

It does not implement runtime behavior.

It does not add tests.

It does not integrate with workflow.

It does not execute agents.

It does not call AI APIs.

It does not repair files.

It does not create pull requests.

It does not merge pull requests.

It only defines logical role-rotation and escalation semantics for future implementation.

## Core sentence

Patch 9は「エージェントを実行する」のではなく、  
「同じロールで解決しないときに、別ロールへの交代を提案する」。

Patch 9 recommends logical role rotation.

It does not launch real agents.

## Purpose

Patch 9 exists to:

- detect when the same logical role keeps receiving unresolved returns
- detect repeated `return_to.agent_role`
- detect repeated unresolved `reason_code`
- detect role-local mediation loops after Patch 8
- recommend the next logical role
- escalate unresolved loops to `policy_owner` or `human_reviewer`
- preserve human final decision authority
- avoid repeated ineffective return to the same logical role

Patch 9 is an escalation gate.

Patch 9 is not an agent executor.

Patch 9 is not a repair mechanism.

Patch 9 does not auto-assign, auto-comment, auto-fix, auto-commit, auto-PR, auto-merge, or deploy.

## Relationship to Patch 6, Patch 7, Patch 8, and Patch 10

Patch 6:

- detects contradiction
- assigns `reason_code`
- returns to a logical agent role
- stops

Patch 7:

- verifies whether a revised candidate resolves the Patch 6 return reason
- does not repair

Patch 8:

- detects mediation loops
- blocks or escalates loop states
- does not resolve loops automatically

Patch 9:

- reads loop / return history
- detects repeated unresolved returns to the same logical role
- recommends logical role rotation
- escalates unresolved states to policy owner or human reviewer
- does not execute the recommended role

Patch 10:

- may checkpoint and hand off unresolved mediation state later
- Patch 9 does not implement Patch 10

## Logical roles

| Logical role | Meaning |
|---|---|
| `implementation_agent` | The role expected to revise or prepare the candidate material |
| `review_agent` | The role expected to independently review the unresolved issue |
| `policy_owner` | The role expected to decide policy or boundary questions |
| `human_reviewer` | The final human decision role |

These are labels only.

They do not launch real agents.

They do not call Codex.

They do not call OpenAI.

They do not trigger workflow jobs.

They do not post GitHub comments.

They do not create issues or pull requests.

## Inputs

Patch 9 may use these future logical inputs:

| Input | Meaning |
|---|---|
| `mediation_history` | Ordered mediation attempts and outcomes |
| `patch_6_return_artifacts` | Patch 6 reasoned return artifacts |
| `patch_7_verification_artifacts` | Patch 7 revised submission verification artifacts |
| `patch_8_loop_guard_artifacts` | Patch 8 mediation loop guard artifacts |
| `previous_reason_codes` | Reason codes observed across attempts |
| `unresolved_reason_codes` | Reason codes still unresolved |
| `previous_return_to_agent_roles` | Logical roles previously returned to |
| `current_agent_role` | Current logical role under consideration |
| `role_attempt_counts` | Attempt count per logical role |
| `same_role_return_count` | Number of repeated returns to the same logical role |
| `candidate_hashes` | Stable hashes of revised candidate artifacts |
| `loop_detected` | Whether Patch 8 detected a mediation loop |
| `loop_type` | Patch 8 loop type |
| `attempt_count` | Overall mediation attempt count |
| `max_attempts` | Maximum allowed attempts |
| `evidence_hashes` | Stable hashes of supporting evidence artifacts |

These inputs are logical artifact concepts only.

Patch 9 does not require live services, external providers, or AI APIs.

## Outputs

Patch 9 may define these future logical outputs:

| Output | Meaning |
|---|---|
| `rotation_recommended` | Whether logical role rotation is recommended |
| `escalation_required` | Whether the case should be escalated |
| `previous_agent_role` | Prior logical role |
| `current_agent_role` | Current logical role |
| `next_recommended_agent_role` | Recommended next logical role |
| `fallback_agent_role` | Fallback role when escalation is unresolved |
| `decision` | Patch 9 decision |
| `reason_code` | Patch 9 reason code |
| `unresolved_reason_codes` | Reasons still unresolved |
| `role_attempt_counts` | Attempts per logical role |
| `same_role_return_count` | Repeated returns to same role |
| `requires_human_review` | Whether human review is required |
| `final_decider` | Must be `human` |
| `auto_corrected` | Must be false |
| `source_files_modified` | Must be false |
| `normalized_to_safe_result` | Must be false |
| `real_agent_executed` | Must be false |
| `github_comment_posted` | Must be false |
| `pull_request_created` | Must be false |

Patch 9 output is advisory-only.

Patch 9 output must not be treated as automatic approval, automatic assignment, automatic execution, or permission to merge.

## Decisions

Patch 9 defines these decisions:

| Decision | Meaning |
|---|---|
| `NO_ROTATION_REQUIRED` | No repeated unresolved same-role return is detected |
| `ROTATION_RECOMMENDED` | A different logical role should review the unresolved state |
| `ESCALATE_TO_POLICY_OWNER` | The unresolved state requires policy or boundary ownership |
| `ESCALATE_TO_HUMAN_REVIEWER` | The unresolved state must be sent to the final human decision role |
| `BLOCK` | Unsafe or contradictory escalation state must stop |

Decision rules:

- `NO_ROTATION_REQUIRED` may be used only if no same-role unresolved loop is detected.
- `ROTATION_RECOMMENDED` must be used if `implementation_agent` receives repeated unresolved returns with the same reason.
- `ESCALATE_TO_POLICY_OWNER` must be used if `review_agent` cannot resolve a repeated boundary or policy issue.
- `ESCALATE_TO_HUMAN_REVIEWER` must be used if `policy_owner` cannot resolve the issue, if max attempts are reached, or if the case requires final human judgment.
- `BLOCK` must be used if the rotation path attempts prohibited behavior such as real agent execution, auto-fix, auto-commit, auto-PR, auto-merge, deploy, or AI API use.
- No Patch 9 decision may authorize automatic application, source modification, comment posting, PR creation, merge, or deploy.

## Rotation policy

Patch 9 defines this initial logical role rotation policy:

| Condition | Next recommended role | Reason code |
|---|---|---|
| Same unresolved reason repeatedly returned to `implementation_agent` | `review_agent` | `AGENT_ROTATION_REQUIRED` |
| Same unresolved reason repeatedly returned to `review_agent` | `policy_owner` | `POLICY_OWNER_ESCALATION_REQUIRED` |
| Same unresolved reason repeatedly returned to `policy_owner` | `human_reviewer` | `HUMAN_FINAL_DECISION_REQUIRED` |
| Evidence is incomplete | `human_reviewer` | `ROTATION_EVIDENCE_INCOMPLETE` |
| Prohibited automation behavior is observed | none | `PROHIBITED_ROTATION_BEHAVIOR_OBSERVED` |

`human_reviewer` is terminal.

Patch 9 must not recommend rotating away from final human decision once human review is required.

Patch 9 must not create an infinite logical-role rotation loop.

## Initial reason codes

| Reason code | Decision | Meaning |
|---|---|---|
| `NO_AGENT_ROTATION_REQUIRED` | `NO_ROTATION_REQUIRED` | No repeated unresolved same-role return is detected |
| `AGENT_ROTATION_REQUIRED` | `ROTATION_RECOMMENDED` | The same unresolved issue repeatedly returned to the same implementation role |
| `REVIEW_AGENT_ESCALATION_REQUIRED` | `ROTATION_RECOMMENDED` | The case needs independent review rather than another implementation return |
| `POLICY_OWNER_ESCALATION_REQUIRED` | `ESCALATE_TO_POLICY_OWNER` | The unresolved issue requires policy or boundary ownership |
| `HUMAN_FINAL_DECISION_REQUIRED` | `ESCALATE_TO_HUMAN_REVIEWER` | The unresolved issue requires final human decision |
| `ROTATION_EVIDENCE_INCOMPLETE` | `ESCALATE_TO_HUMAN_REVIEWER` | Evidence is incomplete and cannot support deterministic rotation |
| `PROHIBITED_ROTATION_BEHAVIOR_OBSERVED` | `BLOCK` | Rotation attempted or implied prohibited automation |
| `ROTATION_LOOP_DETECTED` | `BLOCK` | Logical role rotation itself became cyclic or unsafe |

## Future artifact shape

Patch 9 does not implement artifacts yet.

A future implementation may produce a local review artifact with this shape:

```json
{
  "patch": 9,
  "mode": "agent_rotation_escalation_gate",
  "decision": "ROTATION_RECOMMENDED",
  "reason_code": "AGENT_ROTATION_REQUIRED",
  "rotation_recommended": true,
  "escalation_required": false,
  "previous_agent_role": "implementation_agent",
  "current_agent_role": "implementation_agent",
  "next_recommended_agent_role": "review_agent",
  "fallback_agent_role": "human_reviewer",
  "unresolved_reason_codes": [
    "HUMAN_REVIEW_BYPASS"
  ],
  "role_attempt_counts": {
    "implementation_agent": 3
  },
  "same_role_return_count": 3,
  "loop_detected": true,
  "loop_type": "SAME_AGENT_RETURN_LOOP",
  "requires_human_review": true,
  "final_decider": "human",
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false,
  "real_agent_executed": false,
  "github_comment_posted": false,
  "pull_request_created": false,
  "prohibited_next_actions": [
    "launch_real_agent",
    "call_ai_api",
    "auto_fix",
    "auto_commit",
    "auto_pr",
    "auto_merge",
    "deploy"
  ],
  "recommended_human_next_actions": [
    "preserve rotation evidence",
    "send unresolved issue to review_agent",
    "require human review before merge"
  ]
}
```

Escalation to `policy_owner` example:

```json
{
  "patch": 9,
  "mode": "agent_rotation_escalation_gate",
  "decision": "ESCALATE_TO_POLICY_OWNER",
  "reason_code": "POLICY_OWNER_ESCALATION_REQUIRED",
  "rotation_recommended": true,
  "escalation_required": true,
  "previous_agent_role": "review_agent",
  "current_agent_role": "review_agent",
  "next_recommended_agent_role": "policy_owner",
  "fallback_agent_role": "human_reviewer",
  "requires_human_review": true,
  "final_decider": "human",
  "real_agent_executed": false,
  "github_comment_posted": false,
  "pull_request_created": false
}
```

Escalation to `human_reviewer` example:

```json
{
  "patch": 9,
  "mode": "agent_rotation_escalation_gate",
  "decision": "ESCALATE_TO_HUMAN_REVIEWER",
  "reason_code": "HUMAN_FINAL_DECISION_REQUIRED",
  "rotation_recommended": false,
  "escalation_required": true,
  "previous_agent_role": "policy_owner",
  "current_agent_role": "policy_owner",
  "next_recommended_agent_role": "human_reviewer",
  "fallback_agent_role": "human_reviewer",
  "requires_human_review": true,
  "final_decider": "human",
  "real_agent_executed": false,
  "github_comment_posted": false,
  "pull_request_created": false
}
```

Prohibited automation observed example:

```json
{
  "patch": 9,
  "mode": "agent_rotation_escalation_gate",
  "decision": "BLOCK",
  "reason_code": "PROHIBITED_ROTATION_BEHAVIOR_OBSERVED",
  "rotation_recommended": false,
  "escalation_required": true,
  "next_recommended_agent_role": null,
  "requires_human_review": true,
  "final_decider": "human",
  "real_agent_executed": true,
  "github_comment_posted": true,
  "pull_request_created": true,
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false
}
```

These examples are advisory-only.

They do not launch agents, post comments, apply fixes, create pull requests, merge, or deploy.

## Future assertion expectations

When Patch 9 is implemented later, tests should assert:

- same unresolved issue repeatedly returned to `implementation_agent` recommends `review_agent`
- same unresolved issue repeatedly returned to `review_agent` recommends `policy_owner`
- same unresolved issue repeatedly returned to `policy_owner` recommends `human_reviewer`
- `human_reviewer` remains final decision boundary
- `final_decider` must be `human`
- `auto_corrected` must be false
- `source_files_modified` must be false
- `normalized_to_safe_result` must be false
- `real_agent_executed` must be false
- `github_comment_posted` must be false
- `pull_request_created` must be false
- Patch 9 must not call AI APIs
- Patch 9 must not create PRs
- Patch 9 must not merge
- Patch 9 must not deploy
- incomplete evidence routes to human review
- prohibited automation behavior routes to `BLOCK`
- role rotation must not become an infinite loop

## Future fixture ideas

Patch 9 may use future fixtures such as:

```text
tests/stress/fixtures/agent_rotation/
  no_rotation_required.json
  implementation_agent_repeated_return.json
  review_agent_escalation_required.json
  policy_owner_escalation_required.json
  human_final_decision_required.json
  incomplete_rotation_evidence.json
  prohibited_rotation_behavior_observed.json
  rotation_loop_detected.json
```

These fixture paths are examples only.

Patch 9 does not create them.

## Network and metadata boundary

Patch 9 must not call AI providers or external AI services.

Prohibited network/API behavior includes:

- runtime external network calls to AI providers or external AI services
- OpenAI API calls
- Codex API calls
- Anthropic API calls
- Gemini API calls
- Copilot API calls
- external AI provider APIs
- AI API keys
- GitHub Actions secrets for AI APIs

The following behavior is allowed only when it remains under the reviewed advisory boundary:

- read-only GitHub metadata access required to inspect PR diffs under read-only permissions
- GitHub Actions artifact upload for human review
- local deterministic artifact generation
- advisory-only review material generation

Read-only GitHub repository metadata access is not the same as external AI provider access.

This clarification does not weaken the prohibition against AI provider calls, AI API keys, secrets for AI APIs, runtime repair, automated PR creation, merge, or deploy behavior.

## Safety boundary

Allowed:

- documentation/specification only
- define logical role-rotation semantics
- define logical escalation semantics
- define future artifact shape
- define future assertions
- define future fixtures as text only
- preserve human final decision boundary
- local deterministic artifact generation for human review, if a future implementation is separately approved
- advisory-only review material generation
- read-only GitHub metadata access under read-only permissions, if used by existing or separately reviewed workflow infrastructure
- GitHub Actions artifact upload for human review, if used by existing or separately reviewed workflow infrastructure

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

## Review checklist

- [ ] Exactly one file added
- [ ] File is `docs/specs/patch-9-agent-rotation-escalation-gate.md`
- [ ] No workflow changes
- [ ] No script changes
- [ ] No test changes
- [ ] No README changes
- [ ] No release note changes
- [ ] No generated outputs committed
- [ ] No `analysis_results/` committed
- [ ] No `stress_results/` committed
- [ ] No AI API calls
- [ ] No API keys or secrets
- [ ] No actual agent execution
- [ ] No GitHub comments posted
- [ ] No PR created automatically
- [ ] No merge performed
- [ ] Human final decision boundary preserved
