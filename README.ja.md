
# 📘 Maestro Orchestrator — オーケストレーションフレームワーク (fail-closed + HITL)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)

> **不確実なら停止。危険ならエスカレーション。**  
> エージェント型ワークフロー向けの研究 / 教育用ガバナンスシミュレーション。

Maestro Orchestrator は、**fail-closed**、**HITL（Human-in-the-Loop）**、**監査可能性** を重視した  
**研究指向のオーケストレーションフレームワーク** です。

このリポジトリは、**ガバナンス / 調停 / 交渉型シミュレーション** と、  
**追跡可能・再現可能・安全性優先のオーケストレーション** の実装リファレンスを扱います。

---

## このリポジトリが何か

このリポジトリは、以下を提供します。

- **ガバナンス型ワークフロー向けの fail-closed + HITL ベンチ**
- **seed 固定実行 + pytest 契約チェック** による再現可能シミュレータ
- **最小 ARL ログ** による監査可能な追跡性
- **オーケストレーション / ゲーティング挙動** のリファレンス実装

このリポジトリは、次のような位置づけで読むのが適切です。

- **研究プロトタイプ**
- **教育用リファレンス**
- **ガバナンス / 安全性シミュレーションベンチ**

**本番運用向けの自律フレームワークではありません。**

---

## クイックリンク

- **英語版 README:** [README.md](README.md)
- **docs 入口:** [docs/README.md](docs/README.md)
- **推奨シミュレータ:** `mediation_emergency_contract_sim_v5_1_2.py`
- **契約テスト:** `tests/test_v5_1_codebook_consistency.py`
- **旧安定ベンチ:** `mediation_emergency_contract_sim_v4_8.py`

---

## ⚡ TL;DR

- **Fail-closed + HITL** による調停 / 交渉スタイルのワークフローベンチ（研究 / 教育用途）
- **再現性優先**: seed 固定実行 + `pytest` による契約チェック（語彙 / 不変条件）
- **監査対応**: 最小 ARL ログ、必要時のみ incident 単位で `INC#...` 保存してログ肥大を回避

---

## ⚠️ 目的と免責（研究 / 教育）

**本リポジトリは研究 / 教育用途の参照実装（プロトタイプ）です。**  
悪用（例: 侵害、侵入、監視、なりすまし、破壊、データ窃取）や、各種サービス / 実行環境の利用規約・ポリシー・法令・内部規程に違反する目的で使用してはいけません。

本プロジェクトは **教育 / 研究** と **防御的検証**（例: ログ肥大の抑制、fail-closed + HITL 挙動の検証）を目的としています。  
攻撃手法の公開や不正行為の支援を目的としたものではありません。

### リスク / 保証 / 責任

- **自己責任で使用してください:** 関連する利用規約 / ポリシーを確認してください。
- **まず隔離環境で:** ローカルのスモークテストから開始してください（外部ネットワークなし、実システム / 実データなし）。
- **現状有姿 / 無保証:** いかなる保証もなく提供されます。
- **責任制限:** 適用法令で認められる最大限の範囲で、コード、文書、生成物の使用から生じる損害（第三者による悪用を含む）について作者は責任を負いません。

### コードブックに関する注意

同梱のコードブックは **デモ / 参照用成果物** です。  
実運用でそのまま使用せず、要件・脅威モデル・適用ポリシー / 利用規約に基づいて自作してください。  
コードブックはログ項目の圧縮表現用であり、**暗号ではありません**（機密性は提供しません）。

### テスト / 結果に関する注意

スモークテストやストレス実行は、特定の実行条件下で実行されたシナリオのみを検証します。  
実運用における正確性、安全性、適合性、目的適合性を保証するものではありません。結果は OS / Python バージョン / ハードウェア / 設定 / 運用条件により変動します。

---

## このリポジトリの目的

Maestro Orchestrator は、次の3点を中心に設計されています。

- **Fail-closed**
  - 不確実・不安定・危険なら、黙って継続しない
- **HITL エスカレーション**
  - 人間判断が必要な決定を明示的に人へ返す
- **追跡可能性**
  - 意思決定フローを最小 ARL ログで再現・監査可能にする

このリポジトリには、以下を対象としたシミュレーションベンチと実装リファレンスが含まれます。

- 交渉
- 調停
- ガバナンス型ワークフロー
- ゲーティング挙動
- 監査指向オーケストレーション

