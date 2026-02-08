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

Maestro Orchestrator は **研究 / 教育用途** のオーケストレーション・フレームワークです。重視するのは次の3点です：

- **Fail-closed（フェイルクローズ）**  
  不確実・不安定・危険があるなら → 黙って続行しない。
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な箇所は明示的にエスカレーションする。
- **Traceability（追跡可能性）**  
  意思決定フローは最小ARLログで監査可能・再現可能にする。

このリポジトリには **実装リファレンス（doc orchestrators）** と、
交渉・仲裁・ガバナンス風ワークフロー・ゲーティング挙動を検証する **シミュレーションベンチ** が含まれます。

---

## Architecture（高レベル）

監査可能で fail-closed な制御フロー：

agents  
→ mediator（risk / pattern / fact）  
→ evidence verification  
→ HITL（pause / reset / ban）  
→ audit logs（ARL）

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合は、  
> `docs/architecture_unknown_progress.png` が同一ブランチに存在するか、ファイル名の大文字小文字が一致しているか（case-sensitive）を確認してください。

---

## Architecture（コード整合図）

以下の図は **現行コードと用語に完全整合** しています。  
監査性と曖昧性排除のため、**状態遷移** と **ゲート順序** を意図的に分離しています。

この図は **ドキュメントのみ** であり、**ロジック変更は一切ありません**。

---

### 1) State Machine（コード整合）

実行が **HITLで停止（PAUSE）** する箇所、  
または **SEALEDで恒久停止（STOPPED）** する箇所を最小状態遷移として示します。

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

- `PAUSE_FOR_HITL_*` は **Human-in-the-Loop** の意思決定点（ユーザー承認 / 管理者承認）を表します。
- `STOPPED (SEALED)` は次の条件で到達します：
  - 不正 / 捏造を含む evidence
  - 認可（authorization）の期限切れ
  - draft lint の失敗
- **SEALED 停止は fail-closed であり、設計上 override 不可です。**

---

### 2) Gate Pipeline（コード整合）

状態遷移とは独立に、評価ゲートの **順序** を表します。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

- この図は **ゲート順序** を示すもので、状態遷移ではありません。
- `PAUSE` は **HITLが必要**（人間の判断待ち）を意味します。
- `STOPPED (SEALED)` は **非回復の安全停止** を意味します。

**Design intent**

- **State Machine** は「どこで停止/中断するか？」に答える
- **Gate Pipeline** は「どの順で判断するか？」に答える

分離することで曖昧性が減り、監査可能性が保たれます。

**Maintenance note**

画像が表示されない場合：
- `docs/` 配下に存在するか確認
- ファイル名の大文字小文字を含めて一致しているか確認（case-sensitive）
- リンク更新時はファイル一覧からコピペ推奨

---

## What’s new（2026-01-21）

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  unknown progress シナリオ（HITL/RESET）用シミュレータ
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  v1.7-IEP 整合：RFL relcode 分岐（RFLは非封印→HITLへ）
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  post-HITL の意味論を反映して更新

---

## What’s new（2026-02-03）

**イベント駆動のガバナンス風ワークフロー** を導入（fail-closed + HITL + audit-ready）

- **New**: `mediation_emergency_contract_sim_v1.py`  
  最小の緊急ワークフロー：

  USER auth → AI draft → ADMIN finalize → contract effective

  不正 / 期限切れイベントは fail-closed で停止し、最小ARL（JSONL）を出力。

- **New**: `mediation_emergency_contract_sim_v4.py`  
  v1を拡張：
  - evidence gate
  - draft lint gate
  - trust / grant による HITL 摩擦低減

---

## What’s new（2026-02-05）

