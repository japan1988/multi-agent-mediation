# Patch 12 release note: Controlled implementation handoff

## Status

Patch 12 is released as a specification. It is documentation-only, advisory-only, non-executing, and non-authorizing by itself.

It is not a runtime implementation, a workflow modification, or an AI API integration. This release does not itself grant permission to create a pull request, merge, deploy, modify repository settings, or continue to another stage.

## Role-based terminology

This release note uses role-based terminology and does not require, endorse, or depend on any specific company, model, product, provider, service, or repository platform.

- `Human Owner`: provides final approval and makes the final merge decision.
- `Design and Review Advisor`: prepares instructions and provides advisory evidence review without granting repository authority.
- `Implementation Executor`: performs only explicitly approved work for the current stage and cannot broaden the approved instructions.
- `Repository and CI Evidence Sources`: provide review evidence but do not grant authority.

## Summary

Patch 12 defines a controlled, stage-gated implementation handoff between the `Human Owner`, the `Design and Review Advisor`, the `Implementation Executor`, and `Repository and CI Evidence Sources`.

The specified sequence is:

1. Implementation instructions are prepared.
2. The Human Owner explicitly approves implementation.
3. The Implementation Executor performs only the approved work.
4. An Advisory Review evaluates the implementation evidence.
5. The Human Owner separately authorizes exactly one pull-request creation.
6. The Implementation Executor creates exactly one pull request and stops.
7. Repository and CI evidence are reviewed.
8. The Human Owner alone makes the final merge decision.

Completion of one stage does not authorize the next stage.

## Core authorization principle

Authorization is stage-specific, single-use, and non-transitive.
Approval to implement does not authorize pull-request creation.
Approval to create a pull request does not authorize merge or deployment.

Silence is not authorization. Ambiguous wording is not authorization. Prior-stage approval does not transfer, efficiency does not expand authority, and Advisory Review does not grant repository authority. The Implementation Executor cannot broaden instructions, and final human authority remains mandatory.

## What Patch 12 defines

- role-based authority boundaries
- stage-specific authorization
- separate implementation and pull-request authorization
- single-use pull-request authorization
- non-transitive authorization
- exact repository binding
- exact head-branch binding
- exact base-branch binding
- exact expected-head-SHA binding
- exact approved-title binding
- approved-body SHA-256 binding
- Advisory Review outcomes
- evidence requirements
- authorization invalidation
- duplicate-pull-request blocking
- fail-closed retry handling
- post-creation stop requirements
- human-only final merge authority
- compatibility with Patch 6 through Patch 11

These rules are specification requirements, not implemented runtime code.

## Logical handoff states

The 14 logical states are:

1. `PROMPT_DRAFTED`
2. `IMPLEMENTATION_APPROVAL_REQUIRED`
3. `IMPLEMENTATION_AUTHORIZED`
4. `IMPLEMENTATION_IN_PROGRESS`
5. `IMPLEMENTATION_COMPLETE`
6. `ADVISORY_REVIEW_REQUIRED`
7. `CHANGES_REQUIRED`
8. `PR_AUTHORIZATION_REQUIRED`
9. `PR_AUTHORIZED_ONCE`
10. `PR_CREATION_IN_PROGRESS`
11. `PR_CREATED`
12. `CI_REVIEW_REQUIRED`
13. `READY_FOR_HUMAN_MERGE_DECISION`
14. `BLOCKED`

They are logical specification states and audit labels. Patch 12 does not
implement an executable state machine.

## Advisory Review outcomes

- `REVIEW_OK`
- `NEEDS_CHANGES`
- `BLOCK`

`REVIEW_OK` is advisory only and does not authorize pull-request creation.
`NEEDS_CHANGES` requires new or revised Human Owner approval. `BLOCK`
prevents continuation. Missing evidence must not produce `REVIEW_OK`.
No review outcome grants repository permission or authorizes merge or
deployment.

## Reason-code vocabulary

- `IMPLEMENTATION_APPROVAL_REQUIRED`
- `IMPLEMENTATION_SCOPE_MISMATCH`
- `IMPLEMENTATION_EVIDENCE_INCOMPLETE`
- `ADVISORY_REVIEW_REQUIRED`
- `ADVISORY_REVIEW_OK_NON_AUTHORIZING`
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

Reason codes are evidence labels and do not grant authorization.

## Pull-request authorization boundary

Pull-request creation is a separate repository write action. Authorization
must be separately provided by the Human Owner and bound to:

- repository
- head branch
- expected head SHA
- base branch
- approved pull-request title
- approved pull-request body SHA-256
- unused authorization status
- non-revoked authorization status
- absence of a conflicting pull request

Implementation approval alone is insufficient. An advisory statement that
a branch is ready is also insufficient. Vague phrases such as `continue`,
`go ahead`, or `finish it` do not provide authorization.

A compact role-neutral authorization record identifies the authorized
single action and every binding above, and states that it does not authorize
file changes, additional commits, branch changes, comments, labels,
reviewer requests, merge, deployment, retry, or any later-stage action.

## Duplicate, failure, and retry behavior

