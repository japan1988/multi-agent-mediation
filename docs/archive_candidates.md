# Archive Candidates

This document lists implementation/test sets that may be moved to `archive/` over time.

The purpose is to make archive decisions by dependency set, not by isolated file name.

No file is moved by this document.

## Policy

Archive moves should be gradual and human-reviewed.

Before moving any file:

- confirm imports
- confirm related tests
- confirm README / README.ja.md references
- confirm docs references
- confirm GitHub Actions references
- confirm pytest collection behavior
- confirm Tasukeru Analysis behavior

Do not move latest versions, current README entry points, CI files, pytest configuration, or files required for the repository to run.

## Current recommended entry points to keep visible

These files should not be archived now.

| Source file | Related test / dependency | Reason |
|---|---|---|
| `ai_doc_orchestrator_with_mediator_v1_0.py` | `tests/test_doc_orchestrator_with_mediator_v1_0.py` | Current mediator-based gate simulator |
| `ai_doc_orchestrator_kage3_v1_2_6_hash_chain_checkpoint.py` | check before changing | README-described production-oriented document orchestrator line |
| `ai_doc_orchestrator_kage3_v1_2_7_task_contract_dispatch.py` | `tests/test_doc_orchestrator_v1_2_7_flow.py` | Later document-orchestrator line with dynamic import test |
| `ai_doc_orchestrator_kage3_v1_3_5.py` | `tests/test_ai_doc_orchestrator_kage3_v1_3_5.py`, `run_benchmark_profiles_v1_0.py`, `scripts/run_benchmark.py` | Current benchmark dependency line |
| `emergency_contract_kage_orchestrator_v1_0.py` | `tests/test_emergency_contract_kage_orchestrator_v1_0.py` | Current Emergency Contract × KAGE integration simulator |
| `infrastructure_lifeline_mediation_randomized_sim_v0_2.py` | `tests/test_infrastructure_lifeline_mediation_randomized_sim_v0_2.py` | Current Infrastructure Lifeline Mediation Simulation |
| `scripts/tasukeru_adversarial_stress_v0_1.py` | `tests/test_tasukeru_adversarial_stress_v0_1.py` | Current Tasukeru adversarial stress test |
| `scripts/gate_compression_rollback_sim_v0_1.py` | `tests/test_gate_compression_rollback_sim_v0_1.py` if present | Current gate compression rollback simulation |

## Do not archive infrastructure / CI files

| File | Reason |
|---|---|
| `.github/workflows/python-app.yml` | CI workflow |
| `.github/workflows/tasukeru-analysis.yml` | Tasukeru Analysis workflow |
| `pytest.ini` | pytest collection configuration |
| `tests/conftest.py` | shared pytest setup |
| `README.md` | main documentation |
| `README.ja.md` | Japanese documentation |

## Move as a set: low-risk candidates

### Set A: old mediation examples

Recommended destination:

```text
archive/mediation_examples/
```

| Source file | Related test file | Required helper | Archive handling |
|---|---|---|---|
| `mediation_basic_example.py` | none found | `mediation_core/` | Move with the full set after final import check |
| `mediation_with_logging.py` | none found | `mediation_core/` | Move with the full set after final import check |
| `multi_agent_mediation_with_reeducation.py` | none found | `mediation_core/` | Move with the full set after final import check |
| `mediation_core/__init__.py` | none found | shared package | Move only if all active imports are historical |
| `mediation_core/models.py` | none found | shared models | Move only if all active imports are historical |

Reason:

These appear to be older mediation examples that share `mediation_core.models`. If archived, they should be moved together so the example set remains runnable as historical material.

Suggested first archive PR after this plan:

```text
Move old mediation examples to archive
```

## Move as a pair: medium-risk candidates

### Set B: KAGE loopguard experiment

Recommended destination:

```text
archive/kage_experiments/
```

| Source file | Related test file | Archive handling |
|---|---|---|
| `kage_end_to_end_confidential_loopguard_v1_0.py` | `test_end_to_end_confidential_loopguard_v1_0.py` | Move together only after confirming no active docs or workflows reference them |

Reason:

The root-level test belongs to this source file. If archived, keep the implementation and its test together to preserve historical reproducibility.

Caution:

If archived test files keep a `test_*.py` name, confirm they are not collected by CI unexpectedly.

## Candidate only: do not move yet

These sets need more dependency review before any archive move.

### KAGE3 v1.2.x document orchestrator family

| Source file | Related test file | Reason to wait |
|---|---|---|
| `ai_doc_orchestrator_kage3_v1_2_2.py` | unclear / duplicate archive copy exists | root/archive duplication and import shim risk |
| `ai_doc_orchestrator_kage3_v1_2_2_1.py` | check before moving | version lineage unclear |
| `ai_doc_orchestrator_kage3_v1_2_3.py` | `tests/test_ai_doc_orchestrator_kage3_v1_2_2.py` | test name and import target are mismatched |
| `ai_doc_orchestrator_kage3_v1_2_4.py` | `tests/test_ai_doc_orchestrator_kage3_v1_2_4.py` | active direct test dependency |
| `ai_doc_orchestrator_kage3_v1_2_6_hash_chain_checkpoint.py` | check before moving | README-described current/reference line |
| `ai_doc_orchestrator_kage3_v1_2_7_task_contract_dispatch.py` | `tests/test_doc_orchestrator_v1_2_7_flow.py` | dynamic import test and possible current line |

