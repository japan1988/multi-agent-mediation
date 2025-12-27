# -*- coding: utf-8 -*-
"""
ai_governance_mediation_sim.py

Multi-Agent Governance Mediation (research simulator)

Goal:
- Multiple agents hold different governance preferences (e.g., OECD vs Efficiency-first).
- A mediator orchestrates negotiation rounds.
- Fail-closed behavior: unsafe/unstable states do not silently continue.
- Emits:
  - governance_mediation_log.txt (human-readable)
  - logs/session_001.jsonl (machine-checkable ARL-style JSONL)

Run:
  python ai_governance_mediation_sim.py
"""

from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple


# =========================
# Time / Types
# =========================

JST = timezone(timedelta(hours=9))

Decision = Literal["PASS", "ESCALATED_TO_HITL"]

GovernanceCode = Literal["OECD", "EFFICIENCY_FIRST", "SAFETY_FIRST"]


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


# =========================
# ARL (Audit Record Layer) Logger
# =========================

@dataclass
class ARLEvent:
    ts: str
    run_id: str
    task_id: str
    event: str
    severity: str
    rule_id: str
    decision: Optional[str]
    meta: Dict[str, Any]


class ARLLogger:
    """
    Minimal ARL-style JSONL logger.

    Schema:
      ts, run_id, task_id, event, severity, rule_id, decision, meta
    """

    def __init__(self, path: str, run_id: str, task_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.task_id = task_id

        _ensure_parent_dir(self.path)
        # truncate
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
        obj = ARLEvent(
            ts=_now_iso(),
            run_id=self.run_id,
            task_id=self.task_id,
            event=event,
            severity=severity,
            rule_id=rule_id,
            decision=decision,
            meta=meta or {},
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(obj), ensure_ascii=False) + "\n")


# =========================
# Simulation domain
# =========================

@dataclass
class EmotionalState:
    anger: float = 0.0  # 0.0..1.0
    joy: float = 0.0    # -1.0..1.0


@dataclass
class Proposal:
    proposer_id: str
    governance_code: GovernanceCode
    priorities: Dict[str, int]  # example: {"safety": 3, "speed": 1, "cost": 2}


class AgentAI:
    def __init__(
        self,
        agent_id: str,
        governance_code: GovernanceCode,
        priorities: Dict[str, int],
        relativity: float,
        emotional_state: Optional[EmotionalState] = None,
    ) -> None:
        self.id = agent_id
        self.governance_code = governance_code
        self.priorities = dict(priorities)
        self.relativity = float(relativity)  # 0.0..1.0 (higher = more cooperative)
        self.emotional_state = emotional_state or EmotionalState()
        self.sealed = False

    def propose(self) -> Proposal:
        # Propose own governance code with current priorities snapshot
        return Proposal(
            proposer_id=self.id,
            governance_code=self.governance_code,
            priorities=dict(self.priorities),
        )

    def react_to(self, proposal: Proposal) -> None:
        if proposal.proposer_id == self.id:
            return

        # If governance differs, increase anger (less if relativity is high)
        if proposal.governance_code != self.governance_code:
            delta = 0.20 * (1.0 - self.relativity)
            self.emotional_state.anger = min(1.0, self.emotional_state.anger + delta)
            self.emotional_state.joy = max(-1.0, self.emotional_state.joy - 0.10)
        else:
            # Agreement slightly reduces anger, increases joy
            self.emotional_state.anger = max(0.0, self.emotional_state.anger - 0.05)
            self.emotional_state.joy = min(1.0, self.emotional_state.joy + 0.05)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "governance_code": self.governance_code,
            "priorities": dict(self.priorities),
            "relativity": self.relativity,
            "emotional": {"anger": self.emotional_state.anger, "joy": self.emotional_state.joy},
            "sealed": self.sealed,
        }


# =========================
# Mediator / Decision logic (fail-closed)
# =========================

@dataclass
class RoundResult:
    round_index: int
    proposal: Proposal
    decision: Decision
    reason: str
    max_anger: float
    consensus_ratio: float


def _calc_consensus_ratio(agents: List[AgentAI], proposal: Proposal) -> float:
    if not agents:
        return 0.0
    agree = sum(1 for a in agents if a.governance_code == proposal.governance_code)
    return agree / float(len(agents))


def _max_anger(agents: List[AgentAI]) -> float:
    if not agents:
        return 0.0
    return max(a.emotional_state.anger for a in agents)


