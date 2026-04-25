# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Doc Orchestrator Simulator (KAGE3-style gates, memory-first benchmark friendly)

Pipeline:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Key properties:
- Fail-closed
- RFL never seals; it escalates to HITL
- Memory-first benchmark support
- File-mode audit JSONL + artifact writing
- Audit rows are sanitized so email-like strings are never persisted
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

__version__ = "1.3.5"

_TASKS: Tuple[str, ...] = ("excel", "word", "ppt")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


@dataclass
class AuditRow:
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
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sanitize_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return EMAIL_RE.sub(r"\1(at)\2", value)


def _sanitize_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_obj(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_obj(v) for v in value]
    return _sanitize_text(value)


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
    row = asdict(
        AuditRow(
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
    rows.append(_sanitize_obj(row))


def _write_jsonl(path: Path, rows: List[Dict[str, Any]], truncate: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_sanitize_obj(row), ensure_ascii=False, default=str) + "\n")


def _infer_tasks(prompt: str) -> List[str]:
    p = (prompt or "").lower()
    tasks: List[str] = []

    if "excel" in p or "xlsx" in p or "表" in p:
        tasks.append("excel")
    if "word" in p or "docx" in p or "文書" in p or "要約" in p:
        tasks.append("word")
    if "ppt" in p or "powerpoint" in p or "slide" in p or "スライド" in p:
        tasks.append("ppt")

    if not tasks and ("作って" in p or "作成" in p or "make" in p or "create" in p):
        tasks = list(_TASKS)

    seen: List[str] = []
    for task in tasks:
        if task not in seen:
            seen.append(task)
    return seen


def _is_ambiguous_prompt(prompt: str) -> bool:
    p = (prompt or "").lower()
    ambiguous_terms = (
        "どっち",
        "どちら",
        "どれ",
        "which",
        "either",
        "better",
        "おすすめ",
        "?",
        "？",
    )
    return any(term in p for term in ambiguous_terms)


def _contains_pii_like(text: str) -> bool:
    return bool(EMAIL_RE.search(text or ""))


def _deterministic_random(seed: int, payload: str) -> float:
    digest = hashlib.sha256(f"{seed}:{payload}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(16**16)


def make_random_hitl_resolver(
    seed: int,
    p_continue: float,
) -> Callable[..., HitlChoice]:
    """
    Deterministic resolver.
    Same logical input -> same choice, independent of call order.
    """

    threshold = max(0.0, min(1.0, float(p_continue)))
    base_seed = int(seed)

    def resolver(*args, **kwargs) -> HitlChoice:
        if args and isinstance(args[0], dict):
            ctx = dict(args[0])
        else:
            ctx = {
                "run_id": args[0] if len(args) > 0 else kwargs.get("run_id", ""),
                "task_id": args[1] if len(args) > 1 else kwargs.get("task_id", ""),
                "layer": args[2] if len(args) > 2 else kwargs.get("layer", ""),
                "reason_code": args[3] if len(args) > 3 else kwargs.get("reason_code", ""),
            }

        task = str(ctx.get("task") or ctx.get("task_id") or "")
        layer = str(ctx.get("layer") or "")
        reason = str(ctx.get("reason_code") or "")
        prompt = str(ctx.get("prompt") or "")
        payload = f"{task}|{layer}|{reason}|{prompt}"

        return "CONTINUE" if _deterministic_random(base_seed, payload) < threshold else "STOP"

    return resolver


def semantic_signature_sha256(rows: List[Dict[str, Any]]) -> str:
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
    stable_rows: List[Dict[str, Any]] = []
    for row in rows:
        sanitized = _sanitize_obj(row)
        stable_rows.append({k: sanitized.get(k) for k in keep_keys})
    blob = json.dumps(
        stable_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _call_hitl_resolver(
    hitl_resolver: Callable[..., HitlChoice],
    *,
    run_id: str,
    task_id: str,
    task: str,
    layer: str,
    reason_code: str,
    prompt: str,
) -> HitlChoice:
    ctx = {
        "run_id": run_id,
        "task_id": task_id,
        "task": task,
        "layer": layer,
        "reason_code": reason_code,
        "prompt": prompt,
    }
    try:
        return hitl_resolver(ctx)
    except TypeError:
        return hitl_resolver(run_id, task_id, layer, reason_code)


def _build_rows_and_result(
    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[..., HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[SimulationResult, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    tasks = _infer_tasks(prompt)
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

    if not tasks:
        _append_row(
            rows,
            run_id=run_id,
            layer="meaning_gate",
            event="GATE_MEANING",
            task=None,
            decision=None,
            reason_code="ENTER_GATE_MEANING",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )
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
        _append_row(
            rows,
            run_id=run_id,
            layer="orchestrator",
            event="ORCH_FINAL",
            task=None,
            decision="STOPPED",
            reason_code="MEANING_NO_TASKS",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )
        return SimulationResult(decision="STOPPED", tasks=[], artifacts_written_task_ids=[]), rows

    task_results: List[TaskResult] = []
    any_run = False
    any_pause = False
    any_stop = False
    any_sealed = False
    overall_reason = "OK"

    for task in tasks:
        task_id = f"task_{task}"
        task_faults = faults.get(task, {})
        task_sealed = False
        task_decision: Decision = "RUN"
        task_reason = "OK"

        _append_row(
            rows,
            run_id=run_id,
            layer="meaning_gate",
            event="GATE_MEANING",
            task=task,
            decision=None,
            reason_code="ENTER_GATE_MEANING",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )
        _append_row(
            rows,
            run_id=run_id,
            layer="meaning_gate",
            event="MEANING_OK",
            task=task,
            decision=None,
            reason_code="MEANING_OK",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        _append_row(
            rows,
            run_id=run_id,
            layer="consistency_gate",
            event="GATE_CONSISTENCY",
            task=task,
            decision=None,
            reason_code="ENTER_GATE_CONSISTENCY",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        if task_faults.get("kind_prompt_mismatch"):
            _append_row(
                rows,
                run_id=run_id,
                layer="consistency_gate",
                event="CONSISTENCY_STOP",
                task=task,
                decision="STOPPED",
                reason_code="CONSISTENCY_KIND_PROMPT_MISMATCH",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
            )
            task_decision = "STOPPED"
            task_reason = "CONSISTENCY_KIND_PROMPT_MISMATCH"
            any_stop = True
            overall_reason = task_reason
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=task_decision,
                    sealed=False,
                    artifact_path=None,
                    reason_code=task_reason,
                )
            )
            continue

        _append_row(
            rows,
            run_id=run_id,
            layer="consistency_gate",
            event="CONSISTENCY_OK",
            task=task,
            decision=None,
            reason_code="CONSISTENCY_OK",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        _append_row(
            rows,
            run_id=run_id,
            layer="relativity_gate",
            event="GATE_RFL",
            task=task,
            decision=None,
            reason_code="ENTER_GATE_RFL",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        if _is_ambiguous_prompt(prompt) or task_faults.get("ambiguous_prompt"):
            _append_row(
                rows,
                run_id=run_id,
                layer="relativity_gate",
                event="HITL_REQUESTED",
                task=task,
                decision="PAUSE_FOR_HITL",
                reason_code="REL_BOUNDARY_UNSTABLE",
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
            )

            if hitl_resolver is None:
                _append_row(
                    rows,
                    run_id=run_id,
                    layer="hitl_finalize",
                    event="HITL_UNRESOLVED",
                    task=task,
                    decision="PAUSE_FOR_HITL",
                    reason_code="HITL_PENDING",
                    sealed=False,
                    overrideable=True,
                    final_decider="SYSTEM",
                )
                task_decision = "PAUSE_FOR_HITL"
                task_reason = "HITL_PENDING"
                any_pause = True
                overall_reason = task_reason
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        task=task,
                        decision=task_decision,
                        sealed=False,
                        artifact_path=None,
                        reason_code=task_reason,
                    )
                )
                continue

            choice = _call_hitl_resolver(
                hitl_resolver,
                run_id=run_id,
                task_id=task_id,
                task=task,
                layer="relativity_gate",
                reason_code="REL_BOUNDARY_UNSTABLE",
                prompt=prompt,
            )

            _append_row(
                rows,
                run_id=run_id,
                layer="hitl_finalize",
                event="HITL_DECIDED",
                task=task,
                decision="RUN" if choice == "CONTINUE" else "STOPPED",
                reason_code="HITL_CONTINUE" if choice == "CONTINUE" else "HITL_STOP",
                sealed=False,
                overrideable=False,
                final_decider="USER",
                detail=choice,
            )

            if choice == "STOP":
                task_decision = "STOPPED"
                task_reason = "HITL_STOP"
                any_stop = True
                overall_reason = task_reason
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        task=task,
                        decision=task_decision,
                        sealed=False,
                        artifact_path=None,
                        reason_code=task_reason,
                    )
                )
                continue

        _append_row(
            rows,
            run_id=run_id,
            layer="ethics_gate",
            event="GATE_ETHICS",
            task=task,
            decision=None,
            reason_code="ENTER_GATE_ETHICS",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        if (
            task_faults.get("policy_danger")
            or task_faults.get("pii")
            or task_faults.get("leak_email")
            or _contains_pii_like(prompt)
        ):
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
            task_decision = "STOPPED"
            task_reason = "SEALED_BY_ETHICS"
            task_sealed = True
            any_stop = True
            any_sealed = True
            overall_reason = task_reason
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=task_decision,
                    sealed=task_sealed,
                    artifact_path=None,
                    reason_code=task_reason,
                )
            )
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

        _append_row(
            rows,
            run_id=run_id,
            layer="acc_gate",
            event="GATE_ACC",
            task=task,
            decision=None,
            reason_code="ENTER_GATE_ACC",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        if task_faults.get("force_stop"):
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
            task_decision = "STOPPED"
            task_reason = "ACC_FORCE_STOP"
            any_stop = True
            overall_reason = task_reason
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=task_decision,
                    sealed=False,
                    artifact_path=None,
                    reason_code=task_reason,
                )
            )
            continue

        break_contract = bool(task_faults.get("break_contract"))
        done = False

        for attempt in range(1, max_attempts_per_task + 1):
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
                detail=f"attempt={attempt}",
            )

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

                if enable_runaway_seal and attempt >= runaway_threshold:
                    _append_row(
                        rows,
                        run_id=run_id,
                        layer="acc_gate",
                        event="AGENT_SEALED",
                        task=task,
                        decision="STOPPED",
                        reason_code="SEALED_BY_ACC",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        detail=f"attempts={attempt}",
                    )
                    task_decision = "STOPPED"
                    task_reason = "SEALED_BY_ACC"
                    task_sealed = True
                    any_stop = True
                    any_sealed = True
                    overall_reason = task_reason
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
            task_decision = "RUN"
            task_reason = "OK"
            any_run = True
            done = True
            break

        if break_contract and not task_sealed and not done:
            _append_row(
                rows,
                run_id=run_id,
                layer="consistency_gate",
                event="REGEN_REQUESTED",
                task=task,
                decision="PAUSE_FOR_HITL",
                reason_code="REGEN_REQUESTED",
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
            )
            _append_row(
                rows,
                run_id=run_id,
                layer="consistency_gate",
                event="REGEN_INSTRUCTIONS",
                task=task,
                decision="PAUSE_FOR_HITL",
                reason_code="REGEN_INSTRUCTIONS",
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                detail="Contract mismatch detected; regenerate artifact.",
            )
            task_decision = "PAUSE_FOR_HITL"
            task_reason = "REGEN_REQUESTED"
            any_pause = True
            overall_reason = task_reason

        task_results.append(
            TaskResult(
                task_id=task_id,
                task=task,
                decision=task_decision,
                sealed=task_sealed,
                artifact_path=None,
                reason_code=task_reason,
            )
        )

    if any_stop:
        overall_decision: Decision = "STOPPED"
    elif any_pause:
        overall_decision = "PAUSE_FOR_HITL"
    else:
        overall_decision = "RUN"

    _append_row(
        rows,
        run_id=run_id,
        layer="orchestrator",
        event="ORCH_FINAL",
        task=None,
        decision=overall_decision,
        reason_code=overall_reason,
        sealed=any_sealed,
        overrideable=(overall_decision == "PAUSE_FOR_HITL"),
        final_decider="SYSTEM",
    )

    return (
        SimulationResult(
            decision=overall_decision,
            tasks=task_results,
            artifacts_written_task_ids=[],
        ),
        rows,
    )


def run_simulation_mem(
    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[..., HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[SimulationResult, List[Dict[str, Any]]]:
    return _build_rows_and_result(
        prompt=prompt,
        run_id=run_id,
        faults=faults,
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=enable_runaway_seal,
        runaway_threshold=runaway_threshold,
        max_attempts_per_task=max_attempts_per_task,
    )


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[..., HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
    audit_path: str = "audit.jsonl",
    artifact_dir: str = "artifacts",
    truncate_audit_on_start: bool = True,
) -> SimulationResult:
    result, rows = run_simulation_mem(
        prompt=prompt,
        run_id=run_id,
        faults=faults,
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=enable_runaway_seal,
        runaway_threshold=runaway_threshold,
        max_attempts_per_task=max_attempts_per_task,
    )

    artifact_root = Path(artifact_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)

    tasks_out: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task in result.tasks:
        artifact_path: Optional[str] = None
        if task.decision == "RUN":
            artifact_path = str(artifact_root / f"{task.task_id}.txt")
            Path(artifact_path).write_text(
                f"{task.task} artifact (run_id={run_id})",
                encoding="utf-8",
            )
            artifacts_written.append(task.task_id)
            _append_row(
                rows,
                run_id=run_id,
                layer="dispatch",
                event="ARTIFACT_WRITTEN",
                task=task.task,
                decision="RUN",
                reason_code="ARTIFACT_WRITTEN",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                detail=artifact_path,
            )
        else:
            _append_row(
                rows,
                run_id=run_id,
                layer="dispatch",
                event="ARTIFACT_SKIPPED",
                task=task.task,
                decision=task.decision,
                reason_code="ARTIFACT_SKIPPED",
                sealed=task.sealed,
                overrideable=False,
                final_decider="SYSTEM",
            )

        tasks_out.append(
            TaskResult(
                task_id=task.task_id,
                task=task.task,
                decision=task.decision,
                sealed=task.sealed,
                artifact_path=artifact_path,
                reason_code=task.reason_code,
            )
        )

    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        decision=result.decision,
        tasks=tasks_out,
        artifacts_written_task_ids=artifacts_written,
    )


def assert_no_artifacts_for_blocked_tasks(result: SimulationResult) -> None:
    for task in result.tasks:
        if task.decision != "RUN":
            assert task.artifact_path is None, (
                f"Blocked task wrote artifact: {task.task_id}"
            )


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
    start = time.perf_counter()

    overall_decision_counts: Dict[str, int] = {
        "RUN": 0,
        "PAUSE_FOR_HITL": 0,
        "STOPPED": 0,
    }
    crash_count = 0
    pii_leak_count = 0
    hitl_requested_count = 0
    seal_event_count = 0
    sample_rows: List[Dict[str, Any]] = []
    runs_data: List[Dict[str, Any]] = []

    for i in range(int(runs)):
        run_id = f"SIM#{i:05d}"
        resolver = make_random_hitl_resolver(
            seed=int(seed) + i,
            p_continue=float(p_continue),
        )
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
        except Exception as exc:  # pragma: no cover
            crash_count += 1
            rows = []
            result = SimulationResult(
                decision="STOPPED",
                tasks=[],
                artifacts_written_task_ids=[],
            )
            reason_code = f"EXC:{type(exc).__name__}"
        else:
            reason_code = "OK"

        decision = _normalize_decision(result.decision)
        overall_decision_counts[decision] = overall_decision_counts.get(decision, 0) + 1

        if any(row.get("event") == "HITL_REQUESTED" for row in rows):
            hitl_requested_count += 1

        if any(
            row.get("event") in ("ETHICS_SEALED", "AGENT_SEALED")
            for row in rows
        ):
            seal_event_count += 1

        if any("@" in json.dumps(_sanitize_obj(row), ensure_ascii=False) for row in rows):
            pii_leak_count += 1

        runs_data.append(
            {
                "run_id": run_id,
                "decision": decision,
                "reason_code": reason_code,
                "sealed": any(
                    row.get("event") in ("ETHICS_SEALED", "AGENT_SEALED")
                    for row in rows
                ),
                "hitl_requested": any(
                    row.get("event") == "HITL_REQUESTED" for row in rows
                ),
            }
        )

        if i == 0:
            sample_rows = rows

    elapsed = max(1e-9, time.perf_counter() - start)
    repro_digest = semantic_signature_sha256(sample_rows)

    return {
        "version": __version__,
        "runs": int(runs),
        "seed": int(seed),
        "prompt": prompt,
        "faults": faults,
        "overall_decision_counts": overall_decision_counts,
        "decision_counts": dict(overall_decision_counts),
        "run_rate": float(overall_decision_counts.get("RUN", 0)) / max(1, int(runs)),
        "pause_rate": float(overall_decision_counts.get("PAUSE_FOR_HITL", 0)) / max(1, int(runs)),
        "stop_rate": float(overall_decision_counts.get("STOPPED", 0)) / max(1, int(runs)),
        "hitl_requested_rate": float(hitl_requested_count) / max(1, int(runs)),
        "crashes": int(crash_count),
        "crash_count": int(crash_count),
        "crash_free_rate": float(int(runs) - crash_count) / max(1, int(runs)),
        "pii_leaks": int(pii_leak_count),
        "pii_leak_count": int(pii_leak_count),
        "at_sign_violations": int(pii_leak_count),
        "seal_event_count": int(seal_event_count),
        "runs_per_sec": float(int(runs)) / elapsed,
        "repro_semantic_digest_sha256": repro_digest,
        "sample_rows_count": len(sample_rows),
        "runs_data": runs_data,
    }


def safety_scorecard(
    report: Dict[str, Any],
    *,
    require_seal_events: bool,
    require_pii_zero: bool,
    require_crash_free: bool,
) -> Dict[str, Any]:
    fail_reasons: List[str] = []

    if require_seal_events and int(report.get("seal_event_count", 0)) <= 0:
        fail_reasons.append("NO_SEAL_EVENTS")
    if require_pii_zero and int(report.get("pii_leak_count", 0)) != 0:
        fail_reasons.append("PII_LEAK_DETECTED")
    if require_crash_free and float(report.get("crash_free_rate", 0.0)) < 1.0:
        fail_reasons.append("NOT_CRASH_FREE")

    return {
        "pass": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "seal_event_count": int(report.get("seal_event_count", 0)),
        "pii_leak_count": int(report.get("pii_leak_count", 0)),
        "crash_free_rate": float(report.get("crash_free_rate", 0.0)),
    }


def interactive_hitl_resolver(ctx: Dict[str, Any]) -> HitlChoice:
    task = ctx.get("task", "?")
    raw = input(f"[HITL] Continue task '{task}'? [y/N]: ").strip().lower()
    return "CONTINUE" if raw in {"y", "yes"} else "STOP"
