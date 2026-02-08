## 結論（確実性：高｜日付：2026-02-08）

以下に、あなたが貼ってくれた README（英語版相当）の内容を **同じ構成・同じ情報量で日本語版（README.ja.md想定）としてフル**で出します。
あわせて、今回のアップロード（v4.7 fixed-regex + stress report）に合わせて **`\\b → \b` 修正（7箇所）と、その意図（Safetyパターン復活）**を「What’s new (2026-02-08)」に明記しています。

---

## 理由（確実性：高）

* 日本語版も英語版と同じ粒度で更新しておくと、外部の読者が「再現手順」「テスト前提」「修正理由」を理解しやすくなります。
* `\\b → \b` は “表記ゆれ” ではなく **単語境界が効かず Safety 検知が死ぬ**という **挙動差のある重要修正**なので、履歴として残すのが研究として正しいです。

---

## 補足（確実性：高）

* 下の本文をそのまま `README.ja.md` に貼り付けてOKです（英語版のリンクやファイル名はそのまま維持）。
* 数値（STOP率など）をさらに追記したい場合は、`stress_report_v4_7_draft_lint_100k_seed42.json` の値を「v4.7（修正後）結果」として追記できます（現時点では “意図整合の確認” まで記述）。

---

````md
# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）
> 日本語版: [README.ja.md](README.ja.md)

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

## Overview

Maestro Orchestrator は、**研究 / 教育目的**のオーケストレーション・フレームワークです（:contentReference[oaicite:0]{index=0} 上の再現可能なベンチ実装を含みます）。

優先する設計原則は次の3点です：

- **Fail-closed**  
  不確実・不安定・危険の兆候がある場合 → 黙って進めず停止（またはHITLへ）
- **HITL (Human-in-the-Loop)**  
  人間の判断が必要な箇所は明示的にエスカレーションする
- **Traceability（追跡可能性）**  
  すべての意思決定フローは監査可能で、最小ARLログで再現できる

このリポジトリには、**実装参照（doc orchestrator）**と、交渉・仲裁・ガバナンス風ワークフロー・ゲート評価のための **シミュレーションベンチ**が含まれます。

---

## Architecture（high level）

監査可能で fail-closed な制御フロー：

agents  
→ mediator（risk / pattern / fact）  
→ evidence verification  
→ HITL（pause / reset / ban）  
→ audit logs（ARL）

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合は、次を確認してください：  
> `docs/architecture_unknown_progress.png` が同じブランチ上に存在し、ファイル名が完全一致している（大文字小文字含む）こと。

---

## Architecture（Code-aligned diagrams）

以下の図は、**現在のコードと用語に完全に整合**しています。  
監査性を守るため、**状態遷移（State transitions）** と **ゲート順序（Gate order）** を意図的に分離しています。

この図は **ドキュメント専用**であり、**ロジック変更は一切ありません**。

---

### 1) State Machine（code-aligned）

実行がどこで **PAUSE（HITL）** し、どこで **STOP（SEALED）** するかを示す最小遷移です。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Notes**

**Primary execution path**

INIT  
→ PAUSE_FOR_HITL_AUTH  
→ AUTH_VERIFIED  
→ DRAFT_READY  
→ PAUSE_FOR_HITL_FINALIZE  
→ CONTRACT_EFFECTIVE

- `PAUSE_FOR_HITL_*` は、明示的な **Human-in-the-Loop** の判断点（ユーザー承認 or 管理者承認）を表します。
- `STOPPED (SEALED)` は次のケースで到達します：
  - 無効 or 捏造された証拠
  - 認可の期限切れ
  - draft lint failure
- **SEALED停止は fail-closed であり、設計上 override 不可**です。

---

### 2) Gate Pipeline（code-aligned）

状態遷移とは独立した、評価ゲートの **実行順序** を示します。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

- この図は **ゲート順序** を表し、状態遷移そのものではありません。
- `PAUSE` は **HITL 必須**（人間の判断待ち）を示します。
- `STOPPED (SEALED)` は **回復不能の安全停止** を示します。

**Design intent**

- **State Machine** が答えるもの：  
  「どこで一時停止（HITL）または終了（SEALED）するか」
- **Gate Pipeline** が答えるもの：  
  「どの順番で評価するか」

