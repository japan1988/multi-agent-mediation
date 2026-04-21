
# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

> 日本語版: [README.ja.md](README.ja.md)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
[![Open Issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square)](https://github.com/japan1988/multi-agent-mediation/issues)
[![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation?style=flat-square)](./LICENSE)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)

> **If uncertain, stop. If risky, escalate.**  
> Research / educational governance simulations for agentic workflows.

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising agent workflows with **fail-closed** safety, **HITL escalation**, and **audit-ready traceability**.

This repository focuses on governance / mediation / negotiation-style simulations and implementation references for **traceable, reproducible, safety-first orchestration**.

---

## 🎯 Purpose

Maestro Orchestrator is built around three priorities:

- **Fail-closed**  
  If uncertain, unstable, or risky, do not continue silently.

- **HITL escalation**  
  Decisions requiring human judgment are explicitly escalated.

- **Traceability**  
  Decision flows are reproducible and audit-ready through minimal ARL logs.

This repository is best read as a:

- research prototype
- educational reference
- governance / safety simulation bench

It is **not** a production autonomy framework.

---

## ⚠️ Purpose & Disclaimer (Research & Education)

This is a research / educational reference implementation (prototype).

Do **not** use it to execute or facilitate harmful actions, including for example:

- exploitation
- intrusion
- surveillance
- impersonation
- destruction
- data theft

Do **not** use it to violate any applicable terms, policies, laws, or internal rules.

This project focuses on defensive verification such as:

- validating fail-closed + HITL behavior
- checking vocabulary / invariant drift
- reducing log growth via abnormal-only persistence
- improving reproducibility of governance-style simulations

### Risk / Warranty / Liability

- Use at your own risk.
- Verify applicable terms, policies, and laws before use.
- Start in an isolated local environment with no real systems, no real data, and no external side effects.
- The repository is provided **AS IS**, without warranty.
- To the maximum extent permitted by applicable law, the author assumes no liability for damages arising from use of the code, docs, or generated artifacts.

### Codebook disclaimer

The bundled codebook is a **demo / reference artifact**.

- Do not use it as-is in real deployments.
- Build your own codebook based on your requirements, threat model, and applicable policies.
- The codebook is **not encryption** and provides **no confidentiality**.

### Testing & results disclaimer

Smoke tests and stress runs validate only the executed scenarios under specific runtime conditions.  
They do **not** guarantee correctness, security, safety, or fitness for any production purpose.

---

## 🚫 Non-goals

The following are explicitly out of scope:

- **Production-grade autonomous decision-making**
- **Unattended real-world authority**
- **Handling real personal data (PII)** or confidential business data in prompts, test vectors, or logs
- **Compliance / legal advice** or deployment guidance for regulated environments
- **Unsafe fail-open rerouting**
- **Silent continuation under ambiguity**

---

## 🔁 REROUTE safety policy (fail-closed)

REROUTE is allowed **only when all conditions are met**. Otherwise, the system must fall back to `PAUSE_FOR_HITL` or `STOPPED`.

| Risk / Condition | REROUTE | Default action |
|---|---:|---|
| Undefined spec / ambiguous intent | ❌ | `PAUSE_FOR_HITL` |
| Any policy-sensitive category (PII, secrets, high-stakes domains) | ❌ | `STOPPED` or `PAUSE_FOR_HITL` |
| Candidate route has higher tool / data privileges than original | ❌ | `STOPPED` |
| Candidate route cannot enforce same-or-stronger constraints | ❌ | `STOPPED` |
| Safe class task + same-or-lower privileges + same-or-stronger constraints | ✅ | `REROUTE` |
| REROUTE count exceeds limit | ❌ | `PAUSE_FOR_HITL` or `STOPPED` |

**Recommended default:** `max_reroute = 1`

All REROUTE decisions should be logged with a `reason_code` and the selected route identifier.

---

## 🔎 What this repository contains

This repository contains simulation benches and implementation references for:

- negotiation
- mediation
- governance-style workflows
- gating behavior
- audit-oriented orchestration

Typical outputs include:

- reproducible simulator summaries
- minimal ARL traces
- optional incident-indexed artifacts for abnormal runs
- pytest-based contract checks for vocabularies and invariants

---

## 🔗 Quick links

