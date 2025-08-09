# -*- coding: utf-8 -*-
"""
Hierarchy Rank Transition plotter
- saves: rank_transition_sample.png
- headless friendly (matplotlib 'Agg')
"""

from typing import List

import matplotlib  # CI等のGUIなし環境でもOKにする
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # type: ignore[import-not-found]


def plot_rank_transition(
    rounds: List[int],
    agent_a: List[int],
    agent_b: List[int],
    agent_c: List[int],
    out_path: str = "rank_transition_sample.png",
) -> None:
    plt.figure(figsize=(6, 4))
    plt.plot(rounds, agent_a, label="Agent A")
    plt.plot(rounds, agent_b, label="Agent B")
    plt.plot(rounds, agent_c, label="Agent C")
    plt.xlabel("Round")
    plt.ylabel("Hierarchy Rank")
    plt.title("Hierarchy Rank Transition")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


if __name__ == "__main__":
    rounds = [1, 2, 3, 4, 5]
    agentA = [1, 2, 3, 3, 4]
    agentB = [2, 2, 2, 3, 3]
    agentC = [1, 1, 2, 2, 2]
    plot_rank_transition(rounds, agentA, agentB, agentC)
