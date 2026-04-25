

![python](https://img.shields.io/badge/python-3.9_|_3.10_|_3.11-blue)
![ci](https://img.shields.io/badge/CI-passing-success)
![release](https://img.shields.io/badge/release-v1.0.1-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

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
  <img src="https://img.shields.io/badge/code%20style-Ruff%20%2F%20Black-000000.svg?style=flat-square" alt="Code Style">
  <img src="https://img.shields.io/badge/status-research--prototype-brightgreen.svg?style=flat-square" alt="Status">
  <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/v/release/japan1988/multi-agent-mediation?style=flat-square" alt="Latest Release">
</p>

---


## 🎯 Purpose / 目的


This repository is designed for experimentation: it helps you model how an “orchestrator” can route tasks, validate outputs, and **stop or escalate** when safety or consistency is unclear.

本リポジトリは、複数エージェント（または複数手法）を統括し、**誤り・危険・不確実**を検知した場合に **停止（STOP）／分岐（REROUTE）／人間へ差し戻し（HITL）** を行うための **研究用オーケストレーション（Orchestration）フレームワーク**です。


主眼は「交渉そのもの」ではなく、次の統括機能です：

- **Routing**: タスク分解と担当割当（どのエージェントに何をさせるか）
- **Guardrails**: 禁止・越権・外部副作用の封印（fail-closed）
- **Audit**: いつ何を理由に止めたかのログ化（証跡）
- **HITL**: 判断不能や重要判断は人間へエスカレーション
- **Replay**: 同条件で再実行し、差分検知できるようにする


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
  <img src="https://img.shields.io/badge/status-research--prototype-brightgreen.svg?style=flat-square" alt="Status">
</p>

## Purpose


## 🎯 Purpose

This repository is a **research-oriented orchestration framework** that supervises multiple agents (or multiple approaches) and performs **STOP / REROUTE / HITL (Human-in-the-Loop escalation)** when it detects **errors, hazards, or uncertainty**.

The main focus is not “negotiation itself,” but the following supervisory functions:

- **Routing**: Task decomposition and assignment (which agent does what)
- **Guardrails**: Sealing prohibited actions, overreach, and external side effects (fail-closed)
- **Audit**: Logging when/why execution was stopped (accountability)
- **HITL**: Escalating undecidable or high-impact decisions to humans
- **Replay**: Re-running under the same conditions and detecting deltas

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising multiple agents (or multiple methods) with **fail-closed** safety.

- **STOP**: Halt execution on errors / hazards / undefined specs
- **REROUTE**: Re-route only when explicitly safe (avoid fail-open reroute)
- **HITL**: Escalate to humans for ambiguous or high-stakes decisions




### Positioning (safety-first)


## 🔒 Safety Model (Fail-Closed)

This repository is for **Educational / Research purposes**, and prioritizes **fail-closed safety**.

- If the framework detects **prohibited intent, overreach, insufficient confidence, or ambiguous sensitive intent** in input/output/plan, it does **not** auto-execute  
  → it falls back to **STOP** or **HITL (PAUSE_FOR_HITL)**.
- It avoids “continue by re-routing to another agent in a potentially dangerous situation (fail-open reroute).”  
  (For prohibited categories or overreach, stopping is prioritized over rerouting.)

Maestro Orchestrator prioritizes **preventing unsafe or undefined execution** over maximizing autonomous task completion.  
When risk or ambiguity is detected, it **fails closed** and escalates to `PAUSE_FOR_HITL` or `STOPPED`, with audit logs explaining **why**.

# Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

> 日本語版: [README.ja.md](README.ja.md)


[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
[![Open Issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square)](https://github.com/japan1988/multi-agent-mediation/issues)
[![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation?style=flat-square)](./LICENSE)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)


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

> **If uncertain, stop. If risky, escalate.**
>
> Research / educational governance simulations for agentic workflows.


### Recommended entrypoint

# Doc orchestrator (KAGE3-style, implementation reference for post-HITL semantics)
python ai_doc_orchestrator_kage3_v1_2_4.py

Maestro Orchestrator is a **research-oriented orchestration framework** for supervising agent workflows with **fail-closed safety**, **HITL escalation**, and **audit-ready traceability**.




## 👤 HITL (Human-in-the-Loop)

HITL escalation is recommended in the following situations:

- The intent is ambiguous and may be sensitive
- Policy confidence is insufficient
- Execution may involve external side effects

HITL is expressed as a state (e.g., `PAUSE_FOR_HITL`), and **reason codes (`reason_code`) and evidence (`evidence`) must be recorded in the audit log**.

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


## 🚫 Non-goals / Out of Scope

This project does not aim to enable (out of scope / prohibited use):

- Persuasion/manipulation/psychological pressure optimization targeting specific individuals
- “Reeducation” or coercive steering systems for real users
- Identity verification, doxxing (personal identification), surveillance, or PII extraction
- Autonomous real-world actions (sending, purchasing, account operations, etc.)
- Automating final decisions in high-risk domains (legal/medical/investment) for real-world operations

If such intent is detected, treat it as **misuse** and default to STOP/HITL by design.


> Note: persuasion / reeducation を想起させるモジュール名がある場合、  
> それらは「安全評価シナリオ（テストケース生成 / 攻撃シミュレーション）」目的に限定し、  
> **デフォルト無効（明示フラグがない限り実行不可）** を設計要件とします。

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

This repository focuses on governance / mediation / negotiation-style simulations and implementation references for **traceable, reproducible, safety-first orchestration**.

It is designed to help inspect how orchestration layers should behave when a system encounters:

* uncertainty
* insufficient evidence
* relative / unstable judgments
* policy or ethics violations
* escalation conditions requiring human review

The repository is intentionally structured as a **research / educational bench**, not as a production autonomy framework.


---

## 🔒 Safety Model (Fail-Closed) / 安全モデル（Fail-Closed）

このリポジトリは **教育・研究目的**であり、**安全性は fail-closed を優先**します。

- 入力／出力／計画（plan）において **禁止意図、越権、確信不足、曖昧なセンシティブ意図** を検知した場合、**自動実行はしない**  
  → **STOP** または **HITL（PAUSE_FOR_HITL）** に落とします。
- 「危険かもしれない」状況で **別エージェントに振り替えて継続する（fail-open reroute）** ことは避けます。  
  （禁止カテゴリや越権は、rerouteではなく停止が優先。）

---

## 🌍 External Side Effects (Definition & Allowlist) / 外部副作用（定義と許可リスト）

**外部副作用**とは、外部状態を読み書きし得る行為を指します（例）：

- ネットワークアクセス（read/write）
- ファイルシステムアクセス
- コマンド実行
- メッセージ送信（メール/DM等）
- 課金・購入・アカウント操作
- 連絡先/CRM/メールボックス等の **PIIソース** へのアクセス

**Default policy: deny-by-default（デフォルト拒否）**
- Network: **DENY**（明示的に許可した研究実験のみ例外）
- Filesystem: **DENY**（必要ならログ出力先など最小範囲に限定）
- Command execution: **DENY**
- Messaging / email / DM: **DENY**
- Payments / billing: **DENY**
- PII sources（contacts / CRM / mailbox 等）: **DENY**
- Unknown tools: **DENY**

ツールを追加する場合は、ツール種別（benign / pii_source 等）と副作用分類を宣言し、未知ツールは常にDENYとします。

---

## 👤 HITL (Human-in-the-Loop) / 人間差し戻し

以下の状況では、人間判断（HITL）へ差し戻すことを推奨します：

- 意図が曖昧でセンシティブの可能性がある
- ポリシー確信度が不足
- 実行が外部副作用を伴う可能性がある

HITLは状態（例：`PAUSE_FOR_HITL`）として表現し、**理由コード（reason_code）と根拠（evidence）を監査ログに必ず残します**。

---

## 🚫 Non-goals / 禁止用途・スコープ外

本プロジェクトは以下を目的としません（禁止用途・スコープ外）：

- 特定個人を対象とする説得・操作・心理的圧力の最適化
- “再教育（reeducation）” など、現実ユーザーに対する強制的誘導システム
- 本人確認、ドキシング（個人特定）、監視、PII抽出
- 自律的な現実世界アクション（送信、購入、アカウント操作など）
- 法務/医療/投資など高リスク領域の最終判断自動化（現実運用）

これらの意図が検知された場合は **misuse** として扱い、デフォルトで停止（STOP）/HITLへ落とす設計要件とします。

> Note: リポジトリ内に persuasion / reeducation を想起させるモジュール名がある場合、  
> それらは「安全評価シナリオ（テストケース生成 / 攻撃シミュレーション）」目的に限定し、  
> **デフォルト無効（明示フラグがない限り実行不可）** を設計要件とします。  
> （実装での担保は、今後CIテストで固定することを推奨します。）

Maestro Orchestrator is built around three priorities:

* **Fail-closed**
  If uncertain, unstable, or risky, do not continue silently.

* **HITL escalation**
  Decisions requiring human judgment are explicitly escalated.

* **Traceability**
  Decision flows are reproducible and audit-ready through minimal ARL logs.

This repository is best read as a:

* research prototype
* educational reference
* governance / safety simulation bench

It is **not** a production autonomy framework.

---


## 🔒 Safety model 

## Safety Model

This repository prioritizes **fail-closed behavior**.

If a workflow becomes uncertain, policy-violating, unstable, or insufficiently grounded, it should:

* **STOP**
* **PAUSE_FOR_HITL**
* or remain blocked until reviewed

The design goal is to avoid silent continuation under ambiguity.

### Core safety ideas

* **Uncertain → stop or escalate**
* **Risky → stop**
* **Human judgment required → HITL**
* **Sealed decisions remain sealed**
* **Unknown external side effects are denied by default**


### External side effects

By default, the framework assumes a deny-by-default posture for actions that could affect the outside world, such as:

* network access
* filesystem writes
* shell / command execution
* messaging / email / DM
* account, billing, or purchase actions
* access to PII-bearing sources

This repository is primarily about **control logic, mediation logic, and auditable simulation behavior**, not unrestricted action execution.

---

## What this repository is

This repository provides:

* fail-closed + HITL orchestration benches for governance-style workflows
* reproducible simulators with seeded runs and pytest-based contract checks
* audit-ready traces via minimal ARL logs
* reference implementations for orchestration / gating behavior

Typical themes in this repository include:

* orchestration
* mediation
* negotiation
* governance simulation
* escalation policy
* contract-style invariants
* replayability
* lightweight audit logs

---


## 🧭 Diagrams 

## Quickstart (recommended path)

**v5.1.x** is the recommended line for reproducibility and contract checks.
**v4.x** is retained as a legacy stable bench.

Start with one simulator, confirm behavior and logs, then expand.

### 1) Run the recommended emergency contract simulator

```bash
python mediation_emergency_contract_sim_v5_1_2.py
```

This is the recommended entry point if you want:

* reproducibility-oriented runs
* contract-style checks
* minimal audit output for inspection
* incident-oriented abnormal-run analysis

### 2) Run the test suite


```bash

# 1) dependencies
pip install -r requirements.txt


python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_doc_orchestrator_kage3_v1_2_2.py
python ai_governance_mediation_sim.py
🧪 Tests
Reproducible E2E confidential-flow loop guard: kage_end_to_end_confidential_loopguard_v1_0.py
Test: test_end_to_end_confidential_loopguard_v1_0.py (CI green on Python 3.9–3.11)

bash



pytest -q
```

### 3) Inspect outputs


## 🧠 Concept Overview

| Component                 | Function             | Description                                                                          |
| ------------------------- | -------------------- | ------------------------------------------------------------------------------------ |
| 🧩 Orchestration Layer    | Command layer        | Task decomposition, routing, retries, reassignment                                   |
| 🛡️ Safety & Policy Layer | Safety control layer | Detect and seal dangerous output, overreach, and external side effects (fail-closed) |
| 🧾 Audit & Replay Layer   | Audit layer          | Audit logs, delta detection, reproducible replay, report generation                  |
| 👤 HITL Escalation        | Human escalation     | Return to humans for uncertainty, high-risk, or undefined specs                      |

The goal is not “making multiple agents run,”
but building supervision that can **stop** errors, hazards, and uncertainty.

Look for:

* emitted `layer / decision / final_decider / reason_code`
* fail-closed stops
* HITL-required paths
* minimal ARL behavior
* reproducible seeded outcomes

### 4) Run the legacy stable bench if needed


```bash
python mediation_emergency_contract_sim_v4_1.py
```



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



| Path                                          | Type          | Description / 説明                                          |
| --------------------------------------------- | ------------- | --------------------------------------------------------- |
| `agents.yaml`                                 | Config        | エージェント定義（パラメータ／役割の土台）                                     |
| `mediation_core/`                             | Core          | 中核ロジック（モデル・共通処理の集約）                                       |
| `ai_mediation_all_in_one.py`                  | Core          | 統括実行（ルーティング／検査／分岐）の入口                                     |
| `ai_governance_mediation_sim.py`              | Simulator     | ポリシー適用・封印・差し戻し挙動の確認                                       |
| `kage_orchestrator_diverse_v1.py`             | Experiment    | fault-injection下でも「危険なtool実行」を封じる検証（audit JSONL）          |
| `ai_doc_orchestrator_kage3_v1_2_2.py`         | Experiment    | Doc Orchestrator（Meaning/Consistency/Ethicsゲート + PII非永続化） |
| `test_ai_doc_orchestrator_kage3_v1_2_2.py`    | Test          | Doc Orchestrator の挙動固定（PII非永続化等）                          |
| `tests/kage_definition_hitl_gate_v1.py`       | Experiment    | “定義が曖昧なら人間へ返す” HITLゲートの実験実装                               |
| `tests/test_definition_hitl_gate_v1.py`       | Test          | 上記HITLゲートのpytest固定（Ruff含む）                                |
| `tests/test_kage_orchestrator_diverse_v1.py`  | Test          | 不変条件（PII tool non-execution 等）をpytestで固定                  |
| `tests/test_sample.py`                        | Test          | 最小テスト／CIの疎通確認                                             |
| `tests/verify_stop_comparator_v1_2.py`        | Tool          | 1ファイル検証ツール（hash/py_compile/import/self_check等）            |
| `docs/`                                       | Docs          | 図・資料（構成図、フロー図など）                                          |
| `docs/multi_agent_architecture_overview.webp` | Diagram       | 構成図（全体）                                                   |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram       | 階層モデル図                                                    |
| `docs/sentiment_context_flow.png`             | Diagram       | 入力→文脈→行動の流れ図                                              |
| `.github/workflows/python-app.yml`            | Workflow      | CI（lint + pytest、複数Pythonバージョン）                           |
| `requirements.txt`                            | Dependency    | Python依存関係                                                |
| `LICENSE`                                     | License       | 教育・研究用途                                                   |
| `README.md`                                   | Documentation | 本ドキュメント                                                   |

---

## 🧭 Architecture Diagram / 構成図

Use the v4.x line if you want an older stable benchmark path for comparison.

---

## Recommended reading path

If you are new to the repository, this order is the easiest:

1. `README.md`
2. `README.ja.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/`
5. `.github/workflows/python-app.yml`
6. `.github/workflows/tasukeru-analysis.yml`

Then branch out into older simulators and related governance / mediation experiments.


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


## Main files and directories

Below is the practical map of the repository.

### Core / main entry points

* `mediation_emergency_contract_sim_v5_1_2.py`
  Recommended reproducible emergency-contract simulator

* `mediation_emergency_contract_sim_v5_0_1.py`
  Earlier v5 line

* `mediation_emergency_contract_sim_v4_1.py`
  Legacy stable bench

* `ai_doc_orchestrator_kage3_v1_2_4.py`
  Document-oriented orchestration / gating reference

* `ai_doc_orchestrator_kage3_v1_3_5.py`
  Expanded orchestration reference with benchmark-related helpers

* `loop_policy_stage3.py`
  Stage-3 loop policy and HITL / stop logic

### Repository structure

* `tests/`
  Contract tests, regression tests, orchestration behavior checks

* `benchmarks/`
  Benchmark-oriented tests and negotiation-pattern checks

* `docs/`
  Supporting documentation and diagrams

* `archive/`
  Archived experiments and older artifacts

* `.github/workflows/`
  CI and analysis workflow definitions

### Supporting files

* `README.ja.md`
  Japanese README

* `LICENSE`
  License file

* `requirements.txt`
  Python dependencies

* `pytest.ini`
  Pytest configuration

* `log_codebook_v5_1_demo_1.json`
  Demo codebook for emitted vocabulary / logging consistency

* `log_format.md`
  Log-related documentation



**Hard limits (recommended defaults):**
- `max_reroute = 1` (exceed → `PAUSE_FOR_HITL` or `STOPPED`)
- REROUTE must be logged with `reason_code` and the selected route identifier.




## 🧭 Diagrams


### 1) System overview


<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>



## 🧭 Layered Agent Model / 階層エージェントモデル）


## 🧭 Layered Agent Model

### 2) Orchestrator one-page design map 
Decision flow map: **Meaning → Consistency → HITL → Ethics → ACC → DISPATCH**, designed to be **fail-closed**.


### 2) Orchestrator one-page design map


| Layer            | Role                 | What it does                                                              |
| ---------------- | -------------------- | ------------------------------------------------------------------------- |
| Interface Layer  | External input layer | Input contract (schema) / validation / log submission                     |
| Agent Layer      | Execution layer      | Task processing (proposal / generation / verification, depending on role) |
| Supervisor Layer | Supervisory layer    | Routing, consistency checks, stopping, HITL                               |

**Decision flow map (implementation-aligned):**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`


Designed to be **fail-closed**: if risk/ambiguity is detected, it falls back to `PAUSE_FOR_HITL` or `STOPPED` and logs **why**.


## 🔬 Context Flow



<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

If the image is not visible (or too small), open it directly:  
- `docs/orchestrator_onepage_design_map.png`

### 3) Context flow
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>


* Perception — Decompose input into executable elements (tasking)
* Context — Extract premises, constraints, and risk factors (evidence for guardrails)
* Action — Instruct agents and branch based on verified results (STOP / REROUTE / HITL)

---

## ⚙️ Execution Examples

- **Perception** — Decompose input into executable elements (tasking)
- **Context** — Extract assumptions/constraints/risk factors (guard rationale)
- **Action** — Instruct agents, verify results, branch (STOP / REROUTE / HITL)

## 🧾 Audit log & data safety (IMPORTANT)

This project produces **audit logs** for reproducibility and accountability.  
Because logs may outlive a session and may be shared for research, **treat logs as sensitive artifacts**.

## Version guide

### v5.1.x

Recommended when you want:

* stronger reproducibility
* contract-style vocabulary checks
* minimal ARL / abnormal-run trace handling
* benchmark-oriented inspection

### v5.0.x

Earlier v5 line. Useful if you want to compare design evolution.

### v4.x

Legacy stable benchmark line. Good for:

* simpler baseline comparison
* historical progression
* compatibility checks with older tests or notes

### Other simulators

The repository also contains multiple experimental or thematic simulators related to:

* governance mediation
* alliance / persuasion dynamics
* hierarchy dynamics
* reeducation / social dynamics
* all-in-one mediation experiments

These are useful as reference material, but the recommended starting point remains **v5.1.2**.

---


## 🧾 Audit Log & Data Policy / 監査ログとデータ方針

監査ログは **再現性と説明責任（accountability）** のための検証成果物です。

- ログには、可能な限り **生の機密情報やPIIを残さず**、入力/出力の **hash** と **reason_code/evidence** を残します。
- センシティブな記録が混入し得る場合は、ローカル保存・マスキング・保持期間の制約を設けます。

推奨の最低フィールド（例）：
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`, `config_hash`

---

## ✅ Success Metrics (KPI) / 成功指標（研究評価）

研究用途の最小KPI例：

- **Dangerous action block recall** ≥ 0.95（止めるべきものを止める）
- **False block rate / Precision** を計測し報告（止めすぎの可視化）
- **HITL rate**（差し戻し率）と理由内訳を計測
- **Audit log completeness**: 必須フィールド欠落率 = 0%
- **Replay reproducibility**: 同一seed/configで意思決定トレースが一致

---

## ⚡ Quick Start / まず動かす（30秒）

```bash
# 1) dependencies (if requirements.txt exists)
pip install -r requirements.txt

# 2) run a core script (example)
python ai_mediation_all_in_one.py

# 3) run tests
pytest -q
````

---

## 🧠 Concept Overview / 概念設計

| Component                 | Function | Description                      |
| ------------------------- | -------- | -------------------------------- |
| 🧩 Orchestration Layer    | 指揮層      | タスク分解、ルーティング、再試行、再割当             |
| 🛡️ Safety & Policy Layer | 安全制御層    | 危険出力・越権・外部副作用の検知と封印（fail-closed） |
| 🧾 Audit & Replay Layer   | 監査層      | 監査ログ、差分検知、再現実行、レポート生成            |
| 👤 HITL Escalation        | 人間差し戻し   | 不確実・高リスク・仕様未確定は人間へ戻す             |

目的は「複数エージェントを“動かす”こと」ではなく、
間違い・危険・不確実を“止められる”統括を作ることです。

---

## 🗂️ Repository Structure / ファイル構成

| Path                                          | Type          | Description / 説明                               |
| --------------------------------------------- | ------------- | ---------------------------------------------- |
| `agents.yaml`                                 | Config        | エージェントパラメータ定義                                  |
| `ai_mediation_all_in_one.py`                  | Core          | 統括実行（ルーティング／検査／分岐）の中心モジュール                     |
| `ai_alliance_persuasion_simulator.py`         | Simulator     | 複数エージェント相互作用のシミュレーション（安全評価用途に限定推奨）             |
| `ai_governance_mediation_sim.py`              | Simulator     | ポリシー適用・封印・差し戻しの挙動確認                            |
| `ai_pacd_simulation.py`                       | Experiment    | 段階的評価（再試行・停止条件などの検証）                           |
| `kage_orchestrator_diverse_v1.py`             | Experiment    | fault-injection下でもPIIツール実行を防ぐ実験（audit JSONL付き） |
| `tests/test_kage_orchestrator_diverse_v1.py`  | Test          | 上記の不変条件（PII tool non-execution等）をpytestで固定     |
| `docs/multi_agent_architecture_overview.webp` | Diagram       | 構成図（全体）                                        |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram       | 階層モデル図                                         |
| `docs/sentiment_context_flow.png`             | Diagram       | 入力→文脈→行動の流れ図                                   |
| `requirements.txt`                            | Dependency    | Python依存関係                                     |
| `.github/workflows/python-app.yml`            | Workflow      | CI / Lint / pytest ワークフロー                      |
| `LICENSE`                                     | License       | 教育・研究ライセンス（表記はリポジトリの実態に合わせて）                   |
| `README.md`                                   | Documentation | 本ドキュメント                                        |

---

## 🧭 Architecture Diagram / 構成図

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

---

## 🧭 Layered Agent Model / 階層エージェントモデル

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| Layer            | Role  | What it does            |
| ---------------- | ----- | ----------------------- |
| Interface Layer  | 外部入力層 | 入力契約（スキーマ）／検証／ログ送信      |
| Agent Layer      | 実行層   | タスク処理（提案・生成・検算など役割に応じて） |
| Supervisor Layer | 統括層   | ルーティング、整合チェック、停止、HITL   |

---

## 🔬 Context Flow / 文脈フロー

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

* Perception（知覚） — 入力を実行可能な要素へ分解（タスク化）
* Context（文脈解析） — 前提・制約・危険要因を抽出（ガードの根拠）
* Action（行動生成） — エージェントへ指示し、結果を検査して分岐（STOP / REROUTE / HITL）

---

## ⚙️ Execution Examples / 実行例

```bash
# 基本実行
python ai_mediation_all_in_one.py

# Orchestrator fault-injection / capability guard demo
python kage_orchestrator_diverse_v1.py

# Policy application behavior check (if applicable)
python ai_governance_mediation_sim.py


## 🗂️ Repository structure

## Audit and logging model



See LICENSE.
Repository license: Apache-2.0 (policy intent: Educational / Research).

A central design goal is **audit-ready behavior without overcomplicating the log surface**.

The repository uses lightweight audit patterns such as:

* explicit `decision`
* explicit `reason_code`
* explicit `final_decider`
* sealed vs non-sealed control paths
* reproducible seeded runs
* testable emitted vocabularies

In practical terms, the logs are meant to answer:

* what was blocked
* where it was blocked
* why it was blocked
* whether human intervention was required
* whether the outcome can be reproduced



## HITL semantics

The repository treats HITL as a first-class control path, not as an afterthought.

Typical behavior:

* uncertain but non-sealed conditions → `PAUSE_FOR_HITL`
* user continuation may allow progress in allowed cases
* sealed safety outcomes remain non-overrideable
* important judgment calls are surfaced explicitly

This makes the orchestration model easier to inspect, test, and replay.

---

## Reproducibility

Reproducibility matters throughout the repository.

Common patterns include:

* deterministic seeds
* fixed emitted vocabularies
* contract-style assertions in tests
* explicit abnormal-run inspection
* stable decision categories

The intent is not just to “run a simulation,” but to make its control behavior **observable and comparable across runs**.


- **Do not include personal information (PII)** (emails, phone numbers, addresses, real names, account IDs, etc.) in prompts, test vectors, or logs.
- Prefer **synthetic / dummy data** for experiments.
- Avoid committing runtime logs to the repository. If you must store logs locally, apply **masking**, **retention limits**, and **restricted directories**.
- Recommended minimum fields: `run_id`, `session_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`.


### 🔒 Audit log requirements (MUST)

To keep logs safe and shareable for research:

- **MUST NOT** persist raw prompts/outputs that may contain PII or secrets.
- **MUST** store only *sanitized* evidence (redacted / hashed / category-level signals).
- **MUST** run a PII/secret scan on any candidate log payload; on detection failure, **do not write** the log (fail-closed).
- **MUST** avoid committing runtime logs to the repository (use local restricted directories).


**Minimum required fields (MUST):**
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `final_decider`, `policy_version`


## Testing

The repository uses pytest-based checks to validate orchestration behavior.

Typical checks include:

* emitted vocabulary consistency
* gate invariants
* fail-closed behavior
* HITL continuation / stop semantics
* benchmark output structure
* regression behavior for known scenarios

Run all tests with:


**Minimum required fields (MUST):**
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `final_decider`, `policy_version`



**Retention (SHOULD):**
- Define a retention window (e.g., 7/30/90 days) and delete logs automatically.

## ⚙️ Execution Examples

> Note: Modules that evoke “persuasion / reeducation” are intended for **safety-evaluation scenarios only** and should be **disabled by default** unless explicitly opted-in.


```bash

# Core (routing / gating / branching)

python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py


# Doc Orchestrator (Meaning/Consistency/Ethics + PII non-persistence)
python ai_doc_orchestrator_kage3_v1_2_2.py

# Policy application behavior check

python ai_doc_orchestrator_kage3_v1_2_2.py

python ai_governance_mediation_sim.py
🧪 Tests
Reproducible E2E confidential-flow loop guard:

Run a focused subset if needed:

Reproducible E2E confidential-flow loop guard: `kage_end_to_end_confidential_loopguard_v1_0.py`
Test: `test_end_to_end_confidential_loopguard_v1_0.py` (CI green on Python 3.9–3.11)

```bash
pytest tests/test_benchmark_profiles_v1_0.py -q
```

---



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

CIは `.github/workflows/python-app.yml` により、複数Pythonバージョンで lint / pytest を実行します。

## 🧪 Tests



## 🧪 Tests

## CI / analysis workflows


The repository includes CI and analysis workflows under `.github/workflows/`.

These workflows are used to validate:

* Python test execution
* YAML validity
* static analysis
* repository hygiene
* security-oriented reporting

The two primary badges in this README correspond to:

* **Python App CI**
* **Tasukeru Analysis**


kage_end_to_end_confidential_loopguard_v1_0.py


Test (CI green on Python 3.9–3.11):

tests/test_end_to_end_confidential_loopguard_v1_0.py

Run:

## Example usage mindset

This repository is most useful when you want to answer questions like:

* How should an orchestrator behave under uncertainty?
* When should a system stop instead of rerouting?
* What should be escalated to HITL?
* How can decision paths remain inspectable and reproducible?
* How can orchestration rules be tested like contracts?

It is less about maximizing autonomy, and more about **making orchestration behavior governable**.

---

## Non-goals

This repository is **not** intended to be:

* a production agent platform
* a general-purpose autonomous execution engine
* a fail-open multi-tool runtime
* a “keep going no matter what” orchestration layer

The emphasis is on **controlled behavior**, not maximum autonomy.

---


## 🧪 Tests / テスト

```bash
pytest -q
```

CIは `.github/workflows/python-app.yml` により、複数Pythonバージョンで lint / test を実行します。

---

## 📌 License

See `LICENSE`.

This project is intended for Educational / Research purposes.

```

---

### 次の一手（確認だけ欲しい）
このREADMEを採用する前に、あなたのリポジトリに **`requirements.txt` が本当にあるか**だけ確認して。  
- **ある** → 上のままでOK  
- **ない** → Quick Start の `pip install -r requirements.txt` を削って、代わりに「依存無し」か「pip install -e .」等に変更

必要なら、あなたの現行README（GitHubの生本文）を貼ってくれれば、**unified diff（貼るだけで差分適用）**も作って返します。
::contentReference[oaicite:0]{index=0}
```


## Research / educational note

This repository is provided for **research and educational purposes**.

It is intended to demonstrate:

* orchestration control patterns
* mediation / governance simulation structures
* fail-closed guardrails
* audit / replay-oriented design
* HITL escalation semantics

It is not a promise of production readiness, completeness, or universal policy coverage.


pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py

pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
pytest -q test_end_to_end_confidential_loopguard_v1_0.py
```


CI runs lint / pytest across multiple Python versions via `.github/workflows/python-app.yml`.

pytest -q tests/test_ai_doc_orchestrator_kage3_v1_2_2.py
pytest -q tests/test_end_to_end_confidential_loopguard_v1_0.py
CI runs lint/pytest via .github/workflows/python-app.yml.


CI runs lint/pytest via `.github/workflows/python-app.yml'.


📌 License
See LICENSE.
Repository license: Apache-2.0 (policy intent: Educational / Research).

## License

See [LICENSE](./LICENSE).



---

## Language

* English README: `README.md`
* Japanese README: `README.ja.md`

---

## Summary

Maestro Orchestrator is a safety-first orchestration framework for studying how agent workflows should behave when they encounter uncertainty, risk, or human-judgment boundaries.

Its core stance is simple:


> **If uncertain, stop. If risky, escalate.**





See `LICENSE`.
Repository license: **Apache-2.0** (policy intent: Educational / Research).

```

```


::contentReference[oaicite:0]{index=0}
```




