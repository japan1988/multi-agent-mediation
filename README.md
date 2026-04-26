# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

This repository is provided for **research and educational purposes**.

It is intended to demonstrate:

- orchestration control patterns
- mediation / governance simulation structures
- fail-closed guardrails
- audit / replay-oriented design
- HITL escalation semantics

It is **not** a promise of production readiness, completeness, or universal policy coverage.

---

## Summary

Maestro Orchestrator is a safety-first orchestration framework for studying how agent workflows should behave when they encounter uncertainty, risk, or human-judgment boundaries.

Its core stance is simple:

> **If uncertain, stop. If risky, escalate.**

This repository contains multiple experimental and versioned simulators, benchmark runners, audit/logging examples, and test suites for studying guarded orchestration behavior.

---

## What is in this repository

The repository currently includes:

- orchestration and document workflow simulators
- mediator / governance negotiation simulations
- emergency-contract and HITL-controlled workflow simulations
- benchmark runners and evaluation helpers
- audit/log / codebook examples
- regression and invariant-focused pytest suites

Representative files include:

- `ai_doc_orchestrator_kage3_v1_3_5.py`
- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `mediation_emergency_contract_sim_v5_1_2.py`
- `ai_governance_mediation_sim.py`
- `ai_mediation_all_in_one.py`
- `run_benchmark_kage3_v1_3_5.py`
- `run_benchmark_profiles_v1_0.py`
- `rank_transition_sample.py`

Main directories include:

- `.github/workflows/`
- `archive/`
- `benchmarks/`
- `docs/`
- `evaluation/`
- `mediation_core/`
- `scripts/`
- `tests/`

---

## Repository shape

This repository contains both:

- actively referenced test / workflow targets
- historical or versioned experimental files kept for comparison and traceability

That means some modules are newer reference points, while others remain as archived or earlier-stage variants.

---

## Quick start

Create an environment and install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Run the full test suite:

pytest -q
Quick test commands
Examples for targeted runs:

pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_3_5.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
Continuous Integration
CI runs lint / validation / pytest through:

.github/workflows/python-app.yml
Additional advisory or analysis workflows may exist under:

.github/workflows/
Design stance
This repository is centered on a fail-closed mindset:

stop on uncertainty

escalate on risk

preserve auditability

keep human judgment in the loop where required

Common themes across the simulations include:

fixed gate ordering

explicit stop / pause semantics

reproducibility-oriented tests

structured logging and replayability

human-in-the-loop escalation boundaries

Notes
Because this repository contains multiple experiments and versioned files, not every file should be read as the single canonical implementation of the whole project.

The most reliable guide to current behavior is usually the combination of:

current tests in tests/

current CI workflow files in .github/workflows/

the latest maintained simulator / orchestrator files

benchmark runners and codebook / log definitions where applicable

Language
English README: README.md

Japanese README: README.ja.md

License
See LICENSE.

Repository license: Apache-2.0
Policy intent: Educational / Research

