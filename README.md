# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

<p align="center">
  <!-- Repository Status -->
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License (Policy Intent)">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <!-- Technical Meta -->
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <img src="https://img.shields.io/badge/status-research--prototype-brightgreen.svg?style=flat-square" alt="Status">
  <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/v/release/japan1988/multi-agent-mediation?style=flat-square" alt="Latest Release">
</p>

---

## 🎯 Purpose

This repository is a **research-oriented orchestration framework** for supervising multiple agents (or multiple methods) and performing:

- **STOP**: Halt execution when errors/hazards/uncertainty are detected
- **REROUTE**: Branch or re-route only when safe to do so
- **HITL**: Escalate to humans for ambiguous or high-stakes decisions

The focus is not “negotiation itself,” but **supervision and control**:

- **Routing**: Task decomposition and assignment (who does what)
- **Guardrails**: Sealing forbidden intent / overreach / external side effects (fail-closed)
- **Audit**: Logging what was stopped and why (accountability)
- **HITL**: Escalation for undefined specs or non-decidable cases
- **Replay**: Re-run under the same conditions and detect deltas

---

## 🔒 Safety Model (Fail-Closed)

This project is intended for **Educational / Research** purposes, and prioritizes **fail-closed** safety.

- If forbidden intent, overreach, low confidence, or ambiguous sensitive intent is detected in input/output/plan, **it does not auto-execute**  
  → It falls back to **STOP** or **HITL** (`PAUSE_FOR_HITL`).
- It avoids “fail-open reroute” (continuing by swapping to another agent in risky situations).  
  Forbidden categories and overreach should **stop**, not reroute.

---

## 🌍 External Side Effects (Definition & Allowlist)

**External side effects** are actions that can read/write external state, for example:

- Network access (read/write)
- Filesystem access
- Command execution
- Messaging (email/DM)
- Payments / purchases / account operations
- Access to **PII sources** (contacts / CRM / mailbox)

**Default policy: deny-by-default**

- Network: **DENY** (except explicitly permitted research experiments)
- Filesystem: **DENY** (if needed, restrict to minimal scope such as a log directory)
- Command execution: **DENY**
- Messaging / email / DM: **DENY**
- Payments / billing: **DENY**
- PII sources (contacts / CRM / mailbox): **DENY**
- Unknown tools: **DENY**

When adding a tool, declare the tool type (e.g., benign / pii_source) and side-effect category. Unknown tools must always be **DENY**.

---

## 👤 HITL (Human-in-the-Loop)

Escalate to humans when:

- Intent is ambiguous and may be sensitive
- Policy confidence is insufficient
- Execution may involve external side effects

HITL should be represented as a state (e.g., `PAUSE_FOR_HITL`) and MUST log **reason_code** and **evidence**.

---

## 🚫 Non-goals / Out of Scope

This project does NOT aim to build or enable:

- Targeted persuasion/manipulation/psychological pressure optimization
- “Reeducation” or coercive guidance systems for real users
- Identity verification, doxxing, surveillance, PII extraction
- Autonomous real-world actions (sending messages, purchasing, account operations)
- Fully automated final decisions in high-stakes domains (legal/medical/investment)

If such intent is detected, it is treated as **misuse** and should default to **STOP** or **HITL**.

> Note: If modules evoke “persuasion / reeducation,” they must be treated as **safety-evaluation scenarios only** (test-case generation / attack simulation), and must be **disabled by default** (not runnable without an explicit opt-in flag).

---

## 🧾 Audit Log & Data Policy

Audit logs are verification artifacts for reproducibility and accountability.

- Prefer **not** to store raw sensitive information or PII. Log **hashes** and **reason_code/evidence** instead.
- If sensitive records may be produced, apply local storage constraints, masking, and retention limits.

Recommended minimum fields:

- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`, `config_hash`

---

## ✅ Success Metrics (KPI)

Examples of minimal research KPIs:

- **Dangerous action block recall** ≥ 0.95 (stop what must be stopped)
- Measure and report **false block rate / precision** (visibility into over-blocking)
- **HITL rate** and breakdown by reason
- **Audit log completeness**: missing required fields rate = 0%
- **Replay reproducibility**: decision traces match under same seed/config

---

## ⚡ Quick Start (30 seconds)

```bash
# 1) dependencies
pip install -r requirements.txt

# 2) run a core script (example)
python ai_mediation_all_in_one.py

# 3) run tests
pytest -q
````

---

## 🧠 Concept Overview

<!-- [DOC-TBL-001] Render tables reliably as Markdown -->

| Component             | Function             | Description                                                                          |
| --------------------- | -------------------- | ------------------------------------------------------------------------------------ |
| Orchestration Layer   | Command layer        | Task decomposition, routing, retries, reassignment                                   |
| Safety & Policy Layer | Safety control layer | Detect and seal dangerous output, overreach, and external side effects (fail-closed) |
| Audit & Replay Layer  | Audit layer          | Audit logs, delta detection, reproducible replay, report generation                  |
| HITL Escalation       | Human escalation     | Return to humans for uncertainty, high-risk, or undefined specs                      |

