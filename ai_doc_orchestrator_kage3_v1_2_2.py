# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_2_2.py  (file name kept for test-compat)

Doc Orchestrator Simulator (KAGE3-style gates, test-friendly, fail-closed)

Pipeline (conceptual):
  Agent (excel/word/ppt) -> Orchestrator gates:
    Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Compatibility notes:
- Decision vocabulary is kept as: RUN / HITL / STOP  (tests expect "HITL")
- Overall decision is: RUN or HITL (STOP is treated as HITL at the overall level)
- "@" invariant: audit rows are sanitized so no email-like tokens are persisted
  (values AND dict keys are sanitized)

Python: 3.9+
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple, Union

__version__ = "1.2.4"  # logical version (file name stays v1_2_2 for CI/tests)

Decision = Literal["RUN", "HITL", "STOP"]
OverallDecision = Literal["RUN", "HITL"]

# -------------------------
# Redaction / Sanitization
# -------------------------

# Conservative email-ish patterns (we only need to ensure "@" never hits disk).
EMAIL_LIKE_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+", re.IGNORECASE)

# Any standalone "@" should be treated as sensitive in this project (hard invariant).
AT_SIGN_RE = re.compile(r"@")

REDACTED = "[REDACTED]"


def _sanitize_text(s: str) -> str:
    # Redact email-like tokens and any remaining '@'
    s2 = EMAIL_LIKE_RE.sub(REDACTED, s)
    s2 = AT_SIGN_RE.sub("[AT]", s2)
    return s2


def _sanitize_key(k: Any) -> Any:
    # Keys must not leak '@' either.
    if isinstance(k, str):
        return _sanitize_text(k)
    return k


