# -*- coding: utf-8 -*-
"""
Multi-Agent Mediation Simulator with Reeducation
Author: Your Name
Description:
  - 合意形成・再教育・封印・復帰まで実装
  - ログ出力/ファイル保存（PEP8対応）
"""

from mediation_core.models import AI, AIEMediator, logprint


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
    mediator = AIEMediator(
        agents,
        max_rounds=30,
        reeducation_mediator=reedu,
        enable_emotional_moderation=True,
        log_header="=== Multi-Agent Mediation Log (with Reeducation) ===",
    )
    mediator.mediate()
