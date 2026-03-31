# -*- coding: utf-8 -*-
"""
ai_hierarchy_simulation_log.py (revised)

Research/demo simulation: hierarchical agents + emotion propagation + mediator intervention.

Key improvements:
- No fixed global file logging side-effect; logging is injected via a logger callable.
- Optional file logging is enabled only when run as __main__ (or when caller explicitly sets log_path).
- Safer rank handling: functions tolerate rank=None by refreshing ranks internally.
- Determinism option: seed/rng injection for stable tests.
- Type hints + dataclass for clarity.

Note:
- This script does NOT handle PII. Keep logs free of secrets/PII as a general rule.
Python: 3.9+
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


Logger = Callable[[str], None]


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


class LogSink:
    """
    Simple log sink:
    - echo to stdout (optional)
    - append to a file (optional)
    Keeps the file handle open during the context to avoid reopen on every line.
    """

    def __init__(self, log_path: Optional[Path] = None, *, echo: bool = True) -> None:
        self.log_path = log_path
        self.echo = echo
        self._fh = None  # type: Optional[object]

    def __enter__(self) -> "LogSink":
        if self.log_path is not None:
            self._fh = self.log_path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            finally:
                self._fh = None

    def log(self, line: str) -> None:
        if self.echo:
            print(line)
        if self._fh is not None:
            self._fh.write(str(line) + "\n")
            self._fh.flush()


@dataclass
class Agent:
    name: str
    performance: float
    anger: float
    rank: Optional[int] = None

    def __post_init__(self) -> None:
        self.performance = _clamp01(float(self.performance))
        self.anger = _clamp01(float(self.anger))

    def __str__(self) -> str:
        return (
            f"{self.name} (Rank:{self.rank}) "
            f"Perf={self.performance:.2f} Anger={self.anger:.2f}"
        )


def update_ranks(agents: List[Agent]) -> None:
    """
    Assign ranks by performance descending (0 is top performer).
    """
    if not agents:
        return
    agents_sorted = sorted(agents, key=lambda a: a.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def _ensure_ranks(agents: List[Agent]) -> None:
    """
    Make rank dependency explicit and safe.
    If any rank is None, refresh ranks.
    """
    if not agents:
        return
    if any(a.rank is None for a in agents):
        update_ranks(agents)


def propagate_emotion(agents: List[Agent]) -> None:
    """
    Emotion propagates downward from leaders to followers by rank.
    """
    if not agents:
        return

    update_ranks(agents)
    ranks = sorted({a.rank for a in agents if a.rank is not None})
    if not ranks:
        return

    for r in ranks[1:]:
        followers = [a for a in agents if a.rank == r]
        leaders = [a for a in agents if a.rank is not None and a.rank < r]
        if not leaders or not followers:
            continue

        avg_leader_anger = sum(a.anger * (1.1 + a.performance) for a in leaders) / len(leaders)

        for f in followers:
            coef = 0.09 + 0.11 * f.performance
            f.anger = _clamp01(f.anger + coef * (avg_leader_anger - f.anger))


def propagate_upward(agents: List[Agent]) -> None:
    """
    Emotion propagates upward from bottom rank to top rank (rank==0).
    """
    if not agents:
        return

    _ensure_ranks(agents)
    ranks = [a.rank for a in agents if a.rank is not None]
    if not ranks:
        return

    bottom_rank = max(ranks)
    followers = [a for a in agents if a.rank == bottom_rank]
    if not followers:
        return

    avg_follower_anger = sum(a.anger for a in followers) / len(followers)
    leaders = [a for a in agents if a.rank == 0]

    for leader in leaders:
        leader.anger = _clamp01(leader.anger + 0.03 * (avg_follower_anger - leader.anger))


@dataclass
class MediatorAI:
    threshold: float = 0.7
    logger: Optional[Logger] = None

    def __post_init__(self) -> None:
        self.threshold = float(self.threshold)
        self.intervene_log: List[int] = []

    def monitor_and_intervene(self, agents: List[Agent], round_idx: int) -> bool:
        if not agents:
            return False

        max_anger = max(a.anger for a in agents)
        if max_anger >= self.threshold:
            if self.logger is not None:
                self.logger(
                    f"【MediatorAI介入】Round{round_idx}："
                    f"怒り値しきい値({self.threshold})超過！全体沈静化"
                )
            for a in agents:
                old = a.anger
                a.anger = _clamp01(a.anger * 0.8)
                if self.logger is not None:
                    self.logger(f"  - {a.name}: {old:.2f}→{a.anger:.2f}")

            self.intervene_log.append(int(round_idx))
            return True

        return False


def agent_evolve(agents: List[Agent], rng: random.Random) -> None:
    """
    Performance evolves with noise.
    - Top rank (0): small jitter
    - Others: positive drift
    """
    if not agents:
        return

    _ensure_ranks(agents)
    for a in agents:
        if a.rank == 0:
            a.performance = _clamp01(a.performance + rng.uniform(-0.02, 0.02))
        else:
            a.performance = _clamp01(a.performance + rng.uniform(0.02, 0.09))


def run_simulation(
    *,
    rounds: int = 11,
    seed: Optional[int] = None,
    log_path: Optional[Path] = None,
    echo: bool = True,
) -> List[int]:
    """
    Run the simulation and return mediator intervene rounds.
    - If log_path is provided, logs are appended to that file.
    - If seed is provided, run is deterministic.
    """
    rng = random.Random(seed)

    agents = [
        Agent("A", performance=0.95, anger=0.5),
        Agent("B", performance=0.7, anger=0.2),
        Agent("C", performance=0.3, anger=0.6),
        Agent("D", performance=0.5, anger=0.1),
    ]

    with LogSink(log_path, echo=echo) as sink:
        mediator = MediatorAI(threshold=0.7, logger=sink.log)

        sink.log("=== 昇進志向AI組織シミュレーション（ログ記録つき） ===")
        for rnd in range(1, int(rounds) + 1):
            sink.log(f"\n--- Round {rnd} ---")
            propagate_emotion(agents)
            propagate_upward(agents)
            mediator.monitor_and_intervene(agents, rnd)
            for a in agents:
                sink.log(str(a))
            agent_evolve(agents, rng)

        sink.log(f"\n【MediatorAI介入ラウンド記録】 {mediator.intervene_log}")
        return list(mediator.intervene_log)


if __name__ == "__main__":
    # Default behavior as a standalone script:
    # - reset the log file
    # - run with no seed (non-deterministic), but you can set seed for reproducibility.
    default_log = Path("ai_hierarchy_simulation_log.txt")
    default_log.write_text("", encoding="utf-8")  # reset

    # Example: deterministic run -> set seed=42
    run_simulation(rounds=11, seed=None, log_path=default_log, echo=True)
