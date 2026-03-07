# 📘 Maestro Orchestrator — オーケストレーションフレームワーク（fail-closed + HITL）

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml)

> **不確実なら停止。危険ならエスカレーション。**  
> エージェント型ワークフローのための研究・教育用ガバナンスシミュレーション。

---

## ⚠️ 目的と免責（研究・教育用途）

**これは研究・教育用の参照実装（プロトタイプ）です。**  
有害な行為（例: 悪用、侵入、監視、なりすまし、破壊、データ窃取）を実行・支援する目的や、利用するサービス・実行環境の規約/ポリシー、法令、内部ルールに違反する目的で使用しないでください。

このプロジェクトは、**教育・研究** および **防御的検証**（例: ログ肥大の抑制、fail-closed + HITL 挙動の検証）に焦点を当てています。  
**攻撃手法の公開や不正行為の支援を目的としたものではありません。**

### リスク / 無保証 / 責任制限

- **自己責任で使用してください:** 関連する規約・ポリシーを確認してください。
- **まず隔離環境で:** ローカルのスモークテストから開始してください（外部ネットワークなし・実システム/実データなし）。
- **現状有姿 / 無保証:** いかなる種類の保証もなく提供されます。
- **責任制限:** 適用法令の許す最大限の範囲で、コード・ドキュメント・生成物の使用により生じる損害（第三者による悪用を含む）について、作者は責任を負いません。

### コードブックに関する注意

同梱されているコードブックは **デモ / 参照用アーティファクト** です。実運用でそのまま使わず、要件・脅威モデル・適用されるポリシー / 規約に基づいて自作してください。  
このコードブックはログ項目の圧縮エンコード / デコード用であり、**暗号ではありません**（機密性は提供しません）。

### テストと結果に関する注意

スモークテストやストレスランは、特定の実行条件下で実行されたシナリオのみを検証します。  
それらは、実運用における正確性・安全性・セキュリティ・特定用途適合性を保証するものではありません。結果は OS / Python バージョン、ハードウェア、設定、運用方法により変わる可能性があります。

---

🇺🇸 **English version:** [README.md](README.md)

## ⚡ 要約
- **Fail-closed + HITL** を前提にした、交渉 / 調停系ワークフロー向けの研究・教育用ベンチ。
- **再現性重視**: seed 固定実行 + `pytest` 契約チェック（語彙 / 不変条件）。
- **監査しやすい構造**: 最小 ARL ログ、必要に応じて incident-only ARL indexing（`INC#...`）でログ肥大を回避。

---

## 概要

Maestro Orchestrator は、次を優先する研究・教育用オーケストレーションフレームワークです。

- **Fail-closed**  
  不確実・不安定・危険なら、黙って続行しない。
- **HITL (Human-in-the-Loop)**  
  人間の判断が必要な決定は明示的にエスカレーションする。
- **追跡可能性**  
  最小 ARL ログにより、判断フローを監査しやすく、再現可能にする。

このリポジトリには、実装リファレンス（doc orchestrators）と、交渉・調停・ガバナンス系ワークフローおよびゲーティング挙動のシミュレーションベンチが含まれます。

---

## 最新更新（このリポジトリで何が変わったか）

今回の更新では、emergency contract simulator 用の zip バンドルを追加しました。

- 追加: `docs/mediation_emergency_contract_sim_pkg.zip`（v5.1.2 用の convenience bundle）
- 目的: エントリポイントを変えずに、再現可能な smoke / stress run（seed 固定）を素早く試せるようにするため
- 正式なソース・オブ・トゥルース（権威あるロジック）:
  - `mediation_emergency_contract_sim_v5_1_2.py`
  - `pytest -q tests/test_v5_1_codebook_consistency.py`
- CI への影響: なし（docs アーティファクトであり、エントリポイントではない）
- 注意: zip バンドルは **生成物 / 利便用アーティファクト** です（レビュー可能な証跡であり、権威あるロジックそのものではありません）。使用前に内容を確認してください。

