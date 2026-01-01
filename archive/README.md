# Archive (research history)

This directory contains archived / legacy / exploratory materials kept for traceability and comparison.

## Policy

- Not part of active entrypoints.
- Not guaranteed to run. (Compatibility may intentionally drift.)
- CI should not depend on this directory unless explicitly wired.
- Prefer keeping only the current/recommended entrypoints at repo root.

## Why keep this?

- Preserve research history and comparisons
- Reduce clutter in repo root while keeping reproducibility
- Keep old variants without implying "current / recommended"

## Structure (convention)

- `orchestrator_versions/`: older orchestrator variants
- `experiments/`: one-off runs / exploratory scripts
- `legacy_tests/`: tests not used by current CI

## Planned moves (initial)

- `ai_doc_orchestrator_kage3_v1_2_2.py` → `archive/orchestrator_versions/`
- `ai_doc_orchestrator_kage3_v1_2_4.py` → `archive/orchestrator_versions/`

## Move checklist (must-do before moving)

1. Search references (GitHub search):
   - `ai_doc_orchestrator_kage3_v1_2_2`
   - `ai_doc_orchestrator_kage3_v1_2_4`
   - If referenced by imports/tests/docs, update paths or keep in root.
2. Move via `git mv` (recommended) or GitHub UI rename.
3. Run CI/tests.

## How to use (optional)

- To run maintained tests (CI suite):
  - `pytest -q`

- To run archived tests (best-effort, may fail):
  - CI excludes `archive/` via `pytest.ini` (`norecursedirs = archive`).
  - Run locally by overriding config, e.g.:
    - `pytest -q -c /dev/null archive/legacy_tests`
    - (Windows) `pytest -q -c NUL archive/legacy_tests`

Note: `archive/` is best-effort; only maintained entrypoints/tests are expected to stay green.
