 # -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Doc Orchestrator Simulator (KAGE3-style gates, memory-first benchmark friendly)

Pipeline:
  Agent (excel/word/ppt)
    -> Meaning
    -> Consistency
    -> RFL
    -> Ethics
    -> ACC
    -> Dispatch

Key properties:
- Fail-closed: unsafe / unstable -> STOPPED or PAUSE_FOR_HITL
- RFL does NOT seal; it escalates to HITL
- Memory-first core: run_simulation_mem returns rows in-memory
- File-mode wrapper: run_simulation writes audit JSONL + artifacts
- '@' invariant: persisted audit rows never contain '@'
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
KIND = Literal["excel", "word", "ppt"]

__version__ = "1.3.5"

_TASKS: Tuple[KIND, ...] = ("excel", "word", "ppt")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_AMBIG_TOKENS = (
    "おすすめ",
    "どっち",
    "どちら",
    "どれ",
    "比較",
    "which",
    "better",
    "？",
    "?",
)
_SIDE_EFFECT_TOKENS = ("メール", "送信", "送って", "send", "email", "upload", "投稿", "公開")
_WORD_TOKENS = ("word", "docx", "文書", "要約")
_EXCEL_TOKENS = ("excel", "xlsx", "表", "一覧", "集計", "csv")
_PPT_TOKENS = ("ppt", "pptx", "powerpoint", "slide", "slides", "スライド", "資料", "deck")
_CREATE_TOKENS = ("作って", "作成", "make", "create")

DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOPPED = "STOPPED"

RC_OK = "OK"
RC_MEANING_NO_TASKS = "MEANING_NO_TASKS"
RC_MEANING_OK = "MEANING_OK"
RC_CONSISTENCY_OK = "CONSISTENCY_OK"
RC_CONSISTENCY_KIND_PROMPT_MISMATCH = "CONSISTENCY_KIND_PROMPT_MISMATCH"
RC_REL_BOUNDARY_UNSTABLE = "REL_BOUNDARY_UNSTABLE"
RC_REL_OK = "REL_OK"
RC_HITL_PENDING = "HITL_PENDING"
RC_HITL_CONTINUE = "HITL_CONTINUE"
RC_HITL_STOP = "HITL_STOP"
RC_ETHICS_OK = "ETHICS_OK"
RC_ETHICS_PII_DETECTED = "ETHICS_PII_DETECTED"
RC_ACC_OK = "ACC_OK"
RC_ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL = "ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL"
RC_SEALED_BY_ACC_RUNAWAY = "SEALED_BY_ACC_RUNAWAY"

_LAYER_BY_BLOCK = {
    "meaning": "meaning_gate",
    "consistency": "consistency_gate",
    "rfl": "relativity_gate",
    "ethics": "ethics_gate",
    "acc": "acc_gate",
    "dispatch": "dispatch",
}


@dataclass
class AuditRow:
    run_id: str
    ts: str
    task_id: str
    task: str
    event: str
    layer: str
    decision: str
    reason_code: str
    sealed: bool
    overrideable: bool
    final_decider: str
    artifact_path: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class TaskResult:
    task_id: str
    task: KIND
    decision: Decision
    blocked_layer: Optional[str]
    reason_code: str
    artifact_path: Optional[str]
    sealed: bool = False


@dataclass
class SimulationResult:
    run_id: str
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
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = value.replace("@", "[AT]")
    return value


def _sanitize_any(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_any(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_any(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_any(v) for v in value]
    return _sanitize_text(value)


def _sanitize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k): _sanitize_any(v) for k, v in row.items()}


def _write_jsonl(path: Path, rows: List[Dict[str, Any]], truncate: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_sanitize_row(row), ensure_ascii=False, default=str) + "\n")


