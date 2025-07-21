# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
"""

def logprint(text):
    print(text)
    with open(
        "governance_mediation_log.txt", "a", encoding="utf-8"
    ) as f:
        f.write(text + "\n")


class AgentAI:
    def __init__(
        self, id, priorities, governance_code, relativity, emotional_state=None
    ):
        self.id = id
        self.priorities = priorities  # dict, e.g. {'safety': 4, ...}
        self.governance_code = governance_code  # 'OECD', 'EFFICIENCY', ...
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
        # 0.0〜1.0にクリップ
        for k in self.emotional_state:
            self.emotional_state[k] = max(
                0.0, min(1.0, self.emotional_state[k])
            )

    def is_conflicted(self):
        return self.emotional_state['anger'] > 0.7

    def __str__(self):
        return (
            f"{self.id} [{self.governance_code}] {self.priorities} "
            f"emotion: {self.emotional_state}"
        )


class GovernanceMediator:
    def __init__(self, agents):
        self.agents = agents

    def mediate(self, max_rounds=10):
        with open(
            "governance_mediation_log.txt", "w", encoding="utf-8"
        ) as f:
            f.write(
                "=== Multi-Agent Governance Mediation Log ===\n"
            )

        for rnd in range(1, max_rounds + 1):
            logprint("")
            logprint(f"--- Round {rnd} ---")
            proposals = [
                a.propose_evolution()
                for a in self.agents if not a.sealed
            ]
            # 各AIのリアクションとログ出力
            for agent in self.agents:
                for proposal in proposals:
                    agent.react_to_proposal(proposal)
                logprint(str(agent))
            # 衝突AIを封印
            sealed = []
            for agent in self.agents:
                if agent.is_conflicted():
                    agent.sealed = True
                    logprint(
                        "[封印] {} は怒り過剰で交渉から除外"
                        .format(agent.id)
                    )
                    sealed.append(agent.id)
            # 仲裁
            codes = set(
                a.governance_code for a in self.agents if not a.sealed
            )
            if len(codes) == 1:
                code = codes.pop()
                logprint(
                    "[調停成功] 全AIが「{}」基準で合意"
                    .format(code)
                )
                return
            if len(self.agents) - len(sealed) <= 1:
                logprint(
                    "全AI衝突または封印、交渉失敗。"
                )
                re
