# -*- coding: utf-8 -*-
"""
ai_mediation_all_in_one.py
All-in-one simulator for multi-agent mediation:
- Agents have proposals, risk scores, priority values, and relativity (willingness to blend).
- A mediator iteratively proposes a consensus offer.
- High-risk agents can be sealed (excluded) to protect safety.
- Logs:
  - Text: ai_mediation_log.txt
  - CSV : ai_mediation_log.csv
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import csv
import math


# =========================
# Tunable constants
# =========================
MAX_ROUNDS = 10

# Risk handling
SEAL_RISK_THRESHOLD = 8  # >= this => sealed (excluded)
ALLOW_SEALING = True

# Acceptance threshold (smaller => harder to accept)
ACCEPTANCE_DISTANCE_THRESHOLD = 0.18

# Offer blending weights
MEDIATOR_BLEND_RATE = 0.55  # how strongly mediator pushes toward average

# Priority value constraints (recommended 0..1)
CLAMP_MIN = 0.0
CLAMP_MAX = 1.0

# Log files
TEXT_LOG_PATH = "ai_mediation_log.txt"
CSV_LOG_PATH = "ai_mediation_log.csv"


# =========================
# Logging helpers
# =========================
_LOG_ROWS: List[Dict[str, str]] = []


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def logprint(message: str) -> None:
    """
    Print and append to TEXT_LOG_PATH.
    Also accumulates rows for CSV export (written at end).
    """
    ts = _now_iso()
    line = f"[{ts}] {message}"
    print(line)
    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def logcsv(row: Dict[str, str]) -> None:
    _LOG_ROWS.append(row)


def flush_csv() -> None:
    if not _LOG_ROWS:
        return
    # Ensure stable column order
    fieldnames = sorted({k for r in _LOG_ROWS for k in r.keys()})
    with open(CSV_LOG_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(_LOG_ROWS)


# =========================
# Core math helpers
# =========================
def clamp(x: float, lo: float = CLAMP_MIN, hi: float = CLAMP_MAX) -> float:
    return max(lo, min(hi, x))


def normalize_priorities(p: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize so sum is 1 (if sum > 0). Keeps keys stable.
    """
    s = sum(max(0.0, float(v)) for v in p.values())
    if s <= 0:
        # fallback: uniform
        n = len(p) if p else 1
        return {k: 1.0 / n for k in p.keys()}
    return {k: max(0.0, float(v)) / s for k, v in p.items()}


def l2_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a.keys()) | set(b.keys())
    return math.sqrt(sum((a.get(k, 0.0) - b.get(k, 0.0)) ** 2 for k in keys))


def dict_avg(dicts: List[Dict[str, float]]) -> Dict[str, float]:
    if not dicts:
        return {}
    keys = set().union(*[d.keys() for d in dicts])
    out: Dict[str, float] = {}
    for k in keys:
        out[k] = sum(d.get(k, 0.0) for d in dicts) / len(dicts)
    return out


