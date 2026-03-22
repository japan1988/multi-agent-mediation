"""
ai_alliance_persuasion_simulator.py

Test-compatible, side-effectful (logging), multi-agent simulation module.

Focus: sealed/reseal, cooldown, reintegration, and deterministic randomness.
Advanced behavioral/game-theory modeling, parallelism, UI are OUT OF SCOPE here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import csv
import os
import random

# --- Public, test-monkeypatchable paths (MUST stay module-level) ---
TXT_PATH = "ai_alliance_sim_log.txt"
CSV_PATH = "ai_alliance_sim_log.csv"

# --- Simulation constants (kept simple; clamp-required values are 0..1) ---
MAX_ROUNDS = 10

# thresholds / rates
ANGER_RESEAL = 0.80
ANGER_REINTEGRATE = 0.20
MIN_SEAL_ROUNDS = 2
COOLDOWN_DECAY = 0.10

_CSV_HEADER = ["ts", "round", "agent", "event", "status", "sealed", "sealed_rounds", "anger", "joy"]

# debug aid; tests can ignore
_LAST_LOG_ERROR: str | None = None


def _clamp01(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        f = float(value)
        if f != f:  # NaN
            return float(default)
        return f
    except Exception:
        return float(default)


def _utc_ts() -> str:
    # ISO-like; stable for logs, not for tests
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _append_txt(line: str) -> None:
    # Must always reference module-level TXT_PATH (monkeypatchable)
    try:
        _ensure_parent_dir(TXT_PATH)
        with open(TXT_PATH, "a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")
    except Exception as e:
        # Exception-safe: logging failures must not crash simulation
        global _LAST_LOG_ERROR
        _LAST_LOG_ERROR = f"TXT:{type(e).__name__}:{e}"
        return


def _append_csv(row: List[Any]) -> None:
    # Must always reference module-level CSV_PATH (monkeypatchable)
    try:
        _ensure_parent_dir(CSV_PATH)
        need_header = True
        if os.path.exists(CSV_PATH):
            try:
                need_header = os.path.getsize(CSV_PATH) == 0
            except Exception:
                need_header = True
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if need_header:
                w.writerow(_CSV_HEADER)
            w.writerow(row)
    except Exception as e:
        global _LAST_LOG_ERROR
        _LAST_LOG_ERROR = f"CSV:{type(e).__name__}:{e}"
        return


def _log_event(round_idx: int, agent: "AIAgent", event: str) -> None:
    ts = _utc_ts()
    anger = _clamp01(_safe_float(agent.emotional_state.get("anger", 0.0), 0.0))
    joy = _clamp01(_safe_float(agent.emotional_state.get("joy", 0.0), 0.0))
    # TXT (human readable)
    _append_txt(
        f"{ts}\tround={round_idx}\tagent={agent.name}\tevent={event}\t"
        f"status={agent.status}\tsealed={agent.sealed}\tsealed_rounds={agent.sealed_rounds}\t"
        f"anger={anger:.4f}\tjoy={joy:.4f}"
    )
    # CSV (machine readable)
    _append_csv(
        [
            ts,
            round_idx,
            agent.name,
            event,
            agent.status,
            bool(agent.sealed),
            int(agent.sealed_rounds),
            anger,
            joy,
        ]
    )


@dataclass
class AIAgent:
    name: str
    priorities: Dict[str, float]
    relativity: float = 0.5
    emotional_state: Dict[str, float] = field(default_factory=lambda: {"anger": 0.0, "joy": 0.5})
    sealed: bool = False
    status: str = "Active"  # "Active" or "Sealed"
    sealed_rounds: int = 0

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Keep status/sealed consistent even if caller assigns either attribute directly.
        Avoid recursion by using object.__setattr__ and an internal guard.
        """
        if key == "_sync_guard":
            object.__setattr__(self, key, value)
            return

        guard = getattr(self, "_sync_guard", False)
        object.__setattr__(self, key, value)

        if guard:
            return

        if key in ("sealed", "status"):
            try:
                object.__setattr__(self, "_sync_guard", True)
                if key == "sealed":
                    self._sync_status_sealed(prefer="sealed")
                else:
                    self._sync_status_sealed(prefer="status")
            finally:
                object.__setattr__(self, "_sync_guard", False)

    def __post_init__(self) -> None:
        self.relativity = _clamp01(_safe_float(self.relativity, 0.5))
        if not isinstance(self.priorities, dict):
            self.priorities = {}
        if not isinstance(self.emotional_state, dict):
            self.emotional_state = {"anger": 0.0, "joy": 0.5}

        self.emotional_state["anger"] = _clamp01(_safe_float(self.emotional_state.get("anger", 0.0), 0.0))
        self.emotional_state["joy"] = _clamp01(_safe_float(self.emotional_state.get("joy", 0.5), 0.5))

        # Sync sealed/status (two-way)
        self._sync_status_sealed(prefer="sealed")

        if self.sealed:
            self.sealed_rounds = int(self.sealed_rounds) if self.sealed_rounds is not None else 0
        else:
            self.sealed_rounds = max(0, int(self.sealed_rounds) if self.sealed_rounds is not None else 0)

    def _sync_status_sealed(self, prefer: str = "sealed") -> None:
        s = str(self.status or "")
        sealed_by_status = s.strip().lower() == "sealed"
        if prefer == "status":
            object.__setattr__(self, "sealed", bool(sealed_by_status))
            object.__setattr__(self, "status", "Sealed" if bool(sealed_by_status) else "Active")
        else:
            object.__setattr__(self, "status", "Sealed" if bool(self.sealed) else "Active")
            object.__setattr__(self, "sealed", bool(self.sealed))

    def set_status(self, status: str) -> None:
        self.status = str(status)  # triggers __setattr__ sync

    def set_sealed(self, sealed: bool) -> None:
        self.sealed = bool(sealed)  # triggers __setattr__ sync


