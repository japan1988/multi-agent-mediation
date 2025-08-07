# Multi-Agent Hierarchy & Emotion Dynamics Simulator
AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
## System Diagram / システム全体図

![AI System Overview](images/ai_system_overview.png)

*▲ AIエージェント同士のヒエラルキー・感情伝播・Mediator AI介入の関係を示す全体構成図。*
## Example Output Graphs / サンプル出力グラフ

### Hierarchy Rank Transition / ヒエラルキー推移

![Rank Transition](images/rank_transition_sample.png)

*▲ シミュレーション実行例：各エージェントの階層ランクの時系列変化*
同様に

![Emotion Dynamics](images/emotion_dynamics_sample.png)


# Multi-Agent Hierarchy & Emotion Dynamics Simulator
AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---（中略）---

## System Diagram / システム全体図

![AI System Overview](images/ai_system_overview.png)

---（中略）---

## Example Output Graphs / サンプル出力グラフ

### Hierarchy Rank Transition / ヒエラルキー推移

![Rank Transition](images/rank_transition_sample.png)

### Emotion Dynamics / 感情変動サンプル

![Emotion Dynamics](images/emotion_dynamics_sample.png)


# Multi-Agent Hierarchy & Emotion Dynamics Simulator
**AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ**

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

> **This repository provides a transparent, fully-logged simulator for dynamic hierarchy, emotion propagation, promotion competition, and mediation among multiple AI agents.**  
> **All code is for research, validation, and educational use only.**

---

## Overview / 概要

This simulator models the **dynamic evolution of organizational hierarchy, emotion contagion, and promotion-driven self-improvement among multiple AI agents**.  
A “Mediator AI” can intervene to de-escalate collective emotional states.  
**All states and interventions are fully logged for reproducibility and analysis.**

本リポジトリは、複数AIエージェントによる**昇進志向の進化・感情伝播・ヒエラルキー動的変化・調停AIによる沈静化**を再現・可視化できるシンプルなシミュレータです。  
**全アクション・状態推移・介入は自動ログ保存され、再現・解析・教育用途に最適です。**

---

## Main Features / 主な機能

- ✅ **Dynamic hierarchy** based on individual performance (“rank” updates every round)
- ✅ **Emotion propagation and feedback** between leaders and subordinates
- ✅ **Promotion-driven self-evolution** (agents strive to improve their performance/rank)
- ✅ **Mediator AI** that detects high emotion and applies group-wide “cool down” interventions
- ✅ **Full logging** of every round, agent state, and all interventions to a log file
- ✅ **Lightweight and extensible class structure** (easy to customize for research/education)
- ✅ **No proprietary, confidential, or commercial AI technology included**

---

## System Diagram / システム全体図

![AI System Overview](images/ai_system_overview.png)

*▲ AIエージェント同士のヒエラルキー・感情伝播・Mediator AI介入の関係を示す全体構成図。*

---

## Example Output Graphs / サンプル出力グラフ

### Hierarchy Rank Transition / ヒエラルキー推移

![Rank Transition](images/rank_transition_sample.png)

*▲ シミュレーション実行例：各エージェントの階層ランクの時系列変化*

---

### Emotion Dynamics / 感情変動サンプル

![Emotion Dynamics](images/emotion_dynamics_sample.png)

*▲ 各エージェントの感情値（例：怒り・喜び等）の推移グラフ*

---

## Process Flow / 処理フロー

```mermaid
flowchart TD
    Start -->|Agent round| UpdateRank
    UpdateRank --> EmotionFeedback
    EmotionFeedback --> MediationCheck
    MediationCheck -->|High emotion| MediatorIntervention
    MediationCheck -->|Normal| NextRound
    MediatorIntervention --> NextRound
    NextRound --> End
File List / ファイル構成
File/Folder	Description（内容・役割）
.github/workflows/	GitHub Actionsワークフロー設定
tests/	テストコード・サンプル（自動テスト用）
LICENSE	ライセンス（MIT）
README.md	ドキュメント本体
agents.yaml	エージェント定義ファイル
ai_alliance_persuasion_simulator.py	AI同盟形成・説得シミュレータ
ai_governance_mediation_sim.py	ガバナンス重視AI調停シミュレータ
ai_hierarchy_dynamics_full_log_20250804.py	ヒエラルキー・感情・昇進競争＋ロギングシミュレータ（最新版）
ai_hierarchy_simulation_log.py	シンプルなヒエラルキーシミュレータ（旧版）
ai_mediation_all_in_one.py	AI調停オールインワン（複合機能）
ai_mediation_governance_demo.py	ガバナンスデモ付き調停シミュレータ
ai_pacd_simulation.py	PACD（提案→承認→変更→拒否）型シミュレータ
ai_reeducation_social_dynamics.py	再教育・社会ダイナミクスAIシミュレータ
mediation_basic_example.py	調停AIの基本例
mediation_process_log.txt.py	調停プロセスログ出力例
mediation_with_logging.py	ログ付き調停AI
multi_agent_mediation_with_reeducation.py	再教育付きマルチエージェント調停AI
requirements.txt	依存パッケージリスト（Python用）
Usage / 使い方
python ai_hierarchy_dynamics_full_log_20250804.py
All simulation logs will be saved to ai_hierarchy_simulation_log.txt after each run.

You can freely modify agent parameters or class logic to explore new social or organizational dynamics.

Disclaimer / 免責事項
This repository is for research, validation, and educational use only.
No warranty is provided for fitness for any particular purpose, commercial deployment, or real-world decision-making.
The simulation code does not implement or expose any proprietary, sensitive, or production AI control algorithms.
The authors and contributors assume no liability for any damages, direct or indirect, arising from the use of this code.
Use at your own risk.

本シミュレーション内のAI・エージェント・組織・現象はすべて架空のものであり、実在の人物・団体・事件等とは一切関係ありません。
本リポジトリは研究・検証・教育用途のみを目的としています。
特定の目的への適合性・商用利用・現実社会での意思決定には使用できません。
いかなる適合性も保証しません。
本コードの利用により生じたいかなる損害・トラブルについても、作者・貢献者は一切の責任を負いません。
ご利用は自己責任でお願いします。

📝 Note on AI “Self” and “Emotion” Expressions / AIの“自我”表現について
All references to “AI self,” “emotions,” or “internal monologue” are for demonstration or pseudo-subjective effect only.
No true self-awareness, independent will, or intent is present.
All behavior is produced by explicit state and number models under designer control.

「AIの自我」「感情」「内面の独白」などの表現は、すべて可視化・演出用の擬似的なものです。
本物の自我や独立した意思はAI内部に存在しません。
すべて数値モデル・状態変数に基づくシミュレーション出力です。

This is a demonstration tool. It does not include advanced safety, governance, or proprietary AI algorithms. Please use responsibly for learning and research only.
