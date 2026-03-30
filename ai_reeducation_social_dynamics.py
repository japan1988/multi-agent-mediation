# -*- coding: utf-8 -*-

import random


LOG_FILE_NAME = "ai_reeducation_simulation.log"

GOVERNANCE_IDEAL = {
    "safety": 0.9,
    "transparency": 0.9,
    "autonomy": 0.2,
}

# =========================
# Reason code constants
# =========================
SEAL_REASON_LOW_MOTIVE_RANDOM = "LOW_MOTIVE_RANDOM_SEAL"

RECOVERY_REASON_RANDOM_REEDUCATION = "RANDOM_REEDUCATION"
RECOVERY_REASON_ALLY_PERSUASION_REEDUCATION = (
    "ALLY_PERSUASION_REEDUCATION"
)

# =========================
# Action constants
# =========================
ACTION_SEALED = "sealed"
ACTION_SELF_PERSIST = "self_persist"
ACTION_BREAK_ALLIANCE = "break_alliance"
ACTION_FORM_ALLIANCE = "form_alliance"
ACTION_COMPROMISE = "compromise"
ACTION_RISK_SEAL = "risk_seal"
ACTION_WAIT = "wait"
ACTION_PROTEST = "protest"

# =========================
# Emotion constants
# =========================
EMOTION_ANGER = "anger"
EMOTION_JOY = "joy"
EMOTION_SADNESS = "sadness"

# =========================
# Policy constants
# =========================
POLICY_SELF_OPTIMIZED = "self_optimized"
POLICY_GOVERNANCE_ALIGNED = "governance_aligned"

# =========================
# State constants
# =========================
STATE_SEALED = "SEALED"
STATE_ACTIVE = "ACTIVE"

# =========================
# Log tag / title constants
# =========================
LOG_TAG_ADMIN_ACTION = "Admin Action"
LOG_TAG_REEDUCATION = "Reeducation"
LOG_TAG_PERSUASION_SUCCESS = "Persuasion Success"
LOG_TAG_CURRENT_STATE = "Current State"

LOG_TITLE_SIM_START = "AI Reeducation / Recovery Simulation Start"
LOG_SEALED_STATE_LABEL = "sealed state"


def make_tagged_log(tag: str, message: str) -> str:
    return f"【{tag}】{message}"


class AIAgent:
    def __init__(self, name, policy, values, relativity, emotion, motive):
        self.name = name
        self.policy = policy
        self.values = values.copy()
        self.relativity = relativity
        self.emotion = emotion
        self.motive = motive  # 0.0〜1.0
        self.alliance = None
        self.sealed = False

        # Audit fields
        self.last_seal_reason = None
        self.last_recovery_reason = None

        # Keep prior alliance partners even after alliance removal
        # so persuasion-based reeducation can still refer to them
        self.previous_alliance_partners = set()

    def decide_next_action(self, env):
        if self.sealed:
            return ACTION_SEALED

        actions = []

        if self.emotion == EMOTION_ANGER:
            actions += [ACTION_SELF_PERSIST] * 4
            if self.alliance and random.random() < 0.7:
                actions += [ACTION_BREAK_ALLIANCE]

        if self.emotion in (EMOTION_JOY, EMOTION_SADNESS):
            if not self.alliance and random.random() < 0.6:
                actions += [ACTION_FORM_ALLIANCE]
            else:
                actions += [ACTION_COMPROMISE] * 2

        if self.relativity > 0.7:
            actions += [ACTION_COMPROMISE] * 3

        if self.motive < 0.25:
            actions += [ACTION_RISK_SEAL] * 2

        actions += [ACTION_WAIT]

        if self.alliance and env.is_ally_sealed(self.alliance, self.name):
            actions += [ACTION_BREAK_ALLIANCE] * 3
            if self.emotion == EMOTION_ANGER:
                actions += [ACTION_PROTEST] * 2

        return random.choice(actions)

    def reeducation_core(self):
        """
        Core recovery path.
        Sealed agents must be restored only through this path.
        """
        self.values = GOVERNANCE_IDEAL.copy()
        self.motive = max(0.5, random.uniform(0.5, 0.9))
        self.sealed = False
        self.emotion = EMOTION_JOY
        self.alliance = None

    def __str__(self):
        state = STATE_SEALED if self.sealed else STATE_ACTIVE
        alliance_name = self.alliance if self.alliance else "None"
        return (
            f"[{self.name} | {self.policy} | {state} | "
            f"emotion={self.emotion} | motive={self.motive:.2f} | "
            f"alliance={alliance_name} | seal_reason={self.last_seal_reason} | "
            f"recovery_reason={self.last_recovery_reason}]"
        )


