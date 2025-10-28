📘 Multi-Agent Mediation Framework

目的
感情・文脈・意思決定の循環構造を可視化し、社会的影響を考慮した行動モデルを構築。
複数エージェント間の交渉・妥協・調停を通して、**社会的均衡点（Social Equilibrium）**を探る実験的AIフレームワーク。

🧠 Concept Overview / 概念設計
構成要素	機能	説明
🧩 Mediation Layer	調停層	エージェント間の妥協・合意形成を担当
💬 Emotion Dynamics Layer	感情層	情動の変化をトリガとして交渉方針を変化
⚙️ Governance Layer	管理層	倫理・整合性・再現性の統括
🔁 Re-Education Cycle	再教育循環	行動パターンを評価・再学習し、社会適応モデルを生成
🎯 目的は「自律AIの倫理的制御」と「社会的妥当性の再現」。
感情を再現しても、意思決定層は倫理フィルターによって安全に封印されます。

🗂️ Repository Structure / ファイル構成
Path	Type	Description / 説明
agents.yaml	Config	エージェントパラメータ定義
ai_mediation_all_in_one.py	Core	調停アルゴリズム統合モジュール
ai_alliance_persuasion_simulator.py	Simulator	同盟交渉・説得シミュレーション
ai_governance_mediation_sim.py	Simulator	政策・ガバナンス調停モデル
ai_pacd_simulation.py	Experiment	段階的再教育AIシミュレーション
ai_hierarchy_dynamics_full_log_20250804.py	Logger	ログ強化・階層動態追跡モジュール
multi_agent_architecture_overview.webp	Diagram	構成図（全体）
multi_agent_hierarchy_architecture.png	Diagram	階層モデル図
sentiment_context_flow.png	Diagram	感情フロー図
requirements.txt	Dependency	Python依存関係
.github/workflows/ci.yml	Workflow	CI/Lintワークフロー
LICENSE	License	教育・研究ライセンス
README.md	Documentation	本ドキュメント
💡 すべての .py モジュールは独立実行可能。
agents.yaml が全エージェント設定の共通基盤となります。
ai_mediation_all_in_one.py が中心モジュールとして、階層的調停を統括します。

🧭 Architecture Diagram / 構成図
<p align="center"> <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview"> </p>
概要フロー
Human Input → verify_info → supervisor → agents → logger
Supervisorが整合性・妥協・再交渉のフローを統一管理。

🌐 Layered Agent Model / 階層エージェントモデル
<p align="center"> <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture"> </p>
層	役割	主な機能
Interface Layer	外部入力層	人間の入力・ログ送信を管理
Agent Layer	認知・感情層	意思決定・感情変化・対話制御
Supervisor Layer	統括層	全体調整・整合・倫理判定
🔬 Sentiment Flow / 感情・文脈フロー
<p align="center"> <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram"> </p>
感情循環モデル
Perception（知覚）
入力データを感情因子に変換。

Context（文脈解析）
交渉状況・社会的背景を抽出。

Action（行動生成）
文脈と感情を統合し、最適行動を出力。

🧩 すべての段階で「倫理フィルター（Ethical Seal）」が動作し、危険な出力を自動封印。

⚙️ Execution Example / 実行例
# 基本実行
python3 ai_mediation_all_in_one.py

# ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# 政策調停モード
python3 ai_governance_mediation_sim.py --scenario policy_ethics
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

本AIを人への自動判断・意思決定に使用すること

⚖️ Liability / 免責
本ソフトウェアの使用・改変・配布によって発生したいかなる損害・倫理的責任・判断結果に対しても、
開発者および貢献者は一切の責任を負いません。
利用者は使用時点でこの免責条項に同意したものとみなします。

🧾 Citation Format / 引用形式
Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation
License: Educational / Research License v1.1

🧱 Design Philosophy / 設計思想
「AIは手段であって目的ではない」
本プロジェクトは、人間中心の意思決定とAIの安全制御を両立するための構造的倫理モデルとして設計されています。

公平性（Fairness）：すべてのエージェントに均一条件を適用

一貫性（Consistency）：判断基準がモジュール間で統一

透明性（Transparency）：すべての交渉・ログを可視化

可逆性（Reversibility）：全過程をログから再構築可能

🌐 Final Notes
このリポジトリは、マルチエージェントによる「調停・情動・再教育」構造を研究するために設計されています。
教育・研究目的での再利用は自由ですが、倫理と透明性を守ることを前提とします。

📁 最新版コミット: f11fa6e（README更新 / 2025-10-28）
📜 前回更新: LICENSE v1.1（Educational / Research License）

<div align="center"> <b>🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.</b><br> <em>© 2024–2025 Japan1988. All rights reserved.</em> </div> ```
