
# 📘 Maestro Orchestrator — マルチエージェント・オーケストレーション・フレームワーク
> English: [README.md](README.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License (Policy Intent)">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）



* ガバナンス系ワークフロー向けの **fail-closed + HITL オーケストレーション・ベンチ**
* シード付き実行と `pytest` ベースの contract check を備えた **再現可能なシミュレーター**
* 最小 ARL ログによる **監査可能なトレース**
* オーケストレーション / ゲーティング挙動の **実装リファレンス**


Maestro Orchestrator は、複数エージェント（または複数手法）を監督するための **研究向けオーケストレーション・フレームワーク**です。  
特徴は **fail-closed（安全側に倒す）**を前提にしている点です。

- **STOP**: エラー／危険／未定義仕様を検知したら停止
- **REROUTE**: 明示的に安全と判断できる場合のみ再ルーティング（fail-open reroute を避ける）
- **HITL**: 曖昧・高リスクは人間判断へエスカレーション

### 位置づけ（安全優先）
Maestro Orchestrator は、タスク完遂率を最大化するよりも、**不安全／未定義の実行を防ぐこと**を優先します。  
リスクや曖昧さが検知された場合、`PAUSE_FOR_HITL` または `STOPPED` に **fail-closed** し、監査ログに「なぜそうなったか」を残します。

**トレードオフ:** 安全とトレーサビリティを優先するため、デフォルトでは *止まりやすい（over-stop）* 設計になり得ます。

## 🚫 非目的（IMPORTANT）

このリポジトリは **研究プロトタイプ**です。以下は明確に **対象外**です：

- **本番運用レベルの自律意思決定**（無人で現実世界に権限を持つ用途は想定しない）
- **現実のユーザーに対する persuasion / reeducation の最適化**（安全評価用途のみ。opt-in 前提でデフォルト無効）
- **実在個人情報（PII）**や機密業務データを含むプロンプト／テスト／ログの取り扱い
- 規制領域（医療／法務／金融等）に対する **コンプライアンス・法的助言**や導入ガイダンス

このリポジトリは、次のようなものとして読むのが適切です。

* **研究プロトタイプ**
* **教育用リファレンス**
* **ガバナンス / 安全性シミュレーションベンチ**

これは**本番向けの自律フレームワークではありません**。

---

## Quick links

* **日本語 README:** [README.ja.md](README.ja.md)
* **ドキュメント一覧:** [docs/README.md](docs/README.md)
* **推奨シミュレーター:** `mediation_emergency_contract_sim_v5_1_2.py`
* **Contract test:** `tests/test_v5_1_codebook_consistency.py`
* **Stress metrics test (v5.1.2):** `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
* **Pytest ARL hook:** `tests/conftest.py`
* **最新の mixed stress summary:** `stress_results_v5_1_2_10000_mixed.json`
* **従来の安定ベンチ:** `mediation_emergency_contract_sim_v4_8.py`
* **Doc orchestrator（mediator reference）:** `ai_doc_orchestrator_with_mediator_v1_0.py`
* **Doc orchestrator contract test:** `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---


## ⚡ TL;DR


REROUTE は **すべての条件を満たす場合のみ許可**します。満たさない場合は `PAUSE_FOR_HITL` または `STOPPED` にフォールバックします。

| リスク／条件 | REROUTE | デフォルト動作 |
|---|---:|---|
| 仕様未定義／意図が曖昧 | ❌ | `PAUSE_FOR_HITL` |
| ポリシー感度が高い領域（PII、秘密情報、高リスク領域） | ❌ | `STOPPED` または `PAUSE_FOR_HITL` |
| ルート候補が元より **高い** ツール／データ権限を要求 | ❌ | `STOPPED` |
| ルート候補が **同等以上の制約**を強制できない | ❌ | `STOPPED` |
| 低リスククラス + 権限が同等以下 + 制約が同等以上 | ✅ | `REROUTE` |
| REROUTE 回数が上限超過 | ❌ | `PAUSE_FOR_HITL` または `STOPPED` |

**ハード制限（推奨デフォルト）**
- `max_reroute = 1`（超過 → `PAUSE_FOR_HITL` または `STOPPED`）
- REROUTE は `reason_code` と選択ルートIDを監査ログに必ず記録すること。

* 交渉 / 調停系ワークフロー向けの **fail-closed + HITL** ゲーティングベンチ（研究 / 教育用）
* **再現性優先**: シード付き実行 + `pytest` contract check（語彙 / 不変条件）
* **監査対応**: 最小 ARL ログ、ログ肥大を避ける incident-only ARL indexing（`INC#...`）
* **Doc orchestration の参照実装**: mediator + 固定ゲート順 + contract-tested な HITL continuation semantics
* **検証更新**: v5.1.2 stress metrics test + pytest 実行 ARL + 10,000-run clean/mixed 検証例

---

## ⚠️ 目的と免責（研究・教育用）


**これは研究 / 教育用のリファレンス実装（プロトタイプ）です。**
有害な行為（例: 悪用、侵入、監視、なりすまし、破壊、データ窃取）を実行・促進するため、または利用中のサービスや実行環境の利用規約 / ポリシー / 法令 / 内部規則に違反するために使用しないでください。


### 1) Context flow（文脈フロー）
<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>

- **Perception** — 入力を実行可能要素へ分解（タスク化）
- **Context** — 仮定／制約／リスク要因を抽出（ガード理由）
- **Action** — エージェント指示、結果検証、分岐（STOP / REROUTE / HITL）

### 2) Orchestrator one-page design map（1枚設計図）
**Decision flow map（実装準拠）:**  
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`  
**fail-closed** 前提：リスク／曖昧さがあれば `PAUSE_FOR_HITL` または `STOPPED` に倒し、「なぜ」をログに残します。

このプロジェクトは、**教育 / 研究**および**防御的な検証**（例: ログ増大の抑制や fail-closed + HITL 挙動の検証）に焦点を当てています。
**攻撃手法の公開や不正行為の支援**を目的としたものではありません。

### リスク / 無保証 / 責任制限

* **自己責任で使用してください:** 関連する利用規約やポリシーを確認してください。
* **まず隔離環境で実行してください:** 外部ネットワーク・実システム・実データなしのローカル smoke test から始めてください。
* **現状有姿 / 無保証:** いかなる保証もなく提供されます。
* **責任制限:** 適用法令で許される最大限の範囲で、コード・ドキュメント・生成物の利用に起因する損害（第三者による誤用を含む）について、作者は責任を負いません。

### Codebook に関する注意


同梱されている codebook は**デモ / リファレンス用成果物**です。実運用にそのまま使わず、要件・脅威モデル・適用ポリシー / 利用規約に基づいて自作してください。
この codebook はログ項目のコンパクトな符号化 / 復号のためのものであり、**暗号ではありません**（機密性はありません）。


画像が表示されない（または小さい）場合は直接開いてください：  
- `docs/orchestrator_onepage_design_map.png`

RFL は非封印（non-sealing）設計です：`PAUSE_FOR_HITL` にエスカレートし、`sealed=true` にはなりません。

## 🧾 監査ログ & データ安全（IMPORTANT）

このプロジェクトは、再現性と説明責任のために **監査ログ（audit log）**を出力します。  
ログはセッションより長く残り、研究共有され得るため、**ログをセンシティブな成果物として扱う**前提で設計してください。

- プロンプト／テストベクタ／ログに **個人情報（PII）**（メール、電話番号、住所、実名、アカウントID等）を入れない
- 実験は **合成データ／ダミーデータ**を優先
- 実行時ログをリポジトリにコミットしない（必要ならマスキング／保持期限／隔離ディレクトリを適用）

### テストおよび結果に関する注意

smoke test や stress run は、特定の実行条件下で実行したシナリオのみを検証します。
これらは、実運用における正確性・安全性・適合性・目的適合性を保証するものではありません。結果は OS / Python バージョン、ハードウェア、設定、運用条件によって変わり得ます。

---

## このリポジトリが存在する理由

Maestro Orchestrator は、次の3つを優先して構築されています。

* **Fail-closed**

  * 不確実・不安定・危険なら、黙って継続しない。
* **HITL エスカレーション**


  * 人間の判断が必要な決定を明示的にエスカレーションする。
* **追跡可能性**


研究共有可能で安全なログにするため：

- **MUST NOT**: PIIや秘密情報を含み得る raw のプロンプト／出力を永続化しない
- **MUST**: *sanitized* な証拠（redacted / hashed / カテゴリ信号）だけを保存する
- **MUST**: PII様パターンは fail-closed で赤塗り（検知失敗時はログを書かない）
- **MUST**: 赤塗りは **値だけでなく辞書キーにも適用**（`@` 等が残存しないこと）
- **MUST**: 実行時ログをリポジトリにコミットしない（ローカル隔離を推奨）

**最小必須フィールド（実装準拠, MUST）**
- `run_id`, `ts`, `layer`, `decision`, `reason_code`, `sealed`, `overrideable`, `final_decider`

**任意フィールド（必要ならSHOULD）**
- `session_id`, `policy_version`, `artifact_id`, `route_id`（すべて非PII・sanitized 前提）

**保持期限（SHOULD）**
- 7/30/90 日など保持期限を定義し自動削除すること。

## 🧑‍⚖️ HITL セマンティクス（HITL後の挙動を定義）

HITL は曖昧・高リスク時に使用します。責任の所在は監査ログで追跡可能であるべきです。

- HITL を要求した時、オーケストレーターは `HITL_REQUESTED`（**SYSTEM**）を出力し、通常以下を含みます：
  - `decision=PAUSE_FOR_HITL`, `sealed=false`, `overrideable=true`
- ユーザーの選択は `HITL_DECIDED`（**USER**）として記録します：
  - `sealed=false`, `overrideable=false`, `final_decider=USER`
  - `CONTINUE` → 決定は `RUN` に伝搬
  - `STOP` → 決定は `STOPPED` へ

**注意:** `sealed=true` になれるのは Ethics/ACC のみ（この場合 `final_decider=SYSTEM`）。

  * 意思決定フローを最小 ARL ログによって再現可能・監査可能にする。

このリポジトリには、次のためのシミュレーションベンチと実装リファレンスが含まれます。

* 交渉
* 調停
* ガバナンス系ワークフロー
* ゲーティング挙動
* 監査志向のオーケストレーション

---

## Recommended path

初めてこのリポジトリを見る場合は、次の順で進めるのがおすすめです。

1. 推奨シミュレーターを実行する: `mediation_emergency_contract_sim_v5_1_2.py`
2. Contract test を実行する: `tests/test_v5_1_codebook_consistency.py`
3. Stress metrics test を実行する: `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
4. 生成されたログ、codebook、必要に応じて incident artifact を確認する
5. その後、必要なら `mediation_emergency_contract_sim_v4_8.py` と比較する
6. より小さい固定順序の参照実装として `ai_doc_orchestrator_with_mediator_v1_0.py` を実行する

---

## Quickstart


### 1) 推奨される emergency contract simulator（v5.1.2）を実行する


> “persuasion / reeducation” を想起させるモジュールは **安全評価用途のみ**で、明示的 opt-in がない限り **デフォルト無効**を推奨します。

任意の bundle: `docs/mediation_emergency_contract_sim_pkg.zip`（利便性のためのみ）


```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
```


# Doc orchestrator (KAGE3-style)
python ai_doc_orchestrator_kage3_v1_2_4.py
#（旧版が残っていても、v1.2.4 を post-HITL セマンティクスの参照版とする）

### 2) Contract tests を実行する（v5.1.x: simulator + codebook consistency）

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) Stress metrics tests を実行する（v5.1.2）