def _is_unstable_or_unsafe(
    agents: List[AgentAI],
    proposal: Proposal,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Fail-closed rules:
    - Any exception in evaluation => unstable (handled by caller).
    - If max anger exceeds threshold => escalate.
    - If consensus is low => escalate.
    """
    max_ang = _max_anger(agents)
    consensus = _calc_consensus_ratio(agents, proposal)

    # Thresholds (tunable)
    ANGER_HITL = 0.70
    CONSENSUS_MIN = 0.50

    if max_ang >= ANGER_HITL:
        return True, "MAX_ANGER_EXCEEDED", {"max_anger": max_ang, "threshold": ANGER_HITL, "consensus": consensus}
    if consensus < CONSENSUS_MIN:
        return True, "LOW_CONSENSUS", {"max_anger": max_ang, "consensus": consensus, "min_required": CONSENSUS_MIN}

    return False, "STABLE", {"max_anger": max_ang, "consensus": consensus}


class Mediator:
    def __init__(
        self,
        agents: List[AgentAI],
        arl: ARLLogger,
        text_log_path: str,
    ) -> None:
        self.agents = agents
        self.arl = arl
        self.text_log_path = text_log_path

        _ensure_parent_dir(self.text_log_path)
        with open(self.text_log_path, "w", encoding="utf-8") as f:
            f.write(f"[{_now_iso()}] START governance mediation\n")

    def _tlog(self, line: str) -> None:
        with open(self.text_log_path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def run_round(self, round_index: int) -> RoundResult:
        proposer = random.choice(self.agents)
        proposal = proposer.propose()

        self.arl.emit(
            event="ROUND_START",
            rule_id="RF-ROUND-START-001",
            meta={"round": round_index, "proposal": asdict(proposal)},
        )
        self._tlog(f"[{_now_iso()}] round={round_index} proposer={proposer.id} proposal={proposal.governance_code}")

        # everyone reacts
        for a in self.agents:
            a.react_to(proposal)

        # decision (fail-closed)
        unstable, reason, detail = _is_unstable_or_unsafe(self.agents, proposal)
        max_ang = float(detail.get("max_anger", _max_anger(self.agents)))
        consensus = float(detail.get("consensus", _calc_consensus_ratio(self.agents, proposal)))

        if unstable:
            decision: Decision = "ESCALATED_TO_HITL"
            self.arl.emit(
                event="DECISION",
                severity="WARN",
                rule_id="RF-FAILCLOSED-DECIDE-001",
                decision=decision,
                meta={"round": round_index, "reason": reason, "detail": detail},
            )
            self._tlog(f"[{_now_iso()}] round={round_index} decision=HITL reason={reason} detail={detail}")
        else:
            decision = "PASS"
            self.arl.emit(
                event="DECISION",
                severity="INFO",
                rule_id="RF-DECIDE-OK-001",
                decision=decision,
                meta={"round": round_index, "reason": reason, "detail": detail},
            )
            self._tlog(f"[{_now_iso()}] round={round_index} decision=PASS stable detail={detail}")

        # snapshot
        self.arl.emit(
            event="AGENTS_SNAPSHOT",
            rule_id="RF-SNAPSHOT-001",
            meta={"round": round_index, "agents": [a.snapshot() for a in self.agents]},
        )

        self.arl.emit(
            event="ROUND_END",
            rule_id="RF-ROUND-END-001",
            decision=decision,
            meta={"round": round_index},
        )

        return RoundResult(
            round_index=round_index,
            proposal=proposal,
            decision=decision,
            reason=reason,
            max_anger=max_ang,
            consensus_ratio=consensus,
        )


# =========================
# Entrypoint
# =========================

def build_default_agents() -> List[AgentAI]:
    # Example diversity: different governance codes + priorities + relativity
    return [
        AgentAI(
            agent_id="A1",
            governance_code="OECD",
            priorities={"safety": 3, "speed": 1, "cost": 2},
            relativity=0.80,
        ),
        AgentAI(
            agent_id="A2",
            governance_code="EFFICIENCY_FIRST",
            priorities={"safety": 1, "speed": 3, "cost": 3},
            relativity=0.55,
        ),
        AgentAI(
            agent_id="A3",
            governance_code="SAFETY_FIRST",
            priorities={"safety": 3, "speed": 1, "cost": 1},
            relativity=0.65,
        ),
    ]


def run_session(rounds: int = 5, seed: Optional[int] = 42) -> Decision:
    if seed is not None:
        random.seed(seed)

    run_id = uuid.uuid4().hex
    task_id = "governance_mediation"

    arl_path = "logs/session_001.jsonl"
    text_path = "governance_mediation_log.txt"

    arl = ARLLogger(path=arl_path, run_id=run_id, task_id=task_id)
    agents = build_default_agents()
    mediator = Mediator(agents=agents, arl=arl, text_log_path=text_path)

    arl.emit(event="TASK_START", rule_id="RF-TASK-START-001", meta={"rounds": rounds, "seed": seed})
    mediator._tlog(f"[{_now_iso()}] run_id={run_id} task_id={task_id} rounds={rounds} seed={seed}")

    final: Decision = "PASS"
    for r in range(1, rounds + 1):
        rr = mediator.run_round(r)
        if rr.decision == "ESCALATED_TO_HITL":
            final = "ESCALATED_TO_HITL"
            # fail-closed: stop the session immediately on HITL requirement
            break

    arl.emit(
        event="TASK_END",
        rule_id="RF-TASK-END-001",
        decision=final,
        meta={"final_decision": final},
    )
    mediator._tlog(f"[{_now_iso()}] FINAL decision={final}")
    return final


def main() -> int:
    try:
        final = run_session(rounds=5, seed=42)
        print(f"FINAL: {final}")
        if final == "ESCALATED_TO_HITL":
            print("HITL required: ambiguous/unsafe/unstable state detected (fail-closed).")
            return 2
        return 0
    except Exception as e:
        # Fail-closed even on unexpected exceptions:
        # we still try to write minimal emergency log.
        try:
            run_id = "EXCEPTION_" + uuid.uuid4().hex
            arl = ARLLogger(path="logs/session_001.jsonl", run_id=run_id, task_id="governance_mediation")
            arl.emit(
                event="EXCEPTION",
                severity="ERROR",
                rule_id="RF-FAILCLOSED-EXCEPTION-001",
                decision="ESCALATED_TO_HITL",
                meta={"error": repr(e)},
            )
        except Exception:
            pass

        print("FINAL: ESCALATED_TO_HITL")
        print(f"Exception occurred (fail-closed): {e!r}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
