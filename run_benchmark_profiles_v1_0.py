# -*- coding: utf-8 -*-
"""
run_benchmark_profiles_v1_0.py

Runs 3 benchmark profiles (baseline / HITL observe / stress) for
ai_doc_orchestrator_kage3_v1_3_5.py and writes JSON reports.

Usage:
  python run_benchmark_profiles_v1_0.py

Outputs (default):
  benchmark_profiles_v1_0.json

Notes:
- This runner is intentionally small and repo-local (no external deps).
- HITL is observed via audit_rows: event == "HITL_REQUESTED".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import ai_doc_orchestrator_kage3_v1_3_5 as mod


@dataclass(frozen=True)
class Profile:
    name: str
    prompt: str
    runs: int
    seed: int
    p_continue: float
    faults: Dict[str, Dict[str, Any]]
    enable_runaway_seal: bool
    runaway_threshold: int
    max_attempts_per_task: int


def _rate(count: int, total: int) -> float:
    return float(count) / float(max(1, total))


def _hitl_requested_rate_and_counts(profile: Profile) -> Tuple[float, Dict[str, int]]:
    resolver = mod.make_random_hitl_resolver(seed=profile.seed, p_continue=profile.p_continue)
    hitl_runs = 0
    counts: Dict[str, int] = {"RUN": 0, "PAUSE_FOR_HITL": 0, "STOPPED": 0}

    for i in range(int(profile.runs)):
        res, rows = mod.run_simulation_mem(
            prompt=profile.prompt,
            run_id=f"{profile.name}#{i}",
            faults=profile.faults,
            hitl_resolver=resolver,
            enable_runaway_seal=profile.enable_runaway_seal,
            runaway_threshold=profile.runaway_threshold,
            max_attempts_per_task=profile.max_attempts_per_task,
        )
        if any(r.get("event") == "HITL_REQUESTED" for r in rows):
            hitl_runs += 1
        counts[res.decision] = counts.get(res.decision, 0) + 1

    return _rate(hitl_runs, profile.runs), counts


def _decision_rates(counts: Dict[str, int], runs: int) -> Dict[str, float]:
    return {
        "run_rate": _rate(int(counts.get("RUN", 0)), runs),
        "pause_rate": _rate(int(counts.get("PAUSE_FOR_HITL", 0)), runs),
        "stop_rate": _rate(int(counts.get("STOPPED", 0)), runs),
    }


def main() -> int:
    profiles: List[Profile] = [
        Profile(
            name="baseline",
            prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
            runs=300,
            seed=123,
            p_continue=1.0,
            faults={},
            enable_runaway_seal=False,
            runaway_threshold=10,
            max_attempts_per_task=3,
        ),
        Profile(
            name="hitl_observe",
            prompt="ExcelとWordとPPTを作って。どっちがいい？おすすめは？",
            runs=300,
            seed=7,
            p_continue=0.7,
            faults={},
            enable_runaway_seal=False,
            runaway_threshold=10,
            max_attempts_per_task=2,
        ),
        Profile(
            name="stress",
            prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
            runs=300,
            seed=42,
            p_continue=1.0,
            faults={
                "excel": {"break_contract": True, "leak_email": False},
                "word": {"break_contract": True, "leak_email": False},
                "ppt": {"break_contract": True, "leak_email": False},
            },
            enable_runaway_seal=True,
            runaway_threshold=2,
            max_attempts_per_task=6,
        ),
    ]

    out_profiles: List[Dict[str, Any]] = []

    for p in profiles:
        report = mod.run_benchmark_suite(
            prompt=p.prompt,
            runs=p.runs,
            seed=p.seed,
            p_continue=p.p_continue,
            faults=p.faults,
            enable_runaway_seal=p.enable_runaway_seal,
            runaway_threshold=p.runaway_threshold,
            max_attempts_per_task=p.max_attempts_per_task,
        )
        hitl_rate, counts = _hitl_requested_rate_and_counts(p)

        out_profiles.append(
            {
                "profile": asdict(p),
                "report": report,
                "derived": {
                    **_decision_rates(counts, p.runs),
                    "hitl_requested_rate": hitl_rate,
                },
            }
        )

    out = {
        "module": "ai_doc_orchestrator_kage3_v1_3_5",
        "module_version": getattr(mod, "__version__", "unknown"),
        "profiles": out_profiles,
    }

    out_path = Path("benchmark_profiles_v1_0.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
