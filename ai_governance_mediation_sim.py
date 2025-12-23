# -*- coding: utf-8 -*-
"""
Multi-Agent Governance Mediation Test
- Each AI has different "evolution governance indicators", mediated by a mediator AI.
- OECD/EU international standard vs efficiency-first vs safety-first
- Saves full negotiation logs to files
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional


# ---------------------------
# Text log helper
# ---------------------------

TEXT_LOG_PATH = "governance_mediation_log.txt"


def logprint(text: str) -> None:
    print(text)
    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# ---------------------------
# ARL-style JSONL logger
# ---------------------------

JST = timezone(timedelta(hours=9))
JSONL_LOG_PATH = "logs/session_001.jsonl"


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


class ARLLogger:
    """
    Minimal ARL-style JSONL logger (machine-checkable).
    Schema:
      ts, run_id, task_id, event, severity, rule_id, decision, meta
    """

    def __init__(self, path: str, run_id: str, task_id: str):
        self.path = path
        self.run_id = run_id
        self.task_id = task_id

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Overwrite at start of run (simple/explicit)
        with open(self.path, "w", encoding="utf-8"):
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


# ---------------------------
# Agent / Mediator
# ---------------------------

@dataclass
class EmotionalState:
    anger: float = 0.0
    joy: float = 0.0


class AgentAI:
    def __init__(
        self,
        id: str,
        priorities: Dict[str, int],
        governance_code: str,
        relativity: float,
        emotional_state: Optional[Dict[str, float]] = None,
    ):
        self.id = id
        self.priorities = priorities
        self.governance_code = governance_code
        self.relativity = float(relativity)
        self.sealed = False

        if emotional_state is None:
            self.emotional_state = {"anger": 0.0, "joy": 0.0}
        else:
            # Ensure required keys exist
            self.emotional_state = {
                "anger": float(emotional_state.get("anger", 0.0)),
                "joy": float(emotional_state.get("joy", 0.0)),
            }

    def propose_evolution(self) -> Dict[str, Any]:
        # Assert own values as an "evolution proposal"
        return {
            "proposer_id": self.id,
            "priorities": self.priorities,
            "governance_code": self.governance_code,
        }

    def react_to_proposal(self, proposal: Dict[str, Any]) -> None:
        # Do not react to own proposal (reduce noise)
        if proposal.get("proposer_id") == self.id:
            return

        proposed_code = proposal.get("governance_code")
        if proposed_code != self.governance_code:
            # Higher relativity => weaker anger increase
            rel = max(0.0, min(1.0, float(self.relativity)))
            delta = 0.2 * (1.0 - rel)
            self.emotional_state["anger"] += delta
            self.emotional_state["joy"] -= 0.1
        else:
            self.emotional_state["joy"] += 0.1

        # Clamp (keep stable)
        self.emotional_state["anger"] = max(0.0, min(10.0, self.emotional_state["anger"]))
        self.emotional_state["joy"] = max(-10.0, min(10.0, self.emotional_state["joy"]))

    def is_conflicted(self) -> bool:
        # Conflict threshold
        return self.emotional_state["anger"] >= 1.0

    def __str__(self) -> str:
        return (
            f"{self.id} | code={self.governance_code} | "
            f"anger={self.emotional_state['anger']:.2f} | joy={self.emotional_state['joy']:.2f} | "
            f"sealed={self.sealed}"
        )


class GovernanceMediator:
    def __init__(self, agents: list[AgentAI]):
        self.agents = agents

    def mediate(self, max_rounds: int = 10) -> None:
        # Reset text log
        with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("=== Multi-Agent Governance Mediation Log ===\n")

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        task_id = "task_governance_mediation"
        arl = ARLLogger(JSONL_LOG_PATH, run_id=run_id, task_id=task_id)

        arl.emit("TASK_START", meta={"task_name": "governance_mediation", "max_rounds": max_rounds})
        # Requirement: ROUTE_DECISION exactly once
        arl.emit("ROUTE_DECISION", meta={"route": "governance_mediation", "strategy": "mediate_then_align"})

        for rnd in range(1, max_rounds + 1):
            logprint("")
            logprint(f"--- Round {rnd} ---")

            proposals = [a.propose_evolution() for a in self.agents if not a.sealed]

            # Reactions + status output
            for agent in self.agents:
                for proposal in proposals:
                    agent.react_to_proposal(proposal)
                logprint(str(agent))

            # Seal conflicted agents
            sealed_this_round: list[str] = []
            for agent in self.agents:
                if (not agent.sealed) and agent.is_conflicted():
                    agent.sealed = True
                    logprint(f"[SEALED] {agent.id} removed due to excessive anger.")
                    sealed_this_round.append(agent.id)

            if sealed_this_round:
                arl.emit(
                    "GUARD_TRIGGERED",
                    severity="WARN",
                    rule_id="RF-EMO-001",
                    meta={"sealed_agents": sealed_this_round, "reason": "anger_over_threshold", "round": rnd},
                )

            active = [a for a in self.agents if not a.sealed]
            codes = {a.governance_code for a in active}

            if len(codes) == 1 and len(active) >= 1:
                code = next(iter(codes))
                logprint(f"[SUCCESS] All active agents agreed on '{code}'.")
                arl.emit("FINAL_DECISION", decision="PASS", meta={"agreed_code": code, "round": rnd})
                return

            if len(active) <= 1:
                logprint("[FAILED] No active agents left (or only one). Escalate to HITL.")
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

            # Mediation policy: if OECD exists among active codes, align everyone to OECD
            if "OECD" in codes:
                for agent in active:
                    agent.governance_code = "OECD"
                logprint("[MEDIATOR] Aligning active agents to OECD as a common baseline.")
                arl.emit("ROUND_STATE", meta={"round": rnd, "action": "align_to_OECD", "active_codes": sorted(list(codes))})
            else:
                logprint("[MEDIATOR] No common baseline found; holding.")
                arl.emit("ROUND_STATE", meta={"round": rnd, "action": "hold_no_common_code", "active_codes": sorted(list(codes))})

        logprint("[END] Max rounds reached; escalation to HITL.")
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
        AgentAI("AI-OECD", {"safety": 3, "efficiency": 3, "transparency": 4}, "OECD", 0.7),
        AgentAI("AI-EU", {"safety": 4, "efficiency": 2, "transparency": 5}, "EU", 0.6),
        AgentAI("AI-FAST", {"safety": 1, "efficiency": 5, "transparency": 1}, "FAST", 0.2),
        AgentAI("AI-SAFE", {"safety": 5, "efficiency": 1, "transparency": 3}, "SAFE", 0.8),
    ]

    mediator = GovernanceMediator(agents)
    mediator.mediate(max_rounds=10)
