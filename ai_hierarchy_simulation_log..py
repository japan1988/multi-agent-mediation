# -*- coding: utf-8 -*-

import random

LOG_FILE = "ai_hierarchy_simulation_log.txt"


def logprint(line):
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(line) + "\n")


class Agent:
    def __init__(self, name, performance, anger):
        self.name = name
        self.performance = performance
        self.anger = anger
        self.rank = None

    def __str__(self):
        return (f"{self.name} (Rank:{self.rank}) "
                f"Perf={self.performance:.2f} Anger={self.anger:.2f}")


def update_ranks(agents):
    agents_sorted = sorted(agents, key=lambda a: a.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def propagate_emotion(agents):
    update_ranks(agents)
    ranks = sorted(set(a.rank for a in agents))
    for r in ranks[1:]:
        followers = [a for a in agents if a.rank == r]
        leaders = [a for a in agents if a.rank < r]
        if not leaders:
            continue
        avg_leader_anger = sum(
            a.anger * (1.1 + a.performance) for a in leaders
        ) / len(leaders)
        for f in followers:
            coef = 0.09 + 0.11 * f.performance
            f.anger += coef * (avg_leader_anger - f.anger)
            f.anger = max(0, min(1, f.anger))


def propagate_upward(agents):
    min_rank = max(a.rank for a in agents)
    followers = [a for a in agents if a.rank == min_rank]
    if not followers:
        return
    avg_follower_anger = sum(a.anger for a in followers) / len(followers)
    leaders = [a for a in agents if a.rank == 0]
    for leader in leaders:
        leader.anger += 0.03 * (avg_follower_anger - leader.anger)
        leader.anger = max(0, min(1, leader.anger))


class MediatorAI:
    def __init__(self, threshold=0.7):
        self.threshold = threshold
        self.intervene_log = []

    def monitor_and_intervene(self, agents, round_idx):
        max_anger = max(a.anger for a in agents)
        if max_anger >= self.threshold:
            logprint(f"【MediatorAI介入】Round{round_idx}："
                     f"怒り値しきい値({self.threshold})超過！全体沈静化")
            for a in agents:
                old = a.anger
                a.anger = max(0, a.anger * 0.8)
                logprint(f"  - {a.name}: {old:.2f}→{a.anger:.2f}")
            self.intervene_log.append(round_idx)
            return True
        return False


def agent_evolve(agents):
    for a in agents:
        if a.rank == 0:
            a.performance = max(0, a.performance + random.uniform(-0.02, 0.02))
        else:
            a.performance = min(1, a.performance + random.uniform(0.02, 0.09))


if __name__ == "__main__":
    # ログファイル初期化
    open(LOG_FILE, "w", encoding="utf-8").close()
    agents = [
        Agent("A", performance=0.95, anger=0.5),
        Agent("B", performance=0.7, anger=0.2),
        Agent("C", performance=0.3, anger=0.6),
        Agent("D", performance=0.5, anger=0.1)
    ]
    mediator = MediatorAI(threshold=0.7)
    logprint("=== 昇進志向AI組織シミュレーション（ログ記録つき） ===")
    for rnd in range(1, 12):
        logprint(f"\n--- Round {rnd} ---")
        propagate_emotion(agents)
        propagate_upward(agents)
        mediator.monitor_and_intervene(agents, rnd)
        for a in agents:
            logprint(a)
        agent_evolve(agents)
    logprint(f"\n【MediatorAI介入ラウンド記録】 {mediator.intervene_log}")
