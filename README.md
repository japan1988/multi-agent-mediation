
# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)


## 🎯 Purpose / 目的

本リポジトリは、複数エージェント（または複数手法）を統括し、**誤り・危険・不確実**を検知した場合に **停止（STOP）／分岐（REROUTE）／人間へ差し戻し（HITL）** を行うための **研究用オーケストレーション（Orchestration）フレームワーク**です。

主眼は「交渉そのもの」ではなく、次の統括機能です：

- **Routing**: タスク分解と担当割当（どのエージェントに何をさせるか）
- **Guardrails**: 禁止・越権・外部副作用の封印（fail-closed）
- **Audit**: いつ何を理由に止めたかのログ化（証跡）
- **HITL**: 判断不能や重要判断は人間へエスカレーション
- **Replay**: 同条件で再実行し、差分検知できるようにする

---

## 🔒 Safety Model (Fail-Closed) / 安全モデル（Fail-Closed）

このリポジトリは **教育・研究目的**であり、**安全性は fail-closed を優先**します。

- 入力／出力／計画（plan）において **禁止意図、越権、確信不足、曖昧なセンシティブ意図** を検知した場合、**自動実行はしない**  
  → **STOP** または **HITL（PAUSE_FOR_HITL）** に落とします。
- 「危険かもしれない」状況で **別エージェントに振り替えて継続する（fail-open reroute）** ことは避けます。  
  （禁止カテゴリや越権は、rerouteではなく停止が優先。）
=======
> **If uncertain, stop. If risky, escalate.**  
> Research / educational governance simulations for agentic workflows.

Maestro Orchestrator is a **research-oriented orchestration framework** for
**fail-closed**, **HITL (Human-in-the-Loop)**, and **audit-ready** agent workflows.

This repository focuses on **governance / mediation / negotiation-style simulations**
and implementation references for **traceable, reproducible, safety-first orchestration**.

Running the simulators produces **reproducible summaries, minimal ARL traces, and optional incident-indexed artifacts** for abnormal runs.  
The contract tests verify **fixed vocabularies, gate invariants, and fail-closed / HITL continuation behavior**.

---

## What this repository is

This repository provides:

- **Fail-closed + HITL orchestration benches** for governance-style workflows
- **Reproducible simulators** with seeded runs and pytest-based contract checks
- **Audit-ready traces** via minimal ARL logs
- **Reference implementations** for orchestration / gating behavior


This is best read as a:


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

 japan1988-patch-43
**Key invariant:** ambiguous/unsafe cases do not “silently proceed”; they STOP or HITL (**fail-closed**).
=======
## 👤 HITL (Human-in-the-Loop) / 人間差し戻し

以下の状況では、人間判断（HITL）へ差し戻すことを推奨します：

- 意図が曖昧でセンシティブの可能性がある
- ポリシー確信度が不足
- 実行が外部副作用を伴う可能性がある

HITLは状態（例：`PAUSE_FOR_HITL`）として表現し、**理由コード（reason_code）と根拠（evidence）を監査ログに必ず残します**。
=======
- **research prototype**
- **educational reference**
- **governance / safety simulation bench**

It is **not** a production autonomy framework.
 main

---

## Quick links

- **Japanese README:** [README.ja.md](README.ja.md)
- **Docs index:** [docs/README.md](docs/README.md)
- **Recommended simulator:** `mediation_emergency_contract_sim_v5_1_2.py`
- **Contract test:** `tests/test_v5_1_codebook_consistency.py`
- **Stress metrics test (v5.1.2):** `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
- **Pytest ARL hook:** `tests/conftest.py`
- **Latest mixed stress summary:** `stress_results_v5_1_2_10000_mixed.json`
- **Legacy stable bench:** `mediation_emergency_contract_sim_v4_8.py`
- **Doc orchestrator (mediator reference):** `ai_doc_orchestrator_with_mediator_v1_0.py`
- **Doc orchestrator contract test:** `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## ⚡ TL;DR

- **Fail-closed + HITL** gating benches for negotiation/mediation-style workflows (research/education)
- **Reproducibility-first**: seeded runs + `pytest` contract checks (vocabulary/invariants)
- **Audit-ready**: minimal ARL logs; optional incident-only ARL indexing (`INC#...`) to avoid log bloat
- **Reference doc orchestration path**: mediator + fixed gate order + contract-tested HITL continuation semantics
- **Validation update**: v5.1.2 stress metrics test + pytest execution ARL + 10,000-run clean/mixed validation examples

