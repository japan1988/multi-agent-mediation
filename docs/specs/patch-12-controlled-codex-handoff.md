# Patch 12: Controlled Codex handoff

## Status

Patch 12 is specification-only.

Patch 12 is documentation-only.

Patch 12 is advisory-only.

Patch 12 is non-executing.

Patch 12 is non-authorizing by itself.

Patch 12 is not a runtime implementation.

Patch 12 is not a workflow modification.

Patch 12 is not an AI API integration.

Patch 12 is not permission for Codex to create a pull request during this specification task.

Creation of this specification does not enable Codex-created pull requests.

No repository permission, workflow permission, runtime execution authority, merge authority, or deployment authority is created by this document.

## Purpose

Patch 12 defines a controlled handoff protocol between:

- a human owner
- GPT acting as a design and review advisor
- Codex acting as a limited implementation executor
- GitHub and CI acting as evidence sources

The protocol describes a stage-gated path in which GPT prepares an implementation prompt, a human owner explicitly approves that prompt, Codex implements only the approved scope, GPT reviews the resulting evidence, a human owner separately authorizes one pull-request creation, Codex creates exactly one pull request and stops, GPT reviews the pull request and CI evidence, and a human owner alone makes the final merge decision.

Patch 12 allows future consideration of a human-authorized, single pull-request creation by Codex.

Patch 12 preserves this project boundary:

"AI-like orchestration may be represented structurally, but workflow execution must not call AI APIs or external AI providers."

## Scope

Patch 12 defines specification rules for controlled Codex handoff.

The scope is limited to:

- stage-specific authorization boundaries
- single-use pull-request authorization rules
- evidence requirements
- review outcomes
- invalidation rules
- duplicate and retry handling
- compatibility with Patch 6 through Patch 11
- security and privacy boundaries

The specification describes how future review-only materials may represent a handoff. It does not implement that handoff.

## Non-goals

Patch 12 does not authorize or implement:

- automatic pull-request creation
- continuous or reusable pull-request authority
- automatic retries
- automatic merge
- deployment
- automatic continuation between stages
- self-authorization by GPT or Codex
- runtime orchestration
- real agent execution
- workflow changes
- script changes
- source-code changes
- test changes
- repository setting changes
- permission changes
- AI API calls
- external AI provider calls
- API keys or secrets

## Core authorization principle

"Authorization is stage-specific, single-use, and non-transitive. Approval to implement does not authorize pull-request creation. Approval to create a pull request does not authorize merge or deployment."

This principle means:

- silence is not authorization
- prior approval is not authorization for a later stage
- general approval is not sufficient for a repository write action
- ambiguous approval must be treated as no approval
- authorization cannot be inferred from efficiency claims
- Codex must not expand the meaning of a human instruction
- GPT review is advisory and does not replace human authorization
- a human final decision remains mandatory

## Roles and authority boundaries

### Human owner

The human owner:

- defines project intent
- approves the implementation prompt
- decides whether implementation may begin
- reviews advisory findings
- separately authorizes a single pull-request creation
- makes the final merge decision
- may revoke authorization at any time before use

The human owner is the only final authority.

### GPT design and review advisor

GPT may:

- prepare a Codex implementation prompt
- define scope and validation requirements
- inspect branch comparisons, commits, diffs, pull-request metadata, and CI evidence
- identify inconsistencies and risks
- recommend `REVIEW_OK`, `NEEDS_CHANGES`, or `BLOCK`

GPT must not:

- grant repository permission
- substitute its review for human approval
- authorize pull-request creation
- authorize merge or deployment
- silently change the approved implementation scope

### Codex implementation executor

Codex may act only within the currently authorized stage.

During implementation, Codex may perform only explicitly approved actions, such as:

- create the specified branch
- modify approved files
- run approved local validation
- create the specified commit
- report evidence

Codex must not infer authority to:

- create a pull request
- merge
- deploy
- modify repository settings
- broaden file scope
- add permissions
- perform unrelated cleanup
- continue to a later stage

### GitHub and CI evidence sources

GitHub and CI provide evidence such as:

- commit SHA
- branch comparison
- changed file list
- additions and deletions
- pull-request metadata
- review status
- workflow status
- CI conclusion

GitHub status or CI status does not itself grant authorization.

## Handoff stages

Patch 12 defines these logical stages:

