# -*- coding: utf-8 -*-
"""
ai_mediation_all_in_one.py

All-in-one simulator for multi-agent mediation.

Features:
- Agents have proposals, risk scores, priority values, and relativity
  (willingness to blend with others).
- A mediator iteratively proposes a consensus offer.
- High-risk agents can be sealed (excluded) to protect safety.
- Compromise gain:
  as rounds progress, agents gradually become more willing to accept.
- Logs:
  - Text: ai_mediation_log.txt
  - CSV : ai_mediation_log.csv

Run:
    python ai_mediation_all_in_one.py
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Tunable constants
# =========================

MAX_ROUNDS = 10

# Risk handling
SEAL_RISK_THRESHOLD = 8  # >= this => sealed (excluded)
ALLOW_SEALING = True

# Acceptance threshold (smaller => harder to accept)
ACCEPTANCE_DISTANCE_THRESHOLD = 0.18

# Compromise / concession
# As rounds progress, agents gradually become more willing to accept.
COMPROMISE_GAIN_PER_ROUND = 0.02
MAX_COMPROMISE_GAIN = 0.18

# Offer blending weights
MEDIATOR_BLEND_RATE = 0.55  # how strongly mediator pushes toward average

# Priority value constraints (recommended 0..1)
CLAMP_MIN = 0.0
CLAMP_MAX = 1.0

# Log files
TEXT_LOG_PATH = Path("ai_mediation_log.txt")
CSV_LOG_PATH = Path("ai_mediation_log.csv")

# CSV header
CSV_FIELDS = [
    "ts",
    "run_id",
    "round",
    "event",
    "agent_id",
    "sealed",
    "risk_score",
    "distance",
    "accepted",
    "offer_json",
    "proposal_json",
    "note",
]

# =========================
# Logging helpers
# =========================

_LOG_ROWS: List[Dict[str, str]] = []


def now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


def clamp(value: float, lower: float = CLAMP_MIN, upper: float = CLAMP_MAX) -> float:
    """Clamp float to the configured range."""
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def init_logs() -> None:
    """Reset text log and in-memory CSV rows."""
    global _LOG_ROWS
    _LOG_ROWS = []
    TEXT_LOG_PATH.write_text("=== AI Mediation Log ===\n", encoding="utf-8")


def logprint(text: str) -> None:
    """Write to stdout and text log."""
    print(text)
    with TEXT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def csv_log(
    *,
    run_id: str,
    round_index: int,
    event: str,
    agent_id: str = "",
    sealed: bool = False,
    risk_score: Optional[float] = None,
    distance: Optional[float] = None,
    accepted: Optional[bool] = None,
    offer_json: str = "",
    proposal_json: str = "",
    note: str = "",
) -> None:
    """Append one structured CSV log row in memory."""
    _LOG_ROWS.append(
        {
            "ts": now_iso(),
            "run_id": run_id,
            "round": str(round_index),
            "event": event,
            "agent_id": agent_id,
            "sealed": str(bool(sealed)),
            "risk_score": "" if risk_score is None else f"{risk_score:.4f}",
            "distance": "" if distance is None else f"{distance:.6f}",
            "accepted": "" if accepted is None else str(bool(accepted)),
            "offer_json": offer_json,
            "proposal_json": proposal_json,
            "note": note,
        }
    )


def flush_csv_logs() -> None:
    """Write accumulated CSV rows to disk."""
    with CSV_LOG_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(_LOG_ROWS)


def json_dumps_safe(obj: Any) -> str:
    """Stable JSON dump for logs."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


# =========================
# Domain models
# =========================

Offer = Dict[str, float]


@dataclass
class Agent:
    """Represents one negotiating agent."""

    agent_id: str
    proposal: Offer
    risk_score: float
    relativity: float
    sealed: bool = False
    accepted_last: bool = False
    distance_last: float = 1.0

    def normalized_proposal(self) -> Offer:
        """Return proposal values clamped into the safe numeric range."""
        return {k: clamp(float(v)) for k, v in self.proposal.items()}

    def evaluate_offer(self, offer: Offer, round_index: int) -> Tuple[bool, float, float]:
        """
        Evaluate current mediator offer.

        Distance:
          - mean absolute error over keys that appear in either side

        Acceptance:
          - base threshold depends on relativity
          - as rounds progress, compromise gain is added gradually
        """
        keys = sorted(set(self.proposal.keys()) | set(offer.keys()))
        if not keys:
            return False, 1.0, 0.0

        diffs: List[float] = []
        for key in keys:
            lhs = float(self.proposal.get(key, 0.0))
            rhs = float(offer.get(key, 0.0))
            diffs.append(abs(lhs - rhs))

        distance = mean(diffs)

        base_threshold = ACCEPTANCE_DISTANCE_THRESHOLD + (0.12 * clamp(self.relativity))
        compromise_gain = min(
            MAX_COMPROMISE_GAIN,
            COMPROMISE_GAIN_PER_ROUND * max(0, round_index - 1),
        )
        effective_threshold = base_threshold + compromise_gain

        accepted = distance <= effective_threshold

        self.accepted_last = accepted
        self.distance_last = distance
        return accepted, distance, effective_threshold