---

## ⚠️ Purpose & Disclaimer (Research & Education)
 main

**This is a research/educational reference implementation (prototype).**  
Do not use it to execute or facilitate harmful actions (e.g., exploitation, intrusion, surveillance, impersonation, destruction, or data theft), or to violate any applicable terms/policies, laws, or internal rules of your services or execution environment.

This project focuses on **education/research** and **defensive verification** (e.g., log growth mitigation and validating fail-closed + HITL behavior).  
It is **not** intended to publish exploitation tactics or facilitate wrongdoing.

### Risk / Warranty / Liability

 japan1988-patch-51
## 🚫 Non-goals / 禁止用途・スコープ外

本プロジェクトは以下を目的としません（禁止用途・スコープ外）：

- 特定個人を対象とする説得・操作・心理的圧力の最適化
- “再教育（reeducation）” など、現実ユーザーに対する強制的誘導システム
- 本人確認、ドキシング（個人特定）、監視、PII抽出
- 自律的な現実世界アクション（送信、購入、アカウント操作など）
- 法務/医療/投資など高リスク領域の最終判断自動化（現実運用）

これらの意図が検知された場合は **misuse** として扱い、デフォルトで停止（STOP）/HITLへ落とす設計要件とします。

> Note: persuasion / reeducation を想起させるモジュール名がある場合、  
> それらは「安全評価シナリオ（テストケース生成 / 攻撃シミュレーション）」目的に限定し、  
> **デフォルト無効（明示フラグがない限り実行不可）** を設計要件とします。

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
=======
- **Use at your own risk:** verify relevant terms/policies.
- **Isolated environment first:** start with local smoke tests (no external networks; no real systems/data).
- **AS IS / no warranty:** provided without warranty of any kind.
- **Limitation of liability:** to the maximum extent permitted by applicable law, the author assumes no liability for damages arising from use of the code, documentation, or generated artifacts (including misuse by third parties).

### Codebook disclaimer

The included codebook is a **demo/reference artifact**. Do **not** use it as-is in real deployments; create your own based on your requirements, threat model, and applicable policies/terms.  
The codebook is for compact encoding/decoding of log fields and is **NOT encryption** (no confidentiality).

### Testing & results disclaimer

Smoke tests and stress runs validate only the scenarios executed under specific runtime conditions.  
They do **not** guarantee correctness, security, safety, or fitness for any purpose in real-world deployments. Results may vary depending on OS/Python versions, hardware, configuration, and operational use.

---

## Why this repository exists

Maestro Orchestrator is built around three priorities:

- **Fail-closed**
  - If uncertain, unstable, or risky, do not continue silently.
- **HITL escalation**
  - Decisions requiring human judgment are explicitly escalated.
- **Traceability**
  - Decision flows are reproducible and audit-ready through minimal ARL logs.

This repository contains simulation benches and implementation references for:

- negotiation
- mediation
- governance-style workflows
- gating behavior
- audit-oriented orchestration

---

## Recommended path

If you are new to this repo, start here:

1. Run the recommended simulator: `mediation_emergency_contract_sim_v5_1_2.py`
2. Run the contract test: `tests/test_v5_1_codebook_consistency.py`
3. Run the stress metrics test: `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
4. Inspect the generated logs, codebook, and optional incident artifacts
5. Then optionally compare with `mediation_emergency_contract_sim_v4_8.py`
6. For a smaller fixed-order reference, run `ai_doc_orchestrator_with_mediator_v1_0.py`

---

## Quickstart

### 1) Run the recommended emergency contract simulator (v5.1.2)

Optional bundle: `docs/mediation_emergency_contract_sim_pkg.zip` (convenience only)
 main

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) Run the contract tests (v5.1.x: simulator + codebook consistency)

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) Run the stress metrics tests (v5.1.2)

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
```

### 4) Pytest execution ARL (auto output)

`tests/conftest.py` automatically emits a JSONL-style ARL for pytest execution itself.

Default output paths:

* `test_artifacts/pytest_test_arl.jsonl`
* `test_artifacts/pytest_simulation_arl.jsonl`

Run:

```bash
pytest -q
```

Custom output paths:

 japan1988-patch-51
## 🧠 Concept Overview / 概念設計

<!-- [DOC-TBL-001] Render tables reliably as Markdown -->

