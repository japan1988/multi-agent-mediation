# Archive

This directory contains historical, superseded, comparison-only, or review-support files that are preserved for reference and reproducibility.

Archiving does **not** mean deletion.
Files in this directory are retained so older experiments, stress results, simulator versions, and review artifacts can still be inspected manually.

## Archive policy

* `archive/` is for historical or best-effort reference material.
* Files here are not expected to be primary maintained entry points.
* Files here may not be part of the default CI test surface.
* Current source files, active tests, GitHub workflows, README files, SECURITY files, and active shared packages should remain outside `archive/`.
* Archive moves should be small, human-reviewed, and dependency-checked.
* Before moving files into `archive/`, check imports, tests, README references, documentation references, workflow references, and pytest collection behavior.

## Current archive layout

```text
archive/
├─ README.md
├─ emergency_contract_versions/
├─ hierarchy_experiments/
├─ mediation_examples/
└─ review-artifacts/
```

## Folders

### `emergency_contract_versions/`

Historical Emergency Contract simulator versions and related stress/report artifacts.

Current contents include:

```text
mediation_emergency_contract_sim_v1.py
mediation_emergency_contract_sim_v4.py
mediation_emergency_contract_sim_v4_4.py
mediation_emergency_contract_sim_v4_4_stress.py
mediation_emergency_contract_sim_v4_6_full.py
mediation_emergency_contract_sim_v4_7_full.py
mediation_emergency_contract_sim_v4_7_full_fixed_regex.py
mediation_emergency_contract_sim_v5_0_1.py
stress_report_v4_7_draft_lint_100k_seed42.json
```

These files are preserved for historical comparison, regression reference, and simulator lineage review.

### `hierarchy_experiments/`

Historical hierarchy / coordination experiment files.

Current contents include:

```text
ai_hierarchy_dynamics_full_log_20250804.py
ai_hierarchy_simulation_log.py
```

These files are preserved as historical experiments and are not the primary maintained entry points.

### `mediation_examples/`

Historical mediation example files.

Current contents include:

```text
README.md
mediation_basic_example.py
mediation_with_logging.py
multi_agent_mediation_with_reeducation.py
```

See `archive/mediation_examples/README.md` for folder-specific notes.

### `review-artifacts/`

Historical review artifacts, stress-result JSON files, release bundles, and other non-source outputs used for audit, review, or comparison.

Current contents include:

```text
ai_evolution_mediation_RELEASE.zip
stress_results_v4_4_1000.json
stress_results_v4_4_10000.json
stress_results_v4_6_100000.json
stress_results_v5_1_2_10000_mixed.json
```

These files are archived as historical artifacts only.

They are not source code, not tests, and not workflow definitions.

## How to use

Maintained repository tests should be run from the repository root:

```bash
pytest -q
```

Archive files are best-effort historical materials.
Some archived files may require old assumptions, old import paths, or manual setup.

## Do not archive without review

Do not move these categories into `archive/` without explicit review:

```text
active source files
active tests
.github/workflows/*
README.md
README.ja.md
SECURITY.md
SECURITY.ja.md
pytest.ini
requirements*.txt
mediation_core/*
current benchmark scripts
```

## Pre-move checklist

Before any future archive move:

```text
1. Check Python imports.
2. Check pytest collection.
3. Check direct test dependencies.
4. Check README / README.ja.md references.
5. Check docs references.
6. Check GitHub Actions workflow references.
7. Check scripts and benchmark references.
8. Run the relevant test suite.
9. Keep each archive PR small.
10. Do not auto-merge.
```

## Status

This archive is intended for historical preservation and repository hygiene.

Current maintained entry points should remain outside this directory.