---

## 推奨の読み方 / 触り方

初見なら、次の順で入るのが分かりやすいです。

1. 推奨シミュレータ（`v5.1.2`）を実行
2. 契約テストを実行
3. コードブックとログを確認
4. 必要なら旧安定ベンチ（`v4.8`）と比較

---

## Quickstart

### 1) 推奨の緊急契約シミュレータを実行する（v5.1.2）

任意バンドル: `docs/mediation_emergency_contract_sim_pkg.zip`（利便用のみ）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テストを実行する（v5.1.x: simulator + codebook consistency）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモコードブックを確認 / 固定する（v5.1-demo.1）

* `log_codebook_v5_1_demo_1.json`（デモ用コードブック。成果物交換時はバージョン固定を推奨）
* 注意: コードブックは **暗号ではありません**（機密性なし）

### 4) 任意: 旧安定ベンチを実行する（v4.8）

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意: 証跡バンドルを確認する（v4.8 生成物）

* `docs/artifacts/v4_8_artifacts_bundle.zip`

証跡バンドル（zip）はテスト / 実行で生成される成果物です。
正本はジェネレータスクリプトとテストです。

---

## 最新更新

この更新では、緊急契約シミュレータの zip バンドルを追加しました。

* 追加: `docs/mediation_emergency_contract_sim_pkg.zip`（v5.1.2 利便用バンドル）
* 理由: entrypoint を変えずに、seed 固定の smoke / stress 実行を素早く再現できるようにするため
* 正本（authoritative logic）:

  * `mediation_emergency_contract_sim_v5_1_2.py`
  * `pytest -q tests/test_v5_1_codebook_consistency.py`
* CI 影響: なし（docs 成果物であり entrypoint ではない）
* 注意: zip バンドルは **生成 / 利便用成果物** です（レビュー用証跡であり、正本ロジックではありません）。利用前に確認してください。

### この更新での修正点（旧 draft → 現行）

旧 v5.1.2 draft で見つかった2つのスケール問題を修正しています。

* **incident-only persistence の不一致**

  * 問題: 一部の非 incident イベント（例: evaluation / reward）が FULL ARL 行として強制保存され、正常実行でもログが肥大する可能性があった
  * 修正: evaluation / reward イベントは **SUMMARY** として出力されるよう変更（強制保存なし）。ARL 保存は **incident-only** を維持

* **一意 `run_id` 下での pre-context candidate 増加**

  * 問題: `full_context_n > 0` かつ各 run が一意 `run_id` を使う場合、大規模実行で in-memory candidate buffer が蓄積しうる
  * 修正: 各 run 終了時に per-run candidate buffer を明示的に破棄（`drop_candidates_for_run(run_id)`）

---

## ストレステスト（安全側デフォルト）

v5.1.2 は、デフォルトでメモリ肥大を避ける設計です。

* 集計専用モード（`keep_runs=False` がデフォルト）: 全 run の詳細結果をメモリに保持しない
* 任意で abnormal run のみ ARL 保存（`INC#...` による incident indexing）

### A) 軽量 smoke → 中規模 stress（推奨ランプ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) incident を強制する（例: fabricate-rate 10%, 200 runs）

abnormal run を意図的に発生させ、設定時に `INC#` ファイルを生成します。

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

abnormal run 発生時の出力:

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（incident ARL）
* `arl_out/incident_index.jsonl`（incident 1件につき1行）
* `arl_out/incident_counter.txt`（永続カウンタ）

ヒント: ディスク肥大を防ぐため `--max-arl-files` を設定してください。

---

## 図と docs

すべての図表とバンドルの入口: **[docs/README.md](docs/README.md)**

主な図:

* 緊急契約 overview (v5.1.2): [docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* アーキテクチャ（コード整合版）: [docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* Unknown-progress + HITL 図: [docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* Multi-agent 階層図: [docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* Sentiment context flow: [docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

推奨読書順:

1. この README
2. `docs/README.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/test_v5_1_codebook_consistency.py`

---

## アーキテクチャ（高レベル）

監査可能かつ fail-closed な制御フロー:

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
```

### アーキテクチャ overview（v5.1.2）

文書用図です。ロジック変更はありません。

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### アーキテクチャ（コード整合図）

以下の図は現在のコード語彙に合わせたものです。
文書用図であり、ロジック変更はありません。

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## 実行例

### Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

### 緊急契約（推奨: v5.1.2）+ 契約テスト

```bash
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 緊急契約（旧安定ベンチ: v4.8）

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 緊急契約（v4.4 stress）

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## バージョン差分

### v5.0.1 → v5.1.2

v5.1.2 は、大規模 run 安定性と incident-only persistence を強化しています。

* **デフォルトで index + 集計専用**

  * 全 run の詳細結果をメモリ保持しない（大規模 `--runs` でのメモリ肥大防止）
  * 出力は counters + HITL summary 中心（必要に応じて詳細追加）

* **incident indexing（任意）**

  * abnormal run に `INC#000001...` を付与
  * abnormal ARL を `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` として保存
  * index を `{arl_out_dir}/incident_index.jsonl` に追記
  * 永続カウンタを `{arl_out_dir}/incident_counter.txt` に保存

維持されているもの:

* abnormal-only ARL persistence（pre-context + incident + post-context）
* Tamper-evident ARL hash chaining（OSS デモ用に demo key をデフォルト利用）
* Fabricate-rate mixing + deterministic seeding（`--fabricate-rate` / `--seed`）

中核不変条件:

* `sealed` を設定できるのは `ethics_gate` / `acc_gate` のみ
* `relativity_gate` は絶対に sealed にならない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

### v5.1.2 の実務的安定性改善

上記の挙動面に加え、v5.1.2 ではリポジトリ運用上の安定性も改善しています。

* **永続化処理**

  * Trust / grants / eval store の path 処理と serializer がより一貫化
  * 実行時挙動と保存成果物のズレを減らす

* **テスト互換性**

  * 永続 store path をより一貫して公開し、テストで patch しやすくした
  * CI 分離性と契約 / stress チェックの再現性が向上

* **出力安定性**

  * JSON 出力を UTF-8 / 改行安定 / serializer 安定に寄せた
  * 環境差による不要な差分を減らし、成果物確認をしやすくした

### V1 → V4（概念差分）

`mediation_emergency_contract_sim_v1.py` は、最小構成のパイプラインを示します。
線形・イベント駆動で、fail-closed 停止と最小監査ログを持ちます。

`mediation_emergency_contract_sim_v4.py` は、そのパイプラインを
早期拒否と制御付き自動化を備えた繰り返し可能なガバナンスベンチへ拡張します。

v4 で追加されたもの:

* Evidence gate（無効 / 無関係 / 捏造証拠を fail-closed で停止）
* Draft lint gate（draft-only 意味論とスコープ境界）
* Trust system（score + streak + cooldown）
* AUTH HITL auto-skip（trust + grant による安全な摩擦低減、ARL 理由付き）

### V4 → V5（概念差分）

v4 は、安定した「緊急契約」ガバナンスベンチとして、smoke test と stress runner を中心に構成されています。
v5 は、そのベンチを成果物レベルの再現性と契約互換チェックへ拡張します。

v5 で追加 / 強化されたもの:

* **ログコードブック（demo）+ 契約テスト**
  `layer / decision / final_decider / reason_code` の語彙を pytest で強制

* **再現性 surface（固定すべきものの明示）**
  simulator version、test version、codebook version を pin 可能にする

* **不変条件のより厳密な強制**
  契約テストによって silent drift を減らす

v5 でも変わらないもの:

* 研究 / 教育目的
* Fail-closed + HITL セマンティクス
* synthetic data のみを使用し、隔離環境で実行する前提
* セキュリティ保証はしない（コードブックは暗号ではなく、テストも実運用安全性を保証しない）

---

## プロジェクトの意図 / 非目標

### 意図

* 再現可能な安全性 / ガバナンスシミュレーション
* 明示的な HITL セマンティクス（pause / reset / ban）
* 監査可能な意思決定トレース（最小 ARL）

### 非目標

* 本番グレードの自律運用
* 無制限な自己主導エージェント制御
* 明示テストを超える安全性主張

---

## データ / 安全上の注意

* synthetic / dummy data のみ使用してください
* runtime log はなるべく commit せず、証跡成果物は最小・再現可能に保ってください
* 生成 zip バンドルは、正本ではなくレビュー可能な証跡として扱ってください

---

## ライセンス

Apache License 2.0（`LICENSE` を参照）
