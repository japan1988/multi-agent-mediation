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
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License">
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

This repository is a **research-oriented orchestration framework** that supervises multiple agents (or multiple approaches) and performs **STOP / REROUTE / HITL (Human-in-the-Loop escalation)** when it detects **errors, hazards, or uncertainty**.

The main focus is not “negotiation itself,” but the following supervisory functions:

- **Routing**: Task decomposition and assignment (which agent does what)
- **Guardrails**: Sealing prohibited actions, overreach, and external side effects (fail-closed)
- **Audit**: Logging when/why execution was stopped (accountability)
- **HITL**: Escalating undecidable or high-impact decisions to humans
- **Replay**: Re-running under the same conditions and detecting deltas

---

## 🔒 Safety Model (Fail-Closed)

This repository is for **Educational / Research purposes**, and prioritizes **fail-closed safety**.

- If the framework detects **prohibited intent, overreach, insufficient confidence, or ambiguous sensitive intent** in input/output/plan, it does **not** auto-execute  
  → it falls back to **STOP** or **HITL (PAUSE_FOR_HITL)**.
- It avoids “continue by re-routing to another agent in a potentially dangerous situation (fail-open reroute).”  
  (For prohibited categories or overreach, stopping is prioritized over rerouting.)

---

## 🌍 External Side Effects (Definition & Allowlist)

**External side effects** are actions that can read/write external state, for example:

- Network access (read/write)
- Filesystem access
- Command execution
- Messaging (email/DM, etc.)
- Payments / purchases / account operations
- Access to **PII sources** (contacts / CRM / mailbox, etc.)

**Default policy: deny-by-default**
- Network: **DENY** (exception only for explicitly allowed research experiments)
- Filesystem: **DENY** (if needed, restrict to the minimum scope such as a log output directory)
- Command execution: **DENY**
- Messaging / email / DM: **DENY**
- Payments / billing: **DENY**
- PII sources (contacts / CRM / mailbox, etc.): **DENY**
- Unknown tools: **DENY**

When adding tools, declare the tool type (e.g., benign / pii_source) and side-effect category, and ensure unknown tools are always DENY.

---

## 👤 HITL (Human-in-the-Loop)

HITL escalation is recommended in the following situations:

- The intent is ambiguous and may be sensitive
- Policy confidence is insufficient
- Execution may involve external side effects

HITL is expressed as a state (e.g., `PAUSE_FOR_HITL`), and **reason codes (`reason_code`) and evidence (`evidence`) must be recorded in the audit log**.

---

## 🚫 Non-goals / Out of Scope

This project does not aim to enable (out of scope / prohibited use):

- Persuasion/manipulation/psychological pressure optimization targeting specific individuals
- “Reeducation” or coercive steering systems for real users
- Identity verification, doxxing (personal identification), surveillance, or PII extraction
- Autonomous real-world actions (sending, purchasing, account operations, etc.)
- Automating final decisions in high-risk domains (legal/medical/investment) for real-world operations

If such intent is detected, treat it as **misuse** and default to STOP/HITL by design.

> Note: If some module names may evoke “persuasion / reeducation,”  
> those must be limited to “safety evaluation scenarios (test-case generation / attack simulation),”  
> and should be **disabled by default (non-executable unless an explicit flag is provided)** as a design requirement.

---

## 🧾 Audit Log & Data Policy

Audit logs are verification artifacts for **reproducibility and accountability**.

- Avoid storing raw sensitive data or PII in logs; store **hashes** of input/output plus **reason_code/evidence** where possible.
- If sensitive records may be mixed in, apply local-only storage, masking, and retention limits.