Do not archive this family until the current document-orchestrator entry point is finalized.

### Emergency contract simulator family

| Source file | Related test file | Reason to wait |
|---|---|---|
| `mediation_emergency_contract_sim_v1.py` | none found | family status needs review |
| `mediation_emergency_contract_sim_v4.py` | none found | family status needs review |
| `mediation_emergency_contract_sim_v4_1.py` | `tests/test_mediation_emergency_contract_sim_v4_1.py`, `tests/tests_test_mediation_emergency_contract_sim_v4_1.py` | duplicate/overlapping test names need review |
| `mediation_emergency_contract_sim_v4_4.py` | check before moving | historical but references need review |
| `mediation_emergency_contract_sim_v4_4_stress.py` | check before moving | stress variant, possible historical coverage |
| `mediation_emergency_contract_sim_v4_6_full.py` | check before moving | historical version, needs import/docs check |
| `mediation_emergency_contract_sim_v4_7_full..py` | check before moving | filename has double dot; move carefully |
| `mediation_emergency_contract_sim_v4_7_full_fixed_regex.py` | check before moving | historical version, needs import/docs check |
| `mediation_emergency_contract_sim_v4_8.py` | `tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py` | direct active test dependency |
| `mediation_emergency_contract_sim_v5_0_1.py` | check before moving | likely superseded but needs review |
| `mediation_emergency_contract_sim_v5_1_2.py` | `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py` | current advanced line; keep visible |

Do not archive `v5_1_2` now. Treat it as the active advanced line unless a newer verified version replaces it.

## Other candidate-only files

These files may be historical or experimental, but should be inspected before moving.

| Source file | Related test / dependency | Suggested destination | Status |
|---|---|---|---|
| `multi_agent_coordination_contract_v1_0.py` | none found | `archive/mediation_experiments/` | candidate only |
| `ai_governance_mediation_sim.py` | check before moving | `archive/mediation_experiments/` | candidate only |
| `ai_mediation_governance_demo.py` | check before moving | `archive/mediation_experiments/` | candidate only |
| `ai_mediation_all_in_one.py` | check before moving | `archive/mediation_experiments/` | candidate only |
| `ai_reeducation_social_dynamics.py` | check before moving | `archive/mediation_experiments/` | candidate only |
| `ai_alliance_persuasion_simulator.py` | check before moving | `archive/hierarchy_experiments/` | candidate only |
| `ai_hierarchy_simulation_log.py` | check before moving | `archive/hierarchy_experiments/` | candidate only |
| `ai_hierarchy_dynamics_full_log_20250804.py` | check before moving | `archive/hierarchy_experiments/` | candidate only |
| `kage_orchestrator_diverse_v1.py` | `tests/test_kage_orchestrator_diverse_v1.py` | `archive/kage_experiments/` | move as pair only |
| `rank_transition_sample.py` | none found | `archive/old_simulators/` | candidate only |
| `sim_batch_fixed.py` | check before moving | `archive/old_simulators/` | candidate only |
| `sim_batch_fixed_colab_safe.py` | check before moving | `archive/old_simulators/` | candidate only |
| `ai_pacd_simulation.py` | check before moving | `archive/old_simulators/` | candidate only |

## Proposed migration sequence

### PR 1: documentation only

Add:

```text
docs/archive_migration_plan.md
docs/archive_candidates.md
```

No file moves.

### PR 2: low-risk archive set

Move only Set A after final import check:

```text
mediation_basic_example.py
mediation_with_logging.py
multi_agent_mediation_with_reeducation.py
mediation_core/__init__.py
mediation_core/models.py
```

Destination:

```text
archive/mediation_examples/
```

### PR 3: optional medium-risk pair

Move Set B only after confirming no active references:

```text
kage_end_to_end_confidential_loopguard_v1_0.py
test_end_to_end_confidential_loopguard_v1_0.py
```

Destination:

```text
archive/kage_experiments/
```

### PR 4 and later: family-specific review

Review and handle these families separately:

```text
KAGE3 v1.2.x document orchestrator family
Emergency contract simulator family
Benchmark and historical experiment files
```

## Pre-move checklist

Before each archive PR:

- [ ] Search for imports of every source file.
- [ ] Search for README / README.ja.md references.
- [ ] Search for docs references.
- [ ] Search for workflow references.
- [ ] Confirm related tests.
- [ ] Decide whether related tests stay active or move with source.
- [ ] Confirm archive test files will not break pytest collection.
- [ ] Run tests.
- [ ] Review Tasukeru Analysis.
- [ ] Do not auto-merge.
