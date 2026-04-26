
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
    <img src="https://img.shields.io/badge/license-Apache--2.0-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

## 概要

Maestro Orchestrator は、複数エージェント、複数手法、または複数の制御段を監督するための**研究・教育向けオーケストレーション・フレームワーク**です。

中核となる立場はシンプルです。

> **不確実なら止まる。危険なら人に返す。**

このリポジトリは主に次のような構造や挙動を示すためのものです。

- オーケストレーション制御パターン
- 調停 / ガバナンス・シミュレーション構造
- fail-closed ガードレール
- 監査 / 再現を意識したログ設計
- HITL（Human-in-the-Loop）エスカレーションの意味論

これは**本番運用レベルの完成品や包括的ポリシー実装を約束するものではありません**。

---

## このリポジトリの特徴

- ガバナンス系ワークフロー向けの **fail-closed + HITL オーケストレーション・ベンチ**
- シード付き実行と `pytest` ベースの contract check を備えた **再現可能なシミュレーター**
- 最小 ARL ログによる **監査可能なトレース**
- オーケストレーション / ゲーティング挙動の **実装リファレンス**
- バージョン差分や比較検証のための **複数世代のシミュレーター群**

特徴は、**fail-closed（安全側に倒す）** を前提にしている点です。

- **STOP**: エラー / 危険 / 未定義仕様を検知したら停止
- **REROUTE**: 明示的に安全と判断できる場合のみ再ルーティング
- **HITL**: 曖昧・高リスクは人間判断へエスカレーション

---

## 位置づけ（安全優先）

Maestro Orchestrator は、タスク完遂率を最大化するよりも、**不安全 / 未定義の実行を防ぐこと**を優先します。

リスクや曖昧さが検知された場合、`PAUSE_FOR_HITL` または `STOPPED` に **fail-closed** し、監査ログに「なぜそうなったか」を残します。

**トレードオフ:**  
安全性とトレーサビリティを優先するため、デフォルトでは**止まりやすい（over-stop）**設計になり得ます。

---

## 🚫 非目的（IMPORTANT）

このリポジトリは **研究プロトタイプ** です。以下は明確に **対象外** です。

- **本番運用レベルの自律意思決定**
- **現実ユーザーに対する persuasion / reeducation の最適化**
- **実在個人情報（PII）** や機密業務データを含むプロンプト / テスト / ログの取り扱い
- 医療 / 法務 / 金融などの規制領域に対する **コンプライアンス保証や法的助言**
- 普遍的な安全基準や網羅的なポリシーカバレッジの主張

このリポジトリは、次のようなものとして読むのが適切です。

- **研究プロトタイプ**
- **教育用リファレンス**
- **ガバナンス / 安全性シミュレーションベンチ**
- **fail-closed / HITL 設計の実装例**

---

## リポジトリの中身

このリポジトリには、主に次のような種類のファイルが含まれています。

- ドキュメント系オーケストレーター
- 調停 / ガバナンス・シミュレーター
- 緊急契約・HITL 制御付きワークフロー・シミュレーター
- ベンチマーク実行スクリプト
- 評価 / 分析補助スクリプト
- ARL / codebook / ログ形式の例
- 回帰テスト・不変条件テスト

代表的なファイル例:

- `ai_doc_orchestrator_kage3_v1_3_5.py`
- `ai_doc_orchestrator_with_mediator_v1_0.py`
- `mediation_emergency_contract_sim_v5_1_2.py`
- `ai_governance_mediation_sim.py`
- `ai_mediation_all_in_one.py`
- `run_benchmark_kage3_v1_3_5.py`
- `run_benchmark_profiles_v1_0.py`
- `rank_transition_sample.py`

主なディレクトリ例:

- `.github/workflows/`
- `archive/`
- `benchmarks/`
- `docs/`
- `evaluation/`
- `mediation_core/`
- `scripts/`
- `tests/`

---

## リポジトリ構成の考え方

このリポジトリには、**現在参照される実装**と、**比較・履歴保持のためのバージョン付き実験ファイル**の両方が含まれます。

そのため、すべての `.py` ファイルが同じ優先度の「唯一の正解実装」ではありません。

読み方としては、基本的に次を優先するのが自然です。

1. `tests/` にある現行テスト
2. `.github/workflows/` にある現行 CI
3. 最新系のシミュレーター / オーケストレーター
4. `evaluation/` や codebook / log 定義
5. `archive/` 以下の旧版・参考版

---

## Quick links

- **英語 README:** [README.md](README.md)
- **日本語 README:** [README.ja.md](README.ja.md)
- **ドキュメント一覧:** [docs/README.md](docs/README.md)
- **推奨シミュレーター:** `mediation_emergency_contract_sim_v5_1_2.py`
- **Contract test:** `tests/test_v5_1_codebook_consistency.py`
- **Stress metrics test (v5.1.2):** `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
- **Pytest ARL hook:** `tests/conftest.py`
- **最新の mixed stress summary:** `stress_results_v5_1_2_10000_mixed.json`
- **従来の安定ベンチ:** `mediation_emergency_contract_sim_v4_8.py`
- **Doc orchestrator（mediator reference）:** `ai_doc_orchestrator_with_mediator_v1_0.py`
- **Doc orchestrator contract test:** `tests/test_doc_orchestrator_with_mediator_v1_0.py`

---

## セットアップ

依存を入れる例です。

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
requirements-dev.txt には requirements.txt が含まれている前提です。

クイックテスト
フルテスト:

pytest -q
代表的な個別テスト:

pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_3_5.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
CI
CI は主に以下の workflow で実行されます。

.github/workflows/python-app.yml
この workflow では、少なくとも以下を確認します。

依存インストール

workflow 自体の yamllint

pytest 実行

環境差分の確認のため、複数 Python バージョンで回す構成です。

設計上の共通テーマ
このリポジトリの各シミュレーターには差分がありますが、よく出てくる共通テーマは次の通りです。

固定ゲート順序

明示的な RUN / PAUSE_FOR_HITL / STOPPED

fail-open より fail-closed を優先

ログ / 監査 / 再現性の重視

人間判断の境界を明示する設計

実験コードと検証コードの併走

テストと実装の見方
このリポジトリでは、テストが実装の期待挙動をかなり強く規定している箇所があります。

したがって、挙動を確認する際は、

実装ファイルだけを見る

README だけを見る

よりも、対象実装 + 対応テスト をセットで見る方が正確です。

例:

ai_doc_orchestrator_with_mediator_v1_0.py

tests/test_doc_orchestrator_with_mediator_v1_0.py

注意事項
一部ファイルは、研究中の比較対象や履歴保持のために残されています。

バージョン番号が新しいことと、常に最優先の推奨対象であることは同義ではありません。

ファイル名に近い内容でも、テストや workflow の参照先が異なる場合があります。

archive/ は原則として現行の主要参照先ではなく、比較・保管目的です。

Language
English README: README.md

Japanese README: README.ja.md

License
See LICENSE.

Repository license: Apache-2.0
Policy intent: Educational / Research