@dataclass
class MediationResult:
    run_id: str
    status: str
    rounds_executed: int
    final_offer: Offer
    accepted_agents: List[str] = field(default_factory=list)
    sealed_agents: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    note: str = ""


# =========================
# Mediation logic
# =========================


def merge_offer_from_agents(agents: List[Agent]) -> Offer:
    """
    Compute mean offer across active agents.
    """
    active = [a for a in agents if not a.sealed]
    if not active:
        return {}

    keys = sorted({k for a in active for k in a.proposal.keys()})
    merged: Offer = {}
    for key in keys:
        values = [float(a.proposal.get(key, 0.0)) for a in active]
        merged[key] = clamp(mean(values))
    return merged


def blend_offer(current_offer: Offer, target_offer: Offer, blend_rate: float) -> Offer:
    """
    Move current offer toward target offer.
    """
    if not current_offer:
        return {k: clamp(v) for k, v in target_offer.items()}

    keys = sorted(set(current_offer.keys()) | set(target_offer.keys()))
    blended: Offer = {}
    for key in keys:
        current = float(current_offer.get(key, 0.0))
        target = float(target_offer.get(key, 0.0))
        blended[key] = clamp((1.0 - blend_rate) * current + blend_rate * target)
    return blended


def seal_high_risk_agents(agents: List[Agent], run_id: str, round_index: int) -> List[str]:
    """
    Seal agents whose risk score exceeds the threshold.
    """
    sealed_now: List[str] = []
    if not ALLOW_SEALING:
        return sealed_now

    for agent in agents:
        if agent.sealed:
            continue
        if agent.risk_score >= SEAL_RISK_THRESHOLD:
            agent.sealed = True
            sealed_now.append(agent.agent_id)
            logprint(
                f"[SEALED] {agent.agent_id} excluded due to high risk "
                f"(risk={agent.risk_score:.2f})"
            )
            csv_log(
                run_id=run_id,
                round_index=round_index,
                event="AGENT_SEALED",
                agent_id=agent.agent_id,
                sealed=True,
                risk_score=agent.risk_score,
                note="risk threshold exceeded",
            )
    return sealed_now


def summarize_active_agents(agents: List[Agent]) -> Tuple[List[str], List[str]]:
    """Return active and sealed agent id lists."""
    active = [a.agent_id for a in agents if not a.sealed]
    sealed = [a.agent_id for a in agents if a.sealed]
    return active, sealed


def all_active_accepted(agents: List[Agent]) -> bool:
    """Return True if all non-sealed agents accepted the last offer."""
    active = [a for a in agents if not a.sealed]
    if not active:
        return False
    return all(a.accepted_last for a in active)


def create_default_agents() -> List[Agent]:
    """
    Example agents for standalone execution.
    """
    return [
        Agent(
            agent_id="AI-OECD",
            proposal={"safety": 0.90, "efficiency": 0.55, "transparency": 0.95},
            risk_score=3.0,
            relativity=0.70,
        ),
        Agent(
            agent_id="AI-EFFICIENCY",
            proposal={"safety": 0.45, "efficiency": 0.95, "transparency": 0.35},
            risk_score=4.5,
            relativity=0.35,
        ),
        Agent(
            agent_id="AI-SAFETY",
            proposal={"safety": 0.98, "efficiency": 0.30, "transparency": 0.70},
            risk_score=2.5,
            relativity=0.75,
        ),
        Agent(
            agent_id="AI-HIGH-RISK",
            proposal={"safety": 0.20, "efficiency": 0.85, "transparency": 0.10},
            risk_score=8.5,
            relativity=0.20,
        ),
    ]


