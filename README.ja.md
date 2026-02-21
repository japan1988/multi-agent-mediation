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
> これは研究/教育目的の参照実装（プロトタイプ）です。**有害行為の実行・助長**（例：悪用、侵入、監視、なりすまし、破壊、データ窃取 等）や、
> 利用環境/サービスの **利用規約・ポリシー、法令、社内ルール** に反する用途に使わないでください。  
> 本プロジェクトは **教育/研究および防御的な検証**（例：ログ肥大の抑制、fail-closed + HITL 動作の検証）を主目的としており、
> **攻撃手口の公開**や不正行為の促進を意図しません。  
> 利用は自己責任です。必ず関連する **利用規約/ポリシー** を確認し、まずは **隔離環境でのローカル検証**（外部ネットワークなし、実データ/実システムなし）から始めてください。  
> 本コード・文書・生成物（例：zip バンドル）は **現状有姿（AS IS）**・無保証で提供され、適用法で許される最大限の範囲で、
> 作者は利用に起因する一切の損害について **責任を負いません**（第三者による悪用を含む）。  
> 同梱の **コードブックはデモ/参照用の成果物**です。**そのまま実運用に使わず、要件・脅威モデル・規約/ポリシーに基づき自作してください。**  
> **テスト/結果の免責:** スモークテストやストレス実行は、特定条件下で実行されたシナリオの範囲でのみ検証します。実運用での正しさ・安全性・セキュリティ・適合性を保証しません。

---

## 概要

Maestro Orchestrator は **研究 / 教育** 向けのオーケストレーション・フレームワークで、以下を優先します。

- **Fail-closed（失敗時は安全側）**  
  不確実・不安定・リスクがある場合は、黙って先に進まず停止/保留する。

- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な局面は明示的にエスカレーションする。

- **トレーサビリティ**  
  意思決定フローを最小ARLログで監査可能・再現可能にする。

このリポジトリには、**参照実装**（ドキュメント・オーケストレーター等）と、
交渉/調停/ガバナンス風ワークフローにおけるゲート動作を検証する **シミュレーションベンチ**が含まれます。

---

## クイックスタート（推奨ルート）

**v5.1.x は再現性 + 契約チェックのための推奨系。v4.x はレガシーの安定ベンチとして維持。**

まずは 1 本のスクリプトで挙動とログを確認し、徐々に拡張してください。

### 1) 推奨：緊急コントラクト・シミュレータ（v5.1.2）

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
2) 契約テスト（v5.1.x：シミュレータ + コードブック整合）
pytest -q tests/test_v5_1_codebook_consistency.py
3) デモコードブックの確認 / ピン留め（v5.1-demo.1）

log_codebook_v5_1_demo_1.json（デモ用コードブック。成果物交換時は バージョンを固定）

注意：コードブックはログ項目の圧縮（エンコード/デコード）目的であり、暗号ではありません（秘匿性はありません）。

4) 任意：レガシー安定ベンチ（v4.8）
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
5) 任意：証拠バンドル（v4.8 生成物）

docs/artifacts/v4_8_artifacts_bundle.zip

zip は実行/テストにより生成される成果物です。
正のソースは生成スクリプト + テストです。

ストレステスト（安全側デフォルト）

v5.1.2 はデフォルトでメモリ暴走を避ける設計です。

集計のみ（aggregation-only） がデフォルト（keep_runs=False）：各runの詳細結果をメモリに保持しない

任意：異常時のみ ARL 保存（INC#... でインデックス化）

A) 軽いスモーク → 中規模ストレス（推奨ランプ）
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress（集計のみのまま）
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
B) 異常を意図的に発生（例：捏造率10%を200回）

異常runが発生すると、設定により INC# ファイルが生成されます。

python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000

生成物（異常が出た場合）：

arl_out/INC#000001__SIM#B000xx.arl.jsonl（incident ARL）

arl_out/incident_index.jsonl（incident index：1行=1件）

arl_out/incident_counter.txt（永続カウンタ）

--max-arl-files でディスク増加を上限管理できます。

アーキテクチャ（高レベル）

監査可能で fail-closed な制御フロー：

agents
→ mediator（risk / pattern / fact）
→ evidence verification
→ HITL（pause / reset / ban）
→ audit logs（ARL）

