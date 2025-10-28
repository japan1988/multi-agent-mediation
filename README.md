# 📘 **Multi-Agent Mediation Framework**

<p align="center">

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/issues)
[![GitHub release](https://img.shields.io/github/v/release/japan1988/multi-agent-mediation?color=blue)](https://github.com/japan1988/multi-agent-mediation/releases)
[![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)](./LICENSE)
[![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)](#)

</p>

---

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
