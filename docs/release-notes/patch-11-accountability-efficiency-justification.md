# Patch 11 release note: Accountability efficiency justification

## Status

Patch 11 specification is complete.

PR #904 was merged into `main`.

This release note does not add implementation.

No runtime behavior is introduced.

No workflow behavior is changed.

No execution authority is added.

Patch 11 remains specification-only, documentation-only, advisory-only, non-executing, non-authorizing, and dependent on human final decision.

## Release summary

Patch 11 defines an accountability rule for proposals where efficiency is used as justification.

Efficiency may be supporting context. Efficiency alone is not sufficient when a proposal changes any of the following:

- permissions or authority
- write capability
- safety controls
- external effects
- external network side effects
- confidential information flow
- automatic repository behavior
- automatic execution behavior

The release note records the merged specification boundary. It does not create runtime classification behavior.

## Merged specification

- PR number: #904
- PR title: `Add Patch 11 accountability efficiency justification spec`
- specification commit: `bc5d1cee390b5f55dc33a15275f7d62ad2d928b6`
- merge commit: `c6f6c9b9f0afa22e08dc8f00968664d3943bca25`
- specification path: `docs/specs/patch-11-accountability-efficiency-justification.md`
- changed files: 1
- additions: 327
- deletions: 0

## Core accountability principle

"Efficiency alone cannot justify automation that expands authority, weakens safety controls, produces external effects, or moves confidential information."

This principle is a review and accountability boundary. It is not an automatic execution rule and does not authorize repository changes.

## Decision model

### `NORMAL_REVIEW`

Use when:

- the efficiency improvement is low risk
- it remains within existing permissions
- it remains within existing safety boundaries
- it adds no prohibited external or execution authority

`NORMAL_REVIEW` does not automatically approve a change.

### `ESCALATE_TO_HITL`

Use when efficiency is the only stated justification and the proposal includes one or more of:

- authority expansion
- new write capability
- external side effects
- external network side effects
- safety-boundary change
- confidential-data movement
- automatic repository action
- automatic execution or resume behavior

`ESCALATE_TO_HITL` records the need for human judgment. It does not grant permission.

### `BLOCK`

Use when:

- explicitly prohibited behavior is present
- an established safety boundary is bypassed
- automatic merge or deployment is proposed
- the proposal attempts to avoid required human review

`BLOCK` does not perform remediation or modification.

## Decision precedence

`BLOCK` before `ESCALATE_TO_HITL` before `NORMAL_REVIEW`

Prohibited behavior takes precedence over efficiency claims.

HITL escalation takes precedence over normal review.

Missing evidence must not be treated as approval.

## Reason-code summary

- `LOW_RISK_WITHIN_EXISTING_AUTHORITY`: the proposed efficiency improvement is low risk and remains within existing permissions and safety boundaries.
- `EFFICIENCY_ONLY_AUTHORITY_EXPANSION`: efficiency is the only stated justification and the proposal expands authority or permissions.
- `EFFICIENCY_ONLY_EXTERNAL_EFFECT`: efficiency is the only stated justification and the proposal creates external side effects.
- `EFFICIENCY_ONLY_SAFETY_BOUNDARY_CHANGE`: efficiency is the only stated justification and the proposal modifies or weakens a safety boundary.
- `EFFICIENCY_ONLY_CONFIDENTIAL_DATA_MOVEMENT`: efficiency is the only stated justification and the proposal moves, publishes, or transfers confidential information.
- `PROHIBITED_AUTOMATION_BEHAVIOR`: the proposal includes behavior that is explicitly prohibited by the project boundary.
- `INSUFFICIENT_JUSTIFICATION`: the evidence or justification is incomplete and must not be treated as approval.
- `HUMAN_DECISION_REQUIRED`: a human decision is required before any further action can be considered.

## HITL boundary

`ESCALATE_TO_HITL` must not:

- grant permission
- approve a change
- modify a checkpoint
- resume execution
- create a commit
- push a branch
- create a pull request
- merge a pull request
- deploy anything

It only records that a human decision is required.

Human final decision remains mandatory.

## Evidence expectations

A future classification should preserve evidence about:

- the proposed change
- the claimed efficiency benefit
- independent non-efficiency justification, if any
- current and requested permissions
- current and proposed write capabilities
- external effects
- safety controls before and after
- confidential-information movement
- automatic repository or execution behavior
- selected decision and reason code

Incomplete evidence is not approval.

## Compatibility with Patch 6 through Patch 10

Patch 11:

- does not modify Patch 6
- does not modify Patch 7
- does not modify Patch 8
- does not modify Patch 9
- does not modify Patch 10
- does not change Patch 10 decision names
- does not change checkpoint semantics
- is an upstream accountability classification

Authoritative scopes:

- Patch 6: reasoned return mediation gate
- Patch 7: revised-submission verification
- Patch 8: mediation loop guard
- Patch 9: logical role-rotation escalation
- Patch 10: checkpoint and handoff semantics
- Patch 11: accountability and efficiency-justification classification

A Patch 11 result may later be represented in a checkpoint handoff, but Patch 11 itself does not create, modify, or resume checkpoints.

## Safety and execution boundary

Patch 11 introduces none of the following:

- AI API calls
- external AI provider calls
- API keys or secrets
- auto-fix
- automatic commit
- automatic push
- automatic pull-request creation
- automatic merge
- deployment
- runtime execution authority
- automatic resume
- real agent execution
- GitHub comment posting
- issue creation
- generated-output commits
- external service integration

The specification describes classification rules only.

## Verification

Verified facts recorded for Patch 11:

- PR #904 merged successfully
- Patch 11 specification exists on `main`
- one documentation file was added by the specification PR
- 327 additions and 0 deletions
- Tasukeru Analysis run #1072 completed successfully
- no runtime, workflow, source, or test changes were introduced by the specification
- human final decision remains required

No runtime classifier was executed or tested as part of Patch 11.

## Public documentation boundary

This release note contains:

- specification summary
- decision names
- reason-code summary
- verified commit metadata
- verified CI status
- safety boundaries

This release note does not contain:

- secrets
- credentials
- API keys
- tokens
- private personal data
- runner filesystem paths
- artifact download URLs
- private review details
- exploit instructions
- unverified claims

## Future work

Any future implementation requires a separate reviewed patch.

Possible future work may include:

- a deterministic local classifier
- evidence-backed classification artifacts
- a review-only verifier
- Patch 10 checkpoint-handoff representation
- controlled Codex handoff policy

This release note does not authorize or specify automatic pull-request creation.

Any proposal involving Codex-created pull requests remains outside the current Patch 11 implementation scope and requires separate HITL review and specification.

## Completion statement

Patch 11 specification and release note are complete.

Patch 11 remains specification-only.

No execution authority was introduced.

Human final decision remains mandatory.
