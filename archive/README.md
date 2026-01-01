Comment (paste as-is)

CI is still red because pytest is collecting legacy tests under tests/ that import modules which are no longer present at repo root:

tests/test_ai_doc_orchestrator_kage3_v1_2_4.py → ModuleNotFoundError: ai_doc_orchestrator_kage3_v1_2_4

tests/test_ai_doc_orchestrator_kage3_v1_3_5.py → ModuleNotFoundError: ai_doc_orchestrator_kage3_v1_3_5

tests/test_doc_orchestrator_with_mediator_v1_0.py → ModuleNotFoundError: ai_doc_orchestrator_with_mediator_v1_0

pytest.ini excludes archive/, but these failing tests live in tests/, so they are still part of the CI suite.

Next step (recommended):

Move version-pinned tests from tests/ to archive/legacy_tests/ (or mark them skipped), keeping only maintained tests in tests/.

CI stays green, while legacy variants remain runnable manually (best-effort).