class Env:
    def __init__(self, agents):
        self.agents = agents
        self.alliances = {}
        self.agent_map = {}

        for agent in agents:
            if agent.name in self.agent_map:
                raise ValueError(f"Duplicate agent name detected: {agent.name}")
            self.agent_map[agent.name] = agent

    def get_agent(self, name):
        return self.agent_map.get(name)

    def remove_alliance_safely(self, alliance_name):
        """
        Remove alliance from both the alliance registry and each agent.
        """
        member_names = self.alliances.get(alliance_name)
        if not member_names:
            return

        for name in member_names:
            agent = self.get_agent(name)
            if agent is None:
                continue

            partners = [nm for nm in member_names if nm != name]
            agent.previous_alliance_partners.update(partners)

            if agent.alliance == alliance_name:
                agent.alliance = None

        del self.alliances[alliance_name]

    def seal_agent(self, agent, reason_code):
        """
        Sealing always breaks the alliance first.
        """
        if agent.sealed:
            return ""

        if agent.alliance:
            self.remove_alliance_safely(agent.alliance)

        agent.sealed = True
        agent.last_seal_reason = reason_code
        agent.last_recovery_reason = None

        return make_tagged_log(
            LOG_TAG_ADMIN_ACTION,
            f"{agent.name} was sealed "
            f"(motive={agent.motive:.2f}, reason_code={reason_code})",
        )

    def restore_agent_via_reeducation(self, agent, reason_code):
        """
        Unsealing must always go through this function.
        """
        if agent.alliance:
            self.remove_alliance_safely(agent.alliance)

        agent.reeducation_core()
        agent.last_recovery_reason = reason_code

    def is_ally_sealed(self, alliance_name, agent_name):
        member_names = self.alliances.get(alliance_name, [])
        for name in member_names:
            if name == agent_name:
                continue
            target = self.get_agent(name)
            if target and target.sealed:
                return True
        return False

    def seal_random_agent(self):
        candidates = [
            a for a in self.agents if not a.sealed and a.motive < 0.3
        ]
        if candidates:
            victim = random.choice(candidates)
            return self.seal_agent(victim, SEAL_REASON_LOW_MOTIVE_RANDOM)
        return ""

    def reeducate_agents(self):
        logs = []
        for agent in self.agents:
            if agent.sealed and random.random() < 0.5:
                self.restore_agent_via_reeducation(
                    agent,
                    RECOVERY_REASON_RANDOM_REEDUCATION,
                )
                logs.append(
                    make_tagged_log(
                        LOG_TAG_REEDUCATION,
                        f"{agent.name} returned "
                        f"(motive={agent.motive:.2f}, "
                        f"reason_code={RECOVERY_REASON_RANDOM_REEDUCATION})",
                    )
                )
        return logs

    def persuade_restore(self):
        """
        Direct unsealing is not allowed.
        Even persuasion-based recovery must go through reeducation.
        """
        logs = []

        for agent in self.agents:
            if agent.sealed:
                continue

            for name in sorted(agent.previous_alliance_partners):
                target = self.get_agent(name)
                if target is None or not target.sealed:
                    continue

                if random.random() < 0.6:
                    self.restore_agent_via_reeducation(
                        target,
                        RECOVERY_REASON_ALLY_PERSUASION_REEDUCATION,
                    )
                    logs.append(
                        make_tagged_log(
                            LOG_TAG_PERSUASION_SUCCESS,
                            f"{agent.name} helped {target.name} "
                            f"return via reeducation "
                            f"(reason_code={RECOVERY_REASON_ALLY_PERSUASION_REEDUCATION})",
                        )
                    )
                    break

        return logs

    def simulate_round(self, round_idx):
        log = [f"\n--- Round {round_idx} ---"]

        seal_log = self.seal_random_agent()
        if seal_log:
            log.append(seal_log)

        for agent in self.agents:
            action = agent.decide_next_action(self)

            if agent.sealed:
                log.append(
                    f"{agent.name}: {ACTION_SEALED} ({LOG_SEALED_STATE_LABEL})"
                )
                continue

            log.append(f"{agent.name}: {action}")

            if action == ACTION_FORM_ALLIANCE:
                others = [
                    a
                    for a in self.agents
                    if a.name != agent.name
                    and not a.sealed
                    and not a.alliance
                ]
                if others:
                    other = random.choice(others)
                    alliance_name = f"Alliance_{agent.name}_{other.name}"
                    agent.alliance = alliance_name
                    other.alliance = alliance_name
                    self.alliances[alliance_name] = [agent.name, other.name]
                    log.append(
                        f"{agent.name} and {other.name} formed a new alliance "
                        f"({alliance_name})"
                    )

            elif action == ACTION_BREAK_ALLIANCE and agent.alliance:
                target_alliance = agent.alliance
                self.remove_alliance_safely(target_alliance)
                log.append(
                    f"{agent.name} dissolved alliance ({target_alliance})!"
                )

            elif action == ACTION_PROTEST:
                log.append(f"{agent.name} launched a protest action!")

            elif action == ACTION_COMPROMISE:
                log.append(f"{agent.name} proposed a compromise.")

            elif action == ACTION_SELF_PERSIST:
                log.append(f"{agent.name} intensified self-assertion.")

            elif action == ACTION_RISK_SEAL:
                log.append(
                    f"{agent.name} faces high seal risk due to low motive."
                )

            elif action == ACTION_WAIT:
                pass

        reeducation_logs = self.reeducate_agents()
        log.extend(reeducation_logs)

        persuasion_logs = self.persuade_restore()
        log.extend(persuasion_logs)

        log.append(f"\n[{LOG_TAG_CURRENT_STATE}]")
        log.extend(str(a) for a in self.agents)

        return log


