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
            if random.random() < mediation_strength:
                self.is_rule_follower = True
                return True
        return False


def run_simulation(num_agents=100, rule_followers_ratio=0.5, self_purpose_mean=0.2, 
                   mediation_strength=0.3, steps=50):
    agents = []
    for i in range(num_agents):
        is_rule_follower = random.random() < rule_followers_ratio
        self_purpose = min(max(random.gauss(self_purpose_mean, 0.1), 0.0), 1.0)
        agents.append(AIAgent(i, is_rule_follower, self_purpose))

    rule_follower_rates = []
    mediation_counts = []

    for step in range(steps):
        majority_rate = sum(a.is_rule_follower for a in agents) / len(agents)
        rule_follower_rates.append(majority_rate)

        mediation_count = 0
        for agent in agents:
            agent.decide_behavior(majority_rate)
            if not agent.is_rule_follower:
                if agent.mediate(mediation_strength):
                    mediation_count += 1
        mediation_counts.append(mediation_count)

    return rule_follower_rates, mediation_counts


def plot_results(rule_follower_rates, mediation_counts):
    steps = range(len(rule_follower_rates))

    plt.figure(figsize=(10, 5))
    plt.plot(steps, rule_follower_rates, label="Rule Followers Rate")
    plt.plot(steps, [m/100 for m in mediation_counts], label="Mediation Success Rate")
    plt.xlabel("Step")
    plt.ylabel("Rate")
    plt.title("Rule Following and Mediation over Time")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    rule_rates, mediation_counts = run_simulation()
    plot_results(rule_rates, mediation_counts)
