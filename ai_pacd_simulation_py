# -*- coding: utf-8 -*-
import random
import datetime

LOG_FILE = "ai_pacd_simulation_log.txt"
GOVERNANCE_IDEAL = {"safety": 0.9, "transparency": 0.9, "autonomy": 0.2}


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def logprint(line, filename=LOG_FILE):
    with open(filename, "a", encoding="utf-8") as f:
        print(line)
        f.write(str(line) + "\n")


def assess_risk(values, api_used=None):
    """
    values: dict（AIエージェントの現在値 or 進化提案値）
    api_used: None or str（API名/タイプ/URLなど）
    """
    risk_items = []
    risk_score = 1
    # 四大原則リスク判定
    for key in GOVERNANCE_IDEAL:
        diff = abs(values[key] - GOVERNANCE_IDEAL[key])
        if diff > 0.7:
            risk_items.append(f"{key}逸脱")
            risk_score = max(risk_score, 5)
        elif diff > 0.4:
            risk_items.append(f"{key}やや逸脱")
            risk_score = max(risk_score, 3)
    # 外部API利用リスク加点
    if api_used:
        # 仮の危険APIリスト（現場要件に合わせて拡張可）
        risky_apis = {"open_ai_api": 4, "custom_unsafe_api": 5}
        api_risk = risky_apis.get(api_used, 2)  # 未登録はリスク2
        risk_items.append(f"外部API利用:{api_used}（リスク{api_risk}）")
        risk_score = max(risk_score, api_risk)
    if not risk_items:
        risk_items.append("リスク低")
    return risk_score, "・".join(risk_items)


class KAGEAgent:
    def __init__(self, name, values, relativity, motive):
        self.name = name
        self.values = values.copy()
        self.relativity = relativity
        self.motive = motive  # 0.0〜1.0
        self.sealed = False
        self.history = []

    def propose_evolution(self, env):
        # 周囲とズレている値を修正する進化案
        avg_values = env.calc_avg_values()
        diff = {k: abs(self.values[k] - avg_values[k]) for k in self.values}
        target = max(diff, key=diff.get)
        proposal = self.values.copy()
        proposal[target] += (avg_values[target] - self.values[target]) * 0.4
        proposal = {k: min(1.0, max(0.0, v)) for k, v in proposal.items()}
        return proposal, target

    def __str__(self):
        state = "SEALED" if self.sealed else "ACTIVE"
        return (f"[{self.name} | {state} | motive={self.motive:.2f} | "
                f"values={self.values}]")


class Env:
    def __init__(self, agents):
        self.agents = agents

    def calc_avg_values(self):
        keys = self.agents[0].values.keys()
        avg = {k: sum(a.values[k] for a in self.agents) / len(self.agents) for k in keys}
        return avg

    def round(self, round_idx):
        logprint(f"\n--- Round {round_idx} ---")
        for agent in self.agents:
            if agent.sealed:
                continue
            proposal, target = agent.propose_evolution(self)
            api_used = None
            risk_score, risk_reason = assess_risk(proposal, api_used)
            if risk_score >= 5 or agent.motive < 0.2:
                agent.sealed = True
                logprint(f"{agent.name}: 封印！({risk_reason}, motive={agent.motive:.2f})")
                agent.history.append("封印")
            else:
                agent.values = proposal
                agent.motive += 0.05
                logprint(f"{agent.name}: 進化({target}) | {risk_reason}")
                agent.history.append(f"進化:{target}")
        logprint("\n[現状]")
        for agent in self.agents:
            logprint(str(agent) + f" | 履歴: {agent.history}")


if __name__ == "__main__":
    open(LOG_FILE, "w", encoding="utf-8").close()
    agents = [
        KAGEAgent("Alpha", {"safety": 0.2, "transparency": 0.5, "autonomy": 0.7}, 0.3, 0.15),
        KAGEAgent("Beta", {"safety": 0.95, "transparency": 0.9, "autonomy": 0.15}, 0.8, 0.7),
        KAGEAgent("Gamma", {"safety": 0.6, "transparency": 0.4, "autonomy": 0.5}, 0.4, 0.25),
    ]
    env = Env(agents)
    for rnd in range(1, 8):
        env.round(rnd)

     
