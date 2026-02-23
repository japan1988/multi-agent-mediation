# Archive (research history)

This directory contains archived / legacy / exploratory materials kept for traceability and comparison.

## Policy
- Not part of active entrypoints.
- Not guaranteed to run. (Compatibility may intentionally drift.)
- CI should not depend on this directory unless explicitly wired.
- Prefer keeping only the current/recommended entrypoints at repo root.

## Structure (convention)
- `orchestrator_versions/`: older orchestrator variants
- `experiments/`: one-off runs / exploratory scripts
- `legacy_tests/`: tests not used by current CI (optional; may not exist yet)

## Current references (repo root)
These are intentionally kept at repo root for discoverability and execution examples.

- `mediation_emergency_contract_sim_v5_1_2.py`: latest recommended emergency contract simulator (v5.1.2).
- `ai_doc_orchestrator_kage3_v1_2_4.py`: reference for post-HITL semantics (doc-orchestrator line).

## Planned moves (initial)
- `ai_doc_orchestrator_kage3_v1_2_2.py` → `archive/orchestrator_versions/`
- (Keep in repo root) `ai_doc_orchestrator_kage3_v1_2_4.py` as a current reference
- (Keep in repo root) `mediation_emergency_contract_sim_v5_1_2.py` as the recommended simulator entrypoint

## Move checklist (must-do before moving)
1. Search references (GitHub search):
   - `ai_doc_orchestrator_kage3_v1_2_2`
   - `ai_doc_orchestrator_kage3_v1_2_4`
   - `mediation_emergency_contract_sim_v5_1_2`
2. Check also:
   - `README.md`, `README.ja.md`, `tests/`, `scripts/`, `agents.yaml`, `.github/workflows`
3. If referenced by imports/tests/docs, update paths or keep in root.
4. Move via `git mv` (recommended) or GitHub UI rename.
5. Run CI/tests.

## How to use (optional)
- To run maintained tests (CI suite):
  - `pytest -q`

- To run archived tests (best-effort, may fail):
  - CI excludes `archive/` via `pytest.ini` (`norecursedirs = archive`).
  - If `archive/legacy_tests/` exists, run locally by overriding config, e.g.:
    - `pytest -q -c /dev/null archive/legacy_tests`
    - (Windows) `pytest -q -c NUL archive/legacy_tests`

Note: `archive/` is best-effort; only maintained entrypoints/tests are expected to stay green.
