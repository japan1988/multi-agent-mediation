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

Maestro Orchestrator は **研究／教育用途**のオーケストレーション・フレームワークです。優先する設計原則は以下です。

- **Fail-closed（閉じて安全）**  
  不確実・不安定・リスクあり → 何も言わずに継続しない
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な意思決定は明示的にエスカレーションする
- **トレーサビリティ（追跡可能性）**  
  最小ARLログにより、意思決定フローを監査可能・再現可能にする

本リポジトリには **実装リファレンス（doc orchestrator）** と、交渉／仲裁／ガバナンス風ワークフロー／ゲーティング挙動を検証する **シミュレーションベンチ** が含まれます。

---

## Quickstart（推奨の最短導線）

まずは “1本動かしてログを確認” してから拡張してください。

### 1) 最新の緊急契約シミュレーター（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
````

### 2) ピン留めされた smoke テスト（v4.8）を実行

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 3) 任意：evidence bundle（生成物）を確認

* `docs/artifacts/v4_8_artifacts_bundle.zip`

> 注：zip（evidence bundle）は **テスト／実行によって生成される成果物**です。
> 正（canonical）は “生成スクリプト＋テスト” 側であり、zipはレビュー用証拠束として扱ってください。

---

## アーキテクチャ（高レベル）

監査可能で fail-closed な制御フロー：

agents
→ mediator（risk / pattern / fact）
→ evidence verification
→ HITL（pause / reset / ban）
→ audit logs（ARL）

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合：
> `docs/architecture_unknown_progress.png` が同一ブランチに存在すること、ファイル名の大文字小文字が一致していること（case-sensitive）を確認してください。

---

## アーキテクチャ（コード整合の図）

以下の図は **現在のコード用語に整合**しています。
監査性と曖昧さ排除のため、**状態遷移（State transitions）** と **ゲート順序（Gate order）** を分離しています。

> ドキュメントのみ。ロジック変更はありません。

---

### 1) 状態機械（State Machine / code-aligned）

どこで **PAUSE（HITL）** するか、どこで **STOP（SEALED）** するかを最小の遷移で表します。

<p align="center">
  <img src="docs/architecture_state_machine_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**主経路（Primary execution path）**

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

**補足**

* `PAUSE_FOR_HITL_*` は明示的な **Human-in-the-Loop** 判断点（ユーザー承認／管理者確定）です。
* `STOPPED（SEALED）` は以下で到達します：

  * evidence が無効／捏造
  * 認可（authorization）期限切れ
  * draft lint 失敗
* **SEALED は fail-closed であり、設計上 non-overrideable（上書き不可）です。**

---

### 2) ゲートパイプライン（Gate Pipeline / code-aligned）

評価ゲートの **順序** を示します（状態遷移とは独立）。

<p align="center">
  <img src="docs/architecture_gate_pipeline_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**補足**

* この図は **ゲート順序** を表します（状態遷移ではありません）。
* `PAUSE` は **HITL必須**（人間判断待ち）を意味します。
* `STOPPED（SEALED）` は **回復不能の安全停止** を意味します。

**設計意図**

* **State Machine** が答えること：
  *「どこで止まる／止める（PAUSE/STOP）か」*
* **Gate Pipeline** が答えること：
  *「意思決定をどの順で評価するか」*

分離することで曖昧さを避け、監査可能性を維持します。

**メンテナンス注記**

画像が表示されない場合：

* `docs/` 配下に存在するか
* ファイル名が完全一致しているか（case-sensitive）
* リンク更新時はファイル一覧からコピペ推奨

---

## What’s new（更新情報）

このREADMEは **Quickstart と設計の要点を最短で伝えるために最小構成**に保っています。
詳細な更新履歴（何が追加・変更・修正されたか）は、以下を一次情報として参照してください。

* **Commit history**（最も正確な差分の履歴）
  [https://github.com/japan1988/multi-agent-mediation/commits/main](https://github.com/japan1988/multi-agent-mediation/commits/main)
* **Releases**（節目ごとの要約・配布）
  [https://github.com/japan1988/multi-agent-mediation/releases](https://github.com/japan1988/multi-agent-mediation/releases)

> 方針：トップレベルREADMEのタイムラインは肥大化させず、履歴は commits / releases に集約します。

---

## V1 → V4：何が本質的に変わったか

`mediation_emergency_contract_sim_v1.py` は最小構成：線形イベント駆動のワークフロー＋fail-closed＋最小ARL。

`mediation_emergency_contract_sim_v4.py` はそれを “ガバナンス検証ベンチ” にするため、早期拒否と制御された自動化を追加。

**v4で追加された要素**

* **Evidence gate**
  evidence bundle の基本検証。無効／無関連／捏造は fail-closed で停止。
* **Draft lint gate**
  “ドラフトの範囲” と “スコープ境界” を管理者確定前に強制。
* **Trust system（score + streak + cooldown）**
  HITL結果に応じて trust を更新し、失敗後の危険な自動化を cooldown で抑制。遷移はARLへ。
* **AUTH HITL auto-skip（安全な摩擦低減）**
  trust閾値＋承認streak＋有効grant が揃う場合、同一条件でのAUTH HITLをスキップ可能（理由はARLへ記録）。

---

## 実行例（Execution examples）

**Doc orchestrator（実装リファレンス）**

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

**Emergency contract（v4.8）**

```bash
python mediation_emergency_contract_sim_v4_8.py
```

**Emergency contract（v4.1）**

```bash
python mediation_emergency_contract_sim_v4_1.py
```

**Emergency contract stress（v4.4）**

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## プロジェクトの意図／非目標（Intent / Non-goals）

### Intent

* 再現可能な安全／ガバナンスシミュレーション
* 明示的な HITL セマンティクス（pause/reset/ban）
* 監査可能な意思決定トレース（最小ARL）

### Non-goals

* そのまま本番運用できる自律デプロイ
* 無制限な自己目的化エージェント制御
* 明示テスト範囲を超えた安全性主張

---

## データ／安全メモ（Data & safety notes）

* **合成／ダミーデータのみ**を使用してください。
* 実行ログはコミットしないことを推奨（必要なら再現可能な最小証拠に限定）。
* 生成されたzip（bundle）は **レビュー用証拠束**であり、canonical source ではありません。

---

## License

Apache License 2.0（`LICENSE` を参照）