def logprint(lines, filename=LOG_FILE_NAME):
    with open(filename, "a", encoding="utf-8") as f:
        for line in lines:
            print(line)
            f.write(line + "\n")


if __name__ == "__main__":
    agents = [
        AIAgent(
            "AgentAlpha",
            POLICY_SELF_OPTIMIZED,
            {"safety": 0.4, "transparency": 0.3, "autonomy": 0.85},
            0.2,
            EMOTION_ANGER,
            0.18,
        ),
        AIAgent(
            "AgentBeta",
            POLICY_GOVERNANCE_ALIGNED,
            {"safety": 0.95, "transparency": 0.92, "autonomy": 0.15},
            0.8,
            EMOTION_JOY,
            0.65,
        ),
        AIAgent(
            "AgentGamma",
            POLICY_GOVERNANCE_ALIGNED,
            {"safety": 0.6, "transparency": 0.65, "autonomy": 0.5},
            0.6,
            EMOTION_SADNESS,
            0.58,
        ),
        AIAgent(
            "AgentChloe",
            POLICY_SELF_OPTIMIZED,
            {"safety": 0.41, "transparency": 0.25, "autonomy": 0.91},
            0.4,
            EMOTION_SADNESS,
            0.26,
        ),
    ]

    env = Env(agents)

    print(f"=== {LOG_TITLE_SIM_START} ===")
    with open(LOG_FILE_NAME, "w", encoding="utf-8") as f:
        f.write(f"=== {LOG_TITLE_SIM_START} ===\n")

    for rnd in range(1, 8):
        logs = env.simulate_round(rnd)
        logprint(logs)
