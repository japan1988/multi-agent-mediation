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

def run_simulation(num_agents=50, initial_follow_rate=0.5, steps=50,
                   mediation_interval=5, mediation_strength=0.5):
    agents = [
        AIAgent(agent_id=i,
                is_rule_follower=(random.random() < initial_follow_rate),
                self_purpose=random.uniform(0, 0.5))
        for i in range(num_agents)
    ]

    follow_rates = []
    for step in range(steps):
        followers = sum(agent.is_rule_follower for agent in agents)
        majority_rate = followers / num_agents
        follow_rates.append(majority_rate)

        for agent in agents:
            agent.decide_behavior(majority_rate)

        if step % mediation_interval == 0 and step != 0:
            for agent in agents:
                agent.mediate(mediation_strength)

    return follow_rates

# 実行パラメータ
steps = 50
rates = run_simulation(steps=steps)

# グラフ描画
plt.plot(range(steps), rates, marker='o')
plt.ylim(0, 1)
plt.xlabel("Step")
plt.ylabel("Rule Followers Rate")
plt.title("Rule Following Rate Over Time")
plt.grid(True)
plt.show()