An existing matching pull request blocks creation of another one. The
Implementation Executor must not modify it and must report
`DUPLICATE_PR_DETECTED`.

Pull-request creation failure transitions to `BLOCKED`. No automatic retry
is allowed. A retry is a new repository write attempt and requires new
Human Owner authorization. Failed authorization must not be silently
repaired or updated, and authorization reuse is prohibited.

## Post-creation boundary

After successful pull-request creation:

- authorization is consumed
- the Implementation Executor stops
- no continuing authority exists
- no file modification is authorized
- no additional commit is authorized
- no comment, label, reviewer request, merge, or deployment is authorized
- CI success does not authorize merge
- review success does not authorize merge
- mergeability does not authorize merge
- only the Human Owner makes the final merge decision

## Evidence model

The specification preserves evidence for:

- implementation instructions
- Human Owner implementation approval
- branch and base information
- commit SHA
- changed files
- additions and deletions
- validation results
- Advisory Review outcome
- authorization ID
- approved branches
- expected head SHA
- approved title
- approved body SHA-256
- authorization consumption
- pull-request record and attributes
- CI status
- final human decision

Evidence does not grant authorization. It must not contain secrets,
credentials, private keys, tokens, or unnecessary personal information.

## Compatibility with earlier patches

The authoritative scopes remain:

- Patch 6: reasoned return mediation gate
- Patch 7: revised-submission verification
- Patch 8: mediation loop guard
- Patch 9: logical role-rotation escalation
- Patch 10: checkpoint and handoff semantics
- Patch 11: accountability and efficiency-justification classification
- Patch 12: controlled, stage-specific implementation handoff and
  authorization boundaries

Patch 10 remains authoritative for checkpoint and handoff semantics. Patch
11 remains authoritative for accountability classification. An
executor-created pull request is a repository write and external effect.
Patch 11 escalation requires human review, but `ESCALATE_TO_HITL` is not
authorization. Patch 12 defines the later, separate authorization boundary.
Patch 6 through Patch 11 are unchanged.

## Security and privacy boundary

Patch 12 does not add or authorize:

- AI API calls
- external AI provider calls
- API keys
- secrets
- credentials
- permission expansion
- workflow permission modification
- repository-setting modification
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
- inferred authorization
- hidden background execution
- private-data publication
- external artifact upload
- generated-output commits
- unrelated repository cleanup

A separately approved one-time repository write is not the same as
automatic pull-request creation.

## Scenario coverage

1. **Implementation only:** approved implementation ends at
   `IMPLEMENTATION_COMPLETE`, followed by `ADVISORY_REVIEW_REQUIRED`; no
   pull request is created.
2. **Advisory Review passes:** `REVIEW_OK` leads to
   `PR_AUTHORIZATION_REQUIRED`, without creating authority.
3. **Explicit one-time pull-request authorization:** a correctly bound,
   single-use approval permits one creation, resulting in `PR_CREATED` and
   then `CI_REVIEW_REQUIRED`.
4. **Vague instruction:** ambiguous wording results in `BLOCKED` with
   `PR_AUTHORIZATION_AMBIGUOUS`.
5. **Expected head SHA changed:** a mismatch results in `BLOCKED` with
   `PR_AUTHORIZATION_HEAD_SHA_MISMATCH`; new review and authorization are
   required.
6. **Duplicate pull request:** an existing matching request results in
   `BLOCKED` with `DUPLICATE_PR_DETECTED`; no second request is created.
7. **Pull-request creation failure:** failure results in `BLOCKED` with
   `PR_CREATION_FAILED_REAUTHORIZATION_REQUIRED`; no automatic retry occurs.
8. **CI success:** successful CI leads to
   `READY_FOR_HUMAN_MERGE_DECISION`, but does not authorize or perform
   merge.
9. **Automatic merge request:** a request to create and automatically merge
   results in `BLOCKED` with `PROHIBITED_AUTOMATION_ATTEMPT`.

## What this release does not change

This release does not modify:

- runtime behavior
- source code
- tests
- workflows
- configuration
- dependencies
- repository permissions
- branch protection
- existing Patch 6 through Patch 11 specifications
- merge authority
- deployment authority

The terminology correction does not weaken or expand any authorization
boundary.

## Known limitations

Patch 12:

- is specification-only
- does not implement a state machine
- does not store authorization records
- does not authenticate authorization records
- does not create pull requests
- does not inspect live repository state at runtime
- does not call external connectors
- does not retry failed repository writes
- does not merge
- does not deploy

These are deliberate scope boundaries rather than defects.

## Release traceability

- Initial Patch 12 specification: `PR #906`
- Role-neutral terminology correction: `PR #907`
- Normative specification:
  `docs/specs/patch-12-controlled-implementation-handoff.md`

## Future work

Future implementation requires a separate reviewed patch. Possible future
components may include:

- a local deterministic handoff validator
- a machine-readable authorization record
- SHA-256 verification of approved pull-request text
- duplicate-pull-request detection
- expected-head-SHA validation
- evidence-bundle generation
- review-only inspection of repository state attributes

This release does not authorize live pull-request creation, external
connectors, secrets, workflow permission changes, AI API calls, automatic
merge, or deployment.
