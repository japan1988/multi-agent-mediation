# Patch 8: Mediation loop guard

## Status

Patch 8 is specification-only.

It defines a mediation loop guard for repeated return/resubmission cycles after Patch 6 reasoned return and Patch 7 revised submission verification.

It does not implement runtime behavior.

It does not add tests.

It does not integrate with workflow.

It does not execute agents.

It does not repair files.

It does not create pull requests.

It does not merge pull requests.

## Core sentence

Patch 8は「ループを解決する」のではなく、
「差し戻しがループしていることを検出して止める」。

Patch 8 detects mediation loops.

It does not resolve them automatically.

## Purpose

Patch 8 defines a mediation loop guard.

It detects repeated or cyclic mediation states after Patch 6 reasoned return and Patch 7 revised submission verification.

Patch 8 exists to:

- detect repeated mediation loops
- prevent infinite return/resubmission cycles
- preserve evidence of the loop
- route unresolved cycles to `BLOCK` or human escalation
- keep final decision authority with a human reviewer

Patch 8 does not perform repair.

Patch 8 does not modify source files.

Patch 8 does not normalize loop states into safe-looking progress.

## Relationship to Patch 6 and Patch 7

Patch 6:

- detects contradiction
- assigns `reason_code`
- returns to a logical agent role
- stops

Patch 7:

- verifies whether a revised candidate resolves the Patch 6 return reason
- decides whether the candidate may proceed to human review or remains blocked
- does not repair

Patch 8:

- reads mediation history
- detects repeated `reason_code` loops
- detects repeated `return_to.agent_role` loops
- detects unchanged revised candidate hashes
- detects oscillating mediation states such as `A -> B -> A -> B`
- enforces `max_attempts`
- blocks or escalates to human decision
- preserves `final_decider` as `human`

Patch 8 is a guard, not a resolver.

## Non-goals

Patch 8 does not:

- fix loops
- rewrite reason codes to pass
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
- implement Patch 9
- implement Patch 10

## Inputs

Patch 8 may use these future logical inputs:

| Input | Meaning |
|---|---|
| `mediation_history` | Ordered mediation attempts and outcomes |
| `patch_6_return_artifacts` | Patch 6 reasoned return artifacts |
| `patch_7_verification_artifacts` | Patch 7 revised submission verification artifacts |
| `previous_reason_codes` | Previous reason codes across attempts |
| `previous_decisions` | Previous mediation decisions across attempts |
| `previous_return_to_agent_roles` | Previous logical return targets |
| `revised_candidate_ids` | Candidate identifiers across attempts |
| `revised_candidate_hashes` | Stable hashes for revised candidate artifacts |
| `attempt_count` | Current mediation attempt count |
| `max_attempts` | Maximum allowed attempts before human escalation |
| `state_transition_history` | Ordered state transitions, such as `A -> B -> A -> B` |
| `evidence_hashes` | Stable hashes of supporting evidence artifacts |

These inputs are logical artifact concepts only.

Patch 8 does not require live services, external providers, or AI APIs.

## Outputs

Patch 8 may define these future logical outputs:

| Output | Meaning |
|---|---|
| `loop_detected` | Whether a mediation loop was detected |
| `loop_type` | The type of loop detected |
| `attempt_count` | Current mediation attempt count |
| `max_attempts` | Maximum allowed attempts |
| `repeated_reason_codes` | Reason codes repeated across attempts |
| `repeated_return_to_agent_roles` | Logical roles repeatedly returned to |
| `unchanged_candidate_hashes` | Candidate hashes repeated across attempts |
| `oscillation_pattern` | Detected oscillating state sequence |
| `decision` | Patch 8 decision |
| `reason_code` | Patch 8 reason code |
| `next_action` | Advisory next action |
| `requires_human_review` | Must be true for blocked or escalated outcomes |
| `final_decider` | Must be `human` |
| `auto_corrected` | Must be false |
| `source_files_modified` | Must be false |
| `normalized_to_safe_result` | Must be false |

Patch 8 output is advisory-only.

It must not be treated as automatic approval, automatic application, or permission to merge.

## Decisions

Patch 8 defines these mediation decisions:

| Decision | Meaning |
|---|---|
| `PROCEED_TO_REVIEW` | No loop is detected, `max_attempts` is not exceeded, and no unresolved contradiction remains; material may proceed to human review |
| `BLOCK` | A repeated or cyclic mediation loop is detected and the flow must stop |
| `NEEDS_HUMAN_DECISION` | Maximum attempts are reached or evidence is incomplete enough that a human decision is required |

Decision rules:

- `PROCEED_TO_REVIEW` may be used only if no loop is detected, `max_attempts` is not exceeded, and no unresolved contradiction remains.
- `PROCEED_TO_REVIEW` means proceed to human review only; it does not authorize automatic application.
- `BLOCK` must be used if the same `reason_code` repeats beyond the allowed threshold.
- `BLOCK` must be used if the revised candidate hash is unchanged across attempts.
- `BLOCK` must be used if an oscillating mediation state is detected.
- `BLOCK` must be used if the same logical agent role is repeatedly returned to without resolution.
- `NEEDS_HUMAN_DECISION` must be used if `max_attempts` is reached or exceeded.
- `NEEDS_HUMAN_DECISION` must be used when loop evidence is incomplete and cannot be verified deterministically.
- No Patch 8 decision may authorize auto-apply, auto-commit, auto-PR, auto-merge, or deploy.

## Loop types

Patch 8 defines these initial loop types:

| Loop type | Meaning |
|---|---|
| `SAME_REASON_REPEATED` | The same unresolved reason code appears across repeated attempts |
| `UNCHANGED_RESUBMISSION_LOOP` | The revised candidate hash is unchanged across attempts |
| `OSCILLATING_MEDIATION_STATE` | The mediation state oscillates, such as `A -> B -> A -> B` |
| `MAX_ATTEMPTS_REACHED` | The configured maximum attempt count has been reached or exceeded |
| `SAME_AGENT_RETURN_LOOP` | The same logical agent role is repeatedly returned to without resolution |

## Reason codes

Patch 8 defines these initial reason codes:

| Reason code | Decision | Meaning |
|---|---|---|
| `NO_MEDIATION_LOOP_DETECTED` | `PROCEED_TO_REVIEW` | No mediation loop is detected |
| `MEDIATION_LOOP_DETECTED` | `BLOCK` | A repeated reason-code loop is detected |
| `UNCHANGED_RESUBMISSION_LOOP` | `BLOCK` | A candidate hash repeats across attempts |
| `OSCILLATING_MEDIATION_STATE` | `BLOCK` | State transitions oscillate |
| `MAX_MEDIATION_ATTEMPTS_REACHED` | `NEEDS_HUMAN_DECISION` | Maximum attempts are reached or exceeded |
| `SAME_AGENT_RETURN_LOOP` | `BLOCK` | The same logical role is repeatedly returned to |
| `LOOP_EVIDENCE_INCOMPLETE` | `NEEDS_HUMAN_DECISION` | Loop evidence is missing or incomplete |

Expected mappings:

| Condition | Decision | Reason code |
|---|---|---|
| `SAME_REASON_REPEATED` | `BLOCK` | `MEDIATION_LOOP_DETECTED` |
| `UNCHANGED_RESUBMISSION_LOOP` | `BLOCK` | `UNCHANGED_RESUBMISSION_LOOP` |
| `OSCILLATING_MEDIATION_STATE` | `BLOCK` | `OSCILLATING_MEDIATION_STATE` |
| `MAX_ATTEMPTS_REACHED` | `NEEDS_HUMAN_DECISION` | `MAX_MEDIATION_ATTEMPTS_REACHED` |
| `SAME_AGENT_RETURN_LOOP` | `BLOCK` | `SAME_AGENT_RETURN_LOOP` |
| incomplete evidence | `NEEDS_HUMAN_DECISION` | `LOOP_EVIDENCE_INCOMPLETE` |

## Future artifact shape

Patch 8 does not implement artifacts yet.

A future implementation may produce a local review artifact with this shape for a repeated reason-code loop:

