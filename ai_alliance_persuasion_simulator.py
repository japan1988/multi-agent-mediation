# -*- coding: utf-8 -*-
"""
ai_alliance_persuasion_simulator.py

A simulator for modeling alliance, persuasion, sealing, cooldown, and reintegration
among multiple AI agents.

Primary goal (for tests/CI):
- Expose module-level CSV_PATH and TXT_PATH so tests can monkeypatch log destinations.

Compatibility:
- Some tests/older code instantiate AIAgent(..., sealed=True, ...) instead of status="Sealed".
- Some older code may instantiate AIAgent(..., status="Sealed") without sealed arg.
To support BOTH, `sealed` is Optional and only overrides status when explicitly provided.

Logs:
- TXT_PATH: human-readable append log
- CSV_PATH: structured event log
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
import csv
import os
import random

# =========================
# Public log paths (TESTS EXPECT THESE NAMES)
# =========================
TXT_PATH: str = "ai_alliance_sim_log.txt"
CSV_PATH: str = "ai_alliance_sim_log.csv"

# Backward compatible aliases (older code may refer to these)
TEXT_LOG_PATH: str = TXT_PATH
CSV_LOG_PATH: str = CSV_PATH

# =========================
# Adjustable constants (one place to tune behavior)
# =========================
MAX_ROUNDS = 8

PERSUASION_THRESHOLD = 0.15   # base persuasion threshold (higher -> harder)
RELATIVITY_WEIGHT    = 0.20   # (1 - relativity) increases threshold
ANGER_WEIGHT         = 0.10   # anger increases threshold
NUDGE_RATE           = 0.15   # successful persuasion nudges priorities toward mean (0..1)

COOLDOWN_DECAY       = 0.15   # anger cools down per round
ANGER_RESEAL         = 0.90   # reseal trigger: if anger >= this while Active
ANGER_REINTEGRATE    = 0.35   # allow reintegration if sealed and anger <= this

# When sealing, force a minimum cooldown (in rounds) before reintegration checks apply
MIN_SEAL_ROUNDS      = 1


# =========================
# Utilities
# =========================
def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _safe_float(d: Dict[str, Any], k: str, default: float = 0.0) -> float:
    try:
        return float(d.get(k, default))
    except Exception:
        return float(default)


# =========================
# Domain model
# =========================
@dataclass
class AIAgent:
    name: str
    priorities: Dict[str, float]
    relativity: float = 0.5  # 0..1 (higher -> more cooperative)
    emotional_state: Dict[str, float] = field(default_factory=dict)

    # compat: tests may pass sealed=True at init.
    # Use Optional so we can distinguish "not provided" from "provided False".
    sealed: Optional[bool] = None

    # canonical status used by simulation rules
    status: str = "Active"   # "Active" | "Sealed"
    sealed_rounds: int = 0   # counts rounds while sealed

    def __post_init__(self) -> None:
        """
        Compatibility policy:

        1) If `sealed` is explicitly provided (True/False), it wins and sets `status`.
        2) Otherwise, `status` wins and sets `sealed`.
        """
        if self.status not in ("Active", "Sealed"):
            self.status = "Active"

        if self.sealed is True:
            self.status = "Sealed"
        elif self.sealed is False:
            self.status = "Active"
        else:
            # sealed not provided => mirror from status
            self.sealed = (self.status == "Sealed")

        # normalize sealed_rounds
        if self.status != "Sealed":
            # not sealed => sealed_rounds should not accumulate
            if self.sealed_rounds < 0:
                self.sealed_rounds = 0
        else:
            if self.sealed_rounds < 0:
                self.sealed_rounds = 0

    def anger(self) -> float:
        return _clamp01(_safe_float(self.emotional_state, "anger", 0.0))

    def joy(self) -> float:
        return _clamp01(_safe_float(self.emotional_state, "joy", 0.0))

    def set_anger(self, v: float) -> None:
        self.emotional_state["anger"] = _clamp01(v)

    def cooldown(self) -> None:
        # Decay anger each round
        self.set_anger(self.anger() - COOLDOWN_DECAY)


# =========================
# Logging
# =========================
_CSV_HEADER = [
    "ts_utc",
    "event",
    "agent",
    "peer",
    "detail",
]


def _init_csv_if_needed(csv_path: str) -> None:
    _ensure_parent_dir(csv_path)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(_CSV_HEADER)


def _log_txt(line: str) -> None:
    _ensure_parent_dir(TXT_PATH)
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _log_csv(event: str, agent: str = "", peer: str = "", detail: str = "") -> None:
    _init_csv_if_needed(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([_utc_ts(), event, agent, peer, detail])


def log_event(event: str, agent: str = "", peer: str = "", detail: str = "") -> None:
    ts = _utc_ts()
    _log_txt(f"[{ts}] {event} agent={agent} peer={peer} detail={detail}")
    _log_csv(event=event, agent=agent, peer=peer, detail=detail)


# =========================
# Core mechanics
# =========================
def _mean_priorities(agents: Iterable[AIAgent]) -> Dict[str, float]:
    agents_list = list(agents)
    if not agents_list:
        return {}
    keys: List[str] = sorted({k for a in agents_list for k in a.priorities.keys()})
    out: Dict[str, float] = {}
    for k in keys:
        vals = [float(a.priorities.get(k, 0.0)) for a in agents_list]
        out[k] = sum(vals) / max(1, len(vals))
    return out


def _nudge_toward(agent: AIAgent, target: Dict[str, float], rate: float) -> None:
    rate = _clamp01(rate)
    for k, v in target.items():
        cur = float(agent.priorities.get(k, 0.0))
        agent.priorities[k] = cur + (float(v) - cur) * rate


def _persuasion_threshold(persuader: AIAgent) -> float:
    # Higher threshold => harder to persuade
    t = float(PERSUASION_THRESHOLD)
    t += (1.0 - _clamp01(float(persuader.relativity))) * float(RELATIVITY_WEIGHT)
    t += persuader.anger() * float(ANGER_WEIGHT)
    return _clamp01(t)


def attempt_persuasion(
    persuader: AIAgent,
    target: AIAgent,
    rng: random.Random,
) -> bool:
    """
    Returns True on persuasion success.
    Simple model:
    - success probability = (1 - threshold) * (0.5 + 0.5 * relativity)
    """
    if persuader.status != "Active" or target.status != "Active":
        return False
    threshold = _persuasion_threshold(persuader)
    base = (1.0 - threshold)
    coop = 0.5 + 0.5 * _clamp01(float(persuader.relativity))
    p = _clamp01(base * coop)
    roll = rng.random()
    ok = roll < p
    log_event(
        "PERSUADE_ATTEMPT",
        agent=persuader.name,
        peer=target.name,
        detail=f"p={p:.3f} roll={roll:.3f} ok={ok}",
    )
    return ok


def seal_agent(agent: AIA_
