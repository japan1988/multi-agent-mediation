# Maestro Orchestrator — Multi-Agent Orchestration Framework

![python](https://img.shields.io/badge/python-3.9_|_3.10_|_3.11-blue)
![ci](https://img.shields.io/badge/CI-passing-success)
![release](https://img.shields.io/badge/release-v1.0.1-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

Maestro Orchestrator is a multi-agent mediation / orchestration simulator focused on **fail-closed guardrails**, **audit logs**, and **HITL escalation**.

This repository is designed for experimentation: it helps you model how an “orchestrator” can route tasks, validate outputs, and **stop or escalate** when safety or consistency is unclear.

---

## Purpose

- Provide a minimal but concrete orchestration pattern:
  - **RUN** when the request is safe and unambiguous
  - **STOP** when it is unsafe
  - **HITL** (Human-in-the-Loop) when it is ambiguous or requires an explicit human decision
- Keep outcomes reproducible via **JSONL audit logs**
- Offer testable entrypoints so CI can verify “fail-closed” behavior

---

## Structure (high-level)

| Layer | Role | Responsibility |
|------:|------|----------------|
| Agent Layer | Execution | task processing (proposal / generation / verification) |
| Supervisor Layer | Control | routing, consistency checks, STOP, HITL |
| Audit Layer | Evidence | append-only JSONL logs (reproducibility) |

---

## Architecture (minimal orchestrator)

```mermaid
flowchart TD
    U["User Prompt"] --> S["Supervisor / Orchestrator"]
    S -->|dispatch| A["Agent Layer<br/>proposal / generation / verification"]
    A --> V["Output + Plan validation<br/>(consistency + safety gates)"]
    V --> D{Decision}

    D -->|RUN|  R["RUN (exit 0)"]
    D -->|STOP| X["STOP (exit 1)"]
    D -->|HITL| H["HITL (exit 2)"]

    R --> L["JSONL Audit Log"]
    X --> L
    H --> L
````

**Key invariant:** ambiguous/unsafe cases do not “silently proceed”; they STOP or HITL (**fail-closed**).

---

## Repository Structure (tree)

```text
multi-agent-mediation/
├─ .github/
│  └─ workflows/
│     └─ python-app.yml
├─ docs/
│  └─ sentiment_context_flow.png
├─ mediation_core/
│  └─ ... (shared orchestration / policy logic)
├─ tests/
│  └─ test_min_entrypoint_v1.py
├─ agents.yaml
├─ ai_mediation_all_in_one.py
├─ kage_orchestrator_diverse_v1.py
├─ run_orchestrator_min.py
├─ log_format.md
├─ requirements.txt
├─ LICENSE
└─ README.md
```

---

## Context Flow (existing image path)

![Context Flow](docs/sentiment_context_flow.png)

Flow (description updated):

1. **Perception** — decompose input into executable units (tasking)
2. **Context** — extract constraints / assumptions / risk factors (guardrail evidence)
3. **Action** — dispatch to agents, validate outputs, then branch (**RUN / STOP / HITL**)

Safety is prioritized at every stage: unsafe or ambiguous cases are stopped or escalated.

---

## Quickstart (minimal)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python run_orchestrator_min.py
```

---

## License

Apache-2.0
