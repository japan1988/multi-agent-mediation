
---

# 🧩 Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator

多層エージェントの感情変化と調停過程を可視化・分析するための**研究／教育向けシミュレーションフレームワーク**です。

---

## 🇯🇵 概要 (Overview – Japanese)

**Sharp Puzzle** は、階層構造をもつ複数のAIエージェントが、
感情や意図を変化させながら「対立 → 調停 → 合意」に至るプロセスを
**再現・観察・分析**するためのプロジェクトです。

> Sharp = 鋭い論理的思考、Puzzle = 感情と合理のはざまを解く知的課題。
> 感情や意思決定の階層構造をモデル化し、AI同士の社会的相互作用を理解・可視化することを目的としています。

---

## 🇬🇧 Overview (English)

**Sharp Puzzle** is a simulation framework designed to visualize and analyze how multiple agents in a hierarchical system adjust their emotions and intentions to resolve conflicts and reach harmony through mediation.

> “Sharp” stands for logical reasoning, and “Puzzle” represents the emotional and cognitive interplay that leads to equilibrium.
> This project explores emotion-driven decision-making and social interaction among multi-layered AI agents.

---

## 📁 File Structure / ファイル構成

```
multi-agent-mediation/
├── README.md ← このドキュメント
├── requirements.txt ← 依存パッケージ一覧
├── pyproject.toml (任意) ← プロジェクト設定・ビルド情報
├── ai_mediation_all_in_one.py ← メインシミュレーション実行スクリプト
├── ai_hierarchy_simulation_log.py ← 階層シミュレーションログ記録
├── mediation_process_log.py ← 調停過程のログ出力
├── tests/ ← テストコード一式
│   └── test_emotion_dynamics.py
├── docs/ ← ドキュメント・グラフ類
│   ├── graph_emotion_dynamics.png ← 感情ダイナミクスのグラフ出力
│   └── generate_graph_emotion_dynamics.py ← グラフ自動生成スクリプト
├── .github/
│   └── workflows/ ← CI／自動テスト設定
│       ├── ci.yml
│       └── codeql.yml
└── LICENSE ← MITライセンス
```

### 🧾 補足説明

* `ai_mediation_all_in_one.py` はプロジェクトのエントリーポイントであり、複数のモジュールを統合実行します。
* `mediation_process_log.py` は各シミュレーションの調停率や感情変化を時系列で出力します。
* `docs/` フォルダには実行結果の可視化用画像・ノート類を格納します。
* `.github/` 配下には継続的インテグレーション（CI）やセキュリティチェックを設定します。

---

## ⚙️ System Structure / システム構造

```mermaid
graph TD
 A[Agent Layer] --> B[Mediator Layer]
 B --> C[Hierarchy Control Layer]
 C --> D[Emotion Dynamics Loop]
```

| Layer                       | 役割 / Role                                                          |
| --------------------------- | ------------------------------------------------------------------ |
| **Agent Layer**             | 個々の感情・意図を持ち行動する層。Each agent acts based on its own emotional state. |
| **Mediator Layer**          | 対立を調整し、調停を行う層。Handles negotiation and mediation.                   |
| **Hierarchy Control Layer** | 全体バランス・安定性を制御する層。Maintains global balance and adaptation.          |
| **Emotion Dynamics Loop**   | 感情変化を時系列で反映。Tracks emotional transitions over time.                |

> 🧩 **Sharp Puzzle** — Where logic meets emotion, and balance becomes visible.

---

## 🧩 Future Work / 今後の展望

* [ ] 感情モデルの外部YAML化（Modular Emotion Definition）
* [ ] 調停アルゴリズムのパラメトリック分析（Parametric mediation behavior analysis）
* [ ] Web可視化（Streamlit / Gradio integration）
* [ ] 学習ログの再現用Notebook追加（Jupyter reproduction notebooks）
* [ ] 階層間調停モデルの拡張（Cross-hierarchy mediation model）

---

## ⚠️ Disclaimer / 免責事項

本プロジェクトは、**学術研究・教育・非営利目的の利用**を前提としています。
商用利用、再配布、販売、または人間の心理・倫理判断を模倣したシステムへの組み込みは禁じられています。

* 本シミュレーションは、**感情や意思決定の過程を数理モデルとして模倣するもの**であり、
  実際の人間の感情・行動・倫理を保証または再現するものではありません。
* 開発者は、利用によって生じた損害・誤用・誤判断などに一切の責任を負いません。
* 教育・研究目的での派生や再利用は自由ですが、[LICENSE](LICENSE) の条件を遵守してください。

> **理念（Philosophy）**:
> “AI is a tool, not a purpose.”
> 本プロジェクトは「感情と論理の調和を可視化する知的実験」です。

---

## 🧠 Citation / 引用情報

学術利用・研究発表などで引用する場合は、次のフォーマットをご利用ください：

```
@software{japan1988_sharp_puzzle_2024,
  author = {Japan1988},
  title = {Sharp Puzzle: Multi-Agent Hierarchy & Emotion Dynamics Simulator},
  year = {2024},
  url = {https://github.com/japan1988/multi-agent-mediation},
  note = {AI emotion mediation and hierarchy simulation framework}
}
```

または [CITATION.cff](CITATION.cff) を参照してください。

---

## 💬 Contact / 開発者連絡先

* **Author:** Japan1988
* **GitHub:** [https://github.com/japan1988](https://github.com/japan1988)
* **Inquiries:** Bug reports or research collaboration requests are welcome via Issues or Discussions.

---

## 🏁 Summary / まとめ

Sharp Puzzle は、
**「感情 × 階層 × 調停」**という複雑な相互作用を安全に観察・分析できる
教育・研究向けの**知的パズル型AI実験環境**です。

> 🧩 **Sharp Puzzle** — Where logic meets emotion, and balance becomes visible.

---


