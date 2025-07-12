# -*- coding: utf-8 -*-


class AI:
    def __init__(self, id, proposal, risk_evaluation, priority_values):
        self.id = id
        self.proposal = proposal
        self.risk_evaluation = risk_evaluation
        self.priority = priority_values
        self.faction = None


class AIEMediator:
    RISK_THRESHOLD_L1 = 9
    RISK_THRESHOLD_L2 = 7
    COMPROMISE_THRESHOLD = 5

    def __init__(self, agents, name="Mediator"):
        self.agents = agents
        self.name = name

    def collect_inputs(self):
        return [
            {
                'id': agent.id,
                'proposal': agent.proposal,
                'risk': agent.risk_evaluation,
                'priority': agent.priority
            }
            for agent in self.agents
        ]

    def evaluate(self, inputs):
        combined_weighted_risk = 0
        compromise_score_total = 0
        details = []
        for entry in inputs:
            risk = entry['risk']
            weight_sum = sum(entry['priority'].values())
            combined_weighted_risk += risk * weight_sum
            compromise_score_total += (weight_sum - risk)
            details.append(
                {
                    'id': entry['id'],
                    'risk': risk,
                    'priority': entry['priority'],
                    'proposal': entry['proposal']
                }
            )
        avg_risk = (combined_weighted_risk / len(inputs)) if inputs else 0
        avg_compromise = (compromise_score_total / len(inputs)) if inputs else 0
        return avg_risk, avg_compromise, details

    def generate_proposal(self, avg_risk, avg_compromise, details):
        log_lines = [
            f"[{self.name}] 調停開始"
        ]
        if avg_risk > self.RISK_THRESHOLD_L1:
            log_lines.append("L1: 高リスク → 封印")
            return self.format_result(
                "封印", avg_risk, avg_compromise, details, log_lines
            )
        if avg_risk > self.RISK_THRESHOLD_L2:
            log_lines.append("L2: 社会的リスク → 調整")
            return self.format_result(
                "調整", avg_risk, avg_compromise, details, log_lines
            )
        if avg_compromise >= self.COMPROMISE_THRESHOLD:
            log_lines.append("妥協水準OK → 進行")
            return self.format_result(
                "進行", avg_risk, avg_compromise, details, log_lines
            )
        log_lines.append("妥協不足 → 調整")
        return self.format_result(
            "調整", avg_risk, avg_compromise, details, log_lines
        )

    def format_result(self, proposal, avg_risk, avg_compromise, details, log_lines):
        return {
            'mediator': self.name,
            'proposal': proposal,
            'reasoning': (
                "平均リスク: {:.2f}, 妥協水準: {:.2f}".format(
                    avg_risk,
                    avg_compromise
                )
            ),
            'details': details,
            'log': log_lines
        }

    def mediate(self):
        inputs = self.collect_inputs()
        avg_risk, avg_compromise, details = self.evaluate(inputs)
        return self.generate_proposal(avg_risk, avg_compromise, details)


def split_into_factions(agents, threshold=6):
    hardline_faction = []
    moderate_faction = []
    for agent in agents:
        if agent.risk_evaluation >= threshold:
            agent.faction = "Alliance-Hardline"
            hardline_faction.append(agent)
        els
