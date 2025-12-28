# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

<p align="center">
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
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <img src="https://img.shields.io/badge/status-research--prototype-brightgreen.svg?style=flat-square" alt="Status">
</p>

## 🎯 Purpose

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising multiple agents (or multiple methods) with **fail-closed** safety.

- **STOP**: Halt execution on errors / hazards / undefined specs
- **REROUTE**: Re-route only when explicitly safe (avoid fail-open reroute)
- **HITL**: Escalate to humans for ambiguous or high-stakes decisions

## 🧭 One-page design map (implementation-aligned)

**Decision flow map:** `mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
Designed to be **fail-closed**: if risk/ambiguity is detected, it falls back to `PAUSE_FOR_HITL` or `STOPPED` and logs **why**.

- **Meaning**: task/intent category validation (undefined/ambiguous -> HITL)
- **Consistency**: schema/contract checks (mismatch -> HITL)
- **RFL (Relativity Filter)**: unstable/subjective boundaries -> `PAUSE_FOR_HITL` (overrideable, non-sealed)
- **Ethics / ACC**: non-overridable sealing gates (PII/tool side-effects, policy violations)
- **DISPATCH**: run only when cleared

## 🧭 Architecture Diagram

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

## 🧭 Layered Agent Model

| Layer | Role | What it does |
| --- | --- | --- |
| Interface Layer | External input layer | Input contract (schema) / validation / log submission |
| Agent Layer | Execution layer | Task processing (proposal / generation / verification) |
| Supervisor Layer | Supervisory layer | Routing, consistency checks, STOP / HITL decisions |

## 🔬 Context Flow

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception** — Decompose input into executable elements (tasking)
- **Context** — Extract assumptions/constraints/risk factors (guard rationale)
- **Action** — Instruct agents, verify results, branch (STOP / REROUTE / HITL)

## 🔒 Safety & External Side Effects (default deny)

External side effects include: network, filesystem, command execution, messaging, payments, and **PII sources**.

**Default policy is deny-by-default.** Unknown tools are **DENY**.

## 🧾 Audit log (research artifact)

Audit logs are produced for reproducibility and accountability. Recommended minimum fields:

- `run_id`, `session_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`

Avoid storing raw PII; log hashes / reason codes instead.

## ⚙️ Execution Examples

> Note: Modules that evoke “persuasion / reeducation” are intended for **safety-evaluation scenarios only** and should be **disabled by default** unless explicitly opted-in.

```bash
# Core (routing / gating / branching)
python ai_mediation_all_in_one.py

# Orchestrator fault-injection / capability guard demo
python kage_orchestrator_diverse_v1.py

# Doc Orchestrator (Meaning/Consistency/Ethics + PII non-persistence)
python ai_doc_orchestrator_kage3_v1_2_2.py

# Policy application behavior check
python ai_governance_mediation_sim.py
````

## 🧪 Tests

```bash
pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
```

CI runs lint/pytest via `.github/workflows/python-app.yml`.

## 📌 License

See `LICENSE`.
Repository license: **Apache-2.0** (policy intent: Educational / Research).

```
::contentReference[oaicite:0]{index=0}
```