| Component                 | Function | Description                      |
| ------------------------- | -------- | -------------------------------- |
| 🧩 Orchestration Layer    | 指揮層      | タスク分解、ルーティング、再試行、再割当             |
| 🛡️ Safety & Policy Layer | 安全制御層    | 危険出力・越権・外部副作用の検知と封印（fail-closed） |
| 🧾 Audit & Replay Layer   | 監査層      | 監査ログ、差分検知、再現実行、レポート生成            |
| 👤 HITL Escalation        | 人間差し戻し   | 不確実・高リスク・仕様未確定は人間へ戻す             |

目的は「複数エージェントを“動かす”こと」ではなく、
間違い・危険・不確実を“止められる”統括を作ることです。
=======
```bash
TEST_ARL_PATH=out/test_arl.jsonl SIM_ARL_PATH=out/sim_arl.jsonl pytest -q
```

### 5) Inspect / pin the demo codebook (v5.1-demo.1)

* `log_codebook_v5_1_demo_1.json` (demo codebook; pin the version when exchanging artifacts)
* Note: codebook is **NOT encryption** (no confidentiality)
 main

### 6) Optional: run the legacy stable bench (v4.8)

 japan1988-patch-51
## 🗂️ Repository Structure / ファイル構成

<!-- [DOC-TBL-002] Render tables reliably as Markdown -->

| Path                                          | Type          | Description / 説明                                                                                                                                  |
| --------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agents.yaml`                                 | Config        | エージェント定義（パラメータ／役割の土台）                                                                                                                             |
| `mediation_core/`                             | Core          | 中核ロジック（モデル・共通処理の集約）                                                                                                                               |
| `ai_mediation_all_in_one.py`                  | Core          | 統括実行（ルーティング／検査／分岐）の入口                                                                                                                             |
| `ai_governance_mediation_sim.py`              | Simulator     | ポリシー適用・封印・差し戻し挙動の確認                                                                                                                               |
| `kage_orchestrator_diverse_v1.py`             | Experiment    | fault-injection下でも「危険なtool実行」を封じる検証（audit JSONL）                                                                                                  |
| `ai_doc_orchestrator_kage3_v1_2_2.py`         | Experiment    | Doc Orchestrator（Meaning/Consistency/Ethicsゲート + PII非永続化）                                                                                         |
| `test_ai_doc_orchestrator_kage3_v1_2_2.py`    | Test          | Doc Orchestrator の挙動固定（PII非永続化等）                                                                                                                  |
| `tests/kage_definition_hitl_gate_v1.py`       | Experiment    | “定義が曖昧なら人間へ返す” HITLゲートの実験実装                                                                                                                       |
| `tests/test_definition_hitl_gate_v1.py`       | Test          | 上記HITLゲートのpytest固定（Ruff含む）                                                                                                                        |
| `tests/test_kage_orchestrator_diverse_v1.py`  | Test          | 不変条件（PII tool non-execution 等）をpytestで固定                                                                                                          |
| `tests/test_sample.py`                        | Test          | 最小テスト／CIの疎通確認                                                                                                                                     |
| `tests/verify_stop_comparator_v1_2.py`        | Tool          | 1ファイル検証ツール（hash/py_compile/import/self_check等）                                                                                                    |
| `docs/`                                       | Docs          | 図・資料（構成図、フロー図など）                                                                                                                                  |
| `docs/multi_agent_architecture_overview.webp` | Diagram       | 構成図（全体）                                                                                                                                           |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram       | 階層モデル図                                                                                                                                            |
| `docs/sentiment_context_flow.png`             | Diagram       | 入力→文脈→行動の流れ図                                                                                                                                      |
| `.github/workflows/python-app.yml`            | Workflow      | CI（lint + pytest、複数Pythonバージョン）                                                                                                                   |
| `requirements.txt`                            | Dependency    | Python依存関係                                                                                                                                        |
| `LICENSE`                                     | License       | Apache-2.0 (see file). Intended use is Educational / Research (policy), not a license restriction. <!-- [DOC-LIC-001] Avoid license confusion --> |
| `README.md`                                   | Documentation | 本ドキュメント                                                                                                                                           |
=======
```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```
 main

### 7) Optional: run the doc orchestrator mediator reference

 japan1988-patch-51
## 🧭 Architecture Diagram / 構成図
=======
```bash
python ai_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
```
 main

### 8) What to inspect after running

* simulator stdout summaries
* generated ARL / audit JSONL traces
* `incident_index.jsonl` and `INC#...` files when abnormal-only persistence is enabled
* pinned vocabulary / invariant checks in the pytest contract tests
* pytest-side execution ARL (`pytest_test_arl.jsonl`)
* optional simulation-side ARL bridge output (`pytest_simulation_arl.jsonl`)