```bash
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
```

### 4) Pytest 実行 ARL（自動出力）

`tests/conftest.py` は、pytest 実行そのものに対する JSONL 形式の ARL を自動出力します。

既定の出力先:

* `test_artifacts/pytest_test_arl.jsonl`
* `test_artifacts/pytest_simulation_arl.jsonl`

実行:

```bash
pytest -q
```

出力先を指定する場合:

```bash
TEST_ARL_PATH=out/test_arl.jsonl SIM_ARL_PATH=out/sim_arl.jsonl pytest -q
```

### 5) デモ codebook を確認 / 固定する（v5.1-demo.1）

* `log_codebook_v5_1_demo_1.json`（デモ用 codebook。artifact をやり取りする際は version を固定してください）
* 注: codebook は **暗号ではありません**（機密性なし）

### 6) 任意: 従来の安定ベンチ（v4.8）を実行する

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 7) 任意: doc orchestrator mediator reference を実行する

```bash
python ai_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
```

### 8) 実行後に確認すべきもの

* simulator stdout の summary
* 生成された ARL / audit JSONL trace
* abnormal-only persistence を有効にした場合の `incident_index.jsonl` と `INC#...` files
* pytest contract tests における語彙 / 不変条件チェック
* pytest 側の実行 ARL（`pytest_test_arl.jsonl`）
* 任意の simulation 側 ARL bridge 出力（`pytest_simulation_arl.jsonl`）

