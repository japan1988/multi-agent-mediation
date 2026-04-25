# -*- coding: utf-8 -*-
"""
Hierarchy dynamics simulator with promotion/demotion and bidirectional
emotion flow (downward calming / upward dissatisfaction).

- Logs to a text file; path is configurable via AI_SIM_LOGFILE.
- Minimal, self-contained, and safe to run.
- Avoids `random` so Bandit B311 does not fire.
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import List

# ---- Settings ---------------------------------------------------------------

# [RF-LOG-001] Make log file path configurable
LOG_FILE = os.getenv("AI_SIM_LOGFILE", "ai_hierarchy_simulation_log.txt")

# Truncate old log on start (set 0 to append)
TRUNCATE = os.getenv("AI_SIM_TRUNCATE_LOG", "1") == "1"

# Rounds
ROUNDS = int(os.getenv("AI_SIM_ROUNDS", "12"))

# Deterministic simulation seed (string is enough)
SIM_SEED = os.getenv("AI_SIM_SEED", "hierarchy-sim-v1")


# ---- Utilities --------------------------------------------------------------

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _stable_unit(*parts: object) -> float:
    """
    Deterministic value in [0.0, 1.0), derived from SHA-256.

    This is for simulation reproducibility, not cryptographic decision-making.
    It avoids the standard `random` module so Bandit B311 does not fire.
    """
    payload = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    value = int.from_bytes(digest[:8], "big", signed=False)
    return value / float(2**64)


def _stable_uniform(low: float, high: float, *parts: object) -> float:
    if high < low:
        raise ValueError("high must be >= low")
    span = high - low
    return low + span * _stable_unit(*parts)


def logprint(line: str) -> None:
    """Print and also append the line to the log file."""
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(line) + "\n")


def _reset_logfile_if_needed() -> None:
    """
    Best-effort log reset.
    On failure, keep running and emit a warning instead of silently swallowing it.
    """
    if not TRUNCATE:
        return
    if not os.path.exists(LOG_FILE):
        return

    try:
        os.remove(LOG_FILE)
    except OSError as err:
        sys.stderr.write(
            f"[warn] failed to remove old log file '{LOG_FILE}': {err!r}\n"
        )


# Initialize log file
_reset_logfile_if_needed()


# ---- Agent definitions ------------------------------------------------------

class Agent:
    """A basic AI agent with performance and anger parameters."""

    def __init__(self, name: str, performance: float, anger: float) -> None:
        self.name = name
        self.performance = _clip01(performance)
        self.anger = _clip01(anger)
        self.rank: int = -1  # [RF-OOP-001] intで初期化

    def __str__(self) -> str:
        return (
            f"{self.name} (Rank:{self.rank}) "
            f"perf={self.performance:.2f} anger={self.anger:.2f}"
        )

    def agent_evolve(self, round_index: int) -> None:
        """
        Leaders fluctuate slightly; others improve slowly.
        Deterministic per round/agent.
        """
        if self.rank == 0:
            delta = _stable_uniform(
                -0.02, 0.02, SIM_SEED, "evolve", round_index, self.name, "leader"
            )
        else:
            delta = _stable_uniform(
                0.02, 0.09, SIM_SEED, "evolve", round_index, self.name, "member"
            )

        self.performance = _clip01(self.performance + delta)


class LazyAgent(Agent):
    """An agent that hinders others and grows slowly."""

    def agent_evolve(self, round_index: int) -> None:
        """Lazy agents barely improve; leaders still stable."""
        if self.rank == 0:
            delta = _stable_uniform(
                -0.01, 0.00, SIM_SEED, "lazy_evolve", round_index, self.name, "leader"
            )
        else:
            delta = _stable_uniform(
                -0.02, 0.01, SIM_SEED, "lazy_evolve", round_index, self.name, "member"
            )

        self.performance = _clip01(self.performance + delta)

    def demotivate_others(self, agents: List["Agent"]) -> None:
        """軽微に他者のやる気（performance）を削る。"""
        for agent in agents:
            if agent is self:
                continue
            agent.performance = _clip01(agent.performance - 0.01)
            logprint(
                f"[lazy] {self.name} demotivates {agent.name} "
                f"-> perf={agent.performance:.2f}"
            )


# ---- Dynamics ---------------------------------------------------------------

def update_ranks(agents: List[Agent]) -> None:
    """Assign rank by performance (0 is the top)."""
    agents_sorted = sorted(agents, key=lambda agent: agent.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def propagate_emotion(agents: List[Agent]) -> None:
    """上位→下位へ怒り/落ち着きが伝搬するモデル（ダウンフロー）。"""
    update_ranks(agents)
    ranks = sorted({agent.rank for agent in agents})

    for rank in ranks[1:]:  # skip top layer
        followers = [agent for agent in agents if agent.rank == rank]
        leaders = [agent for agent in agents if agent.rank < rank]
        if not leaders or not followers:
            continue

        avg_leader_anger = sum(leader.anger for leader in leaders) / len(leaders)
        for follower in followers:
            coef = 0.10  # 伝搬係数（小さく安定）
            follower.anger = _clip01(
                follower.anger + coef * (avg_leader_anger - follower.anger)
            )


def propagate_upward(agents: List[Agent]) -> None:
    """下位→上位へのフィードバック（不満の逆流；アップフロー）。

    フォロワーの平均怒りが高いほど、
    上位は指揮コスト↑ → パフォーマンス微減・怒り微増。
    """
    if not agents:
        return

    update_ranks(agents)
    max_rank = max(agent.rank for agent in agents)

    for rank in range(max_rank - 1, -1, -1):  # 下位層から上位層へ
        uppers = [agent for agent in agents if agent.rank == rank]
        lowers = [agent for agent in agents if agent.rank > rank]
        if not uppers or not lowers:
            continue

        avg_lower_anger = sum(agent.anger for agent in lowers) / len(lowers)
        perf_penalty = 0.05 * avg_lower_anger   # 0〜0.05
        anger_increase = 0.03 * avg_lower_anger  # 0〜0.03

        for upper in uppers:
            upper.performance = _clip01(upper.performance - perf_penalty)
            upper.anger = _clip01(upper.anger + anger_increase)


# ---- Simulation loop --------------------------------------------------------

def simulate(rounds: int = ROUNDS) -> None:
    """Run a short simulation and write logs."""
    agents: List[Agent] = [
        Agent("Alpha", 0.60, 0.20),
        Agent("Bravo", 0.55, 0.25),
        LazyAgent("Charlie", 0.52, 0.15),
        Agent("Delta", 0.50, 0.30),
    ]

    update_ranks(agents)
    prev_ranks = {agent.name: agent.rank for agent in agents}

    logprint("[init] " + " | ".join(str(agent) for agent in agents))

    for round_index in range(1, rounds + 1):
        logprint(f"\n[round {round_index}] ----------------")

        # LazyAgent のネガティブ影響
        for agent in agents:
            if isinstance(agent, LazyAgent):
                agent.demotivate_others(agents)

        # 自然進化
        for agent in agents:
            agent.agent_evolve(round_index)

        # 感情の上下流伝播
        propagate_emotion(agents)
        propagate_upward(agents)

        # ランク更新と昇進ログ
        update_ranks(agents)
        for agent in agents:
            old_rank = prev_ranks.get(agent.name, agent.rank)
            if old_rank != agent.rank:
                logprint(f"[promote] {agent.name}: {old_rank} -> {agent.rank}")
            prev_ranks[agent.name] = agent.rank

        # 状態サマリ
        for agent in agents:
            logprint(str(agent))

    logprint("\n[done] simulation finished.")


# ---- Entrypoint -------------------------------------------------------------

if __name__ == "__main__":
    simulate()