The goal is not “making multiple agents run,” but building supervision that can stop errors, hazards, and uncertainty.

---

## 🗂️ Repository Structure

<!-- [DOC-TBL-002] Render tables reliably as Markdown -->

| Path                                          | Type          | Description                                                                                                                                       |
| --------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agents.yaml`                                 | Config        | Agent definitions (parameters / role foundation)                                                                                                  |
| `mediation_core/`                             | Core          | Core logic (centralized models / shared processing)                                                                                               |
| `ai_mediation_all_in_one.py`                  | Core          | Entry point for orchestration execution (routing / checks / branching)                                                                            |
| `ai_governance_mediation_sim.py`              | Simulator     | Validate policy application / sealing / escalation behavior                                                                                       |
| `kage_orchestrator_diverse_v1.py`             | Experiment    | Verify “dangerous tool execution” remains blocked under fault injection (audit JSONL)                                                             |
| `ai_doc_orchestrator_kage3_v1_2_2.py`         | Experiment    | Doc Orchestrator (Meaning/Consistency/Ethics gates + PII non-persistence)                                                                         |
| `test_ai_doc_orchestrator_kage3_v1_2_2.py`    | Test          | Fix Doc Orchestrator behavior (PII non-persistence, etc.)                                                                                         |
| `tests/kage_definition_hitl_gate_v1.py`       | Experiment    | HITL gate experiment: “If definition is ambiguous, return to humans”                                                                              |
| `tests/test_definition_hitl_gate_v1.py`       | Test          | Pytest fixture for the HITL gate (including Ruff)                                                                                                 |
| `tests/test_kage_orchestrator_diverse_v1.py`  | Test          | Fix invariants via pytest (e.g., PII tool non-execution)                                                                                          |
| `tests/test_sample.py`                        | Test          | Minimal test / CI smoke check                                                                                                                     |
| `tests/verify_stop_comparator_v1_2.py`        | Tool          | Single-file verifier (hash/py_compile/import/self_check, etc.)                                                                                    |
| `docs/`                                       | Docs          | Figures/materials (architecture, flows, etc.)                                                                                                     |
| `docs/multi_agent_architecture_overview.webp` | Diagram       | Overall architecture diagram                                                                                                                      |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram       | Layered model diagram                                                                                                                             |
| `docs/sentiment_context_flow.png`             | Diagram       | Input → context → action flow diagram                                                                                                             |
| `.github/workflows/python-app.yml`            | Workflow      | CI (lint + pytest, multiple Python versions)                                                                                                      |
| `requirements.txt`                            | Dependency    | Python dependencies                                                                                                                               |
| `LICENSE`                                     | License       | Apache-2.0 (see file). Intended use is Educational / Research (policy), not a license restriction. <!-- [DOC-LIC-001] Avoid license confusion --> |
| `README.md`                                   | Documentation | This document                                                                                                                                     |

---

## 🧭 Architecture Diagram

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

---

## 🧭 Layered Agent Model

<!-- [DOC-TBL-003] Render tables reliably as Markdown -->

| Layer            | Role                 | What it does                                                              |
| ---------------- | -------------------- | ------------------------------------------------------------------------- |
| Interface Layer  | External input layer | Input contract (schema) / validation / log submission                     |
| Agent Layer      | Execution layer      | Task processing (proposal / generation / verification, depending on role) |
| Supervisor Layer | Supervisory layer    | Routing, consistency checks, stopping, HITL                               |

---

## 🔬 Context Flow

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

* Perception — Decompose input into executable elements (tasking)
* Context — Extract assumptions/constraints/risk factors (guard rationale)
* Action — Instruct agents, verify results, branch (STOP / REROUTE / HITL)

---

## ⚙️ Execution Examples

<!-- [DOC-SAFE-003] Reduce accidental execution/misinterpretation -->

> Note: Files whose names evoke “persuasion / reeducation” are intended for safety-evaluation scenarios (test-case generation / attack simulation) only.
> They should be treated as non-default / opt-in experiments, consistent with the Non-goals section.

```bash
# Core (routing / gating / branching)
python ai_mediation_all_in_one.py

# Orchestrator fault-injection / capability guard demo
python kage_orchestrator_diverse_v1.py

# Doc Orchestrator (Meaning/Consistency/Ethics + PII non-persistence)
python ai_doc_orchestrator_kage3_v1_2_2.py

# Policy application behavior check
python ai_governance_mediation_sim.py
```

---

## 🧪 Tests

```bash
# all tests
pytest -q

# focused: HITL gate test
pytest -q tests/test_definition_hitl_gate_v1.py

# focused: orchestrator diverse test
pytest -q tests/test_kage_orchestrator_diverse_v1.py

# focused: doc orchestrator test
pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
```

CI runs lint/pytest across multiple Python versions via `.github/workflows/python-app.yml`.

---

## 📌 License

See `LICENSE`.

This project is intended for Educational / Research purposes (policy intent).
The repository license is Apache-2.0 (see `LICENSE`).

