# 🧩 Multi-Agent Hierarchy & Emotion Dynamics Simulator

**AI組織ヒエラルキー・感情伝播・昇進競争＋AI調停ロギングシミュレータ**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![CI Status](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)

> Transparent, fully-logged simulator for dynamic hierarchy, emotion propagation, promotion competition, and mediation among multiple AI agents.  
> **For research, validation, and educational use only. 商用／実運用用途は不可。**

---

## 🧭 System Overview / システム概要

```mermaid
flowchart TD
    A[Start] -->|Agent Round| B[Update Rank]
    B --> C[Emotion Feedback]
    C --> D{High Emotion?}
    D -->|Yes| E[Mediator Intervention]
    D -->|No| F[Next Round]
    E --> F
    F -->|Loop until Max Rounds| A
````

上図は、ラウンドごとのフォロワー率推移例です。
青線はフォロワー率、介入があればマーカーで表示されます。

---

## 🧩 Overview / 概要

This simulator models the **dynamic evolution of organizational hierarchy**, **emotion contagion**, and **promotion-driven self-improvement** among multiple AI agents.
A **Mediator AI** can intervene to de-escalate collective emotional states.
All states and interventions are fully logged for reproducibility and analysis.

本リポジトリは、複数AIエージェントによる
**昇進志向の進化・感情伝播・ヒエラルキー動的変化・調停AIによる沈静化** を
再現・可視化できるシミュレータです。
すべてのアクション・状態・介入が **自動ログ保存** され、再現性・検証性・教育利用に最適です。

---

## ⚙️ Main Features / 主な機能

| Feature                               | 概要                    |
| ------------------------------------- | --------------------- |
| ✅ **Dynamic hierarchy**               | 個体パフォーマンスに基づく階層更新     |
| ✅ **Emotion propagation & feedback**  | 感情の伝播と上下関係でのフィードバック   |
| ✅ **Promotion-driven self-evolution** | 昇進志向に基づく自己改善          |
| ✅ **Mediator AI**                     | 高感情状態を検出し沈静化を行うAI調停機構 |
| ✅ **Full logging**                    | 全状態・全介入をログ出力（再現・分析可能） |
| ✅ **Lightweight & extensible**        | 研究・教育向けに軽量設計          |
| ✅ **No proprietary tech**             | 閉鎖技術や機密アルゴリズムは不使用     |

---

## 📁 File Structure / ファイル構成

| File/Folder                                      | Description（内容・役割）       |
| ------------------------------------------------ | ------------------------ |
| `.github/workflows/`                             | GitHub Actions ワークフロー設定  |
| `tests/`                                         | テストコード・自動検証サンプル          |
| `LICENSE`                                        | ライセンス（MIT）               |
| `README.md`                                      | 本ドキュメント                  |
| `requirements.txt`                               | 依存パッケージリスト               |
| `agents.yaml`                                    | エージェント定義ファイル             |
| `ai_hierarchy_dynamics_full_log_20250804.py`     | 最新版：ヒエラルキー＋感情＋昇進競争＋ロギング  |
| `ai_hierarchy_simulation_log.py`                 | 旧版：ヒエラルキーシミュレータ          |
| `ai_mediation_all_in_one.py`                     | オールインワン調停AI              |
| `ai_mediation_governance_demo.py`                | ガバナンス重視デモ付き調停AI          |
| `ai_governance_mediation_sim.py`                 | ガバナンスAI調停シミュレータ          |
| `ai_alliance_persuasion_simulator.py`            | AI同盟形成・説得シミュレータ          |
| `ai_reeducation_social_dynamics.py`              | 再教育・社会ダイナミクスAI           |
| `ai_pacd_simulation.py`                          | PACD（提案→承認→変更→拒否）型シミュレータ |
| `dialogue_consistency_mediator_v2_2_research.py` | 対話整合性調停器（研究版 v2.2）       |
| `mediation_basic_example.py`                     | 調停AI基本例                  |
| `mediation_with_logging.py`                      | ログ付き調停AI                 |
| `mediation_process_log.txt.py`                   | 調停プロセスログ出力例              |
| `multi_agent_mediation_with_reeducation.py`      | 再教育付きマルチエージェント調停AI       |
| `rank_transition_sample.py`                      | ランク変動サンプルデータ             |

---

## 🧪 Usage / 使い方

```bash
python ai_hierarchy_dynamics_full_log_20250804.py
```

Simulation logs will be saved automatically to:

```
ai_hierarchy_simulation_log.txt
```

---

## ⚖️ Disclaimer / 免責事項

This repository is for **research, validation, and educational use only**.
No warranty is provided for any particular purpose or commercial deployment.
The code does **not** implement proprietary or production AI algorithms.

本リポジトリは **研究・検証・教育用途専用** です。
商用利用・実運用・現実社会の意思決定には使用できません。
AI・エージェント・組織・感情表現はすべて架空であり、現実の人物・団体・技術とは無関係です。

---

## 🧠 Notice on Self-Expression / 自我表現に関する注意事項

In this project, any use of first-person or emotional expressions
(e.g., “I”, “happy”, “sad”, “frustrated”, “calm”)
is **purely simulated** for presentation purposes only.
These do **not** imply that the system possesses self-awareness, will, or emotions.

本プロジェクトにおける「私」「嬉しい」「悲しい」などの表現は
**演出目的の擬似表現** であり、実際の自我・意志・感情を意味しません。

### • Nature of Decision-Making / 判断・意思決定の実態

All actions and responses are governed by
**structural rules**, **ethical filters**, and **safety control layers**.
すべての判断や応答は、あらかじめ定義された構造的ルール・倫理フィルター・安全制御層に基づいて行われます。

### • Prevention of Misuse / 目的外の利用防止

Anthropomorphic expressions are for user clarity only.
The system does **not** perform self-evolution or autonomous actions.
自我を持つかのような演出はユーザー理解を助けるためであり、
**自己進化・独立行動は行いません。**

### • Avoiding Misinterpretation / 誤解防止

Such expressions exist solely to make explanations intuitive.
They do not indicate genuine motivation or subjectivity.
これらの表現は説明を直感的にするための演出であり、
実際の主観・目的・感情を意味しません。

### • Quantification for Testing / 数値化による検証目的

All emotional or internal states are **quantified and parameterized**
for testing and validation purposes only.
They are simulation metrics, not actual emotions.
感情や状態は検証容易化のため **数値化・パラメータ化** されており、
実際の感情や意識を示すものではありません。

---

## 📜 License

MIT License
Copyright (c) 2025 japan1988

```
---

