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
  <img src="https://img.shields.io/badge/status-stable-brightgreen.svg?style=flat-square" alt="Status">
  <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/v/release/japan1988/multi-agent-mediation?style=flat-square" alt="Release">
</p>

---

## 🎯 Purpose

**Maestro Orchestrator** is an experimental framework to orchestrate multiple agents (or multiple methods) with:

- **Fail-closed guardrails** (block unsafe / ambiguous / policy-violating execution)
- **Audit logs** (what was decided, why, and when)
- **HITL escalation** (route uncertain/high-risk decisions back to a human)
- **Replayability** (run under consistent conditions and compare outcomes)

The focus is not “negotiation itself,” but **safe orchestration**: stopping, rerouting, or escalating decisions when the system is uncertain.

---

## ✅ Key Capabilities

- **Routing**: assign tasks to agents / methods
- **Guardrails (fail-closed)**: block dangerous outputs, privilege escalation, or external side effects
- **Audit & traceability**: reason codes + reproducible logs
- **HITL (Human-in-the-Loop)**: pause/stop and require explicit human decision
- **Determinism-first testing**: the same input should produce the same decision + reason code

---

## 🧠 Concept Overview

| Component | Function | Description |
|---|---|---|
| 🧩 Orchestration Layer | Control plane | task decomposition, routing, retries, reassignment |
| 🛡️ Safety & Policy Layer | Guardrails | detect unsafe / ambiguous cases and **fail-closed** |
| 🧾 Audit & Replay Layer | Evidence | audit logs, diff/replay, reporting |
| 👤 HITL Escalation | Human override | route uncertain/high-risk decisions to humans |

> The goal is not simply to “run agents,” but to **reliably stop** unsafe or uncertain execution.

---

## 🗂️ Repository Structure

> All `.py` modules are intended to be runnable/inspectable as independent experiments.  
> `agents.yaml` is the shared configuration backbone for agent parameters.

| Path | Type | Description |
|---|---|---|
| `.github/workflows/python-app.yml` | CI | GitHub Actions (tests / structure checks) |
| `docs/` | Docs | diagrams and documentation assets |
| `mediation_core/` | Core | shared orchestration / policy logic |
| `tests/` | Tests | pytest coverage for reproducible safety checks |
| `agents.yaml` | Config | agent definitions / parameters |
| `kage_orchestrator_diverse_v1.py` | Orchestrator | main orchestrator experiment (diverse routing / safety checks) |
| `ai_mediation_all_in_one.py` | Orchestrator | integrated orchestration experiment (routing / checks / branching) |
| `ai_governance_mediation_sim.py` | Simulator | governance / policy application behavior |
| `ai_alliance_persuasion_simulator.py` | Simulator | multi-agent interaction / persuasion loop experiments |
| `log_format.md` | Spec | logging/audit format notes |

### HITL Gate (v1) — newly added

> IMPORTANT: Please confirm the **real file paths** below and adjust these two rows if needed.

| Path | Type | Description |
|---|---|---|
| `mediation_core/kage_definition_hitl_gate_v1.py` | Policy | HITL gate decisions + reason codes (fail-closed) |
| `tests/test_definition_hitl_gate_v1.py` | Tests | pytest vectors verifying expected HITL decisions |

---

## 🧭 Architecture Diagram (unchanged)

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### High-level flow

`Human Input → verify_info → supervisor → agents → logger`

- `verify_info`: input validation (schema, assumptions, red flags)
- `supervisor`: routing / retry / STOP / HITL decisions
- `logger`: audit logs (decision + reason + reproducibility metadata)

---

## 🌐 Layered Agent Model (unchanged)

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| Layer | Role | What it does |
|---|---|---|
| Interface Layer | Input | contract/schema validation, logging |
| Agent Layer | Execution | task processing (proposal/generation/verification) |
| Supervisor Layer | Control | routing, consistency checks, STOP, HITL |

---

## 🔬 Context Flow (unchanged image path)

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

### Flow (description updated)

1. **Perception** — decompose input into executable units (tasking)  
2. **Context** — extract constraints/assumptions/risk factors (guardrail evidence)  
3. **Action** — dispatch to agents, validate outputs, then branch (RUN / STOP / HITL)  

> Safety is prioritized at every stage: unsafe or ambiguous cases are stopped or escalated.

---

## ⚙️ Quickstart

### 1) Install dependencies
```bash
python -m pip install -r requirements.txt
````

### 2) Run tests

```bash
pytest -q
```

### 3) Run an orchestrator experiment (examples)

Pick one of the orchestrator entry scripts:

```bash
python kage_orchestrator_diverse_v1.py
# or
python ai_mediation_all_in_one.py
```

---

## 🧪 Testing

* CI should pass via GitHub Actions.
* Locally:

```bash
pytest -q
```

---

## 📜 License

This repository is intended for Educational / Research use. See `LICENSE` for details.

```

--- 