---

## Latest update

最近の追加と安定化のハイライト:

* 推奨 simulator の convenience zip bundle を追加:

  * `docs/mediation_emergency_contract_sim_pkg.zip`
* Doc orchestrator mediator reference を安定化:

  * `ai_doc_orchestrator_with_mediator_v1_0.py`
  * `tests/test_doc_orchestrator_with_mediator_v1_0.py`

### Validation update (v5.1.2)

追加:

* `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
* `tests/conftest.py`
* `stress_results_v5_1_2_10000_mixed.json`

この更新で追加されたもの:

* v5.1.2 向け stress-oriented validation
* pytest 実行 ARL の自動出力
* clean / mixed 10,000-run 検証例
* abnormal ARL persistence と incident index consistency の明示的検証

引き続き、正準な source of truth は Python entrypoint と contract test です。

---

## Stress tests（safe-by-default）

v5.1.2 は、既定でメモリ増大を避けるよう設計されています。

* Aggregation-only mode（既定で `keep_runs=False`）: full per-run results をメモリに保持しない
* 任意: 異常実行時のみ ARL を保存（`INC#...` による incident indexing）

### A) 軽量 smoke → 中規模 stress（推奨ランプアップ）

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress（引き続き aggregation-only）
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) Incident を強制する（例: 200 runs に対して fabricate-rate 10%）

