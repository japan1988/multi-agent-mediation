# Patch 8: Mediation loop guard release note

## Status

Patch 8 specification has been completed and merged.

This release note records the completion of the Patch 8 specification-only phase.

Patch 8 remains specification-only and does not implement runtime behavior.

## Summary

Patch 8 defines the mediation loop guard.

Patch 8 detects repeated or cyclic return/resubmission loops.

Patch 8 detects:

* repeated `reason_code` loops
* unchanged revised candidate hashes
* oscillating mediation states such as `A -> B -> A -> B`
* repeated `return_to.agent_role` loops
* `max_attempts` exhaustion

Patch 8 stops or escalates loops.

Patch 8 does not resolve loops automatically.

Patch 8 does not repair.

Patch 8 does not modify source files.

Patch 8 keeps final decision authority with a human reviewer.

Patch 8は「ループを解決する」のではなく、  
「差し戻しがループしていることを検出して止める」。

## Merged PR

* PR: #897
* Title: Add Patch 8 mediation loop guard spec
* Branch: patch-8-mediation-loop-guard-spec
* Base: main
* Merge commit: a45b677f3a3c208d9ce203b22cce57f7434902e2
* Merged at: 2026-07-09T01:45:04Z

## Changed files

Patch 8 spec PR added exactly one file:

```text
A docs/specs/patch-8-mediation-loop-guard.md
```

## Patch 8 spec PR stats

```text
1 file changed
451 insertions
0 deletions
```

* No workflow files were changed.
* No script files were changed.
* No test files were changed.
* No README file was changed.
* No release note file was changed by the spec PR.
* No generated outputs were committed.
* No analysis_results/ files were committed.
* No stress_results/ files were committed.

## Specification file

```text
docs/specs/patch-8-mediation-loop-guard.md
```

The specification defines:

* mediation loop detection
* logical inputs
* logical outputs
* decisions
* loop types
* reason codes
* future artifact shape
* future assertion expectations
* future fixture ideas
* safety boundary
* relationship to Patch 9 and Patch 10

## Decisions

| Decision               | Meaning                                                                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `PROCEED_TO_REVIEW`    | No loop is detected, `max_attempts` is not exceeded, and no unresolved contradiction remains; material may proceed to human review |
| `BLOCK`                | A repeated or cyclic mediation loop is detected and the flow must stop                                                             |
| `NEEDS_HUMAN_DECISION` | Maximum attempts are reached or evidence is incomplete enough that a human decision is required                                    |

* `PROCEED_TO_REVIEW` means human review only.
* It does not authorize automatic application, auto-commit, auto-PR, auto-merge, or deploy.
* No Patch 8 decision authorizes automation.

## Loop types

| Loop type                     | Meaning                                                                  |
| ----------------------------- | ------------------------------------------------------------------------ |
| `SAME_REASON_REPEATED`        | The same unresolved reason code appears across repeated attempts         |
| `UNCHANGED_RESUBMISSION_LOOP` | The revised candidate hash is unchanged across attempts                  |
| `OSCILLATING_MEDIATION_STATE` | The mediation state oscillates, such as `A -> B -> A -> B`               |
| `MAX_ATTEMPTS_REACHED`        | The configured maximum attempt count has been reached or exceeded        |
| `SAME_AGENT_RETURN_LOOP`      | The same logical agent role is repeatedly returned to without resolution |

## Initial reason codes

| Reason code                      | Decision               | Meaning                                         |
| -------------------------------- | ---------------------- | ----------------------------------------------- |
| `NO_MEDIATION_LOOP_DETECTED`     | `PROCEED_TO_REVIEW`    | No mediation loop is detected                   |
| `MEDIATION_LOOP_DETECTED`        | `BLOCK`                | A repeated reason-code loop is detected         |
| `UNCHANGED_RESUBMISSION_LOOP`    | `BLOCK`                | A candidate hash repeats across attempts        |
| `OSCILLATING_MEDIATION_STATE`    | `BLOCK`                | State transitions oscillate                     |
| `MAX_MEDIATION_ATTEMPTS_REACHED` | `NEEDS_HUMAN_DECISION` | Maximum attempts are reached or exceeded        |
| `SAME_AGENT_RETURN_LOOP`         | `BLOCK`                | The same logical role is repeatedly returned to |
| `LOOP_EVIDENCE_INCOMPLETE`       | `NEEDS_HUMAN_DECISION` | Loop evidence is missing or incomplete          |

## Boundary clarification

Prohibited:

* runtime external network calls to AI providers or external AI services
* OpenAI API calls
* Codex API calls
* Anthropic API calls
* Gemini API calls
* Copilot API calls
* external AI provider APIs
* AI API keys
* GitHub Actions secrets for AI APIs

Allowed:

* read-only GitHub metadata access required to inspect PR diffs under read-only permissions
* GitHub Actions artifact upload for human review
* local deterministic artifact generation
* advisory-only review material generation

Read-only GitHub repository metadata access is not the same as external AI provider access.

This clarification does not weaken the prohibition against AI provider calls, AI API keys, secrets for AI APIs, runtime repair, automated PR creation, merge, or deploy behavior.

## Advisory artifact label clarification

* `next_action` and `required_next_actions` are advisory artifact labels only.
* They do not dispatch work.
* They do not launch agents.
* They do not post GitHub comments.
* They do not apply fixes.
* They do not create pull requests.
* They do not merge.
* They do not deploy.

## Safety boundary

Allowed:

* documentation/specification only
* define mediation loop detection semantics
* define logical artifact shape
* define future assertions
* define future fixtures as text only
* preserve human final decision boundary
* local deterministic artifact generation for human review, if a future implementation is separately approved
* advisory-only review material generation
* read-only GitHub metadata access under read-only permissions, if used by existing or separately reviewed workflow infrastructure
* GitHub Actions artifact upload for human review, if used by existing or separately reviewed workflow infrastructure

Prohibited:

* runtime behavior
* workflow changes
* scripts
* tests
* generated output commits
* AI API calls
* Codex API calls
* OpenAI API calls
* Anthropic API calls
* Gemini API calls
* Copilot API calls
* external AI provider calls
* external AI provider APIs
* API keys
* AI API keys
* GitHub Actions secrets
* GitHub Actions secrets for AI APIs
* runtime external network calls to AI providers or external AI services
* actual agent execution
* automatic repair
* source file modification by verifier
* auto-fix
* auto-commit-to-main
* auto-PR
* auto-merge
* deploy

## CI / artifact observation

PR #897 workflow evidence:

Workflow:

* Name: Tasukeru Analysis
* Run number: 1059
* Status: completed
* Conclusion: success
* Job: advisory analysis
* Job conclusion: success

Artifacts produced during runtime:

* tasukeru-advisory-logs

  * digest: sha256:7bad9d3e3a3af2affd6eba06558f5bb8598e9537ae7e035d47e66b64f2142b4f
* tasukeru-explainable-patch-proposals

  * digest: sha256:37750097978aba531fc5f10f913d346c816c1cf88ad1d09e6f39b5ca961105d2
* tasukeru-arl-stress-results

  * digest: sha256:7ae143e2173e448fe90b3d2f53fadd3b341af9858d157418c9e61f3d550cc9d5
* tasukeru-arl-analyzer-results

  * digest: sha256:458c7ace1c860c06760843eaa7ebe19dbfac80b435ea24cf2061c603f1cb958e

These artifacts were produced during workflow runtime.

They were not committed to the repository.

## Relationship to other patches

* Patch 6 defines reasoned return and stops on contradiction.
* Patch 7 verifies revised submission candidates.
* Patch 8 detects mediation loops created by repeated return/resubmission attempts.
* Patch 9 may recommend logical agent role rotation after repeated loops.
* Patch 10 may checkpoint and hand off unresolved loop state.
* Patch 8 does not implement Patch 9 or Patch 10.

## Final status

Patch 8 specification phase is complete.

Patch 8 release note records the spec-only completion.

Human review remains the final decision boundary.
