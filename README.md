<h1 align="center">📘 <b>Multi-Agent Mediation Framework</b></h1>

<table>
<tr><th>層</th><th>役割</th><th>主な機能</th></tr>
<tr><td><b>Interface Layer</b></td><td>外部入力層</td><td>人間の入力・ログ送信を管理</td></tr>
<tr><td><b>Agent Layer</b></td><td>認知・感情層</td><td>意思決定・感情変化・対話制御</td></tr>
<tr><td><b>Supervisor Layer</b></td><td>統括層</td><td>全体調整・整合・倫理判定</td></tr>
</table>

<hr>

<h2>🔬 <b>Sentiment Flow / 感情・文脈フロー</b></h2>

<p align="center">
  <img src="docs/sentiment_context_flow.png" width="720" alt="Emotion Flow Diagram">
</p>

<h3>🧠 感情循環モデル</h3>

<ol>
<li><b>Perception（知覚）</b> — 入力データを感情因子に変換</li>
<li><b>Context（文脈解析）</b> — 交渉状況・社会的背景を抽出</li>
<li><b>Action（行動生成）</b> — 文脈と感情を統合し、最適行動を出力</li>
</ol>

<blockquote>🧩 すべての段階で「倫理フィルター（Ethical Seal）」が動作し、危険な出力を自動封印。</blockquote>

<hr>

<h2>🗂️ <b>File Structure / ファイル構成</b></h2>

<pre><code>
multi-agent-mediation/
├── ai_mediation_all_in_one.py              # 中核モジュール（調停AIメイン）
├── ai_governance_mediation_sim.py          # 政策・倫理シナリオ用
├── ai_alliance_persuasion_simulator.py     # 説得・同盟形成シミュレータ
├── ai_hierarchy_dynamics_full_log_2.py     # 階層動態・感情ログ記録
├── ai_pacd_simulation.py                   # PACD（感情パターン循環）モデル
├── ai_mediation_governance_demo.py         # 教育向けデモ
│
├── aggregate/
│   ├── metrics.csv
│   └── diff_table_gen.py
│
├── tests/
│   └── test_sample.py
│
├── docs/
│   └── sentiment_context_flow.png
│
├── agents.yaml
├── LICENSE
├── README.md
└── .github/workflows/python-app.yml
</code></pre>

<hr>

<h2>⚙️ <b>Execution Example / 実行例</b></h2>

<pre><code class="bash">
# 基本実行
python3 ai_mediation_all_in_one.py

# ログ付きで実行
python3 ai_mediation_all_in_one.py --log logs/session_001.jsonl

# 政策調停モード
python3 ai_governance_mediation_sim.py --scenario policy_ethics
</code></pre>

<hr>

<h2>🧾 <b>Citation Format / 引用形式</b></h2>

<p>Japan1988 (2025). <i>Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator.</i><br>
GitHub Repository: <a href="https://github.com/japan1988/multi-agent-mediation">https://github.com/japan1988/multi-agent-mediation</a><br>
License: MIT + Attribution (Commercial Use Permitted with Credit)</p>

<hr>

<h2>⚖️ <b>License & Attribution / ライセンスおよび出典表示</b></h2>

<p>This project is released under the <b>MIT License + Attribution</b> with the following conditions:</p>

<ol>
<li>Commercial use is permitted <b>only if the source is clearly attributed</b>.<br>
 Required attribution:<br>
 <code>"Based on the work by Takuya Enoki (japan1988) – Multi-Agent Mediation Framework"</code><br>
 and a link to the original repository.</li>
<li>Redistribution and modification are allowed under the same license terms.</li>
<li>The author assumes <b>no liability</b> for any damages or losses arising from use of this software.</li>
</ol>

<p><b>本プロジェクトは MIT ライセンス に基づき公開されていますが、商用利用時は必ず出典（作者名・リポジトリURL）を明記してください。</b><br>
再配布・改変は自由ですが、本ソフトウェアの使用によって生じたいかなる損害についても、作者は一切の責任を負いません。</p>

<hr>

<h2>📈 <b>Release Highlights / 更新履歴</b></h2>

<table>
<tr><th>バージョン</th><th>日付</th><th>主な変更内容</th></tr>
<tr><td>v1.0.0</td><td>2025-04-01</td><td>初回公開：構造・感情・調停モジュール統合</td></tr>
<tr><td>v1.1.0</td><td>2025-08-04</td><td>階層動態ログ・再教育モジュールを追加</td></tr>
<tr><td>v1.2.0</td><td>2025-10-28</td><td>README再構成・OSS公開用バッジ対応版</td></tr>
</table>

<hr>

<h2>🤝 <b>Contributing / 貢献ガイド</b></h2>

<ol>
<li>Fork リポジトリ</li>
<li>新ブランチを作成 <pre><code>git checkout -b feature/new-module</code></pre></li>
<li>コードを編集・テスト</li>
<li>Pull Request を作成</li>
</ol>

<p>💡 教育・研究目的の貢献は歓迎します。<br>
ただし 倫理的配慮・安全性・透明性の確保を前提とします。</p>

<hr>

<div align="center">
<b>🧩 Multi-Agent Mediation Project — Designed for Research, Built for Transparency.</b><br>
<em>© 2024–2025 Takuya Enoki (japan1988). All rights reserved.</em>
</div>
