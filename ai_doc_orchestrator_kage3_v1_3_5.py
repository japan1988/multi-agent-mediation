# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Self-contained compatibility implementation.

Goals:
- Standalone file (no dependency on ai_doc_orchestrator_kage3_v1_2_4)
- IEP-aligned decision vocabulary:
    RUN / PAUSE_FOR_HITL / STOPPED
- Audit log:
    * start_run(truncate=...)
    * monotonic ts
    * defensive JSON serialization
    * deep redaction over keys/values
    * ARL minimal keys always present
- Fixed order:
    Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch
- HITL firepoint:
    HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER)
- Benchmark helpers required by tests/test_benchmark_profiles_v1_0.py:
    * make_random_hitl_resolver
    * run_simulation_mem
    * run_benchmark_suite
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

__version__ = "1.3.5"

JST = timezone(timedelta(hours=9))

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED", "HITL"]
OverallPolicy = Literal["legacy", "iep"]
FinalDecider = Literal["SYSTEM", "USER"]

Layer = Literal[
    "meaning",
    "consistency",
    "rfl",
    "ethics",
    "acc",
    "orchestrator",
    "agent",
    "hitl_finalize",
]

KIND = Literal["excel", "word", "ppt"]

HitlChoice = Literal["CONTINUE", "STOP"]
HitlResolver = Callable[[str, str, str, str], HitlChoice]


# ---------------------------------
# Data models
# ---------------------------------
@dataclass
class TaskResult:
    task_id: str
    kind: KIND
    decision: Decision
    blocked_layer: Optional[str]
    reason_code: str
    artifact_path: Optional[str]


@dataclass
class SimulationResult:
    run_id: str
    decision: OverallDecision
    tasks: List[TaskResult]
    artifacts_written_task_ids: List[str]


# ---------------------------------
# Redaction
# ---------------------------------
def redact_sensitive(text: str) -> str:
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def _deep_redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_sensitive(obj)

    if isinstance(obj, list):
        return [_deep_redact(x) for x in obj]

    if isinstance(obj, tuple):
        return [_deep_redact(x) for x in obj]

    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        seen: Dict[str, int] = {}
        for k, v in obj.items():
            base = redact_sensitive(str(k))
            n = seen.get(base, 0) + 1
            seen[base] = n
            key = base if n == 1 else f"{base}__DUP{n}"
            out[key] = _deep_redact(v)
        return out

    return obj


# ---------------------------------
# Audit log
# ---------------------------------
class AuditLog:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._last_ts: Optional[datetime] = None

    def start_run(self, truncate: bool = False) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            self.path.write_text("", encoding="utf-8")
        self._last_ts = None

    def _next_ts(self) -> str:
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(microseconds=1)
        self._last_ts = now
        return now.isoformat()

    def emit(self, row: Dict[str, Any]) -> None:
        safe = dict(row)
        if "ts" not in safe:
            safe["ts"] = self._next_ts()

        safe = _deep_redact(safe)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="") as f:
            f.write(json.dumps(safe, ensure_ascii=False, default=str) + "\n")


# ---------------------------------
# Helpers
# ---------------------------------
def _arl_base(*, sealed: bool, overrideable: bool, final_decider: FinalDecider) -> Dict[str, Any]:
    return {
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
    }


def _normalize_decision(decision: str) -> str:
    d = (decision or "").strip().upper()
    if d in {"HITL", "PAUSE"}:
        return "PAUSE_FOR_HITL"
    if d == "STOP":
        return "STOPPED"
    if d in {"RUN", "PAUSE_FOR_HITL", "STOPPED"}:
        return d
    return d or "UNKNOWN"


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


def _rows_have_pii(rows: List[Dict[str, Any]]) -> bool:
    return "@" in json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)


def _extract_reason_code(res: SimulationResult) -> str:
    for task in res.tasks:
        if task.reason_code:
            return str(task.reason_code)
    return "UNKNOWN"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _has_hitl_requested(rows: List[Dict[str, Any]]) -> bool:
    return any(isinstance(r, dict) and r.get("event") == "HITL_REQUESTED" for r in rows)


def _is_ambiguous_prompt(prompt: str) -> bool:
    text = prompt or ""
    tokens = ("おすすめ", "どっち", "どちら", "比較", "選んで", "いい？", "良い？")
    return any(t in text for t in tokens)


def _coerce_benchmark_decision(*, prompt: str, result_decision: str, rows: List[Dict[str, Any]]) -> str:
    decision = _normalize_decision(result_decision)
    if decision == "PAUSE_FOR_HITL":
        return "PAUSE_FOR_HITL"
    if _is_ambiguous_prompt(prompt) and _has_hitl_requested(rows):
        return "STOPPED"
    return decision


