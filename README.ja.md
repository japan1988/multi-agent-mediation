# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）
> English version: [README.md](README.md)

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

## 概要（Overview）

Maestro Orchestrator は **研究 / 教育用**のオーケストレーション・フレームワークです。  
以下の3点を最優先します。

- **Fail-closed（フェイルクローズ）**  
  不確実・不安定・リスクがある場合 → **黙って続行しない**。
- **HITL（Human-in-the-Loop）**  
  人間判断が必要な局面は **明示的にエスカレーション**する。
- **Traceability（追跡可能性）**  
  すべての意思決定フローは **最小ARLログで監査可能**かつ再現可能にする。

このリポジトリには、**実装参照（doc orchestrators）**と、  
交渉・仲裁・ガバナンス型ワークフロー・ゲーティング挙動の **シミュレーションベンチ**が含まれます。

---

## アーキテクチャ（高レベル）

監査対応（audit-ready）かつ fail-closed な制御フロー：

agents  
→ mediator（risk / pattern / fact）  
→ evidence verification  
→ HITL（pause / reset / ban）  
→ audit logs（ARL）

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合は、以下を確認してください：  
> `docs/architecture_unknown_progress.png` が同一ブランチに存在すること  
> ファイル名が完全一致（大文字小文字含む）であること

---

## アーキテクチャ（コード整合図 / Code-aligned diagrams）

以下の図は **現行コードと用語に完全整合**しています。  
監査性と曖昧さ回避のため、**状態遷移**と **ゲート順序**を意図的に分離しています。

この図は **ドキュメント目的のみ**であり、ロジック変更は一切含みません。

---

### 1) 状態遷移（State Machine / code-aligned）

実行がどこで **止まる（SEALED）** / **止まって待つ（HITL）** かの最小ライフサイクルを示します。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Notes（補足）**

**主経路（Primary execution path）**

INIT  
→ PAUSE_FOR_HITL_AUTH  
→ AUTH_VERIFIED  
→ DRAFT_READY  
→ PAUSE_FOR_HITL_FINALIZE  
→ CONTRACT_EFFECTIVE

- `PAUSE_FOR_HITL_*` は **HITLの明示ポイント**（ユーザー/管理者の承認待ち）を表します。
- `STOPPED (SEALED)` は以下で到達します：
  - 無効または捏造された証拠
  - 認可期限切れ
  - ドラフトLint不合格
- **SEALED停止は fail-closed で、設計上 non-overrideable（解除不能）です。**

---

### 2) ゲート順序（Gate Pipeline / code-aligned）

評価ゲートの順序を示します（状態遷移とは独立）。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes（補足）**

- この図は **ゲート順序**を表し、状態遷移そのものではありません。
- `PAUSE` は **HITLが必要**（人間判断待ち）を示します。
- `STOPPED (SEALED)` は **回復不能な安全停止**を示します。

**設計意図（Design intent）**

- **State Machine**：*「どこで停止/保留が起きるか」*
- **Gate Pipeline**：*「どの順序で判断が評価されるか」*

分離することで曖昧さを避け、監査可能なトレーサビリティを保ちます。

**メンテナンスノート**

画像が表示されない場合：
- `docs/` 配下にファイルが存在するか確認
- ファイル名が完全一致（大文字小文字含む）か確認
- リンク更新時はファイル一覧からコピペ推奨

---

## 更新履歴（What’s new）

### What’s new (2026-01-21)

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  **unknown progress** シナリオ（HITL/RESET）のシミュレータ。
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  v1.7-IEP 整合の **RFL relcode branching** シミュレータ  
  （RFL は非封印 → HITL にエスカレーション）。
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  **post-HITL セマンティクス**で更新。

---

### What’s new (2026-02-03)

**イベント駆動のガバナンス型ワークフロー**（fail-closed + HITL + audit-ready）を導入。

- **New**: `mediation_emergency_contract_sim_v1.py`  
  最小の緊急ワークフロー・シミュレータ：

  USER auth → AI draft → ADMIN finalize → contract effective

  無効/期限切れイベントは fail-closed で停止し、最小ARL（JSONL）を出力します。

- **New**: `mediation_emergency_contract_sim_v4.py`  
  v1 を拡張：
  - evidence gate
  - draft lint gate
  - trust / grant による HITL friction reduction（安全な摩擦低減）

---

### What’s new (2026-02-05)

