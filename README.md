# Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

> 日本語版: [README.ja.md](README.ja.md)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
[![Open Issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square)](https://github.com/japan1988/multi-agent-mediation/issues)
[![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation?style=flat-square)](./LICENSE)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)

> **If uncertain, stop. If risky, escalate.**
>
> Research / educational governance simulations for agentic workflows.

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising agent workflows with **fail-closed safety**, **HITL escalation**, and **audit-ready traceability**.

This repository focuses on governance / mediation / negotiation-style simulations and implementation references for **traceable, reproducible, safety-first orchestration**.

It is designed to help inspect how orchestration layers should behave when a system encounters:

* uncertainty
* insufficient evidence
* relative / unstable judgments
* policy or ethics violations
* escalation conditions requiring human review

The repository is intentionally structured as a **research / educational bench**, not as a production autonomy framework.

---

## Purpose

Maestro Orchestrator is built around three priorities:

* **Fail-closed**
  If uncertain, unstable, or risky, do not continue silently.

* **HITL escalation**
  Decisions requiring human judgment are explicitly escalated.

* **Traceability**
  Decision flows are reproducible and audit-ready through minimal ARL logs.

This repository is best read as a:

* research prototype
* educational reference
* governance / safety simulation bench

It is **not** a production autonomy framework.

---

## Safety Model

This repository prioritizes **fail-closed behavior**.

If a workflow becomes uncertain, policy-violating, unstable, or insufficiently grounded, it should:

* **STOP**
* **PAUSE_FOR_HITL**
* or remain blocked until reviewed

The design goal is to avoid silent continuation under ambiguity.

### Core safety ideas

* **Uncertain → stop or escalate**
* **Risky → stop**
* **Human judgment required → HITL**
* **Sealed decisions remain sealed**
* **Unknown external side effects are denied by default**

### External side effects

By default, the framework assumes a deny-by-default posture for actions that could affect the outside world, such as:

* network access
* filesystem writes
* shell / command execution
* messaging / email / DM
* account, billing, or purchase actions
* access to PII-bearing sources

This repository is primarily about **control logic, mediation logic, and auditable simulation behavior**, not unrestricted action execution.

---

## What this repository is

This repository provides:

* fail-closed + HITL orchestration benches for governance-style workflows
* reproducible simulators with seeded runs and pytest-based contract checks
* audit-ready traces via minimal ARL logs
* reference implementations for orchestration / gating behavior

Typical themes in this repository include:

* orchestration
* mediation
* negotiation
* governance simulation
* escalation policy
* contract-style invariants
* replayability
* lightweight audit logs

---

## Quickstart (recommended path)

**v5.1.x** is the recommended line for reproducibility and contract checks.
**v4.x** is retained as a legacy stable bench.

Start with one simulator, confirm behavior and logs, then expand.

### 1) Run the recommended emergency contract simulator

```bash
python mediation_emergency_contract_sim_v5_1_2.py
```

This is the recommended entry point if you want:

* reproducibility-oriented runs
* contract-style checks
* minimal audit output for inspection
* incident-oriented abnormal-run analysis

### 2) Run the test suite

```bash
pytest -q
```

### 3) Inspect outputs

Look for:

* emitted `layer / decision / final_decider / reason_code`
* fail-closed stops
* HITL-required paths
* minimal ARL behavior
* reproducible seeded outcomes

### 4) Run the legacy stable bench if needed

```bash
python mediation_emergency_contract_sim_v4_1.py
```

Use the v4.x line if you want an older stable benchmark path for comparison.

---

## Recommended reading path

If you are new to the repository, this order is the easiest:

1. `README.md`
2. `README.ja.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/`
5. `.github/workflows/python-app.yml`
6. `.github/workflows/tasukeru-analysis.yml`

Then branch out into older simulators and related governance / mediation experiments.

---

## Main files and directories

Below is the practical map of the repository.

### Core / main entry points

* `mediation_emergency_contract_sim_v5_1_2.py`
  Recommended reproducible emergency-contract simulator

* `mediation_emergency_contract_sim_v5_0_1.py`
  Earlier v5 line

* `mediation_emergency_contract_sim_v4_1.py`
  Legacy stable bench

* `ai_doc_orchestrator_kage3_v1_2_4.py`
  Document-oriented orchestration / gating reference

* `ai_doc_orchestrator_kage3_v1_3_5.py`
  Expanded orchestration reference with benchmark-related helpers

* `loop_policy_stage3.py`
  Stage-3 loop policy and HITL / stop logic

### Repository structure

* `tests/`
  Contract tests, regression tests, orchestration behavior checks

