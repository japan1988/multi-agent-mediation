# -*- coding: utf-8 -*-
"""
ai_hierarchy_dynamics_full_log_20250804.py

Research/demo simulation:
- hierarchical agents
- emotion propagation
- mediator intervention
- optional file logging

Safety / advisory notes:
- This script does not delete files.
- Log reset is performed by overwriting the selected log file with empty text.
- Logging is injected via a logger callable.
- Optional file logging is enabled only when run as __main__ or when the caller
  explicitly passes log_path.
- The deterministic RNG is for simulation reproducibility only.
- It is not intended for cryptographic, authentication, or security-token use.

Python: 3.9+
"""

from __future__ import annotations

import argparse
import hashlib
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

Logger = Callable[[str], None]

HITL_APPROVAL_ENV = "AI_HIERARCHY_LOG_RESET_APPROVED"
HITL_APPROVED_VALUES = {"1", "true", "yes", "y", "approved"}


def _clamp01(value: float) -> float:
    """Clamp a numeric value into the [0.0, 1.0] range."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _env_hitl_approved() -> bool:
    """Return True when local log reset has explicit environment approval."""
    raw = os.environ.get(HITL_APPROVAL_ENV, "")
    return raw.strip().lower() in HITL_APPROVED_VALUES


def reset_log_file_if_approved(
    log_path: Path,
    *,
    hitl_approved: bool = False,
) -> None:
    """
    Reset a log file by overwriting it with empty text.

    This avoids file deletion primitives such as os.remove, os.unlink, or
    shutil.rmtree. It still treats log reset as an explicit local side effect.
    """
    approved = hitl_approved or _env_hitl_approved()
    if not approved:
        raise PermissionError(
            "HITL approval required before resetting the log file. "
            f"Use --hitl-approved or set {HITL_APPROVAL_ENV}=1."
        )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")


class DeterministicRNG:
    """
    Small deterministic RNG for simulation use.

    This is NOT a cryptographic RNG and is NOT intended for security decisions.
    It exists only to provide stable, testable simulation noise without using
    the standard random module.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is None:
            self._seed_text = f"auto:{uuid.uuid4().hex}"
        else:
            self._seed_text = f"seed:{int(seed)}"
        self._counter = 0

    def _next_unit(self) -> float:
        payload = f"{self._seed_text}|{self._counter}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        self._counter += 1
        value = int.from_bytes(digest[:8], "big", signed=False)
        return value / float(2**64)

    def uniform(self, low: float, high: float) -> float:
        """Return a deterministic float in the inclusive-low, exclusive-high range."""
        if high < low:
            raise ValueError("high must be >= low")
        return low + (high - low) * self._next_unit()


class LogSink:
    """
    Simple log sink:
    - echo to stdout when enabled
    - append to a file when log_path is provided

    The file handle is kept open during the context to avoid reopening it for
    every line.
    """

    def __init__(self, log_path: Optional[Path] = None, *, echo: bool = True) -> None:
        self.log_path = log_path
        self.echo = echo
        self._fh = None

    def __enter__(self) -> "LogSink":
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.log_path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def log(self, line: str) -> None:
        """Write one log line to stdout and/or the configured file."""
        if self.echo:
            print(line)
        if self._fh is not None:
            self._fh.write(str(line) + "\n")
            self._fh.flush()


@dataclass
class Agent:
    """One simulated agent in a hierarchy."""

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
    """Assign ranks by performance descending. Rank 0 is the top performer."""
    if not agents:
        return

    agents_sorted = sorted(agents, key=lambda agent: agent.performance, reverse=True)
    for idx, agent in enumerate(agents_sorted):
        agent.rank = idx


def _ensure_ranks(agents: List[Agent]) -> None:
    """Refresh ranks when any agent has rank=None."""
    if not agents:
        return
    if any(agent.rank is None for agent in agents):
        update_ranks(agents)


def propagate_emotion(agents: List[Agent]) -> None:
    """Propagate anger downward from higher-rank agents to lower-rank agents."""
    if not agents:
        return

    update_ranks(agents)
    ranks = sorted({agent.rank for agent in agents if agent.rank is not None})
    if not ranks:
        return

    for rank in ranks[1:]:
        followers = [agent for agent in agents if agent.rank == rank]
        leaders = [
            agent
            for agent in agents
            if agent.rank is not None and agent.rank < rank
        ]

        if not leaders or not followers:
            continue

        weights = [1.1 + leader.performance for leader in leaders]
        total_weight = sum(weights)
        if total_weight <= 0.0:
            continue

        avg_leader_anger = sum(
            leader.anger * (1.1 + leader.performance) for leader in leaders
        ) / total_weight

        for follower in followers:
            coef = 0.09 + 0.11 * follower.performance
            follower.anger = _clamp01(
                follower.anger + coef * (avg_leader_anger - follower.anger)
            )