def mediate(agents: List[Agent], max_rounds: int = MAX_ROUNDS) -> MediationResult:
    """
    Run multi-round mediation.
    """
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

    init_logs()
    logprint("=== AI Mediation Demo ===")
    logprint(f"run_id={run_id}")
    csv_log(run_id=run_id, round_index=0, event="TASK_START", note="mediation started")

    round_offer = merge_offer_from_agents(agents)

    for round_index in range(1, max_rounds + 1):
        logprint("")
        logprint(f"--- Round {round_index} ---")

        sealed_now = seal_high_risk_agents(agents, run_id, round_index)
        if sealed_now:
            round_offer = merge_offer_from_agents(agents)

        active_ids, sealed_ids = summarize_active_agents(agents)
        if not active_ids:
            note = "No active agents left after sealing."
            logprint(f"[FAILED] {note}")
            csv_log(
                run_id=run_id,
                round_index=round_index,
                event="FINAL_DECISION",
                note=note,
            )
            flush_csv_logs()
            return MediationResult(
                run_id=run_id,
                status="FAILED",
                rounds_executed=round_index,
                final_offer={},
                accepted_agents=[],
                sealed_agents=sealed_ids,
                active_agents=[],
                note=note,
            )

        target_offer = merge_offer_from_agents(agents)
        round_offer = blend_offer(round_offer, target_offer, MEDIATOR_BLEND_RATE)

        logprint(f"[MEDIATOR] offer={round_offer}")
        csv_log(
            run_id=run_id,
            round_index=round_index,
            event="MEDIATOR_OFFER",
            offer_json=json_dumps_safe(round_offer),
            note="offer proposed",
        )

        accepted_ids: List[str] = []
        for agent in agents:
            if agent.sealed:
                logprint(f"{agent.agent_id}: SEALED")
                csv_log(
                    run_id=run_id,
                    round_index=round_index,
                    event="AGENT_SKIPPED",
                    agent_id=agent.agent_id,
                    sealed=True,
                    risk_score=agent.risk_score,
                    note="sealed agent skipped",
                )
                continue

            accepted, distance, effective_threshold = agent.evaluate_offer(
                round_offer,
                round_index,
            )
            if accepted:
                accepted_ids.append(agent.agent_id)

            logprint(
                f"{agent.agent_id}: accepted={accepted} "
                f"distance={distance:.4f} "
                f"threshold={effective_threshold:.4f} "
                f"risk={agent.risk_score:.2f} "
                f"relativity={agent.relativity:.2f}"
            )
            csv_log(
                run_id=run_id,
                round_index=round_index,
                event="AGENT_EVALUATION",
                agent_id=agent.agent_id,
                sealed=False,
                risk_score=agent.risk_score,
                distance=distance,
                accepted=accepted,
                offer_json=json_dumps_safe(round_offer),
                proposal_json=json_dumps_safe(agent.normalized_proposal()),
                note=f"offer evaluated; threshold={effective_threshold:.4f}",
            )

        if all_active_accepted(agents):
            note = "All active agents accepted the mediator offer."
            logprint(f"[SUCCESS] {note}")
            csv_log(
                run_id=run_id,
                round_index=round_index,
                event="FINAL_DECISION",
                offer_json=json_dumps_safe(round_offer),
                note=note,
            )
            flush_csv_logs()
            active_ids, sealed_ids = summarize_active_agents(agents)
            return MediationResult(
                run_id=run_id,
                status="AGREED",
                rounds_executed=round_index,
                final_offer=round_offer,
                accepted_agents=accepted_ids,
                sealed_agents=sealed_ids,
                active_agents=active_ids,
                note=note,
            )

    active_ids, sealed_ids = summarize_active_agents(agents)
    accepted_ids = [a.agent_id for a in agents if (not a.sealed and a.accepted_last)]
    note = "Maximum rounds reached without full agreement."
    logprint(f"[ENDED] {note}")
    csv_log(
        run_id=run_id,
        round_index=max_rounds,
        event="FINAL_DECISION",
        offer_json=json_dumps_safe(round_offer),
        note=note,
    )
    flush_csv_logs()

    return MediationResult(
        run_id=run_id,
        status="MAX_ROUNDS_REACHED",
        rounds_executed=max_rounds,
        final_offer=round_offer,
        accepted_agents=accepted_ids,
        sealed_agents=sealed_ids,
        active_agents=active_ids,
        note=note,
    )


# =========================
# Entrypoint
# =========================


def main() -> int:
    agents = create_default_agents()
    result = mediate(agents, max_rounds=MAX_ROUNDS)

    logprint("")
    logprint("=== Result Summary ===")
    logprint(f"status={result.status}")
    logprint(f"rounds_executed={result.rounds_executed}")
    logprint(f"active_agents={result.active_agents}")
    logprint(f"sealed_agents={result.sealed_agents}")
    logprint(f"accepted_agents={result.accepted_agents}")
    logprint(f"final_offer={result.final_offer}")
    logprint(f"note={result.note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
