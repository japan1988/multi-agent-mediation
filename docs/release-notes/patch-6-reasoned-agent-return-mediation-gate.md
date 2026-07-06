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
