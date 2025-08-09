# Multi-Agent Hierarchy & Emotion Dynamics Simulator
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)

AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ

Transparent, fully-logged simulator for dynamic hierarchy, emotion propagation, promotion competition, and mediation among multiple AI agents.  
研究・検証・教育用途のみ（商用/実運用不可）。

---

## Overview / 概要
This simulator models the dynamic evolution of organizational hierarchy, emotion contagion, and promotion-driven self-improvement among multiple AI agents.  
A **Mediator AI** can intervene to de-escalate collective emotional states.  
All states and interventions are fully logged for reproducibility and analysis.

本リポジトリは、複数AIエージェントによる**昇進志向の進化**・**感情伝播**・**ヒエラルキー動的変化**・**調停AIによる沈静化**を再現・可視化できるシンプルなシミュレータです。  
全アクション・状態推移・介入は**自動ログ保存**され、再現・解析・教育用途に最適です。

---

## Main Features / 主な機能
* ✅ **Dynamic hierarchy** based on individual performance (rank updates each round)  
  個体パフォーマンスに基づくダイナミックな階層更新
* ✅ **Emotion propagation & feedback** between leaders and subordinates  
  感情の伝播と上下関係でのフィードバック
* ✅ **Promotion-driven self-evolution**  
  昇進志向に基づく自己改善（パフォーマンス向上）
* ✅ **Mediator AI** that detects high emotion and applies group-wide cool-down  
  高感情状態を検出し全体沈静化を行う調停AI
* ✅ **Full logging** of rounds, agent states, and interventions  
  すべてのラウンド・状態・介入をログ出力
* ✅ **Lightweight & extensible** class structure  
  研究・教育向けに軽量＆拡張容易
* ✅ **No proprietary tech included**  
  閉鎖技術や機密アルゴリズムは含みません

---

## System Overview / システム概要
```mermaid
flowchart TD
    Start -->|Agent Round| UpdateRank
    UpdateRank --> EmotionFeedback
    EmotionFeedback -->|High Emotion| MediatorIntervention
    EmotionFeedback -->|Normal| NextRound
    MediatorIntervention --> NextRound
    NextRound -->|Loop until Max Rounds| UpdateRank
    NextRound --> End

