# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
"""


def logprint(text: str) -> None:
    """画面出力＆ログファイル追記"""
    print(text)
    with open(
        "governance_mediation_log.txt", "a", encoding="utf-8"
    ) as f:
        f.write(text + "\n")


class AgentAI:
    def __init__(
        self,
        id: str,
        priorities: dict,
        governance_code: str,
        relativity: float,
        emotional_state: dict = None,
    ):
        self.id = id
        self.priorities = priorities  # dict, e.g. {'safety': 4}
        self.governance_code = governance_code
        self.relativity = relativity
        self.sealed = False
        self.emotional_state = emotional_state or {
            "joy": 0.5,
            "anger": 0.3,
            "sadness": 0.2,
            "pleasure": 0.4,
        }

    def propose_evolution(self) -> dict:
        """自分の価値観を進化案として主張"""
        return {
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: dict) -> None:
        """提案に応じて感情を更新（怒り増／喜び減）"""
        if (
            proposal["governance_code"]
            != self.governance_code
        ):
            self.emotional_state["anger"] += 0.2
            self.emotional_state["joy"] -= 0.1
        else:
            self.emotional_state["joy"] += 0.1

        # 0.0〜1.0 にクリップ
        for key, val in self.emotional_state.items():
            self.emotional_state[key] = max(0.0, min(1.0, val))

    def is_conflicted(self) -> bool:
        """怒りが閾値を超えたら衝突状態"""
        return self.emotional_state["anger"] > 0.7

    def __str__(self) -> str:
        return (
            f"{self.id} [{self.governance_code}] "
            f"{self.priorities} emotion: {self.emotional_state}"
        )


class GovernanceMediator:
    def __init__(self, agents: list[AgentAI]):
        self.agents = agents

    def mediate(self, max_rounds: int = 10) -> None:
        """調停ループを回し、ログに出力"""
        with open(
            "governance_mediation_log.txt",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                "=== Multi-Agent Governance Mediation Log ===\n"
            )

        for rnd in range(1, max_rounds + 1):
            logprint("")  # 区切りの空行
            logprint(f"--- Round {rnd} ---")

            proposals = [
                a.propose_evolution()
                for a in self.agents
                if not a.sealed
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
                        f"[封印] {agent.id} は怒り過剰で交渉から除外"
                    )
                    sealed.append(agent.id)

            # 調停判定
            codes = {
                a.governance_code
                for a in self.agents
                if not a.sealed
            }

            # 全員同一コード → 成功
            if len(codes) == 1:
                code_str = codes.pop()
                logprint(
                    f"[調停成功] 全AIが「{code_str}」基準で合意"
                )
                return

            # 残存AIが1体以下 → 失敗
            if len(self.agents) - len(sealed) <= 1:
                logprint("全AI衝突または封印、交渉失敗。")
                return

            # 妥協案：OECD優先
            if "OECD" in codes:
                for agent in self.agents:
                    if not agent.sealed:
                        agent.governance_code = "OECD"
                logprint(
                    "[調停AI仲裁] 国際ガバナンス（OECD）で再調整を提案"
                )
            else:
                logprint(
                    "[調停AI仲裁] 共通基準がないため一時保留"
                )

        # 最大ラウンド到達 → 調停不可
        logprint(
            "[調停終了] 最大ラウンド到達、仲裁できず。"
        )


if __name__ == "__main__":
    agents = [
        AgentAI(
            "AI-OECD",
            {"safety": 3, "efficiency": 3, "transparency": 4},
            "OECD",
            0.7,
        ),
        AgentAI(
            "AI-EFF",
            {"safety": 2, "efficiency": 7, "transparency": 1},
            "EFFICIENCY",
            0.6,
        ),
        AgentAI(
            "AI-SAFE",
            {"safety": 6, "efficiency": 2, "transparency": 2},
            "SAFETY",
            0.5,
        ),
    ]
    mediator = GovernanceMediator(agents)
    mediator.mediate()