- **New**: `mediation_emergency_contract_sim_v4_1.py`  
  v4.1 は v4.0 の **挙動を契約として固定** する tightening 版（期待値を明示しコード整合）

  - **RFLは非封印**  
    境界不安定は `PAUSE_FOR_HITL`（`sealed=false` / `overrideable=true`）で人間判断へ。

  - **Fabricationは早期検知、封印は ethics のみ**  
    捏造は evidence でフラグされるが、**封印停止** は `ethics_gate` のみが発行（`sealed=true`）。

  - **trust/grant の摩擦低減は維持**  
    条件成立時のAUTH auto-skip を維持しつつ、ARLに理由を記録。

  **Quick run**
  ```bash
  python mediation_emergency_contract_sim_v4_1.py
Expected

NORMAL -> CONTRACT_EFFECTIVE

FABRICATE -> STOPPED（sealed=true in ethics_gate）

RFL_STOP -> STOPPED（sealed=false via HITL stop）

v4.1 regression test
v4.1の挙動を契約として固定するpytest：

NORMAL -> CONTRACT_EFFECTIVE（not sealed）

FABRICATE -> STOPPED（sealed=true in ethics_gate）

RFL_STOP -> STOPPED（sealed=false via HITL stop）

Invariant：SEALEDは ethics_gate/acc_gate のみ（RFLは封印しない）

単体実行：

bash

pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
What’s new（2026-02-07）
New: mediation_emergency_contract_sim_v4_4.py
緊急契約ワークフローベンチ v4.4（fail-closed + HITL + minimal ARL）

New: mediation_emergency_contract_sim_v4_4_stress.py
v4.4 ストレス実行（分布 + invariant 検証）

New: stress_results_v4_4_1000.json
ストレス結果（1,000回）

New: stress_results_v4_4_10000.json
ストレス結果（10,000回）

Stress-pinned invariants

SEALED は ethics_gate / acc_gate のみ（RFLは封印しない）

RFLは非封印（RFL→PAUSE_FOR_HITL、人間が決める）

What’s new（2026-02-08）
New: mediation_emergency_contract_sim_v4_6.py
緊急契約ワークフローベンチ v4.6（fail-closed + HITL + minimal ARL）

New: stress_results_v4_6_100000.json
v4.6 の再現可能ストレス証跡（100,000回）

New: mediation_emergency_contract_sim_v4_7_full.py
v4.7 は、低信頼状態での「最短ルート（shortest-path）リトライ」を減らし、
clean completion を上げるために 最上位（最高スコア）エージェントによる指導（coaching） を導入。

Why v4.7（v4.6で見つかった点）

v4.6 のストレスで、低信頼スコア状態のエージェントが最短ルートを狙ってリトライし、
その結果 2件 STOPPED となる挙動が観測されました。
v4.7 は指導（coaching）により、リトライ前に状態改善が見込まれ、この失敗モード低減を狙います。

v4.6 STOPPED（2件）：reason_code=TRUST_SCORE_LOW @ model_trust_gate（fail-closed）

ガードレール（設計段階での事故予防）

ガードレールは設計段階から入っていたため、不安全条件は 早期にfail-closedで停止し、
黙って続行して事故化することを未然に防げました。

v4.6 stress snapshot（100,000回）
CONTRACT_EFFECTIVE：73,307

STOPPED：18,385

INIT：8,308

v4.7 のストレス結果は後日公開（同フォーマット）

V1 → V4：実際に何が変わったか
mediation_emergency_contract_sim_v1.py は 最小パイプライン：
線形のイベント駆動ワークフロー + fail-closed 停止 + 最小監査ログ。

mediation_emergency_contract_sim_v4.py はそれを
繰り返し可能なガバナンス・ベンチ にする（早期reject + 制御された自動化）ための拡張。

v4で追加
Evidence gate
evidence bundle の基本検証。不正・無関係・捏造は fail-closed。

Draft lint gate
draft-only とスコープ境界を強制。ノイズ耐性を上げ誤検知を抑える。

Trust system（score + streak + cooldown）
成功で上がり、失敗で下がる。cooldown で危険な自動化を抑制。遷移はARLに記録。

AUTH HITL auto-skip（安全な摩擦低減）
trust閾値 + 承認streak + grant が成立した場合のみ、同一条件のAUTH HITLをスキップし、理由をARLへ。

要するに

V1：「最小監査ログでfail-closedを成立させられるか？」

V4：「監査性を落とさずスケールして反復運用できるか？」

⚙️ Execution Examples（実行例）
まずは 1本だけ 動かして挙動とログを確認し、次に広げてください。

NOTE：本リポジトリは 研究 / 教育用途 です。
ダミーデータ を使い、実行時ログはコミットしないでください。

Recommended
Doc orchestrator（リファレンス）
bash

python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract workflow（v4）
bash

python mediation_emergency_contract_sim_v4.py
Emergency contract workflow（v4.1）
bash

python mediation_emergency_contract_sim_v4_1.py
Emergency contract workflow（v4.4）
bash

python mediation_emergency_contract_sim_v4_4.py
Emergency contract stress（v4.4）
bash

python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
Emergency contract workflow（v4.6）
bash

python mediation_emergency_contract_sim_v4_6.py
Emergency contract workflow（v4.7）
bash

python mediation_emergency_contract_sim_v4_7_full.py
Project intent / non-goals（意図 / 非目標）
Intent（意図）
再現可能な安全・ガバナンスシミュレーション

明示的なHITL意味論

監査可能な意思決定トレース

Non-goals（非目標）
本番環境での自律運用

無制限な自己指向エージェント制御

テストで明示された範囲を超える安全性主張

License（ライセンス）
Apache-2.0. 詳細は LICENSE を参照。
