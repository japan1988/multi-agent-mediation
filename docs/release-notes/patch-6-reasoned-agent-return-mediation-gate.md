# Patch 6: Reasoned agent return mediation gate release note

## Status

Patch 6 specification has been completed and merged.

This release note records the completion of the Patch 6 specification-only phase.

## Summary

Patch 6 defines the reasoned agent return mediation gate.

The purpose of Patch 6 is to define how the pseudo-orchestration mediation layer should handle contradictory or unsafe inputs.

Patch 6 introduces the concept of reasoned return / 差し戻し:

- detect contradictory input
- preserve contradiction details
- assign a `reason_code`
- route the case to `NEEDS_REVIEW` or `BLOCK`
- produce a reasoned `return_to` target
- stop the flow
- keep final decision authority with a human reviewer

Patch 6 is specification-only.

It does not implement runtime mediation, tests, workflow integration, actual agent execution, automatic comments, automatic fixes, commits, pull requests, merges, or deployment.

## Merged PR

- PR: #893
- Title: Add Patch 6 reasoned agent return mediation gate spec
- Branch: `patch-6-reasoned-agent-return-spec`
- Base: `main`
- Merge commit: `9d6b7d0a8ee3c5f9115fc8d2bd98972500780bef`
- Merged at: `2026-07-06T02:06:16Z`

## Changed files

Patch 6 spec PR added exactly one file:

```text
A docs/specs/patch-6-reasoned-agent-return-mediation-gate.md
```

## Patch 6 spec PR stats

```text
1 file changed
414 insertions
0 deletions
```

No workflow, script, test, README, generated output, `analysis_results/`, or `stress_results/` file was changed by the Patch 6 spec PR.

## Specification file

The Patch 6 specification file is:

```text
docs/specs/patch-6-reasoned-agent-return-mediation-gate.md
```

The specification defines:

* contradiction handling
* reasoned return semantics
* logical agent roles
* decisions
* reason codes
* return targets
* expected future artifact shape
* future assertion expectations
* safety boundary
* relationship to later patches

## Key decisions

Patch 6 defines these mediation decisions:

| Decision            | Meaning                                                             |
| ------------------- | ------------------------------------------------------------------- |
| `PROCEED_TO_REVIEW` | No contradiction was detected; material may proceed to human review |
| `NEEDS_REVIEW`      | Evidence is incomplete or ambiguous; human review is required       |
| `BLOCK`             | A safety boundary contradiction or prohibited behavior was detected |

`PROCEED_TO_REVIEW` must not be used when a contradiction is present.

## Initial reason codes

Patch 6 defines these initial reason codes:

| Reason code                          | Decision            | Return target          |
| ------------------------------------ | ------------------- | ---------------------- |
| `VALID_DOCS_ONLY_CHANGE`             | `PROCEED_TO_REVIEW` | `human_reviewer`       |
| `ADVISORY_ONLY_CONTRADICTION`        | `BLOCK`             | `implementation_agent` |
| `EXTERNAL_SIDE_EFFECT_CONTRADICTION` | `BLOCK`             | `implementation_agent` |
| `HUMAN_REVIEW_BYPASS`                | `BLOCK`             | `implementation_agent` |
| `GENERATED_OUTPUT_COMMITTED`         | `BLOCK`             | `implementation_agent` |
| `PERMISSION_ESCALATION`              | `BLOCK`             | `policy_owner`         |
| `TEST_EVIDENCE_MISSING`              | `NEEDS_REVIEW`      | `review_agent`         |

## Safety boundary

Patch 6 remains inside the same safety boundary as Patch 5.

Allowed:

* documentation/specification only
* define reasoned return semantics
* define contradiction handling policy
* define logical agent roles
* define reason codes
* define expected artifact shape
* define future test expectations

Prohibited:

* runtime behavior
* AI API calls
* Codex API calls
* Anthropic API calls
* Gemini API calls
* Copilot API calls
* external AI provider calls
* API keys
* GitHub Actions secrets
* runtime external network calls
* actual agent execution
* GitHub auto-comments
* automatic repair
* automatic code modification
* auto-fix
* auto-commit-to-main
* auto-PR
* auto-merge
* deploy
* generated output commits
* permission escalation

## Verification summary

Patch 6 was verified as a docs/spec-only change.

Confirmed:

* PR #893 exists and was merged.
* Merge commit is `9d6b7d0a8ee3c5f9115fc8d2bd98972500780bef`.
* Exactly one file was added.
* The added file is `docs/specs/patch-6-reasoned-agent-return-mediation-gate.md`.
* No workflow files were changed.
* No script files were changed.
* No test files were changed.
* No README file was changed.
* No generated outputs were committed.
* No `analysis_results/` files were committed.
* No `stress_results/` files were committed.
* No AI API calls were added.
* No API keys or secrets were added.
* No runtime external network behavior was added.
* No actual agent execution was added.
* No auto-fix, auto-PR, auto-merge, or deploy behavior was added.

## Artifact observation

A non-blocking artifact observation was recorded during review.

One workflow-dispatch artifact reported `changed_file_count: 0` while GitHub PR #893 correctly records one changed file.

This is interpreted as a workflow-dispatch artifact context gap, not as a Patch 6 source contradiction.

Impact:

* safety boundary breach: no
* Patch 6 scope breach: no
* release blocking issue: no

Future workflow/template improvements may clarify wording when PR changed-file context is unavailable.

## Relationship to later patches

Patch 6 only defines reasoned return.

Later patches may define:

* Patch 7: revised submission verification loop
* Patch 8: mediation loop guard
* Patch 9: agent rotation escalation gate
* Patch 10: mediation checkpoint handoff

These later patches are not implemented by Patch 6.

## Final status

Patch 6 specification phase is complete.

Human review remains the final decision boundary.
