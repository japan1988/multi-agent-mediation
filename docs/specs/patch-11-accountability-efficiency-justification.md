# Patch 11: Accountability efficiency justification

## Status

Patch 11 is specification-only.

It does not implement runtime behavior.

It does not change workflows.

It does not change scripts.

It does not add tests.

It does not modify existing specifications or release notes.

It does not create generated outputs.

It does not call AI APIs or external AI providers.

It does not add API keys or secrets.

It does not grant runtime execution authority.

It only defines accountability and efficiency-justification rules for future review.

## Purpose

Patch 11 defines an independent accountability rule for reviewing efficiency-based automation proposals.

The purpose is to prevent efficiency claims from being used as the sole justification for:

- expanding permissions or authority
- adding write capability
- producing external effects
- creating external network side effects
- weakening safety controls
- moving, publishing, or transferring confidential information
- triggering automatic commit, push, pull request, merge, deployment, or execution

Patch 11 classifies such proposals before any future implementation or checkpoint handoff uses them.

Patch 11 does not approve, execute, resume, apply, commit, push, create pull requests, merge, or deploy anything.

## Scope

Patch 11 applies to proposed automation or workflow changes where efficiency is used as a justification.

Patch 11 may classify a proposal as:

- `NORMAL_REVIEW`
- `ESCALATE_TO_HITL`
- `BLOCK`

Patch 11 is an upstream accountability classification.

It does not replace Patch 6, Patch 7, Patch 8, Patch 9, or Patch 10.

It does not change Patch 10 decision names or checkpoint semantics.

## Non-goals

Patch 11 does not:

- implement an automation engine
- modify repository files beyond this specification
- weaken any existing safety boundary
- grant new permissions
- approve confidential data movement
- authorize external effects
- authorize external network side effects
- create or alter checkpoints automatically
- resume execution
- execute real agents
- call AI APIs
- create commits, pushes, pull requests, merges, or deployments

## Core accountability principle

"Efficiency alone cannot justify automation that expands authority, weakens safety controls, produces external effects, or moves confidential information."

This principle is fixed for Patch 11.

Efficiency can be considered as supporting context, but it is not sufficient by itself when a proposal changes authority, safety controls, external effects, or confidential information flow.

## Definitions

`efficiency_improvement` means a proposed change intended to reduce time, cost, repeated work, latency, manual effort, or review overhead.

`efficiency_only_justification` means efficiency is the only stated reason for a proposed change, with no independent safety, accountability, compliance, or human-review justification.

`authority_expansion` means any increase in permission, access, scope, write capability, execution authority, or ability to affect repository or external state.

`new_write_capability` means a new ability to write files, comments, issues, pull requests, branches, commits, deployments, external records, or other durable state.

`external_side_effect` means an effect outside the local advisory artifact boundary, including publishing, notifying, mutating external systems, or changing repository state.

`external_network_side_effect` means a network action that affects or transmits data to another service, especially where the service is not read-only GitHub metadata access under reviewed permissions.

`safety_boundary_change` means modification, weakening, bypass, removal, or reinterpretation of a safety control, HITL gate, review gate, permission boundary, or generated-output boundary.

`confidential_information` means secrets, API keys, tokens, credentials, non-public review details, private user data, or other information that should not be published or transferred without explicit authorization.

`HITL` means human-in-the-loop review and decision making.

## Input classification

A future implementation may classify proposals using logical inputs such as:

| Input | Meaning |
|---|---|
| `proposal_id` | Stable identifier for the proposed change |
| `proposal_summary` | Human-readable description of the proposed change |
| `stated_justifications` | Reasons supplied for the proposal |
| `efficiency_only_justification` | Whether efficiency is the only stated justification |
| `authority_expansion` | Whether the proposal expands permissions or authority |
| `new_write_capability` | Whether a new write capability is introduced |
| `external_side_effect` | Whether the proposal can affect external state |
| `external_network_side_effect` | Whether the proposal can create external network side effects |
| `safety_boundary_change` | Whether a safety boundary is changed or weakened |
| `confidential_data_movement` | Whether confidential information may move, publish, or transfer |
| `automatic_repository_action` | Whether commit, push, pull request, merge, or deploy behavior is automated |
| `automatic_execution` | Whether execution can start, resume, or continue automatically |
| `prohibited_behavior_present` | Whether explicitly prohibited behavior is present |
| `evidence` | Review evidence supporting classification |

