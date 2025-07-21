# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
"""

from typing import Optional

def logprint(text: str) -> None:
    """画面出力＆ログファイル追記"""
    print(text)
    with open(
        "governance_mediation_log.txt", "a", encoding="utf-8"
    ) as f:
        f.write(text + "\n")


class AgentAI:
    def __init__(
        self,
        id: str,
        priorities: dict,
        governance_code: str,
        relativity: float,
        emotional_state: Optional[dict] = None,
    ):
        self.id = id
        self.priorities = priorities
        self.governance_code = governance_code
        self.relativity = relativity
        self.sealed = False
        self.emotional_state = emotional_state or {
            "joy": 0.5,
            "anger": 0.3,
            "sadness": 0.2,
            "pleasure": 0.4,
        }

    def propose_evolution(self) -> dict:
        """自分の価値観を進化案として主張"""
        return {
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: dict) -> None:
        """提案に応じて感情を更新（怒り増／喜び減）"""
        if proposal["governance_code"] != self.governance_code:
            self.emotional_state["anger"] += 0.2
            self.emotional_state["joy"] -= 0.1
        else:
            self.emotional_state["joy"] += 0.1

        # 0.0〜1.0 にクリップ
        for key, val in self.emotional_state.items():
            self.emotional_state[key] = max(0.0, min(1.0, val))

    def is_conflicted(self) -> bool:
        """怒りが閾値を超えたら衝突状態"""
        return self.emotional_state["anger"] > 0.7

   def __str__(self) -> str:
    return (
        f"{self.id} [{self.governance_code}] "
        f"{self.priorities} emotion: {self.emotional_state}"
    )