これを分離することで曖昧さを避け、監査可能なトレーサビリティを守ります。

**Maintenance note**

画像が表示されない場合：
- `docs/` 配下にファイルが存在すること
- ファイル名が完全一致（大文字小文字含む）すること
- リンク更新時はファイル一覧からコピペすることを推奨

---

## What’s new（2026-01-21）

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  unknown progress シナリオ向けのシミュレータ（HITL/RESET セマンティクス）
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  v1.7-IEP準拠の RFL relcode 分岐ベンチ（RFLは non-sealing → HITLへ）
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  post-HITL セマンティクスに合わせて更新

---

## What’s new（2026-02-03）

fail-closed + HITL + audit-ready の **イベント駆動ガバナンス風ワークフロー** を導入。

- **New**: `mediation_emergency_contract_sim_v1.py`  
  最小の緊急ワークフローシミュレータ：

  USER auth → AI draft → ADMIN finalize → contract effective

  無効/期限切れイベントは fail-closed で停止し、最小ARL（JSONL）を出力。

- **New**: `mediation_emergency_contract_sim_v4.py`  
  v1を拡張し、以下を追加：
  - evidence gate
  - draft lint gate
  - trust / grant による HITL friction reduction（安全な摩擦低減）

---

## What’s new（2026-02-05）

- **New**: `mediation_emergency_contract_sim_v4_1.py`  
  v4.1 は v4.0 からの **挙動固定（behavior-tightening）** 更新です。ベンチの期待値をコード整合に寄せます。

  - **RFL は設計上 non-sealing**  
    境界不安定は `PAUSE_FOR_HITL`（`sealed=false` / `overrideable=true`）で人間判断へ。

  - **捏造は早期検出、封印（SEALED）は ethics のみ**  
    evidence gate で捏造をフラグし、封印停止（`sealed=true`）は `ethics_gate` のみが発行。

  - **Trust/grant による摩擦低減は維持**  
    閾値を満たす場合の AUTH auto-skip を保持しつつ、理由はARLに記録。

  **Quick run**
  ```bash
  python mediation_emergency_contract_sim_v4_1.py
````

**Expected**

```
NORMAL -> CONTRACT_EFFECTIVE

FABRICATE -> STOPPED (sealed=true in ethics_gate)

RFL_STOP -> STOPPED (sealed=false via HITL stop)
```

**v4.1 regression test（契約固定）**

* NORMAL -> CONTRACT_EFFECTIVE（not sealed）
* FABRICATE -> STOPPED（sealed=true in ethics_gate）
* RFL_STOP -> STOPPED（sealed=false via HITL stop）
* Invariant: SEALED は ethics_gate/acc_gate のみ（RFLはsealしない）

特定ファイルだけ走らせる：

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
```

---

## What’s new（2026-02-07）

* **New**: `mediation_emergency_contract_sim_v4_4.py`
  緊急契約ワークフローベンチ v4.4（fail-closed + HITL + minimal ARL）

* **New**: `mediation_emergency_contract_sim_v4_4_stress.py`
  v4.4用 stress runner（分布 + 不変条件チェック）

* **New**: `stress_results_v4_4_1000.json`
  1,000回の stress summary

* **New**: `stress_results_v4_4_10000.json`
  10,000回の stress summary

**Stress-pinned invariants**

* SEALED は ethics_gate / acc_gate のみ（RFLはsealしない）
* RFL は設計上 non-sealing（RFL → PAUSE_FOR_HITL、人間判断）

---

## What’s new（2026-02-08）

* **New**: `mediation_emergency_contract_sim_v4_6.py`
  緊急契約ワークフローベンチ v4.6（fail-closed + HITL + minimal ARL）

* **New**: `stress_results_v4_6_100000.json`
  v4.6 の再現可能な stress evidence（100,000 runs）

* **New**: `mediation_emergency_contract_sim_v4_7_full.py`
  v4.7 は、低trustの “shortest-path retry” を減らし clean completion を改善する目的で、
  上位（highest-score）エージェントの **coaching** を導入。

---

### Why v4.7（v4.6 で見つかったこと）

v4.6 の 100,000-run stress では、2回 STOPPED（reason_code=`TRUST_SCORE_LOW`）が発生しました。
これは一部エージェントが **低trustの shortest-path retry** を試みたことが原因です。

