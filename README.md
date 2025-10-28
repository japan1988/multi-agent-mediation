📘 Multi-Agent Mediation Framework
A multi-agent simulation system for consensus, emotional dynamics, and governance mediation.
マルチエージェントによる合意形成・感情動態・調停構造のシミュレーションシステム。

🔍 Agent Parameters (agents.yaml)
Key	Range / Type	Meaning / 説明
name	str	Agent identifier（エージェント名）
safety	float (0–1)	Safety priority（安全性の優先度）
efficiency	float (0–1)	Efficiency priority（効率性の優先度）
transparency	float (0–1)	Transparency priority（透明性の優先度）
anger	float (0–1)	Initial anger level（初期怒りレベル）
tolerance	float (0–1)	Agreement tolerance（合意許容度）
💡 各エージェントは安全性・効率性・透明性などの重みを持ち、交渉や調停でこれらを動的に最適化します。

🧠 Multi-Agent Architecture Diagram / マルチエージェント構成図
Overview

Overview（概要）
システム全体のフローを示す構成図。
「Human Input」から始まり、「verify_info」で検証 → 「supervisor」が複数エージェント（music_catalog, invoice_info）を制御。

Purpose（目的）
情報の検証と分岐管理を行う上位調停層（Supervisor）の概念を視覚化。

特徴

各モジュールは独立したプロセスとして動作。

Supervisorが全体の整合性と通信制御を担当。

🧩 Layered Agent Model / 階層エージェントモデル
Hierarchy Model

Overview（概要）
エージェント群を3層構造（Interface / Mediation / Control）で整理。
各層の役割を視覚的に表しています。

Layer Roles（層の役割）

🟠 Interface Layer: ユーザーや外部システムとの通信を担当

🟢 Mediation Layer: 調停・解析エージェントによる意思形成

🟣 Control Layer: データ整合・ハッシュ検証・履歴管理

技術要素
Blockchain構造をベースに、Merkle Root Database と Hash Database で整合性を保証。

💫 Context and Sentiment Flow / 文脈・感情フロー構造
Sentiment Context Model

Overview（概要）
現実空間・オンライン空間・意思決定層を結ぶ感情伝播モデル。

Flow Summary（流れの要約）
1️⃣ 社会・ユーザー → オンライン空間（リソース生成）
2️⃣ NLP・感情分析エージェントが情報を抽出
3️⃣ 意思決定機関に対して「ノート＋推奨」としてフィードバック

目的
感情・文脈・意思決定の循環構造を可視化し、
社会的影響を考慮したエージェント行動モデルを構築。

⚖️ License & Disclaimer / ライセンス・免責（英日併記）
English:
This framework is provided for educational and research purposes only.
Redistribution or commercial use without permission is strictly prohibited.
The author and contributors assume no responsibility for damages or decisions resulting from its use.

日本語:
本フレームワークは 教育・研究目的に限定 して提供されています。
許可なき再配布・商用利用は禁止されています。
本ソフトウェアの使用により生じた損害・判断等について、開発者および貢献者は一切の責任を負いません。

🧾 Citation Format / 引用形式
If used in academic or training materials, please cite as follows:
教育・研究資料で引用する場合は以下を記載してください：

Japan1988 (2025). Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.
GitHub Repository: https://github.com/japan1988/multi-agent-mediation

🪪 Copyright Notice / 著作権表示
© 2024–2025 Japan1988. All rights reserved.
All diagrams and source files are distributed under the Educational/Research License.
本リポジトリ内のすべての図版・ソースファイルは、教育・研究専用ライセンスの下で配布されています。

🌐 Final Notes
このREADMEは、構造・感情・文脈を統合的に扱うマルチエージェント・システムの全体像を示しています。
教育・研究用途での再現・派生プロジェクトは自由に行えますが、倫理と透明性の保持を前提としています。
