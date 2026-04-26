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
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="Python App CI">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main" alt="Tasukeru Advisory">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

このリポジトリは、**研究・教育目的**で提供されています。

主に以下を示すことを目的としています。

- オーケストレーション制御パターン
- 調停 / ガバナンス・シミュレーション構造
- fail-closed ガードレール
- 監査 / 再現を意識した設計
- HITL（Human-in-the-Loop）エスカレーションの意味論

これは、**本番運用への対応、完成度、またはあらゆるポリシーを網羅することを保証するものではありません**。

---

## 概要

Maestro Orchestrator は、エージェント型ワークフローが不確実性、リスク、人間判断の境界に直面したとき、どのように振る舞うべきかを研究するための、安全優先のオーケストレーション・フレームワークです。

中核となる立場はシンプルです。

> **不確実なら止まる。危険なら人に返す。**

このリポジトリには、保護されたオーケストレーション挙動を研究するための、複数の実験的・バージョン付きシミュレーター、ベンチマーク実行スクリプト、監査 / ログ例、テストスイートが含まれています。

---

## このリポジトリに含まれるもの

このリポジトリには、現在以下のようなものが含まれています。

- オーケストレーションおよびドキュメント・ワークフロー・シミュレーター
- 調停 / ガバナンス交渉シミュレーション
- 緊急契約および HITL 制御付きワークフロー・シミュレーション
- ベンチマーク実行スクリプトと評価補助ツール
- 監査ログ / codebook の例
- 回帰テストおよび不変条件重視の pytest スイート

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

## リポジトリ構成

このリポジトリには、以下の両方が含まれています。

- 現在のテストや workflow から参照される対象
- 比較やトレーサビリティのために保持されている履歴的・バージョン付き実験ファイル

そのため、一部のモジュールは比較的新しい参照点であり、別のモジュールはアーカイブ的または初期段階の変種として残されています。

このリポジトリには複数の実験とバージョン付きファイルが含まれているため、すべてのファイルをプロジェクト全体の唯一の正規実装として読むべきではありません。

現在の挙動を確認する際は、通常、以下の組み合わせを見るのが最も信頼できます。

- `tests/` にある現行テスト
- `.github/workflows/` にある現行 CI workflow
- 最新の維持対象シミュレーター / オーケストレーター
- ベンチマーク実行スクリプト
- codebook / log 定義

---

## Quick start

環境を作成し、依存関係をインストールします。

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

フルテストを実行します。

```bash
pytest -q
```

---

## Quick test commands

代表的な個別実行例:

```bash
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q tests/test_ai_doc_orchestrator_kage3_v1_3_5.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
```

---

## Continuous Integration

主要 CI は、以下の workflow で lint、検証、pytest を実行します。

```text
.github/workflows/python-app.yml
```

このメイン CI workflow は、リポジトリが設定された Python バージョン上で実行可能かつテスト可能な状態を保つことを目的としています。

現在の Python 対象:

```text
Python 3.10
Python 3.11
```

追加の advisory や分析 workflow は、以下に存在する場合があります。

```text
.github/workflows/
```

---
## Tasukeru Advisory（助ける君）

**Tasukeru（助ける君）** は、軽量な品質・安全性・ロジックレビューのための non-blocking advisory workflow です。

このリポジトリの保守を補助するために、静的解析、依存関係チェック、workflow summary、プロジェクト固有のロジックチェックから advisory signal を収集します。

Tasukeru は、**本番レベルのセキュリティ保証ではありません**。  
開発中のコード品質、よくある Python 上の問題、依存関係リスク、リポジトリ整合性、advisory finding を確認するための補助層です。

現在の Tasukeru の主な機能:

- **Ruff advisory scan**  
  Python のスタイル問題、未使用 import、import 位置の問題、構文レベルの問題、その他 lint finding を検出します。

- **Bandit advisory scan**  
  非暗号用途の乱数使用、`assert` 使用、危険になり得る実装パターンなど、Python の一般的なセキュリティ警告を報告します。

- **pip-audit dependency scan**  
  Python 依存関係に既知の脆弱性 advisory がないか確認します。

- **Tasukeru logic review**  
  未解決のマージ競合記号、ARL 不変条件違反、ライセンスポリシーの不整合、workflow 上の危険要因、副作用候補など、プロジェクト固有の整合性ルールを確認します。

- **ARL / governance invariant advisory checks**  
  audit-style record が、canonical decision、必須 ARL key、RFL 非封印、sealed-state semantics などの安全契約に従っているかを確認します。

- **GitHub Actions summary 出力**  
  workflow run の中に、人間が読みやすい advisory summary を生成します。

- **Artifact 出力**  
  raw scan result を後から確認できるように advisory log をアップロードします。

Tasukeru は意図的に **advisory / non-blocking** として扱われます。

目的は、研究・検証の反復を止めることではなく、問題を早い段階で見える化することです。

要約すると:

> **Tasukeru はリポジトリのレビューを補助するが、人間の判断を置き換えるものではありません。**
---

## 設計上の立場

このリポジトリは、fail-closed の考え方を中心にしています。

- 不確実なら止まる
- 危険なら人間へエスカレーションする
- 監査可能性を保持する
- 必要な場所では人間判断を残す

各シミュレーションに共通して現れるテーマは次の通りです。

- 固定されたゲート順序
- 明示的な stop / pause 意味論
- 再現性を重視したテスト
- 構造化ログと replayability
- HITL エスカレーション境界

---

## 安全性とスコープ

このリポジトリは **研究プロトタイプ** です。

以下を目的としていません。

- 本番環境での自律意思決定
- 人間の監督なしの現実世界制御
- 法務、医療、金融、規制領域に関する助言
- 実在個人情報や機密業務データの処理
- 完全または普遍的な安全性カバレッジの提示

このリポジトリ内の例は、次のようなものとして読むのが適切です。

- 研究シミュレーション
- 教育用リファレンス
- ガバナンス / 安全性テストベンチ
- fail-closed と HITL 設計の実装例

---

## テストと挙動

このリポジトリでは、テストがシミュレーターやオーケストレーション・ロジックの期待挙動を定義している場合があります。

挙動を確認する際は、実装ファイルだけでなく、対応するテストも一緒に読む方が正確です。

例:

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py
```

これは特に、以下を確認する場合に重要です。

- gate invariant
- reason-code の期待値
- HITL transition
- sealed / non-sealed の挙動
- 再現性チェック
- benchmark 期待値

---

## Notes

一部ファイルは、履歴比較、再現性、またはバージョン付き実験のために保持されています。

バージョン番号が新しいことは、そのファイルが常に最優先の推奨 entry point であることを意味しません。

`archive/` 配下のファイルは、現行テストやドキュメントから明示的に参照されていない限り、通常は履歴資料または参考資料として扱うべきです。

---

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

---

## License / ライセンス

このリポジトリは分離ライセンス方式を採用しています。

- ソースコード: **Apache License 2.0**
- ドキュメント、図、研究資料: **CC BY-NC-SA 4.0**

詳細は [LICENSE_POLICY.md](./LICENSE_POLICY.md) を参照してください。
