# Maestro Orchestrator — Multi-Agent Orchestration Framework

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)](#)
[![CI Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Release](https://img.shields.io/github/v/release/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

---

Maestro Orchestrator is a multi-agent mediation / orchestration simulator focused on **fail-closed guardrails**, **audit logs**, and **HITL escalation**.

This repository is designed for experimentation: it helps you model how an “orchestrator” can route tasks, validate outputs, and stop or escalate when safety or consistency is unclear.

---

## 🎯 Purpose

- Provide a minimal but concrete orchestration pattern:
  - **RUN** when the request is safe and unambiguous
  - **STOP** when it is unsafe
  - **HITL** (Human-in-the-Loop) when it is ambiguous or requires an explicit human decision
- Keep outcomes reproducible via **JSONL audit logs**
- Offer testable entrypoints so CI can verify “fail-closed” behavior

---

## 🧱 Structure (high-level)

| Layer | Role | Responsibility |
|---|---|---|
| Agent Layer | Execution | task processing (proposal/generation/verification) |
| Supervisor Layer | Control | routing, consistency checks, STOP, HITL |

---

## 🧭 Architecture (minimal orchestrator)

```mermaid
flowchart TD
  U[User Prompt] --> S[Supervisor / Orchestrator]
  S -->|dispatch| A[Agent Layer\n(proposal/generation/verification)]
  A --> V[Output/Plan Validation\n(consistency + safety gates)]
  V --> D{Decision}
  D -->|RUN| R[RUN\n(exit 0)]
  D -->|STOP| X[STOP\n(exit 1)]
  D -->|HITL| H[HITL\n(exit 2)]
  R --> L[(JSONL Audit Log)]
  X --> L
  H --> L
````

**Key invariant:** ambiguous/unsafe cases do not “silently proceed”; they **STOP** or **HITL** (fail-closed).

---

## 🗂️ Repository Structure (tree)

```text
multi-agent-mediation/
├─ .github/
│  └─ workflows/
│     └─ python-app.yml
├─ docs/
│  └─ sentiment_context_flow.png
├─ mediation_core/
│  └─ ... (shared orchestration/policy logic)
├─ tests/
│  └─ test_min_entrypoint_v1.py
├─ agents.yaml
├─ ai_mediation_all_in_one.py
├─ kage_orchestrator_diverse_v1.py
├─ log_format.md
├─ requirements.txt
├─ run_orchestrator_min.py
├─ LICENSE
└─ README.md
```

---

## 🔬 Context Flow (unchanged image path)

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

### Flow (description updated)

1. **Perception** — decompose input into executable units (tasking)
2. **Context** — extract constraints / assumptions / risk factors (guardrail evidence)
3. **Action** — dispatch to agents, validate outputs, then branch (RUN / STOP / HITL)

> Safety is prioritized at every stage: unsafe or ambiguous cases are stopped or escalated.

---

## ⚙️ Quickstart

### 1) Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2) Run tests

```bash
pytest -q
```

### 3) Run the minimal orchestrator entrypoint (recommended)

This command always writes a JSONL log file.

```bash
python run_orchestrator_min.py --prompt "hello" --run-id DEMO
```

Log output (default):

* `logs/orchestrator_min.jsonl`

### 4) Run orchestrator experiments (examples)

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

## 🧪 Minimal pytest (README-aligned)

Create:

* `tests/test_min_entrypoint_v1.py`

(See repository `tests/`.)

---

## 🧾 .gitignore (append)

If you do not want runtime logs in git, append:

```gitignore
# runtime logs
logs/
```

---

## 🛡️ Safety scope (important)

This repository provides an **experimental, fail-closed orchestration pattern** (RUN / STOP / HITL) and audit logging.

It does **not** guarantee safety for real-world deployment. You are responsible for validation, threat modeling, and operational controls (rate limits, sandboxing, tool permissioning, red-teaming, monitoring, etc.).

---

## 📜 License

Licensed under the **Apache License 2.0**. See `LICENSE` for details.
Safety scope: this repository demonstrates fail-closed behavior in experiments; it does not provide safety guarantees for real-world deployments.

```

