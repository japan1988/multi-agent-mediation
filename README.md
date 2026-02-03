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

## Overview
Maestro Orchestrator is a **research / educational** orchestration framework that prioritizes:

- **Fail-closed**: if uncertain, unstable, or risky → do not continue silently
- **HITL (Human-in-the-loop)**: escalate decisions that require human judgment
- **Traceability**: decision flows are meant to be auditable and reproducible

This repo contains **implementation references** (doc orchestrator) and **simulators** for negotiation/mediation and gating behavior.

---

## Architecture
High-level control flow for **audit-ready** and **fail-closed** orchestration:

agents → mediator (risk/pattern/fact) → evidence verification → HITL (reset/ban) → audit logs.

![Architecture](docs/architecture_unknown_progress.png)

> If the image does not render, confirm that `docs/architecture_unknown_progress.png` exists on the same branch as this README and that the filename matches exactly (case-sensitive).

---

## What’s new (2026-01-21)
Recent additions introduced new entry points and updated core behavior:

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  A simulator focused on handling **unknown progress** scenarios with HITL/RESET semantics.
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  A simulator aligned to **KAGE v1.7-IEP** behavior for **RFL relcode branching**.
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  Doc orchestrator implementation reference updated.

(See commit history for exact PRs and messages.)

---

## What’s new (2026-02-03)
Latest additions introduced an event-driven governance-style workflow:

- **New**: `mediation_emergency_contract_sim_v1.py`  
  Event-driven emergency workflow simulator (fail-closed + HITL + audit-ready).  
  Implements a 2-step human approval pipeline: USER auth → AI generates draft → ADMIN finalization → effective contract.  
  Produces minimal ARL (JSONL) and seals/stops on expired auth or invalid events.

- **New**: `copilot_mediation_min.py`  
  Copilot Python SDK minimal example (tool call + local HITL + fail-closed routing + ARL minimal log).

- **Updated**: `.github/workflows/python-app.yml`  
  CI workflow hardened (pytest + ruff + yamllint) with concurrency and artifact upload.

---

## Recommended entry points (pick one)

### 1) Doc orchestrator (implementation reference)
Best starting point if you want to understand a “KAGE3-style” doc orchestrator pipeline.

```powershell
python ai_doc_orchestrator_kage3_v1_2_4.py
2) KAGE v1.7-IEP RFL relcode branching simulator
Use this if you want to focus on RFL → HITL branching semantics.

powershell
python ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py
3) HITL/RESET simulator with “unknown progress”
Use this if you want to validate behavior when agents claim progress that cannot be verified.

powershell
# NOTE: if the file exists without ".py", run it as-is or rename to .py for consistency.
python ai_mediation_hitl_reset_full_with_unknown_progress.py
4) Emergency contract workflow simulator (event-driven + 2-step HITL)
Use this if you want to validate a governance-style flow where AI drafts only and humans authorize/finalize.

powershell
python mediation_emergency_contract_sim_v1.py
Highlights

USER auth (field operator) → draft generation → ADMIN finalize

Fail-closed: invalid/expired events → stop (+ sealed when applicable)

Traceability: minimal ARL JSONL output for audits

Tip: If you’re new, start with the doc orchestrator; if you want governance/fail-closed workflows, try mediation_emergency_contract_sim_v1.py.

Repository layout (quick file map)
This repo is script-heavy. Use this map to find the right entry point fast.

Core / implementation references
mediation_core/
Core dataclasses / shared models used by simulators and orchestrators.

ai_doc_orchestrator_kage3_v1_2_4.py
KAGE3-style doc orchestrator reference (audit-ready + post-HITL semantics).

ai_doc_orchestrator_kage3_v1_3_5.py
Newer doc orchestrator variant; keep v1_2_4 as a stable reference if you prefer minimal surface.

HITL / fail-closed simulators (bench-style)
ai_mediation_hitl_reset_full_with_unknown_progress (or .py)
Unknown-progress + HITL/RESET simulator (claims of progress that cannot be verified).

ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py
KAGE v1.7-IEP aligned RFL relcode branching (RFL is non-sealing → HITL).

Governance / event-driven workflow
mediation_emergency_contract_sim_v1.py
Event-driven emergency workflow: USER auth → AI drafts → ADMIN finalize → effective.
Fail-closed on invalid/expired events; outputs minimal ARL (JSONL).

Social / alliance dynamics simulator
ai_alliance_persuasion_simulator.py
Alliance/persuasion/sealing/cooldown/reintegration simulator.
Exposes CSV_PATH / TXT_PATH for tests (monkeypatch-friendly).

Copilot SDK minimal
copilot_mediation_min.py
Copilot Python SDK minimal working example + local HITL + ARL minimal log.

Bench runners / scripts / tests / CI
scripts/
Helper CLIs / runners.

benchmarks/
Scenario runners (optional).

tests/ and test_*.py
Maintained test surface for CI.

.github/workflows/python-app.yml
CI workflow (pytest + ruff + yamllint).

Quickstart
powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
Environment Setup
Prerequisites
Python 3.10+ (recommended: 3.11)

Latest pip

1) Create and activate a virtual environment (Windows / PowerShell)
powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
If PowerShell blocks activation:

powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
2) Install dependencies
Runtime only:

powershell
pip install -r requirements.txt
Development / tests:

powershell
pip install -r requirements-dev.txt
3) Run tests
powershell
python -m pytest -q
Optional: lock dependencies (pip-tools)
powershell
pip install pip-tools
pip-compile requirements.txt -o requirements.lock.txt
pip-compile requirements-dev.txt -o requirements-dev.lock.txt
pip-sync requirements-dev.lock.txt
Notes
matplotlib: use plt.savefig(...) in headless environments (CI, servers). Avoid plt.show() unless a GUI backend is available.

Linux / macOS (equivalent):

bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -m pytest -q
Benchmarks (optional)
If you want to run benchmark-style scripts (profiles / scenarios), these are available:

bash
python run_benchmark_kage3_v1_3_5.py
python run_benchmark_profiles_v1_0.py
Project intent / non-goals
This repository is intentionally oriented toward research and reproducible simulation.

Non-goals
Production-grade autonomous agent deployment

Unbounded “self-directed” orchestration without HITL

Safety claims beyond what is explicitly tested in this repo

Contributing
Issues and PRs are welcome, especially for:

Additional benchmark cases

Reproducibility improvements

Stronger tests for fail-closed / HITL routing invariants

Documentation clarifications (JP/EN parity)

License
Apache-2.0. See LICENSE.
