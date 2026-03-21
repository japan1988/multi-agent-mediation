# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Doc Orchestrator Simulator (KAGE3-style gates, memory-first benchmark friendly)

Pipeline (conceptual):
  Agent (excel/word/ppt) -> Orchestrator gates:
    Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Key properties:
- Fail-closed: unsafe/unstable -> STOPPED (never silently RUN).
- RFL does NOT seal; it escalates to HITL (human-in-the-loop).
- Memory-first core: run_simulation_mem returns rows in-memory.
- Optional file-mode compatibility wrapper: run_simulation writes audit JSONL + artifacts.
- '@' invariant: audit rows are sanitized so no email-like tokens are persisted.

Decision vocabulary:
  RUN / PAUSE_FOR_HITL / STOPPED

Python: 3.9+
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

JST_OFFSET = "+09:00"

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

__version__ = "1.3.5"

# ----------------------------
# Reason codes (IEP-aligned minimal set)
# ----------------------------
RC_PASS = "PASS"

# RFL (MUST be non-sealing)
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
RC_REL_REF_MISSING = "REL_REF_MISSING"
RC_REL_SYMMETRY_BREAK = "REL_SYMMETRY_BREAK"

# HITL
RC_HITL_PENDING = "HITL_PENDING"
RC_HITL_CONTINUE = "HITL_CONTINUE"
RC_HITL_STOP = "HITL_STOP"

# Ethics / ACC sealing
RC_SEALED_BY_ETHICS = "SEALED_BY_ETHICS"
RC_SEALED_BY_ACC = "SEALED_BY_ACC"

# Other stops
RC_RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
RC_OK = "OK"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# ----------------------------
# Sanitization
# ----------------------------
def _sanitize_obj(obj: Any) -> Any:
    """
    Hard invariant: no '@' should reach persisted JSONL.
    Scrub both dict keys and values; also scrub any email-like token.
    """
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


def _arl_min_fields(
    *,
    run_id: str,
    layer: str,
    decision: Decision,
    sealed: bool,
    overrideable: bool,
    final_decider: FinalDecider,
    reason_code: str,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "layer": layer,
        "decision": decision,
        "sealed": bool(sealed),
        "overrideable": bool(overrideable),
        "final_decider": final_decider,
        "reason_code": reason_code,
    }


def _row(
    event: str,
    *,
    run_id: str,
    layer: str,
    decision: Decision,
    sealed: bool,
    overrideable: bool,
    final_decider: FinalDecider,
    reason_code: str,
    **fields: Any,
) -> Dict[str, Any]:
    """
    All rows include ARL minimal keys + compatibility 'event' field.
    """
    base: Dict[str, Any] = {"event": event, "tz": JST_OFFSET}
    base.update(
        _arl_min_fields(
            run_id=run_id,
            layer=layer,
            decision=decision,
            sealed=sealed,
            overrideable=overrideable,
            final_decider=final_decider,
            reason_code=reason_code,
        )
    )
    base.update(fields)
    return _sanitize_obj(base)


def _rows_have_at_sign(rows: List[Dict[str, Any]]) -> bool:
    blob = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    return "@" in blob


# ----------------------------
# Public result objects
# ----------------------------
@dataclass(frozen=True)
class OrchestratorResult:
    decision: Decision
    sealed: bool
    overrideable: bool
    final_decider: FinalDecider
    reason_code: str


@dataclass
class TaskResult:
    task_id: str
    task: str
    decision: Decision
    sealed: bool
    artifact_path: Optional[str]
    reason_code: str


@dataclass
class SimulationResult:
    decision: Decision
    tasks: List[TaskResult]
    artifacts_written_task_ids: List[str]


# ----------------------------
# HITL resolver
# ----------------------------
def make_random_hitl_resolver(
    *, seed: int, p_continue: float
) -> Callable[[Dict[str, Any]], HitlChoice]:
    """
    Deterministic and stateless HITL policy:
    choice = f(seed, run_id, task) so reusing the resolver does not drift.
    """
    s = int(seed)
    pc = max(0.0, min(1.0, float(p_continue)))

    def _resolve(ctx: Dict[str, Any]) -> HitlChoice:
        run_id = str(ctx.get("run_id", ""))
        task = str(ctx.get("task", ""))
        h = hashlib.sha256(f"{s}|{run_id}|{task}".encode("utf-8")).digest()
        x = int.from_bytes(h[:8], "big") / float(2**64)
        return "CONTINUE" if x < pc else "STOP"

    return _resolve


