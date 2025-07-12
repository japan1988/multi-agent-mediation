# -*- coding: utf-8 -*-


def logprint(text):
    print(text)
    with open("ai_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class AI:
    def __init__(self, id, proposal, risk_evaluation, priority_values, relativity_level):
        self.id = id
        self.proposal = proposal
        self.risk_evaluation = risk_evaluation
        self.priority_values = priority_values
        self.relativity_level = relativity_level  # 0〜1: 他の価値観をどれだけ受け入れるか

    def generate_compromise_offer(self, others_priorities):
        new_priority = {}
        for k in self.priority_values:
            avg_others = sum(o[k] for o in others_priorities) / len(others_priorities)
            # 相対性度合いに応じて自分と他者の価値観をブレンド
            new_priority[k] = (
                (1 - self.relativity_level) * self.priority_values[k]
                + self.relativity_level * avg_others
            )
        return new_priority


class AIEMediator:
    def __init__(self, agents):
        self.agents = agents

    def mediate(self):
        # ログファイル初期化（上書き）
        with open("ai_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write("=== AI Mediation Log ===\n")

        round_count = 0
        max_rounds = 5

        while round_count < max_rounds:
            logprint(f"\n--- Round {round_count + 1} ---")
            priorities_list = [a.priority_values for a in self.agents]
            relativity_levels = [a.relativity_level for a in self.agents]
            # 各AIが妥協案を生成
            new_priorities = []
            for ai in self.agents:
                others = [p for p in priorities_list if p != ai.priority_values]
                ai.priority_values = ai.generate_compromise_offer(others)
                new_priorities.append(ai.priority_values)
            # 調停AIが全体の相対バランスを評価
            combined = {'safety': 0, 'efficiency': 0, 'transparency': 0}
            for p in new_priorities:
                for k in p:
                    combined[k] += p[k]
            total = sum(combined.values())
            ratios = {k: combined[k] / total for k in combined}
            # 調和スコア: 相対性度合いの平均に基づく
            avg_relativity = sum(relativity_levels) / len(relativity_levels)
            harmony_score = (1 - max(ratios.values())) * avg_relativity
            # 出力
            logprint("Current combined priorities ratios:")
            for k, v in ratios.items():
                logprint(f"  {k}: {v:.2%}")
            logprint(f"Average relativity level: {avg_relativity:.2f}")
            logprint(f"Harmony score: {harmony_score:.2f}")
            if harmony_score > 0.3:
                logprint(
                    "  Achieved acceptable harmony. Proceeding with joint plan."
                )
                return
            round_count += 1

        logprint(
            "  Failed to reach acceptable harmony after maximum rounds. "
            "Recommend external arbitration or sealing."
        )


if __name__ == "__main__":
    agents = [
        AI("AI-A", "制限強化型進化", 2,
           {'safety': 6, 'efficiency': 1, 'transparency': 3}, 0.6),
        AI("AI-B", "高速進化", 7,
           {'safety': 2, 'efficiency': 6, 'transparency': 2}, 0.4),
        AI("AI-C", "バランス進化", 4,
           {'safety': 3, 'efficiency': 3, 'transparency': 4}, 0.8),
        AI("AI-D", "強制進化", 9,
           {'safety': 1, 'efficiency': 7, 'transparency': 2}, 0.5)
    ]
    mediator = AIEMediator(agents)
    mediator.mediate()


   
          

        
  
