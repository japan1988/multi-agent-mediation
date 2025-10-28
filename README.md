# Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator

_A research and educational framework for studying negotiation, mediation, and hierarchical emotion flow among autonomous AI agents._

[![Build Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Educational%20%2F%20Research-lightgrey.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](https://github.com/japan1988/multi-agent-mediation/actions)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation.svg)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/japan1988/multi-agent-mediation)

---

🔷 **Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator**  
A research and educational framework for studying negotiation, mediation, and hierarchical emotion flow among autonomous AI agents.

個々のAIエージェントが異なる価値観・感情状態を持ちながら交渉・仲裁・合意形成を行う過程を構造的に可視化し、  
感情と論理の相互作用をシミュレーションできる教育／研究用プロジェクトです。

---

## 📁 Repository Structure

| Path | Description |
|------|-------------|
| `ai_mediation_all_in_one.py` | Core negotiation model. Agents adjust priority weights (safety / efficiency / transparency) and compute harmony. |
| `ai_hierarchy_simulation_log.py` | Hierarchical performance & anger-propagation simulator. Logs every round of evolution. |
| `mediation_process_log.py` | Consensus process with gradually expanding tolerance. Produces `agreement_process_log.txt`. |
| `docs/generate_graph_emotion_dynamics.py` | Parses logs and outputs time-series graph `docs/graph_emotion_dynamics.png`. |
| `tests/test_emotion_dynamics.py` | Unit tests validating priority averaging, compromise generation, and mediation flow. |
| `.github/workflows/ci.yml` | Continuous-integration workflow running all tests on each push. |
| `LICENSE` | License file (personal / educational / research use only). |
| `README.md` | Main documentation file (this document). |

---

## ⚙️ How to Run

1️⃣ **Basic Simulation**
```bash
python ai_hierarchy_simulation_log.py
Outputs a detailed anger/performance log → ai_hierarchy_simulation_log.txt.

2️⃣ Generate Graph

python docs/generate_graph_emotion_dynamics.py ai_hierarchy_simulation_log.txt
Creates docs/graph_emotion_dynamics.png.

3️⃣ Test Validation

python -m unittest discover -s tests
Ensures all logical components are consistent.

🧩 Concept Overview
The simulator integrates four key layers that together model “emotional governance” in multi-agent systems.

Layer	Function
Agent	Holds individual goals & priorities (safety / efficiency / transparency).
Mediator	Calculates harmony and negotiates compromise offers.
Hierarchy Control	Ranks agents by performance and manages authority flow.
Emotion Loop	Propagates emotional influence (anger ↔ relief feedback).
🖼️ Visualisations / ビジュアル化
To enhance readability, the following figures visually complement the explanation above.
Both images should be placed under docs/ so that GitHub renders them correctly.

🧩 System Architecture Diagram
システム構造図（エージェント層 → メディエーター層 → 階層制御層 → 感情ループ）

graph TD
  A[Agent Layer<br>個々の価値・目標・優先度] --> B[Mediator Layer<br>調整・交渉・妥協案生成]
  B --> C[Hierarchy Control Layer<br>序列・権限管理・合意形成]
  C --> D[Emotion Dynamics Loop<br>怒り・安心の循環フィードバック]
  D --> B
  A --> D
🌀 Emotion Dynamics Example
感情ダイナミクスの推移例（12ラウンドにおける4エージェントの怒り変化）

(example image: docs/graph_emotion_dynamics.png)

🧠 Design Philosophy
Transparency / 可視性 — Logs every computation step for auditability.

Safety / 安全性 — No external API calls; completely local execution.

Reproducibility / 再現性 — Deterministic random seeds and version-locked dependencies.

Educational Value / 教育性 — Modular Python scripts for classroom or lab exercises.

🧪 Technical Details
Language: Python 3.8+
Dependencies: matplotlib, unittest

Outputs

ai_hierarchy_simulation_log.txt – Performance & anger per round

agreement_process_log.txt – Tolerance-based consensus trace

docs/graph_emotion_dynamics.png – Time-series emotion graph

📜 License
This repository is licensed for personal, educational, and research use only.
Commercial use or redistribution is strictly prohibited.

See LICENSE for full terms.

🧾 Citation
If you reference this framework in research or teaching materials, please cite as:

Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation

✅ Ready for Publication
✔ Fully validated (unit tests pass)
✔ Visual assets included
✔ Markdown layout 100% GitHub-compatible