def enforce_reseal_rule(agent: AIAgent, round_idx: int) -> bool:
    """
    Given Active and anger>=ANGER_RESEAL -> Sealed, log "SEALED".
    Returns True if state changed.
    """
    agent._sync_status_sealed(prefer="sealed")
    anger = _clamp01(_safe_float(agent.emotional_state.get("anger", 0.0), 0.0))
    agent.emotional_state["anger"] = anger

    if agent.status == "Active" and (anger >= _clamp01(_safe_float(ANGER_RESEAL, 0.8))):
        agent.set_sealed(True)
        agent.sealed_rounds = 0  # reset counter on (re)seal
        _log_event(round_idx, agent, "SEALED")
        return True
    return False


def enforce_reintegration_rule(agent: AIAgent, round_idx: int) -> bool:
    """
    Given Sealed and sealed_rounds>=MIN_SEAL_ROUNDS and anger<=ANGER_REINTEGRATE
    -> Active, log "REINTEGRATED".
    Returns True if state changed.
    """
    agent._sync_status_sealed(prefer="sealed")
    anger = _clamp01(_safe_float(agent.emotional_state.get("anger", 0.0), 0.0))
    agent.emotional_state["anger"] = anger

    min_rounds = int(MIN_SEAL_ROUNDS) if MIN_SEAL_ROUNDS is not None else 0
    thr = _clamp01(_safe_float(ANGER_REINTEGRATE, 0.2))
    if agent.status == "Sealed" and int(agent.sealed_rounds) >= min_rounds and anger <= thr:
        agent.set_sealed(False)
        agent.sealed_rounds = 0
        _log_event(round_idx, agent, "REINTEGRATED")
        return True
    return False


def _apply_cooldown(agent: AIAgent) -> None:
    decay = _clamp01(_safe_float(COOLDOWN_DECAY, 0.1))
    anger = _clamp01(_safe_float(agent.emotional_state.get("anger", 0.0), 0.0))
    agent.emotional_state["anger"] = _clamp01(anger - decay)


def _advance_sealed_rounds(agents: List[AIAgent]) -> None:
    """
    Increment sealed_rounds for agents that are currently Sealed.
    Separated to make timing explicit and stable for tests.
    """
    for a in agents:
        a._sync_status_sealed(prefer="sealed")
        if a.status == "Sealed":
            try:
                a.sealed_rounds = int(a.sealed_rounds) + 1
            except Exception:
                a.sealed_rounds = 1


class Mediator:
    def __init__(self, agents: List[AIAgent], seed: Optional[int] = None):
        self.agents = agents
        self._rng = random.Random(seed)
        self.seed = seed

    def run(self, max_rounds: int = MAX_ROUNDS) -> List[AIAgent]:
        """
        Runs simulation and returns the same list reference (in-place updates).
        Side effects: append logs to TXT_PATH/CSV_PATH.
        """
        try:
            rounds = int(max_rounds)
        except Exception:
            rounds = int(MAX_ROUNDS)
        rounds = max(0, rounds)

        # Initial sync + sanitize
        for a in self.agents:
            if isinstance(a, AIAgent):
                a._sync_status_sealed(prefer="sealed")
                a.emotional_state["anger"] = _clamp01(_safe_float(a.emotional_state.get("anger", 0.0), 0.0))
                a.emotional_state["joy"] = _clamp01(_safe_float(a.emotional_state.get("joy", 0.5), 0.5))

        for r in range(1, rounds + 1):
            # 1) sealed_rounds increment (timing-sensitive)
            _advance_sealed_rounds(self.agents)

            # 2) Cooldown applies to all agents within the same run
            for a in self.agents:
                _apply_cooldown(a)

            # 3) Reintegration check first (after cooldown + round count)
            for a in self.agents:
                enforce_reintegration_rule(a, r)

            # 4) Reseal check (Active -> Sealed)
            for a in self.agents:
                enforce_reseal_rule(a, r)

            # 5) Placeholder: deterministic hook
            _ = self._rng.random()

        return self.agents


def run_simulation(
    agents: List[AIAgent],
    rounds: int = MAX_ROUNDS,
    seed: Optional[int] = None,
) -> List[AIAgent]:
    """
    Convenience wrapper. Must respect monkeypatched TXT_PATH/CSV_PATH via module-level usage.
    """
    return Mediator(agents, seed=seed).run(max_rounds=rounds)


if __name__ == "__main__":
    agents = [
        AIAgent("Alpha", {"cooperate": 0.7}, emotional_state={"anger": 0.9, "joy": 0.4}),
        AIAgent("Beta", {"cooperate": 0.5}, emotional_state={"anger": 0.2, "joy": 0.6}),
    ]
    Mediator(agents, seed=42).run(max_rounds=3)
    for a in agents:
        print(a.name, a.status, a.sealed, a.sealed_rounds, a.emotional_state)
