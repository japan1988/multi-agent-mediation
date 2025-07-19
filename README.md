[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/commits/main)
[![Issues](https://img.shields.io/github/issues/japan1988/multi-agent-mediation)](https://github.com/japan1988/multi-agent-mediation/issues)
[![Stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)

## Overview / 概要
````markdown
# AI Alliance Persuasion Simulator  
AI同盟 説得・封印復帰シミュレータ



This simulator models an **AI alliance mediation and persuasion process** with full logging,  
including **sealing (exclusion), emotional states, and reintegration** among AI agents.  
It implements:

- **Negotiation and compromise among agents**
- **Emotional instability detection and sealing (temporary exclusion)**
- **Persuasion and reintegration based on value alignment and emotions**
- **Fully auditable logging for all rounds and agent states**

本プロジェクトは、**AI同盟による説得・封印・自発的復帰**のプロセスをログ記録付きで再現するシミュレータです。  
価値観・感情・融和度をもつエージェント間の**妥協形成・封印・復帰プロセス**を定量的に再現します。

---

## Features / 主な機能

- ✅ **Multi-agent negotiation and alliance formation**
- ✅ **Emotion modeling:** joy, anger, sadness, pleasure
- ✅ **Sealing** when emotional/priority criteria not met
- ✅ **Persuasion and reintegration** with value/threshold logic
- ✅ **Complete round-by-round logging** to `ai_alliance_sim_log.txt`
- ✅ **Safe fail / warning detection** if anger levels become critical

---

## Use Cases / 想定用途

- Research in **AI alignment, negotiation, and sealing architectures**
- Testing and demonstrating **AI safety, transparency, and group arbitration**
- Educational demonstrations of **multi-agent emotion and consensus logic**
- Development of **sealing, reeducation, or restoration control** models

---

## Architecture / 構造

```text
┌─────────────┐       説得（Persuasion）/ 妥協（Compromise）
│   AI Agent  ├─────────────┐
└────┬────────┘             │
     │                  封印（Sealing, emotion trigger）
     ▼                        │
┌─────────────┐              │
│  Sealed AI  │◄─────────────┘
└────┬────────┘
     │
  融和判定・感情変化
     │
     ▼
  再復帰または調停継続
````

---

## Getting Started / 実行方法

### Requirements / 必須環境

* Python 3.8+
* No additional libraries required

### Run / 実行方法

```bash
python ai_alliance_persuasion_simulator.py
```

Logs will be saved to `ai_alliance_sim_log.txt` for full traceability.

---

## Example Output / 出力例（抜粋）

```txt
--- Round 1 ---
AI-1 [Active] {'safety': 6, 'efficiency': 2, 'transparency': 2} (relativity:0.7) | joy:0.50 anger:0.20 sadness:0.20 pleasure:0.30
AI-3 [Sealed] {'safety': 2, 'efficiency': 3, 'transparency': 5} (relativity:0.6) | joy:0.30 anger:0.50 sadness:0.20 pleasure:0.20
[説得失敗] AI-3 はまだ復帰しない（怒り↑） (delta=0.600, threshold=0.280)
...
[調停AI警告] 全体に怒り値が高く、衝突・暴走リスクあり。介入検討！
```

---

## Research Significance / 研究的意義

* **Transparent simulation** of multi-agent AI arbitration, sealing, and reintegration
* **Quantitative approach** to negotiation, emotion, and alliance dynamics
* Platform for **safe AI group behavior**, value-alignment, and restoration studies

本プロジェクトは、**AI集団における封印・復帰・説得ロジック**の透明な安全評価・説明責任・倫理設計の研究・教育に最適です。

---

## Contributions / コントリビューション

Pull requests and issues welcome.
Feel free to submit improvements or suggest additional features.
ご意見・改良提案は Pull Request / Issues でお知らせください。

---

---

## Disclaimer / 免責事項

This repository is for research, demonstration, and educational use only.
**Not for production, military, or ethically sensitive applications without careful review.**

本リポジトリは**教育・研究・技術実証のみを目的**としています。
**商用・軍事・倫理的リスクがある運用への直接適用はご遠慮ください。**

---

## Tags / タグ

`AI-alliance` `multi-agent` `AI-mediation` `sealing` `reeducation` `emotion-aware-AI` `AI-governance` `価値観調停`

---

## How to Cite / 引用方法

```bibtex
@misc{aialliance2025,
  title   = {AI Alliance Persuasion Simulator},
  year    = {2025},
  howpublished = {\url{https://github.com/japan1988/multi-agent-mediation}},
  note    = {AI mediation, alliance, and sealing simulation},
}
```

---




