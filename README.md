# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

> Japanese: [README.ja.md](README.ja.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="Python App CI">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main" alt="Tasukeru Advisory">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

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

Because the repository contains multiple experiments and versioned files, not every file should be read as the single canonical implementation of the whole project.

The most reliable guide to current behavior is usually the combination of:

- current tests in `tests/`
- current CI workflow files in `.github/workflows/`
- the latest maintained simulator / orchestrator files
- benchmark runners and codebook / log definitions where applicable

---

## Quick start

Create an environment and install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Run the full test suite:

```bash
pytest -q
```

---

## Quick test commands

Examples for targeted runs:

```bash
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_3_5.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
```

---

## Continuous Integration

Primary CI runs lint, validation, and pytest through:

```text
.github/workflows/python-app.yml
```

The main CI workflow is intended to check that the repository remains executable and testable across the configured Python versions.

Current Python targets:

```text
Python 3.10
Python 3.11
```

Additional advisory or analysis workflows may exist under:

```text
.github/workflows/
```

---
## Tasukeru Advisory

**Tasukeru** is a non-blocking advisory workflow for lightweight quality, safety, and logic review.

It is designed to help maintain this repository by collecting advisory signals from static analysis, dependency checks, workflow summaries, and project-specific logic checks.

Tasukeru is **not** a production security guarantee.  
It is a support layer for reviewing code quality, common Python issues, dependency risks, repository consistency, and advisory findings during development.

Current Tasukeru functions include:

- **Ruff advisory scan**  
  Detects Python style issues, unused imports, import-position issues, syntax-level problems, and other lint findings.

- **Bandit advisory scan**  
  Reports common Python security warnings such as non-cryptographic randomness, `assert` usage, and risky implementation patterns.

- **pip-audit dependency scan**  
  Checks Python dependencies for known vulnerability advisories.

- **Tasukeru logic review**  
  Checks project-specific consistency rules, including unresolved merge conflict markers, ARL invariant violations, license-policy inconsistencies, workflow hazards, and potential side-effect patterns.

- **ARL / governance invariant advisory checks**  
  Reviews whether audit-style records follow expected safety contracts such as canonical decisions, required ARL keys, non-sealed RFL behavior, and proper sealed-state semantics.

- **GitHub Actions summary output**  
  Generates a readable advisory summary inside the workflow run.

- **Artifact output**  
  Uploads advisory logs so raw scan results can be reviewed later.

Tasukeru is intentionally treated as **advisory / non-blocking**.

Its purpose is to surface issues early without preventing research iterations from continuing.

In short:

> **Tasukeru helps review the repository, but it does not replace human judgment.**
---

## Design stance

This repository is centered on a fail-closed mindset:

- stop on uncertainty
- escalate on risk
- preserve auditability
- keep human judgment in the loop where required

Common themes across the simulations include:

- fixed gate ordering
- explicit stop / pause semantics
- reproducibility-oriented tests
- structured logging and replayability
- human-in-the-loop escalation boundaries

---

## Safety and scope

This repository is a **research prototype**.

It is not intended for:

- production autonomous decision-making
- unsupervised real-world control
- legal, medical, financial, or regulatory advice
- processing real personal data or confidential operational data
- demonstrating complete or universal safety coverage

The examples should be read as:

- research simulations
- educational references
- governance / safety test benches
- fail-closed and HITL design examples

---

## Testing and behavior

In this repository, tests often define the expected behavior of the simulators and orchestration logic.

When checking behavior, it is usually better to read the implementation together with the corresponding tests.

Example:

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

This is especially important for:

- gate invariants
- reason-code expectations
- HITL transitions
- sealed / non-sealed behavior
- reproducibility checks
- benchmark expectations

---

## Notes

Some files are preserved for historical comparison, reproducibility, or versioned experiments.

A newer version number does not always mean that the file is the primary recommended entry point.

Files under `archive/` should generally be treated as historical or reference material unless explicitly referenced by current tests or documentation.

---

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

---

## License

## License

This repository uses a split-license model:

- Software code: **Apache License 2.0**
- Documentation, diagrams, and research materials: **CC BY-NC-SA 4.0**

See [LICENSE_POLICY.md](./LICENSE_POLICY.md) for details.