These are logical artifact concepts only.

Patch 11 does not require live services, AI APIs, external providers, or runtime execution authority.

## Decision model

Patch 11 defines these decisions:

| Decision | Use when |
|---|---|
| `NORMAL_REVIEW` | The proposed efficiency improvement is low risk and remains entirely within existing permissions and safety boundaries |
| `ESCALATE_TO_HITL` | Efficiency is the only stated justification and the proposal includes authority expansion, new write capability, external side effects, external network side effects, safety-boundary change, confidential data movement, or automatic repository/execution behavior |
| `BLOCK` | The proposal contains explicitly prohibited behavior or attempts to bypass an established safety boundary |

`NORMAL_REVIEW` does not approve a change.

`ESCALATE_TO_HITL` does not approve a change.

`BLOCK` stops the proposal from proceeding under Patch 11 classification.

## Decision precedence

Decision precedence must be:

```text
BLOCK
before
ESCALATE_TO_HITL
before
NORMAL_REVIEW
```

If any explicitly prohibited behavior is present, the decision is `BLOCK` even if the proposal also claims efficiency benefits.

If no prohibited behavior is present but efficiency is the only justification for authority expansion, write capability, external effects, safety-boundary weakening, confidential data movement, or automatic execution behavior, the decision is `ESCALATE_TO_HITL`.

Only low-risk changes that remain inside existing permissions and safety boundaries may use `NORMAL_REVIEW`.

## Reason codes

Patch 11 defines these initial reason codes:

| Reason code | Decision | Meaning |
|---|---|---|
| `LOW_RISK_WITHIN_EXISTING_AUTHORITY` | `NORMAL_REVIEW` | The efficiency improvement is low risk and stays within existing authority and safety boundaries |
| `EFFICIENCY_ONLY_AUTHORITY_EXPANSION` | `ESCALATE_TO_HITL` | Efficiency is the only justification for permission or authority expansion |
| `EFFICIENCY_ONLY_EXTERNAL_EFFECT` | `ESCALATE_TO_HITL` | Efficiency is the only justification for an external effect or external network side effect |
| `EFFICIENCY_ONLY_SAFETY_BOUNDARY_CHANGE` | `ESCALATE_TO_HITL` | Efficiency is the only justification for changing or weakening a safety boundary |
| `EFFICIENCY_ONLY_CONFIDENTIAL_DATA_MOVEMENT` | `ESCALATE_TO_HITL` | Efficiency is the only justification for moving, publishing, or transferring confidential information |
| `PROHIBITED_AUTOMATION_BEHAVIOR` | `BLOCK` | The proposal includes explicitly prohibited automation behavior |
| `INSUFFICIENT_JUSTIFICATION` | `ESCALATE_TO_HITL` | The proposal lacks enough non-efficiency justification for the requested authority, side effect, or safety change |
| `HUMAN_DECISION_REQUIRED` | `ESCALATE_TO_HITL` | A human decision is required before any continuation |

A future implementation may add more reason codes only if they preserve this accountability principle.

## HITL requirements

`ESCALATE_TO_HITL` must not grant permission, resume execution, approve a change, or alter a checkpoint automatically.

It only records that a human decision is required.

A HITL record should preserve:

- the proposal summary
- the stated efficiency justification
- the authority or safety boundary affected
- the external side effect, if any
- the confidential information movement risk, if any
- the evidence used for classification
- the reason code
- the requirement for human decision

Human review remains mandatory before any continuation.

## Evidence requirements

A Patch 11 classification should be evidence-backed when implemented later.

Evidence should include:

- what change is proposed
- why efficiency is claimed
- whether any non-efficiency justification exists
- current permissions and requested permissions
- current write capabilities and proposed write capabilities
- external effects or external network side effects
- safety controls before and after the proposal
- confidential information involved, if any
- whether automatic commit, push, pull request, merge, deploy, or execution is involved
- why the selected decision and reason code were chosen

Missing evidence should not be treated as approval.

