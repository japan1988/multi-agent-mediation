# Patch 4: ARL analyzer / graph generator

## Status

Patch 4 は完了し、PR #889 により `main` へマージ済みです。

- PR number: #889
- PR title: Patch 4 ARL analyzer graph integration
- merge commit: 2a0caa849c711c01f8095d8f48f0045e6ce9f42c
- merged at: 2026-07-04T01:17:40Z
- merged_to_main: true
- post_merge_verification: completed
- analyzer artifact verified: true

## Summary

Patch 4 では、ARL / advisory artifacts を対象とする決定的な analyzer / graph generator を追加しました。

- deterministic ARL analyzer / graph generator script
- analyzer tests
- analyzer fixtures
- workflow integration
- analyzer artifact upload

## Files added / changed

主な追加・変更ファイルは以下です。

- `scripts/tasukeru_arl_analyzer.py`
- `tests/stress/test_tasukeru_arl_analyzer.py`
- `tests/stress/fixtures/arl_analyzer/**`
- `.github/workflows/tasukeru-analysis.yml`
- `.gitignore`

## Runtime artifact

- workflow artifact name: `tasukeru-arl-analyzer-results`
- output directory at runtime: `analysis_results/arl/`
- generated output is artifact-only and is not committed to the repository
- analyzer verify result was confirmed as `true` in PR workflow verification

## Safety boundary

Patch 4 は advisory-only の analyzer / graph generator です。

- advisory-only
- human review required
- no AI API calls
- no API keys or secrets
- no external AI provider calls
- no runtime external network calls added by Patch 4
- no billable action
- no auto-fix
- no auto-commit-to-main
- no auto-PR
- no auto-merge
- no deploy
- workflow permissions remain read-only

## Verification

Patch 4 の検証結果は以下です。

- `py_compile` passed
- analyzer focused unittest suite passed
- full stress unittest discovery passed
- GitHub Actions passed before merge
- Python App CI passed
- Tasukeru Analysis passed
- analyzer artifact verify `true` was confirmed
- post-merge verification confirmed `main` contains Patch 4 and generated outputs are not committed

## Notes

- Runtime ARL and stress fixture ARL are treated as distinct sources.
- Expected-negative stress cases are labeled as expected detections.
- HMAC is not claimed when `hmac_enabled` is false.
- Patch 5 pseudo-orchestration is not included in Patch 4.
