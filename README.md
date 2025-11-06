# 📘 **Multi-Agent Mediation Framework / マルチエージェント調停フレームワーク**

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/code%20style-Black-000000.svg?style=flat-square" alt="Code Style: Black">
  <img src="https://img.shields.io/badge/use--case-Education%20%26%20Research-blue.svg?style=flat-square" alt="Use Case">
  <img src="https://img.shields.io/badge/framework-Research%20AI%20Framework-blueviolet.svg?style=flat-square" alt="Framework">
  <img src="https://img.shields.io/badge/KAGE-Compatible-purple.svg?style=flat-square" alt="KAGE Compatible">
  <img src="https://img.shields.io/badge/status-Final%20Build%20v1.3.0-brightgreen.svg?style=flat-square" alt="Status">
</p>

---

This release is for reference only. No active or planned publication.
このリリースは参考用です。現時点で正式公開の予定はありません。

---

## 🎯 **Purpose / 目的**

Visualize the cyclical structure of emotion, context, and decision-making to construct behavior models that consider social influence.
Through negotiation, compromise, and mediation among multiple agents, the framework explores the **Social Equilibrium** point.

感情・文脈・意思決定の循環構造を可視化し、社会的影響を考慮した行動モデルを構築。
複数エージェント間の交渉・妥協・調停を通して、**社会的均衡点（Social Equilibrium）** を探る実験的AIフレームワーク。

> 🎯 The goal is “Ethical Control of Autonomous AI” and “Reproduction of Social Validity.”
> Even if emotions are simulated, the decision layer is safely sealed by ethical filters.

> 🎯 目的は「自律AIの倫理的制御」と「社会的妥当性の再現」。
> 感情を再現しても、意思決定層は倫理フィルターによって安全に封印されます。

---

## 🧠 **Concept Overview / 概念設計**

| Component / 構成要素              | Function / 機能       | Description / 説明                                                                        |
| ----------------------------- | ------------------- | --------------------------------------------------------------------------------------- |
| 🧩 **Mediation Layer**        | Mediation / 調停層     | Handles negotiation and consensus among agents / エージェント間の妥協・合意形成を担当                     |
| 💬 **Emotion Dynamics Layer** | Emotion / 感情層       | Adjusts negotiation strategies triggered by emotional change / 情動の変化をトリガとして交渉方針を変化      |
| ⚙️ **Governance Layer**       | Governance / 管理層    | Oversees ethics, consistency, and reproducibility / 倫理・整合性・再現性の統括                       |
| 🔁 **Re-Education Cycle**     | Re-learning / 再教育循環 | Evaluates behavior and regenerates social adaptation models / 行動パターンを評価・再学習し、社会適応モデルを生成 |

---

## 🗂️ **Repository Structure / ファイル構成**

| Path                                         | Type / 種別     | Description / 説明                                                                                                  |
| -------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------- |
| `agents.yaml`                                | Config        | Defines agent parameters / エージェントパラメータ定義                                                                          |
| `ai_mediation_all_in_one.py`                 | Core          | Main module integrating mediation algorithms / 調停アルゴリズム統合モジュール                                                    |
| `ai_alliance_persuasion_simulator.py`        | Simulator     | Alliance negotiation and persuasion simulation / 同盟交渉・説得シミュレーション                                                  |
| `ai_governance_mediation_sim.py`             | Simulator     | Governance and policy mediation model / 政策・ガバナンス調停モデル                                                             |
| `ai_pacd_simulation.py`                      | Experiment    | Phased re-education AI simulation / 段階的再教育AIシミュレーション                                                              |
| `ai_hierarchy_dynamics_full_log_20250804.py` | Logger        | Enhanced logging and hierarchy tracking / ログ強化・階層動態追跡モジュール                                                        |
| `sim_batch_fixed.py`                         | Batch Runner  | **New (Final Build)**: Unified batch execution, statistics & visualization / **最終ビルド追加**：実験一括実行・統計・可視化自動化（Final版） |
| `multi_agent_architecture_overview.webp`     | Diagram       | System overview / 構成図（全体）                                                                                         |
| `multi_agent_hierarchy_architecture.png`     | Diagram       | Layered architecture diagram / 階層モデル図                                                                             |
| `sentiment_context_flow.png`                 | Diagram       | Sentiment-context flow diagram / 感情フロー図                                                                           |
| `requirements.txt`                           | Dependency    | Python dependencies / Python依存関係                                                                                  |
| `.github/workflows/python-app.yml`           | Workflow      | CI / Lint workflow / CI・Lintワークフロー                                                                                |
| `LICENSE`                                    | License       | Educational / Research license / 教育・研究ライセンス                                                                       |
| `README.md`                                  | Documentation | This document / 本ドキュメント                                                                                           |

💡 All `.py` modules are independently executable.
💡 すべての `.py` モジュールは独立実行可能。

`sim_batch_fixed.py` enables **batch evaluation and visualization** in both raw and filtered modes.
`sim_batch_fixed.py` により **raw / filtered モードの一括評価・可視化** が可能に。

---

## 🧭 **Architecture Diagram / 構成図**

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

**Flow:**
Human Input → verify_info → supervisor → agents → logger
Supervisor manages consistency, compromise, and re-negotiation flow.
Supervisor が整合性・妥協・再交渉のフローを統一管理。

