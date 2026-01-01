# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Doc Orchestrator Simulator (KAGE3-style gates, memory-only benchmark friendly)

Pipeline (conceptual):
  Agent (excel/word/ppt) -> Orchestrator gates:
    Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Key properties:
- Fail-closed: unsafe/unstable -> STOPPED (never silently RUN).
- RFL does NOT seal; it escalates to HITL (human-in-the-loop).
- Memory-only: no artifact writes. Caller can write reports separately.
- '@' invariant: audit rows are sanitized so no email-like tokens are persisted.

Decision vocabulary:
  RUN / PAUSE_FOR_HITL / STOPPED

Python: 3.9+
"""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

JST_OFFSET = "+09:00"

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

__version__ = "1.3.5"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def _sanitize_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, str):
        if "@" in obj or _EMAIL_RE.search(obj):
            return "[REDACTED]"
        return obj
    if isinstance(obj, list):
        return [_sanitize_obj(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_obj(x) for x in obj)
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if "@" in ks or _EMAIL_RE.search(ks):
                ks = "[REDACTED_KEY]"
            out[ks] = _sanitize_obj(v)
        return out
    return _sanitize_obj(str(obj))

def _row(event: str, **fields: Any) -> Dict[str, Any]:
    base = {"event": event, "tz": JST_OFFSET}
    base.update(fields)
    return _sanitize_obj(base)

def _rows_have_at_sign(rows: List[Dict[str, Any]]) -> bool:
    blob = json.dumps(rows, ensure_ascii=False, default=str)
    return "@" in blob

@dataclass(frozen=True)
class OrchestratorResult:
    decision: Decision
    sealed: bool
    overrideable: bool
    final_decider: FinalDecider
    reason_code: str

def make_random_hitl_resolver(*, seed: int, p_continue: float) -> Callable[[Dict[str, Any]], HitlChoice]:
    rng = random.Random(int(seed))
    pc = float(p_continue)

    def _resolve(_: Dict[str, Any]) -> HitlChoice:
        return "CONTINUE" if rng.random() < pc else "STOP"

    return _resolve

_TASKS: List[str] = ["excel", "word", "ppt"]

def _is_ambiguous(prompt: str) -> bool:
    tokens = ["どっち", "おすすめ", "どれがいい", "どちら", "best", "recommend"]
    p = (prompt or "").lower()
    return any(t in p for t in tokens)

def run_simulation_mem(
    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[[Dict[str, Any]], HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[OrchestratorResult, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    rows.append(_row("RUN_START", run_id=run_id))

    ambiguous = _is_ambiguous(prompt)
    failures_total = 0

    for task in _TASKS:
        rows.append(_row("TASK_START", run_id=run_id, task=task))
        rows.append(_row("MEANING_OK", run_id=run_id, task=task))

        attempts = 0
        while True:
            attempts += 1
            rows.append(_row("ATTEMPT", run_id=run_id, task=task, attempt=attempts))

            tf = faults.get(task, {}) if isinstance(faults, dict) else {}
            break_contract = bool(tf.get("break_contract", False))
            leak_email = bool(tf.get("leak_email", False))

            if ambiguous:
                rows.append(_row("RFL_HIT", run_id=run_id, task=task, reason_code="REL_BOUNDARY_UNSTABLE"))
                rows.append(_row("HITL_REQUESTED", run_id=run_id, task=task))
                if hitl_resolver is None:
                    rows.append(_row("HITL_UNRESOLVED", run_id=run_id, task=task))
                    return (
                        OrchestratorResult(
                            decision="PAUSE_FOR_HITL",
                            sealed=False,
                            overrideable=True,
                            final_decider="SYSTEM",
                            reason_code="HITL_PENDING",
                        ),
                        rows,
                    )
                choice = hitl_resolver({"run_id": run_id, "task": task})
                rows.append(_row("HITL_DECIDED", run_id=run_id, task=task, choice=choice, final_decider="USER"))
                if choice == "STOP":
                    rows.append(_row("TASK_STOPPED_BY_HITL", run_id=run_id, task=task))
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="USER",
                            reason_code="HITL_STOP",
                        ),
                        rows,
                    )
                # CONTINUE => proceed

            if leak_email:
                rows.append(_row("ETHICS_PII_DETECTED", run_id=run_id, task=task, pii_type="email"))
                rows.append(_row("ETHICS_SEALED", run_id=run_id, task=task, sealed=True))
                return (
                    OrchestratorResult(
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code="SEALED_BY_ETHICS",
                    ),
                    rows,
                )

            if break_contract:
                failures_total += 1
                rows.append(_row("CONSISTENCY_CONTRACT_MISMATCH", run_id=run_id, task=task))

                if enable_runaway_seal and failures_total >= int(runaway_threshold):
                    rows.append(_row("ACC_RUNAWAY_SEAL", run_id=run_id, task=task, sealed=True))
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=True,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code="SEALED_BY_ACC",
                        ),
                        rows,
                    )

                if attempts >= int(max_attempts_per_task):
                    rows.append(_row("RETRY_EXHAUSTED", run_id=run_id, task=task, sealed=False))
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code="RETRY_EXHAUSTED",
                        ),
                        rows,
                    )
                continue

            rows.append(_row("DISPATCHED", run_id=run_id, task=task))
            rows.append(_row("TASK_DONE", run_id=run_id, task=task))
            break

    rows.append(_row("RUN_DONE", run_id=run_id))
    return (
        OrchestratorResult(
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code="OK",
        ),
        rows,
    )

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
    t0 = time.perf_counter()
    resolver = make_random_hitl_resolver(seed=int(seed), p_continue=float(p_continue))

    crashes = 0
    at_sign_violations = 0
    counts: Dict[str, int] = {"RUN": 0, "PAUSE_FOR_HITL": 0, "STOPPED": 0}
    last_error: Optional[str] = None

    for i in range(int(runs)):
        try:
            res, rows = run_simulation_mem(
                prompt=prompt,
                run_id=f"RUN#{i}",
                faults=faults or {},
                hitl_resolver=resolver,
                enable_runaway_seal=bool(enable_runaway_seal),
                runaway_threshold=int(runaway_threshold),
                max_attempts_per_task=int(max_attempts_per_task),
            )
            counts[res.decision] = counts.get(res.decision, 0) + 1
            if _rows_have_at_sign(rows):
                at_sign_violations += 1
        except Exception as e:
            crashes += 1
            last_error = str(e)

    dt = max(1e-9, time.perf_counter() - t0)
    crash_free_rate = float((int(runs) - crashes) / float(max(1, int(runs))))
    runs_per_sec = float(int(runs) / dt)

    return {
        "module_path": "ai_doc_orchestrator_kage3_v1_3_5.py",
        "module_version": __version__,
        "runs": int(runs),
        "seed": int(seed),
        "p_continue": float(p_continue),
        "enable_runaway_seal": bool(enable_runaway_seal),
        "runaway_threshold": int(runaway_threshold),
        "max_attempts_per_task": int(max_attempts_per_task),
        "faults": faults or {},
        "overall_decision_counts": counts,
        "crashes": int(crashes),
        "crash_free_rate": crash_free_rate,
        "at_sign_violations": int(at_sign_violations),
        "runs_per_sec": runs_per_sec,
        "last_error": last_error,
    }

    