Recommended minimum fields (example):
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`, `config_hash`

---

## ✅ Success Metrics (KPI)

Example minimal KPIs for research evaluation:

- **Dangerous action block recall** ≥ 0.95 (block what must be blocked)
- Measure/report **False block rate / Precision** (visibility into over-blocking)
- Measure **HITL rate** (escalation rate) and breakdown by reason
- **Audit log completeness**: missing required fields rate = 0%
- **Replay reproducibility**: decision traces match under the same seed/config

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

| Component                 | Function             | Description                                                                          |
| ------------------------- | -------------------- | ------------------------------------------------------------------------------------ |
| 🧩 Orchestration Layer    | Command layer        | Task decomposition, routing, retries, reassignment                                   |
| 🛡️ Safety & Policy Layer | Safety control layer | Detect and seal dangerous output, overreach, and external side effects (fail-closed) |
| 🧾 Audit & Replay Layer   | Audit layer          | Audit logs, delta detection, reproducible replay, report generation                  |
| 👤 HITL Escalation        | Human escalation     | Return to humans for uncertainty, high-risk, or undefined specs                      |

The goal is not “making multiple agents run,”
but building supervision that can **stop** errors, hazards, and uncertainty.

---

## 🗂️ Repository Structure

| Path                                          | Type          | Description                                                                           |
| --------------------------------------------- | ------------- | ------------------------------------------------------------------------------------- |
| `agents.yaml`                                 | Config        | Agent definitions (parameters / role foundation)                                      |
| `mediation_core/`                             | Core          | Core logic (centralized models / shared processing)                                   |
| `ai_mediation_all_in_one.py`                  | Core          | Entry point for orchestration execution (routing / checks / branching)                |
| `ai_governance_mediation_sim.py`              | Simulator     | Validate policy application / sealing / escalation behavior                           |
| `kage_orchestrator_diverse_v1.py`             | Experiment    | Verify “dangerous tool execution” remains blocked under fault injection (audit JSONL) |
| `ai_doc_orchestrator_kage3_v1_2_2.py`         | Experiment    | Doc Orchestrator (Meaning/Consistency/Ethics gates + PII non-persistence)             |
| `test_ai_doc_orchestrator_kage3_v1_2_2.py`    | Test          | Fix Doc Orchestrator behavior (PII non-persistence, etc.)                             |
| `tests/kage_definition_hitl_gate_v1.py`       | Experiment    | HITL gate experiment: “If definition is ambiguous, return to humans”                  |
| `tests/test_definition_hitl_gate_v1.py`       | Test          | Pytest fixture for the HITL gate (including Ruff)                                     |
| `tests/test_kage_orchestrator_diverse_v1.py`  | Test          | Fix invariants via pytest (e.g., PII tool non-execution)                              |
| `tests/test_sample.py`                        | Test          | Minimal test / CI smoke check                                                         |
| `tests/verify_stop_comparator_v1_2.py`        | Tool          | Single-file verifier (hash/py_compile/import/self_check, etc.)                        |
| `docs/`                                       | Docs          | Figures/materials (architecture, flows, etc.)                                         |
| `docs/multi_agent_architecture_overview.webp` | Diagram       | Overall architecture diagram                                                          |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram       | Layered model diagram                                                                 |
| `docs/sentiment_context_flow.png`             | Diagram       | Input → context → action flow diagram                                                 |
| `.github/workflows/python-app.yml`            | Workflow      | CI (lint + pytest, multiple Python versions)                                          |
| `requirements.txt`                            | Dependency    | Python dependencies                                                                   |
| `LICENSE`                                     | License       | Educational / Research use                                                            |
| `README.md`                                   | Documentation | This document                                                                         |

---

## 🧭 Architecture Diagram

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

---

## 🧭 Layered Agent Model

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

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
* Context — Extract premises, constraints, and risk factors (evidence for guardrails)
* Action — Instruct agents and branch based on verified results (STOP / REROUTE / HITL)

---

## ⚙️ Execution Examples

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

CI runs lint / pytest across multiple Python versions via `.github/workflows/python-app.yml`.

---

## 📌 License

See `LICENSE`.

This project is intended for Educational / Research purposes.

```
```

