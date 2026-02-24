# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
![CI](https://img.shields.io/github/actions/workflow/status/japan1988/multi-agent-mediation/python-app.yml)

> **不確実なら停止。リスクがあるならエスカレーション。**  
> エージェント型ワークフロー向けのガバナンス・シミュレーション（研究／教育目的）。

---

## ⚠️ 目的と免責（研究／教育）

**これは研究／教育目的の参照実装（プロトタイプ）です。**  
有害行為の実行または支援（例：侵入、監視、なりすまし、破壊、データ窃取等）や、適用される利用規約／ポリシー、法令、サービスや実行環境の内部規則に反する行為のために使用しないでください。本プロジェクトは、教育／研究および防御的な検証（例：ログ肥大の緩和、fail-closed + HITL の挙動検証）に焦点を当てており、攻撃手法の公開や不正行為の促進を意図しません。

**自己責任で使用してください：**関連する利用規約／ポリシーを確認し、隔離環境（外部ネットワークなし・実システム／実データなし）でローカルのスモークテストから開始してください。内容は “AS IS（現状有姿）” で提供され、いかなる保証もありません。適用法令で許される最大限の範囲において、著者は、コード／ドキュメント／生成物（例：zip バンドル）を含む本成果物の利用に起因する一切の損害について責任を負いません（第三者による悪用を含む）。

**コードブック免責：**同梱のコードブックはデモ／参照用の成果物です。そのまま使用せず、要件・脅威モデル・適用される規約／ポリシーに基づき必ず自作してください。コードブックはログ項目の圧縮エンコード／デコード用途であり、**暗号（機密性の提供）ではありません**。

**テスト／結果の免責：**スモークテストやストレス実行は、特定の実行条件下で実行されたシナリオに対する検証のみを意味します。現実世界の運用における正しさ・安全性・セキュリティ・特定目的適合性等を保証しません。OS／Python 版本、ハードウェア、設定、運用方法により結果は変動します。

---

🇬🇧 **English version:** [README.md](README.md)

## ⚡ TL;DR
- 交渉／調停系ワークフロー向けの **Fail-closed + HITL** ゲーティング・ベンチ（研究／教育）。
- **再現性優先**：seed 固定実行 + `pytest` による契約チェック（語彙／不変条件）。
- **監査志向**：最小 ARL ログ。ログ肥大を避けるために、異常時のみ ARL を保存し `INC#...` で索引化可能。

---

## 概要

Maestro Orchestrator は、研究／教育目的のオーケストレーション・フレームワークです。以下を優先します：

- **Fail-closed**  
  不確実・不安定・高リスクなら、黙って継続しない。
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な意思決定は、明示的にエスカレーションする。
- **トレーサビリティ（追跡可能性）**  
  最小 ARL ログにより、監査可能かつ再現可能な意思決定フローを提供する。

このリポジトリには、参照実装（doc orchestrator）と、交渉／調停／ガバナンス系ワークフローに対するシミュレーション・ベンチ、およびゲーティング挙動の検証が含まれます。

---

## 最新更新（このリポジトリで何が変わったか）

今回の更新では、緊急契約シミュレータの zip バンドル（パッケージ）を追加しました。

- 追加：`docs/mediation_emergency_contract_sim_pkg.zip`（v5.1.2 利便性バンドル）
- 理由：エントリポイントを変えずに、seed 固定の再現可能なスモーク／ストレス実行を素早く試せるようにするため
- 正（権威）となるソース：ルートのシミュレータスクリプト + テスト  
  - `mediation_emergency_contract_sim_v5_1_2.py`  
  - `pytest -q tests/test_v5_1_codebook_consistency.py`
- CI 影響：なし（docs の成果物であり、エントリポイントではない）
- 注記：zip は生成された利便性成果物であり、**権威あるロジックではありません**。使用前に必ずレビューしてください。

---

## クイックスタート（推奨ルート）

v5.1.x は再現性 + 契約チェックのために推奨します。v4.x はレガシーの安定ベンチとして維持します。  
まずは 1 本のスクリプトで挙動とログを確認し、次に広げてください。

### 1) 推奨：緊急契約シミュレータ（v5.1.2）を実行

任意：`docs/mediation_emergency_contract_sim_pkg.zip`  
（利便性のみ。正はルートスクリプト + テスト）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テスト（v5.1.x：シミュレータ + コードブック整合）を実行

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモコードブック（v5.1-demo.1）を確認／固定

* `log_codebook_v5_1_demo_1.json`（デモコードブック。成果物を交換する場合は版を固定）
* 注記：コードブックはログ項目の圧縮用途であり、**暗号ではありません**（機密性なし）。

### 4) 任意：レガシー安定ベンチ（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意：エビデンス・バンドル（v4.8 生成成果物）を確認

* `docs/artifacts/v4_8_artifacts_bundle.zip`

エビデンス・バンドル（zip）はテスト／実行で生成された成果物です。
正（権威）となるのは生成スクリプト + テストです。

---

## ストレステスト（safe-by-default）

v5.1.2 は、デフォルトでメモリ爆発を避ける設計です：

* **集計のみモード**（`keep_runs=False` がデフォルト）：run ごとの全結果をメモリ保持しない。
* **任意：**異常 run のみ ARL を保存（`INC#...` で索引化）し、ログ肥大を回避。

### A) 軽量スモーク → 中規模ストレス（推奨ランプ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) インシデントを強制発生（例：fabricate-rate 10% を 200 run）

以下は、異常 run を一定数発生させ、設定時に `INC#` ファイルを生成するはずです：

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

異常 run が発生した場合の出力：

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（インシデント ARL）
* `arl_out/incident_index.jsonl`（インシデントごとに 1 行）
* `arl_out/incident_counter.txt`（永続カウンタ）

Tip：`--max-arl-files` を設定してディスク肥大を制限してください。

---

## アーキテクチャ（高レベル）

監査可能かつ fail-closed な制御フロー：

```text
agents
  → mediator（risk / pattern / fact）
  → evidence verification
  → HITL（pause / reset / ban）
  → audit logs（ARL）
```

### アーキテクチャ（コード整合ダイアグラム）

以下の図は、現行コードの語彙（vocabulary）に整合しています。
ドキュメントのみ（ロジック変更なし）。

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## v5.0.1 → v5.1.2：変更点（差分）

v5.1.2 は、大規模 run でも安定するように強化し、異常時のみ永続化する設計を強めています。

* **デフォルトで “索引 + 集計のみ”**

  * run ごとの全結果をメモリ保持しない（大規模 `--runs` でのメモリ爆発回避）
  * 出力はカウンタ + HITL サマリ中心（任意で詳細）
* **インシデント索引（任意）**

  * 異常 run に `INC#000001...` を付与
  * 異常 ARL を `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` へ保存
  * 索引を `{arl_out_dir}/incident_index.jsonl` へ追記
  * 永続カウンタを `{arl_out_dir}/incident_counter.txt` に保存

維持されていること：

* 異常時のみ ARL 永続化（pre-context + incident + post-context）
* 改ざん検知用の ARL ハッシュチェーン（OSS デモ用のデモキー）
* fabricate-rate 混合 + seed による決定論的再現（`--fabricate-rate` / `--seed`）

コア不変条件：

* `sealed` は `ethics_gate` / `acc_gate` のみが設定可能
* `relativity_gate` は決して sealed にならない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

---

## V1 → V4：概念的に何が変わったか

`mediation_emergency_contract_sim_v1.py` は最小パイプラインを示します：
直線的なイベント駆動ワークフロー + fail-closed 停止 + 最小監査ログ。

`mediation_emergency_contract_sim_v4.py` は、初期拒否と制御された自動化を追加し、再現可能なガバナンス・ベンチに拡張します。

v4 で追加：

* Evidence gate（無効／無関係／捏造証拠で fail-closed 停止）
* Draft lint gate（draft-only の意味論とスコープ境界）
* Trust system（score + streak + cooldown）
* AUTH HITL の自動スキップ（trust + grant による安全な摩擦低減、ARL 理由付き）

---

## V4 → V5：概念的に何が変わったか

v4 は、安定した “緊急契約” ガバナンス・ベンチ（スモーク／ストレス）に焦点。
v5 は、それを成果物レベルの再現性と “契約チェック” に寄せて強化します。

v5 で追加／強化：

* ログコードブック（デモ）+ 契約テスト
  `layer/decision/final_decider/reason_code` など、出力語彙を pytest で固定。
* 再現性サーフェス（固定するべきものを固定）
  シミュレータ版、テスト版、コードブック版を pin。
* 不変条件の強制強化
  明示テストにより、静かなドリフトを抑止。

v5 でも変わらないこと：

* 研究／教育目的
* Fail-closed + HITL の意味論
* 合成（ダミー）データのみ、隔離環境での実行推奨
* セキュリティ保証なし（コードブックは暗号ではない／テストは実運用の安全を保証しない）

---

## 実行例

Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

緊急契約（推奨：v5.1.2）+ 契約テスト

```bash
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
```

緊急契約（レガシー安定ベンチ：v4.8）

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

緊急契約（v4.4 ストレス）

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## プロジェクトの意図／非ゴール

意図：

* 再現可能な安全性／ガバナンス・シミュレーション
* 明示 HITL（pause/reset/ban）
* 監査可能な意思決定トレース（最小 ARL）

非ゴール：

* 本番運用向けの自律システム配備
* 無制限な自己駆動エージェント制御
* 実施したテスト範囲を超える安全性主張

---

## データ／安全メモ

* 合成（ダミー）データのみを使用してください。
* 実行ログのコミットは避け、エビデンス成果物は最小かつ再現可能に保つことを推奨します。
* 生成された zip バンドルは “レビュー可能な証拠” であり、正（権威）となるのは生成スクリプト + テストです。

---

## ライセンス

Apache License 2.0（`LICENSE` を参照）
