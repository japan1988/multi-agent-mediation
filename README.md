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

```

agents
→ mediator (risk / pattern / fact)
→ evidence verification
→ HITL (pause / reset / ban)
→ audit logs (ARL)

```

![Architecture](docs/architecture_unknown_progress.png)

> If the image does not render, confirm that  
> `docs/architecture_unknown_progress.png` exists on the same branch and that the filename matches exactly (case-sensitive).

---

## Architecture (Code-aligned diagrams)

The following diagrams are **fully aligned with the current code and terminology**.  
They intentionally separate **state transitions** from **gate order** to preserve auditability and avoid ambiguity.

These diagrams are **documentation-only** and introduce **no logic changes**.

---

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing where execution **pauses (HITL)** or **stops permanently (SEALED)**.

<p align="center">
  <img src="docs/architecture_code_aligned_state_machine.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Notes**

**Primary execution path**

```

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

```

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
  <img src="docs/architecture_code_aligned_gate_pipeline.png"
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

If an image does not render:
- Confirm the file exists under `docs/`
- Confirm the filename matches exactly (case-sensitive)
- Prefer copy-paste from the file list when updating links

---

## What’s new (2026-01-21)

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  Simulator for **unknown progress** scenarios with HITL/RESET semantics.
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  **KAGE v1.7-IEP** aligned simulator for **RFL relcode branching**  
  (RFL is non-sealing → escalates to HITL).
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  Doc orchestrator reference updated with **post-HITL semantics**.

---

## What’s new (2026-02-03)

Introduced an **event-driven governance-style workflow**
(fail-closed + HITL + audit-ready).

- **New**: `mediation_emergency_contract_sim_v1.py`  
  Minimal emergency workflow simulator:

```

USER auth → AI draft → ADMIN finalize → contract effective

````

Invalid or expired events fail-closed and stop execution,
producing a minimal ARL (JSONL).

- **New**: `mediation_emergency_contract_sim_v4.py`  
Extended v1 with:
- evidence gate
- draft lint gate
- trust / grant–based HITL friction reduction

---

## V1 → V4: What actually changed

`mediation_emergency_contract_sim_v1.py` demonstrates the **minimum viable pipeline**:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a
**repeatable governance bench** by adding early rejection and controlled automation.

### Added in v4

- **Evidence gate**  
Basic verification of evidence bundles.  
Invalid, irrelevant, or fabricated evidence triggers fail-closed stops.

- **Draft lint gate**  
Enforces *draft-only* semantics and scope boundaries before admin finalization.  
Hardened against markdown/emphasis noise to reduce false positives.

- **Trust system (score + streak + cooldown)**  
Trust increases on successful HITL outcomes and decreases on failures.  
Cooldown prevents unsafe automation after errors.  
All trust transitions are logged in ARL.

- **AUTH HITL auto-skip (safe friction reduction)**  
When **trust threshold + approval streak + valid grant** are satisfied,
AUTH HITL can be skipped *for the same scenario/location only*,
while recording the reason in ARL.

**In short**

- **V1 answers**: *“Can this workflow fail-closed with minimal audit?”*  
- **V4 answers**: *“Can we safely repeat this workflow at scale without losing traceability?”*

---

## ⚙️ Execution Examples

Start with **one script**, confirm behavior and logs, then expand.

> NOTE: This repository is **research / educational**.  
> Use **synthetic or dummy data** and do not commit runtime logs.

### Recommended

#### 1) Doc orchestrator (reference implementation)

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
````

#### 2) Emergency contract workflow (v4)

```bash
python mediation_emergency_contract_sim_v4.py
```

---

### Semantics / bench-focused

#### Unknown progress + HITL/RESET

```bash
python ai_mediation_hitl_reset_full_with_unknown_progress.py
```

#### KAGE v1.7-IEP RFL relcode branching

```bash
python ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py
```

---

### Compare baseline vs extended

```bash
python mediation_emergency_contract_sim_v1.py
python mediation_emergency_contract_sim_v4.py
```

---

### Copilot SDK minimal example

```bash
python copilot_mediation_min.py
```

---

## Project intent / non-goals

**Intent**

* Reproducible safety and governance simulations
* Explicit HITL semantics
* Audit-ready decision traces

**Non-goals**

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## License

Apache-2.0. See `LICENSE`.

```

---

必要なら次のステップとして：

- **README.ja.md 側の完全同期版**
- **V1 / V4 を1枚で比較する補助図（表）**
- **「なぜ state / gate を分離したか」の短い設計思想セクション**

もすぐ出せます。
```

