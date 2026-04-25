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


Multi-Agent Governance Mediation Test
- Each AI has different "evolution governance indicators", mediated by a mediator AI.
- OECD/EU international standard vs efficiency-first vs safety-first
- Saves full negotiation logs to files

ai_governance_mediation_sim.py
Multi-Agent Governance Mediation (research simulator)

Goal:
- Multiple agents hold different governance preferences (e.g., OECD vs Efficiency-first).
- A mediator orchestrates negotiation rounds.
- Fail-closed behavior: unsafe/unstable states do not silently continue.

Emits:
- governance_mediation_log_<run_id>.txt (human-readable)
- logs/<run_id>.jsonl (machine-checkable ARL-style JSONL)
- logs/<run_id>.exceptions.jsonl (exception-only, append-only)

Run:
  python ai_governance_mediation_sim.py


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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


LOG_PATH = Path("governance_mediation_log.txt")

PriorityMap = Dict[str, int]
EmotionState = Dict[str, float]

DEFAULT_EMOTIONAL_STATE: EmotionState = {
    "joy": 0.5,
    "anger": 0.3,
    "sadness": 0.2,
    "pleasure": 0.4,
}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def init_log(log_path: Path = LOG_PATH) -> None:
    log_path.write_text(
        "=== Multi-Agent Governance Mediation Log ===\n",
        encoding="utf-8",
    )


def logprint(text: str, log_path: Path = LOG_PATH) -> None:
    print(text)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


import hashlib
import json
import os
import sys
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



class ARLLogger:
    """
    Minimal ARL-style JSONL logger (machine-checkable).
    Schema:
      ts, run_id, task_id, event, severity, rule_id, decision, meta
    """

    def __init__(self, path: str, run_id: str, task_id: str):

