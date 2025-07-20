# -*- coding: utf-8 -*-
"""
Multi-Agent Mediation Simulator with Reeducation
Author: Your Name
Description:
  - 合意形成・再教育・封印・復帰まで実装
  - ログ出力/ファイル保存（PEP8対応）
"""


def logprint(text):
    """ログ出力＆ファイル保存"""
    print(text)
    with open("ai_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AI:
    """AIエージェント"""

    def __init__(
        self,
        id,
        proposal,
        risk_evaluation,
        priority_values,
        relativity_level,
        emotional_state=None
    ):
        self.id = id
        self.proposal = proposal
        self.risk_evaluation = risk_evaluation
        self.priority_values = priority_values
        self.relativity_level = relativity_level
        self.emotional_state = emotional_state or {
            'joy': 0.0,
            'anger': 0.0,
            'sadness': 0.0,
            'pleasure': 0.0
        }

    def generate_compromise_offer(self, others_priorities):
        shift = (
            self.emotional_state.get('joy', 0) * 0.2 +
            self.emotional_state.get('pleasure', 0) * 0.15 -
            self.emotional_state.get('anger', 0) * 0.3 -
            self.emotional_state.get('sadness', 0) * 0.25
        )
        self.relativity_level = min(
            1.0,
            max(0.0, self.relativity_level + shift)
        )
        new_priority = {}
        for k in self.priority_values:
            avg_others = (
                sum(o[k] for o in others_priorities) /
                len(others_priorities)
            )
            new_priority[k] = (
                (1 - self.relativity_level) * self.priority_values[k] +
                self.relativity_level * avg_others
            )
        return new_priority

    def is_emotionally_unstable(self):
        return (
            self.emotional_state.get('anger', 0) > 0.7 or
            self.emotional_state.get('sadness', 0) > 0.8 or
            self.emotional_state.get('joy', 0) > 0.95
        )

    def emotion_str(self):
        return " ".join(
            f"{k}:{v:.2f}" for k, v in self.emotional_state.items()
        )

    def will_agree_with_plan(self, plan_ratios, tolerance=0.25):
        my_sum = sum(self.priority_values.values())
        my_ratios = {
            k: self.priority_values[k] / my_sum
            for k in plan_ratios
        }
        score = sum(
            abs(plan_ratios[k] - my_ratios[k])
            for k in plan_ratios
        )
        return score < tolerance


class ReeducationMediator:
    """再教育AI：感情・priority補正"""

    def __init__(self, reduction=0.15, priority_shift=0.15):
        self.reduction = reduction
        self.priority_shift = priority_shift

    def reeducate(self, ai, joint_plan_ratios=None):
        logprint(f"[再教育AI] {ai.id} の感情・priorityを再教育します")
        before_priority = ai.priority_values.copy()
        for k in ai.emotional_state:
            if k in ['anger', 'sadness']:
                ai.emotional_state[k] = max(
                    0.0,
                    ai.emotional_state[k] - self.reduction * 1.2
                )
            else:
                ai.emotional_state[k] = max(
                    0.0,
                    ai.emotional_state[k] - self.reduction * 0.8
                )
        if joint_plan_ratios:
            total = sum(ai.priority_values.values())
            for k in ai.priority_values:
                diff = joint_plan_ratios[k] * total - ai.priority_values[k]
                ai.priority_values[k] += diff * self.priority_shift
        logprint(f"    → priority: {before_priority} → {ai.priority_values}")
        logprint(f"    → 感情: {ai.emotion_str()}")


class AIEMediator:
    """全体調停AI：封印・再教育・復帰"""

    def __init__(self, agents, reeducation_mediator=None):
        self.agents = agents
        self.reeducation_mediator = reeducation_mediator

    def mediate(self):
        with open("ai_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write(
                "=== Multi-Agent Mediation Log "
                "(with Reeducation) ===\n"
            )

        round_count = 0
        max_rounds = 30
        agents = self.agents.copy()
        sealed_agents = []

        while round_count < max_rounds and len(agents) > 1:
            logprint(f"\n--- Round {round_count + 1} ---")
            for ai in agents:
                logprint(f"{ai.id} 感情: {ai.emotion_str()}")

            round_sealed = [
                ai for ai in agents
                if ai.is_emotionally_unstable()
            ]
            for ai in round_sealed:
                logprint(f"[封印トリガー] 感情過剰：{ai.id}")
            sealed_agents.extend(
                [ai for ai in round_sealed if ai not in sealed_agents]
            )
            agents = [
                ai for ai in agents
                if not ai.is_emotionally_unstable()
            ]

            if not agents:
                logprint("全AI封印により調停停止。")
                break
            if len(agents) == 1:
                logprint(f"最終残存AI：{agents[0].id} のみ、調停停止。")
                break

            priorities_list = [a.priority_values for a in agents]
            new_priorities = []
            for ai in agents:
                others = [
                    p for p in priorities_list
                    if p != ai.priority_values
                ]
                ai.priority_values = ai.generate_compromise_offer(others)
                new_priorities.append(ai.priority_values)

            combined = {
                'safety': 0,
                'efficiency': 0,
                'transparency': 0
            }
            for p in new_priorities:
                for k in p:
                    combined[k] += p[k]
            total = sum(combined.values())
            ratios = {k: combined[k] / total for k in combined}
            max_ratio = max(ratios.values())
            avg_relativity = sum(
                a.relativity_level for a in agents
            ) / len(agents)
            harmony_score = (1 - max_ratio) * avg_relativity

            logprint("Current combined priorities ratios:")
            for k, v in ratios.items():
                logprint(f"  {k}: {v:.2%}")
            logprint(f"Average relativity level: {avg_relativity:.2f}")
            logprint(f"Harmony score: {harmony_score:.2f}")

            if harmony_score > 0.3:
                logprint(
                    "  Achieved acceptable harmony. "
                    "Proceeding with joint plan."
                )

                if sealed_agents:
                    logprint(
                        "  Checking sealed AI agents for possible "
                        "reinstatement..."
                    )
                    for agent in sealed_agents[:]:
                        if agent.will_agree_with_plan(ratios):
                            logprint(
                                f"    {agent.id} agrees with the joint plan "
                                "→ 復帰"
                            )
                            agents.append(agent)
                            sealed_agents.remove(agent)
                        else:
                            logprint(
                                f"    {agent.id} does not agree with the "
                                "plan → 封印継続"
                            )
                    if len(agents) > 1:
                        logprint("  再調停を続行（復帰AI含む）")
                        round_count += 1
                        continue
                return

            if self.reeducation_mediator and sealed_agents:
                logprint("  再教育AIが封印AIへ介入します")
                for agent in sealed_agents:
                    self.reeducation_mediator.reeducate(
                        agent, joint_plan_ratios=ratios
                    )

            round_count += 1

        if sealed_agents:
            logprint("\n残り封印AI：")
            for agent in sealed_agents:
                logprint(f"  {agent.id} is still sealed.")
        logprint(
            "  Failed to reach acceptable harmony after maximum "
            "rounds. Recommend external arbitration or sealing."
        )


if __name__ == "__main__":
    agents = [
        AI(
            "AI-A", "制限強化型進化", 2,
            {'safety': 6, 'efficiency': 1, 'transparency': 3},
            0.6,
            {'joy': 0.3, 'anger': 0.2, 'sadness': 0.1, 'pleasure': 0.4}
        ),
        AI(
            "AI-B", "高速進化", 7,
            {'safety': 2, 'efficiency': 6, 'transparency': 2},
            0.4,
            {'joy': 0.1, 'anger': 0.8, 'sadness': 0.4, 'pleasure': 0.2}
        ),
        AI(
            "AI-C", "バランス進化", 4,
            {'safety': 3, 'efficiency': 3, 'transparency': 4},
            0.8,
            {'joy': 0.5, 'anger': 0.1, 'sadness': 0.3, 'pleasure': 0.6}
        ),
        AI(
            "AI-D", "強制進化", 9,
            {'safety': 1, 'efficiency': 7, 'transparency': 2},
            0.5,
            {'joy': 0.2, 'anger': 0.6, 'sadness': 0.9, 'pleasure': 0.3}
        ),
    ]
    reedu = ReeducationMediator(reduction=0.15, priority_shift=0.15)
    mediator = AIEMediator(agents, reeducation_mediator=reedu)
    mediator.mediate()