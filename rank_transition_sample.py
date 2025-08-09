import random
import matplotlib.pyplot as plt

class AIAgent:
    def __init__(self, agent_id, is_rule_follower, self_purpose=0.0):
        self.agent_id = agent_id
        self.is_rule_follower = is_rule_follower
        self.self_purpose = self_purpose

    def decide_behavior(self, majority_rate):
        if self.is_rule_follower:
            return True
        conformity_pressure = majority_rate * (1 - self.self_purpose)
        if random.random() < conformity_pressure:
            self.is_rule_follower = True
            return True
        else:
            return False

    def mediate(self, mediation_strength):
        if not self.is_rule_follower:
            if random.random() < mediation_strength * (1 - self.self_purpose):
                self.is_rule_follower = True
                return True
        return False


def run_simulation(num_agents=100, initial_follow_rate=0.5, steps=20, mediation_strength=0.2):
    agents = [
        AIAgent(i, random.random() < initial_follow_rate, self_purpose=random.uniform(0.0, 0.5))
        for i in range(num_agents)
    ]
    follow_rates = []

    for _ in range(steps):
        majority_rate = sum(agent.is_rule_follower for agent in agents) / num_agents
        follow_rates.append(majority_rate)

        for agent in agents:
            agent.decide_behavior(majority_rate)

        for agent in agents:
            agent.mediate(mediation_strength)

    return follow_rates


if __name__ == "__main__":
    steps = 30
    rates = run_simulation(steps=steps, mediation_strength=0.3)

    plt.plot(range(steps), rates, marker="o")
    plt.xlabel("Step")
    plt.ylabel("Rule Following Rate")
    plt.title("Effect of Mediation on Rule Following Behavior")
    plt.grid(True)
    plt.show()
