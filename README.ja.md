# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
![CI](https://img.shields.io/github/actions/workflow/status/japan1988/multi-agent-mediation/python-app.yml)

> **不確実なら停止。危険ならエスカレーション。**  
> エージェントワークフロー向けのガバナンス・シミュレーション（研究／教育目的）

---

## ⚠️ 目的と免責（研究／教育）

**本リポジトリは研究／教育目的の参照実装（プロトタイプ）です。**  
悪用（例：侵害、侵入、監視、なりすまし、破壊、データ窃取等）を実行・支援する目的で使用しないでください。また、利用環境やサービスの利用規約／ポリシー、適用法令、社内規程などに違反する用途で使用しないでください。

本プロジェクトは **研究／教育** と **防御的検証**（例：ログ肥大の緩和、fail-closed + HITL 挙動の検証）に焦点を当てています。  
攻撃手口の公開や不正行為の促進を目的としたものではありません。

### リスク／保証／責任

- **自己責任で利用**：関連する利用規約／ポリシーを確認してください。
- **隔離環境から開始**：まずはローカルのスモークテスト（外部ネットワークなし／実システム・実データなし）から始めてください。
- **現状有姿（AS IS）**：いかなる保証もありません。
- **責任の制限**：適用法令で許容される最大限の範囲で、作者はコード・文書・生成物（zipバンドル等）の利用に起因する損害（第三者による悪用を含む）について一切の責任を負いません。

### コードブック免責

同梱のコードブックは **デモ／参照用アーティファクト**です。実運用でそのまま使わず、要件・脅威モデル・適用される規約／ポリシーに基づいて自作してください。  
コードブックはログ項目の圧縮エンコード／デコード用途であり、**暗号ではありません**（機密性は提供しません）。

### テスト結果の免責

スモークテスト／ストレステストが検証するのは、特定のランタイム条件下で実行したシナリオに限られます。  
現実の運用における正しさ・安全性・セキュリティ・特定目的適合性を保証するものではありません。OS／Python／ハードウェア／設定／運用条件により結果は変動します。

---

🇺🇸 **英語版:** [README.md](README.md)

## ⚡ TL;DR
- **Fail-closed + HITL** による交渉／調停系ワークフローのゲーティング・ベンチ（研究／教育）
- **再現性優先**：seed固定の実行 + `pytest` による契約（語彙／不変条件）チェック
- **監査志向**：最小ARLログ／ログ肥大回避のための incident-only ARL（`INC#...`）索引化（任意）

---

## 概要

Maestro Orchestrator は、研究／教育目的のオーケストレーション・フレームワークで、以下を優先します：

- **Fail-closed**  
  不確実・不安定・危険 → 黙って継続しない
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な局面は明示的にエスカレーション
- **トレーサビリティ**  
  意思決定フローを最小ARLログで監査可能にし、seed固定で再現可能にする

本リポジトリには、ドキュメント・オーケストレータの参照実装、および交渉／調停／ガバナンス系ワークフロー向けのシミュレーション・ベンチとゲーティング挙動の検証が含まれます。

---

## 最新更新（このリポジトリで何が変わったか）

今回の更新では、緊急契約シミュレータの zip バンドルを追加しました。

- 追加：`docs/mediation_emergency_contract_sim_pkg.zip`（v5.1.2 便利用バンドル）
- 目的：エントリポイントを変えずに、seed固定で再現可能なスモーク／ストレス実行を素早く試すため
- 正本（ロジックの権威）：
  - `mediation_emergency_contract_sim_v5_1_2.py`
  - `pytest -q tests/test_v5_1_codebook_consistency.py`
- CI への影響：なし（docsアーティファクトであり、エントリポイントではない）
- 注：zip バンドルは **生成物／便利用アーティファクト**（検証可能な証跡）であり、**権威あるロジックではありません**。利用前に必ずレビューしてください。

---

## クイックスタート（推奨ルート）

v5.1.x は再現性と契約チェックのため推奨です。v4.x はレガシー安定ベンチとして残しています。  
まずは 1 本のスクリプトで挙動とログを確認し、その後に拡張してください。

### 1) 推奨：緊急契約シミュレータ（v5.1.2）を実行

任意のバンドル：`docs/mediation_emergency_contract_sim_pkg.zip`（便利用）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) 契約テストを実行（v5.1.x：シミュレータ + コードブック整合）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) デモコードブック（v5.1-demo.1）を確認／固定

* `log_codebook_v5_1_demo_1.json`（デモコードブック。成果物を交換する場合はバージョン固定推奨）
* 注：コードブックは **暗号ではありません**（機密性なし）

### 4) 任意：レガシー安定ベンチ（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) 任意：証跡バンドル（v4.8 生成アーティファクト）を確認

* `docs/artifacts/v4_8_artifacts_bundle.zip`

証跡バンドル（zip）はテスト／実行により生成されるアーティファクトです。
正本は生成スクリプトとテストです。

---

## ストレステスト（安全側デフォルト）

