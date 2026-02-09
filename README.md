# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)
> Japanese version: [README.ja.md](README.ja.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

## Overview

Maestro Orchestrator is a **research / educational** orchestration framework that prioritizes:

- **Fail-closed**  
  If uncertain, unstable, or risky → do not continue silently.
- **HITL (Human-in-the-Loop)**  
  Decisions that require human judgment are explicitly escalated.
- **Traceability**  
  Decision flows are audit-ready and reproducible via minimal ARL logs.

This repository contains **implementation references** (doc orchestrators) and **simulation benches**
for negotiation, mediation, governance-style workflows, and gating behavior.

---

## Quickstart (recommended path)

Start with one script, confirm behavior and logs, then expand.

### 1) Run the latest emergency contract simulator (v4.8)

```bash
python mediation_emergency_contract_sim_v4_8.py
````

### 2) Run the pinned smoke test (v4.8)

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 3) Optional: inspect evidence bundle (generated artifact)

* `docs/artifacts/v4_8_artifacts_bundle.zip`

> Note: evidence bundles (zip) are **generated artifacts** produced by tests/runs.
> The canonical source of truth is the generator scripts + tests.

---

## Architecture (high level)

Audit-ready and fail-closed control flow:

agents
→ mediator (risk / pattern / fact)
→ evidence verification
→ HITL (pause / reset / ban)
→ audit logs (ARL)

![Architecture](docs/architecture_unknown_progress.png)

> If the image does not render, confirm that
> `docs/architecture_unknown_progress.png` exists on the same branch and that the filename matches exactly (case-sensitive).

---

## Architecture (code-aligned diagrams)

The following diagrams are **aligned with the current code vocabulary**.
They separate **state transitions** from **gate order** to preserve auditability and avoid ambiguity.

> Documentation-only. No logic changes.

---

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing where execution **pauses (HITL)**
or **stops permanently (SEALED)**.

<p align="center">
  <img src="docs/architecture_state_machine_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Primary execution path**

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

**Notes**

* `PAUSE_FOR_HITL_*` represents an explicit **Human-in-the-Loop** decision point (user approval or admin approval).
* `STOPPED (SEALED)` is reached on:

  * invalid or fabricated evidence
  * authorization expiry
  * draft lint failure
* **SEALED stops are fail-closed and non-overrideable by design.**

---

### 2) Gate Pipeline (code-aligned)

Ordered evaluation gates, **independent from lifecycle state transitions**.

<p align="center">
  <img src="docs/architecture_gate_pipeline_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

* This diagram represents **gate order**, not state transitions.
* `PAUSE` indicates **HITL required** (human decision pending).
* `STOPPED (SEALED)` indicates a **non-recoverable safety stop**.

**Design intent**

* **State Machine** answers: *“Where does execution pause or terminate?”*
* **Gate Pipeline** answers: *“In what order are decisions evaluated?”*

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

**Maintenance note**

If an image does not render:

* Confirm the file exists under `docs/`
* Confirm the filename matches exactly (case-sensitive)
* Prefer copy-paste from the file list when updating links

---

## What’s new (timeline)

### 2026-01-21

**Added**

* `ai_mediation_hitl_reset_full_with_unknown_progress.py`
  Simulator for **unknown progress** scenarios with HITL/RESET semantics.
* `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`
  v1.7-IEP aligned simulator for **RFL relcode branching** (RFL is non-sealing → escalates to HITL).

**Changed**

* `ai_doc_orchestrator_kage3_v1_2_4.py`
  Doc orchestrator reference updated with **post-HITL semantics**.

---

### 2026-02-03

**Added**

* `mediation_emergency_contract_sim_v1.py`
  Minimal emergency workflow simulator:
  USER auth → AI draft → ADMIN finalize → contract effective
  Invalid or expired events fail-closed and stop execution, producing a minimal ARL (JSONL).
* `mediation_emergency_contract_sim_v4.py`
  Extended v1 with:

  * evidence gate
  * draft lint gate
  * trust / grant–based HITL friction reduction

---

### 2026-02-05 (v4.1 behavior tightening)

**Changed**

* **RFL is non-sealing by design**
  Boundary-unstable proposals trigger `PAUSE_FOR_HITL` with `sealed=false` and `overrideable=true` (human decides).
* **Fabrication flagged early, sealing only in ethics**
  Evidence fabrication is flagged in evidence gate; the only sealing stop is issued by `ethics_gate` (`STOPPED` with `sealed=true`).
* **Trust/grant friction reduction preserved**
  Trust/grant-based AUTH auto-skip behavior stays supported when thresholds are satisfied, while still logging reasons to ARL.

**Repro**

```bash
python mediation_emergency_contract_sim_v4_1.py
```

**Expected**

* NORMAL -> CONTRACT_EFFECTIVE
* FABRICATE -> STOPPED (sealed=true in ethics_gate)
* RFL_STOP -> STOPPED (sealed=false via HITL stop)

**Regression test**

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
```

**Pinned invariants**

* SEALED is issued only by `ethics_gate` / `acc_gate` (RFL never seals).
* RFL is non-sealing by design (RFL → PAUSE_FOR_HITL, human decides).

---

### 2026-02-07 (v4.4 + stress evidence)

**Added**

* `mediation_emergency_contract_sim_v4_4.py`
  Emergency contract workflow bench v4.4 (fail-closed + HITL + minimal ARL).
* `mediation_emergency_contract_sim_v4_4_stress.py`
  Stress runner for v4.4 (distribution + invariant checks).
* `stress_results_v4_4_1000.json`
  Stress summary (1,000 runs).
* `stress_results_v4_4_10000.json`
  Stress summary (10,000 runs).

**Pinned invariants**

* SEALED is issued only by `ethics_gate` / `acc_gate` (RFL never seals).
* RFL is non-sealing by design (RFL → PAUSE_FOR_HITL, human decides).

---

### 2026-02-08 (v4.6 + 100k stress baseline)

**Added**

* `mediation_emergency_contract_sim_v4_6.py`
  Emergency contract workflow bench v4.6 (fail-closed + HITL + minimal ARL).
* `stress_results_v4_6_100000.json`
  Reproducible stress evidence for v4.6 (100,000 runs).

**Why (what v4.6 established)**

* v4.6 serves as a reproducible baseline where unsafe paths are stopped early (fail-closed) and logged via ARL.

---

### 2026-02-08 (v4.7 coaching + compliance signal)

**Added**

* `mediation_emergency_contract_sim_v4_7_full.py`
  v4.7 introduces **coaching** by the top (highest-score) agent to reduce low-trust “shortest-path” retries and improve clean completion.
* (Optional feature) **evaluation multiplier loop**
  Tracks “clean completion” and maintains a multiplier (+0.1 per clean completion, capped), finalized at HITL finalize stage.

**Changed**

* **Critical fix:** word-boundary regex was not functioning in `draft_lint_gate`
  Patterns used raw strings with `\\b` (double backslash), so `\b` did not work as a “word boundary”.
  Fix: `\\b` → `\b` (7 occurrences) so word-boundary matching works as intended.

**Evidence (focused micro-bench)**

* `stress_report_v4_7_draft_lint_100k_seed42.json`
  Validates that stop rates align with configured weights after the word-boundary fix.

> Note: micro-bench is scoped to `draft_lint_gate` only; it is not a general safety claim.

---

### 2026-02-09 (v4.8 ARL detail + evidence bundle)

**Diff summary (v4.6 vs v4.7 vs v4.8)**

* **v4.6**: baseline + 100k stress evidence (fail-closed + HITL + minimal ARL).
* **v4.7**: behavior-side improvement — coaching/compliance signal (and optional eval loop) to reduce low-trust shortest-path retries; plus draft-lint regex hardening.
* **v4.8**: observability-side improvement — ARL detail + evidence bundle so STOP/PAUSE causes are reviewable and actionable.

**Changed**

* v4.8 focuses on **ARL detail** so STOP/PAUSE causes are more actionable
  (reduces human re-triage burden and improves iterative correction).

**Added**

* `mediation_emergency_contract_sim_v4_8.py`
* `tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py`
* `docs/artifacts/v4_8_artifacts_bundle.zip` (ARL + results + report)

**Repro**

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

**Note**

* The zip is an **evidence bundle generated by tests/runs**; do not treat it as canonical source.

---

## V1 → V4: What actually changed

`mediation_emergency_contract_sim_v1.py` demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

**Added in v4**

* **Evidence gate**
  Basic verification of evidence bundles. Invalid/irrelevant/fabricated evidence triggers fail-closed stops.
* **Draft lint gate**
  Enforces draft-only semantics and scope boundaries before admin finalization.
* **Trust system (score + streak + cooldown)**
  Trust increases on successful HITL outcomes and decreases on failures. Cooldown prevents unsafe automation after errors. All transitions are logged in ARL.
* **AUTH HITL auto-skip (safe friction reduction)**
  When trust threshold + approval streak + valid grant are satisfied, AUTH HITL can be skipped for the same scenario/location only, while recording reasons in ARL.

---

## Execution examples

**Doc orchestrator (reference implementation)**

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

**Emergency contract (v4.8)**

```bash
python mediation_emergency_contract_sim_v4_8.py
```

**Emergency contract (v4.1)**

```bash
python mediation_emergency_contract_sim_v4_1.py
```

**Emergency contract stress (v4.4)**

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## Project intent / non-goals

### Intent

* Reproducible safety and governance simulations
* Explicit HITL semantics (pause/reset/ban)
* Audit-ready decision traces (minimal ARL)

### Non-goals

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## Data & safety notes

* Use **synthetic/dummy data** only.
* Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible.
* Treat generated bundles (zip) as **reviewable evidence**, not canonical source.

---

## License

Apache License 2.0 (see `LICENSE`)