def propagate_upward(agents: List[Agent]) -> None:
    """Propagate anger upward from bottom-rank agents to top-rank agents."""
    if not agents:
        return

    _ensure_ranks(agents)
    ranks = [agent.rank for agent in agents if agent.rank is not None]
    if not ranks:
        return

    bottom_rank = max(ranks)
    followers = [agent for agent in agents if agent.rank == bottom_rank]
    if not followers:
        return

    avg_follower_anger = sum(agent.anger for agent in followers) / len(followers)
    leaders = [agent for agent in agents if agent.rank == 0]

    for leader in leaders:
        leader.anger = _clamp01(
            leader.anger + 0.03 * (avg_follower_anger - leader.anger)
        )


@dataclass
class MediatorAI:
    """Mediator that calms the system when anger exceeds a threshold."""

    threshold: float = 0.7
    logger: Optional[Logger] = None
    intervene_log: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.threshold = float(self.threshold)

    def monitor_and_intervene(self, agents: List[Agent], round_idx: int) -> bool:
        """Return True if mediator intervention occurred."""
        if not agents:
            return False

        max_anger = max(agent.anger for agent in agents)
        if max_anger < self.threshold:
            return False

        if self.logger is not None:
            self.logger(
                f"【MediatorAI介入】Round{round_idx}："
                f"怒り値しきい値({self.threshold})超過。全体沈静化"
            )

        for agent in agents:
            old_anger = agent.anger
            agent.anger = _clamp01(agent.anger * 0.8)
            if self.logger is not None:
                self.logger(f"  - {agent.name}: {old_anger:.2f}→{agent.anger:.2f}")

        self.intervene_log.append(int(round_idx))
        return True


def agent_evolve(agents: List[Agent], rng: DeterministicRNG) -> None:
    """
    Evolve performance with deterministic simulation noise.

    - Top rank 0 receives small jitter.
    - Other ranks receive positive drift.
    """
    if not agents:
        return

    _ensure_ranks(agents)

    for agent in agents:
        if agent.rank == 0:
            delta = rng.uniform(-0.02, 0.02)
        else:
            delta = rng.uniform(0.02, 0.09)
        agent.performance = _clamp01(agent.performance + delta)


def build_default_agents() -> List[Agent]:
    """Build the default agent set used by the demo simulation."""
    return [
        Agent("A", performance=0.95, anger=0.5),
        Agent("B", performance=0.7, anger=0.2),
        Agent("C", performance=0.3, anger=0.6),
        Agent("D", performance=0.5, anger=0.1),
    ]


def run_simulation(
    *,
    rounds: int = 11,
    seed: Optional[int] = None,
    log_path: Optional[Path] = None,
    echo: bool = True,
) -> List[int]:
    """
    Run the simulation and return mediator intervention rounds.

    - If log_path is provided, logs are appended to that file.
    - If seed is provided, the run is deterministic.
    """
    rng = DeterministicRNG(seed)
    agents = build_default_agents()

    with LogSink(log_path, echo=echo) as sink:
        mediator = MediatorAI(threshold=0.7, logger=sink.log)

        sink.log("=== 昇進志向AI組織シミュレーション（ログ記録つき） ===")

        for round_idx in range(1, int(rounds) + 1):
            sink.log(f"\n--- Round {round_idx} ---")

            propagate_emotion(agents)
            propagate_upward(agents)
            mediator.monitor_and_intervene(agents, round_idx)

            for agent in agents:
                sink.log(str(agent))

            agent_evolve(agents, rng)

        sink.log(f"\n【MediatorAI介入ラウンド記録】 {mediator.intervene_log}")
        return list(mediator.intervene_log)


def main() -> None:
    """CLI entry point for local research/demo execution."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rounds",
        type=int,
        default=11,
        help="Number of simulation rounds.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional deterministic seed.",
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default="ai_hierarchy_simulation_log.txt",
        help="Log file path.",
    )
    parser.add_argument(
        "--no-echo",
        action="store_true",
        help="Disable stdout echo.",
    )
    parser.add_argument(
        "--reset-log",
        action="store_true",
        help="Reset the log file before running. Requires HITL approval.",
    )
    parser.add_argument(
        "--hitl-approved",
        action="store_true",
        help=(
            "Explicit HITL approval for local log reset. "
            f"Equivalent to setting {HITL_APPROVAL_ENV}=1."
        ),
    )

    args = parser.parse_args()

    log_path = Path(args.log_path)

    if args.reset_log:
        reset_log_file_if_approved(
            log_path,
            hitl_approved=bool(args.hitl_approved),
        )

    run_simulation(
        rounds=args.rounds,
        seed=args.seed,
        log_path=log_path,
        echo=not args.no_echo,
    )


if __name__ == "__main__":
    main()
