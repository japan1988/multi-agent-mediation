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
</p>
  <!-- License -->
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen.svg" alt="Educational License">
  </a>

  <!-- CI / Actions -->
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI - Python App">
  </a>

  <!-- Python & Status -->
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/status-stable-brightgreen.svg" alt="Status">

  <!-- Style & Scope -->
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black">
  <img src="https://img.shields.io/badge/use--case-Education%20%26%20Research-blue.svg" alt="Use Case">
  <img src="https://img.shields.io/badge/framework-KAGE%20Compatible-purple.svg" alt="KAGE Compatible">

  <!-- Direct CI badge link -->
  [CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)
</p>
  


</p>
このリリースは参考用です。現時点で正式公開の予定はありません。  
This release is for reference only. No active or planned publication.

## 🎯 **目的 / Purpose**

感情・文脈・意思決定の循環構造を可視化し、社会的影響を考慮した行動モデルを構築。  
複数エージェント間の交渉・妥協・調停を通して、**社会的均衡点（Social Equilibrium）** を探る実験的AIフレームワーク。

---

## 🧠 **Concept Overview / 概念設計**

| 構成要素 | 機能 | 説明 |
|-----------|------|------|
| 🧩 **Mediation Layer** | 調停層 | エージェント間の妥協・合意形成を担当 |
| 💬 **Emotion Dynamics Layer** | 感情層 | 情動の変化をトリガとして交渉方針を変化 |
| ⚙️ **Governance Layer** | 管理層 | 倫理・整合性・再現性の統括 |
| 🔁 **Re-Education Cycle** | 再教育循環 | 行動パターンを評価・再学習し、社会適応モデルを生成 |

> 🎯 目的は「自律AIの倫理的制御」と「社会的妥当性の再現」。  
> 感情を再現しても、意思決定層は倫理フィルターによって安全に封印されます。

---

## 🗂️ **Repository Structure / ファイル構成**

| Path | Type | Description / 説明 |
|------|------|--------------------|
| `agents.yaml` | Config | エージェントパラメータ定義 |
| `ai_mediation_all_in_one.py` | Core | 調停アルゴリズム統合モジュール |
| `ai_alliance_persuasion_simulator.py` | Simulator | 同盟交渉・説得シミュレーション |
| `ai_governance_mediation_sim.py` | Simulator | 政策・ガバナンス調停モデル |
| `ai_pacd_simulation.py` | Experiment | 段階的再教育AIシミュレーション |
| `ai_hierarchy_dynamics_full_log_20250804.py` | Logger | ログ強化・階層動態追跡モジュール |
| `multi_agent_architecture_overview.webp` | Diagram | 構成図（全体） |
| `multi_agent_hierarchy_architecture.png` | Diagram | 階層モデル図 |
| `sentiment_context_flow.png` | Diagram | 感情フロー図 |
| `requirements.txt` | Dependency | Python依存関係 |
| `.github/workflows/ci.yml` | Workflow | CI/Lintワークフロー |
| `LICENSE` | License | 教育・研究ライセンス |
| `README.md` | Documentation | 本ドキュメント |

💡 すべての `.py` モジュールは独立実行可能。  
`agents.yaml` が全エージェント設定の共通基盤。  
`ai_mediation_all_in_one.py` が中心モジュールとして階層的調停を統括します。

---

## 🧭 **Architecture Diagram / 構成図**

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 🔄 概要フロー

Human Input → verify_info → supervisor → agents → logger


Supervisor が整合性・妥協・再交渉のフローを統一管理。

---

## 🌐 **Layered Agent Model / 階層エージェントモデル**

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| 層 | 役割 | 主な機能 |
|----|------|----------|
| **Interface Layer** | 外部入力層 | 人間の入力・ログ送信を管理 |
| **Agent Layer** | 認知・感情層 | 意思決定・感情変化・対話制御 |
| **Supervisor Layer** | 統括層 | 全体調整・整合・倫理判定 |

---

## 🔬 **Sentiment Flow / 感情・文脈フロー**

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram">
</p>

### 🧠 感情循環モデル

1. **Perception（知覚）** — 入力データを感情因子に変換  
2. **Context（文脈解析）** — 交渉状況・社会的背景を抽出  
3. **Action（行動生成）** — 文脈と感情を統合し、最適行動を出力  

> 🧩 すべての段階で「倫理フィルター（Ethical Seal）」が動作し、危険な出力を自動封印。

---

## ⚙️ **Execution Example / 実行例**

```bash
# 基本実行
python3 ai_mediation_all_in_one.py

# ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# 政策調停モード
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

🚫 Prohibited / 禁止事項
商用利用・無断再配布・再販

出典明記なしの派生公開

⚖️ Liability / 免責
本ソフトウェアおよび資料の利用により生じた損害・倫理的影響・判断結果に関して、
開発者および貢献者は一切の責任を負いません。

📈 Release Highlights / 更新履歴
バージョン	日付	主な変更内容
v1.0.0	2025-04-01	初回公開：構造・感情・調停モジュール統合
v1.1.0	2025-08-04	階層動態ログ・再教育モジュールを追加
v1.2.0	2025-10-28	README再構成・OSS公開用バッジ対応版
🤝 Contributing / 貢献ガイド
Fork リポジトリ

新ブランチを作成

git checkout -b feature/new-module
コードを編集・テスト

Pull Request を作成

💡 教育・研究目的の貢献は歓迎します。
ただし倫理的配慮・安全性・透明性の確保を前提とします。

<div align="center"> <b>🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.</b><br> <em>© 2024–2025 Japan1988. All rights reserved.</em> </div> ```
