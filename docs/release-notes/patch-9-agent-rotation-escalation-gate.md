# Patch 9: Agent rotation escalation gate release note

## Status

Patch 9 specification has been completed and merged.

This release note records completion of the Patch 9 specification-only phase.

Patch 9 remains specification-only.

Patch 9 does not implement runtime behavior or real agent execution.

## Core summary

Patch 9 defines the agent rotation escalation gate.

Patch 9 detects repeated unresolved returns to the same logical role.

Patch 9 recommends a different logical role when the current role is not resolving the issue.

Patch 9 may escalate to `review_agent`, `policy_owner`, or `human_reviewer`.

Patch 9 does not launch real agents.

Patch 9 does not repair files.

Patch 9 does not post GitHub comments.

Patch 9 does not create or merge pull requests.

Human review remains the final decision boundary.

Patch 9は「エージェントを実行する」のではなく、  
「同じロールで解決しないときに、別ロールへの交代を提案する」。

Patch 9 recommends logical role rotation.  
It does not launch real agents.

## Merged PR

* PR: #900
* Title: Add Patch 9 agent rotation escalation gate spec
* Branch: patch-9-agent-rotation-escalation-gate-spec
* Base: main
* Head commit: c256a08b7b5219fe09dc9d163c3fda2ab9d0d0fd
* Merge commit: f8e6649b84ffecdf0a5800ded4d66d1bdfcd2496
* Merged at: 2026-07-11T00:26:20Z

## Changed files

The Patch 9 spec PR added exactly one file:

```text
A docs/specs/patch-9-agent-rotation-escalation-gate.md
```

## Spec PR stats

```text
1 file changed
479 insertions
0 deletions
```

* No workflow files were changed.
* No script files were changed.
* No test files were changed.
* No README file was changed.
* No release note was changed by the spec PR.
* No generated outputs were committed.
* No `analysis_results/` files were committed.
* No `stress_results/` files were committed.

## Specification file

```text
docs/specs/patch-9-agent-rotation-escalation-gate.md
```

The specification defines:

* logical role-rotation semantics
* escalation semantics
* logical roles
* inputs
* outputs
* decisions
* rotation policy
* reason codes
* future artifact shape
* future assertions
* future fixture ideas
* network and metadata boundary
* safety boundary
* relationship to Patch 10

## Logical roles

| Logical role           | Meaning                                 |
| ---------------------- | --------------------------------------- |
| `implementation_agent` | Prepares or revises candidate material  |
| `review_agent`         | Independently reviews unresolved issues |
| `policy_owner`         | Decides policy or boundary questions    |
| `human_reviewer`       | Final human decision role               |

* These are labels only.
* They do not launch real agents.
* They do not call Codex or OpenAI.
* They do not trigger workflow jobs.
* They do not post comments.
* They do not create issues or pull requests.

## Decisions

| Decision                     | Meaning                                                     |
| ---------------------------- | ----------------------------------------------------------- |
| `NO_ROTATION_REQUIRED`       | No repeated unresolved same-role return is detected         |
| `ROTATION_RECOMMENDED`       | A different logical role should review the unresolved state |
| `ESCALATE_TO_POLICY_OWNER`   | The issue requires policy or boundary ownership             |
| `ESCALATE_TO_HUMAN_REVIEWER` | The issue requires final human decision                     |
| `BLOCK`                      | Unsafe or contradictory escalation state must stop          |

* No decision authorizes real agent execution.
* No decision authorizes automatic repair.
* No decision authorizes source modification.
* No decision authorizes comment posting, PR creation, merge, or deploy.

## Rotation policy

| Condition                                                            | Next recommended role | Reason code                             |
| -------------------------------------------------------------------- | --------------------- | --------------------------------------- |
| Same unresolved reason repeatedly returned to `implementation_agent` | `review_agent`        | `AGENT_ROTATION_REQUIRED`               |
| Same unresolved reason repeatedly returned to `review_agent`         | `policy_owner`        | `POLICY_OWNER_ESCALATION_REQUIRED`      |
| Same unresolved reason repeatedly returned to `policy_owner`         | `human_reviewer`      | `HUMAN_FINAL_DECISION_REQUIRED`         |
| Evidence is incomplete                                               | `human_reviewer`      | `ROTATION_EVIDENCE_INCOMPLETE`          |
| Prohibited automation behavior is observed                           | none                  | `PROHIBITED_ROTATION_BEHAVIOR_OBSERVED` |