* `benchmarks/`
  Benchmark-oriented tests and negotiation-pattern checks

* `docs/`
  Supporting documentation and diagrams

* `archive/`
  Archived experiments and older artifacts

* `.github/workflows/`
  CI and analysis workflow definitions

### Supporting files

* `README.ja.md`
  Japanese README

* `LICENSE`
  License file

* `requirements.txt`
  Python dependencies

* `pytest.ini`
  Pytest configuration

* `log_codebook_v5_1_demo_1.json`
  Demo codebook for emitted vocabulary / logging consistency

* `log_format.md`
  Log-related documentation

---

## Version guide

### v5.1.x

Recommended when you want:

* stronger reproducibility
* contract-style vocabulary checks
* minimal ARL / abnormal-run trace handling
* benchmark-oriented inspection

### v5.0.x

Earlier v5 line. Useful if you want to compare design evolution.

### v4.x

Legacy stable benchmark line. Good for:

* simpler baseline comparison
* historical progression
* compatibility checks with older tests or notes

### Other simulators

The repository also contains multiple experimental or thematic simulators related to:

* governance mediation
* alliance / persuasion dynamics
* hierarchy dynamics
* reeducation / social dynamics
* all-in-one mediation experiments

These are useful as reference material, but the recommended starting point remains **v5.1.2**.

---

## Audit and logging model

A central design goal is **audit-ready behavior without overcomplicating the log surface**.

The repository uses lightweight audit patterns such as:

* explicit `decision`
* explicit `reason_code`
* explicit `final_decider`
* sealed vs non-sealed control paths
* reproducible seeded runs
* testable emitted vocabularies

In practical terms, the logs are meant to answer:

* what was blocked
* where it was blocked
* why it was blocked
* whether human intervention was required
* whether the outcome can be reproduced

---

## HITL semantics

The repository treats HITL as a first-class control path, not as an afterthought.

Typical behavior:

* uncertain but non-sealed conditions → `PAUSE_FOR_HITL`
* user continuation may allow progress in allowed cases
* sealed safety outcomes remain non-overrideable
* important judgment calls are surfaced explicitly

This makes the orchestration model easier to inspect, test, and replay.

---

## Reproducibility

Reproducibility matters throughout the repository.

Common patterns include:

* deterministic seeds
* fixed emitted vocabularies
* contract-style assertions in tests
* explicit abnormal-run inspection
* stable decision categories

The intent is not just to “run a simulation,” but to make its control behavior **observable and comparable across runs**.

---

## Testing

The repository uses pytest-based checks to validate orchestration behavior.

Typical checks include:

* emitted vocabulary consistency
* gate invariants
* fail-closed behavior
* HITL continuation / stop semantics
* benchmark output structure
* regression behavior for known scenarios

Run all tests with:

```bash
pytest -q
```

Run a focused subset if needed:

```bash
pytest tests/test_benchmark_profiles_v1_0.py -q
```

---

## CI / analysis workflows

The repository includes CI and analysis workflows under `.github/workflows/`.

These workflows are used to validate:

* Python test execution
* YAML validity
* static analysis
* repository hygiene
* security-oriented reporting

The two primary badges in this README correspond to:

* **Python App CI**
* **Tasukeru Analysis**

---

## Example usage mindset

This repository is most useful when you want to answer questions like:

* How should an orchestrator behave under uncertainty?
* When should a system stop instead of rerouting?
* What should be escalated to HITL?
* How can decision paths remain inspectable and reproducible?
* How can orchestration rules be tested like contracts?

It is less about maximizing autonomy, and more about **making orchestration behavior governable**.

---

## Non-goals

This repository is **not** intended to be:

* a production agent platform
* a general-purpose autonomous execution engine
* a fail-open multi-tool runtime
* a “keep going no matter what” orchestration layer

The emphasis is on **controlled behavior**, not maximum autonomy.

---

## Research / educational note

This repository is provided for **research and educational purposes**.

It is intended to demonstrate:

* orchestration control patterns
* mediation / governance simulation structures
* fail-closed guardrails
* audit / replay-oriented design
* HITL escalation semantics

It is not a promise of production readiness, completeness, or universal policy coverage.

---

## License

See [LICENSE](./LICENSE).

---

## Language

* English README: `README.md`
* Japanese README: `README.ja.md`

---

## Summary

Maestro Orchestrator is a safety-first orchestration framework for studying how agent workflows should behave when they encounter uncertainty, risk, or human-judgment boundaries.

Its core stance is simple:

> **If uncertain, stop. If risky, escalate.**


