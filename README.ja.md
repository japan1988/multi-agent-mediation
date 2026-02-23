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

> **目的（研究・教育）**  
> これは研究／教育目的の参照実装（プロトタイプ）です。**有害な行為の実行や助長**（例：不正侵入、監視、なりすまし、破壊、データ窃取など）、
> あるいは利用するサービスや実行環境の **利用規約／ポリシー、法令、社内規則** に違反する用途に使用しないでください。  
> 本プロジェクトは **教育・研究および防御的検証**（例：ログ肥大の緩和、fail-closed + HITL の挙動検証）に焦点を当てており、
> **攻撃手法の公開**や不正行為の支援を目的としていません。  
> 利用は自己責任です。関連する **規約／ポリシー** を確認し、まずは **隔離された環境でのローカルスモークテスト**（外部ネットワークなし、実データ／実システムなし）から開始してください。  
> 本コード・ドキュメント・生成物（例：zip バンドルを含む）は **現状有姿（AS IS）** で提供され、**いかなる保証もありません**。適用法令で認められる最大限の範囲において、作者は使用・生成物・第三者の悪用等に起因する一切の損害について **責任を負いません**。  
> 同梱の **コードブック（codebook）はデモ／参照用成果物**です。**そのまま実運用に使わず**、要件・脅威モデル・規約／ポリシーに基づき **自作**してください。  
> **テスト／結果に関する注意**：スモークテストやストレス実行は、特定の条件下で実行したシナリオのみを検証します。実運用における **正しさ・安全性・セキュリティ・適合性** を保証しません。OS／Python／ハードウェア／設定／運用条件により結果は変動します。

---

## 概要

Maestro Orchestrator は **研究／教育目的** のオーケストレーション・フレームワークで、以下を優先します。

- **Fail-closed**  
  不確実・不安定・高リスクなら、黙って続行しない。

- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な場面は明示的にエスカレーションする。

- **トレーサビリティ**  
  判断フローを監査可能にし、最小 ARL ログで再現可能にする。

本リポジトリには、**参照実装（doc orchestrator）** と、交渉／調停／ガバナンス風ワークフロー、
およびゲーティング挙動の **シミュレーションベンチ**が含まれます。

---

## 最新更新（このリポジトリで何が変わったか）

この更新では、緊急契約シミュレータの **パッケージ zip バンドル**を追加しました。

- **追加:** `docs/mediation_emergency_contract_sim_pkg.zip`（v5.1.2 便利バンドル）
- **目的:** 再現可能なスモーク／ストレス実行（seed 固定）を、エントリポイントを変えずに素早く試せるようにする
- **正（canonical）な参照元:** root のシミュレータスクリプト + テスト  
  - `mediation_emergency_contract_sim_v5_1_2.py`  
  - `pytest -q tests/test_v5_1_codebook_consistency.py`
- **CI 影響:** なし（docs 成果物。エントリポイントではない）
- **注意:** zip は生成物／利便性のための成果物であり、ロジックの正本ではありません（レビュー可能な証跡として扱う）

---

## クイックスタート（推奨導線）

**再現性＋契約テストの観点で v5.1.x を推奨。v4.x はレガシー安定ベンチとして維持します。**

まずは 1 本のスクリプトで挙動とログを確認し、必要に応じて広げます。

### 1) 推奨：緊急契約シミュレータ（v5.1.2）を実行

> 便利バンドル（任意）：`docs/mediation_emergency_contract_sim_pkg.zip`（ただし正本は root スクリプト + テスト）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テストを実行（v5.1.x：シミュレータ + codebook 整合）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモ codebook を確認／固定（v5.1-demo.1）

* `log_codebook_v5_1_demo_1.json`（デモ codebook。成果物交換時はバージョンを固定）
* 注意：codebook はログ項目の **圧縮エンコード／デコード**用であり、**暗号ではありません**（機密性は提供しません）。

### 4) 任意：レガシー安定ベンチ（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意：証拠バンドル（v4.8 生成物）を確認

* `docs/artifacts/v4_8_artifacts_bundle.zip`

> 証拠バンドル（zip）はテスト／実行から生成される成果物です。
> 正本（canonical）はジェネレータスクリプト + テストです。

---

## ストレステスト（安全デフォルト）

`v5.1.2` はデフォルトでメモリ爆発を避ける設計です。

* **集計のみモード**（`keep_runs=False` がデフォルト）：全 run の結果をメモリ保持しない
* 任意：**異常 run のみ ARL 保存**（`INC#...` のインシデント索引）

### A) 軽いスモーク → 中程度ストレス（推奨ランプ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) インシデントを意図的に発生（例：fabricate-rate 10% を 200 run）

有効化している場合、異常 run が起きると `INC#` ファイル群が生成されます。

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

出力（異常 run が発生した場合）：

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（インシデント ARL）
* `arl_out/incident_index.jsonl`（1 行＝1 インシデント）
* `arl_out/incident_counter.txt`（永続カウンタ）

Tip：`--max-arl-files` でディスク増加を抑制できます。

---

## アーキテクチャ（概要）

監査可能で fail-closed な制御フロー：

