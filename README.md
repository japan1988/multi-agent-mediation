# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

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
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <img src="https://img.shields.io/badge/status-research--prototype-brightgreen.svg?style=flat-square" alt="Status">
</p>

A **research-oriented orchestration framework** for supervising multiple agents (or multiple methods) with **fail-closed guardrails** and **HITL escalation**.

- **STOP**: halt on hazards / errors / non-decidable ambiguity
- **HITL**: return uncertain or high-stakes decisions to humans
- **Audit & Replay**: log decisions + reproduce runs

> Policy intent: Educational / Research. No autonomous real-world actions by default.

---

## 🎯 What this repo focuses on

This project is **not “negotiation itself”**. It is supervision and control:

- **Routing**: decomposition and assignment (who does what)
- **Guardrails**: forbid overreach and external side effects (fail-closed)
- **HITL**: explicit escalation state (`PAUSE_FOR_HITL`)
- **Audit**: log what stopped and why (accountability)
- **Replay**: rerun under same seed/config and detect deltas

---

## 🔒 Safety model 

- If forbidden intent, overreach, low confidence, or ambiguous sensitive intent is detected in **input/output/plan**, the system **does not auto-execute**.  
  → It falls back to **STOP** or **HITL** (`PAUSE_FOR_HITL`).
- “Fail-open reroute” is avoided in risky situations.

### External side effects (default: DENY)
Examples: network, filesystem, command execution, messaging/email/DM, payments, account operations, **PII sources** (contacts/mailbox/CRM).  
Unknown tools are **DENY**.

> Note: Files whose names evoke “persuasion / reeducation” are intended for **safety-evaluation scenarios only** (attack simulation / test-case generation). They should be treated as non-default / opt-in experiments.

---

## 🧭 Diagrams 
### 1) System overview
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="820" alt="System Overview">
</p>

### 2) Orchestrator one-page design map 
Decision flow map: **Meaning → Consistency → HITL → Ethics → ACC → DISPATCH**, designed to be **fail-closed**.
<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="980" alt="Orchestrator One-page Design Map">
</p>

### 3) Context flow
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="820" alt="Context Flow Diagram">
</p>

---

## 🗂️ Repository structure

| Path | Description |
| --- | --- |
| `mediation_core/` | shared core logic / models |
| `agents.yaml` | agent definitions / configuration |
| `docs/` | figures (architecture, flows, maps) |
| `tests/` | pytest suite |
| `.github/workflows/python-app.yml` | CI (ruff + pytest, multi Python) |

**Key scripts (examples):**
- `ai_mediation_all_in_one.py` — entry point (routing / checks / branching)
- `kage_orchestrator_diverse_v1.py` — fault-injection safety demo (tool execution remains blocked)
- `ai_doc_orchestrator_kage3_v1_2_2.py` — doc orchestrator (Meaning/Consistency/Ethics + PII non-persistence)
- `ai_governance_mediation_sim.py` — policy application behavior check

---

## ⚡ Quick start

```bash
pip install -r requirements.txt
pytest -q
````

Run examples:

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_doc_orchestrator_kage3_v1_2_2.py
python ai_governance_mediation_sim.py
```

---

## 🧪 Tests

```bash
# all tests
pytest -q

# HITL gate test
pytest -q tests/test_definition_hitl_gate_v1.py

# orchestrator diverse test
pytest -q tests/test_kage_orchestrator_diverse_v1.py

# doc orchestrator test
pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
```

CI runs via `.github/workflows/python-app.yml`.

---

## 📌 License

Apache-2.0 (see `LICENSE`).
Policy intent: Educational / Research.

```