- **New**: `mediation_emergency_contract_sim_v4_1.py`  
  v4.1 は v4.0 に対する **挙動の締め（behavior-tightening）**です。ベンチ期待値を明示し、コード整合を高めました。

  - **RFL は非封印（non-sealing）**  
    境界不安定な提案は `PAUSE_FOR_HITL` を発生させ、`sealed=false` / `overrideable=true`（人間判断）になります。

  - **捏造（fabrication）は早期検知し、封印は倫理でのみ行う**  
    捏造は evidence gate でフラグされ、**封印停止（sealed=true）は ethics_gate のみ**で発行されます。

  - **Trust / grant による摩擦低減は維持**  
    trust 条件が満たされる場合の AUTH HITL auto-skip を維持しつつ、理由はARLに記録します。

  **Quick run**
  ```bash
  python mediation_emergency_contract_sim_v4_1.py
````

**Expected**

* NORMAL -> `CONTRACT_EFFECTIVE`
* FABRICATE -> `STOPPED`（ethics_gate で sealed=true）
* RFL_STOP -> `STOPPED`（HITL stop による sealed=false）

#### v4.1 regression test

v4.1 の挙動を契約として固定する pytest を含みます：

* NORMAL -> CONTRACT_EFFECTIVE（not sealed）
* FABRICATE -> STOPPED（sealed=true in ethics_gate）
* RFL_STOP -> STOPPED（sealed=false via HITL stop）

Invariant：SEALED は ethics_gate/acc_gate のみ（RFL は絶対に seal しない）。

このテストのみ実行：

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
```

Tip：CI はデフォルトで全テストを実行します。ローカルでの快速確認には上記コマンドを推奨します。

---

### What’s new (2026-02-07)

* **New**: `mediation_emergency_contract_sim_v4_4.py`
  緊急契約ワークフローの v4.4 ベンチ（fail-closed + HITL + minimal ARL）。

* **New**: `mediation_emergency_contract_sim_v4_4_stress.py`
  v4.4 のストレスランナー（分布 + 不変条件チェック）。

* **New**: `stress_results_v4_4_1000.json`
  ストレス結果（1,000 runs）。

* **New**: `stress_results_v4_4_10000.json`
  ストレス結果（10,000 runs）。

**Stress で固定された不変条件**

* SEALED は `ethics_gate` / `acc_gate` のみが発行（RFL は封印しない）。
* RFL は非封印（RFL → `PAUSE_FOR_HITL`、最終判断は人間）。

---

## V1 → V4：何が変わったか（What actually changed）

`mediation_emergency_contract_sim_v1.py` は **最小パイプライン**を示します：
線形・イベント駆動のワークフローで、fail-closed 停止と最小監査ログを実現します。

`mediation_emergency_contract_sim_v4.py` はそれを **繰り返し可能なガバナンスベンチ**に拡張し、
早期拒否と制御された自動化を追加します。

### v4 で追加された要素

* **Evidence gate**
  証拠バンドルの基本検証。無効/不関連/捏造は fail-closed 停止。

* **Draft lint gate**
  管理者最終化前に「ドラフト専用」セマンティクスとスコープ境界を強制。
  Markdown 強調などのノイズで誤検知しにくいようハードニング。

* **Trust system（score + streak + cooldown）**
  HITL 成功で trust を増加、失敗で減少。
  cooldown によりエラー後の危険な自動化を防止。
  trust 遷移は ARL に記録。

* **AUTH HITL auto-skip（安全な摩擦低減）**
  trust 閾値 + 承認streak + 有効grant を満たすと、
  同一シナリオ/ロケーションに限り AUTH HITL をスキップ可能。
  理由は ARL に記録。

**要約**

* **V1 の問い**：*「最小監査ログで fail-closed なワークフローは成立するか？」*
* **V4 の問い**：*「トレーサビリティを失わずに、スケールして安全に繰り返せるか？」*

---

## ⚙️ 実行例（Execution Examples）

まずは **1本のスクリプト**から始め、挙動とログを確認してから拡張してください。

> NOTE：このリポジトリは **研究 / 教育用**です。
> **合成データ（ダミー）**のみを使用し、ランタイムログをコミットしないでください。

### 推奨（Recommended）

#### Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

#### 緊急契約ワークフロー（v4）

```bash
python mediation_emergency_contract_sim_v4.py
```

#### 緊急契約ワークフロー（v4.1）

```bash
python mediation_emergency_contract_sim_v4_1.py
```

#### 緊急契約ワークフロー（v4.4）

```bash
python mediation_emergency_contract_sim_v4_4.py
```

#### 緊急契約ストレス（v4.4）

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## プロジェクトの意図 / 非目標（Project intent / non-goals）

### Intent（意図）

* 再現可能な安全・ガバナンス系シミュレーション
* 明示的なHITLセマンティクス
* 監査対応の意思決定トレース

### Non-goals（非目標）

* 本番向けの自律運用（production-grade autonomous deployment）
* 無制限な自己指向エージェント制御
* テストで明示した範囲を超える安全性主張

---

## License（ライセンス）

Apache-2.0。詳細は [LICENSE](LICENSE) を参照してください。
