🔷 Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator
A research and educational framework for studying negotiation, mediation, and hierarchical emotion flow among autonomous AI agents.

個々のAIエージェントが異なる価値観・感情状態を持ちながら交渉・仲裁・合意形成を行う過程を構造的に可視化し、
感情と論理の相互作用をシミュレーションできる教育／研究用プロジェクトです。

📁 Repository Structure
Path	Description
ai_mediation_all_in_one.py	Core negotiation model. Agents adjust priority weights (safety / efficiency / transparency) and compute harmony.
ai_hierarchy_simulation_log.py	Hierarchical performance & anger-propagation simulator. Logs every round of evolution.
mediation_process_log.py	Consensus process with gradually expanding tolerance. Produces agreement_process_log.txt.
docs/generate_graph_emotion_dynamics.py	Parses a log from ai_hierarchy_simulation_log.py and outputs a time-series graph (docs/graph_emotion_dynamics.png).
tests/test_emotion_dynamics.py	Unit tests validating priority averaging, compromise generation, and mediation flow.
.github/workflows/ci.yml	Continuous-integration workflow running all tests on each push.
LICENSE	License file (personal / educational / research use only).
README.md	Main documentation file (this document).
⚙️ How to Run
1️⃣ Basic Simulation
python ai_hierarchy_simulation_log.py
Outputs a detailed anger/performance log and saves ai_hierarchy_simulation_log.txt.

2️⃣ Generate Graph
python docs/generate_graph_emotion_dynamics.py ai_hierarchy_simulation_log.txt
Creates docs/graph_emotion_dynamics.png.

3️⃣ Test Validation
python -m unittest discover -s tests
Ensures all logical components are consistent.

🧩 Concept Overview
The simulator integrates four key layers that together model “emotional governance” in multi-agent systems.

Agent Layer
   ↓
Mediator Layer
   ↓
Hierarchy Control Layer
   ↓
Emotion Dynamics Loop
Each layer has defined roles:

Layer	Function
Agent	Holds individual goals & priorities (safety / efficiency / transparency).
Mediator	Calculates harmony and negotiates compromise offers.
Hierarchy Control	Ranks agents by performance and manages authority flow.
Emotion Loop	Propagates emotional influence (anger ↔ relief feedback).
🖼️ Visualisations / ビジュアル化
To enhance readability, the following figures visually complement the explanation above.
Both images should be placed under docs/ so that GitHub renders them correctly.

System Architecture Diagram
システム構造図（エージェント層 → メディエーター層 → 階層制御層 → 感情ループ）

Emotion Dynamics Example
感情ダイナミクスの推移例（12ラウンドにおける4エージェントの怒り変化）

🧠 Design Philosophy
Transparency / 可視性 — Logs every computation step for auditability.

Safety / 安全性 — No external API calls; completely local execution.

Reproducibility / 再現性 — Deterministic random seeds and version-locked dependencies.

Educational Value / 教育性 — Modular Python scripts for classroom or lab exercises.

🧪 Technical Details
Language: Python 3.8 +

Dependencies: matplotlib, unittest

Outputs:

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
Fully validated (unit tests pass ✅)

Visual assets included

Markdown layout 100% GitHub-compatible

No HTML/CSS dependencies required



