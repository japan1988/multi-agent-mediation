
---
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Python Application CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)
# -*- coding: utf-8 -*-
"""
Hierarchy Rank Transition plotter
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

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


def save_plot(path: Path, rates: list[float], steps: int, with_legend: bool = False) -> None:
    plt.figure(figsize=(6, 4))
    plt.plot(range(steps), rates, marker="o", label="Follower Rate" if with_legend else None)
    plt.ylim(0.0, 1.0)
    plt.xlabel("Step")
    plt.ylabel("Rule Followers Rate")
    plt.title("Rule Following Rate Over Time")
    plt.grid(True)
    if with_legend:
        plt.legend()
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path.as_posix())
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--mediation-strength", type=float, default=0.5)
    parser.add_argument(
        "--save-readme-img",
        action="store_true",
        help="Also save docs/images/simulation_example.png for README",
    )
    args = parser.parse_args()

    rates = run_simulation(steps=args.steps, mediation_strength=args.mediation_strength)

    # 既存の出力（従来のPNG）
    save_plot(Path("rank_transition_sample.png"), rates, args.steps, with_legend=False)

    # README用の画像（必要なときだけ）
    if args.save_readme_img:
        save_plot(Path("docs/images/simulation_example.png"), rates, args.steps, with_legend=True)


if __name__ == "__main__":
    main()
