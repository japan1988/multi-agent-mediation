# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)
> Japanese version: [README.ja.md](README.ja.md)

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

---

> **Purpose / 目的（Research & Education）**  
> **JP:** 本リポジトリは研究・教育目的の参考実装（プロトタイプ）です。**侵入・監視・なりすまし・破壊・窃取など他者に害を与える行為**、またはそれらを容易にする目的での利用、ならびに**各サービス／実行環境の利用規約・ポリシー・法令・社内規程に反する利用**を禁止します（悪用厳禁）。本プロジェクトは **教育・研究および防御的検証（例：ログ肥大の緩和、fail-closed + HITL の挙動検証）** を目的としており、**悪用手口の公開や犯罪助長を目的としません**。  
> 利用者は自己責任で、所属組織・サービス提供者・実行環境の **規約／ポリシー** を確認し、**外部ネットワークや実システム／実データに接続しない隔離環境でローカルのスモークテストから開始**してください（実システム／実データ／外部ネットワークに対するテストは禁止）。本成果物は **無保証（現状有姿 / “AS IS”）** で提供され、作者は **いかなる損害についても責任を負いません**。  
> なお、**Codebook（辞書）はデモ／参考例**です。**そのまま使用せず**、利用者が自身の要件・脅威モデル・規約／ポリシーに合わせて **必ず自作**してください。  
> **EN:** This is a research/educational reference implementation (prototype). **Do not use it to execute or facilitate harmful actions** (e.g., exploitation, intrusion, surveillance, impersonation, destruction, data theft) or to violate any applicable **terms/policies, laws, or internal rules**. This project focuses on **education/research and defensive verification** (e.g., log growth mitigation and validating fail-closed + HITL behavior) and is **not intended to publish exploitation tactics** or facilitate wrongdoing.  
> Use at your own risk: verify relevant **terms/policies** and start with **local smoke tests in an isolated environment** (no external networks, no real systems/data). Contents are provided **“AS IS”, without warranty**, and the author assumes **no liability for any damages**.  
> The included **codebook is a demo/reference artifact—do not use it as-is; create your own** based on your requirements, threat model, and applicable policies/terms.

---

## Overview

Maestro Orchestrator is a **research / educational** orchestration framework that prioritizes:

- **Fail-closed**  
  If uncertain, unstable, or risky → do not continue silently.

- **HITL (Human-in-the-Loop)**  
  Decisions that require human judgment are explicitly escalated.

- **Traceability**  
  Decision flows are audit-ready and reproducible via minimal ARL logs.

This repository contains **implementation references** (doc orchestrators) and **simulation benches**
for negotiation, mediation, governance-style workflows, and gating behavior.

---

## Quickstart (recommended path)

Start with one script, confirm behavior and logs, then expand.

### 1) Run the latest emergency contract simulator (v4.8)

```bash
python mediation_emergency_contract_sim_v4_8.py
````

### 2) Run the pinned smoke test (v4.8)

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 3) Optional: inspect evidence bundle (generated artifact)

* `docs/artifacts/v4_8_artifacts_bundle.zip`

> Note: evidence bundles (zip) are **generated artifacts** produced by tests/runs.
> The canonical source of truth is the generator scripts + tests.

---

## Architecture (high level)

Audit-ready and fail-closed control flow:

agents
→ mediator (risk / pattern / fact)
→ evidence verification
→ HITL (pause / reset / ban)
→ audit logs (ARL)

![Architecture](docs/architecture_unknown_progress.png)

### If an image does not render

Confirm that:

* the file exists under `docs/`
* the filename matches exactly (case-sensitive)
* the link points to the same branch you are viewing

---

## Architecture (code-aligned diagrams)

The following diagrams are **aligned with the current code vocabulary**.
They separate **state transitions** from **gate order** to preserve auditability and avoid ambiguity.

> Documentation-only. No logic changes.

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing where execution **pauses (HITL)**
or **stops permanently (SEALED)**.

<p align="center">
  <img src="docs/architecture_state_machine_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Primary execution path**

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

**Notes**

* `PAUSE_FOR_HITL_*` represents an explicit **Human-in-the-Loop** decision point (user approval or admin approval).
* `STOPPED (SEALED)` is reached on:

  * invalid or fabricated evidence
  * authorization expiry
  * draft lint failure
* **SEALED stops are fail-closed and non-overrideable by design.**

### 2) Gate Pipeline (code-aligned)

Ordered evaluation gates, **independent from lifecycle state transitions**.

<p align="center">
  <img src="docs/architecture_gate_pipeline_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

* This diagram represents **gate order**, not state transitions.
* `PAUSE` indicates **HITL required** (human decision pending).
* `STOPPED (SEALED)` indicates a **non-recoverable safety stop**.

**Design intent**

* **State Machine** answers: “Where does execution pause or terminate?”
* **Gate Pipeline** answers: “In what order are decisions evaluated?”

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

---

## What’s new

This project is under active development.

* Latest updates: check the **commit history** (GitHub “Commits”) and release notes (if tagged).
* Key additions/changes are documented as needed in `docs/` (and/or `CHANGELOG.md` if present).

> Design note: the README stays minimal on purpose to keep the “recommended path” clear.

---

## V1 → V4: What actually changed

`mediation_emergency_contract_sim_v1.py` demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

**Added in v4**

* **Evidence gate**
  Basic verification of evidence bundles. Invalid/irrelevant/fabricated evidence triggers fail-closed stops.

* **Draft lint gate**
  Enforces draft-only semantics and scope boundaries before admin finalization.

* **Trust system (score + streak + cooldown)**
  Trust increases on successful HITL outcomes and decreases on failures. Cooldown prevents unsafe automation after errors. All transitions are logged in ARL.

* **AUTH HITL auto-skip (safe friction reduction)**
  When trust threshold + approval streak + valid grant are satisfied, AUTH HITL can be skipped for the same scenario/location only, while recording reasons in ARL.

---

## Execution examples

**Doc orchestrator (reference implementation)**

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

**Emergency contract (v4.8)**

```bash
python mediation_emergency_contract_sim_v4_8.py
```

**Emergency contract (v4.1)**

```bash
python mediation_emergency_contract_sim_v4_1.py
```

**Emergency contract stress (v4.4)**

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## Project intent / non-goals

### Intent

* Reproducible safety and governance simulations
* Explicit HITL semantics (pause/reset/ban)
* Audit-ready decision traces (minimal ARL)

### Non-goals

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## Data & safety notes

* Use **synthetic/dummy data** only.
* Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible.
* Treat generated bundles (zip) as **reviewable evidence**, not canonical source.

---

## License

Apache License 2.0 (see `LICENSE`)
必要なら次は、これと**完全に対応する README.ja.md（全文）**も同じ構造で整形して出せます。
```