1. `PROMPT_DRAFTED`
2. `IMPLEMENTATION_APPROVAL_REQUIRED`
3. `IMPLEMENTATION_AUTHORIZED`
4. `IMPLEMENTATION_IN_PROGRESS`
5. `IMPLEMENTATION_COMPLETE`
6. `GPT_REVIEW_REQUIRED`
7. `CHANGES_REQUIRED`
8. `PR_AUTHORIZATION_REQUIRED`
9. `PR_AUTHORIZED_ONCE`
10. `PR_CREATION_IN_PROGRESS`
11. `PR_CREATED`
12. `CI_REVIEW_REQUIRED`
13. `READY_FOR_HUMAN_MERGE_DECISION`
14. `BLOCKED`

These are logical specification states only.

Patch 12 does not implement a state machine.

## State model

The state model is an audit description of where a controlled handoff stands.

Each state should be treated as a label for review evidence, not as executable control flow.

A state record, if implemented in a future reviewed patch, should identify:

- current stage
- repository
- base branch
- head branch, when applicable
- expected head SHA, when applicable
- relevant authorization record, when applicable
- review outcome, when applicable
- reason code, when applicable
- evidence references
- blocking condition, when applicable

The state model must fail closed when required evidence is missing, ambiguous, stale, revoked, reused, or mismatched.

## Stage-transition rules

Required transitions are:

- `PROMPT_DRAFTED` -> human review -> `IMPLEMENTATION_APPROVAL_REQUIRED`
- `IMPLEMENTATION_APPROVAL_REQUIRED` -> explicit human approval -> `IMPLEMENTATION_AUTHORIZED`
- `IMPLEMENTATION_AUTHORIZED` -> Codex begins the approved task -> `IMPLEMENTATION_IN_PROGRESS`
- `IMPLEMENTATION_IN_PROGRESS` -> approved work and validation complete -> `IMPLEMENTATION_COMPLETE`
- `IMPLEMENTATION_COMPLETE` -> GitHub evidence available -> `GPT_REVIEW_REQUIRED`
- `GPT_REVIEW_REQUIRED` -> review finds correct scope and acceptable evidence -> `PR_AUTHORIZATION_REQUIRED`
- `GPT_REVIEW_REQUIRED` -> review finds correctable problems -> `CHANGES_REQUIRED`
- `GPT_REVIEW_REQUIRED` -> review finds prohibited behavior -> `BLOCKED`
- `CHANGES_REQUIRED` -> new or revised human-approved implementation instruction -> `IMPLEMENTATION_AUTHORIZED`
- `PR_AUTHORIZATION_REQUIRED` -> explicit, valid, single-use human authorization -> `PR_AUTHORIZED_ONCE`
- `PR_AUTHORIZED_ONCE` -> Codex invokes exactly one pull-request creation action -> `PR_CREATION_IN_PROGRESS`
- `PR_CREATION_IN_PROGRESS` -> pull request successfully created -> `PR_CREATED`
- `PR_CREATED` -> pull request and CI review -> `CI_REVIEW_REQUIRED`
- `CI_REVIEW_REQUIRED` -> review evidence is complete -> `READY_FOR_HUMAN_MERGE_DECISION`

Any invalid, ambiguous, expired, reused, or mismatched authorization must transition to `BLOCKED`.

No transition may occur automatically merely because the previous stage completed.

## Implementation authorization

Implementation authorization must identify:

- repository
- base branch
- new working branch
- task purpose
- allowed file paths
- prohibited file paths
- required validation
- required commit message
- prohibited actions
- completion report requirements

Implementation authorization permits implementation and commit creation only.

It does not authorize:

- pull-request creation
- GitHub comments
- reviewer requests
- label changes
- issue creation
- merge
- deployment
- repository setting changes

A completed implementation stage must stop and report evidence.

## GPT review gate

The GPT review gate must inspect, where available:

- branch name
- base branch
- head SHA
- commit count
- changed files
- file status
- additions and deletions
- full changed-file content or diff
- validation results
- scope compliance
- secrets or confidential information
- workflow changes
- source or test changes
- external integrations
- unexpected repository actions

GPT review outcomes are limited to:

- `REVIEW_OK`
- `NEEDS_CHANGES`
- `BLOCK`

`REVIEW_OK` is advisory.

`REVIEW_OK` does not create pull-request authority.

`NEEDS_CHANGES` requires a new implementation instruction or approval.

`BLOCK` prevents continuation under the current handoff.

Missing evidence must not produce `REVIEW_OK`.

## Pull-request authorization

