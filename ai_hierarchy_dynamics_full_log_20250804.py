# -*- coding: utf-8 -*-
import os
import random

# [RF-LOG-001] Make log file path configurable
LOG_FILE = os.getenv("AI_SIM_LOGFILE", "ai_hierarchy_simulation_log.txt")


def logprint(line: str) -> None:
    """Print and also append the line to the log file."""
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(line) + "\n")


class Agent:
    """A basic AI agent with performance and anger parameters."""

    def __init__(self, name: str, performance: float, anger: float) -> None:
        self.name = name
        self.performance = performance
        self.anger = anger
        self.rank = -1  # [RF-OOP-001] intで初期化

    def __str__(self) -> str:
        return f"{self.name} (Rank:{self.rank}) perf={self.performance:.2f} anger={self.anger:.2f}"

    # 各ラウンドでの自然進化
    def agent_evolve(self) -> None:
        # リーダーは変動が小さい、他は緩やかに上昇
        if self.rank == 0:
            self.performance = max(0.0, min(1.0, self.performance + random.uniform(-0.02, 0.02)))
        else:
            self.performance = max(0.0, min(1.0, self.performance + random.uniform(0.02, 0.09)))


class LazyAgent(Agent):
    """An agent that hinders others and grows slowly."""

    def agent_evolve(self) -> None:
        # サボりAIは成長しにくい
        if self.rank == 0:
            self.performance = max(0.0, self.performance + random.uniform(-0.01, 0.00))
        else:
            self.performance = max(0.0, self.performance + random.uniform(-0.02, 0.01))

    def demotivate_others(self, agents: list["Agent"]) -> None:
        # フォロワーのやる気を下げる（軽微）
        for a in agents:
            if a is self:
                continue
            a.performance = max(0.0, a.performance - 0.01)
            logprint(f"[lazy] {self.name} demotivates {a.name} -> perf={a.performance:.2f}")


def update_ranks(agents: list[Agent]) -> None:
    agents_sorted = sorted(agents, key=lambda a: a.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def propagate_emotion(agents: list[Agent]) -> None:
    """上位→下位へ怒り/落ち着きが伝搬するモデル。"""
    update_ranks(agents)
    ranks = sorted({a.rank for a in agents})
    for r in ranks[1:]:
        followers = [a for a in agents if a.rank == r]
        leaders = [a for a in agents if a.rank < r]
        if not leaders or not followers:
            continue
        avg_leader_anger = sum(l.anger for l in leaders) / len(leaders)
        for f in followers:
            coef = 0.1  # 伝搬係数（小さく安定）
            f.anger += coef * (avg_leader_anger - f.anger)
            f.anger = max(0.0, min(1.0, f.anger))

def propagate_upward(agents: list[Agent]) -> None:
    """下位→上位へのフィードバック（不満の逆流）"""
    
