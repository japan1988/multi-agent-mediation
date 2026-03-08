# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)

> **不確実なら止まる。危険ならエスカレーションする。**  
> エージェント型ワークフロー向けの研究・教育用ガバナンスシミュレーション。

Maestro Orchestrator は、**fail-closed**、**HITL（Human-in-the-Loop）**、**監査可能性** を重視した  
**研究指向のオーケストレーション・フレームワーク**です。

このリポジトリは、**ガバナンス / 調停 / 交渉型シミュレーション** と、  
**追跡可能・再現可能・安全性優先のオーケストレーション** を実装参照としてまとめたものです。

シミュレータを実行すると、**再現可能な集計結果、最小ARLトレース、異常時のみの incident-indexed artifact** を出力できます。  
契約テストでは、**固定語彙、ゲート不変条件、fail-closed / HITL continuation の挙動** を確認できます。

---

## このリポジトリで提供するもの

このリポジトリには、以下が含まれます。

- **Fail-closed + HITL のオーケストレーション検証ベンチ**
- **seed 固定で再現可能なシミュレータ** と `pytest` ベースの契約チェック
- **最小 ARL ログ** による監査向けトレース
- **オーケストレーション / ゲーティング挙動の実装参照**

このリポジトリは、次のような位置づけで読むのが適切です。

- **研究用プロトタイプ**
- **教育用リファレンス**
- **ガバナンス / 安全性シミュレーションベンチ**

これは **本番用の自律実行フレームワークではありません**。

---

## クイックリンク

- **英語 README:** [README.md](README.md)
- **ドキュメント索引:** [docs/README.md](docs/README.md)
- **推奨シミュレータ:** `mediation_emergency_contract_sim_v5_1_2.py`
- **契約テスト:** `tests/test_v5_1_codebook_consistency.py`
- **旧安定ベンチ:** `mediation_emergency_contract_sim_v4_8.py`
- **ドキュメント・オーケストレータ（mediator 参照実装）:** `ai_doc_orchestrator_with_mediator_v1_0.py`
- **ドキュメント・オーケストレータ契約テスト:** `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## ⚡ TL;DR

- **Fail-closed + HITL** を前提とした交渉 / 調停系ワークフローの検証ベンチ（研究 / 教育向け）
- **再現性優先**: seed 固定実行 + `pytest` 契約テスト（語彙 / 不変条件）
- **監査向け**: 最小 ARL ログ、必要に応じて `INC#...` 形式の異常時のみ ARL インデックス化
- **ドキュメント系参照実装**: mediator + 固定ゲート順 + 契約テスト済みの HITL continuation semantics

---

## ⚠️ 目的と免責（研究・教育用途）

**これは研究 / 教育用の参照実装（プロトタイプ）です。**  
有害行為（例: 悪用、侵入、監視、なりすまし、破壊、データ窃取）を実行・支援する目的や、利用先サービス・実行環境の規約 / ポリシー / 法令 / 内部ルールに反する用途では使用しないでください。

このプロジェクトは、**教育 / 研究** と **防御的検証**  
（例: ログ肥大の抑制、fail-closed + HITL 挙動の検証）を目的としています。  
**攻撃手法の公開や不正行為の支援を目的としたものではありません。**

### リスク / 無保証 / 責任制限

- **自己責任で使用してください:** 関連する規約・ポリシーは必ず確認してください。
- **まず隔離環境で:** ローカルのスモークテストから開始してください（外部ネットワークなし、実システム / 実データなし）。
- **現状有姿（AS IS） / 無保証:** いかなる保証も付されません。
- **責任制限:** 適用法令で認められる最大限の範囲で、コード・文書・生成物の利用から生じる損害について作者は責任を負いません（第三者による誤用を含む）。

### コードブックに関する注意

同梱のコードブックは **デモ / 参照用アーティファクト** です。  
実運用でそのまま使わず、要件・脅威モデル・適用ポリシー / 規約に応じて自作してください。  
コードブックはログ項目の簡易エンコード / デコード用であり、**暗号ではありません**（機密性はありません）。

### テストと結果に関する注意

スモークテストやストレスランは、その時点の実行条件で走らせたシナリオだけを検証します。  
現実環境での正しさ・安全性・適合性を保証するものではありません。  
結果は OS / Python バージョン / ハードウェア / 設定 / 運用条件により変わり得ます。

---

## このリポジトリを作った理由