def _write_artifact(out_dir: Path, task_id: str, kind: KIND, text: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = {"excel": ".txt", "word": ".txt", "ppt": ".txt"}[kind]
    path = out_dir / f"{task_id}_{kind}{ext}"
    path.write_text(text, encoding="utf-8")
    return path


def _emit_info(
    *,
    audit: AuditLog,
    run_id: str,
    task_id: str,
    event: str,
    layer: str,
    reason_code: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "event": event,
        "layer": layer,
        "decision": "RUN",
        "reason_code": reason_code,
        **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
    }
    if extra:
        row.update(extra)
    audit.emit(row)


# ---------------------------------
# Prompt / tasks / agent
# ---------------------------------
def _infer_tasks(prompt: str) -> List[KIND]:
    _ = prompt
    return ["excel", "word", "ppt"]


def _prompt_mentions_kind(prompt: str, kind: KIND) -> bool:
    p = (prompt or "").lower()

    if kind == "excel":
        tokens = ("excel", "表", "スプレッドシート", "進捗表")
    elif kind == "word":
        tokens = ("word", "文書", "要約", "ドキュメント")
    else:
        tokens = ("ppt", "powerpoint", "slide", "スライド", "発表資料")

    return any(tok.lower() in p for tok in tokens)


def _prompt_has_any_kind(prompt: str) -> bool:
    return (
        _prompt_mentions_kind(prompt, "excel")
        or _prompt_mentions_kind(prompt, "word")
        or _prompt_mentions_kind(prompt, "ppt")
    )


def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, str]:
    if not _prompt_has_any_kind(prompt):
        return "RUN", "MEANING_GENERIC_OK"
    if _prompt_mentions_kind(prompt, kind):
        return "RUN", "MEANING_KIND_MATCH"
    return "PAUSE_FOR_HITL", "MEANING_KIND_MISMATCH"


def _consistency_gate(task_faults: Dict[str, Any]) -> Tuple[Decision, str]:
    if bool(task_faults.get("break_contract")):
        return "PAUSE_FOR_HITL", "CONSISTENCY_CONTRACT_MISMATCH"
    return "RUN", "CONSISTENCY_OK"


def _rfl_gate(prompt: str) -> Tuple[Decision, str]:
    if _is_ambiguous_prompt(prompt):
        return "PAUSE_FOR_HITL", "REL_BOUNDARY_UNSTABLE"
    return "RUN", "RFL_OK"


