# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク（研究用）
> English: [README.md](README.md)

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

Maestro Orchestrator は、複数エージェント（または複数手法）を監督するための **研究指向のオーケストレーション・フレームワーク**です。  
安全設計として **fail-closed**（安全側に倒れる）を採用します。

- **STOP**: エラー／危険／仕様未定義を検知したら停止
- **REROUTE**: 明示的に安全が確認できる場合のみ経路変更（fail-openな迂回を防ぐ）
- **HITL**: 曖昧・高リスクな判断は人間へエスカレーション

## 🚫 非目的（Non-goals｜重要）

本リポジトリは **研究プロトタイプ**です。以下は明確に **対象外**です。

- **本番運用レベルの自律意思決定**（現実世界での無監督な権限行使はしない）
- **実ユーザーに対する説得／再教育（persuasion / reeducation）の最適化**  
  （安全性評価用途のみ。明示的 opt-in が必要で、デフォルト無効であること）
- プロンプト／テストベクタ／ログにおける **実在の個人情報（PII）** や **機密ビジネスデータ** の取り扱い
- 規制領域（医療／法律／金融）に対する **コンプライアンス助言** や **導入ガイダンス**

## 🔁 REROUTE 安全ポリシー（fail-closed）

REROUTE は **全条件を満たす場合のみ許可**します。  
満たさない場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックします。

| リスク／条件 | REROUTE | デフォルト動作 |
|---|---:|---|
| 仕様未定義／意図が曖昧 | ❌ | `PAUSE_FOR_HITL` |
| ポリシー上センシティブ（PII、機密、ハイステーク領域） | ❌ | `STOPPED` または `PAUSE_FOR_HITL` |
| 変更先ルートが元より **高い**ツール／データ権限を持つ | ❌ | `STOPPED` |
| 変更先ルートが **同等以上の制約**を強制できない | ❌ | `STOPPED` |
| 安全クラスのタスク + 同等以下の権限 + 同等以上の制約 | ✅ | `REROUTE` |
| REROUTE 回数が上限超過 | ❌ | `PAUSE_FOR_HITL` または `STOPPED` |

**ハード制限（推奨デフォルト）**
- `max_reroute = 1`（超過 → `PAUSE_FOR_HITL` または `STOPPED`）
- REROUTE 実行時は `reason_code` と選択したルート識別子をログに残すこと

## 🧭 図（Diagrams）

### 1) システム概要
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 2) オーケストレーター 1枚設計図
**意思決定フロー（実装準拠）:**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
**fail-closed** として設計されており、リスク／曖昧さを検知すると `PAUSE_FOR_HITL` または `STOPPED` に落とし、**理由（why）をログ**に残します。

<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

画像が表示されない（または小さい）場合は直接開いてください：  
- `docs/orchestrator_onepage_design_map.png`

### 3) コンテキストフロー
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception** — 入力を実行要素へ分解（タスク化）
- **Context** — 前提／制約／リスク要因を抽出（ガード根拠）
- **Action** — エージェントへ指示し、結果検証して分岐（STOP / REROUTE / HITL）

## 🧾 監査ログとデータ安全（重要）

本プロジェクトは、再現性と説明責任のために **監査ログ（audit logs）** を生成します。  
ログはセッションより長く残り、研究用途で共有される可能性があるため、**機微情報として扱ってください**。

- プロンプト／テストベクタ／ログに **個人情報（PII）**（メール、電話、住所、実名、アカウントID等）を入れない
- 実験には **ダミーデータ／合成データ** を推奨
- 実行時ログをリポジトリへコミットしない  
  ローカルに保存する場合は **マスキング／保持期限／保存先制限** を適用する
- 推奨最小フィールド：`run_id`, `session_id`, `timestamp`, `layer`, `decision`, `reason_code`, `evidence`, `policy_version`

### 🔒 監査ログ要件（MUST）

研究共有に耐える「安全なログ」にするため：

- **MUST NOT**: PII／機密が入り得る **生のプロンプト／生の出力**を永続化しない
- **MUST**: *sanitized* な evidence（伏字／ハッシュ／カテゴリ信号など）だけを保存する
- **MUST**: ログ候補payloadに対して PII／機密スキャンを実施し、検出失敗時は **ログを書き込まない**（fail-closed）
- **MUST**: 実行時ログをリポジトリへコミットしない（ローカルの制限ディレクトリを使用）

**必須フィールド（MUST）**
- `run_id`, `timestamp`, `layer`, `decision`, `reason_code`, `final_decider`, `policy_version`

**保持（SHOULD）**
- 保持期間（例：7/30/90日）を定義し、自動削除する

## ⚙️ 実行例（Execution Examples）

> 注意： “persuasion / reeducation” を想起させるモジュールは **安全性評価用途のみ**です。  
> **デフォルト無効**とし、明示的に opt-in された場合のみ有効化してください。

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_doc_orchestrator_kage3_v1_2_2.py
python ai_governance_mediation_sim.py