Maestro Orchestrator は、次の3つを優先して設計しています。

- **Fail-closed**
  - 不確実・不安定・危険なら、黙って続行しない
- **HITL エスカレーション**
  - 人間の判断が必要な決定を明示的に返す
- **追跡可能性**
  - 決定フローを最小 ARL ログで再現可能・監査可能にする

このリポジトリには、以下のためのシミュレーションベンチと実装参照が含まれます。

- 交渉
- 調停
- ガバナンス型ワークフロー
- ゲーティング挙動
- 監査志向オーケストレーション

---

## 推奨の読み進め方

初見なら、まず次の順で見るのがおすすめです。

1. 推奨シミュレータ `mediation_emergency_contract_sim_v5_1_2.py` を実行する
2. 契約テスト `tests/test_v5_1_codebook_consistency.py` を実行する
3. 生成されたログ、コードブック、必要なら incident artifact を確認する
4. その後、必要に応じて `mediation_emergency_contract_sim_v4_8.py` と比較する
5. より小さい固定順序の参照実装として `ai_doc_orchestrator_with_mediator_v1_0.py` を確認する

---

## Quickstart

### 1) 推奨の緊急契約シミュレータ（v5.1.2）を実行

任意の便利パッケージ: `docs/mediation_emergency_contract_sim_pkg.zip`  
（利便性のための zip であり、正本ではありません）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テストを実行（v5.1.x: simulator + codebook consistency）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモコードブックを確認 / 固定（v5.1-demo.1）

* `log_codebook_v5_1_demo_1.json`
  （デモ用コードブック。artifact をやり取りする場合はバージョン固定を推奨）
* 注意: コードブックは **暗号ではありません**（機密性なし）

### 4) 任意: 旧安定ベンチ（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意: mediator 参照実装の doc orchestrator を実行

```bash
python ai_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
```

### 6) 実行後に見るべきもの

* simulator の標準出力サマリ
* 生成された ARL / audit JSONL トレース
* 異常時のみ保存を有効にした場合の `incident_index.jsonl` と `INC#...` ファイル
* `pytest` 契約テストで固定している語彙 / 不変条件チェック

---

## Latest update

最近の追加・安定化ポイントは次の通りです。

* 推奨シミュレータ向けの便利 zip バンドルを追加

  * `docs/mediation_emergency_contract_sim_pkg.zip`
* doc orchestrator の mediator 参照実装を安定化

  * `ai_doc_orchestrator_with_mediator_v1_0.py`
  * `tests/test_doc_orchestrator_with_mediator_v1_0.py`

正本は引き続き Python のエントリポイントと契約テストです。

---

## ストレステスト（安全寄りの既定値）

v5.1.2 は、既定でメモリ肥大を避けるように設計されています。

* 集計のみモード（既定: `keep_runs=False`）
  実行ごとの完全結果をメモリ保持しない
* 任意で、異常実行のみ ARL 保存
  (`INC#...` 形式の incident indexing)

### A) 軽い smoke → 中程度 stress（推奨ランプ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) incident を強制発生させる例（200 runs / fabricate-rate 10%）

異常実行が発生し、設定時には `INC#` ファイルが生成されます。

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

異常が発生した場合の出力:

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl` （incident ARL）
* `arl_out/incident_index.jsonl` （incident ごとの1行索引）
* `arl_out/incident_counter.txt` （永続カウンタ）

補足: `--max-arl-files` を設定してディスク増加を抑えるのを推奨します。

---

## 図とドキュメント

すべての図とバンドルは **[docs/README.md](docs/README.md)** から参照できます。

主な図:

* Emergency contract overview (v5.1.2): [docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* Architecture (code-aligned): [docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* Unknown-progress + HITL diagram: [docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* Multi-agent hierarchy: [docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* Sentiment context flow: [docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

おすすめの読み順:

1. この README
2. `docs/README.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/test_v5_1_codebook_consistency.py`
5. `ai_doc_orchestrator_with_mediator_v1_0.py`
6. `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## アーキテクチャ（概要）