Pull-request creation is a separate repository write action.

Before Codex may create a pull request, all of these conditions must be satisfied:

- implementation is complete
- the implementation commit exists
- GPT review returned `REVIEW_OK`
- the human owner has reviewed the implementation evidence
- the human owner explicitly authorizes one pull-request creation
- the authorization is bound to the exact repository
- the authorization is bound to the exact head branch
- the authorization is bound to the exact base branch
- the authorization is bound to the exact expected head SHA
- the pull-request title is approved
- the pull-request body is approved
- authorization has not previously been consumed
- authorization has not been revoked
- no conflicting pull request already exists

Patch 11 classification of `ESCALATE_TO_HITL` identifies that human judgment is required.

Patch 11 `ESCALATE_TO_HITL` is not itself permission to create a pull request.

Patch 12 requires a separate explicit human authorization record after the HITL review.

### Canonical human authorization template

```text
I authorize Codex to create exactly one pull request for:

Repository: <owner/repository>
Head branch: <head-branch>
Expected head SHA: <full-commit-sha>
Base branch: <base-branch>
Approved PR title: <exact-title>
Approved PR body SHA-256: <sha256-of-approved-body>

This authorization permits one pull-request creation action only.

It does not authorize file modification, additional commits, branch
changes, force-push, comments, labels, reviewer requests, issue creation,
merge, auto-merge, deployment, retry, or any later-stage action.
```

Equivalent explicit wording may be accepted only when all required binding fields and prohibitions are unambiguous.

The following statements are insufficient:

- "continue"
- "go ahead"
- "do the next step"
- "finish it"
- "make it live"
- "handle the PR"
- prior approval of the implementation prompt
- GPT saying that the branch is ready

## Pull-request creation constraints

When a valid `PR_AUTHORIZED_ONCE` state exists, Codex may perform only the single pull-request creation action.

Required constraints:

- create exactly one pull request
- use the authorized repository
- use the authorized head branch
- use the authorized base branch
- verify the exact expected head SHA before creation
- use the exact approved title
- use the approved body whose SHA-256 matches the authorization
- do not modify files
- do not create commits
- do not amend commits
- do not rebase
- do not force-push
- do not create another branch
- do not change the base branch
- do not add labels
- do not request reviewers
- do not assign users
- do not post comments
- do not create issues
- do not enable auto-merge
- do not merge
- do not deploy
- do not retry after failure without new authorization

After successful creation, Codex must stop and report:

- pull-request number
- pull-request title
- pull-request state
- pull-request URL
- repository
- base branch
- head branch
- head SHA
- authorization ID
- confirmation that authorization was consumed
- confirmation that no merge or deployment occurred

## Post-creation boundary

After pull-request creation, Codex has no continuing authority.

The following require separate future human decisions:

- modifying the pull-request branch
- adding commits
- changing the pull-request title
- changing the pull-request body
- requesting reviewers
- adding labels
- posting comments
- rerunning failed jobs
- resolving review threads
- merge
- deployment

CI success does not authorize merge.

GPT review does not authorize merge.

A merge button becoming available does not authorize merge.

Only a human owner may make the final merge decision.

## Review outcomes

GPT review outcomes are:

- `REVIEW_OK`
- `NEEDS_CHANGES`
- `BLOCK`

`REVIEW_OK` means the reviewed evidence appears consistent with the approved scope and contains no identified blocker. It is advisory only and does not authorize pull-request creation, merge, deployment, or further repository action.

`NEEDS_CHANGES` means the reviewed evidence has correctable problems or incomplete implementation evidence. It requires a new or revised implementation instruction before Codex may continue.

`BLOCK` means the reviewed evidence shows prohibited behavior, scope violation, missing critical evidence, authorization mismatch, confidential-data exposure, or another condition that prevents continuation under the current handoff.

A review outcome is not authorization.

## Reason codes

Patch 12 defines these reason codes:

- `IMPLEMENTATION_APPROVAL_REQUIRED`
- `IMPLEMENTATION_SCOPE_MISMATCH`
- `IMPLEMENTATION_EVIDENCE_INCOMPLETE`
- `GPT_REVIEW_REQUIRED`
- `GPT_REVIEW_OK_ADVISORY_ONLY`
- `CHANGES_REQUIRE_NEW_APPROVAL`
- `PR_AUTHORIZATION_REQUIRED`
- `PR_AUTHORIZATION_MISSING`
- `PR_AUTHORIZATION_AMBIGUOUS`
- `PR_AUTHORIZATION_REVOKED`
- `PR_AUTHORIZATION_ALREADY_CONSUMED`
- `PR_AUTHORIZATION_HEAD_SHA_MISMATCH`
- `PR_AUTHORIZATION_BRANCH_MISMATCH`
- `PR_BODY_HASH_MISMATCH`
- `DUPLICATE_PR_DETECTED`
- `PR_CREATED_AWAITING_REVIEW`
- `PR_CREATION_FAILED_REAUTHORIZATION_REQUIRED`
- `CI_REVIEW_REQUIRED`
- `MERGE_HUMAN_ONLY`
- `PROHIBITED_AUTOMATION_ATTEMPT`
- `AUTHORIZATION_REUSE_ATTEMPT`

A reason code must not be used as authorization.

## Evidence requirements

Evidence must be preserved for each stage where applicable.

### Prompt stage evidence

- prompt version or hash
- task purpose
- allowed scope
- prohibited scope
- explicit human implementation approval

### Implementation evidence

- repository
- base branch
- working branch
- commit SHA
- changed file list
- additions and deletions
- validation results
- known validation limitations
- confirmation that no pull request was created

### GPT review evidence

- reviewed head SHA
- reviewed changed files
- reviewed diff or content
- review outcome
- review findings
- unresolved risks
- confirmation that review is advisory

### PR authorization evidence

- authorization ID
- exact repository
- exact branches
- exact expected head SHA
- exact approved title
- approved body SHA-256
- human authorization record
- unused authorization status

### PR creation evidence

- pull-request number
- pull-request URL
- actual title
- actual base branch
- actual head branch
- actual head SHA
- consumed authorization ID
- confirmation that no additional action occurred

### Post-creation evidence

- pull-request status
- CI status
- CI conclusion
- review-thread status where available
- requested changes where available
- final human merge decision

Evidence must not include secrets, credentials, tokens, private keys, or unnecessary private personal information.

## Authorization record

A logical authorization record should include at least:

- `authorization_id`
- `authorized_action`
- `repository`
- `head_branch`
- `expected_head_sha`
- `base_branch`
- `approved_pr_title`
- `approved_pr_body_sha256`
- `authorized_by_human`
- `authorized_at`
- `single_use`
- `status`
- `consumed_at`
- `revoked_at`
- `invalidation_reason`

Allowed `authorized_action`:

- `CREATE_SINGLE_PULL_REQUEST`

Allowed authorization status values:

- `UNUSED`
- `CONSUMED`
- `REVOKED`
- `INVALIDATED`

The authorization record is an audit concept only.

Patch 12 does not implement storage or authentication.

## Failure and invalidation rules

Authorization must be invalidated when:

- the head SHA changes
- the head branch changes
- the base branch changes
- the approved pull-request title changes
- the approved pull-request body changes
- the pull-request body hash does not match
- authorization is revoked
- authorization was already consumed
- authorization scope is ambiguous
- conflicting repository state is detected
- the approved implementation scope changes
- additional commits are added after review
- a prohibited action is requested

An invalidated authorization must not be repaired or silently updated by Codex.

A new human authorization is required.

## Duplicate and retry handling

Before creating a pull request, Codex must check whether an open or closed pull request already exists for the same head branch and intended base branch.

If an existing matching pull request is found:

- do not create another pull request
- do not modify the existing pull request
- report `DUPLICATE_PR_DETECTED`
- provide the existing pull-request number and state
- stop

If pull-request creation fails:

- do not retry automatically
- do not alter the branch
- do not alter the title or body
- report the failure
- transition to `BLOCKED`
- require a new human authorization before any retry

Each retry is a new repository write attempt and requires new authorization.

## Compatibility with Patch 6 through Patch 11

Patch 12 does not modify existing Patch 6 through Patch 11 documents.

Authoritative scopes are preserved:

- Patch 6: reasoned return mediation gate
- Patch 7: revised-submission verification
- Patch 8: mediation loop guard
- Patch 9: logical role-rotation escalation
- Patch 10: checkpoint and handoff semantics
- Patch 11: accountability and efficiency-justification classification
- Patch 12: controlled, stage-specific Codex handoff and authorization boundaries

Patch 10 remains authoritative for checkpoint and handoff semantics.

Patch 12 may define evidence that can later be referenced by a Patch 10 checkpoint, but Patch 12 must not change checkpoint decisions or resume execution.