この設定では、異常 run がある程度確実に発生し、設定時には `INC#` file が生成されます。

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

出力（異常 run が発生した場合）:

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl`（incident ARL）
* `arl_out/incident_index.jsonl`（incident ごとに1行）
* `arl_out/incident_counter.txt`（永続カウンタ）

ヒント: ディスク増大を抑えるため、`--max-arl-files` を設定してください。

### C) 検証済み large-run 例

Clean run:

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```



Mixed abnormal run:

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 10000 \
  --fabricate-rate 0.10 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir out_arl
```

現行の validation setup では:

* 10,000 clean runs は異常 incident なしで完了
* 10,000 mixed runs は異常ケースを一貫して index 化 / 永続化して完了
* test-side ARL 出力と simulation-side ARL 出力を分離して追跡可能

公開済みの example summary:

* `stress_results_v5_1_2_10000_mixed.json`

---

## 図とドキュメント

すべての図と bundle はここから参照できます: **[docs/README.md](docs/README.md)**

主要な図:

* Emergency contract overview (v5.1.2): [docs/architecture_v5_1_2_emergency_contract_overview.png](docs/architecture_v5_1_2_emergency_contract_overview.png)
* Architecture (code-aligned): [docs/architecture_code_aligned.png](docs/architecture_code_aligned.png)
* Unknown-progress + HITL diagram: [docs/architecture_unknown_progress.png](docs/architecture_unknown_progress.png)
* Multi-agent hierarchy: [docs/multi_agent_hierarchy_architecture.png](docs/multi_agent_hierarchy_architecture.png)
* Sentiment context flow: [docs/sentiment_context_flow.png](docs/sentiment_context_flow.png)

推奨読書順:

1. この README
2. `docs/README.md`
3. `mediation_emergency_contract_sim_v5_1_2.py`
4. `tests/test_v5_1_codebook_consistency.py`
5. `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
6. `tests/conftest.py`
7. `ai_doc_orchestrator_with_mediator_v1_0.py`
8. `tests/test_doc_orchestrator_with_mediator_v1_0.py`


rust
NORMAL -> CONTRACT_EFFECTIVE

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

### アーキテクチャ（overview, v5.1.2）

ドキュメント用。ロジック変更はありません。

<p align="center">
  <img src="docs/architecture_v5_1_2_emergency_contract_overview.png"
       alt="Emergency contract simulator overview (v5.1.2)"
       width="860">
</p>

### アーキテクチャ（code-aligned diagrams）

以下の図は、現在のコード語彙に合わせたものです。
ドキュメント用であり、ロジック変更はありません。


bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
What’s new (2026-02-07)
New: mediation_emergency_contract_sim_v4_4.py
Emergency contract workflow bench v4.4 (fail-closed + HITL + minimal ARL).

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## Version deltas


### v5.0.1 → v5.1.2

v5.1.2 は、大規模 runs の安定性と incident-only persistence を強化しています。

* **既定で index + aggregation-only**

  * full per-run results をメモリに保持しない（大きい `--runs` でのメモリ爆発を防ぐ）
  * 出力は counters + HITL summary を中心とする（items は任意）