v5.1.2 はデフォルトでメモリ爆発を避ける設計です：

* 集計のみ（`keep_runs=False` がデフォルト）：runごとの詳細結果をメモリに保持しない
* 任意：異常runのみ ARL を保存（`INC#...` によるインシデント索引化）

### A) 軽量スモーク → 中程度ストレス（推奨ランプ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress（集計のみのまま）
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) インシデント強制（例：fabricate-rate 10% を200回）

有効化すると `INC#` ファイルが生成されるはずです：

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

出力（異常runが発生した場合）：

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（インシデントARL）
* `arl_out/incident_index.jsonl`（インシデント索引：1行=1件）
* `arl_out/incident_counter.txt`（永続カウンタ）

Tip：`--max-arl-files` でディスク肥大を上限管理してください。

---

## 図とドキュメント

図とバンドルの一覧（ギャラリー）：**[docs/README.md](docs/README.md)**

主要図：

* 緊急契約 overview（v5.1.2）：[docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* アーキテクチャ（code-aligned）：[docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* unknown-progress + HITL 図：[docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* マルチエージェント階層：[docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* 感情コンテキスト・フロー：[docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

---

## アーキテクチャ（高レベル）

監査可能で fail-closed な制御フロー：

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
```

### アーキテクチャ（overview, v5.1.2）

ドキュメントのみ。ロジック変更なし。

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### アーキテクチャ（code-aligned diagrams）

以下の図は現行のコード語彙に整合しています。
ドキュメントのみ。ロジック変更なし。

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## v5.0.1 → v5.1.2：変更点（差分）

v5.1.2 は大量run時の安定性と、異常のみ永続化（incident-only）を強化しています。

* **デフォルト：索引 + 集計のみ**

  * runごとの詳細結果をメモリに保持しない（大規模 `--runs` でのメモリ爆発回避）
  * 出力はカウンタとHITLサマリ中心（任意で追加）
* **インシデント索引化（任意）**

  * 異常runに `INC#000001...` を採番
  * 異常ARLは `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` に保存
  * 索引は `{arl_out_dir}/incident_index.jsonl` に追記
  * 永続カウンタは `{arl_out_dir}/incident_counter.txt` に保存

維持されている点：

* 異常runのみ ARL 永続化（pre-context + incident + post-context）
* 改ざん検知（ARL hash chaining：OSSデモのデフォルトキー）
* fabricate-rate 混合 + seed 固定（`--fabricate-rate` / `--seed`）

中核不変条件：

* `sealed` は `ethics_gate` / `acc_gate` のみが設定可能
* `relativity_gate` は封印しない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

---

## V1 → V4：何が変わったか（概念）

`mediation_emergency_contract_sim_v1.py` は最小パイプライン（イベント駆動＋fail-closed＋最小ログ）を示します。

`mediation_emergency_contract_sim_v4.py` はそれを反復可能なガバナンス・ベンチへ拡張（早期拒否と制御付き自動化）します。

v4で追加：

* Evidence gate（無効／無関連／捏造の証拠は fail-closed 停止）
* Draft lint gate（ドラフト前提の語彙／境界）
* Trust system（score + streak + cooldown）
* AUTH HITL auto-skip（信頼＋許可に基づく安全な摩擦低減、ARL理由付き）

---

## V4 → V5：何が変わったか（概念）

v4は「緊急契約」ガバナンス・ベンチ（スモーク＋ストレス）を安定化。
v5は成果物レベルの再現性と契約互換テストへ拡張します。

v5で追加／強化：

* ログコードブック（デモ）＋契約テスト
  `layer/decision/final_decider/reason_code` の語彙を pytest で固定します。
* 再現性サーフェス（固定すべき要素の明確化）
  シミュレータ版／テスト版／コードブック版を固定。
* 不変条件の締め付け
  明示的なテストによりサイレントなドリフトを抑止。

v5でも変わらない点：

* 研究／教育目的
* Fail-closed + HITL の意味論
* 合成データのみ／隔離環境推奨
* 安全保証はしない（コードブックは暗号ではない／テストは実運用安全を保証しない）

---

## 実行例

Doc orchestrator（参照実装）

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

緊急契約（推奨：v5.1.2）＋契約テスト

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

## 目的／非目的

目的：

* 再現可能な安全・ガバナンス・シミュレーション
* 明示的な HITL（pause/reset/ban）
* 監査向け意思決定トレース（最小ARL）

非目的：

* 本番向け自律デプロイ
* 無制限な自己指向エージェント制御
* テスト範囲を超える安全性主張

---

## データ／安全メモ

* 合成／ダミーデータのみ使用。
* 実行ログをコミットしない方針を推奨。証跡アーティファクトは最小・再現可能に。
* zipバンドル等の生成物は「レビュー可能な証跡」であり、正本ではない。

---

## ライセンス

Apache License 2.0（`LICENSE` を参照）
必要なら、次の一手として **`docs/README.md` のギャラリー本体（サムネ一覧）**も日本語で同梱した版をフルで出します。
```
