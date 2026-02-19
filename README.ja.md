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

> **Purpose / 目的（Research & Education）**  
> **JP:** 本リポジトリは研究・教育目的の参考実装（プロトタイプ）です。**侵入・監視・なりすまし・破壊・窃取など他者に害を与える行為**、またはそれらを容易にする目的での利用、ならびに**各サービス／実行環境の利用規約・ポリシー・法令・社内規程に反する利用**を禁止します（悪用厳禁）。本プロジェクトは **教育・研究および防御的検証（例：ログ肥大の緩和、fail-closed + HITL の挙動検証）** を目的としており、**悪用手口の公開や犯罪助長を目的としません**。  
> 利用者は自己責任で、所属組織・サービス提供者・実行環境の **規約／ポリシー** を確認し、**外部ネットワークや実システム／実データに接続しない隔離環境でローカルのスモークテストから開始**してください（実システム／実データ／外部ネットワークに対するテストは禁止）。本成果物は **無保証（現状有姿 / “AS IS”）** で提供され、作者は **いかなる損害についても責任を負いません**。  
> なお、**Codebook（辞書）はデモ／参考例**です。**そのまま使用せず**、利用者が自身の要件・脅威モデル・規約／ポリシーに合わせて **必ず自作**してください。  
> **EN:** This is a research/educational reference implementation (prototype). **Do not use it to execute or facilitate harmful actions** (e.g., exploitation, intrusion, surveillance, impersonation, destruction, data theft) or to violate any applicable **terms/policies, laws, or internal rules**. This project focuses on **education/research and defensive verification** (e.g., log growth mitigation and validating fail-closed + HITL behavior) and is **not intended to publish exploitation tactics** or facilitate wrongdoing.  
> Use at your own risk: verify relevant **terms/policies** and start with **local smoke tests in an isolated environment** (no external networks, no real systems/data). Contents are provided **“AS IS”, without warranty**, and the author assumes **no liability for any damages**.  
> The included **codebook is a demo/reference artifact—do not use it as-is; create your own** based on your requirements, threat model, and applicable policies/terms.

---

## Overview

Maestro Orchestrator は、**研究／教育**目的のオーケストレーション・フレームワークで、次を優先します：

- **Fail-closed**  
  不確実・不安定・リスクがあるなら → 黙って続行しない。

- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な決定は、明示的にエスカレーションする。

- **Traceability（追跡可能性）**  
  決定フローは最小限の ARL ログで監査可能・再現可能にする。

このリポジトリには、**参考実装（doc orchestrators）**と、交渉／調停／ガバナンス系ワークフローやゲーティング挙動を検証するための **シミュレーション・ベンチ**が含まれます。

---

## Quickstart（推奨ルート）

まずは1本だけ実行して、挙動とログを確認してから広げます。

### 1) 最新の emergency contract simulator（v4.8）を実行

```bash
python mediation_emergency_contract_sim_v4_8.py
2) ピン留め済みスモークテスト（v4.8）を実行
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py

3) 任意：evidence bundle（生成アーティファクト）を確認

docs/artifacts/v4_8_artifacts_bundle.zip

注：evidence bundle（zip）はテスト／実行により生成されるアーティファクトです。
真のソース・オブ・トゥルースは、生成スクリプトとテストです。

Architecture（高レベル）

監査可能で fail-closed な制御フロー：

agents
→ mediator（risk / pattern / fact）
→ evidence verification
→ HITL（pause / reset / ban）
→ audit logs（ARL）

画像が表示されない場合

以下を確認してください：

docs/ 配下にファイルが存在する

ファイル名が完全一致（大文字小文字を含めて一致）

いま見ているブランチとリンク先が同一ブランチ

Architecture（code-aligned diagrams）

以下の図は、現行コードの語彙に揃えた（code-aligned）ドキュメントです。
状態遷移とゲート順を分離して、監査性と曖昧さ回避を優先します。

ドキュメントのみ。ロジック変更なし。

1) State Machine（code-aligned）

実行が pause（HITL） する箇所と、**恒久停止（SEALED）**に至る箇所を示す最小ライフサイクル。

<p align="center"> <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720"> </p>

Primary execution path（主経路）

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

Notes（注記）

PAUSE_FOR_HITL_* は、ユーザー承認／管理者承認など HITL 前提の明示的停止点を表します。

STOPPED（SEALED） に到達する例：

無効／捏造の evidence

認可の期限切れ

draft lint failure

SEALED 停止は fail-closed で、設計上 override 不可です。

2) Gate Pipeline（code-aligned）

評価ゲートの順序（状態遷移とは独立）。

<p align="center"> <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>

Notes（注記）

この図は ゲート順を表し、状態遷移そのものは表しません。

PAUSE は HITL 必須（人間判断待ち）を意味します。

STOPPED（SEALED） は 非回復の安全停止を意味します。

Design intent（設計意図）

State Machine：どこで pause / terminate するか？

Gate Pipeline：どの順で評価するか？

この分離により、曖昧さを避け、監査可能なトレーサビリティを保ちます。

What’s new

本プロジェクトは継続的に更新されています。

最新更新：GitHub の Commits と（タグがあれば）リリースノートを参照してください。

重要な追加・変更は docs/（または存在するなら CHANGELOG.md）に必要に応じて記録します。

設計メモ：README は「推奨ルート（recommended path）」が迷子にならないよう、意図的にミニマルに保ちます。

V1 → V4：何が変わったか

mediation_emergency_contract_sim_v1.py は最小構成のパイプラインです：
線形のイベント駆動フロー、fail-closed 停止、最小の監査ログ。

mediation_emergency_contract_sim_v4.py はそれを、早期リジェクトと制御された自動化を加えた「繰り返し可能なガバナンス・ベンチ」に拡張します。

v4 で追加されたもの

Evidence gate
evidence bundle を基本検証。無効／無関係／捏造は fail-closed 停止。

Draft lint gate
管理者最終化の前に、draft-only セマンティクスとスコープ境界を強制。

Trust system（score + streak + cooldown）
HITL 成功で trust を上げ、失敗で下げる。cooldown で誤った自動化を抑止。遷移は ARL に記録。

AUTH HITL auto-skip（安全な摩擦低減）
trust 閾値 + 承認 streak + 有効 grant を満たす場合、同一シナリオ／同一ロケーションに限って AUTH HITL をスキップ可能（理由は ARL に記録）。

Execution examples（実行例）

Doc orchestrator（参考実装）

python ai_doc_orchestrator_kage3_v1_2_4.py


Emergency contract（v4.8）

python mediation_emergency_contract_sim_v4_8.py


Emergency contract（v4.1）

python mediation_emergency_contract_sim_v4_1.py


Emergency contract stress（v4.4）

python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json

Project intent / non-goals（目的／非目的）
Intent（目的）

再現可能な安全性・ガバナンス・シミュレーション

明示的な HITL セマンティクス（pause/reset/ban）

監査可能な決定トレース（最小 ARL）

Non-goals（非目的）

本番向けの自律運用（production-grade autonomous deployment）

無制限な自己指向エージェント制御

テストで明示されていない範囲まで含む安全性主張

Data & safety notes（データ／安全メモ）

合成（ダミー）データのみ使用してください。

実行ログのコミットは避け、evidence artifact は最小・再現可能に保つのが推奨です。

生成 bundle（zip）は レビュー可能な証跡として扱い、正本（canonical source）とは見なさないでください。

License

Apache License 2.0（LICENSE を参照）