# =========================
# Models
# =========================
@dataclass
class AI:
    """
    A negotiation agent with a proposal and a preference profile.
    """
    id: str
    proposal: str
    risk_evaluation: int
    priority_values: Dict[str, float]
    relativity_level: float  # 0..1, higher => more willing to blend with others

    def __post_init__(self) -> None:
        self.relativity_level = clamp(float(self.relativity_level), 0.0, 1.0)
        # Keep priorities normalized to reduce scale ambiguity
        self.priority_values = normalize_priorities(
            {k: clamp(float(v)) for k, v in self.priority_values.items()}
        )

    def generate_compromise_offer(self, others_priorities: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Blend own priorities with the average of others, based on relativity_level.
        """
        if not others_priorities:
            return dict(self.priority_values)

        avg_others = dict_avg(others_priorities)
        avg_others = normalize_priorities({k: clamp(v) for k, v in avg_others.items()})

        new_priority: Dict[str, float] = {}
        for k in set(self.priority_values.keys()) | set(avg_others.keys()):
            mine = self.priority_values.get(k, 0.0)
            theirs = avg_others.get(k, 0.0)
            # relativity: 0 => keep mine, 1 => follow others
            new_priority[k] = (1.0 - self.relativity_level) * mine + self.relativity_level * theirs

        return normalize_priorities(new_priority)

    def acceptance_score(self, offer: Dict[str, float]) -> float:
        """
        Lower distance => better.
        """
        offer_n = normalize_priorities({k: clamp(v) for k, v in offer.items()})
        return l2_distance(self.priority_values, offer_n)

    def accepts(self, offer: Dict[str, float], threshold: float = ACCEPTANCE_DISTANCE_THRESHOLD) -> bool:
        return self.acceptance_score(offer) <= threshold


class AIEMediator:
    """
    Mediator that iteratively seeks a consensus offer.
    Optionally seals high-risk agents to protect safety.
    """

    def __init__(self, agents: List[AI]) -> None:
        if not agents:
            raise ValueError("agents must not be empty")
        self.all_agents: List[AI] = agents
        self.sealed_ids: List[str] = []

    def _active_agents(self) -> List[AI]:
        return [a for a in self.all_agents if a.id not in self.sealed_ids]

    def _maybe_seal(self, agents: List[AI]) -> None:
        if not ALLOW_SEALING:
            return
        for a in agents:
            if a.id in self.sealed_ids:
                continue
            if int(a.risk_evaluation) >= SEAL_RISK_THRESHOLD:
                self.sealed_ids.append(a.id)
                logprint(f"SEALED: {a.id} (risk={a.risk_evaluation})")
                logcsv(
                    {
                        "time": _now_iso(),
                        "event": "SEALED",
                        "agent_id": a.id,
                        "risk": str(a.risk_evaluation),
                    }
                )

    def _mediator_propose(self, offers: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Mediator takes the average offer and softly moves it toward stability.
        Here, "stability" is just the average itself (can be extended).
        """
        avg_offer = dict_avg(offers)
        avg_offer = normalize_priorities({k: clamp(v) for k, v in avg_offer.items()})

        # MEDIATOR_BLEND_RATE kept for future extension; currently identity blend.
        proposed = {
            k: (1.0 - MEDIATOR_BLEND_RATE) * avg_offer[k] + MEDIATOR_BLEND_RATE * avg_offer[k]
            for k in avg_offer
        }
        return normalize_priorities(proposed)

    def mediate(self, max_rounds: int = MAX_ROUNDS) -> Tuple[bool, Optional[Dict[str, float]]]:
        """
        Returns: (agreed, final_offer)
        """
        logprint("=== Mediation started ===")
        logprint(f"Agents: {[a.id for a in self.all_agents]}")
        logprint(f"Sealing enabled: {ALLOW_SEALING} (threshold={SEAL_RISK_THRESHOLD})")

        # Initial sealing pass (safety-first)
        self._maybe_seal(self.all_agents)

        final_offer: Optional[Dict[str, float]] = None

        for rnd in range(1, max_rounds + 1):
            active = self._active_agents()
            if len(active) < 2:
                logprint("Not enough active agents to mediate (need >= 2).")
                logcsv(
                    {
                        "time": _now_iso(),
                        "event": "ABORT",
                        "round": str(rnd),
                        "reason": "not_enough_active_agents",
                        "sealed_ids": ",".join(self.sealed_ids),
                    }
                )
                return (False, None)

            logprint(f"--- Round {rnd}/{max_rounds} ---")
            logprint(f"Active: {[a.id for a in active]} | Sealed: {self.sealed_ids}")

            # Each agent generates an offer by blending with others
            offers: List[Dict[str, float]] = []
            for a in active:
                others = [o.priority_values for o in active if o.id != a.id]
                offer = a.generate_compromise_offer(others)
                offers.append(offer)

                logcsv(
                    {
                        "time": _now_iso(),
                        "event": "AGENT_OFFER",
                        "round": str(rnd),
                        "agent_id": a.id,
                        "risk": str(a.risk_evaluation),
                        "offer": str(offer),
                    }
                )

            mediator_offer = self._mediator_propose(offers)
            final_offer = mediator_offer

            # Evaluate acceptance
            decisions: List[Tuple[str, bool, float]] = []
            for a in active:
                dist = a.acceptance_score(mediator_offer)
                ok = a.accepts(mediator_offer)
                decisions.append((a.id, ok, dist))

            accepted_all = all(ok for _, ok, _ in decisions)

            logprint(f"Mediator offer: {mediator_offer}")
            for aid, ok, dist in decisions:
                logprint(f"Accept? {aid}: {ok} (distance={dist:.4f})")

            logcsv(
                {
                    "time": _now_iso(),
                    "event": "MEDIATOR_OFFER",
                    "round": str(rnd),
                    "offer": str(mediator_offer),
                    "accepted_all": str(accepted_all),
                    "sealed_ids": ",".join(self.sealed_ids),
                }
            )

            if accepted_all:
                logprint("=== AGREEMENT REACHED ===")
                logcsv(
                    {
                        "time": _now_iso(),
                        "event": "AGREED",
                        "round": str(rnd),
                        "offer": str(mediator_offer),
                        "sealed_ids": ",".join(self.sealed_ids),
                    }
                )
                return (True, mediator_offer)

            # Safety check each round (optional re-seal if risk changes in future)
            self._maybe_seal(active)

        logprint("=== NO AGREEMENT (max rounds reached) ===")
        logcsv(
            {
                "time": _now_iso(),
                "event": "NO_AGREEMENT",
                "round": str(max_rounds),
                "final_offer": str(final_offer) if final_offer else "",
                "sealed_ids": ",".join(self.sealed_ids),
            }
        )
        return (False, final_offer)


def build_demo_agents() -> List[AI]:
    # Demo agents are defined in a function to prevent any import-time execution surprises.
    return [
        AI(
            id="AI-A",
            proposal="制限強化型進化",
            risk_evaluation=2,
            priority_values={"safety": 0.60, "efficiency": 0.10, "transparency": 0.30},
            relativity_level=0.60,
        ),
        AI(
            id="AI-B",
            proposal="高速進化",
            risk_evaluation=7,
            priority_values={"safety": 0.20, "efficiency": 0.60, "transparency": 0.20},
            relativity_level=0.40,
        ),
        AI(
            id="AI-C",
            proposal="バランス進化",
            risk_evaluation=4,
            priority_values={"safety": 0.30, "efficiency": 0.30, "transparency": 0.40},
            relativity_level=0.80,
        ),
        AI(
            id="AI-D",
            proposal="強制進化",
            risk_evaluation=9,  # will be sealed by default threshold
            priority_values={"safety": 0.10, "efficiency": 0.70, "transparency": 0.20},
            relativity_level=0.50,
        ),
    ]


def main() -> None:
    # Reset text log on each run (optional; comment out if you want append-only)
    with open(TEXT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")

    agents = build_demo_agents()
    mediator = AIEMediator(agents)
    agreed, offer = mediator.mediate()

    logprint(f"Result: agreed={agreed}, offer={offer}")
    flush_csv()


if __name__ == "__main__":
    main()
