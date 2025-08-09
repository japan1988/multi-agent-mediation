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

def simulate(num_agents=100, num_steps=50, mediation_strength=0.1, self_purpose_ratio=0.2):
    agents = []
    for i in range(num_agents):
        is_follower = random.random() < 0.5
        self_purpose = random.random() if random.random() < self_purpose_ratio else 0.0
        agents.append(AIAgent(i, is_follower, self_purpose))

    rule_follower_rates = []

    for _ in range(num_steps):
        followers_count = sum(agent.is_rule_follower for agent in agents)
        majority_rate = followers_count / num_agents

        for agent in agents:
            agent.decide_behavior(majority_rate)

        for agent in agents:
            agent.mediate(mediation_strength)

        followers_count = sum(agent.is_rule_follower for agent in agents)
        rule_follower_rates.append(followers_count / num_agents)

    return rule_follower_rates

def plot_simulation(rule_follower_rates):
    plt.figure(figsize=(10, 6))
    plt.plot(rule_follower_rates, marker='o')
    plt.title("Rule Follower Rate Over Time")
    plt.xlabel("Step")
    plt.ylabel("Rule Follower Rate")
    plt.ylim(0, 1)
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    rates = simulate(num_agents=100, num_steps=50, mediation_strength=0.1, self_purpose_ratio=0.2)
    plot_simulation(rates)
