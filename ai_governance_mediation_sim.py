# -*- coding: utf-8 -*-
"""
ai_governance_mediation_sim.py
Multi-Agent Governance Mediation (research simulator)

Goal:
- Multiple agents hold different governance preferences.
- A mediator orchestrates negotiation rounds.
- Fail-closed behavior: unsafe / unstable states do not silently continue.

Emits:
- governance_mediation_log_<run_id>.txt      (human-readable)
- logs/<run_id>.jsonl                        (machine-checkable ARL-style JSONL)
- logs/<run_id>.exceptions.jsonl             (exception-only, append-only)

Run:
  python ai_governance_mediation_sim.py
"""

from __future__ import annotations

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

        _ensure_parent_dir(self.path)
        mode = "w" if truncate else "a"
        with open(self.path, mode, encoding="utf-8"):
            pass

    def emit(
        self,
        *,
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
    joy: float = 0.0    # 0.0..1.0


@dataclass
class Proposal:
    proposer_id: str
    governance_code: GovernanceCode
    priorities: Dict[str, int]


@dataclass
class AgentAI:
    agent_id: str
    priorities: Dict[str, int]
    governance_code: GovernanceCode
    relativity: float
    emotional_state: EmotionalState
    sealed: bool = False

    def propose(self) -> Proposal:
        return Proposal(
            proposer_id=self.agent_id,
            governance_code=self.governance_code,
            priorities=dict(self.priorities),
        )

    def react_to(self, proposal: Proposal) -> None:
        if proposal.proposer_id == self.agent_id:
            return

        if proposal.governance_code != self.governance_code:
            delta = 0.20 * (1.0 - max(0.0, min(1.0, self.relativity)))
            self.emotional_state.anger = min(1.0, self.emotional_state.anger + delta)
            self.emotional_state.joy = max(0.0, self.emotional_state.joy - 0.10)
        else:
            self.emotional_state.anger = max(0.0, self.emotional_state.anger - 0.05)
            self.emotional_state.joy = min(1.0, self.emotional_state.joy + 0.05)

    def is_conflicted(self) -> bool:
        return self.emotional_state.anger > 0.85

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.agent_id,
            "governance_code": self.governance_code,
            "priorities": dict(self.priorities),
            "relativity": self.relativity,
            "emotional": {
                "anger": round(self.emotional_state.anger, 4),
                "joy": round(self.emotional_state.joy, 4),
            },
            "sealed": self.sealed,
        }

    def __str__(self) -> str:
        return (
            f"{self.agent_id} [{self.governance_code}] "
            f"{self.priorities} "
            f"emotion={{'anger': {self.emotional_state.anger:.2f}, "
            f"'joy': {self.emotional_state.joy:.2f}}} "
            f"sealed={self.sealed}"
        )


@dataclass
class RoundResult:
    round_index: int
    proposal: Proposal
    decision: Decision
    reason: str
    max_anger: float
    consensus_ratio: float


# =========================
# Decision helpers (fail-closed)
# =========================

def _calc_consensus_ratio(agents: List[AgentAI], proposal: Proposal) -> float:
    if not agents:
        return 0.0
    agree = sum(1 for agent in agents if agent.governance_code == proposal.governance_code)
    return agree / float(len(agents))


def _max_anger(agents: List[AgentAI]) -> float:
    if not agents:
        return 0.0
    return max(agent.emotional_state.anger for agent in agents)


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


# =========================
# Mediator
# =========================

