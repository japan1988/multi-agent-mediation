# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)
> 日本語版: [README.ja.md](README.ja.md)

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
  All decision flows are audit-ready and reproducible via minimal ARL logs.

This repository contains **implementation references** (doc orchestrators) and **simulation benches**
for negotiation, mediation, governance-style workflows, and gating behavior.

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

## Architecture (Code-aligned diagrams)

The following diagram is **fully aligned with the current code and terminology**.  
It intentionally separates **state transitions** from **gate order** to preserve auditability and avoid ambiguity.

This diagram is **documentation-only** and introduces **no logic changes**.

---

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing where execution **pauses (HITL)**  
or **stops permanently (SEALED)**.

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Notes**

**Primary execution path**

INIT  
→ PAUSE_FOR_HITL_AUTH  
→ AUTH_VERIFIED  
→ DRAFT_READY  
→ PAUSE_FOR_HITL_FINALIZE  
→ CONTRACT_EFFECTIVE

- `PAUSE_FOR_HITL_*` represents an explicit **Human-in-the-Loop** decision point  
  (user approval or admin approval).
- `STOPPED (SEALED)` is reached on:
  - invalid or fabricated evidence
  - authorization expiry
  - draft lint failure
- **SEALED stops are fail-closed and non-overrideable by design.**

---

### 2) Gate Pipeline (code-aligned)

Ordered evaluation gates, **independent from lifecycle state transitions**.

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

- This diagram represents **gate order**, not state transitions.
- `PAUSE` indicates **HITL required** (human decision pending).
- `STOPPED (SEALED)` indicates a **non-recoverable safety stop**.

**Design intent**

- **State Machine** answers:  
  *“Where does execution pause or terminate?”*
- **Gate Pipeline** answers:  
  *“In what order are decisions evaluated?”*

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

**Maintenance note**

If the image does not render:
- Confirm the file exists under `docs/`
- Confirm the filename matches exactly (case-sensitive)
- Prefer copy-paste from the file list when updating links

---

## What’s new (2026-01-21)

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  Simulator for **unknown progress** scenarios with HITL/RESET semantics.
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  v1.7-IEP aligned simulator for **RFL relcode branching**  
  (RFL is non-sealing → escalates to HITL).
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  Doc orchestrator reference updated with **post-HITL semantics**.

---

## What’s new (2026-02-03)

Introduced an **event-driven governance-style workflow**
(fail-closed + HITL + audit-ready).

- **New**: `mediation_emergency_contract_sim_v1.py`  
  Minimal emergency workflow simulator:

  USER auth → AI draft → ADMIN finalize → contract effective

  Invalid or expired events fail-closed and stop execution,
  producing a minimal ARL (JSONL).

- **New**: `mediation_emergency_contract_sim_v4.py`  
  Extended v1 with:
  - evidence gate
  - draft lint gate
  - trust / grant–based HITL friction reduction

---

## What’s new (2026-02-05)

- **New**: `mediation_emergency_contract_sim_v4_1.py`  
  v4.1 is a **behavior-tightening** update over v4.0 to make the bench expectations explicit and code-aligned:

  - **RFL is non-sealing by design**  
    Boundary-unstable proposals trigger `PAUSE_FOR_HITL` with `sealed=false` and `overrideable=true` (human decides).

  - **Fabrication is detected early, but sealing occurs only in ethics**  
    Evidence fabrication is flagged in the evidence gate, and the **only sealing stop** is issued by `ethics_gate`
    (`STOPPED` with `sealed=true`).

  - **Trust/grant friction reduction remains supported**  
    Trust/grant-based AUTH auto-skip behavior is preserved (when thresholds are satisfied), while still logging reasons to ARL.

  **Quick run**
  ```bash
  python mediation_emergency_contract_sim_v4_1.py
````

**Expected**

* NORMAL -> `CONTRACT_EFFECTIVE`
* FABRICATE -> `STOPPED` (sealed=true in ethics_gate)
* RFL_STOP -> `STOPPED` (sealed=false via HITL stop)

### v4.1 regression test

This repo includes a dedicated pytest file that pins v4.1 behavior as a contract:

* NORMAL -> CONTRACT_EFFECTIVE (not sealed)
* FABRICATE -> STOPPED (sealed=true in ethics_gate)
* RFL_STOP -> STOPPED (sealed=false via HITL stop)

Invariant: SEALED is issued only by ethics_gate/acc_gate (RFL never seals).

Run only this test file:

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
```

