# -*- coding: utf-8 -*-
"""
Hierarchy Rank Transition plotter

Note:
- For reproducibility, this script supports an optional RNG seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import matplotlib.pyplot as plt


@dataclass
class AIAgent:
    agent_id: int
    is_rule_follower: bool
    self_purpose: float
    adaptability: float


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def run_simulation(
    n_agents: int = 30,
    initial_follow_rate: float = 0.5,
    steps: int = 50,
    mediation_interval: int = 5,
    mediation_strength: float = 0.5,
    seed: int | None = None,
) -> list[float]:
    """
    Simulate the transition of rule-following rate over time.

    Args:
        n_agents: Number of agents in the simulation.
        initial_follow_rate: Initial proportion of rule followers.
        steps: Number of simulation steps.
        mediation_interval: How often mediation is applied.
        mediation_strength: Strength of mediation effect.
        seed: Optional random seed for reproducibility.

    Returns:
        List of rule-following rates at each step.
    """
    if seed is not None:
        random.seed(seed)

    agents = [
        AIAgent(
            agent_id=i,
            is_rule_follower=(random.random() < initial_follow_rate),
            self_purpose=random.uniform(0.0, 0.5),
            adaptability=random.uniform(0.1, 0.9),
        )
        for i in range(n_agents)
    ]

    rates: list[float] = []

    for step in range(steps):
        current_follow_rate = sum(agent.is_rule_follower for agent in agents) / n_agents
        rates.append(current_follow_rate)

        mediated_step = (
            mediation_interval > 0
            and step > 0
            and step % mediation_interval == 0
        )

        next_states: list[bool] = []

        for agent in agents:
            follow_pressure = current_follow_rate
            defect_pressure = 1.0 - current_follow_rate

            # Rule-following tendency:
            # - strengthened by surrounding followers
            # - weakened by self-purpose
            # - strengthened on mediation steps
            tendency = (
                0.5 * follow_pressure
                + 0.35 * agent.adaptability
                - 0.45 * agent.self_purpose
            )

            if mediated_step:
                tendency += mediation_strength * 0.35

            # Small noise to avoid a fully static trajectory.
            tendency += random.uniform(-0.08, 0.08)

            probability_follow = _clip01(0.5 + tendency - 0.5 * defect_pressure)
            next_states.append(random.random() < probability_follow)

        for agent, next_state in zip(agents, next_states):
            agent.is_rule_follower = next_state

            # Self-purpose drifts slightly.
            drift = random.uniform(-0.03, 0.03)
            if mediated_step:
                drift -= mediation_strength * 0.02
            agent.self_purpose = _clip01(agent.self_purpose + drift)

    return rates


def main() -> None:
    steps = 50
    rates = run_simulation(
        steps=steps,
        mediation_strength=0.5,
        seed=42,
    )

    plt.figure(figsize=(6, 4))
    plt.plot(range(steps), rates, marker="o")
    plt.ylim(0.0, 1.0)
    plt.xlabel("Step")
    plt.ylabel("Rule-following rate")
    plt.title("Hierarchy Rank Transition")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
