diff --git a/archive/README.md b/archive/README.md
index 1111111..2222222 100644
--- a/archive/README.md
+++ b/archive/README.md
@@ -1,6 +1,6 @@
 # Archive (research history)
 
 This directory contains archived / legacy / exploratory materials kept for traceability and comparison.
 
 ## Policy
 
 - Not part of active entrypoints.
 - Not guaranteed to run. (Compatibility may intentionally drift.)
 - CI should not depend on this directory unless explicitly wired.
 - Prefer keeping only the current/recommended entrypoints at repo root.
@@ -16,20 +16,29 @@
 ## Structure (convention)
 
 - `orchestrator_versions/`: older orchestrator variants
 - `experiments/`: one-off runs / exploratory scripts
-- `legacy_tests/`: tests not used by current CI
+- `legacy_tests/`: tests not used by current CI (optional; may not exist yet)
+
+## Current reference (repo root)
+
+- `ai_doc_orchestrator_kage3_v1_2_4.py` is the current reference for post-HITL semantics
+  and is intentionally kept at repo root for discoverability and execution examples.
 
 ## Planned moves (initial)
 
 - `ai_doc_orchestrator_kage3_v1_2_2.py` → `archive/orchestrator_versions/`
-- `ai_doc_orchestrator_kage3_v1_2_4.py` → `archive/orchestrator_versions/`
+- (Keep in repo root) `ai_doc_orchestrator_kage3_v1_2_4.py` as current reference
 
 ## Move checklist (must-do before moving)
 
 1. Search references (GitHub search):
    - `ai_doc_orchestrator_kage3_v1_2_2`
-   - `ai_doc_orchestrator_kage3_v1_2_4`
-   - If referenced by imports/tests/docs, update paths or keep in root.
+   - Check also: `README.md`, `README.ja.md`, `tests/`, `scripts/`, `agents.yaml`, `.github/workflows`
+   - If referenced by imports/tests/docs, update paths or keep in root.
 2. Move via `git mv` (recommended) or GitHub UI rename.
 3. Run CI/tests.
 
 ## How to use (optional)
 
 - To run maintained tests (CI suite):
   - `pytest -q`
 
 - To run archived tests (best-effort, may fail):
   - CI excludes `archive/` via `pytest.ini` (`norecursedirs = archive`).
-  - Run locally by overriding config, e.g.:
+  - If `archive/legacy_tests/` exists, run locally by overriding config, e.g.:
     - `pytest -q -c /dev/null archive/legacy_tests`
     - (Windows) `pytest -q -c NUL archive/legacy_tests`
 
 Note: `archive/` is best-effort; only maintained entrypoints/tests are expected to stay green.
