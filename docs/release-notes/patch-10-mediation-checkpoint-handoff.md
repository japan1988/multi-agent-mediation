# Patch 10: Mediation checkpoint handoff release note

## Status

Patch 10 specification has been completed and merged.

This release note records completion of the Patch 10 specification-only phase.

Patch 10 remains specification-only.

Patch 10 does not implement runtime behavior.

Patch 10 does not execute real agents.

Patch 10 does not perform automatic resume.

Patch 10 completes the initial Patch 5-10 pseudo-orchestration specification sequence.

## Core summary

Patch 10 defines mediation checkpoint and handoff semantics.

A checkpoint preserves unresolved mediation state.

A handoff passes that preserved state to the next logical role for review.

Patch 10 preserves:

* where mediation stopped
* why mediation stopped
* unresolved reason codes
* completed checks
* failed checks
* loop evidence
* role-rotation evidence
* candidate hashes
* evidence hashes
* checkpoint lineage

Patch 10 recommends a next logical role but does not launch it.

Patch 10 does not repair.

Patch 10 does not modify source files.

Patch 10 does not resume automatically.

Human review remains the final decision boundary.

Patch 10は「エージェントを引き継ぐ」のではなく、  
「未解決の調停状態をcheckpointとして保存し、次のlogical roleへ渡す」。

Checkpoint means preservation of mediation state.  
Handoff means passing that preserved state to the next logical role.

## Checkpoint

Checkpoint means:

* preservation of mediation state
* preservation of completed checks
* preservation of failed checks
* preservation of unresolved issues
* preservation of evidence hashes
* preservation of checkpoint lineage
* preservation of the prior and recommended next logical role

## Handoff

Handoff means:

* the preserved checkpoint may be reviewed by the next logical role
* already completed checks should not be repeated unnecessarily
* unresolved reason codes remain visible
* evidence remains traceable
* human review remains required
* no real agent is launched
* no automatic continuation occurs

チェックポイント = 調停状態の保存  
引き継ぎ = チェックポイントを次のロールへ渡すこと

## Merged PR

* PR: #902
* Title: Add Patch 10 mediation checkpoint handoff spec
* Branch: patch-10-mediation-checkpoint-handoff-spec
* Base: main
* Head commit: f94e1a312c7aec9cb9674ffb22430d75bac5b417
* Merge commit: 221a38a5b2f0377e59ace07081252f96b01c0f45
* Merged at: 2026-07-14T03:43:41Z

## Changed files

The Patch 10 specification PR added exactly one file:

```text
A docs/specs/patch-10-mediation-checkpoint-handoff.md
```

## Specification PR statistics

```text
1 file changed
666 insertions
0 deletions
```

* No workflow files were changed.
* No script files were changed.
* No test files were changed.
* No README file was changed.
* No release note was changed by the specification PR.
* No generated outputs were committed.
* No `analysis_results/` files were committed.
* No `stress_results/` files were committed.

## Specification file

```text
docs/specs/patch-10-mediation-checkpoint-handoff.md
```

The specification defines:

* checkpoint semantics
* handoff semantics
* logical roles
* logical inputs
* checkpoint fields
* decisions
* reason codes
* checkpoint integrity rules
* advisory handoff policy
* future artifact shapes
* advisory artifact clarification
* future assertions
* future fixture ideas
* network and metadata boundary
* safety boundary
* completion of the initial Patch 5-10 specification sequence

## Logical roles

| Logical role           | Meaning                                                   |
| ---------------------- | --------------------------------------------------------- |
| `implementation_agent` | Logical role that prepares or revises candidate material  |
| `review_agent`         | Logical role that independently reviews unresolved issues |
| `policy_owner`         | Logical role that reviews policy or boundary questions    |
| `human_reviewer`       | Final human decision role                                 |

* These are labels only.
* They do not launch real agents.
* They do not call Codex or OpenAI.
* They do not trigger workflow jobs.
* They do not post GitHub comments.
* They do not create issues or pull requests.

## Checkpoint fields

