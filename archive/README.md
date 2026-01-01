CommeFollow-up push on this PR:

This PR intentionally focuses on defining the maintained CI test surface via `pytest.ini` (collection scope), not on rewriting historical tests.

Background:
- Some version-pinned / historical tests under `tests/` still import old module names (archived/renamed entrypoints), which can trigger `ModuleNotFoundError` during collection.

What this PR does:
- Adds `pytest.ini` to standardize the intended maintained test surface (and exclude `archive/` from recursion).

What will be handled next (separate PR):
- Move version-pinned legacy tests out of the active CI suite (e.g., `tests/` → `archive/legacy_tests/`) or mark them as skipped, so CI collects only maintained tests.

Rationale:
- Keep research history for traceability while keeping `main` CI green and stable.
nt (paste as-is)
