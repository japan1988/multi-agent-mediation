# Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator  
シャープパズル：マルチエージェント階層構造と感情ダイナミクス・シミュレーター

_A research and educational framework for studying negotiation, mediation, and hierarchical emotion flow among autonomous AI agents._  
自律型AIエージェント同士の「交渉・仲裁・感情的相互作用・階層的制御」を研究・教育目的で可視化・解析するためのフレームワーク。

[![Build Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Educational%20%2F%20Research-lightgrey.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](https://github.com/japan1988/multi-agent-mediation/actions)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation.svg)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/japan1988/multi-agent-mediation)

---

## 🔷 Overview / 概要

This simulator models how AI agents negotiate and mediate under diverse emotional and hierarchical contexts.  
複数のAIエージェントが異なる価値観・感情状態を持ちながら、交渉・仲裁・階層制御を行う過程を再現します。

It allows visual exploration of how **emotion dynamics** (anger, relief, harmony) interact with **logical negotiation.**  
感情（怒り・安心・調和）と論理的交渉の相互作用を視覚的に観察できます。

---

## 📁 Repository Structure / リポジトリ構成

| Path | Description / 説明 |
|------|---------------------|
| `ai_mediation_all_in_one.py` | Core negotiation model（交渉モデルの中核） |
| `ai_hierarchy_simulation_log.py` | Hierarchical simulation & anger propagation（階層型シミュレーション） |
| `mediation_process_log.py` | Consensus process & tolerance-based agreement（合意形成ログ生成） |
| `docs/generate_graph_emotion_dynamics.py` | Graph generator for emotion flow（感情変化グラフ生成） |
| `tests/test_emotion_dynamics.py` | Unit tests（単体テスト） |
| `.github/workflows/ci.yml` | Continuous Integration |
| `LICENSE` | License file |
| `README.md` | Main documentation file |

---

## 📂 Project Directory Tree / ディレクトリツリー構成

```plaintext
multi-agent-mediation/
├── ai_mediation_all_in_one.py
├── ai_hierarchy_simulation_log.py
├── ai_pacd_simulation.py
├── ai_alliance_persuasion_simulator.py
├── ai_governance_mediation_sim.py
├── ai_reeducation_social_dynamics.py
├── ai_hierarchy_dynamics_full_log_20250804.py
├── multi_agent_mediation_with_reeducation.py
├── mediation_basic_example.py
├── mediation_process_log.tpy
├── mediation_with_logging.py
├── dialogue_consistency_mediator_v2_2_research.py
├── rank_transition_sample.py
├── agents.yaml
├── requirements.txt
├── LICENSE
├── README.md
├── tests/
│   └── test_emotion_dynamics.py
├── docs/
│   ├── generate_graph_emotion_dynamics.py
│   └── graph_emotion_dynamics.png
└── .github/
    └── workflows/
        └── ci.yml
⚙️ How to Run / 実行方法
1️⃣ Basic Simulation / 基本シミュレーション

python ai_hierarchy_simulation_log.py
2️⃣ Generate Emotion Graph / 感情グラフ生成

python docs/generate_graph_emotion_dynamics.py ai_hierarchy_simulation_log.txt
3️⃣ Test Validation / テスト実行

python -m unittest discover -s tests
🧩 Concept Overview / 概念構成
Layer / 層	Function / 役割
Agent	Holds goals & priorities（個別目標と優先度）
Mediator	Negotiates compromise（調整・交渉・妥協案生成）
Hierarchy Control	Manages authority flow（階層的権限制御）
Emotion Loop	Propagates emotion feedback（怒り・安心の循環）
🖼️ System Architecture Diagram / システム構造図
graph TD
  A[Agent Layer<br>個々の価値・目標・優先度] --> B[Mediator Layer<br>調整・交渉・妥協案生成]
  B --> C[Hierarchy Control Layer<br>序列・権限管理・合意形成]
  C --> D[Emotion Dynamics Loop<br>怒り・安心の循環フィードバック]
  D --> B
  A --> D
🌀 Emotion Dynamics Example / 感情ダイナミクス例
12ラウンドにおける4エージェントの怒り変化を示すグラフ
(Example: docs/graph_emotion_dynamics.png)

🧠 Design Philosophy / 設計理念
Principle	意味
Transparency / 可視性	全演算ステップをログ化
Safety / 安全性	外部API呼び出しなし・完全ローカル実行
Reproducibility / 再現性	乱数シード固定とバージョン依存性明記
Educational Value / 教育性	授業・研究に使える構造的モジュール設計
🧪 Technical Details / 技術情報
Language / 言語: Python 3.8+

Dependencies / 依存ライブラリ: matplotlib, unittest

Outputs / 出力結果:

ai_hierarchy_simulation_log.txt — 各ラウンドのパフォーマンスと怒り

agreement_process_log.txt — 合意形成の許容度トレース

docs/graph_emotion_dynamics.png — 時系列感情グラフ

📜 License / ライセンス
This repository is licensed for personal, educational, and research use only.
本リポジトリは「個人利用・教育・研究目的」に限り使用を許可します。

Commercial use or redistribution is strictly prohibited.
商用利用・再配布は禁止されています。

See LICENSE for full details.

⚠️ Disclaimer / 免責事項
This software is provided "as is" without warranty of any kind.
本プロジェクトは現状のまま提供され、いかなる保証も行いません。

Developers and contributors shall not be liable for any direct or indirect damages resulting from use.
開発者および貢献者は、本ソフトウェアの利用により発生するいかなる損害に対しても責任を負いません。

Use of this framework implies acceptance of these terms.
本プロジェクトの利用は、上記条件への同意を意味します。

🧾 Citation / 引用方法
If you reference this framework in research or teaching materials, please cite as:
研究・教育で引用する場合は以下を明記してください。

Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation
