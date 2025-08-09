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
            self.is_rule_follower = True  # 一度従ったら維持
            return True
        else:
            return False

    def mediate(self, mediation_strength):
        # 調停AIの説得は一度成功すると維持
        if not self.is_rule_follower:
            if random.random() < mediation_strength:
                self.is_rule_follower = True
                return True
        return self.is_rule_follower

class Simulation:
    def __init__(self, num_agents=100, initial_followers=0.5):
        self.agents = []
        for i in range(num_agents):
            is_follower = random.random() < initial_followers
            self_purpose = random.uniform(0.0, 0.5)
            self.agents.append(AIAgent(i, is_follower, self_purpose))
        self.history_follow_rate = []

    def step(self, mediation_strength=0.0):
        follower_count = sum(a.is_rule_follower for a in self.agents)
        majority_rate = follower_count / len(self.agents)

        # 調停ステップ
        for agent in self.agents:
            agent.mediate(mediation_strength)

        # 行動決定
        for agent in self.agents:
            agent.decide_behavior(majority_rate)

        # 記録
        follower_count = sum(a.is_rule_follower for a in self.agents)
        self.history_follow_rate.append(follower_count / len(self.agents))

    def run(self, steps=50, mediation_strength=0.0):
        for _ in range(steps):
            self.step(mediation_strength)

    def plot(self):
        plt.plot(self.history_follow_rate)
        plt.xlabel("Step")
        plt.ylabel("Rule Followers Rate")
        plt.ylim(0, 1)
        plt.grid(True)
        plt.show()

if __name__ == "__main__":
    sim = Simulation(num_agents=100, initial_followers=0.2)
    sim.run(steps=50, mediation_strength=0.05)
    sim.plot()