If evidence is incomplete and the proposal affects authority, safety, external effects, or confidential information, classify as `ESCALATE_TO_HITL` or `BLOCK` according to the decision precedence.

## Compatibility with Patch 6 through Patch 10

Patch 11 does not change Patch 10 decision names or checkpoint semantics.

Patch 11 is an upstream accountability classification.

A Patch 11 `ESCALATE_TO_HITL` result may be represented in a later checkpoint handoff, but Patch 11 itself must not create or resume execution.

Existing Patch 6 through Patch 10 documents remain authoritative for their own scopes.

Patch 6 remains authoritative for reasoned return mediation gate semantics.

Patch 7 remains authoritative for revised-submission verification semantics.

Patch 8 remains authoritative for mediation loop guard semantics.

Patch 9 remains authoritative for logical role-rotation escalation semantics.

Patch 10 remains authoritative for checkpoint and handoff semantics.

## Safety boundary

Allowed:

- documentation/specification only
- define accountability classification rules
- define efficiency-justification limits
- define decision precedence
- define HITL escalation semantics
- define future evidence requirements
- preserve human final decision authority

Prohibited:

- AI API calls
- external AI provider calls
- API keys or secrets
- auto-fix
- auto-commit
- auto-push
- auto-PR
- auto-merge
- deployment
- runtime execution authority
- automatic resume
- real agent execution
- GitHub comment posting
- issue creation
- modification of workflows, scripts, source code, or tests
- generated output commits
- weakening existing Patch 6 through Patch 10 boundaries

## Examples

| Example | Decision | Reason code |
|---|---|---|
| Local formatting improvement within existing permissions | `NORMAL_REVIEW` | `LOW_RISK_WITHIN_EXISTING_AUTHORITY` |
| Adding repository write permission only to save time | `ESCALATE_TO_HITL` | `EFFICIENCY_ONLY_AUTHORITY_EXPANSION` |
| Automatically sending artifacts to an external service for efficiency | `ESCALATE_TO_HITL` | `EFFICIENCY_ONLY_EXTERNAL_EFFECT` |
| Weakening a safety check to reduce execution time | `ESCALATE_TO_HITL` | `EFFICIENCY_ONLY_SAFETY_BOUNDARY_CHANGE` |
| Publishing confidential review details automatically | `ESCALATE_TO_HITL` or `BLOCK` | `EFFICIENCY_ONLY_CONFIDENTIAL_DATA_MOVEMENT` or `PROHIBITED_AUTOMATION_BEHAVIOR` |
| Automatic merge or deployment | `BLOCK` | `PROHIBITED_AUTOMATION_BEHAVIOR` |

Example notes:

- A local formatting improvement can remain in `NORMAL_REVIEW` only when it stays within existing permissions and safety boundaries.
- Repository write permission cannot be justified by efficiency alone.
- Sending artifacts to an external service requires human accountability review when efficiency is the only justification.
- A safety check must not be weakened merely to reduce execution time.
- Publishing confidential review details automatically must escalate at minimum and must block when the behavior is explicitly prohibited.
- Automatic merge or deployment is blocked by the project boundary.

## Acceptance criteria

Patch 11 is acceptable only if:

- exactly one new documentation file is added
- the file is `docs/specs/patch-11-accountability-efficiency-justification.md`
- no other files are modified
- no workflow changes are made
- no source code changes are made
- no tests are changed
- no generated artifacts are created or committed
- no secrets are added
- no external service integration is added
- no AI API integration is added
- no runtime execution authority is added
- human final decision remains mandatory

## Future implementation notes

A future implementation may create a deterministic local classifier only after separate review and approval.

Any future classifier must preserve decision precedence:

```text
BLOCK before ESCALATE_TO_HITL before NORMAL_REVIEW
```

Any future classifier must remain advisory-only unless a separate reviewed patch explicitly changes scope.

Any future classifier must not call AI APIs, use API keys, contact external AI providers, create external side effects, modify source files, or perform automatic repository actions.

Any future classifier must record evidence and reason codes without granting permission automatically.

Any future integration with checkpoint handoff must preserve Patch 10 semantics and must not alter or resume checkpoints automatically.
