## How to use (optional)
- To run maintained tests (CI suite):
  - `pytest -q`

- To run archived tests (best-effort, may fail):
  - CI excludes `archive/` via `pytest.ini` (`norecursedirs = archive`).
  - Run locally by overriding config, e.g.:
    - `pytest -q -c /dev/null archive/legacy_tests`
    - (Windows) `pytest -q -c NUL archive/legacy_tests`

Note: `archive/` is best-effort; only maintained entrypoints/tests are expected to stay green.
