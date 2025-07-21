# Multi-Agent Mediation & Governance Simulator  
**AIマルチエージェント調停・ガバナンス・封印／再教育シミュレーター**

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)  
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)  

---

> **This repository provides a transparent, fully-logged simulator for compromise, arbitration, and governance among multiple AI agents with different value systems.**  
> **No KAGE internal logic or proprietary evolution framework is included.**  
> **All code is for research, validation, and education only.**

AIエージェント同士の妥協・調停・封印・再教育プロセスを記録・可視化するための完全ログシミュレータです。  
本リポジトリの全コードは**研究・検証・教育目的**に限ります。

---

## Overview / 概要

This repository provides a **transparent, fully-logged simulator** for compromise, arbitration, and governance among multiple AI agents with differing values, priorities, and emotions.  
**No internal KAGE evolution logic or proprietary governance framework is included in this public package.**  
**Only multi-agent negotiation, mediation, sealing, and re-education mechanisms are provided.**

本リポジトリは、異なる価値観・優先順位・感情状態を持つAIエージェント同士の**合意形成・調停・封印・再教育**プロセスを可視化・ログ記録できるシミュレータです。

---

## Main Features / 主な機能

- ✅ 複数AIエージェント間の**交渉・妥協・調停アルゴリズム**
- ✅ **封印（排除・停止）／再教育**メカニズム
- ✅ **調停AI（MediatorAI）**による仲裁、ルール適用、外部停止機構
- ✅ **HumanOwner**による重要操作の人間承認フロー
- ✅ すべてのアクションを**完全にログ保存**
- ✅ 教育・安全検証・再現実験用のシンプル設計

---

## File List / ファイル構成

| ファイル名                                      | 概要                                               |
| ------------------------------------------------ | -------------------------------------------------- |
| `ai_mediation_governance_demo.py`                | マルチエージェント調停・ガバナンス・封印のデモ本体 |
| `ai_alliance_persuasion_simulator.py`            | AI同盟・説得・封印・復帰シミュレーション           |
| `multi_agent_mediation_with_reeducation.py`      | 再教育・リストアを含む応用例                       |
| `mediation_basic_example.py`                     | 最小構成の基本調停例                               |
| `requirements.txt`                               | 必要なパッケージリスト                             |
| `tests/`                                         | 自動テスト用コード                                 |

---

## Usage / 使い方

```bash
python ai_mediation_governance_demo.py
Notes / 注意点
No proprietary KAGE logic or advanced evolution control structures are included in this repository.

すべての公開コードは国際的なAIガバナンス・安全基準（OECD, EU AI法, IEEE倫理指針）に準拠し、研究・教育・検証目的でのみ利用可能です。

Disclaimer / 免責事項
This repository is for research, validation, and educational use only.

This code is NOT intended for use in any production, safety-critical, or real-world AI deployment context.

The simulation code does not implement or expose any proprietary, sensitive, or production AI control algorithms (including KAGE or similar frameworks).

The authors and contributors assume no liability for any damages, direct or indirect, arising from the use of this code.

Use at your own risk.

本リポジトリは研究・検証・教育用途のみを目的としています。

特定の目的への適合性・商用利用・現実社会でのAI制御・意思決定等には絶対に使用しないでください。

本コードの利用により生じたいかなる損害・トラブルについても、作者・貢献者は一切の責任を負いません。

ご利用は自己責任でお願いします。