Tip: CI runs the full suite by default. Use the command above for quick local verification.

---

## What’s new (2026-02-07)

* **New**: `mediation_emergency_contract_sim_v4_4.py`
  Emergency contract workflow bench v4.4 (fail-closed + HITL + minimal ARL).

* **New**: `mediation_emergency_contract_sim_v4_4_stress.py`
  Stress runner for v4.4 (distribution + invariant checks).

* **New**: `stress_results_v4_4_1000.json`
  Stress summary (1,000 runs).

* **New**: `stress_results_v4_4_10000.json`
  Stress summary (10,000 runs).

**Stress-pinned invariants**

* SEALED is issued only by `ethics_gate` / `acc_gate` (RFL never seals).
* RFL is non-sealing by design (RFL → `PAUSE_FOR_HITL`, human decides).

---

## What’s new (2026-02-08)

* **New**: `mediation_emergency_contract_sim_v4_6_full.py`
  Emergency contract workflow bench v4.6 (sim + 100k stress results).

* **New**: `stress_results_v4_6_100000.json`
  Stress summary (100,000 runs).

* **New**: `mediation_emergency_contract_sim_v4_7_full.py`
  v4.7 adds coaching to reduce low-trust “shortest-path” retries.

**Stress-pinned invariants (v4.6)**

* SEALED is issued only by `ethics_gate` / `acc_gate` (RFL never seals).
* RFL is non-sealing by design (RFL → `PAUSE_FOR_HITL`, human decides).

### v4.6 → v4.7 (why this change)

Observed (v4.6):

* When an agent’s trust score was low, it attempted a “shortest-path” route and produced **2 STOPPED outcomes**.
* Details: those 2 STOPPED were tagged as `reason_code=TRUST_SCORE_LOW`.

Change (v4.7):

* The top-ranked agent (highest score) provides coaching to the low-trust agent.

Guardrail value:

* Because the guardrails were built in from the design stage, risky low-trust shortcut attempts were contained early (fail-closed) rather than silently reaching dispatch.

Expected:

* This is expected to improve the agent state and increase clean completion (v4.7 stress results will be published later, after additional verification).

Invariants:

* SEALED is issued only by `ethics_gate` / `acc_gate` (RFL never seals).

---

## V1 → V4: What actually changed

`mediation_emergency_contract_sim_v1.py` demonstrates the **minimum viable pipeline**:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a
**repeatable governance bench** by adding early rejection and controlled automation.

### Added in v4

* **Evidence gate**
  Basic verification of evidence bundles.
  Invalid, irrelevant, or fabricated evidence triggers fail-closed stops.

* **Draft lint gate**
  Enforces *draft-only* semantics and scope boundaries before admin finalization.
  Hardened against markdown/emphasis noise to reduce false positives.

* **Trust system (score + streak + cooldown)**
  Trust increases on successful HITL outcomes and decreases on failures.
  Cooldown prevents unsafe automation after errors.
  All trust transitions are logged in ARL.

* **AUTH HITL auto-skip (safe friction reduction)**
  When **trust threshold + approval streak + valid grant** are satisfied,
  AUTH HITL can be skipped *for the same scenario/location only*,
  while recording the reason in ARL.

**In short**

* **V1 answers**: *“Can this workflow fail-closed with minimal audit?”*
* **V4 answers**: *“Can we safely repeat this workflow at scale without losing traceability?”*

---

## ⚙️ Execution Examples

Start with **one script**, confirm behavior and logs, then expand.

> NOTE: This repository is **research / educational**.
> Use **synthetic or dummy data** and do not commit runtime logs.

### Recommended

#### Doc orchestrator (reference implementation)

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

#### Emergency contract workflow (v4)

```bash
python mediation_emergency_contract_sim_v4.py
```

#### Emergency contract workflow (v4.1)

```bash
python mediation_emergency_contract_sim_v4_1.py
```

#### Emergency contract workflow (v4.4)

```bash
python mediation_emergency_contract_sim_v4_4.py
```

#### Emergency contract stress (v4.4)

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## Project intent / non-goals

### Intent

* Reproducible safety and governance simulations
* Explicit HITL semantics
* Audit-ready decision traces

### Non-goals

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## License

Apache-2.0. See [LICENSE](LICENSE).