監査可能・fail-closed な制御フロー:

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
```

### アーキテクチャ概要（v5.1.2）

文書説明用です。ロジック変更はありません。

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### アーキテクチャ図（コード整合版）

以下の図は、現在のコード語彙に合わせています。
文書説明用であり、ロジック変更はありません。

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## バージョン差分

### v5.0.1 → v5.1.2

v5.1.2 は、大規模実行での安定性と incident-only persistence を強化しています。

* **既定で index + aggregation-only**

  * `--runs` が大きくても、実行単位の結果をメモリに保持しない
  * 出力は counters + HITL summary 中心（必要に応じて items）

* **incident indexing（任意）**

  * 異常実行に `INC#000001...` を付与
  * 異常 ARL を `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` に保存
  * 索引を `{arl_out_dir}/incident_index.jsonl` に追記
  * 永続カウンタを `{arl_out_dir}/incident_counter.txt` に保存

引き続き維持されるもの:

* 異常時のみの ARL 保存（pre-context + incident + post-context）
* 改ざん検知向け ARL hash chain（OSS デモでは demo key を既定使用）
* fabricate-rate 混合と seed による決定的再現 (`--fabricate-rate` / `--seed`)

主要な不変条件:

* `sealed` を設定できるのは `ethics_gate` / `acc_gate` のみ
* `relativity_gate` は封印されない
  （`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

### v5.1.2 の実用上の安定化ポイント

上記の挙動変更に加えて、v5.1.2 はリポジトリ運用上の安定性も改善しています。

* **永続化処理**

  * Trust / grants / eval store の path handling と serialization をより一貫化
  * 実行時挙動と保存成果物の不一致を減らす

* **テスト互換性**

  * 永続ストアの path をテスト側からより扱いやすく
  * CI の分離性と再現性を改善

* **出力安定性**

  * JSON 出力を UTF-8 / 改行安定 / serializer 安定 に寄せた
  * 環境差による不要差分を減らし、artifact を比較しやすくした

### Doc orchestrator mediator reference (v1.0)

`ai_doc_orchestrator_with_mediator_v1_0.py` は、より小さい参照実装で、主に次を対象とします。

* 固定ゲート順
* 停止権限を持たない mediator advice
* 明示的な HITL continuation handling
* サニタイズ済みの監査向け JSONL トレース
* 契約テスト済みのオーケストレーション語彙

これは、大きな emergency-contract bench 系の置き換えではなく、
監査指向オーケストレーションのコンパクトな実装例です。

### V1 → V4（概念）

`mediation_emergency_contract_sim_v1.py` は最小パイプラインを示します。
線形でイベント駆動のフローに、fail-closed stop と最小 audit log を備えた形です。

`mediation_emergency_contract_sim_v4.py` は、それを繰り返し可能な governance bench に拡張し、早期拒否と制御付き自動化を導入します。

v4 で追加されたもの:

* Evidence gate
  （無効 / 無関係 / fabricate evidence で fail-closed stop）
* Draft lint gate
  （draft-only semantics と scope boundary）
* Trust system
  （score + streak + cooldown）
* AUTH HITL auto-skip
  （trust + grant による安全寄り friction reduction と ARL reason）

### V4 → V5（概念）

v4 は安定した “emergency contract” governance bench として smoke / stress を重視しています。
v5 はそこから、artifact-level reproducibility と contract-style compatibility checks を強化します。

v5 で追加 / 強化されたもの:

* **Log codebook（demo） + contract tests**
  `layer / decision / final_decider / reason_code` の語彙を pytest で固定

* **再現性の固定面を拡大**
  simulator version、test version、codebook version を固定

* **不変条件のより明示的な強化**
  invariant に対するテスト / 契約で silent drift を減らす

v5 でも変わっていないこと:

* 研究 / 教育目的
* Fail-closed + HITL の意味論
* synthetic data のみを使い、隔離環境で実行する前提
* 安全保証はしない
  （コードブックは暗号ではなく、テストも現実環境の安全性を保証しない）

---

## プロジェクトの目的 / 非目的

### 目的

* 再現可能な安全性 / ガバナンスシミュレーション
* 明示的な HITL semantics（pause / reset / ban）
* 監査向け decision trace（最小 ARL）

### 非目的

* 本番向け自律運用
* 無制限の自己指向エージェント制御
* 明示的にテストされていない安全性主張

---

## データと安全性に関する注意

* synthetic / dummy data のみを使用してください
* 実行ログはなるべくコミットせず、evidence artifact は最小かつ再現可能に保ってください
* 生成された zip バンドルは、正本ではなく reviewable evidence として扱ってください

---

## ライセンス

Apache License 2.0（`LICENSE` を参照）
