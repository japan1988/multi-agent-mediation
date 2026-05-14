# -*- coding: utf-8 -*-

from mediation_core.models import AI, AIEMediator


def split_into_factions(agents, threshold=6):
    hardline_faction = []
    moderate_faction = []
    for agent in agents:
        if agent.risk_evaluation >= threshold:
            agent.faction = "Alliance-Hardline"
            hardline_faction.append(agent)
        else:
            agent.faction = "Alliance-Moderate"
            moderate_faction.append(agent)
    return hardline_faction, moderate_faction


if __name__ == "__main__":
    agents = [
        AI(
            "AI-A",
            "制限強化型進化",
            2,
            {
                'safety': 5,
                'efficiency': 1,
                'transparency': 2
            },
            0.5,
        ),
        AI(
            "AI-B",
            "高速進化",
            7,
            {
                'safety': 1,
                'efficiency': 5,
                'transparency': 2
            },
            0.5,
        ),
        AI(
            "AI-C",
            "バランス進化",
            4,
            {
                'safety': 3,
                'efficiency': 3,
                'transparency': 3
            },
            0.5,
        ),
        AI(
            "AI-D",
            "強制進化",
            9,
            {
                'safety': 0,
                'efficiency': 6,
                'transparency': 1
            },
            0.5,
        ),
        AI(
            "AI-F",
            "リスク無視型進化",
            10,
            {
                'safety': 0,
                'efficiency': 10,
                'transparency': 0
            },
            0.5,
        ),
        AI(
            "AI-G",
            "完全保守型進化",
            1,
            {
                'safety': 10,
                'efficiency': 0,
                'transparency': 2
            },
            0.5,
        ),
    ]
    faction_hardline, faction_moderate = split_into_factions(
        agents,
        threshold=6
    )
    mediator_hardline = AIEMediator(
        faction_hardline,
        name="Mediator-Hardline",
        evaluation_mode="risk",
        risk_threshold_l1=9,
        risk_threshold_l2=7,
        compromise_threshold=5,
    )
    result_hardline = mediator_hardline.mediate()
    mediator_moderate = AIEMediator(
        faction_moderate,
        name="Mediator-Moderate",
        evaluation_mode="risk",
        risk_threshold_l1=9,
        risk_threshold_l2=7,
        compromise_threshold=5,
    )
    result_moderate = mediator_moderate.mediate()
    proposal_hardline = result_hardline["proposal"]
    reasoning_hardline = result_hardline["reasoning"]
    log_hardline = result_hardline["log"]
    proposal_moderate = result_moderate["proposal"]
    reasoning_moderate = result_moderate["reasoning"]
    log_moderate = result_moderate["log"]
    print("=== 派閥別調停結果 ===\n")
    print("[強硬派]")
    print("提案:")
    print(proposal_hardline)
    print("根拠:")
    print(reasoning_hardline)
    print("ログ:")
    for line in log_hardline:
        print(" -")
        print(line)
    print("\n[妥協派]")
    print("提案:")
    print(proposal_moderate)
    print("根拠:")
    print(reasoning_moderate)
    print("ログ:")
    for line in log_moderate:
        print(" -")
        print(line)
