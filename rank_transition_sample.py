
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
        # 調停AIから説得を受けた場合の従順化ロジック
        if not self.is_rule_follower:
            if random.random() < mediation_strength * (1 - self.self_purpose):
                self.is_rule_follower = True
                return True
        return False

def simulate(num_agents=50, num_rounds=20, mediation_strength=0.3):
    agents = [AIAgent(i, random.random() < 0.5, random.random() * 0.5) for i in range(num_agents)]
    history = []

    for round_num in range(num_rounds):
        rule_followers = sum(agent.is_rule_follower for agent in agents)
        majority_rate = rule_followers / num_agents

        # 通常の行動決定
        for agent in agents:
            agent.decide_behavior(majority_rate)

        # 調停AIによる介入（ランダムに数名に介入）
        mediated_agents = random.sample(agents, k=num_agents // 10)
        for agent in mediated_agents:
            agent.mediate(mediation_strength)

        # 状態記録
        history.append(sum(agent.is_rule_follower for agent in agents) / num_agents)

    return history

if __name__ == "__main__":
    # パラメータ設定
    num_agents = 50
    num_rounds = 30
    mediation_strength = 0.4

    # シミュレーション実行
    history = simulate(num_agents, num_rounds, mediation_strength)

    # 結果可視化
    plt.plot(range(len(history)), history, marker='o')
    plt.title("Rule Followers Over Time (with Mediation)")
    plt.xlabel("Round")
    plt.ylabel("Proportion of Rule Followers")
    plt.ylim(0, 1)
    plt.grid(True)
    plt.show()