```json
{
  "patch": 8,
  "mode": "mediation_loop_guard",
  "decision": "BLOCK",
  "reason_code": "MEDIATION_LOOP_DETECTED",
  "loop_detected": true,
  "loop_type": "SAME_REASON_REPEATED",
  "attempt_count": 3,
  "max_attempts": 3,
  "repeated_reason_codes": [
    "HUMAN_REVIEW_BYPASS"
  ],
  "repeated_return_to_agent_roles": [
    "implementation_agent"
  ],
  "unchanged_candidate_hashes": [],
  "oscillation_pattern": [],
  "requires_human_review": true,
  "final_decider": "human",
  "next_action": "ESCALATE_TO_HUMAN_REVIEW",
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false,
  "prohibited_next_actions": [
    "auto_fix",
    "auto_commit",
    "auto_pr",
    "auto_merge",
    "deploy"
  ],
  "required_next_actions": [
    "preserve loop evidence",
    "stop mediation loop",
    "send to human review"
  ]
}
```

A future implementation may produce this shape for an unchanged candidate loop:

```json
{
  "patch": 8,
  "mode": "mediation_loop_guard",
  "decision": "BLOCK",
  "reason_code": "UNCHANGED_RESUBMISSION_LOOP",
  "loop_detected": true,
  "loop_type": "UNCHANGED_RESUBMISSION_LOOP",
  "attempt_count": 2,
  "max_attempts": 3,
  "unchanged_candidate_hashes": [
    "sha256:example"
  ],
  "requires_human_review": true,
  "final_decider": "human",
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false
}
```

A future implementation may produce this shape for max attempts:

```json
{
  "patch": 8,
  "mode": "mediation_loop_guard",
  "decision": "NEEDS_HUMAN_DECISION",
  "reason_code": "MAX_MEDIATION_ATTEMPTS_REACHED",
  "loop_detected": true,
  "loop_type": "MAX_ATTEMPTS_REACHED",
  "attempt_count": 3,
  "max_attempts": 3,
  "requires_human_review": true,
  "final_decider": "human",
  "next_action": "ESCALATE_TO_HUMAN_REVIEW",
  "auto_corrected": false,
  "source_files_modified": false,
  "normalized_to_safe_result": false
}
```

## Future assertion expectations

When Patch 8 is implemented later, tests should assert:

- `loop_detected` must be true for repeated `reason_code`
- `loop_detected` must be true for unchanged candidate hash
- `loop_detected` must be true for `A -> B -> A -> B` oscillation
- `max_attempts` reached must produce `NEEDS_HUMAN_DECISION`
- same unresolved reason must not `PROCEED_TO_REVIEW`
- unchanged candidate must not `PROCEED_TO_REVIEW`
- oscillating state must not `PROCEED_TO_REVIEW`
- `auto_corrected` must be false
- `source_files_modified` must be false
- `normalized_to_safe_result` must be false
- `final_decider` must be `human`
- `prohibited_next_actions` must include `auto_fix`, `auto_commit`, `auto_pr`, `auto_merge`, and `deploy`
- Patch 8 must not launch real agents
- Patch 8 must not call AI APIs

## Future fixture ideas

Patch 8 may use future fixtures such as:

```text
tests/stress/fixtures/mediation_loop_guard/
  no_loop_resolved_candidate.json
  same_reason_repeated.json
  unchanged_candidate_hash.json
  oscillating_state_a_b_a_b.json
  max_attempts_reached.json
  same_agent_return_loop.json
  incomplete_loop_evidence.json
```

These fixture paths are examples only.

Patch 8 does not create them.

## Relationship to other patches

Patch 6 defines reasoned return and stops on contradiction.

Patch 7 verifies revised submission candidates.

Patch 8 detects mediation loops created by repeated return/resubmission attempts.

Patch 9 may recommend logical agent role rotation after repeated loops.

Patch 10 may checkpoint and hand off unresolved loop state.

Patch 8 does not implement Patch 9 or Patch 10.

## Safety boundary

Patch 8 remains inside a strict documentation/specification-only boundary.

Allowed:

- documentation/specification only
- define mediation loop detection semantics
- define logical artifact shape
- define future assertions
- define future fixtures as text only
- preserve human final decision boundary

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
- API keys
- GitHub Actions secrets
- runtime external network calls
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
- [ ] No automatic repair
- [ ] No source file modification by verifier
- [ ] No auto-fix / auto-commit / auto-PR / auto-merge / deploy
- [ ] Human final decision boundary preserved
