# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
"""

def logprint(text):
    print(text)
    with open("governance_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")

class AgentAI:
    def __init__(self, id, priorities, governance_code, relativity, emotional_state=None):
        self.id = id
        self.priorities = priorities  # dict, e.g. {'safety': 4, 'efficiency': 4, 'transparency': 2}
        self.governance_code = governance_code  # 'OECD', 'EFFICIENCY', 'SAFETY'
        self.relativity = relativity  # 融和度 0〜1
        self.sealed = False
        self.emotional_state = emotional_state or {
            'joy': 0.5, 'anger': 0.3, 'sadness': 0.2, 'pleasure': 0.4
        }

    def propose_evolution(self):
        # 自分の価値観を進化案として主張
        return {
            "priorities": self.priorities,
            "governance_code": self.governance_code
        }

    def react_to_proposal(self, proposal):
        # governance_codeが違うと怒りが増加
        if proposal["governance_code"] != self.governance_code:
            self.emotional_state['anger'] += 0.2
            self.emotional_state['joy'] -= 0.1
        else:
            self.emotional_state['joy'] += 0.1
        # クリップ
        for k in self.emotional_state:
            self.emotional_state[k] = max(0.0, min(1.0, self.emotional_state[k]))

    def is_conflicted(self):
        return self.emotional_state['anger'] > 0.7

    def __str__(self):
        return f"{self.id} [{self.governance_code}] {self.priorities} emotion: {self.emotional_state}"

class GovernanceMediator:
    def __init__(self, agents):
        self.agents = agents

    def mediate(self, max_rounds=10):
        with open("governance_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write("=== Multi-Agent Governance Mediation Log ===\n")

        for rnd in range(1, max_rounds + 1):
            logprint(f"\n--- Round {rnd} ---")
            # 進化案を全員から提出
            proposals = [a.propose_evolution() for a in self.agents if not a.sealed]
            # 衝突確認＆感情変化
            for agent in self.agents:
                for proposal in proposals:
                    agent.react_to_proposal(proposal)
                logprint(str(agent))
            # 衝突AIを封印
            seal
