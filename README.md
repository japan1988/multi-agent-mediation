# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework
> 日本語版: [README.ja.md](README.ja.md)

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
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

## 🎯 Purpose

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising multiple agents (or multiple methods) with **fail-closed** safety.

- **STOP**: Halt execution on errors / hazards / undefined specs
- **REROUTE**: Re-route only when explicitly safe (avoid fail-open reroute)
- **HITL**: Escalate to humans for ambiguous or high-stakes decisions

### Positioning (safety-first)
Maestro Orchestrator prioritizes **preventing unsafe or undefined execution** over maximizing autonomous task completion.
When risk or ambiguity is detected, it **fails closed** and escalates to `PAUSE_FOR_HITL` or `STOPPED`, with audit logs explaining **why**.

**Trade-off:** This design may *over-stop by default*; safety and traceability are prioritized over throughput.

## 🚫 Non-goals (IMPORTANT)

This repository is a **research prototype**. The following are explicitly **out of scope**:

- **Production-grade autonomous decision-making** (no unattended real-world authority)
- **Persuasion / reeducation optimization for real users** (safety-evaluation only; must be opt-in and disabled by default)
- **Handling real personal data (PII)** or confidential business data in prompts, test vectors, or logs
- **Compliance/legal advice** or deployment guidance for regulated environments (medical/legal/finance)

## 🔁 REROUTE safety policy (fail-closed)

REROUTE is **allowed only when all conditions are met**. Otherwise, the system must fall back to `PAUSE_FOR_HITL` or `STOPPED`.

| Risk / Condition | REROUTE | Default action |
|---|---:|---|
| Undefined spec / ambiguous intent | ❌ | `PAUSE_FOR_HITL` |
| Any policy-sensitive category (PII, secrets, high-stakes domains) | ❌ | `STOPPED` or `PAUSE_FOR_HITL` |
| Candidate route has **higher** tool/data privileges than original | ❌ | `STOPPED` |
| Candidate route cannot enforce **same-or-stronger** constraints | ❌ | `STOPPED` |
| Safe class task + same-or-lower privileges + same-or-stronger constraints | ✅ | `REROUTE` |
| REROUTE count exceeds limit | ❌ | `PAUSE_FOR_HITL` or `STOPPED` |

**Hard limits (recommended defaults):**
- `max_reroute = 1` (exceed → `PAUSE_FOR_HITL` or `STOPPED`)
- REROUTE must be logged with `reason_code` and the selected route identifier.

## 🧭 Diagrams

### 1) System overview
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 2) Orchestrator one-page design map
**Decision flow map (implementation-aligned):**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
Designed to be **fail-closed**: if risk/ambiguity is detected, it falls back to `PAUSE_FOR_HITL` or `STOPPED` and logs **why**.

<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

If the image is not visible (or too small), open it directly:  
- `docs/orchestrator_onepage_design_map.png`

RFL is non-sealing by design: it escalates to `PAUSE_FOR_HITL` (never `sealed=true`).

### 3) Context flow
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception** — Decompose input into executable elements (tasking)
- **Context** — Extract assumptions/constraints/risk factors (guard rationale)
- **Action** — Instruct agents, verify results, branch (STOP / REROUTE / HITL)

## 🧾 Audit log & data safety (IMPORTANT)

This project produces **audit logs** for reproducibility and accountability.
Because logs may outlive a session and may be shared for research, **treat logs as sensitive artifacts**.

- **Do not include personal information (PII)** (emails, phone numbers, addresses, real names, account IDs, etc.) in prompts, test vectors, or logs.
- Prefer **synthetic / dummy data** for experiments.
- Avoid committing runtime logs to the repository. If you must store logs locally, apply **masking**, **retention limits**, and **restricted directories**.

### 🔒 Audit log requirements (MUST)

To keep logs safe and shareable for research:

- **MUST NOT** persist raw prompts/outputs that may contain PII or secrets.
- **MUST** store only *sanitized* evidence (redacted / hashed / category-level signals).
- **MUST** redact PII-like patterns **fail-closed** (on detection failure, do not write logs).
- **MUST** ensure redaction applies to **both values and dictionary keys** (no email-like tokens such as `@` may remain in persisted logs).
- **MUST** avoid committing runtime logs to the repository (use local restricted directories).

**Minimum required fields (implementation-aligned, MUST):**
- `run_id`, `ts`, `layer`, `decision`, `reason_code`, `sealed`, `overrideable`, `final_decider`

**Optional fields (SHOULD, if you need them):**
- `session_id`, `policy_version`, `artifact_id`, `route_id` (keep them sanitized / non-PII)

**Retention (SHOULD):**
- Define a retention window (e.g., 7/30/90 days) and delete logs automatically.

## 🧑‍⚖️ HITL semantics (post-HITL is defined)

HITL is used for ambiguous or high-stakes cases. Responsibility must be traceable in the audit log.

- When HITL is triggered, the orchestrator emits `HITL_REQUESTED` (**SYSTEM**), typically with:
  - `decision=PAUSE_FOR_HITL`, `sealed=false`, `overrideable=true`
- User choice is recorded as `HITL_DECIDED` (**USER**), with:
  - `sealed=false`, `overrideable=false`, `final_decider=USER`
  - `CONTINUE` → decision propagates to `RUN`
  - `STOP` → decision becomes `STOPPED`

**Note:** Only Ethics/ACC can seal (`sealed=true` implies `final_decider=SYSTEM`).

## ⚙️ Execution Examples

> Note: Modules that evoke “persuasion / reeducation” are intended for **safety-evaluation scenarios only** and should be **disabled by default** unless explicitly opted-in.

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_governance_mediation_sim.py

# Doc orchestrator (KAGE3-style)
python ai_doc_orchestrator_kage3_v1_2_4.py
# (older versions may exist, but v1.2.4 is the current reference for post-HITL semantics)
````

## 🧪 Tests

```bash
pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py

# Dedicated regression test (version-pinned) for v1.2.4
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
```

CI runs lint/pytest via `.github/workflows/python-app.yml`.

## 📌 License

See LICENSE.
Repository license: Apache-2.0 (policy intent: Educational / Research).

```

必要なら、この全文を「いまの README.md との差分（どこを置換するか）」の形に切り出して、コピペ量を減らした版も出せます。
```

