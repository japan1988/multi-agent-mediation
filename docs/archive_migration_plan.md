# Archive Migration Plan

This document lists files that may be moved to `archive/` over time.

The purpose of archiving is to keep the main repository view focused on current entry points while preserving older experiments for reproducibility, regression comparison, and historical reference.

Archiving does **not** mean immediate deletion.

## Current policy

- Current recommended files remain visible.
- Historical, superseded, comparison-only, or old experiment files may be moved to `archive/`.
- Tests, imports, README links, documentation links, and workflow references must be checked before or together with any move.
- Files are moved gradually, not all at once.
- Archive moves should be made through normal human-reviewed PRs.
- No automatic file movement, automatic PR creation, automatic push, or automatic merge.

## Recommended entry points

The following files should remain visible for now.

| File | Status | Reason |
|---|---|---|
| `infrastructure_lifeline_mediation_randomized_sim_v0_2.py` | current | Current Infrastructure Lifeline Mediation Simulation |
| `scripts/tasukeru_adversarial_stress_v0_1.py` | current | Current Tasukeru adversarial stress test |
| `scripts/gate_compression_rollback_sim_v0_1.py` | current | Current gate compression rollback simulation |
| `emergency_contract_kage_orchestrator_v1_0.py` | current / reference | Current Emergency Contract × KAGE integration simulator |
| `ai_doc_orchestrator_with_mediator_v1_0.py` | current / reference | Current mediator-based gate simulator |
| `ai_doc_orchestrator_kage3_v1_2_6_hash_chain_checkpoint.py` | current / reference | Production-oriented document orchestrator simulator described in README |
| `ai_doc_orchestrator_kage3_v1_2_7_task_contract_dispatch.py` | current / review | Later document-orchestrator line; confirm whether it supersedes v1.2.6 before changing README |

## Archive destination structure

Recommended archive layout:

```text
archive/
├─ README.md
├─ old_simulators/
├─ emergency_contract_versions/
├─ doc_orchestrator_versions/
├─ mediation_experiments/
├─ hierarchy_experiments/
├─ benchmark_experiments/
└─ historical_tests/
```

## Planned archive candidates

These are **candidates**, not immediate moves. Each file must be checked before moving.

### Emergency contract simulator versions

| File | Current status | Planned destination | Notes |
|---|---|---|---|
| `mediation_emergency_contract_sim_v1.py` | historical / superseded | `archive/emergency_contract_versions/` | Confirm no active tests import this path |
| `mediation_emergency_contract_sim_v4.py` | historical / superseded | `archive/emergency_contract_versions/` | Superseded by later v4/v5 versions |
| `mediation_emergency_contract_sim_v4_1.py` | historical / superseded | `archive/emergency_contract_versions/` | Confirm test references before moving |
| `mediation_emergency_contract_sim_v4_4.py` | historical / superseded | `archive/emergency_contract_versions/` | Keep for reproducibility if referenced in notes |
| `mediation_emergency_contract_sim_v4_4_stress.py` | historical stress variant | `archive/emergency_contract_versions/` | Confirm whether any stress tests still reference it |
| `mediation_emergency_contract_sim_v4_6_full.py` | historical / superseded | `archive/emergency_contract_versions/` | Later v4/v5 files appear to exist |
| `mediation_emergency_contract_sim_v4_7_full..py` | historical / filename cleanup candidate | `archive/emergency_contract_versions/` | Double-dot filename; check imports carefully |
| `mediation_emergency_contract_sim_v4_7_full_fixed_regex.py` | historical / superseded | `archive/emergency_contract_versions/` | Confirm whether superseded by v4.8/v5.x |
| `mediation_emergency_contract_sim_v4_8.py` | historical / maybe reference | `archive/emergency_contract_versions/` | Move only if v5.1.2 is the retained active line |
| `mediation_emergency_contract_sim_v5_0_1.py` | historical / superseded | `archive/emergency_contract_versions/` | Keep if useful for regression comparison |
| `mediation_emergency_contract_sim_v5_1_2.py` | active or current advanced reference | keep visible for now | Do not archive until current status is confirmed |

### Document orchestrator versions

| File | Current status | Planned destination | Notes |
|---|---|---|---|
| `ai_doc_orchestrator_kage3_v1_2_2.py` | historical / duplicate candidate | `archive/doc_orchestrator_versions/` | There is already an archived copy; check duplication |
| `ai_doc_orchestrator_kage3_v1_2_3.py` | historical / superseded | `archive/doc_orchestrator_versions/` | Confirm tests/import shims |
| `ai_doc_orchestrator_kage3_v1_2_4.py` | historical / superseded | `archive/doc_orchestrator_versions/` | Confirm tests/import shims |
| `ai_doc_orchestrator_kage3_v1_2_6_hash_chain_checkpoint.py` | current / reference | keep visible for now | README describes this as production-oriented simulator |
| `ai_doc_orchestrator_kage3_v1_2_7_task_contract_dispatch.py` | current / review | keep visible for now | Confirm whether this should become the primary entry point |
| `archive/orchestrator_versions/ai_doc_orchestrator_kage3_v1_2_2.py` | already archived | no move | Confirm whether root duplicate can be removed or redirected later |

### Mediation and governance experiments

