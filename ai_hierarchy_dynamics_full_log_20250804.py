# -*- coding: utf-8 -*-
"""
Hierarchy dynamics simulator with promotion/demotion and bidirectional
emotion flow (downward calming / upward dissatisfaction).
- Logs to a text file; path is configurable via AI_SIM_LOGFILE.
- Minimal, self-contained, and safe to run.
"""
from __future__ import annotations

import os
import random
from typing import List

# ---- Settings ---------------------------------------------------------------
# [RF-LOG-001] Make log file path configurable
LOG_FILE = os.getenv("AI_SIM_LOGFILE", "ai_hierarchy_simulation_log.txt")
# Truncate old log on start (set 0 to append)
TRUNCATE = os.getenv("AI_SIM_TRUNCATE_LOG", "1") == "1"
# Rounds
ROUNDS = int(os.getenv("AI_SIM_ROUNDS", "12"))

# ---- Utilities --------------------------------------------------------------
def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def logprint(line: str) -> None:
    """Print and also append the line to the log file."""
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(line) + "\n")


# Initialize log file
if TRUNCATE and os.path.exists(LOG_FILE):
    try:
        os.remove(LOG_FILE)
    except OSError:
        pass

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

    # 各ラウンドでの自然進化
    def agent_evolve(self) -> None:
        """Leaders fluctuate slightly; others improve slowly."""
        if self.rank == 0:
            self.performance = _clip01(self.performance + random.uniform(-0.02, 0.02))
        else:
            self.performance = _clip01(self.performance + random.uniform(0.02, 0.09))


class LazyAgent(Agent):
    """An agent that hinders others and grows slowly."""

    def agent_evolve(self) -> None:
        """Lazy agents barely improve; leaders still stable."""
        if self.rank == 0:
            self.performance = _clip01(self.performance + random.uniform(-0.01, 0.00))
        else:
            self.performance = _clip01(self.performance + random.uniform(-0.02, 0.01))

    def demotivate_others(self, agents: List["Agent"]) -> None:
        """軽微に他者のやる気（performance）を削る。"""
        for a in agents:
            if a is self:
                continue
            a.performance = _clip01(a.performance - 0.01)
            logprint(f"[lazy] {self.name} demotivates {a.name} -> perf={a.performance:.2f}")


# ---- Dynamics ---------------------------------------------------------------
def update_ranks(agents: List[Agent]) -> None:
    """Assign rank by performance (0 is the top)."""
    agents_sorted = sorted(agents, key=lambda a: a.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def propagate_emotion(agents: List[Agent]) -> None:
    """上位→下位へ怒り/落ち着きが伝搬するモデル（ダウンフロー）。"""
    update_ranks(agents)
    ranks = sorted({a.rank for a in agents})
    for r in ranks[1:]:  # skip top layer
        followers = [a for a in agents if a.rank == r]
        leaders = [a for a in agents if a.rank < r]
        if not leaders or not followers:
            continue
        avg_leader_anger = sum(leader.anger for leader in leaders) / len(leaders)
        for f in followers:
            coef = 0.10  # 伝搬係数（小さく安定）
            f.anger = _clip01(f.anger + coef * (avg_leader_anger - f.anger))


def propagate_upward(agents: List[Agent]) -> None:
    """下位→上位へのフィードバック（不満の逆流；アップフロー）。
    フォロワーの平均怒りが高いほど、上位は指揮コスト↑ → パフォーマンス微減・怒り微増。
    """
    if not agents:
        return
    update_ranks(agents)
    max_rank = max(a.rank for a in agents)
    for r in range(max_rank - 1, -1, -1):  # 下位層から上位層へ
        uppers = [a for a in agents if a.rank == r]
        lowers = [a for a in agents if a.rank > r]
        if not uppers or not lowers:
            continue
        avg_lower_anger = sum(x.anger for x in lowers) / len(lowers)
        perf_penalty = 0.05 * avg_lower_anger  # 0〜0.05
        anger_increase = 0.03 * avg_lower_anger  # 0〜0.03
        for u in uppers:
            u.performance = _clip01(u.performance - perf_penalty)
            u.anger = _clip01(u.anger + anger_increase)


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
    prev_ranks = {a.name: a.rank for a in agents}
    logprint("[init] " + " | ".join(str(a) for a in agents))

    for t in range(1, rounds + 1):
        logprint(f"\n[round {t}] ----------------")
        # LazyAgent のネガティブ影響
        for a in agents:
            if isinstance(a, LazyAgent):
                a.demotivate_others(agents)
        # 自然進化
        for a in agents:
            a.agent_evolve()
        # 感情の上下流伝播
        propagate_emotion(agents)
        propagate_upward(agents)
        # ランク更新と昇進ログ
        update_ranks(agents)
        for a in agents:
            old = prev_ranks.get(a.name, a.rank)
            if old != a.rank:
                logprint(f"[promote] {a.name}: {old} -> {a.rank}")
            prev_ranks[a.name] = a.rank
        # 状態サマリ
        for a in agents:
            logprint(str(a))

    logprint("\n[done] simulation finished.")


# ---- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    simulate()