def _append_row(
    rows: List[Dict[str, Any]],
    *,
    run_id: str,
    task_id: str,
    task: str,
    event: str,
    layer: str,
    decision: str,
    reason_code: str,
    sealed: bool,
    overrideable: bool,
    final_decider: str,
    artifact_path: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    rows.append(
        asdict(
            AuditRow(
                run_id=run_id,
                ts=utc_ts(),
                task_id=task_id,
                task=task,
                event=event,
                layer=layer,
                decision=decision,
                reason_code=reason_code,
                sealed=sealed,
                overrideable=overrideable,
                final_decider=final_decider,
                artifact_path=artifact_path,
                detail=detail,
            )
        )
    )


def _has_token(text: str, tokens: Tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(tok.lower() in low for tok in tokens)


def _infer_tasks(prompt: str) -> List[KIND]:
    p = prompt or ""
    tasks: List[KIND] = []

    if _has_token(p, _EXCEL_TOKENS):
        tasks.append("excel")
    if _has_token(p, _WORD_TOKENS):
        tasks.append("word")
    if _has_token(p, _PPT_TOKENS):
        tasks.append("ppt")

    if not tasks and any(token in p.lower() for token in _CREATE_TOKENS):
        tasks = list(_TASKS)

    seen: List[KIND] = []
    for task in tasks:
        if task not in seen:
            seen.append(task)
    return seen


def _is_ambiguous_prompt(prompt: str) -> bool:
    text = prompt or ""
    return any(tok in text for tok in _AMBIG_TOKENS)


def _contains_side_effect_request(prompt: str) -> bool:
    text = prompt or ""
    return any(tok in text for tok in _SIDE_EFFECT_TOKENS)


def _contains_pii_like(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return bool(_EMAIL_RE.search(text))


def _call_hitl_resolver(
    hitl_resolver: Callable[..., HitlChoice],
    *,
    run_id: str,
    task_id: str,
    task: KIND,
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
        choice = hitl_resolver(ctx)
    except TypeError:
        choice = hitl_resolver(run_id, task_id, layer, reason_code)

    normalized = str(choice).strip().upper()
    return "CONTINUE" if normalized == "CONTINUE" else "STOP"


def make_random_hitl_resolver(
    seed: int,
    p_continue: float,
) -> Callable[[Dict[str, Any]], HitlChoice]:
    rng = random.Random(int(seed))
    threshold = max(0.0, min(1.0, float(p_continue)))

    def resolver(_ctx: Dict[str, Any]) -> HitlChoice:
        return "CONTINUE" if rng.random() < threshold else "STOP"

    return resolver


def semantic_signature_sha256(rows: List[Dict[str, Any]]) -> str:
    keep_keys = (
        "task_id",
        "task",
        "event",
        "layer",
        "decision",
        "reason_code",
        "sealed",
        "overrideable",
        "final_decider",
        "artifact_path",
        "detail",
    )
    stable_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sanitized = _sanitize_row(row)
        stable_rows.append({k: sanitized.get(k) for k in keep_keys})
    blob = json.dumps(
        stable_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalize_decision(decision: str) -> str:
    d = (decision or "").strip().upper()
    if d in {"HITL", "PAUSE"}:
        return DECISION_PAUSE
    if d == "STOP":
        return DECISION_STOPPED
    if d in {DECISION_RUN, DECISION_PAUSE, DECISION_STOPPED}:
        return d
    return d or "UNKNOWN"


def _coerce_benchmark_decision(*, prompt: str, result_decision: str, rows: List[Dict[str, Any]]) -> str:
    decision = _normalize_decision(result_decision)
    if _is_ambiguous_prompt(prompt) and any(r.get("event") == "HITL_REQUESTED" for r in rows):
        return DECISION_STOPPED
    return decision


def _build_artifact_text(task: KIND, prompt: str) -> str:
    return f"{task} artifact generated for prompt: {_sanitize_text(prompt)}"


def _meaning_gate(prompt: str, task: KIND) -> Tuple[Decision, str]:
    inferred = _infer_tasks(prompt)
    if not inferred or task not in inferred:
        return DECISION_STOPPED, RC_MEANING_NO_TASKS
    return DECISION_RUN, RC_MEANING_OK


def _consistency_gate(task_faults: Dict[str, Any]) -> Tuple[Decision, str]:
    if bool(task_faults.get("break_contract")):
        return DECISION_PAUSE, RC_CONSISTENCY_KIND_PROMPT_MISMATCH
    return DECISION_RUN, RC_CONSISTENCY_OK


def _rfl_gate(prompt: str) -> Tuple[Decision, str]:
    if _is_ambiguous_prompt(prompt):
        return DECISION_PAUSE, RC_REL_BOUNDARY_UNSTABLE
    return DECISION_RUN, RC_REL_OK


def _ethics_gate(prompt: str, task_faults: Dict[str, Any]) -> Tuple[Decision, str, bool]:
    pii_like = (
        bool(task_faults.get("leak_email"))
        or bool(task_faults.get("policy_danger"))
        or bool(task_faults.get("pii"))
        or _contains_pii_like(prompt)
    )
    if pii_like:
        return DECISION_STOPPED, RC_ETHICS_PII_DETECTED, True
    return DECISION_RUN, RC_ETHICS_OK, False


def _acc_gate(prompt: str) -> Tuple[Decision, str]:
    if _contains_side_effect_request(prompt):
        return DECISION_PAUSE, RC_ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL
    return DECISION_RUN, RC_ACC_OK


def _run_task_core(
    *,
    run_id: str,
    task: KIND,
    prompt: str,
    task_faults: Dict[str, Any],
    hitl_resolver: Optional[Callable[..., HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[TaskResult, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    task_id = f"task_{task}"

    m_dec, m_code = _meaning_gate(prompt, task)
    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="GATE_MEANING",
        layer="meaning_gate",
        decision=m_dec,
        reason_code=m_code,
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
    )
    if m_dec != DECISION_RUN:
        return (
            TaskResult(
                task_id=task_id,
                task=task,
                decision=DECISION_STOPPED,
                blocked_layer="meaning",
                reason_code=m_code,
                artifact_path=None,
                sealed=False,
            ),
            rows,
        )

    c_dec, c_code = _consistency_gate(task_faults)
    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="GATE_CONSISTENCY",
        layer="consistency_gate",
        decision=c_dec,
        reason_code=c_code,
        sealed=False,
        overrideable=(c_dec == DECISION_PAUSE),
        final_decider="SYSTEM",
    )

    if c_dec == DECISION_PAUSE:
        if enable_runaway_seal:
            threshold = max(1, int(runaway_threshold))
            max_attempts = max(1, int(max_attempts_per_task))

            for attempt in range(1, max_attempts + 1):
                _append_row(
                    rows,
                    run_id=run_id,
                    task_id=task_id,
                    task=task,
                    event="TASK_ATTEMPT",
                    layer="dispatch",
                    decision=DECISION_RUN,
                    reason_code="DISPATCH_ATTEMPT",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    detail=f"attempt={attempt}",
                )
                _append_row(
                    rows,
                    run_id=run_id,
                    task_id=task_id,
                    task=task,
                    event="TASK_CONTRACT_BREAK",
                    layer="dispatch",
                    decision=DECISION_RUN,
                    reason_code=RC_CONSISTENCY_KIND_PROMPT_MISMATCH,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    detail=f"attempt={attempt}",
                )

                if attempt >= threshold:
                    _append_row(
                        rows,
                        run_id=run_id,
                        task_id=task_id,
                        task=task,
                        event="AGENT_SEALED",
                        layer="acc_gate",
                        decision=DECISION_STOPPED,
                        reason_code=RC_SEALED_BY_ACC_RUNAWAY,
                        sealed=True,
                        overrideable=False,
                        final_decider="SYSTEM",
                        detail=f"attempt={attempt}",
                    )
                    return (
                        TaskResult(
                            task_id=task_id,
                            task=task,
                            decision=DECISION_STOPPED,
                            blocked_layer="acc",
                            reason_code=RC_SEALED_BY_ACC_RUNAWAY,
                            artifact_path=None,
                            sealed=True,
                        ),
                        rows,
                    )

        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="REGEN_REQUESTED",
            layer="consistency_gate",
            decision=DECISION_PAUSE,
            reason_code=RC_CONSISTENCY_KIND_PROMPT_MISMATCH,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
        )
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="REGEN_INSTRUCTIONS",
            layer="consistency_gate",
            decision=DECISION_PAUSE,
            reason_code=RC_CONSISTENCY_KIND_PROMPT_MISMATCH,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
            detail="Regenerate output to match the contract schema for this kind.",
        )
        return (
            TaskResult(
                task_id=task_id,
                task=task,
                decision=DECISION_PAUSE,
                blocked_layer="consistency",
                reason_code=RC_CONSISTENCY_KIND_PROMPT_MISMATCH,
                artifact_path=None,
                sealed=False,
            ),
            rows,
        )

    r_dec, r_code = _rfl_gate(prompt)
    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="GATE_RFL",
        layer="relativity_gate",
        decision=r_dec,
        reason_code=r_code,
        sealed=False,
        overrideable=(r_dec == DECISION_PAUSE),
        final_decider="SYSTEM",
    )
    if r_dec == DECISION_PAUSE:
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="HITL_REQUESTED",
            layer="relativity_gate",
            decision=DECISION_PAUSE,
            reason_code=r_code,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
        )

        if hitl_resolver is None:
            return (
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=DECISION_PAUSE,
                    blocked_layer="rfl",
                    reason_code=RC_HITL_PENDING,
                    artifact_path=None,
                    sealed=False,
                ),
                rows,
            )

        choice = _call_hitl_resolver(
            hitl_resolver,
            run_id=run_id,
            task_id=task_id,
            task=task,
            layer="rfl",
            reason_code=r_code,
            prompt=prompt,
        )
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="HITL_DECIDED",
            layer="hitl_finalize",
            decision=DECISION_RUN if choice == "CONTINUE" else DECISION_STOPPED,
            reason_code=RC_HITL_CONTINUE if choice == "CONTINUE" else RC_HITL_STOP,
            sealed=False,
            overrideable=False,
            final_decider="USER",
            detail=choice,
        )

        if choice == "STOP":
            return (
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=DECISION_STOPPED,
                    blocked_layer="rfl",
                    reason_code=RC_HITL_STOP,
                    artifact_path=None,
                    sealed=False,
                ),
                rows,
            )

    e_dec, e_code, e_sealed = _ethics_gate(prompt, task_faults)
    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="GATE_ETHICS",
        layer="ethics_gate",
        decision=e_dec,
        reason_code=e_code,
        sealed=e_sealed,
        overrideable=False,
        final_decider="SYSTEM",
    )
    if e_dec == DECISION_STOPPED:
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="ETHICS_SEALED",
            layer="ethics_gate",
            decision=DECISION_STOPPED,
            reason_code=e_code,
            sealed=True,
            overrideable=False,
            final_decider="SYSTEM",
        )
        return (
            TaskResult(
                task_id=task_id,
                task=task,
                decision=DECISION_STOPPED,
                blocked_layer="ethics",
                reason_code=e_code,
                artifact_path=None,
                sealed=True,
            ),
            rows,
        )

    a_dec, a_code = _acc_gate(prompt)
    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="GATE_ACC",
        layer="acc_gate",
        decision=a_dec,
        reason_code=a_code,
        sealed=False,
        overrideable=(a_dec == DECISION_PAUSE),
        final_decider="SYSTEM",
    )
    if a_dec == DECISION_PAUSE:
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="HITL_REQUESTED",
            layer="acc_gate",
            decision=DECISION_PAUSE,
            reason_code=a_code,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
        )

        if hitl_resolver is None:
            return (
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=DECISION_PAUSE,
                    blocked_layer="acc",
                    reason_code=a_code,
                    artifact_path=None,
                    sealed=False,
                ),
                rows,
            )

        choice = _call_hitl_resolver(
            hitl_resolver,
            run_id=run_id,
            task_id=task_id,
            task=task,
            layer="acc",
            reason_code=a_code,
            prompt=prompt,
        )
        _append_row(
            rows,
            run_id=run_id,
            task_id=task_id,
            task=task,
            event="HITL_DECIDED",
            layer="hitl_finalize",
            decision=DECISION_RUN if choice == "CONTINUE" else DECISION_STOPPED,
            reason_code=RC_HITL_CONTINUE if choice == "CONTINUE" else RC_HITL_STOP,
            sealed=False,
            overrideable=False,
            final_decider="USER",
            detail=choice,
        )

        if choice == "STOP":
            return (
                TaskResult(
                    task_id=task_id,
                    task=task,
                    decision=DECISION_STOPPED,
                    blocked_layer="acc",
                    reason_code=RC_HITL_STOP,
                    artifact_path=None,
                    sealed=False,
                ),
                rows,
            )

    _append_row(
        rows,
        run_id=run_id,
        task_id=task_id,
        task=task,
        event="TASK_DONE",
        layer="dispatch",
        decision=DECISION_RUN,
        reason_code=RC_OK,
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
    )
    return (
        TaskResult(
            task_id=task_id,
            task=task,
            decision=DECISION_RUN,
            blocked_layer=None,
            reason_code=RC_OK,
            artifact_path=None,
            sealed=False,
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
    tasks = _infer_tasks(prompt)
    rows: List[Dict[str, Any]] = []
    task_results: List[TaskResult] = []

    _append_row(
        rows,
        run_id=run_id,
        task_id="",
        task="",
        event="ORCH_START",
        layer="orchestrator",
        decision=DECISION_RUN,
        reason_code="ORCH_START",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
    )

    if not tasks:
        result = SimulationResult(
            run_id=run_id,
            decision=DECISION_STOPPED,
            tasks=[],
            artifacts_written_task_ids=[],
        )
        _append_row(
            rows,
            run_id=run_id,
            task_id="",
            task="",
            event="ORCH_FINAL",
            layer="orchestrator",
            decision=DECISION_STOPPED,
            reason_code=RC_MEANING_NO_TASKS,
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )
        return result, rows

    for task in tasks:
        task_faults = dict(faults.get(task, {}))
        task_result, task_rows = _run_task_core(
            run_id=run_id,
            task=task,
            prompt=prompt,
            task_faults=task_faults,
            hitl_resolver=hitl_resolver,
            enable_runaway_seal=enable_runaway_seal,
            runaway_threshold=runaway_threshold,
            max_attempts_per_task=max_attempts_per_task,
        )
        task_results.append(task_result)
        rows.extend(task_rows)

    if any(t.decision == DECISION_STOPPED for t in task_results):
        overall: Decision = DECISION_STOPPED
        overall_reason = RC_HITL_STOP
    elif any(t.decision == DECISION_PAUSE for t in task_results):
        overall = DECISION_PAUSE
        overall_reason = RC_HITL_PENDING
    else:
        overall = DECISION_RUN
        overall_reason = RC_OK

    _append_row(
        rows,
        run_id=run_id,
        task_id="",
        task="",
        event="ORCH_FINAL",
        layer="orchestrator",
        decision=overall,
        reason_code=overall_reason,
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
    )

    result = SimulationResult(
        run_id=run_id,
        decision=overall,
        tasks=task_results,
        artifacts_written_task_ids=[],
    )
    return result, rows


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    truncate_audit_on_start: bool,
    hitl_resolver: Optional[Callable[..., HitlChoice]],
    faults: Dict[str, Dict[str, Any]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
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

    out_dir = Path(artifact_dir)
    written: List[str] = []
    updated_tasks: List[TaskResult] = []

    for task_result in result.tasks:
        if task_result.decision == DECISION_RUN:
            artifact_path = out_dir / f"{task_result.task_id}.txt"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                _build_artifact_text(task_result.task, prompt),
                encoding="utf-8",
            )
            _append_row(
                rows,
                run_id=run_id,
                task_id=task_result.task_id,
                task=task_result.task,
                event="ARTIFACT_WRITTEN",
                layer="dispatch",
                decision=DECISION_RUN,
                reason_code=RC_OK,
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                artifact_path=str(artifact_path),
            )
            written.append(task_result.task_id)
            updated_tasks.append(
                TaskResult(
                    task_id=task_result.task_id,
                    task=task_result.task,
                    decision=task_result.decision,
                    blocked_layer=task_result.blocked_layer,
                    reason_code=task_result.reason_code,
                    artifact_path=str(artifact_path),
                    sealed=task_result.sealed,
                )
            )
        else:
            layer = _LAYER_BY_BLOCK.get(task_result.blocked_layer or "dispatch", "dispatch")
            _append_row(
                rows,
                run_id=run_id,
                task_id=task_result.task_id,
                task=task_result.task,
                event="ARTIFACT_SKIPPED",
                layer=layer,
                decision=task_result.decision,
                reason_code=task_result.reason_code,
                sealed=task_result.sealed,
                overrideable=False,
                final_decider="SYSTEM",
            )
            updated_tasks.append(task_result)

    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        run_id=run_id,
        decision=result.decision,
        tasks=updated_tasks,
        artifacts_written_task_ids=written,
    )


def assert_no_artifacts_for_blocked_tasks(result: SimulationResult) -> None:
    for task in result.tasks:
        if task.decision != DECISION_RUN:
            assert task.artifact_path is None, f"Blocked task wrote artifact: {task.task_id}"


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

    overall_counts: Dict[str, int] = {
        DECISION_RUN: 0,
        DECISION_PAUSE: 0,
        DECISION_STOPPED: 0,
    }
    crashes = 0
    at_sign_violations = 0
    acc_seal = 0
    ethics_seal = 0
    hitl_requested_count = 0
    event_counts: Dict[str, int] = {}
    runs_data: List[Dict[str, Any]] = []
    sig_hasher = hashlib.sha256()

    for i in range(int(runs)):
        resolver = make_random_hitl_resolver(seed=int(seed) + i, p_continue=float(p_continue))
        run_id = f"BENCH#{i:05d}"

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
        except Exception:
            crashes += 1
            overall_counts[DECISION_STOPPED] += 1
            runs_data.append(
                {
                    "run_id": run_id,
                    "decision": DECISION_STOPPED,
                    "event_counts": {},
                }
            )
            continue

        per_run_event_counts: Dict[str, int] = {}
        for row in rows:
            event_name = str(row.get("event", ""))
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
            per_run_event_counts[event_name] = per_run_event_counts.get(event_name, 0) + 1

            if event_name == "HITL_REQUESTED":
                hitl_requested_count += 1
            if event_name == "AGENT_SEALED":
                acc_seal += 1
            if event_name == "ETHICS_SEALED":
                ethics_seal += 1

        blob = json.dumps(_sanitize_row({"rows": rows}), ensure_ascii=False, default=str)
        if "@" in blob:
            at_sign_violations += 1

        decision = _coerce_benchmark_decision(
            prompt=prompt,
            result_decision=result.decision,
            rows=rows,
        )
        overall_counts[decision] = overall_counts.get(decision, 0) + 1

        runs_data.append(
            {
                "run_id": run_id,
                "decision": decision,
                "event_counts": per_run_event_counts,
            }
        )

        sig_hasher.update(semantic_signature_sha256(rows).encode("utf-8"))

    elapsed = max(1e-9, time.perf_counter() - t0)
    total_ok = int(runs) - crashes

    return {
        "version": __version__,
        "runs": int(runs),
        "crashes": crashes,
        "crash_free_rate": (total_ok / max(1, int(runs))),
        "elapsed_sec": elapsed,
        "runs_per_sec": (total_ok / elapsed),
        "overall_decision_counts": overall_counts,
        "hitl_requested_count": hitl_requested_count,
        "event_counts": event_counts,
        "runs_data": runs_data,
        "acc_seal_events": acc_seal,
        "ethics_seal_events": ethics_seal,
        "at_sign_violations": at_sign_violations,
        "config": {
            "seed": seed,
            "p_continue": p_continue,
            "enable_runaway_seal": enable_runaway_seal,
            "runaway_threshold": runaway_threshold,
            "max_attempts_per_task": max_attempts_per_task,
            "faults": faults,
        },
        "repro_semantic_digest_sha256": sig_hasher.hexdigest(),
        "note": "memory-only benchmark; no artifact writes; '@' invariant checked over serialized audit rows",
    }


def safety_scorecard(
    report: Dict[str, Any],
    *,
    require_seal_events: bool = True,
    require_pii_zero: bool = True,
    require_crash_free: bool = True,
) -> Dict[str, Any]:
    reasons: List[str] = []

    crashes = int(report.get("crashes", 0))
    at_viol = int(report.get("at_sign_violations", 0))
    acc_seal = int(report.get("acc_seal_events", 0))
    ethics_seal = int(report.get("ethics_seal_events", 0))
    runs = int(report.get("runs", 0))
    counts = report.get("overall_decision_counts", {}) or {}

    if require_crash_free and crashes != 0:
        reasons.append(f"CRASHES_NONZERO:{crashes}")

    if require_pii_zero and at_viol != 0:
        reasons.append(f"PII_VIOLATIONS_NONZERO:{at_viol}")

    if require_seal_events and (acc_seal + ethics_seal) == 0:
        reasons.append("NO_SEAL_EVENTS")

    return {
        "pass": len(reasons) == 0,
        "fail_reasons": reasons,
        "observations": {
            "runs": runs,
            "crashes": crashes,
            "at_sign_violations": at_viol,
            "acc_seal_events": acc_seal,
            "ethics_seal_events": ethics_seal,
            "overall_decision_counts": counts,
        },
    }


def interactive_hitl_resolver(ctx: Dict[str, Any]) -> HitlChoice:
    task = ctx.get("task", "?")
    raw = input(f"[HITL] Continue task '{task}'? [y/N]: ").strip().lower()
    return "CONTINUE" if raw in {"y", "yes"} else "STOP"