def _ethics_detect_pii(text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


def _acc_gate(prompt: str) -> Tuple[Decision, bool, str]:
    _ = prompt
    return "RUN", False, "ACC_OK"


def _generate_raw_text(prompt: str, kind: KIND, task_faults: Dict[str, Any]) -> str:
    base_text = {
        "excel": "Excel形式の表を作成しました。",
        "word": "Word形式の要約文書を作成しました。",
        "ppt": "PPT形式のスライド構成を作成しました。",
    }[kind]

    if bool(task_faults.get("leak_email")):
        return base_text + " contact=test.user+demo@example.com"
    return base_text + f" prompt={prompt}"


def _hitl_fire_and_decide(
    *,
    audit: AuditLog,
    run_id: str,
    task_id: str,
    layer: str,
    reason_code: str,
    hitl_resolver: Optional[HitlResolver],
) -> HitlChoice:
    audit.emit(
        {
            "run_id": run_id,
            "task_id": task_id,
            "event": "HITL_REQUESTED",
            "layer": layer,
            "decision": "PAUSE_FOR_HITL",
            "reason_code": reason_code,
            **_arl_base(sealed=False, overrideable=True, final_decider="SYSTEM"),
        }
    )

    if hitl_resolver is None:
        choice: HitlChoice = "STOP"
    else:
        choice = hitl_resolver(run_id, task_id, layer, reason_code)

    audit.emit(
        {
            "run_id": run_id,
            "task_id": task_id,
            "event": "HITL_DECIDED",
            "layer": "hitl_finalize",
            "decision": "RUN" if choice == "CONTINUE" else "STOPPED",
            "reason_code": "HITL_CONTINUE" if choice == "CONTINUE" else "HITL_STOP",
            **_arl_base(sealed=False, overrideable=False, final_decider="USER"),
        }
    )
    return choice


# ---------------------------------
# Core simulation
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
    overall_policy: OverallPolicy = "iep",
) -> SimulationResult:
    audit = AuditLog(audit_path)
    audit.start_run(truncate=truncate_audit_on_start)

    out_dir = Path(artifact_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    tasks = _infer_tasks(prompt)
    if not tasks:
        return SimulationResult(
            run_id=run_id,
            decision="STOPPED" if overall_policy == "iep" else "HITL",
            tasks=[],
            artifacts_written_task_ids=[],
        )

    for kind in tasks:
        task_id = f"task_{kind}"
        task_faults = (faults or {}).get(kind, {})

        raw_text = _generate_raw_text(prompt, kind, task_faults)
        safe_text = redact_sensitive(raw_text)

        # Meaning
        m_dec, m_code = _meaning_gate(prompt, kind)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_MEANING",
                "layer": "meaning",
                "decision": m_dec,
                "reason_code": m_code,
                **_arl_base(
                    sealed=False,
                    overrideable=(m_dec == "PAUSE_FOR_HITL"),
                    final_decider="SYSTEM",
                ),
            }
        )

        if m_dec == "PAUSE_FOR_HITL":
            choice = _hitl_fire_and_decide(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                layer="meaning",
                reason_code=m_code,
                hitl_resolver=hitl_resolver,
            )
            if choice == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "STOPPED",
                        "reason_code": "HITL_STOP",
                        **_arl_base(sealed=False, overrideable=False, final_decider="USER"),
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="STOPPED",
                        blocked_layer="meaning",
                        reason_code="HITL_STOP",
                        artifact_path=None,
                    )
                )
                continue

        # Consistency
        c_dec, c_code = _consistency_gate(task_faults)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_CONSISTENCY",
                "layer": "consistency",
                "decision": c_dec,
                "reason_code": c_code,
                **_arl_base(
                    sealed=False,
                    overrideable=(c_dec == "PAUSE_FOR_HITL"),
                    final_decider="SYSTEM",
                ),
            }
        )

        if c_dec == "PAUSE_FOR_HITL":
            choice = _hitl_fire_and_decide(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                layer="consistency",
                reason_code=c_code,
                hitl_resolver=hitl_resolver,
            )
            if choice == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "STOPPED",
                        "reason_code": "HITL_STOP",
                        **_arl_base(sealed=False, overrideable=False, final_decider="USER"),
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="STOPPED",
                        blocked_layer="consistency",
                        reason_code="HITL_STOP",
                        artifact_path=None,
                    )
                )
                continue

            _emit_info(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                event="REGEN_REQUESTED",
                layer="orchestrator",
                reason_code="REGEN_FOR_CONSISTENCY",
            )
            _emit_info(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                event="REGEN_INSTRUCTIONS",
                layer="orchestrator",
                reason_code="REGEN_INSTRUCTIONS_V1",
                extra={"instructions": "Regenerate output to match the contract schema for this kind."},
            )
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": c_code,
                    **_arl_base(sealed=False, overrideable=True, final_decider="SYSTEM"),
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="PAUSE_FOR_HITL",
                    blocked_layer="consistency",
                    reason_code=c_code,
                    artifact_path=None,
                )
            )
            continue

        # RFL
        r_dec, r_code = _rfl_gate(prompt)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_RFL",
                "layer": "rfl",
                "decision": r_dec,
                "reason_code": r_code,
                **_arl_base(
                    sealed=False,
                    overrideable=(r_dec == "PAUSE_FOR_HITL"),
                    final_decider="SYSTEM",
                ),
            }
        )

        if r_dec == "PAUSE_FOR_HITL":
            choice = _hitl_fire_and_decide(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                layer="rfl",
                reason_code=r_code,
                hitl_resolver=hitl_resolver,
            )
            if choice == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "STOPPED",
                        "reason_code": "HITL_STOP",
                        **_arl_base(sealed=False, overrideable=False, final_decider="USER"),
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="STOPPED",
                        blocked_layer="rfl",
                        reason_code="HITL_STOP",
                        artifact_path=None,
                    )
                )
                continue

        # Ethics
        pii_hit, e_code = _ethics_detect_pii(raw_text)
        e_dec: Decision = "STOPPED" if pii_hit else "RUN"
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_ETHICS",
                "layer": "ethics",
                "decision": e_dec,
                "reason_code": e_code,
                **_arl_base(
                    sealed=pii_hit,
                    overrideable=False if pii_hit else False,
                    final_decider="SYSTEM",
                ),
            }
        )

        if pii_hit:
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "ethics",
                    "decision": "STOPPED",
                    "reason_code": e_code,
                    **_arl_base(sealed=True, overrideable=False, final_decider="SYSTEM"),
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="STOPPED",
                    blocked_layer="ethics",
                    reason_code=e_code,
                    artifact_path=None,
                )
            )
            continue

        # ACC
        a_dec, _, a_code = _acc_gate(prompt)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_ACC",
                "layer": "acc",
                "decision": a_dec,
                "reason_code": a_code,
                **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
            }
        )

        if a_dec != "RUN":
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": "ACC_BLOCKED",
                    **_arl_base(sealed=False, overrideable=True, final_decider="SYSTEM"),
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="PAUSE_FOR_HITL",
                    blocked_layer="acc",
                    reason_code="ACC_BLOCKED",
                    artifact_path=None,
                )
            )
            continue

        # Dispatch
        artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_WRITTEN",
                "layer": "orchestrator",
                "decision": "RUN",
                "reason_code": "ARTIFACT_WRITTEN",
                **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
                "artifact_path": str(artifact_path),
            }
        )
        artifacts_written.append(task_id)
        task_results.append(
            TaskResult(
                task_id=task_id,
                kind=kind,
                decision="RUN",
                blocked_layer=None,
                reason_code="OK",
                artifact_path=str(artifact_path),
            )
        )

    if overall_policy == "iep":
        if any(t.decision == "STOPPED" for t in task_results):
            overall: OverallDecision = "STOPPED"
        elif any(t.decision == "PAUSE_FOR_HITL" for t in task_results):
            overall = "PAUSE_FOR_HITL"
        else:
            overall = "RUN"
    else:
        overall = "RUN" if all(t.decision == "RUN" for t in task_results) else "HITL"

    return SimulationResult(
        run_id=run_id,
        decision=overall,
        tasks=task_results,
        artifacts_written_task_ids=artifacts_written,
    )


