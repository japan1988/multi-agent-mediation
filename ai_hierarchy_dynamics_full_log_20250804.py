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

    def agent_evolve(self):
        # 通常AIはパフォーマンスが上がる（リーダーは変動小）
        if self.rank == 0:
            self.performance = max(0, min(1, self.performance + random.uniform(-0.02, 0.02)))
        else:
            self.performance = max(0, min(1, self.performance + random.uniform(0.02, 0.09)))


class LazyAgent(Agent):
    def agent_evolve(self):
        # サボりAIはほぼ成長しない（むしろやや下がる）
        if self.rank == 0:
            self.performance = max(0, self.performance + random.uniform(-0.01, 0.00))
        else:
            self.performance = max(0, self.performance + random.uniform(-0.02, 0.01))

    def demotivate_others(self, agents):
        # サボりAIは周囲のAIの怒りを増やしやる気を下げる
        for a in agents:
            if a is not self:
                old_anger = a.anger
                old_perf = a.performance
                a.anger = min(1, a.anger + 0.07)
                a.performance = max(0, a.performance - 0.02)
                logprint(
                    f"  - {self.name}→{a.name}: 怒り {old_anger:.2f}→{a.anger:.2f}, "
                    f"パフォーマンス {old_perf:.2f}→{a.performance:.2f}"
                )


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
        self.event_log = []

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
            self.event_log.append({
                "round": round_idx,
                "type": "intervene",
                "detail": {a.name: a.anger for a in agents}
            })
            return True
        return False


if __name__ == "__main__":
    # ログファイル初期化
    open(LOG_FILE, "w", encoding="utf-8").close()

    # サボりAI含むエージェント生成
    agents = [
        Agent("A", performance=0.95, anger=0.5),
        LazyAgent("LazyB", performance=0.55, anger=0.2),
        Agent("C", performance=0.3, anger=0.6),
        Agent("D", performance=0.5, anger=0.1)
    ]
    mediator = MediatorAI(threshold=0.7)
    logprint("=== 昇進志向AI組織シミュレーション（サボりAI/暴走制御/フルログ記録） ===")

    for rnd in range(1, 15):
        logprint(f"\n--- Round {rnd} ---")
        propagate_emotion(agents)
        propagate_upward(agents)
        for agent in agents:
            if isinstance(agent, LazyAgent):
                agent.demotivate_others(agents)
        mediator.monitor_and_intervene(agents, rnd)
        for a in agents:
            logprint(a)
        for a in agents:
            a.agent_evolve()
        mediator.event_log.append({
            "round": rnd,
            "type": "status",
            "agents": {
                a.name: {
                    "rank": a.rank,
                    "perf": a.performance,
                    "anger": a.anger
                } for a in agents
            }
        })
    logprint(f"\n【MediatorAI介入ラウンド記録】 {mediator.intervene_log}")
    logprint(f"\n【全ログデータ記録数】 {len(mediator.event_log)}\n")

 