| Field                              | Requirement                             |
| ---------------------------------- | --------------------------------------- |
| `checkpoint_id`                    | Stable checkpoint identifier            |
| `checkpoint_parent_id`             | Optional previous checkpoint identifier |
| `current_patch_stage`              | Current mediation stage                 |
| `previous_agent_role`              | Previous logical role                   |
| `next_recommended_agent_role`      | Advisory-only next logical role         |
| `decision`                         | Current checkpoint decision             |
| `reason_code`                      | Primary reason code                     |
| `unresolved_reason_codes`          | Reasons still unresolved                |
| `completed_checks`                 | Checks already completed                |
| `failed_checks`                    | Checks that failed                      |
| `attempt_count`                    | Total mediation attempts                |
| `role_attempt_counts`              | Attempts by logical role                |
| `loop_detected`                    | Whether a loop was detected             |
| `loop_type`                        | Detected loop type                      |
| `candidate_hashes`                 | Stable candidate hashes                 |
| `evidence_hashes`                  | Supporting evidence hashes              |
| `handoff_required`                 | Whether handoff review is recommended   |
| `requires_human_review`            | True for unresolved states              |
| `final_decider`                    | Must be `human`                         |
| `auto_corrected`                   | Must be false                           |
| `source_files_modified`            | Must be false                           |
| `real_agent_executed`              | Must be false                           |
| `checkpoint_applied_automatically` | Must be false                           |
| `handoff_executed_automatically`   | Must be false                           |

## Decisions

| Decision               | Meaning                                                                  |
| ---------------------- | ------------------------------------------------------------------------ |
| `CHECKPOINT_CREATED`   | A valid checkpoint was preserved for review                              |
| `HANDOFF_RECOMMENDED`  | Review by another logical role is recommended                            |
| `NEEDS_HUMAN_DECISION` | Human decision is required before continuation                           |
| `BLOCK`                | Unsafe, contradictory, incomplete, or prohibited handoff state must stop |

* `CHECKPOINT_CREATED` does not mean processing resumed.
* `HANDOFF_RECOMMENDED` is advisory-only.
* No decision authorizes automatic resume.
* No decision authorizes real agent execution.
* No decision authorizes source modification.
* No decision authorizes PR creation, merge, deploy, or external action.

## Initial reason codes

| Reason code                            | Decision               | Meaning                                         |
| -------------------------------------- | ---------------------- | ----------------------------------------------- |
| `CHECKPOINT_STATE_PRESERVED`           | `CHECKPOINT_CREATED`   | Mediation state was preserved successfully      |
| `HANDOFF_TO_REVIEW_AGENT_RECOMMENDED`  | `HANDOFF_RECOMMENDED`  | Review by `review_agent` is recommended         |
| `HANDOFF_TO_POLICY_OWNER_RECOMMENDED`  | `HANDOFF_RECOMMENDED`  | Policy or boundary review is recommended        |
| `HANDOFF_TO_HUMAN_REVIEWER_REQUIRED`   | `NEEDS_HUMAN_DECISION` | Final human review is required                  |
| `UNRESOLVED_REASON_CODES_PRESENT`      | `NEEDS_HUMAN_DECISION` | One or more reason codes remain unresolved      |
| `CHECKPOINT_EVIDENCE_INCOMPLETE`       | `BLOCK`                | Required evidence is missing or incomplete      |
| `CHECKPOINT_HASH_MISMATCH`             | `BLOCK`                | Recorded hashes do not match available evidence |
| `CHECKPOINT_PARENT_MISMATCH`           | `BLOCK`                | Checkpoint lineage is inconsistent              |
| `PROHIBITED_HANDOFF_BEHAVIOR_OBSERVED` | `BLOCK`                | Handoff implied prohibited automation           |
| `AUTOMATIC_RESUME_ATTEMPTED`           | `BLOCK`                | Automatic checkpoint resume was attempted       |
| `REAL_AGENT_EXECUTION_ATTEMPTED`       | `BLOCK`                | Real agent execution was attempted              |
| `HUMAN_FINAL_DECISION_REQUIRED`        | `NEEDS_HUMAN_DECISION` | Human final decision remains required           |

## Checkpoint integrity

* checkpoint IDs should be stable and deterministic when possible
* evidence hashes must be preserved
* candidate hashes must not be silently changed
* unresolved reasons must not be removed without evidence
* failed checks must not become passed automatically
* checkpoint lineage must remain traceable
* contradictory state must remain contradictory
* incomplete state must not be normalized into a safe-looking checkpoint
* checkpoint creation must not modify source files
* checkpoint creation must not trigger execution

矛盾をcheckpointで隠してはならない。  
未解決状態を「解決済み」に変換してはならない。

## Advisory handoff policy