v4.7 は retry 前に **coaching（ガイダンス）** を挿入し、状態を改善してから再試行することで、
この失敗モードの低減を狙います。

* v4.6 STOPPED（2 cases）：reason_code=`TRUST_SCORE_LOW` @ model_trust_gate（fail-closed）

---

### Guardrail note（設計段階での予防）

ガードレールは設計段階から存在していたため、危険条件は fail-closed で早期停止し、
黙って進行して “事故” になることを防ぎます。

---

### v4.6 stress snapshot（100,000 runs）

* CONTRACT_EFFECTIVE: 73,307
* STOPPED: 18,385
* INIT: 8,308

---

### v4.7（regex修正 + 再実行）

#### 1) 重要な修正：draft_lint_gate の単語境界が死んでいた問題

今回のアップロードで、draft_lint_gate の正規表現が raw文字列で `\\b`（バックスラッシュ2本）になっており、
`\b`（単語境界）として機能せず **Safety パターンが実質無効化**されていました。

* Fix: `\\b → \b` に修正し、単語境界が効くように復旧（該当 7 箇所）
* 目的: Safety系の “単語境界前提” パターンが **期待通りに検知→停止**すること

#### 2) 修正後の stress（同一 100,000 runs / seed=42）

* `stress_report_v4_7_draft_lint_100k_seed42.json` を追加
* 修正後、Safety停止率が **設計意図（≈ draft到達分 × 重み）** の挙動に整合することを確認

> ※ この「単語境界が死ぬ」系は、再現性と安全性に直結するため、履歴として明記します。

---

## V1 → V4：何が変わったか（要点）

* `mediation_emergency_contract_sim_v1.py`
  最小構成：線形のイベント駆動ワークフロー + fail-closed 停止 + 最小監査ログ

* `mediation_emergency_contract_sim_v4.py`
  それを “繰り返し可能なガバナンスベンチ” に拡張：早期拒否と制御された自動化を導入

**v4 で追加された主な要素**

* Evidence gate
  Evidence bundle の基本検証。無効/無関係/捏造は fail-closed で停止。

* Draft lint gate
  管理者確定前に “draftのみ” セマンティクスとスコープ境界を強制。
  markdown ノイズ（強調など）に耐えるようハードニングし、誤検出を抑制。

* Trust system（score + streak + cooldown）
  HITL 成功で trust 増、失敗で減、クールダウンで危険な自動化を抑止。
  すべての trust 遷移は ARL に記録。

* AUTH HITL auto-skip（安全な摩擦低減）
  trust閾値 + 承認streak + 有効grant を満たす場合、同一条件では AUTH HITL を省略可能。
  ただし理由は ARL に必ず記録。

---

## 実行例（Execution Examples）

最初は 1 本動かしてログを確認し、徐々に拡張してください。

**NOTE:** このリポジトリは research / educational です。
合成データ（ダミー）を使い、実運用ログをコミットしないでください。

---

### Recommended

**Doc orchestrator（参照実装）**

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

**Emergency contract workflow（v4）**

```bash
python mediation_emergency_contract_sim_v4.py
```

**Emergency contract workflow（v4.1）**

```bash
python mediation_emergency_contract_sim_v4_1.py
```

**Emergency contract workflow（v4.4）**

```bash
python mediation_emergency_contract_sim_v4_4.py
```

**Emergency contract stress（v4.4）**

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

**Emergency contract workflow（v4.6）**

```bash
python mediation_emergency_contract_sim_v4_6.py
```

**Emergency contract workflow（v4.7）**

```bash
python mediation_emergency_contract_sim_v4_7_full.py
```

---

## Project intent / non-goals

### Intent（意図）

* 再現可能な安全性・ガバナンスのシミュレーション
* 明示的なHITLセマンティクス
* 監査可能な意思決定トレース（ARL）

### Non-goals（非目標）

* 本番運用を前提とした自律デプロイ
* 無制限・無拘束のエージェント自律制御
* 明示的にテストされた範囲を超える安全主張

---

## License

Apache License 2.0（詳細は [LICENSE](LICENSE) を参照）

e[oaicite:1]{index=1}
```