* `human_reviewer` is terminal.
* Patch 9 must not rotate away from final human review.
* Patch 9 must not create an infinite role-rotation loop.

## Initial reason codes

| Reason code                             | Decision                     | Meaning                                                              |
| --------------------------------------- | ---------------------------- | -------------------------------------------------------------------- |
| `NO_AGENT_ROTATION_REQUIRED`            | `NO_ROTATION_REQUIRED`       | No repeated unresolved same-role return is detected                  |
| `AGENT_ROTATION_REQUIRED`               | `ROTATION_RECOMMENDED`       | Same unresolved issue repeatedly returned to the implementation role |
| `REVIEW_AGENT_ESCALATION_REQUIRED`      | `ROTATION_RECOMMENDED`       | Independent review is required                                       |
| `POLICY_OWNER_ESCALATION_REQUIRED`      | `ESCALATE_TO_POLICY_OWNER`   | Policy or boundary ownership is required                             |
| `HUMAN_FINAL_DECISION_REQUIRED`         | `ESCALATE_TO_HUMAN_REVIEWER` | Final human decision is required                                     |
| `ROTATION_EVIDENCE_INCOMPLETE`          | `ESCALATE_TO_HUMAN_REVIEWER` | Evidence is incomplete                                               |
| `PROHIBITED_ROTATION_BEHAVIOR_OBSERVED` | `BLOCK`                      | Prohibited automation was attempted or implied                       |
| `ROTATION_LOOP_DETECTED`                | `BLOCK`                      | Logical role rotation became cyclic or unsafe                        |

## Advisory artifact clarification

* `next_recommended_agent_role` is advisory metadata only.
* `recommended_human_next_actions` are advisory labels only.
* These fields do not dispatch work.
* They do not launch agents.
* They do not post comments.
* They do not apply fixes.
* They do not create PRs.
* They do not merge.
* They do not deploy.

## Network and metadata boundary

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

Allowed only under the existing reviewed advisory boundary:

* read-only GitHub metadata access under read-only permissions
* GitHub Actions artifact upload for human review
* local deterministic artifact generation
* advisory-only review material generation

Read-only GitHub repository metadata access is not external AI provider access.

This clarification does not weaken the prohibition against AI provider calls, AI API keys, secrets, repair, automated PR creation, merge, or deploy.

## Safety boundary

Allowed:

* documentation/specification only
* define logical role-rotation semantics
* define logical escalation semantics
* define future artifact shape
* define future assertions
* define future fixture ideas as text only
* preserve human final decision boundary
* local deterministic artifact generation for human review if separately approved
* advisory-only review material generation
* read-only GitHub metadata access under read-only permissions if separately reviewed
* GitHub Actions artifact upload for human review if separately reviewed

Prohibited:

* runtime behavior
* workflow changes
* scripts
* tests
* generated output commits
* AI API calls
* external AI provider calls
* API keys or secrets
* actual agent execution
* automatic repair
* source file modification by verifier
* GitHub comment posting
* review comment posting
* issue creation
* PR creation
* auto-fix
* auto-commit-to-main
* auto-PR
* auto-merge
* deploy

## CI observation

* Workflow: Tasukeru Analysis
* Run number: 1063
* Status: completed
* Conclusion: success

CI evidence relates to the Patch 9 spec PR.

Runtime artifacts, if generated, were not committed to the repository.

## Relationship to other patches

* Patch 6 defines reasoned return.
* Patch 7 verifies revised submissions.
* Patch 8 detects mediation loops.
* Patch 9 recommends logical role rotation or escalation.
* Patch 10 may checkpoint and hand off unresolved state.
* Patch 9 does not implement Patch 10.

## Final status

Patch 9 specification phase is complete.

Patch 9 release note records the specification-only completion.

Human review remains the final decision boundary.
