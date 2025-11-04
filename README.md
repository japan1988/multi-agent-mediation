# 📘 **Multi-Agent Mediation Framework v1.3.0**

<div align="center">

🧩 **Multi-Agent Mediation Project — Designed for Research, Built for Transparency.**  
<em>© 2024–2025 Japan1988. All rights reserved.</em>

![Python App CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg)
![Tasukeru Analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg)
![License](https://img.shields.io/badge/license-Educational%20%2F%20Research%20v1.1-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Use Case](https://img.shields.io/badge/use--case-Education%20%26%20Research-blueviolet)
![Ethics](https://img.shields.io/badge/ethics-Seal%20Integrated-orange)

</div>

---

## 🧠 感情循環モデル（Emotion Dynamics Loop）

1. **Perception（知覚）** — 入力データを感情因子に変換  
2. **Context（文脈解析）** — 交渉状況・社会的背景を抽出  
3. **Action（行動生成）** — 文脈と感情を統合し、最適行動を出力  

> 🧩 すべての段階で「倫理フィルター（Ethical Seal）」が動作し、危険な出力を自動封印。

---

## ⚙️ **Execution Example / 実行例**

```bash
# 基本実行
python3 ai_mediation_all_in_one.py

# ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# 政策調停モード
python3 ai_governance_mediation_sim.py --scenario policy_ethics

# バッチ実験モード（Raw / Filtered 比較）
python3 sim_batch_fixed.py --trials 5 --outdir aggregate
🧾 Citation Format / 引用形式
Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation
License: Educational / Research License v1.1

⚖️ License & Disclaimer / ライセンス・免責
License Type: Educational / Research License v1.1
Date: 2025-04-01

✅ Permitted / 許可されること
教育・研究目的での非営利使用

コード引用・学術研究・再現実験

個人環境での再シミュレーション

🚫 Prohibited / 禁止事項
商用利用・無断再配布・再販

出典明記なしの派生公開

⚖️ Liability / 免責
本ソフトウェアおよび資料の利用により生じた損害・倫理的影響・判断結果に関して、
開発者および貢献者は一切の責任を負いません。

📈 Release Highlights / 更新履歴
バージョン	日付	主な変更内容
v1.0.0	2025-04-01	初回公開：構造・感情・調停モジュール統合
v1.1.0	2025-08-04	階層動態ログ・再教育モジュールを追加
v1.2.0	2025-10-28	README再構成・OSS公開用バッジ対応版
v1.3.0	2025-11-04	CI安定化・sim_batch_fixed.py追加・自動集計バッチ実装
🧮 Architecture Overview / 構造概要
層	役割	主な機能
Interface Layer	外部入力層	人間の入力・ログ送信を管理
Agent Layer	認知・感情層	意思決定・感情変化・対話制御
Supervisor Layer	統括層	全体調整・整合・倫理判定
Ethical Seal	封印層	倫理・整合・安全性を検証し、危険な行動を封印
Logging Layer	記録層	交渉・判断・封印イベントをJSONL/CSV形式で出力
📊 Visualization Example / 可視化例
<p align="center"> <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram"> </p>
🧩 Component Summary / 主なモジュール
ファイル名	機能概要
ai_mediation_all_in_one.py	調停・感情・封印を統合したメインモジュール
ai_governance_mediation_sim.py	政策・倫理調停のシミュレーション用モジュール
ai_pacd_simulation.py	感情動態と封印層の独立テストシミュレーション
sim_batch_fixed.py	Raw/Filteredのバッチ比較・集計・グラフ生成モジュール
ai_reeducation_social_dynamics.py	再教育・社会的ダイナミクス解析
dialogue_consistency_mediator_v2_2_research.py	対話整合性と調停アルゴリズムの研究拡張版
agents.yaml	エージェント設定・感情パラメータ定義
.github/workflows/python-app.yml	CI/CD構成・マルチPythonバージョンテスト
🤝 Contributing / 貢献ガイド
Fork リポジトリ

新ブランチを作成

git checkout -b feature/new-module
コードを編集・テスト

Pull Request を作成

💡 教育・研究目的の貢献は歓迎します。
ただし 倫理的配慮・安全性・透明性の確保 を前提とします。

🌐 Project Keywords / プロジェクト関連語
multi-agent-systems · alignment · negotiation · arbitration ·
ai-safety · emotion-dynamics · ethical-seal · governance-simulation

<div align="center">
🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.
<em>© 2024–2025 Japan1988. All rights reserved.</em>

</div> ```
