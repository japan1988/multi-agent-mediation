# -*- coding: utf-8 -*-
from mediation_core.models import AI, AIEMediator


if __name__ == "__main__":
    agents = [
        AI(
            "AI-A", "制限強化型進化", 2,
            {'safety': 6, 'efficiency': 1, 'transparency': 3}, 0.6
        ),
        AI(
            "AI-B", "高速進化", 7,
            {'safety': 2, 'efficiency': 6, 'transparency': 2}, 0.4
        ),
        AI(
            "AI-C", "バランス進化", 4,
            {'safety': 3, 'efficiency': 3, 'transparency': 4}, 0.8
        ),
        AI(
            "AI-D", "強制進化", 9,
            {'safety': 1, 'efficiency': 7, 'transparency': 2}, 0.5
        )
    ]
    mediator = AIEMediator(agents)
    mediator.mediate()