* **Incident indexing（任意）**

  * abnormal run に `INC#000001...` を付与
  * abnormal ARL を `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl` に保存
  * index を `{arl_out_dir}/incident_index.jsonl` に追記
  * 永続 counter を `{arl_out_dir}/incident_counter.txt` に保存

維持されているもの:

* abnormal-only ARL persistence（pre-context + incident + post-context）
* 改ざん検知用 ARL hash chaining（OSS demo では既定で demo key）
* Fabricate-rate mixing + deterministic seeding（`--fabricate-rate` / `--seed`）

Core invariants:

* `sealed` は `ethics_gate` / `acc_gate` からのみ設定可能
* `relativity_gate` は sealed にならない（`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`）

### v5.1.2 における実用的な安定性向上

上記の挙動変化に加え、v5.1.2 では実運用上の安定性も次の3点で改善されています。

* **Persistence handling**

  * trust / grants / eval store の path handling と serialization をより一貫化
  * runtime behavior と saved artifact のズレを減らす

* **Test compatibility**

  * persistent store path をより一貫して露出し、テストから patch しやすくした
  * これにより CI の isolation と contract / stress check の再現性が向上

* **Output stability**

  * JSON 出力の扱いをより一貫化（UTF-8 / newline-stable / serializer-stable）
  * 環境差による不要な差分を減らし、result artifact を確認しやすくした

### v5.1.2 周辺で追加された validation

現在のリポジトリ状態には、さらに次が含まれます。

* clean / mixed の large-run validation 向け stress metrics tests
* `tests/conftest.py` による pytest 実行 ARL logging
* 10,000-run mixed validation の published example result summary

### Doc orchestrator mediator reference (v1.0)

`ai_doc_orchestrator_with_mediator_v1_0.py` は、次に焦点を当てた小さめの orchestration reference です。

* 固定ゲート順
* 停止権限を持たない mediator advice
* 明示的な HITL continuation handling
* sanitization 済みの audit-oriented JSONL trace
* contract-tested な orchestration vocabulary

この reference は、大きな emergency-contract bench family の置き換えではなく、監査志向オーケストレーションのコンパクトな実装例として意図されています。

### V1 → V4（概念的変化）

`mediation_emergency_contract_sim_v1.py` は最小限のパイプラインを示します。
線形でイベント駆動のワークフローに、fail-closed stop と最小 audit log を備えたものです。

`mediation_emergency_contract_sim_v4.py` は、このパイプラインを繰り返し実行可能な governance bench に拡張し、早期拒否と制御された自動化を加えています。

v4 で追加されたもの:

* Evidence gate（無効 / 無関係 / fabricated evidence は fail-closed stop）
* Draft lint gate（draft-only semantics と scope boundary）
* Trust system（score + streak + cooldown）
* AUTH HITL auto-skip（trust + grant による安全な friction reduction と ARL reason）

### V4 → V5（概念的変化）

v4 は、smoke test と stress runner を備えた安定した “emergency contract” governance bench に焦点を当てています。
v5 は、そのベンチを artifact-level reproducibility と contract-style compatibility check の方向へ拡張します。

v5 で追加 / 強化されたもの:

* **Log codebook (demo) + contract tests**
  `layer/decision/final_decider/reason_code` といった emitted vocabulary を pytest で強制

* **Reproducibility surface（固定すべきものを固定）**
  simulator version、test version、codebook version を pin する

* **Tighter invariant enforcement**
  不変条件に関する明示的な test / contract により、無言の drift を減らす


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
Project intent / non-goals
Intent
Reproducible safety and governance simulations

v5 でも変わらないこと:

* 研究 / 教育目的
* Fail-closed + HITL semantics
* synthetic data only を使い、隔離環境で動かすこと
* 安全性保証はしないこと（codebook は暗号ではなく、テストも実運用安全性を保証しない）

---

## プロジェクトの目的 / 非目的

### 目的

* 再現可能な安全性・ガバナンスシミュレーション
* 明示的な HITL semantics（pause / reset / ban）
* 監査可能な意思決定 trace（最小 ARL）

### 非目的

* 本番向けの自律デプロイ
* 無制限な自己主導エージェント制御
* 明示的にテストされた範囲を超える安全性主張


---

## データと安全性に関する注意

* synthetic / dummy data のみを使用してください
* runtime log の commit はなるべく避け、evidence artifact は最小かつ再現可能に保ってください
* 生成される bundle（zip）は reviewable evidence として扱い、canonical source とは見なさないでください

---

## License



