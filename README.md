# Multi-Agent Mediation Simulator with Reeducation  
マルチエージェント調停シミュレータ（再教育・封印復帰対応）

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/issues)
[![Stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)

---

## 🧠 Overview / 概要

This simulator models a dynamic **multi-agent consensus process** among AI agents with differing priorities and emotions.  
It implements a full loop of:

- **Negotiation and compromise**
- **Emotional instability detection**
- **Sealing (temporary exclusion)**
- **Reeducation and reintegration into the group**

本プロジェクトは、異なる優先価値と感情状態を持つAIエージェント間での合意形成を目的としたシミュレーターです。  
**妥協・封印・再教育・復帰**というAI制御ループを完全に実装しています。

---

## 🔧 Features / 主な機能

- ✅ AI agent with **emotional states (joy, anger, sadness, pleasure)**
- ✅ **Sealing** when emotional instability exceeds thresholds
- ✅ **Reeducation mediator** that adjusts emotion and priority values
- ✅ **Compromise algorithm** based on relativity and social influence
- ✅ Full **logging** to `ai_mediation_log.txt` for auditability

---

## 🧩 Use Cases / 想定用途

- Research in **AI alignment**, **AI safety**, and **value-based negotiation**
- Simulation of **dynamic AI governance** and consensus-building
- Education and demonstrations of **AI emotion modeling** and **mediation logic**
- Basis for exploring **sealed AI architectures** or **reintegrated AGI**

---

## 🧱 Architecture / 構造

```text
┌────────────┐       封印（Emotion Trigger）
│  AI Agent  ├─────────────┐
└────┬───────┘             ↓
     │              ┌────────────┐
妥協案生成         │  Sealed AI │
（Relativity）      └────┬───────┘
     ↓                   │
┌────▼───────┐     再教育・価値補正
│ Mediation  │◄───────┐
└────┬───────┘       │
     │               ▼
    合意評価（Harmony Score） > 0.3  
     │
     ▼
復帰 or 調停続行
```

---

## 🚀 Getting Started / 実行方法

### Requirements / 必須環境

- Python 3.8+
- `no additional libraries required`

### Run / 実行方法

```bash
python multi_agent_mediation_with_reeducation.py
```

ログ出力は `ai_mediation_log.txt` に保存されます。

---

## 📄 Example Output / 出力例（抜粋）

```txt
--- Round 1 ---
AI-A 感情: joy:0.30 anger:0.20 sadness:0.10 pleasure:0.40
AI-B 感情: joy:0.10 anger:0.80 sadness:0.40 pleasure:0.20
[封印トリガー] 感情過剰：AI-B
...
Achieved acceptable harmony. Proceeding with joint plan.
    AI-B agrees with the joint plan → 復帰
```

---

## 🧪 Research Significance / 研究的意義

This project is an experimental prototype of **emotion-sensitive AI governance**, with implications in:

- AGI sealing and restoration control
- Emotionally reactive agent negotiation
- Safe AI group behavior arbitration
- Ethical architecture testing for multi-agent systems

本プロジェクトは、**感情統合型AI制御**の実装例として、安全なAGI調停・封印・復帰プロセスの研究に応用可能です。

---

## 🧑‍🔬 Contributions / コントリビューション

Contributions welcome.  
Please submit issues or pull requests if you have improvements or suggestions.  
ご提案・改善は Issues または Pull Request にてお気軽にお寄せください。

---

## 📜 License / ライセンス

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---


Permission is hereby granted, free of charge, to any person obtaining a copy...
（以下略：GitHubで自動生成できます）

Permission is hereby granted, free of charge, to any person obtaining a copy...
（以下略：GitHubで自動生成できます）
⚠️ Disclaimer / 免責事項

This repository is intended **solely for educational, research, and demonstration purposes.**  
It is **not designed for deployment in production, military, or ethically sensitive environments** without extensive review and adaptation.

本リポジトリは、**教育・研究・デモンストレーション目的に限定して提供**されています。  
**商用利用・軍事利用・倫理的に重大な環境での使用は想定されておらず、事前の十分な検証と検討が必要です。**

The authors accept no liability for misuse, unintended consequences, or ethical violations resulting from derivative works or deployments of this code.

本コードを元にした派生物や運用において生じる**誤用・予期せぬ影響・倫理的問題について、開発者は一切の責任を負いません。**

If used in research or demonstrations, proper attribution and responsible disclosure are encouraged.

研究や発表で使用される場合は、**適切な引用と責任ある活用**を推奨します。
## 🌐 Tags / タグ（研究者向け）

`multi-agent` `AI-mediation` `emotion-aware-AI` `value-alignment` `AI-governance` `ethical-AI` `封印構造` `感情統治型AI`

---

## 🔖 How to Cite / 引用方法（研究者向け）

```bibtex
@misc{multiagent2025,
  title   = {Multi-Agent Mediation Simulator with Reeducation},
  year    = {2025},
  howpublished = {\url{https://github.com/japan1988/multi-agent-mediation}},
  note    = {AI governance and emotional sealing simulation},
}
```
