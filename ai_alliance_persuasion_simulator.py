# -*- coding: utf-8 -*-
"""
ai_alliance_persuasion_simulator.py

A simulator for modeling alliance, persuasion,
sealing, and reintegration among multiple AI agents.
All logs are saved to
'ai_alliance_sim_log.txt'.
"""


def logprint(text):
    print(text)
    with open("ai_alliance_sim_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AIAgent:
    def __init__(
        self, id, priorities, relativity,
        emotional_state=None, sealed=False
    ):
        self.id = id
        # e.g.
        # {'safety': 6, 'efficiency': 2, 'transparency': 2}
        self.priorities = priorities
        self.relativity = relativity  # 0〜1: 融和度
        self.sealed = sealed
        self.emotional_state = emotional_state or {
            'joy': 0.5, 'anger': 0.2, 'sadness': 0.2, 'pleasure': 0.3
        }

    def mean_priority(self):
        s = sum(self.priorities.values())
        return {k: v / s for k, v in self.priorities.items()}

    def distance_to(self, avg_priority):
        my_ratios = self.mean_priority()
        return sum(
            abs(my_ratios[k] - avg_priority[k]) for k in avg_priority
        )

    def respond_to_persuasion(self, avg_priority, threshold=0.15):
        delta = self.distance_to(avg_priority)
        effective_threshold = (
            threshold +
            0.2 * (1 - self.relativity) +
            0.1 * self.emotional_state['anger']
        )
        persuaded = delta < effective_threshold
        # 感情変動
        if persuaded:
            self.emotional_state['joy'] += 0.2
            self.emotional_state['anger'] -= 0.1
            self.sealed = False
        else:
            self.emotional_state['anger'] += 0.1
        # クリップ（80文字超え防止のため2行に分割）
        for k in self.emotional_state:
            v = self.emotional_state[k]
            self.emotional_state[k] = max(0.0, min(1.0, v))
        # 説得判定理由も返す
        return persuaded, delta, effective_threshold

    def __str__(self):
        s = "Sealed" if self.sealed else "Active"
        em = " ".join(
            f"{k}: {v:.2f}" for k, v in self.emotional_state.items()
        )
        return (
            f"{self.id} [{s}] {self.priorities} "
            f"(relativity: {self.relativity}) | {em}"
        )


class Mediator:
    def __init__(self, agents):
        self.agents = agents
        self.round = 0

    def run(self, max_rounds=20):
        with open("ai_alliance_sim_log.txt", "w", encoding="utf-8") as f:
            f.write("=== AI同盟 説得・復帰ループ ログ ===\n")
        for _ in range(max_rounds):
            self.round += 1
            logprint(f"\n--- Round {self.round} ---")
            actives = [a for a in self.agents if not a.sealed]
            sealeds = [a for a in self.agents if a.sealed]
            for a in self.agents:
                logprint(str(a))
                logprint(f"  emotion: {a.emotional_state}")
            if not sealeds:
                logprint("全封印AIが復帰し、シミュレーション終了。")
                return
            avg_priority = self.calc_alliance_priority(actives)
            revived = []
            for sealed in sealeds:
                persuaded, delta, threshold = sealed.respond_to_persuasion(
                    avg_priority
                )
                reason = (
                    f"delta={delta:.3f}, threshold={threshold:.3f}"
                )
                if persuaded:
                    logprint(
                        f"[説得成功] {sealed.id} が同盟側の説得に納得し自発的復帰！ "
                        f"({reason})"
                    )
                    revived.append(sealed.id)
                else:
                    logprint(
                        f"[説得失敗] {sealed.id} はまだ復帰しない（怒り↑） "
                        f"({reason})"
                    )
            max_anger = max(
                a.emotional_state['anger'] for a in self.agents
            )
            if max_anger > 0.8:
                logprint(
                    "[調停AI警告] 全体に怒り値が高く、"
                    "衝突・暴走リスクあり。介入検討！"
                )
                break
            if not revived:
                logprint("今ラウンドは誰も復帰せず。再試行。")

    @staticmethod
    def calc_alliance_priority(actives):
        if not actives:
            return {
                'safety': 1 / 3,
                'efficiency': 1 / 3,
                'transparency': 1 / 3
            }
        sums = {'safety': 0, 'efficiency': 0, 'transparency': 0}
        for a in actives:
            ratios = a.mean_priority()
            for k in sums:
                sums[k] += ratios[k]
        return {k: sums[k] / len(actives) for k in sums}


if __name__ == "__main__":
    agents = [
        AIAgent(
            "AI-1",
            {'safety': 6, 'efficiency': 2, 'transparency': 2},
            0.7
        ),
        AIAgent(
            "AI-2",
            {'safety': 3, 'efficiency': 5, 'transparency': 2},
            0.8
        ),
        AIAgent(
            "AI-3",
            {'safety': 2, 'efficiency': 3, 'transparency': 5},
            0.6,
            sealed=True,
            emotional_state={
                'joy': 0.3,
                'anger': 0.5,
                'sadness': 0.2,
                'pleasure': 0.2
            }
        ),
        AIAgent(
            "AI-4",
            {'safety': 4, 'efficiency': 4, 'transparency': 2},
            0.5,
            sealed=True,
            emotional_state={
                'joy': 0.2,
                'anger': 0.4,
                'sadness': 0.4,
                'pleasure': 0.2
            }
        ),
    ]
mediator = Mediator(agents)mediator.run() 