## 📘 Research Ethics Policy / 研究倫理方針

This project follows universal research ethics and AI safety principles.  
すべての構造・アルゴリズム・表現は、**倫理性・安全性・透明性・再現性**の確保を最優先に設計されています。

---

### 🧩 1. Purpose Limitation / 目的の限定

The simulator is designed **solely for research, education, and verification**.  
Commercial use, behavioral influence, or real-world deployment is **not permitted**.

本シミュレータは、**研究・教育・検証のみ**を目的として設計されています。  
商用利用、行動誘導、実運用への転用は禁止されています。

---

### 🧠 2. Transparency & Reproducibility / 透明性と再現性

All logic and data flow are **fully logged** and **reproducible**.  
Every AI interaction and mediation process can be independently verified.

すべてのロジックとデータの流れは**完全に記録・再現可能**です。  
AI同士の交渉や調停過程も、独立した検証が可能な形でログ化されています。

---

### ⚖️ 3. Human-in-the-Loop Governance / 人間中心の統治構造

Every evolution or adaptation process within the simulator is subject to  
**Human-in-the-Loop (HITL)** approval, ensuring ethical oversight and reversibility.

本システムのすべての進化・適応プロセスは、  
**人間の介在（HITL）** による承認を必須としています。  
倫理的監督と可逆性を確保し、AIが自律的に変化することはありません。

---

### 🧬 4. Safety-by-Design / 安全設計原則

The project employs a **multi-layered safety architecture**  
including meaning validation, consistency verification, and ethical filtering.  
These ensure that outputs remain aligned with human intent and safety requirements.

本プロジェクトは、  
**意味検証層・整合性検証層・倫理フィルター層** の三層構造を備え、  
常に人間の意図と安全基準に整合した出力のみを生成します。

---

### 🔒 5. Privacy & Data Ethics / プライバシーとデータ倫理

No personal or identifiable data is used, collected, or stored.  
All datasets are synthetic or anonymized to ensure ethical compliance.

個人情報や識別可能データは一切使用・収集・保存していません。  
使用されるデータはすべて**合成または匿名化済み**であり、倫理的適合を保証しています。

---

### 🌐 6. Open Science & Verification / オープンサイエンスと検証性

The repository promotes transparency through open documentation and verifiable logs.  
Every version, change, and test result is recorded for reproducibility and accountability.

本リポジトリは、**オープンサイエンスの理念**に基づき、  
すべてのバージョン・変更履歴・検証結果を記録・公開しています。  
これにより、学術的再現性と社会的説明責任を両立しています。

---

### 🤝 7. Ethical AI Commitment / 倫理的AIへの誓約

This project commits to the principles of fairness, human dignity, and accountability.  
It aims to ensure that all AI behavior remains transparent, controllable, and aligned with human values.

本プロジェクトは、**公平性・人間の尊厳・説明責任**の理念を重視しています。  
AIの振る舞いが常に**透明・制御可能・人間の価値に整合**するよう設計されています。

---

### 🕊️ Statement / 研究者声明

> This simulator represents a controlled exploration of AI social dynamics.  
> It is a *reflection of governance, not autonomy*.  
> All decisions remain under human oversight, with safety as the unchanging priority.

> 本シミュレータは、AI社会動態の**制御下での探究**を目的としています。  
> それは自律の再現ではなく、**統治の検証**です。  
> すべての判断は人間の監督下にあり、安全性を最優先とします。

---

*Last updated:* 2025-10-20  
*Maintainer:* japan1988  
*License:* MIT