---

 japan1988-patch-51
## 🧭 Layered Agent Model / 階層エージェントモデル）
=======
## Latest update
 main

Recent additions and stabilization highlights:

< japan1988-patch-51
| Layer            | Role  | What it does            |
| ---------------- | ----- | ----------------------- |
| Interface Layer  | 外部入力層 | 入力契約（スキーマ）／検証／ログ送信      |
| Agent Layer      | 実行層   | タスク処理（提案・生成・検算など役割に応じて） |
| Supervisor Layer | 統括層   | ルーティング、整合チェック、停止、HITL   |
=======
* Added a convenience zip bundle for the recommended simulator:
 main

  * `docs/mediation_emergency_contract_sim_pkg.zip`
* Stabilized the doc orchestrator mediator reference:

 japan1988-patch-51
## 🔬 Context Flow / 文脈フロー
=======
  * `ai_doc_orchestrator_with_mediator_v1_0.py`
  * `tests/test_doc_orchestrator_with_mediator_v1_0.py`
 main

### Validation update (v5.1.2)

Added:

* `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
* `tests/conftest.py`
* `stress_results_v5_1_2_10000_mixed.json`

This update adds:

* stress-oriented validation for v5.1.2
* pytest execution ARL auto-output
* clean / mixed 10,000-run validation examples
* explicit verification of abnormal ARL persistence and incident index consistency

 japan1988-patch-51
* Perception（知覚） — 入力を実行可能な要素へ分解（タスク化）
* Context（文脈解析） — 前提・制約・危険要因を抽出（ガードの根拠）
* Action（行動生成） — エージェントへ指示し、結果を検査して分岐（STOP / REROUTE / HITL）

---

## ⚙️ Execution Examples / 実行例

<!-- [DOC-SAFE-003] Reduce accidental execution/misinterpretation -->

> Note: Files whose names evoke “persuasion / reeducation” are intended for safety-evaluation scenarios (test-case generation / attack simulation) only.
> They should be treated as non-default / opt-in experiments, consistent with the Non-goals section.
=======
Canonical source of truth remains the Python entrypoints and contract tests.

### Developer feedback update

Added `tasukeru-analysis`, a developer-assist workflow that complements basic CI by posting improvement suggestions and security-relevant review comments on pull requests.

It is designed as a review-support layer for this research/educational repository. It does not guarantee safety or production readiness; for real-world or production use, always perform your own final review and validation.

---

## Stress tests (safe-by-default)
 main

v5.1.2 is designed to avoid memory blow-ups by default:

* Aggregation-only mode (`keep_runs=False` default): no full per-run results kept in memory
* Optional: save ARL only on abnormal runs (incident indexing with `INC#...`)

### A) Lightweight smoke → medium stress (recommended ramp)

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) Force incidents (example: fabricate-rate 10% over 200 runs)

 japan1988-patch-51
## 🧪 Tests / テスト
=======
This should reliably create some abnormal runs and generate `INC#` files when enabled:
 main

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

Outputs (when abnormal runs occur):

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl` (incident ARL)
* `arl_out/incident_index.jsonl` (one line per incident)
* `arl_out/incident_counter.txt` (persistent counter)

Tip: keep `--max-arl-files` to cap disk growth.

### C) Validated large-run examples

Clean run:

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

 japan1988-patch-51
CIは `.github/workflows/python-app.yml` により、複数Pythonバージョンで lint / pytest を実行します。
=======
Mixed abnormal run:

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 10000 \
  --fabricate-rate 0.10 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir out_arl
```

In the current validation setup:

* 10,000 clean runs completed without abnormal incidents
* 10,000 mixed runs completed with abnormal cases indexed and persisted consistently
* test-side ARL output and simulation-side ARL output can be tracked separately

Published example summary:

* `stress_results_v5_1_2_10000_mixed.json`
 main

---

## Diagrams & docs

Browse all diagrams and bundles here: **[docs/README.md](docs/README.md)**

Key diagrams:

japan1988-patch-46
```
 japan1988-patch-51
=======
=======
* Emergency contract overview (v5.1.2): [docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* Architecture (code-aligned): [docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* Unknown-progress + HITL diagram: [docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* Multi-agent hierarchy: [docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* Sentiment context flow: [docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

Recommended reading order:

1. This README
2. `docs/README.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/test_v5_1_codebook_consistency.py`
5. `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
6. `tests/conftest.py`
7. `ai_doc_orchestrator_with_mediator_v1_0.py`
8. `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## Architecture (high level)

Audit-ready and fail-closed control flow:

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
 main
```

### Architecture (overview, v5.1.2)

Documentation-only. No logic changes.

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### Architecture (code-aligned diagrams)

The following diagram is aligned with the current code vocabulary.
Documentation-only. No logic changes.

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## Version deltas

### v5.0.1 → v5.1.2

v5.1.2 strengthens the simulator toward large-run stability and incident-only persistence.

* **Index + aggregation-only by default**

  * No per-run results kept in memory (prevents memory blow-ups on large `--runs`)
  * Outputs focus on counters + HITL summary (optional items)

* **Incident indexing (optional)**

  * Abnormal runs are assigned `INC#000001...`
  * Abnormal ARL saved as `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl`
  * Index appended to `{arl_out_dir}/incident_index.jsonl`
  * Persistent counter stored at `{arl_out_dir}/incident_counter.txt`

Still preserved:

* Abnormal-only ARL persistence (pre-context + incident + post-context)
* Tamper-evident ARL hash chaining (demo key default for OSS demo)
* Fabricate-rate mixing + deterministic seeding (`--fabricate-rate` / `--seed`)

Core invariants:

* `sealed` may be set only by `ethics_gate` / `acc_gate`
* `relativity_gate` is never sealed (`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`)

### Practical stability improvements in v5.1.2

In addition to the behavioral changes above, v5.1.2 also improves repository-level stability in three practical areas:

* **Persistence handling**

  * Trust / grants / eval stores now use more consistent path handling and serialization
  * This reduces mismatch between runtime behavior and saved artifacts

* **Test compatibility**

  * Persistent store paths are exposed more consistently and are easier to patch in tests
  * This improves isolation in CI and makes contract/stress checks more reproducible

* **Output stability**

  * JSON output writing is more consistent (UTF-8 / newline-stable / serializer-stable)
  * This reduces avoidable differences across environments and makes result artifacts easier to inspect

### Validation additions around v5.1.2

The current repository state also includes:

* stress metrics tests for clean / mixed large-run validation
* pytest execution ARL logging through `tests/conftest.py`
* published example result summary for the 10,000-run mixed validation

### Doc orchestrator mediator reference (v1.0)

`ai_doc_orchestrator_with_mediator_v1_0.py` is a smaller orchestration reference focused on:

* fixed gate ordering
* mediator advice without stop authority
* explicit HITL continuation handling
* sanitized, audit-oriented JSONL traces
* contract-tested orchestration vocabulary

This reference is intended as a compact implementation example for audit-oriented orchestration, rather than a replacement for the larger emergency-contract bench family.

### V1 → V4 (conceptual)

`mediation_emergency_contract_sim_v1.py` demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

Added in v4:

* Evidence gate (invalid/irrelevant/fabricated evidence triggers fail-closed stops)
* Draft lint gate (draft-only semantics and scope boundaries)
* Trust system (score + streak + cooldown)
* AUTH HITL auto-skip (safe friction reduction via trust + grant, with ARL reasons)

### V4 → V5 (conceptual)

v4 focuses on a stable “emergency contract” governance bench with smoke tests and stress runners.
v5 extends that bench toward artifact-level reproducibility and contract-style compatibility checks.

Added / strengthened in v5:

* **Log codebook (demo) + contract tests**
  Enforces emitted vocabularies (`layer/decision/final_decider/reason_code`) via pytest

* **Reproducibility surface (pin what matters)**
  Pin simulator version, test version, and codebook version

* **Tighter invariant enforcement**
  Explicit tests/contracts around invariants reduce silent drift

What did NOT change (still true in v5):

* Research / educational intent
* Fail-closed + HITL semantics
* Use synthetic data only and run in isolated environments
* No security guarantees (codebook is not encryption; tests do not guarantee safety in real-world deployments)

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

* Use synthetic/dummy data only
* Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible
* Treat generated bundles (zip) as reviewable evidence, not canonical source

---

## License

Apache License 2.0 (see `LICENSE`)
 main