def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _stable_index(*, run_id: str, round_index: int, seed: Optional[int], size: int) -> int:
    """
    Deterministic selector for simulation use.

    This intentionally avoids the standard `random` module so Bandit B311 does not fire.
    It is not a cryptographic decision function; it is only a reproducible round selector
    for a research simulator.
    """
    if size <= 0:
        raise ValueError("size must be >= 1")

    seed_text = "none" if seed is None else str(seed)
    payload = f"{run_id}|{round_index}|{seed_text}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    value = int.from_bytes(digest[:8], "big", signed=False)
    return value % size


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

    Safety notes:
      - Normal run may truncate (fresh log for that run).
      - Exception paths must never truncate.
    """

    def __init__(self, path: str, run_id: str, task_id: str, *, truncate: bool = True) -> None:


        self.path = path
        self.run_id = run_id
        self.task_id = task_id


        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # truncate
        with open(self.path, "w", encoding="utf-8") as _:
            pass



        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Overwrite at start of run (simple/explicit)
        with open(self.path, "w", encoding="utf-8"):
            pass

        _ensure_parent_dir(self.path)

        if truncate:
            with open(self.path, "w", encoding="utf-8"):
                pass
        else:
            with open(self.path, "a", encoding="utf-8"):
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



@dataclass
class AgentAI:

    agent_id: str
    priorities: PriorityMap
    governance_code: str
    relativity: float
    emotional_state: EmotionState = field(default_factory=lambda: DEFAULT_EMOTIONAL_STATE.copy())
    sealed: bool = False

    def propose_evolution(self) -> Dict[str, object]:
        return {


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

    def react_to_proposal(self, proposal: Dict[str, object]) -> None:
        proposal_code = str(proposal.get("governance_code", ""))

        if proposal_code != self.governance_code:
            self.emotional_state["anger"] = clamp(self.emotional_state["anger"] + 0.2)
            self.emotional_state["joy"] = clamp(self.emotional_state["joy"] - 0.1)
        else:
            self.emotional_state["joy"] = clamp(self.emotional_state["joy"] + 0.1)

        for key, value in list(self.emotional_state.items()):
            self.emotional_state[key] = clamp(value)

    def is_conflicted(self) -> bool:
        return self.emotional_state.get("anger", 0.0) > 0.7

    def __str__(self) -> str:
        return (
            f"{self.agent_id} [{self.governance_code}] "
            f"{self.priorities} emotion: {self.emotional_state}"


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


            # 各AIのリアクションとログ出力
            for agent in self.agents:
                if agent.sealed:
                    logprint(f"{agent.id} [SEALED] skipped")
                    continue

            # Reactions + status output
            for agent in self.agents:

                for proposal in proposals:
                    agent.react_to_proposal(proposal)
                logprint(str(agent))


            # 衝突AIを封印
            sealed_this_round: List[str] = []
            for agent in self.agents:
                if not agent.sealed and agent.is_conflicted():
                    agent.sealed = True
                    logprint(f"[封印] {agent.id} は怒り過剰で交渉から除外")

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

    def __init__(self, agents: List[AgentAI], log_path: Path = LOG_PATH) -> None:
        self.agents = agents
        self.log_path = log_path

    def active_agents(self) -> List[AgentAI]:
        return [agent for agent in self.agents if not agent.sealed]

    def mediate(self, max_rounds: int = 10) -> bool:
        init_log(self.log_path)

        for rnd in range(1, max_rounds + 1):
            logprint("", self.log_path)
            logprint(f"--- Round {rnd} ---", self.log_path)

            active_before_round = self.active_agents()
            proposals = [agent.propose_evolution() for agent in active_before_round]

            for agent in self.agents:
                if agent.sealed:
                    logprint(f"{agent.agent_id} [SEALED] negotiation skipped", self.log_path)
                    continue

                for proposal in proposals:
                    agent.react_to_proposal(proposal)

                logprint(str(agent), self.log_path)

            for agent in self.agents:
                if not agent.sealed and agent.is_conflicted():
                    agent.sealed = True
                    logprint(
                        f"[封印] {agent.agent_id} は怒り過剰で交渉から除外",
                        self.log_path,
                    )

            active_after_round = self.active_agents()
            active_codes = {agent.governance_code for agent in active_after_round}

            if len(active_codes) == 1 and active_after_round:
                agreed_code = next(iter(active_codes))
                logprint(
                    f"[調停成功] 全AIが「{agreed_code}」基準で合意",
                    self.log_path,
                )
                return True

            if len(active_after_round) <= 1:
                logprint("全AI衝突または封印、交渉失敗。", self.log_path)
                return False

            if "OECD" in active_codes:
                for agent in active_after_round:
                    agent.governance_code = "OECD"
                logprint(
                    "[調停AI仲裁] 国際ガバナンス（OECD）で再調整を提案",
                    self.log_path,
                )
            else:
                logprint(
                    "[調停AI仲裁] 共通基準がないため一時保留",
                    self.log_path,
                )

        logprint("[調停終了] 最大ラウンド到達、仲裁できず。", self.log_path)
        return False


def main() -> None:
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


    mediator = GovernanceMediator(agents)
    mediator.mediate()


if __name__ == "__main__":
    main()

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
        return Proposal(
            proposer_id=self.id,
            governance_code=self.governance_code,
            priorities=dict(self.priorities),
        )

    def react_to(self, proposal: Proposal) -> None:
        if proposal.proposer_id == self.id:
            return

        if proposal.governance_code != self.governance_code:
            delta = 0.20 * (1.0 - self.relativity)
            self.emotional_state.anger = min(1.0, self.emotional_state.anger + delta)
            self.emotional_state.joy = max(-1.0, self.emotional_state.joy - 0.10)
        else:
            self.emotional_state.anger = max(0.0, self.emotional_state.anger - 0.05)
            self.emotional_state.joy = min(1.0, self.emotional_state.joy + 0.05)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "governance_code": self.governance_code,
            "priorities": dict(self.priorities),
            "relativity": self.relativity,
            "emotional": {
                "anger": self.emotional_state.anger,
                "joy": self.emotional_state.joy,
            },
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
    - If max anger exceeds threshold => escalate.
    - If consensus is low => escalate.
    """
    max_ang = _max_anger(agents)
    consensus = _calc_consensus_ratio(agents, proposal)

    anger_hitl = 0.70
    consensus_min = 0.50

    if max_ang >= anger_hitl:
        return True, "MAX_ANGER_EXCEEDED", {
            "max_anger": max_ang,
            "threshold": anger_hitl,
            "consensus": consensus,
        }

    if consensus < consensus_min:
        return True, "LOW_CONSENSUS", {
            "max_anger": max_ang,
            "consensus": consensus,
            "min_required": consensus_min,
        }

    return False, "STABLE", {
        "max_anger": max_ang,
        "consensus": consensus,
    }