| Condition                                        | Recommended next role | Reason code                                                |
| ------------------------------------------------ | --------------------- | ---------------------------------------------------------- |
| Implementation issue remains unresolved          | `review_agent`        | `HANDOFF_TO_REVIEW_AGENT_RECOMMENDED`                      |
| Review cannot resolve a policy or boundary issue | `policy_owner`        | `HANDOFF_TO_POLICY_OWNER_RECOMMENDED`                      |
| Policy owner cannot resolve the issue            | `human_reviewer`      | `HANDOFF_TO_HUMAN_REVIEWER_REQUIRED`                       |
| Maximum attempts are reached                     | `human_reviewer`      | `HUMAN_FINAL_DECISION_REQUIRED`                            |
| Evidence is incomplete                           | none                  | `CHECKPOINT_EVIDENCE_INCOMPLETE`                           |
| Hash or lineage mismatch exists                  | none                  | `CHECKPOINT_HASH_MISMATCH` or `CHECKPOINT_PARENT_MISMATCH` |
| Prohibited automation is observed                | none                  | `PROHIBITED_HANDOFF_BEHAVIOR_OBSERVED`                     |

* `human_reviewer` is terminal.
* Recommendations do not dispatch work.
* Recommendations do not start agents.
* Recommendations do not authorize continuation.
* Human review is required.

## Advisory artifact clarification

* `next_recommended_agent_role` is advisory metadata only.
* `recommended_human_next_actions` are advisory labels only.
* `handoff_required` does not trigger a handoff.
* `checkpoint_id` is not an execution token.
* `current_patch_stage` does not resume processing.
* `decision` does not authorize execution.
* No field dispatches work.
* No field launches agents.
* No field posts comments.
* No field applies fixes.
* No field creates pull requests.
* No field merges.
* No field deploys.

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

Read-only GitHub metadata access is not external AI provider access.

Artifact upload is not agent execution.

Checkpoint generation is not automatic resume.

Handoff recommendation is not automatic dispatch.

## Safety boundary

Allowed:

* documentation/specification only
* define checkpoint semantics
* define handoff semantics
* define checkpoint-integrity rules
* define future artifact shapes
* define future assertions
* define future fixture ideas as text only
* preserve human final decision authority
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
* automatic resume
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
* Run number: 1068
* Status: completed
* Conclusion: success

CI evidence relates to the Patch 10 specification PR.

Runtime artifacts were generated for review.

Runtime artifacts were not committed to the repository.

Detailed artifact contents are not reproduced in the public release note.

## Artifact observation

Only artifact names and SHA-256 digests are recorded.

* `tasukeru-advisory-logs`

  * `sha256:d0011d4cfba85ad3bb983655fa38376911825bf45d409f05e710bf41788e626b`
* `tasukeru-explainable-patch-proposals`

  * `sha256:2a915cffb77bc94e84463f1a80780a793c4e4b3708347720a23f4eda917d9040`
* `tasukeru-arl-stress-results`

  * `sha256:f740e5ce49027d1b7d19d8526cae3efe6138b83d1b74573557457c2c3ed95d26`
* `tasukeru-arl-analyzer-results`

  * `sha256:a9c1d81fbd3dcd4c86b12aaab83fed65f71d4b869502bc7789f1b41c3d4ae8ca`

No artifact IDs, download URLs, runner filesystem paths, detailed advisory findings, detailed source snippets, detailed file-and-line security findings, or exploit instructions are included.

## Patch 5-10 completion note

| Patch    | Specification role                    |
| -------- | ------------------------------------- |
| Patch 5  | Pseudo-orchestration structure        |
| Patch 6  | Reasoned return mediation gate        |
| Patch 7  | Revised-submission verification loop  |
| Patch 8  | Mediation loop guard                  |
| Patch 9  | Logical role-rotation escalation gate |
| Patch 10 | Mediation checkpoint handoff          |

* Patch 5 through Patch 10 form the initial pseudo-orchestration specification sequence.
* Completion of Patch 10 does not mean runtime implementation is complete.
* No real AI orchestration has been activated.
* No real agents are executed.
* Human review remains the final decision boundary.
* External verification, provenance attestation, and verifier-library work remain separate future phases.

## Relationship to future work

* Patch 10 does not implement external verification.
* Patch 10 does not implement artifact attestation.
* Patch 10 does not implement a public verifier library.
* Those capabilities require separate design, review, and approval.
* Any future implementation must preserve the no-AI-API, advisory-only, and human-final-decision boundaries unless explicitly reviewed in a separate patch.

## Final status

Patch 10 specification phase is complete.

Patch 10 release note records the specification-only completion.

The initial Patch 5-10 pseudo-orchestration specification sequence is complete.

Runtime implementation remains separate future work.

Human review remains the final decision boundary.
