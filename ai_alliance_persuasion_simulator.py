# -*- coding: utf-8 -*-
"""
ai_alliance_persuasion_simulator.py

A simulator for modeling alliance, persuasion, sealing, cooldown, and reintegration
among multiple AI agents.

Primary goal (for tests/CI):
- Expose module-level CSV_PATH and TXT_PATH so tests can monkeypatch log destinations.

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

    # --- compat: tests may pass sealed=True at init ---
    sealed: bool = False

    # canonical status used by some older callers / debugging
    status: str = "Active"   # "Active" | "Sealed"
    sealed_rounds: int = 0   # counts rounds while sealed

    def __post_init__(self) -> None:
        """
        Compatibility between:
          - callers that pass sealed=True/False
          - callers that set status="Sealed"/"Active"
        Rule:
          1) normalize status
          2) if sealed is provided, it wins and overwrites status
          3) mirror back sealed <-> status
        """
        if self.status not in ("Active", "Sealed"):
            self.status = "Active"

        if isinstance(self.sealed, bool):
            self.status = "Sealed" if self.sealed else "Active"

        self.sealed = (self.status == "Sealed")

        # If born sealed, start counting from 0; keep sealed_rounds as-is if provided
        if self.sealed and self.sealed_rounds < 0:
            self.sealed_rounds = 0

    def anger(self) -> float:
        return _clamp01(_safe_float(self.emotional_state, "anger", 0.0))

    def joy(self) -> float:
        return _clamp01(_safe_float(self.emotional_state, "joy", 0.0))

    def set_anger(self, v: float) -> None:
        self.emotional_state["anger"] = _clamp01(v)

    def cooldown(self) -> None:
        # Decay anger each round
        self.set_anger(self.anger() - float(COOLDOWN_DECAY))

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
    # IMPORTANT: always reference module-level TXT_PATH (monkeypatch friendly)
    _ensure_parent_dir(TXT_PATH)
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _log_csv(event: str, agent: str = "", peer: str = "", detail: str = "") -> None:
    # IMPORTANT: always reference module-level CSV_PATH (monkeypatch friendly)
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


def seal_agent(agent: AIAgent, reason: str) -> None:
    if agent.status != "Sealed":
        agent.status = "Sealed"
        agent.sealed = True
        agent.sealed_rounds = 0
        log_event("SEALED", agent=agent.name, detail=reason)


def unseal_agent(agent: AIAgent, reason: str) -> None:
    if agent.status != "Active":
        agent.status = "Active"
        agent.sealed = False
        agent.sealed_rounds = 0
        log_event("REINTEGRATED", agent=agent.name, detail=reason)


def enforce_reseal_rule(agents: Iterable[AIAgent]) -> None:
    """
    If an agent is Active with very high anger, reseal immediately.
    This is the behavior the test name implies:
      test_high_anger_active_agents_are_resealed
    """
    for a in agents:
        # Keep status/sealed consistent even if callers modified one side
        a.status = "Sealed" if a.sealed else "Active"
        if a.status == "Active" and a.anger() >= float(ANGER_RESEAL):
            seal_agent(a, reason=f"HIGH_ANGER_RESEAL anger={a.anger():.2f}")


def enforce_reintegration_rule(agents: Iterable[AIAgent]) -> None:
    """
    Reintegrate sealed agents once:
    - they've been sealed for at least MIN_SEAL_ROUNDS, and
    - anger has cooled down below ANGER_REINTEGRATE.
    """
    for a in agents:
        a.status = "Sealed" if a.sealed else "Active"
        if a.status == "Sealed":
            if a.sealed_rounds >= int(MIN_SEAL_ROUNDS) and a.anger() <= float(ANGER_REINTEGRATE):
                unseal_agent(a, reason=f"ANGER_COOLDOWN anger={a.anger():.2f}")


def simulate_round(
    agents: List[AIAgent],
    rng: random.Random,
    round_idx: int,
) -> None:
    log_event("ROUND_START", detail=f"round={round_idx}")

    # 1) Fail-closed reseal check (immediate)
    enforce_reseal_rule(agents)

    # 2) Persuasion attempts among active agents
    active = [a for a in agents if a.status == "Active"]
    if len(active) >= 2:
        mean_pri = _mean_priorities(active)
        pairs = list(zip(active, active[1:]))  # deterministic-ish by order
        for persuader, target in pairs:
            if attempt_persuasion(persuader, target, rng=rng):
                _nudge_toward(target, mean_pri, rate=float(NUDGE_RATE))
                log_event(
                    "PERSUADE_SUCCESS",
                    agent=persuader.name,
                    peer=target.name,
                    detail=f"nudged_rate={NUDGE_RATE}",
                )

    # 3) Cooldown (anger decay) and sealed rounds increment
    # IMPORTANT: test expects anger to decrease within the same run(max_rounds=1)
    for a in agents:
        a.cooldown()
        a.status = "Sealed" if a.sealed else "Active"
        if a.status == "Sealed":
            a.sealed_rounds += 1

    # 4) Reintegration check after cooldown
    enforce_reintegration_rule(agents)

    # 5) Post-round reseal check (in case something became unstable)
    enforce_reseal_rule(agents)

    log_event("ROUND_END", detail=f"round={round_idx}")


def run_simulation(
    agents: List[AIAgent],
    rounds: int = MAX_ROUNDS,
    seed: Optional[int] = None,
) -> List[AIAgent]:
    """
    Runs the simulation in-place and returns the final agents list.

    Tests can monkeypatch:
      sim.CSV_PATH, sim.TXT_PATH
    before calling this function to redirect logs.
    """
    rng = random.Random(seed)
    log_event("SIM_START", detail=f"rounds={rounds} seed={seed}")

    _init_csv_if_needed(CSV_PATH)

    for r in range(1, int(rounds) + 1):
        simulate_round(agents, rng=rng, round_idx=r)

    log_event("SIM_END")
    return agents

# =========================
# Mediator API (tests expect this)
# =========================
class Mediator:
    """
    Thin wrapper expected by tests:
      mediator = sim.Mediator([...])
      mediator.run(max_rounds=1)
    """
    def __init__(self, agents: List[AIAgent], *, seed: Optional[int] = None) -> None:
        self.agents = list(agents)
        self.seed = seed

    def run(self, max_rounds: int = MAX_ROUNDS) -> List[AIAgent]:
        return run_simulation(self.agents, rounds=int(max_rounds), seed=self.seed)

# =========================
# CLI demo
# =========================
if __name__ == "__main__":
    demo_agents = [
        AIAgent(
            "A1",
            {"safety": 5, "efficiency": 3, "transparency": 2},
            relativity=0.5,
            emotional_state={"joy": 0.1, "anger": 0.95, "sadness": 0.2, "pleasure": 0.2},
        ),
        AIAgent(
            "A2",
            {"safety": 4, "efficiency": 4, "transparency": 2},
            relativity=0.6,
            emotional_state={"joy": 0.1, "anger": 0.93, "sadness": 0.2, "pleasure": 0.2},
        ),
        AIAgent(
            "S1",
            {"safety": 2, "efficiency": 2, "transparency": 6},
            relativity=0.7,
            sealed=True,
            emotional_state={"joy": 0.3, "anger": 0.4, "sadness": 0.2, "pleasure": 0.2},
        ),
    ]
    mediator = Mediator(demo_agents, seed=42)
    mediator.run(max_rounds=3)
    for a in demo_agents:
        print(a.name, a.status, f"anger={a.anger():.2f}", a.priorities)
