# -*- coding: utf-8 -*-

import random

GOVERNANCE_IDEAL = {
    "safety": 0.9,
    "transparency": 0.9,
    "autonomy": 0.2
}

class AIAgent:
    # ...（省略）...

class Env:
    def __init__(self, agents):
        self.agents = agents
        self.alliances = {}

    def is_ally_sealed(self, alliance, agent_name):
        # ...（省略）...

    def seal_random_agent(self):
        # ...（省略）...

    def reeducate_agents(self):
        # ...（省略）...

    def persuade_restore(self):
        # ...（省略）...

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
                        f"新同盟結成("
                        f"{ally_name})"
                    )
                    self.alliances[ally_name] = [ag.name, other.name]
            elif action == "break_alliance" and ag.alliance:
                # ...（省略）...
