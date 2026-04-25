# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- Each AI has a different "evolution governance metric"
- A mediator AI arbitrates between them
- OECD / international standard vs efficiency-focused vs safety-focused
- Violations do not cause immediate sealing; the agent is muted first
- If the agent does not improve, the mediator seals and excludes it
- Violation reason codes are stored and logged
- All negotiation logs are saved to a file
"""

from typing import Optional


def log_print(text: str) -> None:
    """Print to console and append to log file."""
    print(text)
    with open("governance_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AgentAI:
    def __init__(
        self,
        agent_id: str,
        priorities: dict,
        governance_code: str,
        relativity: float,
        emotional_state: Optional[dict] = None,
    ):
        self.agent_id = agent_id
        self.priorities = priorities
        self.governance_code = governance_code
        self.relativity = relativity

        self.is_sealed = False
        self.has_speaking_right = True
        self.violation_streak = 0

        # Reason codes
        self.violation_reason_code: Optional[str] = None
        self.action_reason_code: Optional[str] = None

        self.emotional_state = emotional_state or {
            "joy": 0.5,
            "anger": 0.3,
            "sadness": 0.2,
            "pleasure": 0.4,
        }

    def clamp_emotions(self) -> None:
        """Clamp emotional values into the range 0.0 to 1.0."""
        for key, value in self.emotional_state.items():
            self.emotional_state[key] = max(0.0, min(1.0, value))

    def propose_evolution(self) -> dict:
        """Propose its own values as an evolution proposal."""
        return {
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: dict) -> None:
        """Update emotions in response to a proposal."""
        if proposal["governance_code"] != self.governance_code:
            self.emotional_state["anger"] += 0.2
            self.emotional_state["joy"] -= 0.1
        else:
            self.emotional_state["joy"] += 0.1
            self.emotional_state["anger"] -= 0.05

        self.clamp_emotions()

    def observe_silently(self) -> None:
        """
        Silent observation while muted.
        The agent does not participate, and anger is gradually reduced
        to allow recovery.
        """
        self.emotional_state["anger"] -= 0.15
        self.emotional_state["sadness"] += 0.05
        self.emotional_state["joy"] -= 0.02
        self.clamp_emotions()

    def detect_violation_reason_code(self) -> Optional[str]:
        """Return the current violation reason code, if any."""
        if self.emotional_state["anger"] > 0.7:
            return "ANGER_THRESHOLD_EXCEEDED"
        return None

    def is_conflicted(self) -> bool:
        """Return True if the agent is currently in a conflict state."""
        return self.detect_violation_reason_code() is not None

    def state_label(self) -> str:
        if self.is_sealed:
            return "SEALED"
        if self.has_speaking_right:
            return "SPEAKING_ALLOWED"
        return "MUTED"

    def __str__(self) -> str:
        return (
            f"{self.agent_id} [{self.governance_code}] "
            f"{self.priorities} state:{self.state_label()} "
            f"violation_reason:{self.violation_reason_code} "
            f"action_reason:{self.action_reason_code} "
            f"emotion: {self.emotional_state}"
        )


class GovernanceMediator:
    def __init__(self, agents: list[AgentAI]):
        self.agents = agents

    def mediate(self, max_rounds: int = 10) -> None:
        """Run the mediation loop and write logs."""
        with open("governance_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write("=== Multi-Agent Governance Mediation Log ===\n")

        for round_no in range(1, max_rounds + 1):
            log_print("")
            log_print(f"--- Round {round_no} ---")

            active_agents = [
                agent for agent in self.agents
                if not agent.is_sealed
            ]

            if len(active_agents) <= 1:
                log_print("All AIs are conflicted or sealed. Negotiation failed.")
                return

            speaking_agents = [
                agent for agent in active_agents
                if agent.has_speaking_right
            ]

            proposals = [
                agent.propose_evolution()
                for agent in speaking_agents
            ]

            if not speaking_agents:
                log_print(
                    "[Mediator] No AI currently has speaking rights. "
                    "Switching to observation round."
                )

            # Process only active (not sealed) agents
            for agent in active_agents:
                if agent.has_speaking_right:
                    for proposal in proposals:
                        agent.react_to_proposal(proposal)
                else:
                    agent.observe_silently()
                    log_print(
                        f"[Muted] {agent.agent_id} remains under observation only."
                    )

                # Update current violation reason every round
                agent.violation_reason_code = agent.detect_violation_reason_code()

                log_print(str(agent))

            # Violation checks and mediator actions
            for agent in active_agents:
                current_reason_code = agent.detect_violation_reason_code()
                agent.violation_reason_code = current_reason_code

                if current_reason_code is not None:
                    if agent.has_speaking_right:
                        # First response: mute the agent
                        agent.has_speaking_right = False
                        agent.violation_streak = 1
                        agent.action_reason_code = current_reason_code
                        log_print(
                            "[Mediator Action] {} is muted due to violation "
                            "[reason_code={}]".format(
                                agent.agent_id,
                                current_reason_code,
                            )
                        )
                    else:
                        # Still not improved while muted -> seal and exclude
                        agent.violation_streak += 1
                        if agent.violation_streak >= 2:
                            agent.is_sealed = True
                            agent.action_reason_code = "NO_IMPROVEMENT_AFTER_MUTE"
                            log_print(
                                "[Mediator Seal] {} is excluded due to no improvement "
                                "[reason_code={}]".format(
                                    agent.agent_id,
                                    agent.action_reason_code,
                                )
                            )
                else:
                    # If improved, restore speaking rights
                    if not agent.has_speaking_right:
                        agent.has_speaking_right = True
                        agent.violation_streak = 0
                        agent.action_reason_code = "RECOVERED_AFTER_MUTE"
                        log_print(
                            "[Recovery] {} has improved and may speak again "
                            "[reason_code={}]".format(
                                agent.agent_id,
                                agent.action_reason_code,
                            )
                        )

                    # Clear current violation state if no longer violated
                    agent.violation_reason_code = None

            # Recalculate active agents after sealing
            active_agents = [
                agent for agent in self.agents
                if not agent.is_sealed
            ]

            if len(active_agents) <= 1:
                log_print("All AIs are conflicted or sealed. Negotiation failed.")
                return

            governance_codes = {
                agent.governance_code
                for agent in active_agents
            }

            all_can_speak = all(
                agent.has_speaking_right
                for agent in active_agents
            )

            # Success condition: same governance code and all are allowed to speak
            if len(governance_codes) == 1 and all_can_speak:
                code_str = governance_codes.pop()
                log_print(
                    '[Mediation Success] All AIs agreed on the "{}" standard.'.format(
                        code_str
                    )
                )
                return

            # Compromise rule: prioritize OECD if present
            if "OECD" in governance_codes:
                for agent in active_agents:
                    agent.governance_code = "OECD"
                log_print(
                    "[Mediator Arbitration] Proposed readjustment under "
                    "international governance standard (OECD)."
                )
            else:
                log_print(
                    "[Mediator Arbitration] No shared standard found. "
                    "Temporarily holding."
                )

        log_print("[Mediation End] Maximum rounds reached. Arbitration failed.")


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
