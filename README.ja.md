# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）

## 1) Context flow（文脈フロー）

<p align="center">
  <a href="docs/sentiment_context_flow.png">
    <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
  </a>
</p>

- **Perception** — 入力を実行可能要素へ分解（タスク化）
- **Context** — 仮定／制約／リスク要因を抽出（ガード理由）
- **Action** — 実行者へ指示、結果検証、分岐（STOP / REROUTE / HITL）

## 2) Orchestrator one-page design map（1枚設計図）

**Decision flow map（実装準拠）:**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`

**fail-closed** 前提：リスク／曖昧さがあれば `PAUSE_FOR_HITL` または `STOPPED` に倒し、「なぜ」をログに残します。

<p align="center">
  <a href="docs/orchestrator_onepage_design_map.png">
    <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
  </a>
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