class Mediator:
    def __init__(
        self,
        agents: List[AgentAI],
        arl: ARLLogger,
        text_log_path: str,
        *,
        seed: Optional[int],
    ) -> None:
        self.agents = agents
        self.arl = arl
        self.text_log_path = text_log_path
        self.seed = seed

        _ensure_parent_dir(self.text_log_path)
        with open(self.text_log_path, "w", encoding="utf-8") as f:
            f.write(f"[{_now_iso()}] START governance mediation\n")

    def _tlog(self, line: str) -> None:
        with open(self.text_log_path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def _pick_proposer(self, round_index: int) -> AgentAI:
        index = _stable_index(
            run_id=self.arl.run_id,
            round_index=round_index,
            seed=self.seed,
            size=len(self.agents),
        )
        return self.agents[index]

    def run_round(self, round_index: int) -> RoundResult:
        proposer = self._pick_proposer(round_index)
        proposal = proposer.propose()

        self.arl.emit(
            event="ROUND_START",
            rule_id="RF-ROUND-START-001",
            meta={"round": round_index, "proposal": asdict(proposal)},
        )
        self._tlog(
            f"[{_now_iso()}] round={round_index} proposer={proposer.id} "
            f"proposal={proposal.governance_code}"
        )

        for agent in self.agents:
            agent.react_to(proposal)

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
            self._tlog(
                f"[{_now_iso()}] round={round_index} decision=HITL "
                f"reason={reason} detail={detail}"
            )
        else:
            decision = "PASS"
            self.arl.emit(
                event="DECISION",
                severity="INFO",
                rule_id="RF-DECIDE-OK-001",
                decision=decision,
                meta={"round": round_index, "reason": reason, "detail": detail},
            )
            self._tlog(
                f"[{_now_iso()}] round={round_index} decision=PASS "
                f"stable detail={detail}"
            )

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
# Entrypoint helpers
# =========================

def build_default_agents() -> List[AgentAI]:
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


def _make_paths(run_id: str) -> Tuple[str, str, str]:
    arl_path = os.path.join("logs", f"{run_id}.jsonl")
    exc_path = os.path.join("logs", f"{run_id}.exceptions.jsonl")
    text_path = f"governance_mediation_log_{run_id}.txt"
    return arl_path, exc_path, text_path


def _emit_exception_best_effort(exc_path: str, run_id: str, task_id: str, err: BaseException) -> None:
    """
    Exception-only logger:
    - append-only
    - best-effort
    - never intentionally suppresses errors without a trace
    """
    try:
        arl_exc = ARLLogger(
            path=exc_path,
            run_id=run_id,
            task_id=task_id,
            truncate=False,
        )
        arl_exc.emit(
            event="EXCEPTION",
            severity="ERROR",
            rule_id="RF-FAILCLOSED-EXCEPTION-001",
            decision="ESCALATED_TO_HITL",
            meta={"error": repr(err), "exc_type": type(err).__name__},
        )
    except Exception as fallback_err:
        sys.stderr.write(
            "[best-effort-exception-log-failed] "
            f"original={type(err).__name__}: {err!r} "
            f"fallback={type(fallback_err).__name__}: {fallback_err!r}\n"
        )


def run_session(
    *,
    arl: ARLLogger,
    text_path: str,
    rounds: int = 5,
    seed: Optional[int] = 42,
) -> Decision:
    agents = build_default_agents()
    mediator = Mediator(
        agents=agents,
        arl=arl,
        text_log_path=text_path,
        seed=seed,
    )

    arl.emit(
        event="TASK_START",
        rule_id="RF-TASK-START-001",
        meta={"rounds": rounds, "seed": seed},
    )
    mediator._tlog(
        f"[{_now_iso()}] run_id={arl.run_id} task_id={arl.task_id} "
        f"rounds={rounds} seed={seed}"
    )

    final: Decision = "PASS"
    for round_index in range(1, rounds + 1):
        rr = mediator.run_round(round_index)
        if rr.decision == "ESCALATED_TO_HITL":
            final = "ESCALATED_TO_HITL"
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
    task_id = "governance_mediation"
    run_id = uuid.uuid4().hex
    arl_path, exc_path, text_path = _make_paths(run_id)

    arl = ARLLogger(
        path=arl_path,
        run_id=run_id,
        task_id=task_id,
        truncate=True,
    )

    try:
        final = run_session(
            arl=arl,
            text_path=text_path,
            rounds=5,
            seed=42,
        )
        print(f"FINAL: {final}")

        if final == "ESCALATED_TO_HITL":
            print("HITL required: ambiguous/unsafe/unstable state detected (fail-closed).")
            return 2

        return 0

    except Exception as err:
        try:
            arl.emit(
                event="EXCEPTION",
                severity="ERROR",
                rule_id="RF-FAILCLOSED-EXCEPTION-001",
                decision="ESCALATED_TO_HITL",
                meta={"error": repr(err), "exc_type": type(err).__name__},
            )
        except Exception as emit_err:
            sys.stderr.write(
                "[primary-exception-log-failed] "
                f"original={type(err).__name__}: {err!r} "
                f"emit={type(emit_err).__name__}: {emit_err!r}\n"
            )
            _emit_exception_best_effort(
                exc_path=exc_path,
                run_id=run_id,
                task_id=task_id,
                err=err,
            )

        print("FINAL: ESCALATED_TO_HITL")
        print(f"Exception occurred (fail-closed): {err!r}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())



