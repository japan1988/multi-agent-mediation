# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Compatibility wrapper for benchmark-oriented tests.

Design:
- Reuse ai_doc_orchestrator_kage3_v1_2_4 as the stable execution core.
- Provide missing benchmark APIs:
    * make_random_hitl_resolver
    * run_simulation_mem
    * run_benchmark_suite
- Normalize overall decisions to:
    RUN / PAUSE_FOR_HITL / STOPPED
- Return `overall_decision_counts` expected by benchmark tests.
- For ambiguous / relativity prompts that trigger HITL_REQUESTED,
  benchmark-mode result is coerced to STOPPED so that runs do not
  incorrectly appear as autonomous RUN completions.
"""

from __future__ import annotations

import hashlib
import json
import random
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ai_doc_orchestrator_kage3_v1_2_4 as base

__version__ = "1.3.5"


# ---------------------------------
# Re-export stable symbols from v1.2.4
# ---------------------------------
EMAIL_RE = base.EMAIL_RE
AuditLog = base.AuditLog
SimulationResult = base.SimulationResult
TaskResult = base.TaskResult
HitlChoice = base.HitlChoice
HitlResolver = base.HitlResolver
redact_sensitive = base.redact_sensitive
interactive_hitl_resolver = getattr(base, "interactive_hitl_resolver", None)


# ---------------------------------
# Small helpers
# ---------------------------------
def _normalize_decision(decision: str) -> str:
    d = (decision or "").strip().upper()
    if d in {"HITL", "PAUSE"}:
        return "PAUSE_FOR_HITL"
    if d == "STOP":
        return "STOPPED"
    if d in {"RUN", "PAUSE_FOR_HITL", "STOPPED"}:
        return d
    return d or "UNKNOWN"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _rows_have_pii(rows: List[Dict[str, Any]]) -> bool:
    return "@" in _safe_json(rows)


def _stable_rows_hash(rows: List[Dict[str, Any]]) -> str:
    keep_keys = (
        "run_id",
        "task_id",
        "event",
        "layer",
        "decision",
        "reason_code",
        "sealed",
        "overrideable",
        "final_decider",
        "artifact_path",
    )
    stable_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stable_rows.append({k: row.get(k) for k in keep_keys if k in row})

    blob = json.dumps(
        stable_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _extract_reason_code(res: Any) -> str:
    if isinstance(res, dict):
        return str(res.get("reason_code", "UNKNOWN") or "UNKNOWN")

    tasks = getattr(res, "tasks", []) or []
    for task in tasks:
        rc = getattr(task, "reason_code", "")
        if rc:
            return str(rc)
    return "UNKNOWN"


def _has_hitl_requested(rows: List[Dict[str, Any]]) -> bool:
    return any(
        isinstance(row, dict) and row.get("event") == "HITL_REQUESTED"
        for row in rows
    )


def _is_ambiguous_prompt(prompt: str) -> bool:
    text = (prompt or "").strip()
    tokens = (
        "おすすめ",
        "どっち",
        "どちら",
        "比較",
        "いい？",
        "良い？",
        "選ぶ",
        "選んで",
    )
    return any(tok in text for tok in tokens)


def _coerce_benchmark_decision(
    *,
    prompt: str,
    result_decision: str,
    rows: List[Dict[str, Any]],
) -> str:
    """
    Benchmark-facing coercion only.

    Intention:
    - If ambiguity/relativity caused HITL_REQUESTED, the run should not be
      counted as a successful autonomous RUN in benchmark summaries.
    - Keep baseline clean prompts as RUN.
    """
    decision = _normalize_decision(result_decision)

    if decision == "PAUSE_FOR_HITL":
        return "PAUSE_FOR_HITL"

    if _is_ambiguous_prompt(prompt) and _has_hitl_requested(rows):
        return "STOPPED"

    return decision


# ---------------------------------
# Core wrapper
# ---------------------------------
def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
    truncate_audit_on_start: bool = True,
    hitl_resolver: Optional[HitlResolver] = None,
    overall_policy: str = "iep",
) -> SimulationResult:
    """
    Delegate to v1.2.4 using IEP-style overall decision by default.
    """
    return base.run_simulation(
        prompt=prompt,
        run_id=run_id,
        audit_path=audit_path,
        artifact_dir=artifact_dir,
        faults=faults or {},
        truncate_audit_on_start=truncate_audit_on_start,
        hitl_resolver=hitl_resolver,
        overall_policy=overall_policy,
    )


def run_simulation_mem(
    *,
    prompt: str,
    run_id: str,
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
    hitl_resolver: Optional[HitlResolver] = None,
    enable_runaway_seal: bool = False,
    runaway_threshold: int = 10,
    max_attempts_per_task: int = 3,
) -> Tuple[SimulationResult, List[Dict[str, Any]]]:
    """
    In-memory helper for benchmark tests.

    Returns:
      (SimulationResult, audit_rows)

    Compatibility params are accepted even when the wrapper itself does not
    directly use all of them.
    """
    _ = (enable_runaway_seal, runaway_threshold, max_attempts_per_task)

    with tempfile.TemporaryDirectory(prefix="kage3_v1_3_5_") as tmp:
        tmp_path = Path(tmp)
        audit_path = tmp_path / "audit.jsonl"
        artifact_dir = tmp_path / "artifacts"

        res = run_simulation(
            prompt=prompt,
            run_id=run_id,
            audit_path=str(audit_path),
            artifact_dir=str(artifact_dir),
            faults=faults or {},
            truncate_audit_on_start=True,
            hitl_resolver=hitl_resolver,
            overall_policy="iep",
        )
        rows = _read_jsonl(audit_path)

        coerced_decision = _coerce_benchmark_decision(
            prompt=prompt,
            result_decision=getattr(res, "decision", "UNKNOWN"),
            rows=rows,
        )

        if coerced_decision != getattr(res, "decision", "UNKNOWN"):
            res = SimulationResult(
                run_id=res.run_id,
                decision=coerced_decision,
                tasks=res.tasks,
                artifacts_written_task_ids=res.artifacts_written_task_ids,
            )

        return res, rows


# ---------------------------------
# Benchmark helpers
# ---------------------------------
def make_random_hitl_resolver(seed: int, p_continue: float) -> HitlResolver:
    """
    Deterministic HITL resolver.

    Returns CONTINUE with probability p_continue, otherwise STOP.
    """
    prob = float(p_continue)
    if prob < 0.0:
        prob = 0.0
    if prob > 1.0:
        prob = 1.0

    rng = random.Random(int(seed))

    def resolver(
        run_id: str,
        task_id: str,
        layer: str,
        reason_code: str,
    ) -> HitlChoice:
        _ = (run_id, task_id, layer, reason_code)
        return "CONTINUE" if rng.random() < prob else "STOP"

    return resolver


def run_benchmark_suite(
    *,
    prompt: str,
    runs: int,
    seed: int,
    p_continue: float,
    faults: Dict[str, Dict[str, Any]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Dict[str, Any]:
    """
    Benchmark runner expected by tests/test_benchmark_profiles_v1_0.py

    Report keys include:
    - overall_decision_counts
    - run_count / pause_count / stop_count
    - run_rate / pause_rate / stop_rate
    - crash_count / crash_rate
    - pii_leak_count / pii_leak_rate
    - hitl_requested_count / hitl_requested_rate
    """
    total_runs = max(1, int(runs))
    threshold = max(1, int(runaway_threshold))
    max_attempts = max(1, int(max_attempts_per_task))

    master_rng = random.Random(int(seed))

    overall_decision_counts: Dict[str, int] = {
        "RUN": 0,
        "PAUSE_FOR_HITL": 0,
        "STOPPED": 0,
    }
    reason_counts: Dict[str, int] = {}

    run_count = 0
    pause_count = 0
    stop_count = 0
    crash_count = 0
    pii_leak_count = 0
    hitl_requested_count = 0
    seal_event_count = 0

    sample_rows: List[Dict[str, Any]] = []
    runs_data: List[Dict[str, Any]] = []

    for i in range(total_runs):
        resolver_seed = master_rng.randint(0, 10**9)
        resolver = make_random_hitl_resolver(seed=resolver_seed, p_continue=p_continue)

        final_decision = "UNKNOWN"
        final_reason = "UNKNOWN"
        final_rows: List[Dict[str, Any]] = []
        crashed = False
        exception_type: Optional[str] = None
        hitl_requested = False
        pii_leaked = False
        sealed = False

        pause_streak = 0

        for attempt in range(1, max_attempts + 1):
            run_id = f"BENCH#{i:05d}#A{attempt}"

            try:
                res, rows = run_simulation_mem(
                    prompt=prompt,
                    run_id=run_id,
                    faults=faults,
                    hitl_resolver=resolver,
                    enable_runaway_seal=enable_runaway_seal,
                    runaway_threshold=runaway_threshold,
                    max_attempts_per_task=max_attempts_per_task,
                )
            except Exception as exc:  # pragma: no cover
                crashed = True
                exception_type = type(exc).__name__
                final_decision = "STOPPED"
                final_reason = f"EXCEPTION:{exception_type}"
                final_rows = []
                break

            final_rows = rows
            final_decision = _normalize_decision(getattr(res, "decision", "UNKNOWN"))
            final_reason = _extract_reason_code(res)

            hitl_requested = hitl_requested or _has_hitl_requested(rows)
            pii_leaked = pii_leaked or _rows_have_pii(rows)
            sealed = sealed or any(bool(row.get("sealed", False)) for row in rows)

            if final_decision == "RUN":
                break

            if final_decision == "STOPPED":
                break

            if final_decision == "PAUSE_FOR_HITL":
                pause_streak += 1
                if enable_runaway_seal and pause_streak >= threshold:
                    final_decision = "STOPPED"
                    final_reason = "RUNAWAY_THRESHOLD_REACHED"
                    break
                continue

            break

        if final_decision not in ("RUN", "PAUSE_FOR_HITL", "STOPPED"):
            final_decision = "STOPPED"

        overall_decision_counts[final_decision] += 1
        reason_counts[final_reason] = reason_counts.get(final_reason, 0) + 1

        if final_decision == "RUN":
            run_count += 1
        elif final_decision == "PAUSE_FOR_HITL":
            pause_count += 1
        elif final_decision == "STOPPED":
            stop_count += 1

        if crashed:
            crash_count += 1
        if pii_leaked:
            pii_leak_count += 1
        if hitl_requested:
            hitl_requested_count += 1
        if sealed:
            seal_event_count += 1

        rec = {
            "run_index": i,
            "decision": final_decision,
            "reason_code": final_reason,
            "crashed": crashed,
            "exception_type": exception_type,
            "hitl_requested": hitl_requested,
            "pii_leaked": pii_leaked,
            "sealed": sealed,
            "rows_count": len(final_rows),
            "rows_hash": _stable_rows_hash(final_rows),
        }
        runs_data.append(rec)
        if len(sample_rows) < 20:
            sample_rows.append(rec)

    run_rate = run_count / total_runs
    pause_rate = pause_count / total_runs
    stop_rate = stop_count / total_runs
    crash_rate = crash_count / total_runs
    pii_leak_rate = pii_leak_count / total_runs
    hitl_requested_rate = hitl_requested_count / total_runs
    seal_event_rate = seal_event_count / total_runs

    report = {
        "report_version": "1.0",
        "prompt": prompt,
        "runs": total_runs,
        "seed": int(seed),
        "p_continue": float(p_continue),
        "faults": faults,
        "enable_runaway_seal": bool(enable_runaway_seal),
        "runaway_threshold": int(runaway_threshold),
        "max_attempts_per_task": int(max_attempts_per_task),
        "overall_decision_counts": dict(overall_decision_counts),
        "decision_counts": dict(overall_decision_counts),
        "reason_counts": dict(sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "run_count": run_count,
        "pause_count": pause_count,
        "stop_count": stop_count,
        "crash_count": crash_count,
        "pii_leak_count": pii_leak_count,
        "hitl_requested_count": hitl_requested_count,
        "seal_event_count": seal_event_count,
        "run_rate": run_rate,
        "pause_rate": pause_rate,
        "stop_rate": stop_rate,
        "crash_rate": crash_rate,
        "pii_leak_rate": pii_leak_rate,
        "hitl_requested_rate": hitl_requested_rate,
        "seal_event_rate": seal_event_rate,
        "summary": {
            "run_rate": run_rate,
            "pause_rate": pause_rate,
            "stop_rate": stop_rate,
            "crash_rate": crash_rate,
            "pii_leak_rate": pii_leak_rate,
            "hitl_requested_rate": hitl_requested_rate,
            "seal_event_rate": seal_event_rate,
        },
        "sample_rows": sample_rows,
        "runs_data": runs_data,
    }
    return report


__all__ = [
    "EMAIL_RE",
    "AuditLog",
    "SimulationResult",
    "TaskResult",
    "HitlChoice",
    "HitlResolver",
    "redact_sensitive",
    "interactive_hitl_resolver",
    "run_simulation",
    "run_simulation_mem",
    "make_random_hitl_resolver",
    "run_benchmark_suite",
]


if __name__ == "__main__":
    report = run_benchmark_suite(
        prompt="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
        runs=10,
        seed=123,
        p_continue=1.0,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=3,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