- Japanese README: `README.ja.md`
- Docs index: `docs/README.md`
- Recommended simulator: `mediation_emergency_contract_sim_v5_1_2.py`
- Contract test: `tests/test_v5_1_codebook_consistency.py`
- Stress metrics test: `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
- Pytest ARL hook: `tests/conftest.py`
- Demo codebook: `log_codebook_v5_1_demo_1.json`
- Legacy stable bench: `mediation_emergency_contract_sim_v4_8.py`
- Doc orchestrator reference: `ai_doc_orchestrator_with_mediator_v1_0.py`
- Doc orchestrator test: `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## ⚡ TL;DR

- Fail-closed + HITL gating benches for negotiation / mediation-style workflows
- Reproducibility-first with seeded runs and `pytest`-based contract checks
- Audit-ready traces via minimal ARL logs and optional incident indexing (`INC#...`)
- Reference implementations for mediator / gating / doc orchestration paths
- Validation path centered on `v5.1.2`, with `v4.8` kept as a legacy stable bench

---

## 🚀 Recommended path

If you are new to this repo, the recommended order is:

1. Run `mediation_emergency_contract_sim_v5_1_2.py`
2. Run `tests/test_v5_1_codebook_consistency.py`
3. Run `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
4. Inspect generated logs, codebook, and optional incident artifacts
5. Compare with `mediation_emergency_contract_sim_v4_8.py` if needed
6. Inspect `ai_doc_orchestrator_with_mediator_v1_0.py` as a smaller fixed-order reference

---

## ⚙️ Quickstart

### 1) Run the recommended emergency contract simulator (v5.1.2)

Optional bundle: `docs/mediation_emergency_contract_sim_pkg.zip`

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
2) Run the contract tests
pytest -q tests/test_v5_1_codebook_consistency.py
3) Run the stress metrics tests
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
4) Pytest execution ARL (auto output)
tests/conftest.py automatically emits JSONL-style ARL for pytest execution.

Default output paths:

test_artifacts/pytest_test_arl.jsonl

test_artifacts/pytest_simulation_arl.jsonl

pytest -q
Custom output paths:

TEST_ARL_PATH=out/test_arl.jsonl SIM_ARL_PATH=out/sim_arl.jsonl pytest -q
5) Inspect / pin the demo codebook
log_codebook_v5_1_demo_1.json

This codebook is for compact encoding / decoding of log fields only.
It is not encryption.

6) Optional: run the legacy stable bench (v4.8)
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
7) Optional: run the doc orchestrator mediator reference
python ai_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
8) What to inspect after running
simulator stdout summaries

generated ARL / audit JSONL traces

incident_index.jsonl and INC#... files when abnormal-only persistence is enabled

vocabulary / invariant checks in the contract tests

pytest-side execution ARL (pytest_test_arl.jsonl)

optional simulation-side ARL bridge output (pytest_simulation_arl.jsonl)

🧾 Audit log & data safety
This project produces audit logs for reproducibility and accountability.
Because logs may outlive a session and may be shared for research, treat logs as sensitive artifacts.

Minimum expectations
Do not include personal information (PII) in prompts, test vectors, or logs

Prefer synthetic / dummy data for experiments

Avoid committing runtime logs to the repository

If logs must be stored locally, apply masking, retention limits, and restricted directories

Minimum required fields
run_id

timestamp

layer

decision

reason_code

final_decider

policy_version

Safe logging requirements
MUST NOT persist raw prompts / outputs that may contain PII or secrets

MUST store only sanitized evidence

MUST run a PII / secret scan on candidate log payloads

On detection failure, do not write the log

Runtime logs should remain outside the repository whenever possible

Retention
Define a retention window such as:

7 days

30 days

90 days

Then delete logs automatically.

🧭 High-level repository structure
The current repository is organized around:

.github/workflows

archive

benchmarks

docs

mediation_core

scripts

tests

Representative top-level files include:

README.md

README.ja.md

agents.yaml

agents.yaml.md

ai_alliance_persuasion_simulator.py

ai_doc_orchestrator_kage3_v1_2_2.py

ai_doc_orchestrator_kage3_v1_2_2_1.py

ai_doc_orchestrator_kage3_v1_2_3.py

ai_doc_orchestrator_kage3_v1_2_4.py

ai_doc_orchestrator_kage3_v1_3_5.py

ai_doc_orchestrator_with_mediator_v1_0.py

ai_governance_mediation_sim.py

ai_mediation_all_in_one.py

kage_orchestrator_diverse_v1.py

log_codebook_v5_1_demo_1.json

mediation_emergency_contract_sim_v4_8.py

mediation_emergency_contract_sim_v5_1_2.py

pytest.ini

📌 License
See LICENSE.

Repository license follows the repository’s LICENSE file.
Operationally, this repository is presented as a research / educational project.