| File | Current status | Planned destination | Notes |
|---|---|---|---|
| `ai_mediation_all_in_one.py` | early / broad experiment | `archive/mediation_experiments/` | Candidate if not a current entry point |
| `ai_governance_mediation_sim.py` | experiment | `archive/mediation_experiments/` | Confirm README/test references |
| `ai_mediation_governance_demo.py` | demo / experiment | `archive/mediation_experiments/` | Candidate if superseded |
| `mediation_with_logging.py` | older logging experiment | `archive/mediation_experiments/` | Confirm no active tests import it |
| `multi_agent_coordination_contract_v1_0.py` | contract experiment | `archive/mediation_experiments/` | Confirm status before moving |
| `multi_agent_mediation_with_reeducation.py` | reeducation experiment | `archive/mediation_experiments/` | Candidate if not current |
| `ai_reeducation_social_dynamics.py` | social dynamics experiment | `archive/mediation_experiments/` | Candidate if not current |
| `dialogue_consistency_mediator_v2_2_research.` | research / filename cleanup candidate | `archive/mediation_experiments/` | File has no normal extension; move carefully |

### Hierarchy and alliance experiments

| File | Current status | Planned destination | Notes |
|---|---|---|---|
| `ai_hierarchy_simulation_log.py` | historical experiment | `archive/hierarchy_experiments/` | Keep for historical comparison |
| `ai_hierarchy_dynamics_full_log_20250804.py` | dated historical experiment | `archive/hierarchy_experiments/` | Dated file; likely archive candidate |
| `ai_alliance_persuasion_simulator.py` | alliance experiment | `archive/hierarchy_experiments/` | Candidate if not current |
| `kage_orchestrator_diverse_v1.py` | KAGE experiment | `archive/hierarchy_experiments/` | Confirm status before moving |
| `kage_end_to_end_confidential_loopguard_v1_0.py` | KAGE experiment | `archive/hierarchy_experiments/` | Confirm status before moving |

### Benchmark and sample utilities

| File | Current status | Planned destination | Notes |
|---|---|---|---|
| `run_benchmark_profiles_v1_0.py` | benchmark utility | `archive/benchmark_experiments/` or keep | Keep if still useful for active benchmarking |
| `run_benchmark_kage3_v1_3_5.py` | benchmark utility | `archive/benchmark_experiments/` or keep | Keep if still useful for active benchmarking |
| `rank_transition_sample.py` | sample utility | `archive/old_simulators/` | Candidate if not referenced |
| `sim_batch_fixed.py` | batch experiment | `archive/old_simulators/` | Confirm if superseded by safer version |
| `sim_batch_fixed_colab_safe.py` | batch / Colab-safe experiment | `archive/old_simulators/` | Confirm if current docs mention it |
| `ai_pacd_simulation.py` | PACD experiment | `archive/old_simulators/` | Candidate if not current |
| `copilot_mediation_min.py` | Copilot benchmark / demo | keep or `archive/benchmark_experiments/` | Keep visible if release notes still point to it |
| `scripts/pattern_steering_min.py` | benchmark / steering utility | keep or `archive/benchmark_experiments/` | Keep visible if active benchmark utility |
| `scripts/run_benchmark.py` | active script candidate | keep visible for now | Do not archive until benchmark workflow status is confirmed |
| `evaluation/simulate_arl_stats_v1_1.py` | evaluation utility | keep or `archive/benchmark_experiments/` | Keep if used for current evaluation docs |

## Suggested migration order

### Phase 1: Publish plan only

1. Add this file as `docs/archive_migration_plan.md`.
2. Do not move files yet.
3. Confirm current entry points in README / README.ja.md.
4. Confirm CI and Tasukeru Analysis.

### Phase 2: Low-risk archive move

Move only files that appear clearly historical and are unlikely to be imported by active tests.

Recommended first small batch:

| File | Destination |
|---|---|
| `ai_hierarchy_dynamics_full_log_20250804.py` | `archive/hierarchy_experiments/` |
| `ai_hierarchy_simulation_log.py` | `archive/hierarchy_experiments/` |
| `rank_transition_sample.py` | `archive/old_simulators/` |

Before merging:

- Check imports.
- Check tests.
- Check README/docs links.
- Confirm CI.
- Confirm Tasukeru Analysis.

### Phase 3: Emergency contract version cleanup

Move older emergency contract files after confirming which version remains active.

Recommended retained visible candidate:

- `mediation_emergency_contract_sim_v5_1_2.py`

Older versions can then be moved gradually.

### Phase 4: Document orchestrator version cleanup

Decide whether `v1_2_6` or `v1_2_7` is the current visible entry point.

Then archive superseded root-level versions.

### Phase 5: Optional test archive cleanup

Only move tests after their target files have been moved and import paths are updated.

Tests may remain visible longer than implementation files if they are still used for regression coverage.

## Required pre-move checklist

Before moving any file:

- [ ] Confirm whether the file is imported by tests.
- [ ] Confirm whether README / README.ja.md links to the file.
- [ ] Confirm whether docs link to the file.
- [ ] Confirm whether GitHub Actions references the file.
- [ ] Confirm whether Tasukeru classification expects the file at the current path.
- [ ] Move only a small batch per PR.
- [ ] Run CI.
- [ ] Review Tasukeru Analysis.
- [ ] Do not auto-merge.

## Non-goals

- No immediate mass deletion.
- No automatic file movement.
- No automatic PR creation.
- No automatic push.
- No automatic merge.
- No loss of historical reproducibility.
- No change to safety semantics.
- No weakening of tests or gate invariants.

## Notes

This plan is intentionally conservative.

The archive process should reduce visual clutter without changing the meaning of current simulator lines or weakening safety boundaries.
