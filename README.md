# 📘 **Multi-Agent Mediation Framework**

<p align="center">
  <!-- 📊 Repository Status -->
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
  <!-- ⚙️ Technical Meta -->
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/code%20style-Black-000000.svg?style=flat-square" alt="Code Style: Black">
  <img src="https://img.shields.io/badge/use--case-Education%20%26%20Research-blue.svg?style=flat-square" alt="Use Case: Education & Research">
  <img src="https://img.shields.io/badge/framework-Research%20AI%20Framework-blueviolet.svg?style=flat-square" alt="Framework: Research AI">
  <img src="https://img.shields.io/badge/KAGE-Compatible-purple.svg?style=flat-square" alt="KAGE Compatible">
</p>

<!-- Direct CI badge text link -->
[CI Status (Python App)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)

---

このリリースは参考用です。現時点で正式公開の予定はありません。  
This release is for reference only. No active or planned publication.

---

## 🧩 System Overview / システム概要

This repository demonstrates a **multi-agent mediation framework** that models  
negotiation, compromise, and ethical control between agents with simple emotion signals.  
本リポジトリは、感情シグナルと倫理フィルターを組み合わせた  
**多エージェント調停フレームワーク**の実験実装です。

---

## 🎯 **目的 / Purpose**

感情・文脈・意思決定の循環構造を可視化し、社会的影響を考慮した行動モデルを構築。  
複数エージェント間の交渉・妥協・調停を通して、  
**社会的均衡点（Social Equilibrium）** を探る実験的 AI フレームワークです。

The goal is to visualize how “feelings, context, and actions” interact,  
and to explore possible social balance points through repeated mediation between agents.

---

## 🧠 **Concept Overview / 概念設計**

| 構成要素 | 機能 | 説明 |
|-----------|------|------|
| 🧩 **Mediation Layer** | 調停層 | エージェント間の妥協・合意形成を担当 |
| 💬 **Emotion Dynamics Layer** | 感情層 | 情動の変化をトリガとして交渉方針を変化 |
| ⚙️ **Governance Layer** | 管理層 | 倫理・整合性・再現性の統括 |
| 🔁 **Re-Education Cycle** | 再教育循環 | 行動パターンを評価・再学習し、社会適応モデルを生成 |

> 🎯 目的は「自律 AI の倫理的制御」と「社会的妥当性の再現」。  
> 感情を再現しても、意思決定層は倫理フィルターによって安全に封印されます。

---

## 🗂️ **Repository Structure / ファイル構成**

| Path | Type | Description / 説明 |
|------|------|--------------------|
| `agents.yaml`                    | Config   | エージェント設定パラメータ定義 |
| `ai_mediation_all_in_one.py`     | Core     | 調停アルゴリズム統合モジュール |
| `ai_alliance_persuasion_sim.py`  | Simulator| 説得・同盟形成シミュレーション |
| `ai_governance_mediation_sim.py` | Simulator| 政策・ガバナンス調停シミュレーション |
| `ai_hierarchy_dynamics_full_log_*.py` | Logger | 階層の動態ログ取得・再生 |
| `docs/multi_agent_architecture_overview.webp` | Diagram | システム全体構成図 |
| `docs/multi_agent_hierarchy_architecture.png` | Diagram | 階層アーキテクチャ図 |
| `docs/sentiment_context_flow.png`           | Diagram | 感情・文脈フローダイアグラム |
| `.github/workflows/python-app.yml` | CI      | GitHub Actions 設定 |
| `requirements.txt`                | Dependency | Python 依存関係 |
| `LICENSE`                         | License | 教育・研究ライセンス |
| `README.md`                       | Doc     | 本ドキュメント |

※ すべての `.py` モジュールは単体実行可能です。  
`ai_mediation_all_in_one.py` が中核モジュールとして調停シナリオを統合します。

---

## 🧱 **Architecture Diagram / 構成図**

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

- Human Input → verify_info → supervisor → agents → logger  
- Supervisor が整合性・安定性・再交渉のフローを統一管理します。

---

## 🧩 **Layered Agent Model / 階層エージェントモデル**

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| Layer | Role | What it does |
|-------|------|--------------|
| **Interface Layer**  | Input from outside | Receives human input and sends logs. |
| **Agent Layer**      | Thinking & feeling | Controls decisions, simple emotions, and dialogue. |
| **Supervisor Layer** | Overall check      | Watches the whole system, checks consistency, and runs basic ethics checks. |

---

## 🔬 **Sentiment Flow / 感情・文脈フロー**

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram">
</p>

### 🧠 Emotion Cycle Model

1. **Perception** — Takes the input and turns it into simple “emotion signals”.  
2. **Context** — Looks at the situation and background of the negotiation.  
3. **Action** — Combines the situation and emotion, then chooses the next action.

> 🧩 At every step, the **Ethical Seal** checks the result and blocks outputs that may be harmful.

---

## ⚙️ **Execution Example / 実行例**

```bash
# 基本実行 / Basic run
python3 ai_mediation_all_in_one.py

# ログ付き実行 / Run with logging
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# 政策調停モード / Policy mediation mode
python3 ai_governance_mediation_sim.py --scenario policy_ethics
🧾 Citation Format / 引用形式
Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation
License: Educational / Research License v1.1

⚖️ License & Disclaimer / ライセンス・免責
License Type: Educational / Research License v1.1
Date: 2025-04-01

✅ Permitted / 許可されること
教育・研究目的での非営利使用

コード引用・学術研究・再現実験

個人環境での再シミュレーション

You may:

Use this project for non-commercial education and research.

Use parts of the code in academic work, with proper citation.

Run and modify it in your own local environment.

🚫 Prohibited / 禁止事項
商用利用・無断再配布・再販

出典明記なしの派生公開

You may not:

Use this project for commercial services or products.

Redistribute or resell it without permission.

Publish modified versions without clear credit to the original author.

⚖️ Liability / 免責
本ソフトウェアおよび資料の利用により生じた損害・倫理的影響・判断結果に関して、
開発者および貢献者は一切の責任を負いません。

This project is for learning and research.
The developers and contributors are not responsible for any damage, wrong decisions,
or ethical problems that come from using this software or its documents.

📈 Release Highlights / 更新履歴
Version	Date	Main changes / 主な変更内容
v1.0.0	2025-04-01	初回公開：構造・感情・調停モジュール統合
v1.1.0	2025-08-04	階層動態ログ・再教育モジュールを追加
v1.2.0	2025-10-28	README 再構成・OSS 公開用バッジ対応版
🤝 Contributing / 貢献ガイド
Fork リポジトリ / Fork this repository.

新ブランチを作成 / Create a new branch:

git checkout -b feature/new-module
コードを編集・テストを追加 / Change the code and add simple tests.

Pull Request を作成し、以下を説明 / Open a Pull Request and explain:

何を変更したか / what you changed

なぜ有用か / why it is useful

Educational and research contributions are welcome.
Please always care about ethics, safety, and clear explanations.

