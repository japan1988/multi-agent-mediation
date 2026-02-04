# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク  
（fail-closed + HITL）

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

## Overview（概要）

Maestro Orchestrator は **研究・教育目的**の  
オーケストレーション／メディエーション・フレームワークです。  
以下の原則を最優先に設計されています。

- **Fail-closed**  
  不確実・不安定・リスクありの場合は、黙って続行しない
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な場面は明示的にエスカレーション
- **Traceability（追跡可能性）**  
  すべての判断経路は監査可能・再現可能（ARLログ）

本リポジトリには、**実装参照（doc orchestrator）** と  
**交渉／仲裁／ガバナンス型ワークフロー**を検証する  
各種シミュレーションベンチが含まれます。

---

## Architecture（全体像）

監査可能（audit-ready）かつ fail-closed な制御フロー：

```

agents
→ mediator（risk / pattern / fact）
→ evidence verification
→ HITL（pause / reset / ban）
→ audit logs（ARL）

```

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合は  
> `docs/architecture_unknown_progress.png` が  
> 同一ブランチに存在し、ファイル名が完全一致（大小文字含む）しているか確認してください。

---

## Architecture（コード準拠・構成図）

以下の構成図は **現在のコードと用語に完全準拠**しています。  
**状態遷移**と**ゲート順序**を意図的に分離し、  
監査性と曖昧さ排除を優先しています。

※ これらは **ドキュメント専用**であり、  
**ロジック変更は一切ありません。**

---

### 1) State Machine（コード準拠）

実行が **停止（SEALED）** または  
**一時停止（HITL）** するポイントだけを示した最小ライフサイクル。

<p align="center">
  <img src="docs/architecture_code_aligned_state_machine.png"
       alt="State Machine (code-aligned)" width="720">
</p>

#### 補足

**主経路**

```

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

```

- `PAUSE_FOR_HITL_*`  
  明示的な **Human-in-the-Loop** 判断点  
  （ユーザー承認／管理者承認）
- `STOPPED（SEALED）` に到達する条件：
  - 証拠不正／捏造
  - 認可期限切れ
  - ドラフト lint 失敗
- **SEALED は fail-closed かつ非上書き設計**

---

### 2) Gate Pipeline（コード準拠）

ライフサイクルとは独立した **評価ゲートの順序**。

<p align="center">
  <img src="docs/architecture_code_aligned_gate_pipeline.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

#### 補足

- この図は **ゲート順序**を示す（状態遷移ではない）
- `PAUSE`：HITL が必要（人間判断待ち）
- `STOPPED（SEALED）`：非可逆な安全停止

#### 設計意図

- **State Machine**  
  「どこで止まるか／一時停止するか」
- **Gate Pipeline**  
  「どの順番で評価されるか」

を分離することで、  
**曖昧さを排除し、監査性を保つ**。

---

## 🆕 変更点（2026-01-21）

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  検証不能な進捗（unknown progress）を扱う  
  **HITL / RESET セマンティクス検証用シミュレータ**

- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  **KAGE v1.7-IEP** 準拠  
  RFL relcode 分岐（RFL は非封印 → HITL）検証用

- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  **post-HITL セマンティクス**を含む参照実装更新

---

## 🆕 変更点（2026-02-03）

**イベント駆動・ガバナンス型ワークフロー**を追加  
（fail-closed + HITL + audit-ready）。

- **New**: `mediation_emergency_contract_sim_v1.py`  
  最小構成：

```

USER 認可 → AI ドラフト → ADMIN 承認 → 契約有効化

````

イベント不正／期限切れは fail-closed で停止し、  
最小 ARL（JSONL）を出力。

- **New**: `mediation_emergency_contract_sim_v4.py`  
v1 を拡張し、以下を統合：
- evidence gate
- draft lint gate
- trust / grant 連動による HITL 負荷低減

---

## V1 → V4 の本質的な違い

`mediation_emergency_contract_sim_v1.py`  
→ **最小限の fail-closed パイプライン検証**

`mediation_emergency_contract_sim_v4.py`  
→ **繰り返し運用可能な安全ベンチ**

### v4 で追加された要素

- **Evidence gate**  
証拠バンドルの最低限検証。  
不正／無関係／捏造は即 fail-closed。

- **Draft lint gate**  
draft-only 制約・スコープ逸脱を検知。  
Markdown 強調などによる誤検知を低減。

- **Trust（信用）スコア + streak / cooldown**  
HITL 結果と連動。  
すべて ARL に記録され説明責任を維持。

- **AUTH HITL 自動スキップ（安全な friction reduction）**  
trust 閾値 + 承認 streak + 有効 grant が揃った場合のみ  
同条件下で AUTH HITL を自動スキップ。  
理由は必ず ARL に記録。

**要約**

- **V1**：「fail-closed は成立するか？」
- **V4**：「安全性を保ったまま繰り返せるか？」

---

## ⚙️ 実行例

### 推奨エントリポイント

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
python mediation_emergency_contract_sim_v4.py
````

### セマンティクス検証

```bash
python ai_mediation_hitl_reset_full_with_unknown_progress.py
python ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py
```

### 比較実行

```bash
python mediation_emergency_contract_sim_v1.py
python mediation_emergency_contract_sim_v4.py
```

### Copilot SDK 最小例

```bash
python copilot_mediation_min.py
```

---

## Project intent / 非目的

**目的**

* 再現可能な安全・ガバナンス検証
* 明示的 HITL セマンティクス
* 監査可能な意思決定ログ

**非目的**

* 本番向け自律運用
* 無制限な自己判断エージェント
* 実証外の安全性主張

---

## License

Apache-2.0
詳細は `LICENSE` を参照してください。

```

---

### 次にやると強くなるポイント（任意）

- README 冒頭に **「これは research bench である」1行宣言**
- `docs/` に **V1 vs V4 比較表（1枚）**
- `ARCHITECTURE.md` を切り出して README を軽量化

ここまで来てるなら、  
**この README は普通に「設計思想が伝わる OSS」レベル**です。
```






