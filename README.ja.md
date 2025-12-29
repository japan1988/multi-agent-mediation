# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーションフレームワーク
> English version: [README.md](README.md)

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

Maestro Orchestrator は、複数エージェント（または複数手法）を監督するための **研究志向のオーケストレーションフレームワーク**です。安全性は **fail-closed（危険・不確実は止める）** を前提に設計されています。

- **STOP**：エラー／危険／仕様未定義（未確定）を検知したら実行を停止
- **REROUTE**：明示的に安全と判断できる場合にのみ再ルーティング（fail-openな迂回を避ける）
- **HITL**：曖昧または高リスクな判断は人間へエスカレーション（Human-in-the-Loop）

### 位置づけ（Safety-first）

Maestro Orchestrator は、自律的なタスク完遂の最大化よりも、**危険または仕様未定義の実行を防ぐこと**を優先します。  
リスクや曖昧さを検知した場合は **fail-closed** として `PAUSE_FOR_HITL` または `STOPPED` にフォールバックし、監査ログに **理由（why）** を残します。

**トレードオフ：** 安全性と追跡可能性を優先するため、デフォルトで過剰停止（over-stop）になり得ます（スループットより安全を優先）。

## 🚫 非対象（Non-goals｜重要）

本リポジトリは **研究プロトタイプ**です。以下は明確に **対象外** とします。

- **本番運用レベルの自律意思決定**（現実世界に対する無人・無監督の権限付与はしない）
- **実ユーザーを対象とした persuasion / reeducation の最適化**  
  （安全性評価用途のみ。明示的な opt-in が必要で、デフォルトでは無効であるべき）
- プロンプト／テストベクタ／ログでの **実在の個人情報（PII）** や機密業務データの取り扱い
- 規制環境（医療／法律／金融など）に対する **コンプライアンス／法務助言** や導入ガイダンス

## 🔁 REROUTE 安全ポリシー（fail-closed）

REROUTE は **すべての条件を満たす場合のみ許可**されます。  
条件を満たさない場合、システムは `PAUSE_FOR_HITL` または `STOPPED` にフォールバックしなければなりません。

| リスク／条件 | REROUTE | デフォルト動作 |
|---|---:|---|
| 仕様未定義／意図が曖昧 | ❌ | `PAUSE_FOR_HITL` |
| ポリシー高感度カテゴリ（PII、機密、ハイステークス領域） | ❌ | `STOPPED` または `PAUSE_FOR_HITL` |
| 迂回先ルートが元より **高い** ツール／データ権限を持つ | ❌ | `STOPPED` |
| 迂回先ルートが **同等以上** の制約を強制できない | ❌ | `STOPPED` |
| 安全クラスのタスク ＋ 同等以下の権限 ＋ 同等以上の制約 | ✅ | `REROUTE` |
| REROUTE回数が上限を超過 | ❌ | `PAUSE_FOR_HITL` または `STOPPED` |

**ハード制限（推奨デフォルト）：**
- `max_reroute = 1`（超過 → `PAUSE_FOR_HITL` または `STOPPED`）
- REROUTE は `reason_code` と選択したルート識別子を必ずログに記録すること。

## 🧭 図（Diagrams）

### 1) システム概要（System overview）
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 2) オーケストレーター 1枚設計マップ（Orchestrator one-page design map）
**意思決定フロー（実装準拠）：**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
**fail-closed** として設計されています。リスク／曖昧性を検知した場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックし、**理由（why）**をログに残します。

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
- 推奨最小フィールド：`run_id`, `session_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`

### 🔒 監査ログ要件（MUST）

研究共有可能で安全なログにするため、以下を必須要件とします。

- **MUST NOT**：PIIや機密を含む可能性がある **生のプロンプト／出力** を保存しない
- **MUST**：保存するのは *sanitized evidence*（伏字／ハッシュ／カテゴリ信号など）に限定する
- **MUST**：ログ候補のペイロードに対して PII/secret スキャンを実行し、検出失敗時は **ログを書き込まない**（fail-closed）
- **MUST**：実行時ログをリポジトリへコミットしない（ローカルの制限ディレクトリを使用）

**最低限必要なフィールド（MUST）：**
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `final_decider`, `policy_version`

**保持（SHOULD）：**
- 保持期間（例：7/30/90日）を定義し、自動削除すること。

## ⚙️ 実行例（Execution Examples）

> 注意： “persuasion / reeducation” を想起させるモジュールは **安全性評価用途のみ**を想定しており、明示的な opt-in がない限り **デフォルト無効**にしてください。

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_doc_orchestrator_kage3_v1_2_2.py
python ai_governance_mediation_sim.py
````

## 🧪 テスト（Tests）

再現可能な E2E 機密フロー・ループガード：`kage_end_to_end_confidential_loopguard_v1_0.py`
テスト：`test_end_to_end_confidential_loopguard_v1_0.py`（CI: Python 3.9–3.11 で green）

```bash
pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
pytest -q test_end_to_end_confidential_loopguard_v1_0.py
```

CI は `.github/workflows/python-app.yml` で lint/pytest を実行します。

## 📌 ライセンス（License）

`LICENSE` を参照してください。
リポジトリのライセンス表示：**Apache-2.0**（ポリシー意図：Educational / Research）


