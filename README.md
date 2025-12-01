<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>

| Layer | Role | What it does |
|-------|------|--------------|
| **Interface Layer**  | Input from outside | Receives human input and sends logs. |
| **Agent Layer**      | Thinking & feeling | Controls decisions, simple emotions, and dialogue. |
| **Supervisor Layer** | Overall check      | Watches the whole system, checks consistency, and runs basic ethics checks. |

---

## 🔬 **Sentiment Flow / Context Flow**

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram">
</p>

### 🧠 Emotion Cycle Model

1. **Perception** — Takes the input and turns it into simple “emotion signals”.  
2. **Context** — Looks at the situation and background of the negotiation.  
3. **Action** — Combines the situation and emotion, then chooses the next action.

> 🧩 At every step, the **Ethical Seal** checks the result and blocks outputs that may be harmful.

---

## ⚙️ **Execution Example**

```bash
# Basic run
python3 ai_mediation_all_in_one.py

# Run with logging
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# Policy mediation mode
python3 ai_governance_mediation_sim.py --scenario policy_ethics
🧾 How to Cite

Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation
License: Educational / Research License v1.1

⚖️ License & Disclaimer

License Type: Educational / Research License v1.1
Date: 2025-04-01

✅ You May

Use this project for non-commercial education and research.

Use parts of the code in academic work, with a proper citation.

Run and modify it in your own local environment.

🚫 You May Not

Use this project for commercial services or products.

Redistribute or resell it without permission.

Publish modified versions without clear credit to the original author.

⚖️ Disclaimer

This project is for learning and research.
The developers and contributors are not responsible for any damage, wrong decisions, or ethical problems that come from using this software or its documents.

📈 Release Highlights

Version	Date	Main changes
v1.0.0	2025-04-01	First public release. Combined structure, emotion, and mediation modules.
v1.1.0	2025-08-04	Added logging of layer behavior and a re-training module.
v1.2.0	2025-10-28	Updated README and added badges for open source use.
🤝 Contributing

Fork this repository.

Create a new branch:

git checkout -b feature/new-module
Change the code and add simple tests.

Open a Pull Request and explain:

what you changed

why it is useful

Contributions for education and research are welcome.
Please always care about ethics, safety, and clear explanations.