---

## 🌐 **Layered Agent Model / 階層エージェントモデル**

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| Layer / 層            | Role / 役割                    | Main Function / 主な機能                                                          |
| -------------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| **Interface Layer**  | External Input / 外部入力層       | Manages human input and log transmission / 人間の入力・ログ送信を管理                      |
| **Agent Layer**      | Cognition & Emotion / 認知・感情層 | Decision-making, emotion change, and dialogue control / 意思決定・感情変化・対話制御        |
| **Supervisor Layer** | Coordination / 統括層           | Manages global coordination, consistency, and ethical judgment / 全体調整・整合・倫理判定 |

---

## 🔬 **Sentiment Flow / 感情・文脈フロー**

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram">
</p>

1. **Perception（知覚）** — Convert input data into emotional factors / 入力データを感情因子に変換
2. **Context（文脈解析）** — Extract situational and social context / 交渉状況・社会的背景を抽出
3. **Action（行動生成）** — Integrate context and emotion to produce optimal actions / 文脈と感情を統合し、最適行動を出力

> 🧩 The “Ethical Seal” runs in all stages, automatically blocking harmful outputs.
> 🧩 すべての段階で「倫理フィルター（Ethical Seal）」が動作し、危険な出力を自動封印。

---

## ⚙️ **Execution Example / 実行例**

```bash
# Basic execution / 基本実行
python3 ai_mediation_all_in_one.py

# Run with logging / ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# Policy mediation mode / 政策調停モード
python3 ai_governance_mediation_sim.py --scenario policy_ethics

# Batch run (Final Build) / 一括バッチ実行（Final版）
python3 text/sim_batch_fixed.py --trials 10 --seed 42
```

---

## 🧾 **Citation Format / 引用形式**

**English:**
Japan1988 (2025). *Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.*
GitHub Repository: [https://github.com/japan1988/multi-agent-mediation](https://github.com/japan1988/multi-agent-mediation)
License: Educational / Research License v1.1

**日本語:**
Japan1988 (2025). *シャープパズル：マルチエージェント階層・感情動態シミュレーター*
GitHubリポジトリ: [https://github.com/japan1988/multi-agent-mediation](https://github.com/japan1988/multi-agent-mediation)
ライセンス: Educational / Research License v1.1

---

## ⚖️ **License & Disclaimer / ライセンス・免責**

**License Type:** Educational / Research License v1.1
**Date:** 2025-11-06

✅ **Permitted / 許可されること**

* Educational and research use (non-commercial) / 教育・研究目的での非営利使用
* Code citation, academic research, reproduction experiments / コード引用・学術研究・再現実験
* Personal re-simulation environments / 個人環境での再シミュレーション

🚫 **Prohibited / 禁止事項**

* Commercial use, redistribution, resale / 商用利用・無断再配布・再販
* Derivative publications without attribution / 出典明記なしの派生公開

⚖️ **Liability / 免責**
The developer and contributors are not responsible for any damages, ethical effects, or judgments resulting from the use of this software.
本ソフトウェアおよび資料の利用により生じた損害・倫理的影響・判断結果に関して、開発者および貢献者は一切の責任を負いません。

---

## 📈 **Release Highlights / 更新履歴**

| Version / バージョン    | Date / 日付      | Description / 主な変更内容                                                                                                                        |
| ------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0.0             | 2025-04-01     | Initial release: Core structure, emotion, mediation modules / 初回公開：構造・感情・調停モジュール統合                                                          |
| v1.1.0             | 2025-08-04     | Added hierarchy log and re-education module / 階層動態ログ・再教育モジュールを追加                                                                            |
| v1.2.0             | 2025-10-28     | Reorganized README and added OSS badges / README再構成・OSS公開用バッジ対応版                                                                            |
| **v1.3.0 (Final)** | **2025-11-06** | **Added sim_batch_fixed.py with automated aggregation & visualization (Final Build)**<br>**sim_batch_fixed.py追加・自動集計／可視化機能統合（Final Build）** |

---

## 🤝 **Contributing / 貢献ガイド**

1. Fork the repository / リポジトリをフォーク
2. Create a new branch / 新ブランチを作成

   ```bash
   git checkout -b feature/new-module
   ```
3. Edit and test your code / コードを編集・テスト
4. Create a Pull Request / Pull Request を作成

💡 Contributions for educational or research purposes are welcome — provided that safety, ethics, and transparency are maintained.
💡 教育・研究目的の貢献は歓迎します。ただし倫理的配慮・安全性・透明性の確保を前提とします。

---

<div align="center">
<b>🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.</b><br>
<em>© 2024–2025 Japan1988. All rights reserved.</em>
</div>

---

## ✅ **Change Summary / 変更概要**

* **Added:** `sim_batch_fixed.py` (Final Build Integration)
  **追加:** `sim_batch_fixed.py`（Final Build対応）
* **Updated:** Status badge → `Final Build v1.3.0`
  **更新:** バッジ・ステータスを `Final Build v1.3.0` に変更
* **Maintained:** File structure and sentiment flow unchanged
  **維持:** ファイル構成と感情・文脈フローは変更なし
* **Goal:** Final stable version for educational and research environments
  **目的:** 教育・研究向けに安定動作する最終ビルド版として整理

---
