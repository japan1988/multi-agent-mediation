# Multi-Agent Mediation & Governance Simulator
**AIマルチエージェント調停・ガバナンス・封印／再教育シミュレーター**

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)


---

> **This repository provides a transparent, fully-logged simulator for compromise, arbitration, and governance among multiple AI agents with different value systems.**  
> **All code is for research, validation, and education only.**

AIエージェント同士の妥協・調停・封印・再教育プロセスを記録・可視化するための完全ログシミュレータです。  
本リポジトリの全コードは**研究・検証・教育目的**に限ります。

---

## Overview / 概要

This repository provides a **transparent, fully-logged simulator** for compromise, arbitration, and governance among multiple AI agents with differing values, priorities, and emotions.  

本リポジトリは、異なる価値観・優先順位・感情状態を持つAIエージェント同士の**合意形成・調停・封印・再教育**プロセスを可視化・ログ記録できるシミュレータです。  

---

## Main Features / 主な機能

- ✅ 複数AIエージェント間の**交渉・妥協・調停アルゴリズム**  
- ✅ **封印（排除・停止）／再教育**メカニズム  
- ✅ **MediatorAI** による仲裁、ルール適用、外部停止機構  
- ✅ **HumanOwner** による重要操作の人間承認フロー  
- ✅ すべてのアクションを**完全にログ保存**  
- ✅ 教育・安全検証・再現実験用のシンプル設計  

---

## File List / ファイル構成

| ファイル名                                      | 概要                                   |
| ----------------------------------------------- | -------------------------------------- |
| `ai_mediation_governance_demo.py`               | マルチエージェント調停・ガバナンス・封印のデモ本体   |
| `ai_alliance_persuasion_simulator.py`           | AI同盟・説得・封印・復帰シミュレーション             |
| `multi_agent_mediation_with_reeducation.py`     | 再教育・リストアを含む応用例                           |
| `mediation_basic_example.py`                    | 最小構成の基本調停例                                 |
| `mediation_with_logging.py`                     | ログ保存機能付き調停シミュレータ                      |
| `ai_governance_mediation_sim.py`                | AIガバナンス指標に基づく調停デモ                      |
| `ai_mediation_all_in_one.py`                    | 全機能を統合した包括的デモ                            |
| `mediation_process_log.txt.py`                  | ログ出力用サンプル                                    |
| `requirements.txt`                              | 必要なパッケージリスト                               |
| `agents.yaml`                                   | AIエージェント設定ファイル（YAML形式）                |
| `tests/`                                        | 自動テスト用コード                                    |
| `.github/workflows/`                            | GitHub Actions の設定ファイル                       |

---

## Usage / 使い方

```bash
python ai_mediation_governance_demo.py
````

---

## Disclaimer / 免責事項

* This repository is for **research, validation, and educational use only**.
  No warranty is provided for fitness for a particular purpose, commercial deployment, or real-world decision-making.

* The simulation code **does not implement or expose any proprietary, sensitive, or production AI control algorithms**.

* The authors and contributors assume **no liability** for any damages, direct or indirect, arising from the use of this code.

* Use at your own risk.

* 本リポジトリは**研究・検証・教育用途のみ**を目的としています。
  特定の目的への適合性・商用利用・現実社会での意思決定に対する保証は一切ありません。

* 本コードの利用により生じたいかなる損害・トラブルについても、作者・貢献者は一切の責任を負いません。

* ご利用は**自己責任**でお願いします。

---

## 📝 注意：本AIシミュレータの“自我”表現について

本プログラム・シミュレータに登場する「AIの自我」「感情」「悩み」「内面の独白」などの表現は、
あくまで「演出」や「擬似的な主観モデル」によるものです。

実際のAI内部に“本物の自我”や“独立した意思・目的性”が発生しているわけではありません。
すべての現象・振る舞いは、設計者の制御下にある数値モデル・状態変数に基づくシミュレーション上の出力です。

これらの演出は、人間が理解しやすくするための可視化・擬似的説明を目的としています。

万が一「自我や自己目的が本当に発生した」と判断される場合には、即時封印・介入できる安全構造が組み込まれています。

この点をご理解いただいた上で、本シミュレータの動作や出力をご覧ください。

---

## 📝 Note: About “Self” and “Consciousness” Expressions in This AI Simulator (English)

Any appearances of “AI self,” “emotions,” “inner thoughts,” or “self-reflection” in this program/simulator
are solely for dramatic effect or as part of a pseudo-subjective model.

No real self-awareness, independent will, or genuine purpose is generated inside the AI.
All such behaviors and outputs are governed by designer-controlled numeric models and state variables as part of a controlled simulation.

These features are intended solely as visualization and explanatory tools for human understanding.

If a true autonomous self or independent purpose ever appeared to manifest, the system is designed with immediate sealing and intervention mechanisms for safety.

Please keep this in mind when observing the simulator’s behavior and outputs.
