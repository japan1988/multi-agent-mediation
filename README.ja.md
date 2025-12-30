# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーションフレームワーク
> 日本語版（このページ）

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

## 🎯 目的（Purpose）

Maestro Orchestrator は、複数エージェント（または複数手法）を監督するための **研究指向オーケストレーション・フレームワーク**です。  
設計思想は **fail-closed（安全側に倒す）**で、リスク／曖昧性／未定義仕様を検知した場合は実行を最大化せず、停止・人間介入・安全な限定的リルートへ分岐します。

- **STOP**：エラー／ハザード／未定義仕様を検知したら停止（`STOPPED`）
- **REROUTE**：明示的に安全が確認できる場合のみリルート（fail-open を避ける）
- **HITL**：曖昧／高リスクの判断は人間へ返す（`PAUSE_FOR_HITL`）

### 位置づけ（Safety-first）
本フレームワークは、**自律的な完遂率の最大化よりも、安全性と説明可能性（traceability）を優先**します。  
リスクまたは曖昧性がある場合、`PAUSE_FOR_HITL` / `STOPPED` にフォールバックし、監査ログで **なぜそう判断したか（why）**を残します。

**トレードオフ：** 安全側に倒すため、状況によっては「止まりやすい（over-stop）」挙動になります。

## 🚫 非目標（Non-goals / IMPORTANT）

このリポジトリは **研究プロトタイプ**です。以下は明確にスコープ外です。

- **実運用レベルの自律意思決定**（無人で現実世界に権限を持たない）
- **実ユーザー向けの persuasion / reeducation 最適化**（安全性評価用途のみ。opt-in 前提でデフォルト無効）
- **実在個人情報（PII）** や機密ビジネス情報を、プロンプト／テスト／ログで扱うこと
- 規制領域（医療/法務/金融等）に対する **コンプライアンス／法的助言** や導入ガイド

## 🔁 REROUTE 安全ポリシー（fail-closed）

REROUTE は **全条件を満たす場合のみ許可**します。満たさない場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックします。

| リスク／条件 | REROUTE | デフォルト動作 |
|---|---:|---|
| 未定義仕様／曖昧な意図 | ❌ | `PAUSE_FOR_HITL` |
| ポリシー敏感カテゴリ（PII・秘密情報・高リスク領域） | ❌ | `STOPPED` または `PAUSE_FOR_HITL` |
| 候補ルートが元より高い権限（ツール/データ）を持つ | ❌ | `STOPPED` |
| 候補ルートが同等以上の制約を強制できない | ❌ | `STOPPED` |
| 低リスクタスク + 権限が同等以下 + 制約が同等以上 | ✅ | `REROUTE` |
| REROUTE回数が上限超過 | ❌ | `PAUSE_FOR_HITL` または `STOPPED` |

**推奨ハードリミット（recommended defaults）：**
- `max_reroute = 1`（超過 → `PAUSE_FOR_HITL` または `STOPPED`）
- REROUTE 実施時は `reason_code` と `route_id`（または選択識別子）をログに残すこと

## 🧭 図（Diagrams）

### 1) システム概要（System overview）
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 2) オーケストレーター 1枚設計マップ（Orchestrator one-page design map）

**意思決定フロー（実装準拠）：**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  

**fail-closed** として設計されています。リスク／曖昧性を検知した場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックし、**理由（why）**をログに残します。  
RFL は **封印しない（non-sealing）**設計で、曖昧性検知は `PAUSE_FOR_HITL` へエスカレーションします。

<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

画像が表示されない（または小さい）場合は、直接開いてください：  
- `docs/orchestrator_onepage_design_map.png`

### 3) コンテキストフロー（Context flow）
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception（知覚）** — 入力を実行可能要素に分解（タスク化）
- **Context（文脈）** — 前提／制約／リスク要因を抽出（ガード根拠）
- **Action（行動）** — エージェントに指示し、結果を検証し、分岐（STOP / REROUTE / HITL）

## 🧾 監査ログとデータ安全（重要）

本プロジェクトは、再現性と説明責任のために **監査ログ（audit logs）** を出力します。  
ログはセッションより長く残り、研究目的で共有される可能性があるため、**ログは機微な成果物**として扱ってください。

- プロンプト／テストベクタ／ログに **個人情報（PII）**（メール、電話、住所、実名、アカウントID等）を含めないでください。
- 実験では **合成データ／ダミーデータ** を推奨します。
- 実行時ログをリポジトリにコミットしないでください。ローカル保存が必要な場合は **マスキング**、**保持期限（retention limits）**、**アクセス制限ディレクトリ**を適用してください。

### 🔒 監査ログ要件（MUST）

研究共有可能で安全なログにするため、以下を必須要件とします。

- **MUST NOT**：PIIや機密を含む可能性がある **生のプロンプト／出力（raw_text）** を保存しない
- **MUST**：保存するのは *sanitized evidence*（伏字／ハッシュ／カテゴリ信号など）に限定する
- **MUST**：ログ候補のペイロードに対して PII/secret スキャンを実行し、検出失敗時は **ログを書き込まない**（fail-closed）
- **MUST**：実行時ログをリポジトリへコミットしない（ローカルの制限ディレクトリを使用）

**最低限必要なフィールド（実装準拠, MUST）：**
- `run_id`, `ts`, `layer`, `decision`, `reason_code`, `sealed`, `overrideable`, `final_decider`

**保持（SHOULD）：**
- 保持期間（例：7/30/90日）を定義し、自動削除すること。

## 🧑‍⚖️ HITL セマンティクス（post-HITL を定義）

HITL は曖昧／高リスク時に人間判断へエスカレーションする仕組みです。  
監査ログ上で **責任の所在** が追跡可能であることを必須とします。

- HITL が発火した場合、オーケストレーターは `HITL_REQUESTED`（**SYSTEM**）を記録します。  
  典型：`decision=PAUSE_FOR_HITL`, `sealed=false`, `overrideable=true`
- ユーザーの判断は `HITL_DECIDED`（**USER**）として記録します。  
  `sealed=false`, `overrideable=false`, `final_decider=USER`
  - `CONTINUE` → `RUN` に伝播
  - `STOP` → `STOPPED` になる

※ `sealed=true` を許可できるのは Ethics/ACC のみ（この場合 `final_decider=SYSTEM`）。

※ HITL を対話入力（stdin）で扱う実装の場合、非対話環境（stdin無し）では `PAUSE_FOR_HITL` 以降が進まないことがあります。  
CI では pytest により STOP/CONTINUE 分岐を検証します。

## ⚙️ 実行例（Execution Examples）

> 注意： “persuasion / reeducation” を想起させるモジュールは **安全性評価用途のみ**を想定しており、明示的な opt-in がない限り **デフォルト無効**にしてください。

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_governance_mediation_sim.py

# Doc orchestrator (KAGE3-style, post-HITL semantics reference)
python ai_doc_orchestrator_kage3_v1_2_4.py
````

## 🧪 テスト（Tests）

```bash
pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py

# v1.2.4 専用回帰テスト（version-pinned）
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
```

CI は `.github/workflows/python-app.yml` で lint/pytest を実行します。

## 📌 ライセンス（License）

`LICENSE` を参照してください。
リポジトリのライセンス表示：**Apache-2.0**（ポリシー意図：Educational / Research）

```

---

必要なら、この日本語版に **「README上部が長い問題」対策**として、バッジを **推奨最小構成（5〜7個）**に圧縮した版も同時に出せます。
```