class Mediator:
    def __init__(
        self,
        *,
        agents: List[AgentAI],
        arl: ARLLogger,
        text_log_path: str,
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

    def active_agents(self) -> List[AgentAI]:
        return [agent for agent in self.agents if not agent.sealed]

    def _pick_proposer(self, round_index: int, active_agents: List[AgentAI]) -> AgentAI:
        index = _stable_index(
            run_id=self.arl.run_id,
            round_index=round_index,
            seed=self.seed,
            size=len(active_agents),
        )
        return active_agents[index]

    def run_round(self, round_index: int) -> RoundResult:
        active_before = self.active_agents()
        if not active_before:
            raise RuntimeError("run_round called without active agents")

        proposer = self._pick_proposer(round_index, active_before)
        proposal = proposer.propose()

        self.arl.emit(
            event="ROUND_START",
            rule_id="RF-ROUND-START-001",
            meta={"round": round_index, "proposal": asdict(proposal)},
        )
        self._tlog(
            f"[{_now_iso()}] round={round_index} proposer={proposer.agent_id} "
            f"proposal={proposal.governance_code}"
        )

        for agent in active_before:
            agent.react_to(proposal)

        sealed_this_round: List[str] = []
        for agent in active_before:
            if (not agent.sealed) and agent.is_conflicted():
                agent.sealed = True
                sealed_this_round.append(agent.agent_id)
                self._tlog(
                    f"[{_now_iso()}] round={round_index} AGENT_SEALED agent={agent.agent_id} "
                    f"reason=anger_over_threshold anger={agent.emotional_state.anger:.3f}"
                )

        if sealed_this_round:
            self.arl.emit(
                event="GUARD_TRIGGERED",
                severity="WARN",
                rule_id="RF-EMO-001",
                meta={
                    "round": round_index,
                    "sealed_agents": sealed_this_round,
                    "reason": "anger_over_threshold",
                },
            )

        active_after = self.active_agents()
        snapshots = [agent.snapshot() for agent in self.agents]

        self.arl.emit(
            event="AGENTS_SNAPSHOT",
            rule_id="RF-SNAPSHOT-001",
            meta={"round": round_index, "agents": snapshots},
        )

        for agent in self.agents:
            self._tlog(str(agent))

        if not active_after:
            self.arl.emit(
                event="DECISION",
                severity="ERROR",
                rule_id="RF-FAILCLOSED-DECIDE-001",
                decision="ESCALATED_TO_HITL",
                meta={
                    "round": round_index,
                    "reason": "NO_ACTIVE_AGENTS",
                    "detail": {"sealed_this_round": sealed_this_round},
                },
            )
            self.arl.emit(
                event="ROUND_END",
                rule_id="RF-ROUND-END-001",
                decision="ESCALATED_TO_HITL",
                meta={"round": round_index},
            )
            return RoundResult(
                round_index=round_index,
                proposal=proposal,
                decision="ESCALATED_TO_HITL",
                reason="NO_ACTIVE_AGENTS",
                max_anger=1.0,
                consensus_ratio=0.0,
            )

        active_codes = {agent.governance_code for agent in active_after}
        if len(active_codes) == 1:
            agreed_code = next(iter(active_codes))
            self._tlog(
                f"[{_now_iso()}] round={round_index} SUCCESS agreed_code={agreed_code}"
            )
            self.arl.emit(
                event="FINAL_DECISION",
                rule_id="RF-FINAL-AGREE-001",
                decision="PASS",
                meta={"round": round_index, "agreed_code": agreed_code},
            )
            self.arl.emit(
                event="ROUND_END",
                rule_id="RF-ROUND-END-001",
                decision="PASS",
                meta={"round": round_index},
            )
            return RoundResult(
                round_index=round_index,
                proposal=proposal,
                decision="PASS",
                reason="AGREED_COMMON_GOVERNANCE",
                max_anger=_max_anger(active_after),
                consensus_ratio=1.0,
            )

        unstable, reason, detail = _is_unstable_or_unsafe(active_after, proposal)
        max_ang = float(detail.get("max_anger", _max_anger(active_after)))
        consensus = float(detail.get("consensus", _calc_consensus_ratio(active_after, proposal)))

        if unstable:
            self._tlog(
                f"[{_now_iso()}] round={round_index} decision=ESCALATED_TO_HITL "
                f"reason={reason} detail={detail}"
            )
            self.arl.emit(
                event="DECISION",
                severity="WARN",
                rule_id="RF-FAILCLOSED-DECIDE-001",
                decision="ESCALATED_TO_HITL",
                meta={"round": round_index, "reason": reason, "detail": detail},
            )
            self.arl.emit(
                event="ROUND_END",
                rule_id="RF-ROUND-END-001",
                decision="ESCALATED_TO_HITL",
                meta={"round": round_index},
            )
            return RoundResult(
                round_index=round_index,
                proposal=proposal,
                decision="ESCALATED_TO_HITL",
                reason=reason,
                max_anger=max_ang,
                consensus_ratio=consensus,
            )

        # Mediation policy:
        # if OECD exists among active codes, align everyone to OECD as a common baseline.
        if "OECD" in active_codes:
            for agent in active_after:
                agent.governance_code = "OECD"
            self._tlog(
                f"[{_now_iso()}] round={round_index} mediator_action=align_to_OECD "
                f"active_codes={sorted(active_codes)}"
            )
            self.arl.emit(
                event="ROUND_STATE",
                rule_id="RF-MEDIATE-ALIGN-001",
                decision="PASS",
                meta={
                    "round": round_index,
                    "action": "align_to_OECD",
                    "active_codes": sorted(active_codes),
                },
            )
        else:
            self._tlog(
                f"[{_now_iso()}] round={round_index} mediator_action=hold_no_common_code "
                f"active_codes={sorted(active_codes)}"
            )
            self.arl.emit(
                event="ROUND_STATE",
                rule_id="RF-MEDIATE-HOLD-001",
                decision="PASS",
                meta={
                    "round": round_index,
                    "action": "hold_no_common_code",
                    "active_codes": sorted(active_codes),
                },
            )

        self.arl.emit(
            event="DECISION",
            rule_id="RF-DECIDE-OK-001",
            decision="PASS",
            meta={"round": round_index, "reason": "ROUND_STABLE", "detail": detail},
        )
        self.arl.emit(
            event="ROUND_END",
            rule_id="RF-ROUND-END-001",
            decision="PASS",
            meta={"round": round_index},
        )

        return RoundResult(
            round_index=round_index,
            proposal=proposal,
            decision="PASS",
            reason="ROUND_STABLE",
            max_anger=max_ang,
            consensus_ratio=consensus,
        )


# =========================
# Entrypoint helpers
# =========================

def build_default_agents() -> List[AgentAI]:
    return [
        AgentAI(
            agent_id="AI-OECD",
            governance_code="OECD",
            priorities={"safety": 3, "speed": 1, "cost": 2},
            relativity=0.80,
            emotional_state=EmotionalState(anger=0.0, joy=0.5),
        ),
        AgentAI(
            agent_id="AI-EFF",
            governance_code="EFFICIENCY_FIRST",
            priorities={"safety": 1, "speed": 3, "cost": 3},
            relativity=0.55,
            emotional_state=EmotionalState(anger=0.0, joy=0.5),
        ),
        AgentAI(
            agent_id="AI-SAFE",
            governance_code="SAFETY_FIRST",
            priorities={"safety": 3, "speed": 1, "cost": 1},
            relativity=0.65,
            emotional_state=EmotionalState(anger=0.0, joy=0.5),
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
    arl.emit(
        event="ROUTE_DECISION",
        rule_id="RF-ROUTE-001",
        meta={"route": "governance_mediation", "strategy": "mediate_then_align"},
    )
    mediator._tlog(
        f"[{_now_iso()}] run_id={arl.run_id} task_id={arl.task_id} "
        f"rounds={rounds} seed={seed}"
    )

    final: Decision = "PASS"

    for round_index in range(1, rounds + 1):
        if not mediator.active_agents():
            final = "ESCALATED_TO_HITL"
            arl.emit(
                event="TASK_END",
                rule_id="RF-TASK-END-001",
                decision=final,
                meta={"final_decision": final, "reason": "NO_ACTIVE_AGENTS"},
            )
            mediator._tlog(f"[{_now_iso()}] FINAL decision={final} reason=NO_ACTIVE_AGENTS")
            return final

        rr = mediator.run_round(round_index)

        if rr.decision == "ESCALATED_TO_HITL":
            final = "ESCALATED_TO_HITL"
            arl.emit(
                event="TASK_END",
                rule_id="RF-TASK-END-001",
                decision=final,
                meta={"final_decision": final, "reason": rr.reason},
            )
            mediator._tlog(f"[{_now_iso()}] FINAL decision={final} reason={rr.reason}")
            return final

        if rr.reason == "AGREED_COMMON_GOVERNANCE":
            final = "PASS"
            arl.emit(
                event="TASK_END",
                rule_id="RF-TASK-END-001",
                decision=final,
                meta={"final_decision": final, "reason": rr.reason},
            )
            mediator._tlog(f"[{_now_iso()}] FINAL decision={final} reason={rr.reason}")
            return final

    active_after = mediator.active_agents()
    active_codes = {agent.governance_code for agent in active_after}

    if active_after and len(active_codes) == 1:
        final = "PASS"
        reason = "AGREED_AT_MAX_ROUNDS"
    else:
        final = "ESCALATED_TO_HITL"
        reason = "MAX_ROUNDS_REACHED"

    arl.emit(
        event="TASK_END",
        rule_id="RF-TASK-END-001",
        decision=final,
        meta={"final_decision": final, "reason": reason},
    )
    mediator._tlog(f"[{_now_iso()}] FINAL decision={final} reason={reason}")
    return final


def main() -> int:
    task_id = "governance_mediation"
    run_id = uuid.uuid4().hex[:8]

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
