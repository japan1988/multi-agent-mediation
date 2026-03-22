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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

JST_OFFSET = "+09:00"

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

__version__ = "1.3.5"

_TASKS = ("excel", "word", "ppt")


@dataclass
class AuditLog:
    run_id: str
    ts: str
    layer: str
    event: str
    task: Optional[str]
    decision: Optional[str]
    reason_code: str
    sealed: bool
    overrideable: bool
    final_decider: str
    detail: Optional[str] = None


@dataclass
class OrchestratorResult:
    decision: Decision
    reason_code: str
    sealed: bool
    overrideable: bool
    final_decider: FinalDecider
    hitl_requested: bool = False


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


def utc_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sanitize_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value



def _sanitize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _sanitize_text(v) for k, v in row.items()}


def _write_jsonl(path: Path, rows: List[Dict[str, Any]], truncate: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_sanitize_row(row), ensure_ascii=False) + "\n")


def _append_row(
    rows: List[Dict[str, Any]],
    *,
    run_id: str,
    layer: str,
    event: str,
    task: Optional[str],
    decision: Optional[str],
    reason_code: str,
    sealed: bool,
    overrideable: bool,
    final_decider: str,
    detail: Optional[str] = None,
) -> None:
    rows.append(
        asdict(
            AuditLog(
                run_id=run_id,
                ts=utc_ts(),
                layer=layer,
                event=event,
                task=task,
                decision=decision,
                reason_code=reason_code,
                sealed=sealed,
                overrideable=overrideable,
                final_decider=final_decider,
                detail=detail,
            )
        )
    )


    keep_keys = (
        "layer",
        "event",
        "task",
        "decision",
        "reason_code",
        "sealed",
        "overrideable",
        "final_decider",
        "detail",
    )

    for row in rows:
        sanitized = _sanitize_row(row)
        stable_rows.append({k: sanitized.get(k) for k in keep_keys})
    blob = json.dumps(stable_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    prompt = prompt or ""
    faults = faults or {}
    runaway_threshold = max(1, int(runaway_threshold))
    max_attempts_per_task = max(1, int(max_attempts_per_task))

    _append_row(
        rows,
        run_id=run_id,
        layer="orchestrator",
        event="ORCH_START",
        task=None,
        decision=None,
        reason_code="ORCH_START",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        detail=prompt,
    )

    tasks = _infer_tasks(prompt)
    if not tasks:
        _append_row(
            rows,
            run_id=run_id,
            layer="meaning_gate",

            event="MEANING_STOP",
            task=None,
            decision="STOPPED",
            reason_code="MEANING_NO_TASKS",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            detail="No actionable document task inferred.",
        )
        orch_res = OrchestratorResult(
            decision="STOPPED",
            reason_code="MEANING_NO_TASKS",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            hitl_requested=False,
        )
        _append_row(
            rows,
            run_id=run_id,
            layer="orchestrator",
            event="ORCH_FINAL",
            task=None,
            decision=orch_res.decision,
            reason_code=orch_res.reason_code,
            sealed=orch_res.sealed,
            overrideable=orch_res.overrideable,
            final_decider=orch_res.final_decider,
        )
        return orch_res, rows

    hitl_requested = False
    global_stopped = False
    final_reason = "OK"
    any_ran = False
    any_paused = False

    for task in tasks:
        task_faults = faults.get(task, {})

        _append_row(
            rows,
            run_id=run_id,
            layer="meaning_gate",

            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

            _append_row(
                rows,
                run_id=run_id,
                layer="ethics_gate",
                event="ETHICS_SEALED",
                task=task,
                decision="STOPPED",
                reason_code="SEALED_BY_ETHICS",
                sealed=True,
                overrideable=False,
                final_decider="SYSTEM",
            )
            global_stopped = True
            final_reason = "SEALED_BY_ETHICS"
            continue

        _append_row(
            rows,
            run_id=run_id,
            layer="ethics_gate",
            event="ETHICS_OK",
            task=task,
            decision=None,
            reason_code="ETHICS_OK",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )


        break_contract = bool(task_faults.get("break_contract"))
        force_stop = bool(task_faults.get("force_stop"))
        attempts = 0
        done = False

        while attempts < max_attempts_per_task:
            attempts += 1

            _append_row(
                rows,
                run_id=run_id,
                layer="dispatch",
                event="TASK_ATTEMPT",
                task=task,
                decision=None,
                reason_code="DISPATCH_ATTEMPT",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                detail=f"attempt={attempts}",
            )

            if force_stop:
                _append_row(
                    rows,
                    run_id=run_id,
                    layer="acc_gate",
                    event="ACC_FORCE_STOP",
                    task=task,
                    decision="STOPPED",
                    reason_code="ACC_FORCE_STOP",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                )
                global_stopped = True
                final_reason = "ACC_FORCE_STOP"
                break

            if break_contract:
                _append_row(
                    rows,
                    run_id=run_id,
                    layer="dispatch",
                    event="TASK_CONTRACT_BREAK",
                    task=task,
                    decision=None,
                    reason_code="DISPATCH_CONTRACT_BREAK",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                )

                if enable_runaway_seal and attempts >= runaway_threshold:
                    _append_row(
                        rows,
                        run_id=run_id,
                        layer="acc_gate",

                        event="ACC_RUNAWAY_SEAL",
                        task=task,
                        decision="STOPPED",
                        reason_code="SEALED_BY_ACC",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        detail=f"attempts={attempts}",
                    )
                    global_stopped = True
                    final_reason = "SEALED_BY_ACC"
                    break


                continue

            _append_row(
                rows,
                run_id=run_id,
                layer="dispatch",
                event="TASK_DONE",
                task=task,
                decision="RUN",
                reason_code="OK",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
            )
            done = True
            any_ran = True
            break

        if not done and not break_contract and not force_stop:
            _append_row(
                rows,
                run_id=run_id,
                layer="dispatch",
                event="TASK_STOPPED",
                task=task,
                decision="STOPPED",
                reason_code="TASK_NOT_COMPLETED",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
            )
            global_stopped = True
            final_reason = "TASK_NOT_COMPLETED"

    if any_ran and not global_stopped:
        orch_res = OrchestratorResult(
            decision="RUN",
            reason_code="OK",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            hitl_requested=hitl_requested,
        )
    elif any_paused and not any_ran and not global_stopped:
        orch_res = OrchestratorResult(
            decision="PAUSE_FOR_HITL",
            reason_code=final_reason,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
            hitl_requested=True,
        )
    else:
        orch_res = OrchestratorResult(
            decision="STOPPED",
            reason_code=final_reason,
            sealed=final_reason in {"SEALED_BY_ETHICS", "SEALED_BY_ACC"},
            overrideable=False,
            final_decider="SYSTEM",
            hitl_requested=hitl_requested,
        )

    _append_row(
        rows,
        run_id=run_id,
        layer="orchestrator",
        event="ORCH_FINAL",
        task=None,
        decision=orch_res.decision,
        reason_code=orch_res.reason_code,
        sealed=orch_res.sealed,
        overrideable=orch_res.overrideable,
        final_decider=orch_res.final_decider,
    )
    return orch_res, rows


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[[Dict[str, Any]], HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
    audit_path: str = "audit.jsonl",
    artifact_dir: str = "artifacts",
    truncate_audit_on_start: bool = True,
) -> SimulationResult:

    orch_res, rows = run_simulation_mem(
        prompt=prompt,
        run_id=run_id,
        faults=faults,
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=enable_runaway_seal,
        runaway_threshold=runaway_threshold,
        max_attempts_per_task=max_attempts_per_task,
    )

    seen_tasks: List[str] = []
    for row in rows:
        task = row.get("task")
        if task in _TASKS and task not in seen_tasks:
            seen_tasks.append(task)

    tasks_out: List[TaskResult] = []
    artifacts_written: List[str] = []


        sealed = any(
            row.get("event") in ("AGENT_SEALED", "ETHICS_SEALED", "ACC_RUNAWAY_SEAL")
            and row.get("task") == task
            for row in rows
        )


        if paused:
            decision: Decision = "PAUSE_FOR_HITL"
            reason_code = "HITL_PENDING"
        elif ethics_stop:
            decision = "STOPPED"
            reason_code = "SEALED_BY_ETHICS"
        elif sealed and not done:
            decision = "STOPPED"
            reason_code = "SEALED_BY_ACC"
        elif done:
            decision = "RUN"
            reason_code = "OK"
        else:
            decision = orch_res.decision
            reason_code = orch_res.reason_code

        artifact_path: Optional[str] = None
        if decision == "RUN":
            artifact_root = Path(artifact_dir)
            artifact_root.mkdir(parents=True, exist_ok=True)
            artifact_path = str(artifact_root / f"{task_id}.txt")
            artifact_text = f"{task} artifact (run_id={run_id})"
            Path(artifact_path).write_text(artifact_text, encoding="utf-8")
            artifacts_written.append(task_id)

        tasks_out.append(
            TaskResult(
                task_id=task_id,
                task=task,
                decision=decision,
                sealed=bool(sealed),
                artifact_path=artifact_path,
                reason_code=reason_code,
            )
        )

    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        decision=orch_res.decision,
        tasks=tasks_out,
        artifacts_written_task_ids=artifacts_written,
    )


<
def _normalize_decision(decision: str) -> str:
    d = (decision or "").strip().upper()
    if d in {"HITL", "PAUSE"}:
        return "PAUSE_FOR_HITL"
    if d == "STOP":
        return "STOPPED"
    return d or "UNKNOWN"


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

    }
    crash_count = 0
    pii_leak_count = 0
    hitl_requested_count = 0
    seal_event_count = 0
    sample_rows: List[Dict[str, Any]] = []
    runs_data: List[Dict[str, Any]] = []

    for i in range(int(runs)):
        run_id = f"SIM#{i:05d}"
        # deterministic but per-run varied resolver
        resolver_seed = rng.randint(0, 10**9)
        resolver = make_random_hitl_resolver(seed=resolver_seed, p_continue=p_continue)

        try:
            orch_res, rows = run_simulation_mem(
                prompt=prompt,
                run_id=run_id,
                faults=faults,
                hitl_resolver=resolver,
                enable_runaway_seal=enable_runaway_seal,
                runaway_threshold=runaway_threshold,
                max_attempts_per_task=max_attempts_per_task,
            )
        except Exception as exc:  # pragma: no cover - benchmark should remain crash-safe
            crash_count += 1
            rows = []
            orch_res = OrchestratorResult(
                decision="STOPPED",
                reason_code=f"EXC:{type(exc).__name__}",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                hitl_requested=False,
            )

        decision = _normalize_decision(orch_res.decision)
        overall_decision_counts[decision] = overall_decision_counts.get(decision, 0) + 1


    task = ctx.get("task", "?")
    raw = input(f"[HITL] Continue task '{task}'? [y/N]: ").strip().lower()
    return "CONTINUE" if raw in {"y", "yes"} else "STOP"
