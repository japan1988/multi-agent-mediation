# Patch 5: Pseudo-orchestration specification

## Purpose

Patch 5 defines a pseudo-orchestration layer for preparing reviewable materials without calling AI APIs.

AI連携っぽい構造は作る。  
しかし、AI連携はしない。  
workflowはAIを呼ばず、AIに渡せる材料を作るだけ。

The purpose is to make dry-run orchestration structure easier to inspect and review. It is research / education oriented and does not claim to guarantee safety.

## Non-goals

Patch 5 does not implement real AI integration.

- It does not call AI providers.
- It does not perform model inference.
- It does not automate code changes.
- It does not apply fixes.
- It does not commit, push, open PRs, merge, or deploy.

## Scope

Patch 5 scope is limited to dry-run / simulation / fixture-based pseudo-orchestration.

The layer may describe AI-like orchestration roles, inputs, gates, and review outputs, but it must remain local, deterministic, and advisory-only.

## Allowed behavior

- local deterministic material generation
- fixture-based simulation
- advisory-only JSON / JSONL / markdown output design
- human review gate
- no external AI calls

## Prohibited behavior

- OpenAI API calls
- Codex API calls
- Anthropic API calls
- Gemini API calls
- Copilot API calls
- external AI provider calls
- API keys
- GitHub Actions secrets
- billable actions
- runtime external network calls
- auto-fix
- auto-commit-to-main
- auto-PR
- auto-merge
- deploy

## Proposed artifacts

Possible future artifacts, if explicitly approved later:

- `pseudo_orchestration_plan.json`
- `pseudo_orchestration_review.md`
- `pseudo_orchestration_verify.json`

These artifacts would be generated outputs for human review. They are not implemented by this specification.

## Human review boundary

All decisions remain advisory.

Final decisions remain with a human reviewer. Pseudo-orchestration may organize materials, but it must not approve, apply, commit, push, open PRs, merge, or deploy changes.

## Workflow boundary

GitHub Actions may only generate local artifacts for review.

Workflow steps must not call AI APIs, external AI providers, or runtime external network services for pseudo-orchestration. Workflow permissions must remain read-only for Patch 5 initial scope. Any permission increase is out of scope and requires a separate reviewed patch.

## Review checklist

- [ ] AI API call absent
- [ ] secrets absent
- [ ] workflow permissions unchanged
- [ ] generated outputs not committed
- [ ] docs/spec only unless explicitly approved
- [ ] no auto-fix / auto-PR / auto-merge
- [ ] Patch 5 scope not expanded
