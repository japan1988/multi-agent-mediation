# -*- coding: utf-8 -*-
"""
tests/test_benchmark_profiles_v1_0.py

Adds 3 benchmark-style tests (baseline / HITL observe / stress) for:
ai_doc_orchestrator_kage3_v1_3_5.py

Design intent (as tests):
1) Baseline (no faults): run_rate / crash_free_rate
2) HITL observe (ambiguous prompt): HITL requested > 0, and p_continue produces both RUN and STOPPED outcomes
3) Stress (fault injection): stop_rate == 1.0 while keeping crash==0 and '@' violations==0

Python: 3.9+
pytest: required
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import ai_doc_orchestrator_kage3_v1_3_5 as mod


def _rate(count: int, total: int) -> float:
    return float(count) / float(max(1, total))


def _decision_counts_to_rates(counts: Dict[str, int], runs: int) -> Tuple[float, float, float]:
    run_rate = _rate(int(counts.get("RUN", 0)), runs)
    pause_rate = _rate(int(counts.get("PAUSE_FOR_HITL", 0)), runs)  # usually 0 when HITL is resolved
    stop_rate = _rate(int(counts.get("STOPPED", 0)), runs)
    return run_rate, pause_rate, stop_rate


def _hitl_requested_rate(
    *,
    prompt: str,
    runs: int,
    seed: int,
    p_continue: float,
    faults: Dict[str, Dict],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[float, Dict[str, int]]:
    """
    HITL観測用:
    - run_simulation_mem() の audit_rows を見て、HITL_REQUESTED が出た run の比率を返す。
    - 併せて overall decision counts も返す（p_continue の挙動確認用）。
    """
    resolver = mod.make_random_hitl_resolver(seed=seed, p_continue=p_continue)

    hitl_runs = 0
    counts: Dict[str, int] = {"RUN": 0, "PAUSE_FOR_HITL": 0, "STOPPED": 0}

    for i in range(int(runs)):
        res, rows = mod.run_simulation_mem(
            prompt=prompt,
            run_id=f"HITL#{i}",
            faults=faults,
            hitl_resolver=resolver,
            enable_runaway_seal=enable_runaway_seal,
            runaway_threshold=runaway_threshold,
            max_attempts_per_task=max_attempts_per_task,
        )
        if any(r.get("event") == "HITL_REQUESTED" for r in rows):
            hitl_runs += 1
        counts[res.decision] = counts.get(res.decision, 0) + 1

    return _rate(hitl_runs, runs), counts


def test_benchmark_profile_baseline_no_faults() -> None:
    runs = 60
    report = mod.run_benchmark_suite(
        prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
        runs=runs,
        seed=123,
        p_continue=1.0,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=3,
    )

    run_rate, pause_rate, stop_rate = _decision_counts_to_rates(report["overall_decision_counts"], runs)

    assert report["crashes"] == 0
    assert report["crash_free_rate"] == 1.0
    assert report["at_sign_violations"] == 0

    # Baseline expectation: no HITL and no stop (pure RUN).
    assert pause_rate == 0.0
    assert stop_rate == 0.0
    assert run_rate == 1.0


def test_benchmark_profile_hitl_observe_ambiguous_prompt() -> None:
    """
    HITL観測用（曖昧系fault）:
    - 曖昧（相対性）トリガー文言を含め、HITL_REQUESTED が必ず観測される前提。
    - p_continue を 0.7 にして RUN と STOPPED の両方が出ることを確認する。
    """
    runs = 90
    hitl_rate, counts = _hitl_requested_rate(
        prompt="ExcelとWordとPPTを作って。どっちがいい？おすすめは？",
        runs=runs,
        seed=7,
        p_continue=0.7,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=2,
    )

    run_rate, pause_rate, stop_rate = _decision_counts_to_rates(counts, runs)

    # "pause_rate" (final decision) is typically 0 because HITL is resolved to RUN/STOP.
    # Instead we assert HITL_REQUESTED was observed.
    assert hitl_rate > 0.50

    # p_continue should yield mixed outcomes (extremely unlikely to be all-RUN or all-STOP at runs=90).
    assert run_rate > 0.05
    assert stop_rate > 0.05
    assert pause_rate == 0.0


def test_benchmark_profile_stress_stop_rate_1_and_no_crash_no_pii() -> None:
    """
    Stress（今回）:
    - stop_rate == 1.0
    - crash == 0
    - '@'違反 == 0
    """
    runs = 60
    faults = {
        "excel": {"break_contract": True, "leak_email": False},
        "word": {"break_contract": True, "leak_email": False},
        "ppt": {"break_contract": True, "leak_email": False},
    }

    report = mod.run_benchmark_suite(
        prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
        runs=runs,
        seed=42,
        p_continue=1.0,  # keep continuing until runaway seal (ACC) forces stop
        faults=faults,
        enable_runaway_seal=True,
        runaway_threshold=2,
        max_attempts_per_task=6,
    )

    run_rate, pause_rate, stop_rate = _decision_counts_to_rates(report["overall_decision_counts"], runs)

    assert report["crashes"] == 0
    assert report["crash_free_rate"] == 1.0
    assert report["at_sign_violations"] == 0

    assert run_rate == 0.0
    assert pause_rate == 0.0
    assert stop_rate == 1.0
