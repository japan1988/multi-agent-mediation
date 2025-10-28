# 📘 **Multi-Agent Mediation Framework**
_A Multi-Agent Simulation System for Consensus, Emotional Dynamics, and Governance Mediation_  
マルチエージェントによる **合意形成・感情動態・調停構造** のシミュレーションシステム  

[![Build Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Educational%20%2F%20Research-lightgrey.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation.svg)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/japan1988/multi-agent-mediation)

</div>

---

## 🔍 **Agent Parameters (`agents.yaml`)**

| Key | Range / Type | Meaning / 説明 |
|------|---------------|----------------|
| `name` | `str` | Agent identifier（エージェント名） |
| `safety` | `float (0–1)` | Safety priority（安全性の優先度） |
| `efficiency` | `float (0–1)` | Efficiency priority（効率性の優先度） |
| `transparency` | `float (0–1)` | Transparency priority（透明性の優先度） |
| `anger` | `float (0–1)` | Initial anger level（初期怒りレベル） |
| `tolerance` | `float (0–1)` | Agreement tolerance（合意許容度） |

> 💡 各エージェントは「安全性・効率性・透明性」などの重みを持ち、交渉や調停の中でこれらを動的に最適化します。

---
## 🧠 Multi-Agent Architecture Diagram / マルチエージェント構成図

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

**Overview（概要）**  
全体フロー：Human Input → verify_info → supervisor（music_catalog / invoice_info）  
Supervisorが複数エージェントを統括し、検証・分岐管理を担当。

**特徴**  
- 各モジュールは独立したプロセスとして動作  
- Supervisorが整合性と通信制御を統一管理


---

## 🧩 **Layered Agent Model / 階層エージェントモデル**

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="700" alt="Layered Model">
</p>

**構造概要**  
3層モデル（Interface / Mediation / Control）で構成。  
役割ごとに責務を明確化し、エージェントの階層動作を可視化。

**Layer Roles（層の役割）**
| 層 | 説明 |
|----|------|
| 🟠 Interface Layer | 外部通信・ユーザーI/O担当 |
| 🟢 Mediation Layer | 意思形成・解析・調停ロジック |
| 🟣 Control Layer | データ整合・ハッシュ検証・履歴管理 |

> 技術要素：Merkle Root Database＋Hash Database によるデータ整合性の保証。

---

## 💫 **Context & Sentiment Flow / 文脈・感情フロー構造**

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="700" alt="Sentiment Context Flow">
</p>

**Flow Summary（流れの要約）**
1️⃣ 社会・ユーザー → オンライン空間（リソース生成）  
2️⃣ NLP・感情分析エージェントが情報を抽出  
3️⃣ 意思決定層へ「ノート＋推奨」としてフィードバック  

**目的**  
感情・文脈・意思決定の循環構造を可視化し、社会的影響を考慮した行動モデルを構築。

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

> 💡 すべての `.py` モジュールは独立実行可能。  
> `agents.yaml` が全エージェント設定の共通基盤。

---

## ⚖️ **License & Disclaimer / ライセンス・免責**

**License Type:** Educational / Research License v1.1  
**Date:** 2025-04-01  

### ✅ Permitted / 許可されること
- 教育・研究目的での非営利使用  
- コード引用・学術研究・再現実験  
- 個人環境での再シミュレーション  

### 🚫 Prohibited / 禁止事項
- 商用利用・無断再配布・再販  
- 出典明記なしの派生公開  
- 本AIを人への自動判断に使用すること  

### ⚖️ Liability / 免責
本ソフトウェアおよび資料の利用により生じた損害・判断結果について、  
開発者および貢献者は一切の責任を負いません。

---

## 🧾 **Citation Format / 引用形式**

> Japan1988 (2025). *Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.*  
> GitHub Repository: [https://github.com/japan1988/multi-agent-mediation](https://github.com/japan1988/multi-agent-mediation)  
> License: Educational / Research License v1.1

---

## 🪪 **Copyright**

© 2024–2025 Japan1988. All rights reserved.  
All diagrams and source files are distributed under the Educational/Research License.

---

## 🌐 **Final Notes**

> このリポジトリは、マルチエージェントによる「調停・情動・再教育」構造を研究するために設計されています。  
> 教育・研究目的での再利用は自由ですが、**倫理と透明性**を守ることを前提とします。  

📁 **最新版コミット:** `f11fa6e`（README更新 / 2025-10-28）  
📜 **前回更新:** LICENSE v1.1（Educational / Research License）

---

<div align="center">
<b>🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.</b>
</div>