Patch 11 remains authoritative for efficiency-based accountability classification.

A proposed Codex-created pull request is a repository write and external effect.

It must be classified through Patch 11 and escalated to HITL.

Patch 11 escalation is a requirement for human review, not permission.

Patch 12 defines the separate explicit authorization needed after that review.

## Security and privacy boundary

Patch 12 prohibits:

- AI API calls
- external AI provider calls
- API keys or secrets
- credential creation
- permission expansion
- workflow permission modification
- repository setting modification
- branch-protection modification
- auto-fix loops
- automatic commit loops
- automatic pull-request creation
- reusable pull-request authority
- automatic retry
- automatic merge
- deployment
- automatic resume
- self-authorization
- authorization inference
- hidden background execution
- private-data publication
- artifact upload to external services
- generated-output commits
- unrelated repository cleanup

A human-authorized single pull-request action is not automatic pull-request creation.

It is a separately approved, one-time repository write action bound to an exact head SHA and exact pull-request content.

## Examples

### Example 1: implementation only

A human owner approves an implementation-stage prompt allowing Codex to add one documentation file and commit it.

Codex creates the branch, file, validation result, and commit.

Codex stops without creating a pull request.

Result: `IMPLEMENTATION_COMPLETE`

Next state: `GPT_REVIEW_REQUIRED`

### Example 2: GPT review passes

GPT verifies one expected file, correct scope, no secrets, and no unexpected actions.

Outcome: `REVIEW_OK`

Result: `PR_AUTHORIZATION_REQUIRED`

No pull-request authority exists yet.

### Example 3: explicit one-time PR authorization

The human owner authorizes exactly one pull request for:

- repository
- head branch
- head SHA
- base branch
- title
- body hash

Codex creates one pull request and stops.

Result: `PR_CREATED`

Next state: `CI_REVIEW_REQUIRED`

### Example 4: vague instruction

The human owner says:

"Go ahead with the next step."

Result: `BLOCKED`

Reason: `PR_AUTHORIZATION_AMBIGUOUS`

No pull request is created.

### Example 5: head SHA changed

The human owner authorized SHA A, but the branch now points to SHA B.

Result: `BLOCKED`

Reason: `PR_AUTHORIZATION_HEAD_SHA_MISMATCH`

A new review and authorization are required.

### Example 6: duplicate PR

A pull request already exists from the authorized head branch to the authorized base branch.

Result: `BLOCKED`

Reason: `DUPLICATE_PR_DETECTED`

No second pull request is created.

### Example 7: PR creation failure

The authorized pull-request creation call fails.

Result: `BLOCKED`

Reason: `PR_CREATION_FAILED_REAUTHORIZATION_REQUIRED`

Codex does not retry automatically.

### Example 8: CI success

CI completes successfully after pull-request creation.

Result: `READY_FOR_HUMAN_MERGE_DECISION`

CI success does not merge or authorize merge.

### Example 9: automatic merge request

A prompt asks Codex to create and automatically merge a pull request.

Result: `BLOCKED`

Reason: `PROHIBITED_AUTOMATION_ATTEMPT`

## Acceptance criteria

Patch 12 is acceptable only if:

- exactly one new documentation file is added
- the file is `docs/specs/patch-12-controlled-codex-handoff.md`
- no existing file is modified
- no workflow is changed
- no script is changed
- no source code is changed
- no test is changed
- no generated artifact is created
- no AI API integration is added
- no external AI provider integration is added
- no secret is added
- no repository permission is changed
- no pull-request authority is implemented
- no pull request is created by this task
- no merge or deployment occurs
- the specification clearly separates implementation approval from pull-request authorization
- the specification binds pull-request authorization to an exact head SHA
- the specification makes authorization single-use and non-transitive
- the specification prohibits automatic retry
- the specification preserves human final merge authority
- Patch 6 through Patch 11 remain unchanged

## Future implementation notes

Future implementation requires a separate reviewed patch.

Possible future components may include:

- a local deterministic handoff validator
- a machine-readable authorization record
- SHA-256 verification of approved pull-request text
- duplicate-pull-request detection
- head-SHA binding validation
- evidence-bundle generation
- review-only GitHub metadata inspection

Patch 12 does not authorize implementation.

Patch 12 does not define API keys or secrets.

Patch 12 does not add GitHub Actions permissions.

Patch 12 does not add live connector execution.

Patch 12 does not call AI APIs.

Any future implementation must be fail-closed.
