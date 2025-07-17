

---

# Multi-Agent Mediation Simulator / マルチエージェントAI調停シミュレータ

[![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml)

---

## Overview / 概要

This project provides a transparent, fully-logged simulator for modeling compromise and consensus-building among multiple AI agents with differing values and priorities.
It implements dynamic alliance formation, multi-agent mediation, agent sealing/reeducation/restore mechanisms, and logging, in alignment with global AI governance and safety principles.

本プロジェクトは、多様な価値観・優先順位を持つ複数AIエージェント間での合意形成・妥協案生成・再教育・封印・復帰までを段階的にシミュレートできる透明性重視のツールです。
すべての交渉・判断・リスク・経過はログとして保存され、AI安全・倫理・国際ガバナンス基準に基づいた設計となっています。

---

## Main Features / 主な機能

* **Compromise & Mediation**: Dynamic multi-round negotiation with relativity (value adaptation) and emotion (affecting compromise)
* **Sealing & Restoration**: Emotionally unstable agents are auto-sealed; may be reeducated and restored if conditions met
* **Reeducation**: "Reeducation AI" can adjust agent emotions/priorities to align with joint plans
* **Full Logging**: All steps are output to `ai_mediation_log.txt` for full traceability/auditability
* **PEP8 Compliant**: Fully passes Python code style and CI (see green badge above)
* **International Standards**: Scenarios/test logic based on OECD/EU/IEEE principles for safe AI mediation

---

## Intended Use / 想定用途

* Research and education in AI negotiation, compromise, mediation, and arbitration
  AI交渉・調停・妥協・再教育・合意形成メカニズムの研究・教育
* Simulation of safe/ethical value alignment and risk control in multi-agent systems
  マルチエージェントシステムにおける安全な価値調整・リスク制御の検証
* Transparent prototyping, academic competition, case studies
  透明性重視のプロトタイピング、学術コンペ、ケーススタディ
* Policy & governance scenario testing under international frameworks
  国際ガバナンス枠組みに沿った政策・制度設計シミュレーション

---

## Limitations, Risks & Prohibited Use

**制約・リスク・禁止事項**

* **For research/educational use only.**
  研究・教育用途限定。
* **Not for industrial/commercial/real-world deployment.**
  商用・産業・実世界運用には非対応。
* **Risks:** Incorrect parameters or adversarial input may bypass safety/sealing.
  パラメータやシナリオ次第では安全機構が突破されるリスクあり。
* **Prohibited:**

  * Commercial/real-world decision use
    商用・実世界の意思決定への使用
  * Regulatory evasion, adversarial/malicious/illegal contexts
    規制逃れ、敵対的/違法/倫理違反の用途
  * Any non-compliance with global AI ethics & laws
    国際的なAI倫理・法規範への違反

---

## How to Use / 使い方

1. **Install requirements / 必要なPythonパッケージをインストール**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the main simulator / メインシミュレータを実行**

   ```bash
   python multi_agent_mediation_with_reeducation.py
   ```

3. **Check the output log / ログファイル確認**

   * All logs and process steps are saved to `ai_mediation_log.txt`
     すべての交渉・評価・封印・復帰の経過が `ai_mediation_log.txt` に出力されます。

---

## File Structure / ファイル構成

* `multi_agent_mediation_with_reeducation.py`

  * **Main simulation** (recommended: with compromise, emotion, sealing, reeducation, restoration)
* `mediation_with_logging.py`, `mediation_basic_example.py`

  * Baseline/simple negotiation examples
* `ai_mediation_all_in_one.py`

  * Unified previous model (simple integration test)
* `agents.yaml`

  * (Optional) Agent parameter presets/scenarios
* `requirements.txt`

  * Python dependency list

---

## Transparency & Safety / 透明性・安全性

* All mediation steps and logic are logged for full reproducibility.
* Source, parameters, and algorithms are open and externally reviewable.
* Automatic sealing triggers if excessive risk or unintended evolution is detected.

---

## License / ライセンス

This project is released for **research and education only** under an open academic license.
Commercial, adversarial, or real-world deployment is strictly prohibited.
本プロジェクトは研究・教育用途限定の学術ライセンスで公開されています。商用・実世界運用・敵対的利用は厳禁です。

---

## Author / 作者

* [japan1988](https://github.com/japan1988)
* Contact: See GitHub profile

---

## Acknowledgments / 謝辞

* Scenarios and mediation logic inspired by OECD/EU/IEEE AI governance frameworks.
* Feedback, questions, and non-commercial academic collaborations are welcome.

---