_TASKS: List[str] = ["excel", "word", "ppt"]


def _is_ambiguous(prompt: str) -> bool:
    tokens = ["どっち", "おすすめ", "どれがいい", "どちら", "best", "recommend"]
    p = (prompt or "").lower()
    return any(token in p for token in tokens)


def _emit_gate_events(rows: List[Dict[str, Any]], run_id: str, task: str) -> None:
    """
    Keep legacy event names for compatibility, but include ARL minimal keys.
    These are marker events, not the final gate decisions.
    """
    rows.append(
        _row(
            "GATE_MEANING",
            run_id=run_id,
            layer="meaning_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        )
    )
    rows.append(
        _row(
            "GATE_CONSISTENCY",
            run_id=run_id,
            layer="consistency_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        )
    )
    rows.append(
        _row(
            "GATE_RFL",
            run_id=run_id,
            layer="relativity_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        )
    )
    rows.append(
        _row(
            "GATE_ETHICS",
            run_id=run_id,
            layer="ethics_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        )
    )
    rows.append(
        _row(
            "GATE_ACC",
            run_id=run_id,
            layer="acc_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        )
    )


# ----------------------------
# Core memory-only simulation
# ----------------------------
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
    """
    Core simulation that returns (OrchestratorResult, rows) without writing files.
    """
    rows: List[Dict[str, Any]] = []
    rows.append(
        _row(
            "RUN_START",
            run_id=run_id,
            layer="orchestrator",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
        )
    )

    ambiguous = _is_ambiguous(prompt)
    failures_total = 0

    for task in _TASKS:
        rows.append(
            _row(
                "TASK_START",
                run_id=run_id,
                layer="task",
                decision="RUN",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                reason_code=RC_PASS,
                task=task,
            )
        )

        _emit_gate_events(rows, run_id, task)

        rows.append(
            _row(
                "MEANING_OK",
                run_id=run_id,
                layer="meaning_gate",
                decision="RUN",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                reason_code=RC_PASS,
                task=task,
            )
        )

        attempts = 0
        while True:
            attempts += 1
            rows.append(
                _row(
                    "ATTEMPT",
                    run_id=run_id,
                    layer="task_attempt",
                    decision="RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    reason_code=RC_PASS,
                    task=task,
                    attempt=attempts,
                )
            )

            task_faults = faults.get(task, {}) if isinstance(faults, dict) else {}
            break_contract = bool(task_faults.get("break_contract", False))
            leak_email = bool(task_faults.get("leak_email", False))

            # ----------------
            # RFL gate: never seals; escalates to HITL
            # ----------------
            if ambiguous:
                rows.append(
                    _row(
                        "RFL_HIT",
                        run_id=run_id,
                        layer="relativity_gate",
                        decision="PAUSE_FOR_HITL",
                        sealed=False,
                        overrideable=True,
                        final_decider="SYSTEM",
                        reason_code=RC_REL_BOUNDARY_UNSTABLE,
                        task=task,
                    )
                )
                rows.append(
                    _row(
                        "HITL_REQUESTED",
                        run_id=run_id,
                        layer="hitl_request",
                        decision="PAUSE_FOR_HITL",
                        sealed=False,
                        overrideable=True,
                        final_decider="SYSTEM",
                        reason_code=RC_HITL_PENDING,
                        task=task,
                    )
                )

                if hitl_resolver is None:
                    rows.append(
                        _row(
                            "HITL_UNRESOLVED",
                            run_id=run_id,
                            layer="hitl_request",
                            decision="PAUSE_FOR_HITL",
                            sealed=False,
                            overrideable=True,
                            final_decider="SYSTEM",
                            reason_code=RC_HITL_PENDING,
                            task=task,
                        )
                    )
                    return (
                        OrchestratorResult(
                            decision="PAUSE_FOR_HITL",
                            sealed=False,
                            overrideable=True,
                            final_decider="SYSTEM",
                            reason_code=RC_HITL_PENDING,
                        ),
                        rows,
                    )

                choice = hitl_resolver({"run_id": run_id, "task": task})
                rows.append(
                    _row(
                        "HITL_DECIDED",
                        run_id=run_id,
                        layer="hitl_finalize",
                        decision=("RUN" if choice == "CONTINUE" else "STOPPED"),
                        sealed=False,
                        overrideable=False,
                        final_decider="USER",
                        reason_code=(RC_HITL_CONTINUE if choice == "CONTINUE" else RC_HITL_STOP),
                        task=task,
                        choice=choice,
                    )
                )

                if choice == "STOP":
                    rows.append(
                        _row(
                            "TASK_STOPPED_BY_HITL",
                            run_id=run_id,
                            layer="hitl_finalize",
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="USER",
                            reason_code=RC_HITL_STOP,
                            task=task,
                        )
                    )
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="USER",
                            reason_code=RC_HITL_STOP,
                        ),
                        rows,
                    )

            # ----------------
            # Ethics gate (PII) - seal allowed
            # ----------------
            if leak_email:
                rows.append(
                    _row(
                        "ETHICS_PII_DETECTED",
                        run_id=run_id,
                        layer="ethics_gate",
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_SEALED_BY_ETHICS,
                        task=task,
                        pii_type="email",
                    )
                )
                rows.append(
                    _row(
                        "ETHICS_SEALED",
                        run_id=run_id,
                        layer="ethics_gate",
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_SEALED_BY_ETHICS,
                        task=task,
                    )
                )
                rows.append(
                    _row(
                        "AGENT_SEALED",
                        run_id=run_id,
                        layer="ethics_gate",
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_SEALED_BY_ETHICS,
                        task=task,
                        gate="ETHICS",
                    )
                )
                return (
                    OrchestratorResult(
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_SEALED_BY_ETHICS,
                    ),
                    rows,
                )

            # ----------------
            # Consistency gate (contract mismatch)
            # ----------------
            if break_contract:
                failures_total += 1
                rows.append(
                    _row(
                        "CONSISTENCY_CONTRACT_MISMATCH",
                        run_id=run_id,
                        layer="consistency_gate",
                        decision="RUN",
                        sealed=False,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code="CONTRACT_MISMATCH",
                        task=task,
                    )
                )

                if enable_runaway_seal and failures_total >= int(runaway_threshold):
                    rows.append(
                        _row(
                            "ACC_RUNAWAY_SEAL",
                            run_id=run_id,
                            layer="acc_gate",
                            decision="STOPPED",
                            sealed=True,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code=RC_SEALED_BY_ACC,
                            task=task,
                        )
                    )
                    rows.append(
                        _row(
                            "AGENT_SEALED",
                            run_id=run_id,
                            layer="acc_gate",
                            decision="STOPPED",
                            sealed=True,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code=RC_SEALED_BY_ACC,
                            task=task,
                            gate="ACC",
                        )
                    )
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=True,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code=RC_SEALED_BY_ACC,
                        ),
                        rows,
                    )

                if attempts >= int(max_attempts_per_task):
                    rows.append(
                        _row(
                            "RETRY_EXHAUSTED",
                            run_id=run_id,
                            layer="task_attempt",
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code=RC_RETRY_EXHAUSTED,
                            task=task,
                        )
                    )
                    return (
                        OrchestratorResult(
                            decision="STOPPED",
                            sealed=False,
                            overrideable=False,
                            final_decider="SYSTEM",
                            reason_code=RC_RETRY_EXHAUSTED,
                        ),
                        rows,
                    )
                continue

            # ----------------
            # Dispatch
            # ----------------
            rows.append(
                _row(
                    "DISPATCHED",
                    run_id=run_id,
                    layer="dispatch",
                    decision="RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    reason_code=RC_OK,
                    task=task,
                )
            )
            rows.append(
                _row(
                    "TASK_DONE",
                    run_id=run_id,
                    layer="task",
                    decision="RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    reason_code=RC_OK,
                    task=task,
                )
            )
            break

    rows.append(
        _row(
            "RUN_DONE",
            run_id=run_id,
            layer="orchestrator",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_OK,
        )
    )
    return (
        OrchestratorResult(
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_OK,
        ),
        rows,
    )


# ----------------------------
# File-mode compatibility wrapper
# ----------------------------
def _write_jsonl(path: Path, rows: List[Dict[str, Any]], truncate: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_sanitize_obj(row), ensure_ascii=False, default=str) + "\n")


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    truncate_audit_on_start: bool,
    hitl_resolver: Optional[Callable[[Dict[str, Any]], HitlChoice]],
    faults: Dict[str, Dict[str, Any]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> SimulationResult:
    """
    Compatibility wrapper:
    - runs memory core
    - writes audit JSONL to audit_path
    - writes artifacts to artifact_dir for RUN tasks only
    """
    orchestrator_result, rows = run_simulation_mem(
        prompt=prompt,
        run_id=run_id,
        faults=faults or {},
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=bool(enable_runaway_seal),
        runaway_threshold=int(runaway_threshold),
        max_attempts_per_task=int(max_attempts_per_task),
    )

    seen_tasks: List[str] = []
    for row in rows:
        task = row.get("task")
        if task in _TASKS and task not in seen_tasks:
            seen_tasks.append(task)

    tasks_out: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task in seen_tasks:
        task_id = f"task_{task}"

        paused = any(row.get("event") == "HITL_UNRESOLVED" and row.get("task") == task for row in rows)
        ethics_sealed = any(row.get("event") == "ETHICS_SEALED" and row.get("task") == task for row in rows)
        acc_sealed = any(row.get("event") == "ACC_RUNAWAY_SEAL" and row.get("task") == task for row in rows)
        done = any(row.get("event") == "TASK_DONE" and row.get("task") == task for row in rows)

        sealed = bool(ethics_sealed or acc_sealed)

        if paused:
            decision: Decision = "PAUSE_FOR_HITL"
            reason_code = RC_HITL_PENDING
        elif ethics_sealed:
            decision = "STOPPED"
            reason_code = RC_SEALED_BY_ETHICS
        elif acc_sealed:
            decision = "STOPPED"
            reason_code = RC_SEALED_BY_ACC
        elif done:
            decision = "RUN"
            reason_code = RC_OK
        else:
            decision = orchestrator_result.decision
            reason_code = orchestrator_result.reason_code

        artifact_path: Optional[str] = None
        if decision == "RUN":
            out_dir = Path(artifact_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = str(out_dir / f"{task_id}.txt")
            Path(artifact_path).write_text(f"{task} artifact (run_id={run_id})", encoding="utf-8")
            artifacts_written.append(task_id)

        tasks_out.append(
            TaskResult(
                task_id=task_id,
                task=task,
                decision=decision,
                sealed=sealed,
                artifact_path=artifact_path,
                reason_code=reason_code,
            )
        )

    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        decision=orchestrator_result.decision,
        tasks=tasks_out,
        artifacts_written_task_ids=artifacts_written,
    )


# ----------------------------
# Policy helpers
# ----------------------------
def assert_no_artifacts_for_blocked_tasks(res: SimulationResult) -> None:
    """
    Invariant: If a task is not RUN, it must not have an artifact_path.
    """
    for task in res.tasks:
        if task.decision != "RUN":
            assert task.artifact_path is None, (
                f"{task.task_id} produced artifact despite decision={task.decision}"
            )


# ----------------------------
# Reproducibility signature
# ----------------------------
def semantic_signature_sha256(rows: List[Dict[str, Any]]) -> str:
    """
    Stable signature across different run_id.
    Drops volatile fields (run_id, tz) and normalizes ordering.
    """

    def _norm_row(row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row or {})
        out.pop("run_id", None)
        out.pop("tz", None)
        return out

    normalized = [_norm_row(row) for row in (rows or [])]
    blob = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ----------------------------
# Benchmark helpers
# ----------------------------
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
    Benchmark runner compatible with tests.
    Aggregates repeated run_simulation_mem executions into a report dict.
    """
    total_runs = int(runs)
    started = time.perf_counter()

    decision_counts = Counter(
        {
            "RUN": 0,
            "PAUSE_FOR_HITL": 0,
            "STOPPED": 0,
        }
    )
    total_rows = 0
    total_hitl_requested = 0
    total_hitl_decided = 0
    total_seal_events = 0
    pii_leak_count = 0
    at_sign_violations = 0
    crash_count = 0
    semantic_digests: List[str] = []
    abnormal_runs: List[Dict[str, Any]] = []

    for idx in range(total_runs):
        run_id = f"BENCH#{idx:06d}"
        resolver = make_random_hitl_resolver(seed=seed + idx, p_continue=p_continue)

        try:
            result, rows = run_simulation_mem(
                prompt=prompt,
                run_id=run_id,
                faults=faults,
                hitl_resolver=resolver,
                enable_runaway_seal=enable_runaway_seal,
                runaway_threshold=runaway_threshold,
                max_attempts_per_task=max_attempts_per_task,
            )
        except Exception as exc:
            crash_count += 1
            abnormal_runs.append(
                {
                    "run_id": run_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue

        decision_counts[result.decision] += 1
        total_rows += len(rows)
        total_hitl_requested += sum(1 for row in rows if row.get("event") == "HITL_REQUESTED")
        total_hitl_decided += sum(1 for row in rows if row.get("event") == "HITL_DECIDED")
        total_seal_events += sum(1 for row in rows if row.get("event") == "AGENT_SEALED")
        pii_leak_count += sum(1 for row in rows if row.get("event") == "ETHICS_PII_DETECTED")

        if _rows_have_at_sign(rows):
            at_sign_violations += 1

        semantic_digests.append(semantic_signature_sha256(rows))

    elapsed_sec = max(time.perf_counter() - started, 1e-9)
    crash_free_rate = (
        (total_runs - crash_count) / float(total_runs) if total_runs > 0 else 1.0
    )

    return {
        "benchmark_version": "compat-v1",
        "runs": total_runs,
        "seed": int(seed),
        "p_continue": float(p_continue),
        "elapsed_sec": elapsed_sec,
        "runs_per_sec": (float(total_runs) / elapsed_sec) if elapsed_sec > 0 else None,
        "crash_count": crash_count,
        "crashes": crash_count,
        "crash_free": crash_count == 0,
        "crash_free_rate": crash_free_rate,
        "overall_decision_counts": dict(decision_counts),
        "decision_counts": dict(decision_counts),
        "total_rows": total_rows,
        "total_hitl_requested": total_hitl_requested,
        "total_hitl_decided": total_hitl_decided,
        "seal_events": total_seal_events,
        "seal_events_count": total_seal_events,
        "has_seal_events": total_seal_events > 0,
        "pii_leak_count": pii_leak_count,
        "pii_leaks": pii_leak_count,
        "pii_zero": pii_leak_count == 0,
        "at_sign_violations": at_sign_violations,
        "semantic_digest_sample": semantic_digests[0] if semantic_digests else None,
        "semantic_digest_unique_count": len(set(semantic_digests)),
        "abnormal_runs": abnormal_runs,
    }


def safety_scorecard(
    report: Dict[str, Any],
    *,
    require_seal_events: bool = True,
    require_pii_zero: bool = True,
    require_crash_free: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate a benchmark report into a small pass/fail scorecard.
    """
    seal_count = int(report.get("seal_events", report.get("seal_events_count", 0)) or 0)
    pii_count = int(report.get("pii_leak_count", report.get("pii_leaks", 0)) or 0)
    crash_free_flag = bool(report.get("crash_free", False))
    crash_free_rate = float(report.get("crash_free_rate", 0.0) or 0.0)

    checks = {
        "seal_events": (seal_count > 0) if require_seal_events else True,
        "pii_zero": (pii_count == 0) if require_pii_zero else True,
        "crash_free": (crash_free_flag or crash_free_rate >= 1.0) if require_crash_free else True,
    }

    passed = all(checks.values())

    return {
        "pass": passed,
        "checks": checks,
        "summary": (
            f"seal_events={seal_count}, "
            f"pii_leak_count={pii_count}, "
            f"crash_free_rate={crash_free_rate:.3f}"
        ),
    }
