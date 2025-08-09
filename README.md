# Multi-Agent Hierarchy & Emotion Dynamics Simulator
**AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![CI Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)

> Transparent, fully-logged simulator for dynamic hierarchy, emotion propagation, promotion competition, and mediation among multiple AI agents.  
> 研究・検証・教育用途のみ（商用/実運用不可）。

---

## Overview / 概要
This simulator models the dynamic evolution of organizational hierarchy, emotion contagion, and promotion-driven self-improvement among multiple AI agents. A **Mediator AI** can intervene to de-escalate collective emotional states. All states and interventions are fully logged for reproducibility and analysis.  

本リポジトリは、複数AIエージェントによる**昇進志向の進化**・**感情伝播**・**ヒエラルキー動的変化**・**調停AIによる沈静化**を再現・可視化できるシンプルなシミュレータです。全アクション・状態推移・介入は**自動ログ保存**され、再現・解析・教育用途に最適です。

---

## System Overview / システム概観
```mermaid
flowchart TD
    A[Start] -->|Agent Round| B[Update Rank]
    B --> C[Emotion Feedback]
    C --> D{High Emotion?}
    D -- Yes --> E[Mediator Intervention]
    D -- No --> F[Next Round]
    E --> F
    F -->|Loop until Max Rounds| A
