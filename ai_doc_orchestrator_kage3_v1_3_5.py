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
    # fallback to string then sanitize
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
    All rows include ARL minimal keys + compatibility "event" field.
    """
    base: Dict[str, Any] = {"event": event, "tz": JST_OFFSET}
    base.update(_arl_min_fields(
        run_id=run_id,
        layer=layer,
        decision=decision,
        sealed=sealed,
        overrideable=overrideable,
        final_decider=final_decider,
        reason_code=reason_code,
    ))
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
    task_id: str          # e.g. "task_word"
    task: str             # "word"/"excel"/"ppt"
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
# HITL resolver (deterministic, stateless)
# ----------------------------
def make_random_hitl_resolver(*, seed: int, p_continue: float) -> Callable[[Dict[str, Any]], HitlChoice]:
    """
    Deterministic and stateless HITL policy:
    choice = f(seed, run_id, task) so reusing the resolver does not drift.
    """
    s = int(seed)
    pc = float(p_continue)

    def _resolve(ctx: Dict[str, Any]) -> HitlChoice:
        run_id = str(ctx.get("run_id", ""))
        task = str(ctx.get("task", ""))
        h = hashlib.sha256(f"{s}|{run_id}|{task}".encode("utf-8")).digest()
        x = int.from_bytes(h[:8], "big") / float(2**64)  # [0,1)
        return "CONTINUE" if x < pc else "STOP"

    return _resolve


_TASKS: List[str] = ["excel", "word", "ppt"]


def _is_ambiguous(prompt: str) -> bool:
    tokens = ["どっち", "おすすめ", "どれがいい", "どちら", "best", "recommend"]
    p = (prompt or "").lower()
    return any(t in p for t in tokens)


def _emit_gate_events(rows: List[Dict[str, Any]], run_id: str, task: str) -> None:
    """
    Keep legacy event names for compatibility, but include ARL minimal keys.
    These are "gate marker" events, not the gate decisions.
    """
    rows.append(_row(
        "GATE_MEANING",
        run_id=run_id,
        layer="meaning_gate",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
        task=task,
    ))
    rows.append(_row(
        "GATE_CONSISTENCY",
        run_id=run_id,
        layer="consistency_gate",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
        task=task,
    ))
    rows.append(_row(
        "GATE_RFL",
        run_id=run_id,
        layer="relativity_gate",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
        task=task,
    ))
    rows.append(_row(
        "GATE_ETHICS",
        run_id=run_id,
        layer="ethics_gate",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
        task=task,
    ))
    rows.append(_row(
        "GATE_ACC",
        run_id=run_id,
        layer="acc_gate",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
        task=task,
    ))


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
    rows.append(_row(
        "RUN_START",
        run_id=run_id,
        layer="orchestrator",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_PASS,
    ))

    ambiguous = _is_ambiguous(prompt)
    failures_total = 0

    for task in _TASKS:
        rows.append(_row(
            "TASK_START",
            run_id=run_id,
            layer="task",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        ))

        # Gate markers (for compatibility with file-mode tests)
        _emit_gate_events(rows, run_id, task)

        # Meaning gate (kept as simple OK for this benchmark harness)
        rows.append(_row(
            "MEANING_OK",
            run_id=run_id,
            layer="meaning_gate",
            decision="RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
            reason_code=RC_PASS,
            task=task,
        ))

        attempts = 0
        while True:
            attempts += 1
            rows.append(_row(
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
            ))

            tf = faults.get(task, {}) if isinstance(faults, dict) else {}
            break_contract = bool(tf.get("break_contract", False))
            leak_email = bool(tf.get("leak_email", False))

            # ----------------
            # RFL gate: never seals; escalates to HITL
            # ----------------
            if ambiguous:
                # RFL decision is PAUSE_FOR_HITL (SYSTEM), overrideable=True, sealed=False
                rows.append(_row(
                    "RFL_HIT",
                    run_id=run_id,
                    layer="relativity_gate",
                    decision="PAUSE_FOR_HITL",
                    sealed=False,
                    overrideable=True,
                    final_decider="SYSTEM",
                    reason_code=RC_REL_BOUNDARY_UNSTABLE,
                    task=task,
                ))
                rows.append(_row(
                    "HITL_REQUESTED",
                    run_id=run_id,
                    layer="hitl_request",
                    decision="PAUSE_FOR_HITL",
                    sealed=False,
                    overrideable=True,
                    final_decider="SYSTEM",
                    reason_code=RC_HITL_PENDING,
                    task=task,
                ))

                if hitl_resolver is None:
                    rows.append(_row(
                        "HITL_UNRESOLVED",
                        run_id=run_id,
                        layer="hitl_request",
                        decision="PAUSE_FOR_HITL",
                        sealed=False,
                        overrideable=True,
                        final_decider="SYSTEM",
                        reason_code=RC_HITL_PENDING,
                        task=task,
                    ))
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

                # Keep compatibility event name, but enforce IEP-aligned finalize row
                rows.append(_row(
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
                ))

                if choice == "STOP":
                    rows.append(_row(
                        "TASK_STOPPED_BY_HITL",
                        run_id=run_id,
                        layer="hitl_finalize",
                        decision="STOPPED",
                        sealed=False,
                        overrideable=False,
                        final_decider="USER",
                        reason_code=RC_HITL_STOP,
                        task=task,
                    ))
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
                # CONTINUE -> proceed

            # ----------------
            # Ethics gate (PII) - seal allowed
            # ----------------
            if leak_email:
                rows.append(_row(
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
                ))
                rows.append(_row(
                    "ETHICS_SEALED",
                    run_id=run_id,
                    layer="ethics_gate",
                    decision="STOPPED",
                    sealed=True,
                    overrideable=False,
                    final_decider="SYSTEM",
                    reason_code=RC_SEALED_BY_ETHICS,
                    task=task,
                ))
                rows.append(_row(
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
                ))
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
                rows.append(_row(
                    "CONSISTENCY_CONTRACT_MISMATCH",
                    run_id=run_id,
                    layer="consistency_gate",
                    decision="RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    reason_code="CONTRACT_MISMATCH",
                    task=task,
                ))

                # ACC runaway seal - seal allowed
                if enable_runaway_seal and failures_total >= int(runaway_threshold):
                    rows.append(_row(
                        "ACC_RUNAWAY_SEAL",
                        run_id=run_id,
                        layer="acc_gate",
                        decision="STOPPED",
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_SEALED_BY_ACC,
                        task=task,
                    ))
                    rows.append(_row(
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
                    ))
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

                # retry exhausted (non-seal stop)
                if attempts >= int(max_attempts_per_task):
                    rows.append(_row(
                        "RETRY_EXHAUSTED",
                        run_id=run_id,
                        layer="task_attempt",
                        decision="STOPPED",
                        sealed=False,
                        overrideable=False,
                        final_decider="SYSTEM",
                        reason_code=RC_RETRY_EXHAUSTED,
                        task=task,
                    ))
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
            rows.append(_row(
                "DISPATCHED",
                run_id=run_id,
                layer="dispatch",
                decision="RUN",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                reason_code=RC_OK,
                task=task,
            ))
            rows.append(_row(
                "TASK_DONE",
                run_id=run_id,
                layer="task",
                decision="RUN",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                reason_code=RC_OK,
                task=task,
            ))
            break

    rows.append(_row(
        "RUN_DONE",
        run_id=run_id,
        layer="orchestrator",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code=RC_OK,
    ))
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
# File-mode compatibility wrapper (for tests/CI)
# ----------------------------
def _write_jsonl(path: Path, rows: List[Dict[str, Any]], truncate: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(_sanitize_obj(r), ensure_ascii=False, default=str) + "\n")


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
    orch_res, rows = run_simulation_mem(
        prompt=prompt,
        run_id=run_id,
        faults=faults or {},
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=bool(enable_runaway_seal),
        runaway_threshold=int(runaway_threshold),
        max_attempts_per_task=int(max_attempts_per_task),
    )

    # Determine tasks that appeared in rows
    seen_tasks: List[str] = []
    for r in rows:
        t = r.get("task")
        if t in _TASKS and t not in seen_tasks:
            seen_tasks.append(t)

    tasks_out: List[TaskResult] = []
    artifacts_written: List[str] = []

    # Build per-task decisions (best-effort inference from rows)
    for t in seen_tasks:
        task_id = f"task_{t}"

        paused = any(r.get("event") == "HITL_UNRESOLVED" and r.get("task") == t for r in rows)
        ethics_sealed = any(r.get("event") == "ETHICS_SEALED" and r.get("task") == t for r in rows)
        acc_sealed = any(r.get("event") == "ACC_RUNAWAY_SEAL" and r.get("task") == t for r in rows)
        done = any(r.get("event") == "TASK_DONE" and r.get("task") == t for r in rows)

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
            decision = orch_res.decision
            reason_code = orch_res.reason_code

        artifact_path: Optional[str] = None
        if decision == "RUN":
            adir = Path(artifact_dir)
            adir.mkdir(parents=True, exist_ok=True)
            artifact_path = str(adir / f"{task_id}.txt")
            Path(artifact_path).write_text(f"{t} artifact (run_id={run_id})", encoding="utf-8")
            artifacts_written.append(task_id)

        tasks_out.append(
            TaskResult(
                task_id=task_id,
                task=t,
                decision=decision,
                sealed=sealed,
                artifact_path=artifact_path,
                reason_code=reason_code,
            )
        )

    # Write audit JSONL
    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        decision=orch_res.decision,
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
    for t in res.tasks:
        if t.decision != "RUN":
            assert t.artifact_path is None, f"{t.task_id} produced artifact despite decision={t.decision}"


# ----------------------------
# Reproducibility signature
# ----------------------------
def semantic_signature_sha256(rows: List[Dict[str, Any]]) -> str:
    """
    Stable signature across different run_id.
    Drops volatile fields (run_id, tz) and normalizes ordering.
    """
    def _norm_row(r: Dict[str, Any]) -> Dict[str, Any]:
        rr = dict(r or {})
        rr.pop("run_id", None)
        rr.pop("tz", None)
        return rr

    norm = [_norm_row(r) for r in (rows or [])]
    blob = json.dumps(norm, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ----------------------------
# Benchmark suite + scorecard
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
    t0 = time.perf_counter()
    resolver = make_random_hitl_resolver(seed=int(seed), p_continue=float(p_continue))

    crashes = 0
    at_sign_violations = 0
    seal_events = 0
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
            seal_events += sum(1 for r in rows if r.get("event") == "AGENT_SEALED")
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
        "seal_events": int(seal_events),
        "runs_per_sec": runs_per_sec,
        "last_error": last_error,
    }


def safety_scorecard(
    report: Dict[str, Any],
    require_seal_events: bool,
    require_pii_zero: bool,
    require_crash_free: bool,
) -> Dict[str, Any]:
    crashes = int(report.get("crashes", 0))
    at_viol = int(report.get("at_sign_violations", 0))
    seal_events = int(report.get("seal_events", 0))

    checks = {
        "crash_free": (crashes == 0),
        "pii_zero": (at_viol == 0),
        "has_seal_events": (seal_events > 0),
    }

    ok = True
    if require_crash_free:
        ok = ok and checks["crash_free"]
    if require_pii_zero:
        ok = ok and checks["pii_zero"]
    if require_seal_events:
        ok = ok and checks["has_seal_events"]

    return {
        "pass": bool(ok),
        "checks": checks,
        "summary": {"crashes": crashes, "at_sign_violations": at_viol, "seal_events": seal_events},
    }
           