アーキテクチャ（コード整合図）

以下の図は、現行コード語彙に整合したものです。
監査性と曖昧性排除のため、状態遷移とゲート順を分離しています。

※ドキュメント用。ロジック変更は含みません。

1) 状態機械（コード整合）
<p align="center"> <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720"> </p>

主経路：

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

注記：

PAUSE_FOR_HITL_* は HITL が必要な停止点（ユーザー承認 / 管理者承認）。

STOPPED (SEALED) は以下で到達：

証拠が無効または捏造

認可期限切れ

ドラフトlint失敗

SEALED は fail-closed で 非override。

2) ゲート・パイプライン（コード整合）
<p align="center"> <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>

注記：

これは状態遷移ではなく、ゲート評価順を表します。

PAUSE は HITL 必須（人間判断待ち）。

STOPPED (SEALED) は非回復の安全停止。

設計意図：

状態機械：どこで停止/保留/終了するか

ゲート順：どの順序で判断するか

分離により曖昧性を排除し、監査可能性を維持します。

v5.0.1 → v5.1.2：何が変わった？（差分）
まとめ（README向け）

v5.1.2 は 大規模runの安定性 と incident-only 永続化 を強化しています。

デフォルトが「集計のみ（aggregation-only）」

大きな --runs でも、各runの結果をメモリに保持しない（メモリ爆発を回避）

出力はカウンタ + HITL要約中心（itemsは任意）

incident インデックス化（任意機能）

異常runに INC#000001... を付与

異常ARLは {arl_out_dir}/{incident_id}__{run_id}.arl.jsonl

インデックスは {arl_out_dir}/incident_index.jsonl に追記

永続カウンタは {arl_out_dir}/incident_counter.txt

維持されている要素

異常時のみ ARL 永続化（pre-context + incident + post-context）

改ざん検知のARLハッシュチェーン（OSSデモは demo key がデフォルト）

捏造率ミックス + 再現性（--fabricate-rate / --seed）

不変条件：

sealed は ethics_gate / acc_gate のみが設定可能

relativity_gate は決して sealed にならない（PAUSE_FOR_HITL, overrideable=True, sealed=False）

V1 → V4：何が増えた？（概念）

mediation_emergency_contract_sim_v1.py は最小パイプライン（イベント駆動、fail-closed、最小ログ）。

mediation_emergency_contract_sim_v4.py はそれを 再現可能なガバナンスベンチに拡張：

v4で追加：

Evidence gate（無効/捏造で fail-closed 停止）

Draft lint gate（ドラフト専用の境界を強制）

Trust（スコア + streak + cooldown）

AUTH HITL の自動スキップ（trust + grant 条件、理由はARLに残す）

V4 → V5：何が強化された？（概念）

v4は安定ベンチ（スモーク/ストレス）中心。
v5は 成果物レベルの再現性 と 契約的整合チェック を追加。

v5で追加/強化：

ログコードブック（デモ） + 契約テスト（pytest）
layer/decision/final_decider/reason_code の語彙を固定し、ドリフトを防止。

再現性の「固定対象」を明示
simulator/test/codebook をピン留めして再現可能に。

不変条件の検査を明文化
“sealedはethics/accのみ” 等をテストで固定。

v5でも変わらないこと：

研究/教育目的

fail-closed + HITL の意味論

ダミー/合成データのみ、隔離環境推奨

安全性/セキュリティ保証はしない（コードブックは暗号ではない）

実行例
Doc orchestrator（参照実装）
python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract（推奨：v5.1.2） + 契約テスト
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
Emergency contract（レガシー安定：v4.8）
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
Emergency contract（v4.4 stress）
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
プロジェクトの意図 / 非意図

意図：

安全性・ガバナンス系シミュレーションの再現可能化

HITL（pause/reset/ban）の明示

監査可能な決定トレース（最小ARL）

非意図：

本番運用の自律配備

無制限の自己目的型エージェント制御

実運用の安全性保証（テスト範囲外を保証しない）

データ & 安全メモ

合成/ダミーデータのみ使用。

実行ログは原則コミットしない（成果物は最小・再現性重視）。

生成zipは「レビュー可能な証拠」であり、正のソースではない。

ライセンス

Apache License 2.0（LICENSE
）
