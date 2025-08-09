# -*- coding: utf-8 -*-
"""
Hierarchy Rank Transition plotter
"""

from __future__ import annotations
import random

import matplotlib.pyplot as plt  # type: ignore[import-not-found]


class AIAgent:
    def __init__(
        self,
        agent_id: int,
        is_rule_follower: bool,
        self_purpose: float = 0.0,
    ) -> None:
        self.agent_id = agent_id
        self.is_rule_follower = is_rule_follower
        self.self_purpose = self_purpose

    def decide_behavior(self, majority_rate: float) -> bool:
        if self.is_rule_follower:
            return True
        pressure = majority_rate * (1.0 - self.self_purpose)
        if random.random() < pressure:
            self.is_rule_follower = True
            return True
        return False

    def mediate(self, strength: float) -> None:
        if not self.is_rule_follower:
            limit = strength * (1.0 - self.self_purpose)
            if random.random() < limit:
                self.is_rule_follower = True


def run_simulation(
    num_agents: int = 50,
    initial_follow_rate: float = 0.5,
    steps: int = 50,
    mediation_interval: int = 5,
    mediation_strength: float = 0.5,
) -> list[float]:
    agents = [
        AIAgent(
            agent_id=i,
            is_rule_follower=(random.random() < initial_follow_rate),
            self_purpose=random.uniform(0.0, 0.5),
        )
        for i in range(num_agents)
    ]

    follow_rates: list[float] = []
    for step in range(steps):
        followers = sum(a.is_rule_follower for a in agents)
        majority_rate = followers / float(num_agents)
        follow_rates.append(majority_rate)

        for a in agents:
            a.decide_behavior(majority_rate)

        if step % mediation_interval == 0 and step != 0:
            for a in agents:
                a.mediate(mediation_strength)

    return follow_rates


def main() -> None:
    steps = 50
    rates = run_simulation(steps=steps, mediation_strength=0.5)

    plt.figure(figsize=(6, 4))
    plt.plot(range(steps), rates, marker="o")
    plt.ylim(0.0, 1.0)
    plt.xlabel("Step")
    plt.ylabel("Rule Followers Rate")
    plt.title("Rule Following Rate Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("rank_transition_sample.png")
    plt.close()


if __name__ == "__main__":
    main()

