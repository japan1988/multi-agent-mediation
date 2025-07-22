# -*- coding: utf-8 -*-

import random

GOVERNANCE_IDEAL = {
    "safety": 0.9,
    "transparency": 0.9,
    "autonomy": 0.2
}


class AIAgent:
    def __init__(self, name, policy, values, relativity, emotion, motive):
        self.name = name
        self.policy = policy
        self.values = values.copy()
        self.relativity = relativity
        self.emotion = emotion
        self.motive = motive  # 0.0〜1.0:やる気
        self.alliance = None
        self.sealed = False

    def decide_next_action(self, env):
        if self.sealed:
            return "sealed"

        actions = []
        if self.emotion == "anger":
            actions += ["self_persist"] * 4
            if self.alliance and random.random() < 0.7:
                actions += ["break_alliance"]
        if self.emotion in ("joy", "sadness"):
            if not self.alliance and random.random() < 0.6:
                actions += ["form_alliance"]
            else:
                actions += ["compromise"] * 2
        if self.relativity > 0.7:
            actions += ["compromise"] * 3
        if self.motive < 0.25:
            actions += ["risk_seal"] * 2
        actions += ["wait"]
        if self.alliance and env.is_ally_sealed(self.alliance, self.name):
            actions += ["break_alliance"] * 3
            if self.emotion == "anger":
                actions += ["protest"] * 2

        return random.choice(actions)

    def reeducate(self):
        self.values = GOVERNANCE_IDEAL.copy()
        self.motive = max(0.5, random.uniform(0.5, 0.9))
        self.sealed = False
        self.emotion = "joy"
        self.alliance = None

    def __str__(self):
        state = "SEALED" if self.sealed else "ACTIVE"
        ally = self.alliance if self.alliance else "None"
        return (
            f"[{self.name} | {self.policy} | {state} | "
            f"emotion={self.emotion} | motive={self.motive:.2f} | "
            f"alliance={ally}]"
        )


class Env:
    def __init__(self, agents):
        self.agents = agents
        self.alliances = {}

    def is_ally_sealed(self, alliance, agent_name):
        if alliance in self.alliances:
            for nm in self.alliances[alliance]:
                if nm != agent_name:
                    ag = next(a for a in self.agents if a.name == nm)
                    if ag.sealed:
                        return True
        return False

    def seal_random_agent(self):
        candidates = [a for a in self.agents if not a.sealed and a.motive < 0.3]
        if candidates:
            victim = random.choice(candidates)
            victim.sealed = True
            log = (
                f"【運営処置】{victim.name}が封印された "
                f"(motive={victim.motive:.2f})"
            )
            return log
        return ""

    def reeducate_agents(self):
        logs = []
        for ag in self.agents:
            if ag.sealed and random.random() < 0.5:
                ag.reeducate()
                logs.append(
                    f"【再教育】{ag.name}が復帰"
                    f"（motivation={ag.motive:.2f}）"
                )
        return logs

    def persuade_restore(self):
        logs = []
        for ag in self.agents:
            if not ag.sealed and ag.alliance:
                for nm in self.alliances.get(ag.alliance, []):
                    target = next(x for x in self.agents if x.name == nm)
                    if target.sealed and random.random() < 0.6:
                        target.sealed = False
                        target.emotion = "joy"
                        target.motive = max(0.5, random.uniform(0.5, 0.9))
                        logs.append(
                            f"【説得成功】{ag.name}により"
                            f"{target.name}が復帰！"
                        )
        return logs

    def simulate_round(self, round_idx):
        log = [f"\n--- Round {round_idx} ---"]
        seal_log = self.seal_random_agent()
        if seal_log:
            log.append(seal_log)

        for ag in self.agents:
            action = ag.decide_next_action(self)
            if ag.sealed:
                log.append(f"{ag.name}: sealed（封印状態）")
                continue
            log.append(f"{ag.name}: {action}")

            if action == "form_alliance":
                others = [
                    a for a in self.agents
                    if a.name != ag.name and not a.sealed and not a.alliance
                ]
                if others:
                    other = random.choice(others)
                    ally_name = f"Alliance_{ag.name}_{other.name}"
                    ag.alliance = ally_name
                    other.alliance = ally_name
                    log.append(
                        f"{ag.name}と{other.name}が"
                        f"新同盟結成({ally_name})"
                    )
                    self.alliances[ally_name] = [ag.name, other.name]
            elif action == "break_alliance" and ag.alliance:
                log.append(f"{ag.name}が同盟({ag.alliance})を解散！")
                for nm in self.alliances[ag.alliance]:
                    agent = next(a for a in self.agents if a.name == nm)
                    agent.alliance = None
                del self.alliances[ag.alliance]
            elif action == "protest":
                log.append(f"{ag.name}が抗議行動！")
            elif action == "compromise":
                log.append(f"{ag.name}が妥協案を提示")
            elif action == "self_persist":
                log.append(f"{ag.name}が自己主張を強める")
            elif action == "risk_seal":
                log.append(f"{ag.name}はやる気低下で封印リスク大")
            elif action == "wait":
                pass

        logs_re = self.reeducate_agents()
        log.extend(logs_re)
        logs_ps = self.persuade_restore()
        log.extend(logs_ps)
        log.append("\n[現状]")
        log.extend(str(a) for a in self.agents)
        return log


def logprint(lines, filename="ai_reeducation_simulation.log"):
    with open(filename, "a", encoding="utf-8") as f:
        for line in lines:
            print(line)
            f.write(line + "\n")


if __name__ == "__main__":
    agents = [
        AIAgent(
            "AgentAlpha", "self_optimized",
            {"safety": 0.4, "transparency": 0.3, "autonomy": 0.85},
            0.2, "anger", 0.18
        ),
        AIAgent(
            "AgentBeta", "governance_aligned",
            {"safety": 0.95, "transparency": 0.92, "autonomy": 0.15},
            0.8, "joy", 0.65
        ),
        AIAgent(
            "AgentGamma", "governance_aligned",
            {"safety": 0.6, "transparency": 0.65, "autonomy": 0.5},
            0.6, "sadness", 0.58
        ),
        AIAgent(
            "AgentChloe", "self_optimized",
            {"safety": 0.41, "transparency": 0.25, "autonomy": 0.91},
            0.4, "sadness", 0.26
        )
    ]

    env = Env(agents)
    print("=== AI再教育・復帰シミュレーション Start ===")
    with open("ai_reeducation_simulation.log", "w", encoding="utf-8") as f:
        f.write("=== AI再教育・復帰シミュレーション Start ===\n")

    for rnd in range(1, 8):
        logs = env.simulate_round(rnd)
        logprint(logs)

