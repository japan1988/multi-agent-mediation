

---

## README用（最新版テンプレ／KAGE・内部進化構造は非公開前提）

````markdown
# Multi-Agent Mediation & Governance Simulator
AIマルチエージェント調停・ガバナンス・封印／再教育シミュレータ  
[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Overview / 概要
This repository provides a **transparent, fully-logged simulator** for compromise, arbitration, and governance among multiple AI agents with differing values, priorities, and emotions.  
**No internal KAGE evolution logic or proprietary governance framework is included in this public package.**  
**Only multi-agent negotiation, mediation, sealing, and re-education mechanisms are provided.**

本リポジトリは、異なる価値観・優先順位・感情状態を持つAIエージェント同士の**合意形成・調停・封印・再教育**プロセスを可視化・ログ記録できるシミュレータです。  

---

## Main Features / 主な機能
- ✅ **Negotiation and compromise logic** among multiple agents
- ✅ **Agent sealing** (temporary exclusion) based on emotional or rule-based criteria
- ✅ **MediatorAI** for arbitration, rule enforcement, and shutdown control
- ✅ **HumanOwner** class for explicit approval of critical actions (e.g., agent evolution, system shutdown)
- ✅ **Re-education/restoration** for sealed or inactive agents
- ✅ **Fully auditable logging** (all actions saved with timestamps for reproducibility and transparency)

---

## File List / ファイル構成

| ファイル名 | 概要 |
| -------- | ------------------------------------- |
| `ai_mediation_governance_demo.py` | マルチエージェント調停・ガバナンス・封印のデモ本体（KAGE非公開版） |
| `ai_alliance_persuasion_simulator.py` | AI同盟・説得・封印・復帰シミュレーション |
| `multi_agent_mediation_with_reeducation.py` | 再教育・リストアを含む応用例 |
| `mediation_basic_example.py` | 最小構成の基本調停例 |
| `requirements.txt` | 実行に必要なパッケージリスト |
| `tests/` | 自動テスト用コード |

---

## Notes / 注意点
- **No proprietary KAGE logic or advanced evolution control structures are included in this repository.**
- すべての公開コードは国際的なAIガバナンス・安全基準（OECD, EU AI法, IEEE倫理指針）に準拠し、研究・教育・検証目的で自由に利用可能です。

---

## Usage / 使い方
```bash
python ai_mediation_governance_demo.py
````

---

## License

MIT

---

---

このテンプレを**READMEにコピペすれば、  
「今回のリリース内容」「KAGE本体非公開」「公開部分の範囲」**  
すべて明確に説明できます。

必要に応じて、さらに細かい使い方・国際ガバナンスとの対応表なども追加できます。  
要望あればどうぞ！
```

