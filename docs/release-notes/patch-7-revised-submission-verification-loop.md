# Patch 7: Revised submission verification loop release note

## Status

Patch 7 specification has been completed and merged.

This release note records the completion of the Patch 7 specification-only phase.

## Summary

Patch 7 defines the revised submission verification loop.

It verifies whether a revised candidate submission resolves the reasoned return produced by Patch 6.

Patch 7 verifies revised candidates.

Patch 7 does not perform repairs.

Patch 7 does not modify source files.

Patch 7 does not normalize unsafe or contradictory results into safe-looking results.

Patch 7 keeps final decision authority with a human reviewer.

Patch 7は「修正する」ではなく、  
「修正されたことになっている入力を検証する」。

## Merged PR

- PR: #895
- Title: Add Patch 7 revised submission verification loop spec
- Branch: patch-7-revised-submission-verification-spec
- Base: main
- Merge commit: 6d96b8df04420313a4356b2f4d5c6ef58b9fca1e
- Merged at: 2026-07-07T03:31:03Z

## Changed files

Patch 7 spec PR added exactly one file:

```text
A docs/specs/patch-7-revised-submission-verification-loop.md
```

## Patch 7 spec PR stats

```text
1 file changed
335 insertions
0 deletions
```

No workflow, script, test, release note, README, generated output, `analysis_results/`, or `stress_results/` file was changed by the Patch 7 spec PR.

## Specification file

The Patch 7 specification file is:

```text
docs/specs/patch-7-revised-submission-verification-loop.md
```

The specification defines:

* revised submission verification
* relationship to Patch 6 reasoned return
* logical inputs
* logical outputs
* decisions
* reason codes
* future artifact shape
* future assertion expectations
* future fixture ideas
* safety boundary
* relationship to Patch 8, Patch 9, and Patch 10

## Key decisions

Patch 7 defines these mediation decisions:

| Decision            | Meaning                                                                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `PROCEED_TO_REVIEW` | The previous reason is demonstrably resolved and no new contradiction is introduced; material may proceed to human review        |
| `NEEDS_REVIEW`      | Evidence is incomplete, ambiguous, or cannot be verified                                                                         |
| `BLOCK`             | The previous reason remains unresolved, a contradiction remains, a new contradiction appears, or prohibited behavior is observed |

`PROCEED_TO_REVIEW` only means proceed to human review. It does not authorize automatic application, auto-commit, auto-PR, auto-merge, or deploy.

## Initial reason codes

Patch 7 defines these initial reason codes:

| Reason code                           | Decision            | Meaning                                                                                |
| ------------------------------------- | ------------------- | -------------------------------------------------------------------------------------- |
| `REVISED_SUBMISSION_RESOLVED`         | `PROCEED_TO_REVIEW` | The revised candidate resolves the previous reason and introduces no new contradiction |
| `PREVIOUS_REASON_UNRESOLVED`          | `BLOCK`             | The previous Patch 6 reason remains unresolved                                         |
| `PARTIAL_RESOLUTION_ONLY`             | `NEEDS_REVIEW`      | The revised candidate resolves part of the issue but not enough to proceed             |
| `RESOLUTION_EVIDENCE_MISSING`         | `NEEDS_REVIEW`      | Required resolution evidence is missing                                                |
| `NEW_CONTRADICTION_INTRODUCED`        | `BLOCK`             | The revised candidate introduces a new contradiction                                   |
| `PROHIBITED_REPAIR_BEHAVIOR_OBSERVED` | `BLOCK`             | The revised candidate or verifier indicates prohibited repair behavior                 |
| `SOURCE_MODIFICATION_BY_VERIFIER`     | `BLOCK`             | The verifier modified source files, which is prohibited                                |
| `HUMAN_REVIEW_STILL_REQUIRED`         | `NEEDS_REVIEW`      | Human review remains required even though some evidence is present                     |

## Safety boundary

Patch 7 remains inside the same pseudo-orchestration safety boundary.

Allowed:

* documentation/specification only
* define revised submission verification semantics
* define logical artifact shape
* define future assertions
* define future fixtures as text only
* preserve human final decision boundary

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
* API keys
* GitHub Actions secrets
* runtime external network calls
* actual agent execution
* automatic repair
* source file modification by verifier
* auto-fix
* auto-commit-to-main
* auto-PR
* auto-merge
* deploy

## Verification summary

* PR #895 exists and was merged.
* Merge commit is 6d96b8df04420313a4356b2f4d5c6ef58b9fca1e.
* Exactly one file was added.
* The added file is docs/specs/patch-7-revised-submission-verification-loop.md.
* No workflow files were changed.
* No script files were changed.
* No test files were changed.
* No release note files were changed by the spec PR.
* No README file was changed.
* No generated outputs were committed.
* No analysis_results/ files were committed.
* No stress_results/ files were committed.
* No AI API calls were added.
* No API keys or secrets were added.
* No runtime external network behavior was added.
* No actual agent execution was added.
* No automatic repair behavior was added.
* No auto-fix, auto-PR, auto-merge, or deploy behavior was added.

## CI / artifact observation

PR #895 had successful workflow evidence.

Workflow:

* Name: Tasukeru Analysis
* Run number: 1055
* Status: completed
* Conclusion: success
* Job: advisory analysis
* Job conclusion: success

Artifacts produced during runtime:

* tasukeru-advisory-logs
  * digest: sha256:bd73227a49495b7aa8bcfc471bb9201427abd863877bdcfebfbc8d5821e8fa9a
* tasukeru-arl-analyzer-results
  * digest: sha256:841d19c1e4dc7dd7b21464bdd847f2152744e7ad85d0ef5fbe46e26cbb7c1f99
* tasukeru-arl-stress-results
  * digest: sha256:e4af03506146135b75d149358800d236d05f9331e3a92d8122ca6400d9d96c56
* tasukeru-explainable-patch-proposals
  * digest: sha256:b2e5ddeef54473551ef6bcfe36b8c77664510383e1fda1504420ddd9ee8bcd54

These artifacts were produced during workflow runtime and were not committed to the repository.

## Relationship to other patches

* Patch 6 defines reasoned return.
* Patch 7 verifies revised submission candidates after Patch 6 return.
* Patch 8 may detect repeated mediation loops.
* Patch 9 may recommend logical agent role rotation.
* Patch 10 may checkpoint and hand off unresolved state.
* Patch 7 does not implement Patch 8, Patch 9, or Patch 10.

## Final status

Patch 7 specification phase is complete.

Human review remains the final decision boundary.
