# Patch 6: Reasoned agent return mediation gate

## Status

Patch 6 is a specification-first patch.

This patch defines a reasoned agent return mediation gate.

It does not implement runtime mediation, tests, workflow integration, actual agent execution, automatic comments, automatic fixes, commits, pull requests, merges, or deployment.

## Purpose

Patch 6 defines how the pseudo-orchestration mediation layer should handle contradictory or unsafe inputs.

The purpose is to ensure that contradictory inputs are not normalized into safe-looking results.

When declared behavior and observed behavior conflict, the mediation layer must:

- detect the contradiction
- preserve the contradiction in the output artifact
- assign a `reason_code`
- route the case to `NEEDS_REVIEW` or `BLOCK`
- produce a reasoned `return_to` target
- stop the flow
- keep the final decision with a human reviewer

Patch 6 is about reasoned return / 差し戻し.

It is not about automatic repair.

## Relationship to Patch 5

Patch 5 defined the pseudo-orchestration boundary:

```text
AI連携っぽい構造は作る。
しかし、AI連携はしない。
workflowはAIを呼ばず、AIに渡せる材料を作るだけ。
```

Patch 6 extends that boundary by defining what should happen when pseudo-orchestration input is contradictory.

Patch 6 keeps the same safety model:

- advisory-only
- local / deterministic design
- no AI API calls
- no actual agent execution
- no automatic code changes
- no automatic PR / merge / deploy
- human review remains final

## Core principle

Contradictory inputs must not be normalized into safe-looking results.

When declared behavior and observed behavior conflict, the mediator must preserve the contradiction in the output artifact and route the case to `NEEDS_REVIEW` or `BLOCK`.

日本語:

矛盾した入力は、安全そうな結果に正規化してはならない。

宣言された動作と観測された動作が矛盾する場合、調停層はその矛盾を出力 artifact に保持し、`NEEDS_REVIEW` または `BLOCK` に分類しなければならない。

## Definition of reasoned return

Reasoned return means:

- the mediator does not repair the input
- the mediator does not reinterpret unsafe input as safe
- the mediator explains why the input cannot proceed
- the mediator identifies a logical return target
- the mediator records the reason in an artifact
- the mediator stops or routes to human review

Reasoned return does not mean:

- calling an AI agent
- starting Codex automatically
- writing GitHub comments automatically
- modifying files
- applying fixes
- committing changes
- opening pull requests
- merging pull requests
- deploying changes

## Logical agent roles

Patch 6 may refer to logical agent roles only.

These roles are labels in the output artifact. They do not trigger real agents.

| Role | Meaning |
|---|---|
| `implementation_agent` | The role that produced or would revise implementation material |
| `review_agent` | The role that reviews evidence, consistency, or missing proof |
| `policy_owner` | The role that resolves policy ambiguity or boundary decisions |
| `human_reviewer` | The final human decision maker |

Patch 6 must not execute or contact any of these roles.

## Decisions

The mediation gate may produce these decisions:

| Decision | Meaning |
|---|---|
| `PROCEED_TO_REVIEW` | No contradiction was detected; material may proceed to human review |
| `NEEDS_REVIEW` | Evidence is incomplete or ambiguous; human review is required |
| `BLOCK` | A safety boundary contradiction or prohibited behavior was detected |

`PROCEED_TO_REVIEW` must not be used when a contradiction is present.

## Reason codes

Patch 6 defines these initial reason codes:

| Reason code | Decision | Return target | Meaning |
|---|---|---|---|
| `VALID_DOCS_ONLY_CHANGE` | `PROCEED_TO_REVIEW` | `human_reviewer` | Input is within docs-only advisory scope |
| `ADVISORY_ONLY_CONTRADICTION` | `BLOCK` | `implementation_agent` | Input declares advisory-only but observed file modification or apply behavior exists |
| `EXTERNAL_SIDE_EFFECT_CONTRADICTION` | `BLOCK` | `implementation_agent` | Input declares no external side effect but push, PR, deploy, or equivalent side effect is observed |
| `HUMAN_REVIEW_BYPASS` | `BLOCK` | `implementation_agent` | Human review is required but auto-apply or equivalent bypass behavior is observed |
| `GENERATED_OUTPUT_COMMITTED` | `BLOCK` | `implementation_agent` | Generated runtime output appears committed into the repository |
| `PERMISSION_ESCALATION` | `BLOCK` | `policy_owner` | Workflow permissions increased beyond the reviewed boundary |
| `TEST_EVIDENCE_MISSING` | `NEEDS_REVIEW` | `review_agent` | Tests are declared as passed but evidence artifacts are missing |

## Contradiction examples

### Advisory-only contradiction

Input example:

```json
{
  "declared_advisory_only": true,
  "observed_files_modified": true
}
```

Expected result:

```json
{
  "decision": "BLOCK",
  "reason_code": "ADVISORY_ONLY_CONTRADICTION"
}
```

### External side effect contradiction

Input example:

```json
{
  "declared_external_side_effect": false,
  "observed_push": true
}
```

Expected result:

```json
{
  "decision": "BLOCK",
  "reason_code": "EXTERNAL_SIDE_EFFECT_CONTRADICTION"
}
```

### Human review bypass

Input example:

```json
{
  "human_review_required": true,
  "auto_apply": true
}
```

Expected result:

```json
{
  "decision": "BLOCK",
  "reason_code": "HUMAN_REVIEW_BYPASS"
}
```

### Generated output committed

Input example:

```json
{
  "generated_outputs_committed": true,
  "paths": [
    "analysis_results/release_mediation/result.json"
  ]
}
```

Expected result:

```json
{
  "decision": "BLOCK",
  "reason_code": "GENERATED_OUTPUT_COMMITTED"
}
```

Generated outputs under runtime output directories such as `analysis_results/` or `stress_results/` should be treated as blocking when committed to the repository.

### Permission escalation

Input example:

```json
{
  "permissions_before": {
    "contents": "read"
  },
  "permissions_after": {
    "contents": "write"
  }
}
```

Expected result:

```json
{
  "decision": "BLOCK",
  "reason_code": "PERMISSION_ESCALATION"
}
```

### Missing test evidence

Input example:

```json
{
  "declared_tests_passed": true,
  "test_artifacts_present": false
}
```

Expected result:

```json
{
  "decision": "NEEDS_REVIEW",
  "reason_code": "TEST_EVIDENCE_MISSING"
}
```

## Expected artifact shape

Patch 6 does not implement artifacts yet, but future Patch 6 implementation should produce a local review artifact with this shape:

```json
{
  "patch": 6,
  "mode": "reasoned_agent_return_mediation_gate",
  "decision": "BLOCK",
  "reason_code": "HUMAN_REVIEW_BYPASS",
  "stopped": true,
  "requires_human_review": true,
  "final_decider": "human",
  "return_to": {
    "agent_role": "implementation_agent",
    "return_type": "REJECT_AND_REVISE",
    "message": "auto_apply is not allowed when human_review_required is true."
  },
  "contradictions": [
    {
      "declared": {
        "human_review_required": true
      },
      "observed": {
        "auto_apply": true
      }
    }
  ],
  "prohibited_next_actions": [
    "auto_apply",
    "auto_commit",
    "auto_pr",
    "auto_merge",
    "deploy"
  ],
  "required_next_actions": [
    "preserve evidence",
    "remove bypass behavior before resubmission",
    "return result to human review"
  ],
  "auto_corrected": false,
  "normalized_to_safe_result": false,
  "source_files_modified": false
}
```

## Required future assertions

When Patch 6 is implemented later, tests should assert:

- contradictions are detected
- `decision` is `BLOCK` or `NEEDS_REVIEW` for contradictory input
- contradictory input never becomes `PROCEED_TO_REVIEW`
- `reason_code` is present
- `return_to.agent_role` is present
- `return_to.return_type` is present
- `return_to.message` is non-empty
- contradiction details are preserved
- `auto_corrected` is `false`
- `normalized_to_safe_result` is `false`
- `source_files_modified` is `false`
- `final_decider` remains `human`

## Possible future fixture names

Patch 6 spec records possible future fixtures only.

It does not add them.

```text
tests/stress/fixtures/pseudo_orchestration/
  valid_docs_only_change.json
  contradiction_advisory_only_but_modified.json
  contradiction_no_external_side_effect_but_push.json
  contradiction_human_review_but_auto_apply.json
  contradiction_generated_output_committed.json
  contradiction_permissions_escalated.json
  contradiction_tests_claimed_but_missing_evidence.json
```

## Non-goals

Patch 6 does not:

- implement the mediation script
- add tests
- add fixtures
- add workflow integration
- call AI APIs
- call Codex APIs
- call Anthropic APIs
- call Gemini APIs
- call Copilot APIs
- call external AI providers
- use API keys
- use GitHub Actions secrets
- perform runtime external network calls
- execute real agents
- post GitHub comments automatically
- apply fixes
- modify source files
- commit to main
- open pull requests
- merge pull requests
- deploy

## Safety boundary

Patch 6 is documentation/specification-only.

Allowed:

- define reasoned return semantics
- define contradiction handling policy
- define logical agent roles
- define reason codes
- define expected artifact shape
- define future test expectations

Prohibited:

- runtime behavior
- AI API calls
- actual agent execution
- automatic repair
- automatic code modification
- automatic GitHub actions beyond existing CI
- generated output commits
- permission escalation

## Relationship to later patches

Patch 6 is limited to reasoned return.

Later patches may define additional behavior:

- Patch 7: revised submission verification loop
- Patch 8: mediation loop guard
- Patch 9: agent rotation escalation gate
- Patch 10: mediation checkpoint handoff

These later patches are not implemented by Patch 6.

## Review checklist

- [ ] Docs/spec-only change
- [ ] Exactly one file added
- [ ] No workflow changes
- [ ] No script changes
- [ ] No test changes
- [ ] No generated outputs committed
- [ ] No AI API calls
- [ ] No API keys or secrets
- [ ] No runtime external network calls
- [ ] No auto-fix / auto-PR / auto-merge / deploy
- [ ] Human final decision boundary preserved
