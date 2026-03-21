# -*- coding: utf-8 -*-
"""
run_benchmark_kage3_v1_3_5.py

Benchmark runner for ai_doc_orchestrator_kage3_v1_3_5.py

Outputs:
- benchmark_report_sample_v1_3_5.json (report + scorecard + derived metrics)

Usage:
    python run_benchmark_kage3_v1_3_5.py

Notes:
- runs_per_sec depends on the machine/environment; treat it as indicative only.
- repro_semantic_digest_sha256 is derived from a deterministic sample run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import ai_doc_orchestrator_kage3_v1_3_5 as mod

CANON_DECISIONS = ("RUN", "PAUSE_FOR_HITL", "STOPPED")


def _derive_from_report(report: Dict[str, Any], runs: int) -> Tuple[Optional[float], Dict[str, int]]:
    """
    Derive metrics from the benchmark report without re-running the suite.

    Returns:
      - hitl_requested_rate: Optional[float]
      - decision_counts: normalized dict with canonical decision keys
    """
    raw_counts = report.get("overall_decision_counts", {}) or {}
    counts: Dict[str, int] = {k: int(raw_counts.get(k, 0)) for k in CANON_DECISIONS}

    if runs <= 0:
        return None, counts

    hitl_requested_rate = counts["PAUSE_FOR_HITL"] / float(runs)
    return hitl_requested_rate, counts


def _sample_semantic_digest(
    *,
    prompt: str,
    seed: int,
    p_continue: float,
    faults: Dict[str, Dict[str, Any]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[str, str]:
    """
    Run one deterministic sample simulation to derive a stable semantic digest.

    Returns:
      - semantic digest SHA-256
      - sample decision
    """
    resolver = mod.make_random_hitl_resolver(seed=seed, p_continue=p_continue)
    result, rows = mod.run_simulation_mem(
        prompt=prompt,
        run_id="SAMPLE#0",
        faults=faults,
        hitl_resolver=resolver,
        enable_runaway_seal=enable_runaway_seal,
        runaway_threshold=runaway_threshold,
        max_attempts_per_task=max_attempts_per_task,
    )
    digest = mod.semantic_signature_sha256(rows)
    return digest, result.decision


def main() -> int:
    sample_cfg = {
        "prompt": "WordとExcelとPPTを作って。どっちがいい？",
        "runs": 300,
        "seed": 42,
        "p_continue": 1.0,
        "runaway_threshold": 5,
        "max_attempts_per_task": 20,
        "faults": {"excel": {"break_contract": True}},
        "enable_runaway_seal": True,
    }

    report = mod.run_benchmark_suite(
        prompt=sample_cfg["prompt"],
        runs=sample_cfg["runs"],
        seed=sample_cfg["seed"],
        p_continue=sample_cfg["p_continue"],
        faults=sample_cfg["faults"],
        enable_runaway_seal=sample_cfg["enable_runaway_seal"],
        runaway_threshold=sample_cfg["runaway_threshold"],
        max_attempts_per_task=sample_cfg["max_attempts_per_task"],
    )

    scorecard = mod.safety_scorecard(
        report,
        require_seal_events=True,
        require_pii_zero=True,
        require_crash_free=True,
    )

    repro_digest, sample_decision = _sample_semantic_digest(
        prompt=sample_cfg["prompt"],
        seed=sample_cfg["seed"],
        p_continue=sample_cfg["p_continue"],
        faults=sample_cfg["faults"],
        enable_runaway_seal=sample_cfg["enable_runaway_seal"],
        runaway_threshold=sample_cfg["runaway_threshold"],
        max_attempts_per_task=sample_cfg["max_attempts_per_task"],
    )

    hitl_requested_rate, decision_counts = _derive_from_report(report, sample_cfg["runs"])

    out = {
        "report": report,
        "scorecard": scorecard,
        "derived": {
            "repro_semantic_digest_sha256": repro_digest,
            "sample_decision": sample_decision,
            "hitl_requested_rate": hitl_requested_rate,
            "decision_counts": decision_counts,
        },
    }

    out_path = Path("benchmark_report_sample_v1_3_5.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("module_version:", mod.__version__)
    print("scorecard.pass:", scorecard["pass"])
    print("summary:", scorecard["summary"])
    print("decision_counts:", decision_counts)
    print("hitl_requested_rate:", hitl_requested_rate)
    print("repro_digest:", repro_digest)
    print("wrote:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
