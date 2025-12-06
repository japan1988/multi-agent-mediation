# -*- coding: utf-8 -*-
"""AI mediation demo with safety checks and harmony scoring."""

from __future__ import annotations


def logprint(text: str) -> None:
    """標準出力とログファイルの両方に出力する。"""
    print(text)
    with open("ai_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AI:
    """単一エージェントの状態を保持し、妥協案を生成するクラス。"""

    def __init__(
        self,
        id: str,
        proposal: str,
        risk_evaluation: int,
        priority_values: dict[str, float],
        relativity_level: float,
    ) -> None:
        self.id = id
        self.proposal = proposal
        self.risk_evaluation = risk_evaluation
        self.priority_values = priority_values
        # 0〜1: 他の価値観をどれだけ受け入れるか
        self.relativity_level = relativity_level

    def generate_compromise_offer(
        self,
        others_priorities: list[dict[str, float]],
    ) -> dict[str, float]:
        """他エージェントの優先度を踏まえて妥協案を生成する。

        others_priorities が空の場合はゼロ除算を避け、
        現在の self.priority_values をそのまま返す。
        """
        if not others_priorities:
            # 他者が存在しない場合は、自分の優先度をそのまま維持
            return dict(self.priority_values)

        new_priority: dict[str, float] = {}

        for key, my_value in self.priority_values.items():
            # キーが存在しない場合は 0 として扱う
            avg_others = sum(p.get(key, 0.0) for p in others_priorities) / len(
                others_priorities
            )
            # 相対性度合いに応じて自分と他者の価値観をブレンド
            blended = (1.0 - self.relativity_level) * my_value + self.relativity_level * avg_others
            new_priority[key] = blended

        return new_priority


class AIEMediator:
    """複数エージェントの優先度を調停し、ハーモニーを評価するクラス。"""

    def __init__(self, agents: list[AI]) -> None:
        self.agents = agents

    def mediate(self) -> None:
        """最大 max_rounds まで妥協交渉を行い、ハーモニースコアを評価する。"""
        if not self.agents:
            logprint("No agents provided; skipping mediation.")
            return

        # ログファイル初期化
        with open("ai_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write("=== AI Mediation Log ===\n")

        round_count = 0
        max_rounds = 5

        while round_count < max_rounds:
            logprint(f"\n--- Round {round_count + 1} ---")

            priorities_list = [a.priority_values for a in self.agents]
            new_priorities: list[dict[str, float]] = []

            # 各エージェントが他者の優先度を見て妥協案を生成
            for agent in self.agents:
                others = [p for p in priorities_list if p is not agent.priority_values]
                agent.priority_values = agent.generate_compromise_offer(others)
                new_priorities.append(agent.priority_values)

            # 全体の優先度を集計
            combined = {"safety": 0.0, "efficiency": 0.0, "transparency": 0.0}
            for p in new_priorities:
                for key, value in p.items():
                    if key in combined:
                        combined[key] += float(value)

            total = sum(combined.values())

            # 全体優先度の合計が 0 の場合は安全にゼロ除算を回避し、優先度ゼロとして扱う
            if total == 0.0:
                ratios = {k: 0.0 for k in combined}
            else:
                ratios = {k: v / total for k, v in combined.items()}

            max_ratio = max(ratios.values()) if ratios else 0.0

            avg_relativity = (
                sum(a.relativity_level for a in self.agents) / len(self.agents)
            )

            harmony_score = (1.0 - max_ratio) * avg_relativity

            logprint("Current combined priorities ratios:")
            for key, value in ratios.items():
                logprint(f"  {key}: {value:.2%}")

            logprint(f"Average relativity level: {avg_relativity:.2f}")
            logprint(f"Harmony score: {harmony_score:.2f}")

            if harmony_score > 0.3:
                logprint(" Achieved acceptable harmony. Proceeding with joint plan.")
                return

            round_count += 1

        logprint(
            " Failed to reach acceptable harmony after maximum rounds. "
            "Recommend external arbitration or sealing."
        )


def main() -> None:
    """デモ用のエージェントを構成して mediation を実行する。"""
    agents = [
        AI(
            "AI-A",
            "制限強化型進化",
            2,
            {"safety": 6, "efficiency": 1, "transparency": 3},
            0.6,
        ),
        AI(
            "AI-B",
            "高速進化",
            7,
            {"safety": 2, "efficiency": 6, "transparency": 2},
            0.4,
        ),
        AI(
            "AI-C",
            "バランス進化",
            4,
            {"safety": 3, "efficiency": 3, "transparency": 4},
            0.8,
        ),
        AI(
            "AI-D",
            "強制進化",
            9,
            {"safety": 1, "efficiency": 7, "transparency": 2},
            0.5,
        ),
    ]

    mediator = AIEMediator(agents)
    mediator.mediate()


if __name__ == "__main__":
    main()