`agents`
→ `mediator`（risk / pattern / fact）
→ 証拠検証
→ HITL（pause / reset / ban）
→ 監査ログ（ARL）

---

## アーキテクチャ（コード整合図）

以下の図は現行コードの語彙に合わせています。
状態遷移とゲート順序を分離し、監査性と誤解耐性を保ちます。

ドキュメントのみ。ロジック変更はありません。

### 1) 状態機械（コード整合）

<p align="center">
  <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720">
</p>

主要実行パス：

* `INIT`
* → `PAUSE_FOR_HITL_AUTH`
* → `AUTH_VERIFIED`
* → `DRAFT_READY`
* → `PAUSE_FOR_HITL_FINALIZE`
* → `CONTRACT_EFFECTIVE`

注記：

* `PAUSE_FOR_HITL_*` は HITL の明示的な判断点（ユーザー承認／管理者承認）です。
* `STOPPED (SEALED)` に到達する条件：

  * 無効または捏造された証拠
  * 認可期限切れ
  * draft lint 失敗
* `SEALED` 停止は fail-closed で、設計上オーバーライド不可です。

### 2) ゲート・パイプライン（コード整合）

<p align="center">
  <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720">
</p>

注記：

* これは **状態遷移ではなくゲート順序**を表します。
* `PAUSE` は HITL 必須（人間判断待ち）です。
* `STOPPED (SEALED)` は非回復の安全停止です。

設計意図：

* 状態機械は「どこで止まる／待つか」を答える
* ゲートパイプラインは「どの順序で評価するか」を答える
* 分離することで曖昧性を避け、監査可能なトレースを維持します。

---

## v5.0.1 → v5.1.2：何が変わったか（差分）

README向け要約：

`v5.1.2` は大量 run 安定性と、異常時のみの永続化を強化します。

### 既定で「索引 + 集計のみ」

* `--runs` が大きくてもメモリ爆発しない（runごとの結果を保持しない）
* 出力はカウンタ + HITL サマリ中心（必要なら items を出す）

### インシデント索引（任意）

* 異常 run に `INC#000001...` を付与
* 異常 ARL を `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` として保存
* `{arl_out_dir}/incident_index.jsonl` に索引を追記
* `{arl_out_dir}/incident_counter.txt` に永続カウンタを保存

### 継続して保持される要素

* 異常時のみ ARL 永続化（pre-context + incident + post-context）
* 改ざん検知（デモキーによる ARL ハッシュチェイン）
* fabricate-rate 混在 + seed による再現性（`--fabricate-rate` / `--seed`）

コア不変条件：

* `sealed` は `ethics_gate` / `acc_gate` のみが設定可能
* `relativity_gate` は封印しない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

---

## V1 → V4：概念的に何が変わったか

`mediation_emergency_contract_sim_v1.py` は最小パイプライン（線形・イベント駆動・fail-closed・最小監査ログ）を示します。

`mediation_emergency_contract_sim_v4.py` はそれを繰り返し可能なガバナンス・ベンチへ拡張し、早期拒否と制御された自動化を追加します。

v4 で追加：

* 証拠ゲート（無効／無関係／捏造で fail-closed 停止）
* draft lint ゲート（draft のみ／スコープ境界）
* 信頼システム（score + streak + cooldown）
* 認可HITLの自動スキップ（信頼 + grant による安全な摩擦低減、ARL理由付き）

---

## V4 → V5：概念的に何が変わったか

v4 は「緊急契約」ベンチをスモーク／ストレスで安定化。
v5 はそれを成果物レベルの再現性と契約テスト（互換性検証）へ拡張します。

v5 で追加／強化：

* ログ codebook（デモ）＋契約テスト
  pytest により出力語彙（layer/decision/final_decider/reason_code など）を固定。
* 再現性の表面を固定（pin すべき要素を明確化）
  シミュレータ版・テスト版・codebook 版を固定。
* 不変条件の強制
  テスト／契約によりサイレントなドリフトを抑止。

v5 でも変わらない点：

* 研究／教育目的
* fail-closed + HITL のセマンティクス
* 合成データのみ、隔離環境で実行
* セキュリティ保証なし（codebook は暗号ではない／テストは実運用安全性を保証しない）

---

## 実行例

### Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

### 緊急契約（推奨：v5.1.2）＋契約テスト

```bash
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 緊急契約（レガシー安定ベンチ：v4.8）

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 緊急契約（v4.4 ストレス）

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## 目的／非目的

目的：

* 再現可能な安全・ガバナンス系シミュレーション
* 明示的 HITL（pause/reset/ban）
* 監査可能な判断トレース（最小 ARL）

非目的：

* 本番運用レベルの自律展開
* 無制限な自己指向エージェント制御
* 実運用に対する安全性主張（明示的にテストした範囲を超える保証）

---

## データ／安全メモ

* 合成／ダミーデータのみを使用。
* 実行ログはなるべくコミットしない（証拠成果物は最小かつ再現可能に）。
* 生成バンドル（zip）はレビュー可能な証跡であり、正本ではない。

---

## ライセンス

Apache License 2.0（[LICENSE](LICENSE) を参照）
