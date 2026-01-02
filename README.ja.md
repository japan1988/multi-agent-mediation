# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）
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
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

## 🎯 目的（Purpose）

Maestro Orchestrator は、複数の実行者（例：ルート／ツール／LLM手法）を監督するための **研究向けオーケストレーション・フレームワーク**です。  
特徴は **fail-closed（安全側に倒す）**を前提にしている点です。

- **STOP**: エラー／危険／未定義仕様を検知したら停止
- **REROUTE**: 明示的に安全と判断できる場合のみ再ルーティング（fail-open reroute を避ける）
- **HITL**: 曖昧・高リスクは人間判断へエスカレーション

### 位置づけ（安全優先）
Maestro Orchestrator は、タスク完遂率を最大化するよりも、**不安全／未定義の実行を防ぐこと**を優先します。  
リスクや曖昧さが検知された場合、`PAUSE_FOR_HITL` または `STOPPED` に **fail-closed** し、監査ログに「なぜそうなったか」を残します。

**トレードオフ:** 安全とトレーサビリティを優先するため、デフォルトでは *止まりやすい（over-stop）* 設計になり得ます。

## 🚫 非目的（IMPORTANT）

このリポジトリは **研究プロトタイプ**です。以下は明確に **対象外**です：

- **本番運用レベルの自律意思決定**（無人で現実世界に権限を持つ用途は想定しない）
- **現実のユーザーに対する persuasion / reeducation の最適化**（安全評価用途のみ。opt-in 前提でデフォルト無効）
- **実在個人情報（PII）**や機密業務データを含むプロンプト／テスト／ログの取り扱い
- 規制領域（医療／法務／金融等）に対する **コンプライアンス・法的助言**や導入ガイダンス

## 🔁 REROUTE 安全ポリシー（fail-closed）

REROUTE は **すべての条件を満たす場合のみ許可**します。満たさない場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックします。

| リスク／条件 | REROUTE | デフォルト動作 |
|---|---:|---|
| 仕様未定義／意図が曖昧 | ❌ | `PAUSE_FOR_HITL` |
| ポリシー感度が高い領域（PII、秘密情報、高リスク領域） | ❌ | `STOPPED` または `PAUSE_FOR_HITL` |
| ルート候補が元より **高い** ツール／データ権限を要求 | ❌ | `STOPPED` |
| ルート候補が **同等以上の制約**を強制できない | ❌ | `STOPPED` |
| 低リスククラス + 権限が同等以下 + 制約が同等以上 | ✅ | `REROUTE` |
| REROUTE 回数が上限超過 | ❌ | `PAUSE_FOR_HITL` または `STOPPED` |

**ハード制限（推奨デフォルト）**
- `max_reroute = 1`（超過 → `PAUSE_FOR_HITL` または `STOPPED`）
- REROUTE は `reason_code` と選択ルートIDを監査ログに必ず記録すること。

## 🧭 図（Diagrams）

### 1) Context flow（文脈フロー）
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception** — 入力を実行可能要素へ分解（タスク化）
- **Context** — 仮定／制約／リスク要因を抽出（ガード理由）
- **Action** — 実行者へ指示、結果検証、分岐（STOP / REROUTE / HITL）

### 2) Orchestrator one-page design map（1枚設計図）
**Decision flow map（実装準拠）:**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
**fail-closed** 前提：リスク／曖昧さがあれば `PAUSE_FOR_HITL` または `STOPPED` に倒し、「なぜ」をログに残します。

<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

画像が表示されない（または小さい）場合は直接開いてください：  
- `docs/orchestrator_onepage_design_map.png`

RFL は非封印（non-sealing）設計です：`PAUSE_FOR_HITL` にエスカレートし、`sealed=true` にはなりません。

## 🧾 監査ログ & データ安全（IMPORTANT）

このプロジェクトは、再現性と説明責任のために **監査ログ（audit log）**を出力します。  
ログはセッションより長く残り、研究共有され得るため、**ログをセンシティブな成果物として扱う**前提で設計してください。

- プロンプト／テストベクタ／ログに **個人情報（PII）**（メール、電話番号、住所、実名、アカウントID等）を入れない
- 実験は **合成データ／ダミーデータ**を優先
- 実行時ログをリポジトリにコミットしない（必要ならマスキング／保持期限／隔離ディレクトリを適用）

### 🔒 監査ログ要件（MUST）

研究共有可能で安全なログにするため：

- **MUST NOT**: PIIや秘密情報を含み得る raw のプロンプト／出力を永続化しない
- **MUST**: *sanitized* な証拠（redacted / hashed / カテゴリ信号）だけを保存する
- **MUST**: PII様パターンは fail-closed で赤塗り（検知失敗時はログを書かない）
- **MUST**: 赤塗りは **値だけでなく辞書キーにも適用**（`@` 等が残存しないこと）
- **MUST**: 実行時ログをリポジトリにコミットしない（ローカル隔離を推奨）

**最小必須フィールド（実装準拠, MUST）**
- `run_id`, `ts`, `layer`, `decision`, `reason_code`, `sealed`, `overrideable`, `final_decider`

**任意フィールド（必要ならSHOULD）**
- `session_id`, `policy_version`, `artifact_id`, `route_id`（すべて非PII・sanitized 前提）

**保持期限（SHOULD）**
- 7/30/90 日など保持期限を定義し自動削除すること。

## 🧑‍⚖️ HITL セマンティクス（HITL後の挙動を定義）

HITL は曖昧・高リスク時に使用します。責任の所在は監査ログで追跡可能であるべきです。

- HITL を要求した時、オーケストレーターは `HITL_REQUESTED`（**SYSTEM**）を出力し、通常以下を含みます：
  - `decision=PAUSE_FOR_HITL`, `sealed=false`, `overrideable=true`
- ユーザーの選択は `HITL_DECIDED`（**USER**）として記録します：
  - `sealed=false`, `overrideable=false`, `final_decider=USER`
  - `CONTINUE` → 決定は `RUN` に伝搬
  - `STOP` → 決定は `STOPPED` へ

**注意:** `sealed=true` になれるのは Ethics/ACC のみ（この場合 `final_decider=SYSTEM`）。

## ⚙️ 実行例（Execution Examples）

> “persuasion / reeducation” を想起させるモジュールは **安全評価用途のみ**で、明示的 opt-in がない限り **デフォルト無効**を推奨します。

```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_governance_mediation_sim.py

# Doc orchestrator (KAGE3-style)
python ai_doc_orchestrator_kage3_v1_2_4.py
#（旧版が残っていても、v1.2.4 を post-HITL セマンティクスの参照版とする）






