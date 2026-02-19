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
> 本リポジトリは研究・教育目的の参考実装（プロトタイプ）です。**侵入・監視・なりすまし・破壊・窃取など他者に害を与える行為**、
> またはそれらを容易にする目的での利用、ならびに**各サービス／実行環境の利用規約・ポリシー・法令・社内規程に反する利用**を禁止します（悪用厳禁）。
> 本プロジェクトは **教育・研究および防御的検証**（例：ログ肥大の緩和、fail-closed + HITL の挙動検証）を目的としており、
> **悪用手口の公開や犯罪助長を目的としません**。  
> 利用者は自己責任で、所属組織・サービス提供者・実行環境の **規約／ポリシー** を確認し、
> **外部ネットワークや実システム／実データに接続しない隔離環境でローカルのスモークテストから開始**してください（実システム／実データ／外部ネットワークに対するテストは禁止）。
> 本成果物は **無保証（現状有姿 / “AS IS”）** で提供され、適用法令上許される最大限の範囲で、作者は **いかなる損害についても責任を負いません**。
> （コード・ドキュメント・生成物〔例：zip バンドル〕の利用や第三者による誤用を含みます。）  
> **Codebook（辞書）に関する注意：** 同梱の codebook は **デモ／参考例**です。実運用で何らかの符号化・辞書化を行う場合は、
> 各社の **利用規約／ポリシー／社内規程** を必ず確認し、**隔離環境＋合成データ**で十分にテストした上で判断してください。
> codebook を **セキュリティ／暗号化／コンプライアンス保証** と誤解しないでください。  
> **テスト結果に関する注意：** スモークテスト／ストレステストの結果は、特定の環境・条件下での挙動確認に過ぎず、
> **安全性・正確性・適合性を保証するものではありません**。利用方法や運用・統合先の条件により結果は変わり得ます。

---

## 概要（Overview）

Maestro Orchestrator は、研究・教育目的のオーケストレーション・フレームワークで、次を優先します：

- **Fail-closed**  
  不確実／不安定／リスクがある場合 → 何も言わずに続行しない（止める／保留する）

- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な局面は、明示的にエスカレーションする

- **トレーサビリティ（Traceability）**  
  意思決定フローを最小 ARL ログで監査可能・再現可能にする

本リポジトリには、（ドキュメント系の）参照実装と、交渉・調停・ガバナンス風ワークフローの
シミュレーション・ベンチ、ゲート動作の検証コードが含まれます。

---

## クイックスタート（推奨ルート）

まずは 1 本のスクリプトから動かし、挙動とログを確認してから拡張してください。

### 1) 最新の緊急契約シミュレータ（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
2) 固定のスモークテスト（v4.8）を実行
bash

pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
3) 任意：エビデンス・バンドル（生成物）を確認
docs/artifacts/v4_8_artifacts_bundle.zip

注：エビデンス・バンドル（zip）は、テスト／実行により生成される成果物です。
正（カノニカル）な情報源は「生成スクリプト＋テスト」です。

アーキテクチャ（高レベル）
監査可能で fail-closed な制御フロー：

agents
→ mediator（risk / pattern / fact）
→ evidence verification
→ HITL（pause / reset / ban）
→ audit logs（ARL）



画像が表示されない場合
次を確認してください：

ファイルが docs/ 配下に存在するか

ファイル名が完全一致しているか（大小文字を区別）

表示しているブランチとリンク先が一致しているか

アーキテクチャ（コード整合の図）
以下の図は 現在のコード語彙に整合させています。
監査性と曖昧さの排除のため、状態遷移とゲート順序を分離しています。

ドキュメントのみ。ロジック変更はありません。

1) 状態機械（コード整合）
どこで PAUSE（HITL） するか、どこで 停止（SEALED） するか、最小限のライフサイクル遷移を示します。

<p align="center"> <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720"> </p>
主要パス

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

注記

PAUSE_FOR_HITL_* は明示的な Human-in-the-Loop の判断点（ユーザー承認／管理者承認）を表します。

STOPPED (SEALED) に到達する例：

無効／捏造のエビデンス

認可期限切れ

ドラフト lint 失敗

SEALED による停止は fail-closed で、設計上オーバーライド不可です。

2) ゲート・パイプライン（コード整合）
ライフサイクル状態遷移とは独立した、評価ゲートの 順序 を示します。

<p align="center"> <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>
注記

この図は ゲート順序 を表し、状態遷移そのものではありません。

PAUSE は HITL 必須（人間の判断待ち）を表します。

STOPPED (SEALED) は 回復不能な安全停止を表します。

設計意図

状態機械：どこで停止／保留するか？

ゲート順序：どの順番で判断を評価するか？

両者を分離して、曖昧さを避け、監査可能なトレーサビリティを保ちます。

更新情報（What’s new）
このプロジェクトは継続的に開発中です。

最新更新：GitHub の コミット履歴（Commits） と（タグがあれば）リリースノートを参照してください。

重要な追加・変更点は docs/（または CHANGELOG.md があればそこ）に記録します。

設計メモ：README は「推奨ルート」を明確にするため、意図的に最小構成にしています。

V1 → V4：実際に何が変わったか
mediation_emergency_contract_sim_v1.py は、最小構成のパイプライン（イベント駆動の直線的フロー、fail-closed 停止、最小監査ログ）を示します。

mediation_emergency_contract_sim_v4.py は、それを反復可能なガバナンス・ベンチに拡張し、
早期拒否や制御された自動化を導入します。

v4 で追加されたもの

Evidence gate（エビデンス・ゲート）
エビデンス・バンドルの基本検証。不正／無関係／捏造は fail-closed 停止を引き起こします。

Draft lint gate（ドラフト lint ゲート）
管理者確定の前に、ドラフトの意味（ドラフト専用の記述、スコープ境界）を強制します。

Trust system（スコア + 連続成功 + クールダウン）
HITL 成功で信頼を上げ、失敗で下げます。クールダウンはエラー後の危険な自動化を抑制します。遷移は ARL に記録されます。

AUTH HITL の自動スキップ（安全な摩擦低減）
信頼閾値 + 承認ストリーク + 有効な grant が揃うと、同一シナリオ／ロケーションに限り AUTH HITL をスキップできます（理由を ARL に記録）。

実行例（Execution examples）
Doc orchestrator（参照実装）

bash
python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract（v4.8）

bash
python mediation_emergency_contract_sim_v4_8.py
Emergency contract（v4.1）

bash
python mediation_emergency_contract_sim_v4_1.py
Emergency contract stress（v4.4）

bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
目的 / 非目的（Project intent / non-goals）
目的（Intent）
再現可能な安全・ガバナンス・シミュレーション

明示的な HITL セマンティクス（pause/reset/ban）

監査可能な意思決定トレース（最小 ARL）

非目的（Non-goals）
本番向けの自律運用（Production-grade autonomous deployment）

無制限・自己目的のエージェント制御

テストで明示された範囲を超える安全性主張

データ & 安全上の注意（Data & safety notes）
合成／ダミーデータのみを使用してください。

実行ログはコミットしないことを推奨します。エビデンス成果物は最小化し、生成可能性（再現性）を優先してください。

生成バンドル（zip）は レビュー可能なエビデンスであり、正（カノニカル）な情報源ではありません（生成スクリプト＋テストが正）。

ライセンス（License）
Apache License 2.0（LICENSE を参照）
