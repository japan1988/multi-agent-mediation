📘 Maestro Orchestrator — Multi-Agent Orchestration Framework
<p align="center">
  <!-- Repository Status -->
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Educational%20%2F%20Research-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <!-- Technical Meta -->
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/code%20style-Black-000000.svg?style=flat-square" alt="Code Style: Black">
  <img src="https://img.shields.io/badge/status-stable-brightgreen.svg?style=flat-square" alt="Status">
  <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/v/release/japan1988/multi-agent-mediation?style=flat-square" alt="

⸻

🎯 目的 / Purpose

複数エージェント（または複数手法）を統括し、誤り・危険・不確実を検知したら停止／分岐／人間へ差し戻すための実験的フレームワークです。
主眼は「交渉そのもの」ではなく、**タスク実行の指揮（Orchestration）**と、安全制御（Guardrails）、監査（Audit）、**再現性（Replay）**にあります。
	•	Routing: タスク分解と担当割当（どのエージェントに何をさせるか）
	•	Guardrails: 禁止・越権・外部副作用の封印（fail-closed）
	•	Audit: いつ何を理由に止めたかのログ化（証跡）
	•	HITL: 判断不能や重要判断は人間へエスカレーション
	•	Replay: 同条件で再実行して差分検知できるようにする

⸻

🧠 Concept Overview / 概念設計

Component	Function	Description
🧩 Orchestration Layer	指揮層	タスク分解、ルーティング、再試行、再割当
🛡️ Safety & Policy Layer	安全制御層	危険出力・越権・外部副作用の検知と封印（fail-closed）
🧾 Audit & Replay Layer	監査層	監査ログ、差分検知、再現実行、レポート生成
👤 HITL Escalation	人間差し戻し	不確実・高リスク・仕様未確定は人間へ戻す

目的は「複数エージェントを“動かす”こと」ではなく、
間違い・危険・不確実を“止められる”統括を作ること。

⸻

🗂️ Repository Structure / ファイル構成

Path	Type	Description / 説明
agents.yaml	Config	エージェントパラメータ定義
ai_mediation_all_in_one.py	Core	**統括実行（ルーティング／検査／分岐）**の中心モジュール
ai_alliance_persuasion_simulator.py	Simulator	複数エージェント相互作用のシミュレーション
ai_governance_mediation_sim.py	Simulator	ポリシー適用・封印・差し戻しの挙動確認
ai_pacd_simulation.py	Experiment	段階的評価（例：再試行・停止条件の検証）
ai_hierarchy_dynamics_full_log_20250804.py	Logger	監査ログ強化・階層動態追跡
multi_agent_architecture_overview.webp	Diagram	構成図（全体）
multi_agent_hierarchy_architecture.png	Diagram	階層モデル図
sentiment_context_flow.png	Diagram	入力→文脈→行動の流れ図（図はそのまま）
requirements.txt	Dependency	Python依存関係
.github/workflows/ci.yml	Workflow	CI/Lintワークフロー
LICENSE	License	教育・研究ライセンス
README.md	Documentation	本ドキュメント

💡 すべての .py モジュールは独立実行可能。
agents.yaml が全エージェント設定の共通基盤。
ai_mediation_all_in_one.py が中心モジュールとして 統括（orchestrate） を行います。

⸻

🧭 Architecture Diagram / 構成図

<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>


🔄 概要フロー

Human Input → verify_info → supervisor → agents → logger
	•	verify_info: 入力検証（形式、前提、禁止・越権の兆候）
	•	supervisor: ルーティング／再試行／停止／HITL の分岐を統括
	•	logger: 監査ログ（停止理由、分岐理由、再現性のためのメタ情報）

⸻

🌐 Layered Agent Model / 階層エージェントモデル

<p align="center">
  <img src="docs/multi_agent_hierarchy_architecture.png" width="720" alt="Layered Architecture">
</p>


Layer	Role	What it does
Interface Layer	外部入力層	入力契約（スキーマ）／検証／ログ送信
Agent Layer	実行層	タスク処理（提案・生成・検算など役割に応じて）
Supervisor Layer	統括層	ルーティング、整合チェック、停止、HITL


⸻

🔬 Context Flow / 文脈フロー

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Context Flow Diagram">
</p>


🧠 フロー（説明だけ変更）
	1.	Perception（知覚） — 入力を実行可能な要素へ分解（タスク化）
	2.	Context（文脈解析） — 前提・制約・危険要因を抽出（ガードの根拠）
	3.	Action（行動生成） — エージェントへ指示し、結果を検査して分岐（STOP / REROUTE / HITL）

すべての段階で 安全制御（fail-closed） を優先し、
危険・越権・判断不能は停止または人間へ差し戻します。

⸻

⚙️ Execution Example / 実行例

# 基本実行
python3 ai_mediation_all_in_one.py

# ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# ポリシー適用の挙動確認
python3 ai_governance_mediation_sim.py --scenario policy_ethics


⸻



