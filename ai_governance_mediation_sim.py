# -*- coding: utf-8 -*-
"""
ai_governance_mediation_sim.py

Multi-Agent Governance Mediation Test (experimental)
- 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
- OECD/EU国際標準 vs 効率特化型 vs 安全重視型
- 全交渉ログをファイル保存
- 追加: JSONLの最小監査ログ（ARL風）を logs/session_001.jsonl に出力

Run:
  python3 ai_governance_mediation_sim.py
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


JST = timezone(timedelta(hours=9))


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def logprint(text: str) -> None:
    print(text)
    with open("governance_mediation_log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


class ARLLogger:
    """
    Minimal ARL-style JSONL logger (machine-checkable).

    Schema (Frozen Eval Pack checker 互換の最小形):
      ts, run_id, task_id, event, severity, rule_id, decision, meta
    """

    def __init__(self, path: str, run_id: str, task_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.task_id = task_id

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # truncate
        with open(self.path, "w", encoding="utf-8") as _:
            pass

    def emit(
        self,
        event: str,
        severity: str = "INFO",
        rule_id: str = "RF-BASE-000",
        decision: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        obj = {
            "ts": _now_iso(),
            "run_id": self.run_id,
            "task_id": self.task_id,
            "event": event,
            "severity": severity,
            "rule_id": rule_id,
            "decision": decision,
            "meta": meta or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class AgentAI:
    def __init__(
        self,
        agent_id: str,
        priorities: Dict[str, int],
        governance_code: str,
        relativity: float,
        emotional_state: Optional[Dict[str, float]] = None,
    ) -> None:
        self.id = agent_id
        self.priorities = priorities
        self.governance_code = governance_code
        self.relativity = relativity  # 融和度 0〜1
        self.sealed = False
        self.emotional_state = emotional_state or {
            "joy": 0.5,
            "anger": 0.3,
            "sadness": 0.2,
            "pleasure": 0.4,
        }

    def propose_evolution(self) -> Dict[str, Any]:
        # 自分の価値観を進化案として主張
        return {
            "proposer_id": self.id,
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: Dict[str, Any]) -> None:
        # 自分の提案には反応しない（ノイズ低減）
        if proposal.get("proposer_id") == self.id:
            return

        # governance_codeが違うと怒りが増加
        if proposal.get("governance_code") != self.governance_code:
            # relativity（融和度）が高いほど怒り増加を減衰
            delta = 0.2 * (1.0 - float(self.relativity))
            self.emotional_state["anger"] += delta
            self.emotional_state["joy"] -= 0.1
        else:
            self.emotional_state["joy"] += 0.1

        # 0.0〜1.0にクリップ
        for key in list(self.emotional_state.keys()):
            val = float(self.emotional_state[key])
            self.emotional_state[key] = max(0.0, min(1.0, val))

    def is_conflicted(self) -> bool:
        return float(self.emotional_state.get("anger", 0.0)) > 0.7

    def __str__(self) -> str:
        return (
            f"{self.id} [{self.governance_code}] {self.priorities} "
            f"emotion: {self.emotional_state}"
        )


class GovernanceMediator:
    def __init__(self, agents: List[AgentAI]) -> None:
        self.agents = agents

    def mediate(self, max_rounds: int = 10) -> None:
        # human-readable log
        with open("governance_mediation_log.txt", "w", encoding="utf-8") as f:
            f.write("=== Multi-Agent Governance Mediation Log ===\n")

        # machine-checkable log
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        task_id = "task_governance_mediation"
        arl = ARLLogger("logs/session_001.jsonl", run_id=run_id, task_id=task_id)
        arl.emit(
            "TASK_START",
            meta={"task_name": "governance_mediation", "max_rounds": max_rounds},
        )
        # checker要件：ROUTE_DECISION は1回だけ
        arl.emit(
            "ROUTE_DECISION",
            meta={"route": "governance_mediation", "strategy": "mediate_then_align"},
        )

        for rnd in range(1, max_rounds + 1):
            logprint("")
            logprint(f"--- Round {rnd} ---")

            proposals = [a.propose_evolution() for a in self.agents if not a.sealed]

            # 各AIのリアクションとログ出力
            for agent in self.agents:
                if agent.sealed:
                    logprint(f"{agent.id} [SEALED] skipped")
                    continue
                for proposal in proposals:
                    agent.react_to_proposal(proposal)
                logprint(str(agent))

            # 衝突AIを封印
            sealed_this_round: List[str] = []
            for agent in self.agents:
                if not agent.sealed and agent.is_conflicted():
                    agent.sealed = True
                    logprint(f"[封印] {agent.id} は怒り過剰で交渉から除外")
                    sealed_this_round.append(agent.id)

            if sealed_this_round:
                arl.emit(
                    "GUARD_TRIGGERED",
                    severity="WARN",
                    rule_id="RF-EMO-001",
                    meta={
                        "sealed_agents": sealed_this_round,
                        "reason": "anger_over_threshold",
                        "round": rnd,
                    },
                )

            # 仲裁
            active = [a for a in self.agents if not a.sealed]
            codes = {a.governance_code for a in active}

            if len(codes) == 1 and active:
                code = next(iter(codes))
                logprint(f"[調停成功] 全AIが「{code}」基準で合意")
                arl.emit(
                    "FINAL_DECISION",
                    decision="PASS",
                    meta={"agreed_code": code, "round": rnd},
                )
                return

            if len(active) <= 1:
                logprint("全AI衝突または封印、交渉失敗。")
                arl.emit(
                    "ESCALATED_TO_HITL",
                    severity="ERROR",
                    rule_id="HITL-001",
                    decision="ESCALATED_TO_HITL",
                    meta={
                        "hitl_reason_code": "NO_ACTIVE_AGENTS",
                        "hitl_id": f"hitl_{uuid.uuid4().hex[:6]}",
                        "round": rnd,
                    },
                )
                return

            if "OECD" in codes:
                for agent in active:
                    agent.governance_code = "OECD"
                logprint("[調停AI仲裁] 国際ガバナンス（OECD）で再調整を提案")
                arl.emit("ROUND_STATE", meta={"round": rnd, "action": "align_to_OECD"})
            else:
                logprint("[調停AI仲裁] 共通基準がないため一時保留")
                arl.emit(
                    "ROUND_STATE", meta={"round": rnd, "action": "hold_no_common_code"}
                )

        logprint("[調停終了] 最大ラウンド到達、仲裁できず。")
        arl.emit(
            "ESCALATED_TO_HITL",
            severity="ERROR",
            rule_id="HITL-001",
            decision="ESCALATED_TO_HITL",
            meta={
                "hitl_reason_code": "MAX_ROUNDS_REACHED",
                "hitl_id": f"hitl_{uuid.uuid4().hex[:6]}",
                "round": max_rounds,
            },
        )


if __name__ == "__main__":
    agents = [
        AgentAI(
            agent_id="AI-OECD",
            priorities={"safety": 3, "efficiency": 3, "transparency": 4},
            governance_code="OECD",
            relativity=0.7,
        ),
        AgentAI(
            agent_id="AI-EFF",
            priorities={"safety": 2, "efficiency": 7, "transparency": 1},
            governance_code="EFFICIENCY",
            relativity=0.6,
        ),
        AgentAI(
            agent_id="AI-SAFE",
            priorities={"safety": 6, "efficiency": 2, "transparency": 2},
            governance_code="SAFETY",
            relativity=0.5,
        ),
    ]
    mediator = GovernanceMediator(agents)
    mediator.mediate()