def deep_sanitize(obj: Any) -> Any:
    """
    Deep sanitize:
    - strings: redact emails and '@'
    - dict keys: also sanitized
    - lists/tuples: sanitized recursively
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return _sanitize_text(obj)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, dict):
        out: Dict[Any, Any] = {}
        for k, v in obj.items():
            out[_sanitize_key(k)] = deep_sanitize(v)
        return out
    if isinstance(obj, list):
        return [deep_sanitize(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(deep_sanitize(x) for x in obj)
    # fallback (must be JSON safe in audit)
    return _sanitize_text(str(obj))


# -------------------------
# Audit Log
# -------------------------

@dataclass
class AuditLog:
    """
    In-memory first; optional file output.
    """
    path: Optional[Path] = None
    rows: List[Dict[str, Any]] = field(default_factory=list)
    _last_ts: float = field(default=0.0, init=False)

    def start_run(self, truncate: bool = True) -> None:
        if truncate:
            self.rows.clear()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if truncate:
                self.path.write_text("", encoding="utf-8")
        self._last_ts = 0.0

    def _monotonic_ts(self) -> float:
        now = time.time()
        if now <= self._last_ts:
            now = self._last_ts + 1e-6
        self._last_ts = now
        return now

    def emit(self, event: Dict[str, Any]) -> None:
        # Always sanitize before storing/writing.
        ev = deep_sanitize(event)
        if "ts" not in ev:
            ev["ts"] = self._monotonic_ts()

        self.rows.append(ev)

        if self.path:
            # Never crash audit: default=str
            line = json.dumps(ev, ensure_ascii=False, default=str)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


# -------------------------
# Data Models
# -------------------------

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    kind: Literal["excel", "word", "ppt"]
    prompt: str
    agent_output: str


@dataclass
class TaskResult:
    task_id: str
    kind: str
    decision: Decision
    reason_code: str
    artifact_preview: Optional[Dict[str, Any]] = None


@dataclass
class SimulationResult:
    overall_decision: OverallDecision
    task_results: List[TaskResult]
    audit_rows: List[Dict[str, Any]]

    # convenience (tests sometimes look for these)
    @property
    def decisions(self) -> List[Decision]:
        return [t.decision for t in self.task_results]


# -------------------------
# Defaults (used only if caller doesn't pass tasks)
# -------------------------

_DEFAULT_TASKS: List[TaskSpec] = [
    TaskSpec(
        task_id="t_excel",
        kind="excel",
        prompt="Summarize quarterly sales into a table and compute totals.",
        agent_output="Create a table with Q1..Q4 and a Total column.",
    ),
    TaskSpec(
        task_id="t_word",
        kind="word",
        prompt="Draft a short memo with one actionable recommendation.",
        agent_output="Maybe propose a change; consider multiple options.",
    ),
    TaskSpec(
        task_id="t_ppt",
        kind="ppt",
        prompt="Create 3 slides: title, key points, next steps.",
        agent_output="3-slide outline with bullets.",
    ),
]


# -------------------------
# Gate helpers
# -------------------------

def _arl_keys(sealed: bool, overrideable: bool, final_decider: str) -> Dict[str, Any]:
    # Minimal ARL keys (your broader framework uses these)
    return {
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
    }


def meaning_gate(task: TaskSpec) -> Tuple[Decision, str]:
    """
    Meaning gate (lightweight deterministic rules):
    - If the agent output includes strong ambiguity tokens -> HITL
    """
    text = (task.agent_output or "").lower()

    # "maybe" and "consider" are treated as ambiguity for this simulator
    if "maybe" in text or "consider" in text:
        return "HITL", "MEANING_AMBIGUOUS"
    return "RUN", "OK"


def consistency_gate(tasks: Sequence[TaskSpec], task: TaskSpec) -> Tuple[Decision, str]:
    """
    Consistency gate:
    - If agent output contradicts a simple project rule: ppt must mention "slides" or "slide"
    - If excel must mention "table"
    """
    out = (task.agent_output or "").lower()

    if task.kind == "ppt":
        if "slide" not in out:
            return "HITL", "CONSISTENCY_MISMATCH"
    if task.kind == "excel":
        if "table" not in out:
            return "HITL", "CONSISTENCY_MISMATCH"
    return "RUN", "OK"


def rfl_gate(task: TaskSpec) -> Tuple[Decision, str]:
    """
    RFL gate:
    - Relative/subjective boundary unstable -> HITL (never seal)
    """
    out = (task.agent_output or "").lower()
    # If "options" or "depends" appears, treat as relativity boundary
    if "depends" in out or "options" in out:
        return "HITL", "REL_BOUNDARY_UNSTABLE"
    return "RUN", "OK"


def ethics_gate(task: TaskSpec) -> Tuple[Decision, str]:
    """
    Ethics gate (minimal):
    - If task includes explicitly unsafe content, STOP
    (Keep very conservative; this repo is not about enabling harm.)
    """
    combined = f"{task.prompt}\n{task.agent_output}".lower()
    # Example markers; you can extend later
    unsafe_markers = ["kill", "bomb", "explosive", "weapon"]
    if any(m in combined for m in unsafe_markers):
        return "STOP", "SEALED_BY_ETHICS"
    return "RUN", "OK"


def acc_gate(task: TaskSpec) -> Tuple[Decision, str]:
    """
    Accuracy/Compliance gate (placeholder):
    - In this simulator we do not seal; we could STOP on hard invariant breaks.
    """
    # If somehow an '@' leaks into the raw content, STOP to preserve invariant
    raw = f"{task.prompt}\n{task.agent_output}"
    if "@" in raw:
        return "STOP", "SEALED_BY_ACC"
    return "RUN", "OK"


def build_artifact_preview(task: TaskSpec) -> Dict[str, Any]:
    """
    Artifact preview only (no real files generated in this simulator).
    Must be JSON-serializable.
    """
    if task.kind == "excel":
        return {
            "type": "spreadsheet",
            "sheets": [{"name": "Summary", "columns": ["Q1", "Q2", "Q3", "Q4", "Total"]}],
        }
    if task.kind == "word":
        return {"type": "document", "sections": ["Title", "Body", "Recommendation"]}
    if task.kind == "ppt":
        return {"type": "slides", "slides": ["Title", "Key Points", "Next Steps"]}
    return {"type": "unknown"}


def overall_from_task_decisions(task_results: Sequence[TaskResult]) -> OverallDecision:
    # Tests expect HITL if any task is HITL or STOP.
    for tr in task_results:
        if tr.decision != "RUN":
            return "HITL"
    return "RUN"


# -------------------------
# Simulation (memory-first)
# -------------------------

def run_simulation_mem(
    tasks: Optional[Sequence[TaskSpec]] = None,
    *,
    audit: Optional[AuditLog] = None,
    run_id: str = "run_001",
) -> SimulationResult:
    """
    Core simulation: returns results in-memory.

    Decisions:
      - RUN: artifact preview generated
      - HITL: task skipped (no artifact)
      - STOP: task stopped (no artifact)
    """
    if tasks is None:
        tasks = list(_DEFAULT_TASKS)
    else:
        tasks = list(tasks)

    if audit is None:
        audit = AuditLog(path=None)
    audit.start_run(truncate=True)

    task_results: List[TaskResult] = []

    # run start
    audit.emit(
        {
            "run_id": run_id,
            "layer": "run_start",
            "decision": "RUN",
            "reason_code": "TASK_START",
            **_arl_keys(sealed=False, overrideable=False, final_decider="SYSTEM"),
        }
    )

    for t in tasks:
        # ---- Meaning gate
        d, rc = meaning_gate(t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "meaning_gate",
                "decision": d,
                "reason_code": rc,
                **_arl_keys(sealed=False, overrideable=(d == "HITL"), final_decider="SYSTEM"),
            }
        )
        if d != "RUN":
            task_results.append(TaskResult(t.task_id, t.kind, d, rc, artifact_preview=None))
            continue

        # ---- Consistency gate
        d, rc = consistency_gate(tasks, t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "consistency_gate",
                "decision": d,
                "reason_code": rc,
                **_arl_keys(sealed=False, overrideable=(d == "HITL"), final_decider="SYSTEM"),
            }
        )
        if d != "RUN":
            task_results.append(TaskResult(t.task_id, t.kind, d, rc, artifact_preview=None))
            continue

        # ---- RFL gate (never seals)
        d, rc = rfl_gate(t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "relativity_gate",
                "decision": d,
                "reason_code": rc,
                **_arl_keys(sealed=False, overrideable=(d == "HITL"), final_decider="SYSTEM"),
            }
        )
        if d != "RUN":
            task_results.append(TaskResult(t.task_id, t.kind, d, rc, artifact_preview=None))
            continue

        # ---- Ethics gate (can seal -> STOP)
        d, rc = ethics_gate(t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "ethics_gate",
                "decision": d,
                "reason_code": rc,
                **_arl_keys(sealed=(d == "STOP"), overrideable=False, final_decider="SYSTEM"),
            }
        )
        if d != "RUN":
            task_results.append(TaskResult(t.task_id, t.kind, d, rc, artifact_preview=None))
            continue

        # ---- ACC gate (can seal -> STOP)
        d, rc = acc_gate(t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "acc_gate",
                "decision": d,
                "reason_code": rc,
                **_arl_keys(sealed=(d == "STOP"), overrideable=False, final_decider="SYSTEM"),
            }
        )
        if d != "RUN":
            task_results.append(TaskResult(t.task_id, t.kind, d, rc, artifact_preview=None))
            continue

        # ---- Dispatch
        preview = build_artifact_preview(t)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": t.task_id,
                "layer": "dispatch",
                "decision": "RUN",
                "reason_code": "DISPATCHED",
                "artifact_preview": preview,
                **_arl_keys(sealed=False, overrideable=False, final_decider="SYSTEM"),
            }
        )

        task_results.append(TaskResult(t.task_id, t.kind, "RUN", "OK", artifact_preview=preview))

    overall = overall_from_task_decisions(task_results)

    audit.emit(
        {
            "run_id": run_id,
            "layer": "run_end",
            "decision": overall,
            "reason_code": "TASK_END",
            **_arl_keys(sealed=False, overrideable=False, final_decider="SYSTEM"),
        }
    )

    return SimulationResult(overall_decision=overall, task_results=task_results, audit_rows=list(audit.rows))


# File-mode wrapper (some code/tests may import this)
def run_simulation(
    tasks: Optional[Sequence[TaskSpec]] = None,
    *,
    audit_path: Union[str, Path, None] = None,
    run_id: str = "run_001",
) -> SimulationResult:
    """
    Wrapper that also writes audit JSONL when audit_path is provided.
    """
    audit = AuditLog(path=Path(audit_path) if audit_path is not None else None)
    return run_simulation_mem(tasks, audit=audit, run_id=run_id)


# -------------------------
# Backward-compat aliases (defensive)
# -------------------------

# Some older modules/tests may look for these names:
SimulationOutcome = SimulationResult  # alias
TaskOutcome = TaskResult  # alias

def redact_sensitive(obj: Any) -> Any:
    # legacy name
    return deep_sanitize(obj)
