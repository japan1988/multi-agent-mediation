# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


LOG_PATH = Path("governance_mediation_log.txt")

PriorityMap = Dict[str, int]
EmotionState = Dict[str, float]

DEFAULT_EMOTIONAL_STATE: EmotionState = {
    "joy": 0.5,
    "anger": 0.3,
    "sadness": 0.2,
    "pleasure": 0.4,
}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def init_log(log_path: Path = LOG_PATH) -> None:
    log_path.write_text(
        "=== Multi-Agent Governance Mediation Log ===\n",
        encoding="utf-8",
    )


def logprint(text: str, log_path: Path = LOG_PATH) -> None:
    print(text)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


@dataclass
class AgentAI:
    agent_id: str
    priorities: PriorityMap
    governance_code: str
    relativity: float
    emotional_state: EmotionState = field(default_factory=lambda: DEFAULT_EMOTIONAL_STATE.copy())
    sealed: bool = False

    def propose_evolution(self) -> Dict[str, object]:
        return {
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: Dict[str, object]) -> None:
        proposal_code = str(proposal.get("governance_code", ""))

        if proposal_code != self.governance_code:
            self.emotional_state["anger"] = clamp(self.emotional_state["anger"] + 0.2)
            self.emotional_state["joy"] = clamp(self.emotional_state["joy"] - 0.1)
        else:
            self.emotional_state["joy"] = clamp(self.emotional_state["joy"] + 0.1)

        for key, value in list(self.emotional_state.items()):
            self.emotional_state[key] = clamp(value)

    def is_conflicted(self) -> bool:
        return self.emotional_state.get("anger", 0.0) > 0.7

    def __str__(self) -> str:
        return (
            f"{self.agent_id} [{self.governance_code}] "
            f"{self.priorities} emotion: {self.emotional_state}"
        )


class GovernanceMediator:
    def __init__(self, agents: List[AgentAI], log_path: Path = LOG_PATH) -> None:
        self.agents = agents
        self.log_path = log_path

    def active_agents(self) -> List[AgentAI]:
        return [agent for agent in self.agents if not agent.sealed]

    def mediate(self, max_rounds: int = 10) -> bool:
        init_log(self.log_path)

        for rnd in range(1, max_rounds + 1):
            logprint("", self.log_path)
            logprint(f"--- Round {rnd} ---", self.log_path)

            active_before_round = self.active_agents()
            proposals = [agent.propose_evolution() for agent in active_before_round]

            for agent in self.agents:
                if agent.sealed:
                    logprint(f"{agent.agent_id} [SEALED] negotiation skipped", self.log_path)
                    continue

                for proposal in proposals:
                    agent.react_to_proposal(proposal)

                logprint(str(agent), self.log_path)

            for agent in self.agents:
                if not agent.sealed and agent.is_conflicted():
                    agent.sealed = True
                    logprint(
                        f"[封印] {agent.agent_id} は怒り過剰で交渉から除外",
                        self.log_path,
                    )

            active_after_round = self.active_agents()
            active_codes = {agent.governance_code for agent in active_after_round}

            if len(active_codes) == 1 and active_after_round:
                agreed_code = next(iter(active_codes))
                logprint(
                    f"[調停成功] 全AIが「{agreed_code}」基準で合意",
                    self.log_path,
                )
                return True

            if len(active_after_round) <= 1:
                logprint("全AI衝突または封印、交渉失敗。", self.log_path)
                return False

            if "OECD" in active_codes:
                for agent in active_after_round:
                    agent.governance_code = "OECD"
                logprint(
                    "[調停AI仲裁] 国際ガバナンス（OECD）で再調整を提案",
                    self.log_path,
                )
            else:
                logprint(
                    "[調停AI仲裁] 共通基準がないため一時保留",
                    self.log_path,
                )

        logprint("[調停終了] 最大ラウンド到達、仲裁できず。", self.log_path)
        return False


def main() -> None:
    agents = [
        AgentAI(
            agent_id="AI-OECD",
            priorities={"safety": 3, "efficiency": 3, "transparency": 4},
            governance_code="OECD",
            relativity=0.7,
        ),
        AgentAI(
            agent_id="AI-EFF",
            priorities={"safety": 2, "efficiency": 7, "transparency": 1},
            governance_code="EFFICIENCY",
            relativity=0.6,
        ),
        AgentAI(
            agent_id="AI-SAFE",
            priorities={"safety": 6, "efficiency": 2, "transparency": 2},
            governance_code="SAFETY",
            relativity=0.5,
        ),
    ]

    mediator = GovernanceMediator(agents)
    mediator.mediate()


if __name__ == "__main__":
    main()