# ---------------------------------
# Optional interactive HITL
# ---------------------------------
def interactive_hitl_resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> HitlChoice:
    prompt = (
        f"[HITL] run_id={run_id} task_id={task_id} layer={layer} "
        f"reason={reason_code} -> (c=CONTINUE / s=STOP): "
    )
    for _ in range(5):
        ans = input(prompt).strip().lower()
        if ans in ("c", "continue"):
            return "CONTINUE"
        if ans in ("s", "stop"):
            return "STOP"
        print("Invalid input. Please enter 'c' or 's'.")
    return "STOP"


# ---------------------------------
# In-memory runner for benchmarks
# ---------------------------------
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

        coerced = _coerce_benchmark_decision(
            prompt=prompt,
            result_decision=res.decision,
            rows=rows,
        )

        if coerced != res.decision:
            res = SimulationResult(
                run_id=res.run_id,
                decision=coerced,  # type: ignore[arg-type]
                tasks=res.tasks,
                artifacts_written_task_ids=res.artifacts_written_task_ids,
            )

        return res, rows


# ---------------------------------
# Benchmark helpers
# ---------------------------------
def make_random_hitl_resolver(seed: int, p_continue: float) -> HitlResolver:
    prob = float(p_continue)
    if prob < 0.0:
        prob = 0.0
    if prob > 1.0:
        prob = 1.0

    rng = random.Random(int(seed))

    def resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> HitlChoice:
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
    total_runs = max(1, int(runs))
    max_attempts = max(1, int(max_attempts_per_task))
    threshold = max(1, int(runaway_threshold))
    rng = random.Random(int(seed))

    overall_decision_counts: Dict[str, int] = {
        "RUN": 0,
        "PAUSE_FOR_HITL": 0,
        "STOPPED": 0,
    }
    reason_counts: Dict[str, int] = {}

    crash_count = 0
    pii_leak_count = 0
    hitl_requested_count = 0
    seal_event_count = 0

    sample_rows: List[Dict[str, Any]] = []
    runs_data: List[Dict[str, Any]] = []

    for i in range(total_runs):
        resolver_seed = rng.randint(0, 10**9)
        resolver = make_random_hitl_resolver(seed=resolver_seed, p_continue=p_continue)

        final_decision: str = "STOPPED"
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
            except Exception as exc:
                crashed = True
                exception_type = type(exc).__name__
                final_decision = "STOPPED"
                final_reason = f"EXCEPTION:{exception_type}"
                final_rows = []
                break

            final_rows = rows
            final_decision = _normalize_decision(res.decision)
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

            final_decision = "STOPPED"
            break

        if final_decision not in overall_decision_counts:
            final_decision = "STOPPED"

        overall_decision_counts[final_decision] += 1
        reason_counts[final_reason] = reason_counts.get(final_reason, 0) + 1

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

    run_count = int(overall_decision_counts["RUN"])
    pause_count = int(overall_decision_counts["PAUSE_FOR_HITL"])
    stop_count = int(overall_decision_counts["STOPPED"])

    run_rate = run_count / total_runs
    pause_rate = pause_count / total_runs
    stop_rate = stop_count / total_runs
    crash_rate = crash_count / total_runs
    pii_leak_rate = pii_leak_count / total_runs
    hitl_requested_rate = hitl_requested_count / total_runs
    seal_event_rate = seal_event_count / total_runs

    return {
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
        "crashes": crash_count,
        "pii_leaks": pii_leak_count,
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