### 今回の更新での修正点（旧 draft → 現在版）

今回の更新では、以前の v5.1.2 draft に見つかった2つのスケール上の問題を修正しています。

- **incident-only persistence の不整合**
  - 問題: 一部の非インシデントイベント（例: evaluation / reward）が FULL ARL rows として強制保存され、正常 run でもログが膨らむ可能性があった。
  - 修正: evaluation / reward イベントは **SUMMARY** として emit するよう変更（強制保存なし）。ARL persistence は引き続き **incident-only**。

- **一意な `run_id` における pre-context candidate の蓄積**
  - 問題: `full_context_n > 0` かつ各 run が一意な `run_id` を使う場合、in-memory candidate buffer が大量 run で蓄積し得た。
  - 修正: 各 run の終了時に per-run candidate buffer を明示的に破棄するようにした（`drop_candidates_for_run(run_id)`）。

---

## Quickstart（推奨手順）

v5.1.x は再現性 + 契約チェック向けの推奨版です。v4.x は legacy stable bench として残しています。  
まず1つのスクリプトから始めて、挙動とログを確認してから広げてください。

### 1) 推奨版 emergency contract simulator（v5.1.2）を実行

任意の bundle: `docs/mediation_emergency_contract_sim_pkg.zip`（利便用のみ）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テストを実行（v5.1.x: simulator + codebook consistency）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモコードブック（v5.1-demo.1）を確認 / 固定

* `log_codebook_v5_1_demo_1.json`（デモ用コードブック。アーティファクト交換時はバージョンを固定してください）
* 注意: codebook は **暗号ではありません**（機密性なし）。

### 4) 任意: legacy stable bench（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意: evidence bundle（v4.8 生成アーティファクト）を確認

* `docs/artifacts/v4_8_artifacts_bundle.zip`

Evidence bundle（zip）は tests / runs によって生成されるアーティファクトです。
正式な source of truth は generator scripts と tests です。

---

## ストレステスト（safe-by-default）

v5.1.2 はデフォルトでメモリ肥大を避けるよう設計されています。

* Aggregation-only mode（`keep_runs=False` がデフォルト）: 全 run の詳細結果をメモリに保持しない
* 任意: 異常 run のみ ARL を保存（incident indexing with `INC#...`）

### A) 軽量 smoke → 中程度 stress（推奨ランプアップ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) 強制的にインシデントを発生させる例（200 runs 中 fabricate-rate 10%）

異常 run がある程度確実に発生し、設定時には `INC#` ファイルが生成されます。

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

異常 run 発生時の出力:

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（incident ARL）
* `arl_out/incident_index.jsonl`（incident ごとに1行）
* `arl_out/incident_counter.txt`（永続カウンタ）

ヒント: ディスク増加を抑えるために `--max-arl-files` を使って上限を付けてください。

---

## 図とドキュメント

図やバンドルの一覧: **[docs/README.md](docs/README.md)**

主な図:

* Emergency contract overview (v5.1.2): [docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* Architecture (code-aligned): [docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* Unknown-progress + HITL diagram: [docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* Multi-agent hierarchy: [docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* Sentiment context flow: [docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

---

## アーキテクチャ（高レベル）

監査しやすく fail-closed な制御フロー:

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
```

### アーキテクチャ（overview, v5.1.2）

ドキュメント用。ロジック変更なし。

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### アーキテクチャ（code-aligned diagrams）

以下の図は、現在のコード語彙に合わせています。
ドキュメント用。ロジック変更なし。

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## v5.0.1 → v5.1.2: 何が変わったか（差分）

v5.1.2 は、大規模 runs 時の安定性と incident-only persistence を強化しています。

* **デフォルトで index + aggregation-only**

  * 全 run の詳細結果をメモリに保持しない（大規模 `--runs` でのメモリ肥大を防ぐ）
  * 出力は counters + HITL summary（必要なら optional items）を中心にする

* **Incident indexing（任意）**

  * 異常 run には `INC#000001...` のような incident ID を付与
  * 異常 ARL は `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` に保存
  * Index は `{arl_out_dir}/incident_index.jsonl` に追記
  * 永続カウンタは `{arl_out_dir}/incident_counter.txt` に保存

引き続き維持されるもの:

* 異常時のみの ARL persistence（pre-context + incident + post-context）
* 改ざん検知向け ARL hash chaining（OSS demo では demo key がデフォルト）
* Fabricate-rate mixing + deterministic seeding（`--fabricate-rate` / `--seed`）

コア不変条件:

* `sealed` は `ethics_gate` / `acc_gate` のみが設定可能
* `relativity_gate` は決して sealed されない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

### v5.1.2 における実務的な安定化改善

上記の挙動差分に加えて、v5.1.2 ではリポジトリ全体の安定性も次の3点で改善しています。

* **永続化処理**

  * Trust / grants / eval stores の path handling と serialization をより一貫させた
  * これにより、実行時挙動と保存アーティファクトの不一致を減らした

* **テスト適合性**

  * Persistent store paths をより一貫して exposed し、tests で patch しやすくした
  * これにより、CI 上の isolation が改善され、contract / stress checks の再現性が上がった

* **出力安定性**

  * JSON 出力をより一貫した形にした（UTF-8 / newline-stable / serializer-stable）
  * これにより、環境差による不要な差分を減らし、結果アーティファクトを確認しやすくした

---

## V1 → V4: 実際に何が変わったか（概念）

`mediation_emergency_contract_sim_v1.py` は最小構成のパイプラインを示します。
線形・イベント駆動型のワークフローに、fail-closed stops と最小監査ログを持たせたものです。

`mediation_emergency_contract_sim_v4.py` は、そのパイプラインを repeatable governance bench に進化させ、early rejection と controlled automation を加えています。

v4 で追加されたもの:

* Evidence gate（無効 / 無関係 / fabricated evidence による fail-closed stop）
* Draft lint gate（draft-only semantics と scope boundary）
* Trust system（score + streak + cooldown）
* AUTH HITL auto-skip（trust + grant による安全な friction reduction、ARL reasons 付き）

---

## V4 → V5: 何が変わったか（概念）

v4 は安定した “emergency contract” governance bench として、smoke tests / stress runners に重点を置いています。
v5 はそれをさらに、artifact-level reproducibility と contract-style compatibility checks へ拡張しています。

v5 で追加 / 強化されたもの:

* Log codebook（demo）+ contract tests
  `layer/decision/final_decider/reason_code` の語彙を pytest で検証
* Reproducibility surface（重要なものを固定）
  simulator version / test version / codebook version を pin
* より厳密な invariant enforcement
  明示的な tests / contracts により、silent drift を減らす

v5 でも変わらないこと:

* 研究・教育目的
* Fail-closed + HITL の意味論
* synthetic data のみを使い、隔離環境で実行する方針
* セキュリティ保証はしない（codebook は暗号ではなく、tests は実運用の安全性を保証しない）

---

## 実行例

Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

Emergency contract（推奨: v5.1.2）+ contract tests

```bash
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
```

Emergency contract（legacy stable bench: v4.8）

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

Emergency contract（v4.4 stress）

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## プロジェクトの意図 / 非目標

意図:

* 再現可能な安全性・ガバナンスシミュレーション
* 明示的な HITL semantics（pause/reset/ban）
* 監査しやすい decision traces（最小 ARL）

非目標:

* 本番向け autonomous deployment
* 制限のない self-directed agent control
* 明示的にテストされた範囲を超える安全性主張

---

## データと安全上の注意

* synthetic / dummy data のみを使用してください。
* runtime logs はなるべく commit せず、evidence artifacts は最小かつ再現可能に保ってください。
* 生成 bundle（zip）は canonical source ではなく、レビュー用の evidence として扱ってください。

---

## ライセンス

Apache License 2.0（`LICENSE` を参照）

```
```

