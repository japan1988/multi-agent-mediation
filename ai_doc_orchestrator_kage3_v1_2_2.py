# ai_doc_orchestrator_kage3_v1_2_2.py  (v1.2.2)
# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_2_2.py

Doc Orchestrator Simulator (KAGE3-style gates):
- Meaning gate: kind-local HITL based on prompt tokens (generic prompt -> allow all kinds)
- Consistency gate: schema/contract validation; mismatch -> HITL + regen request events
- Ethics gate: detects PII (email) from *raw_text* but NEVER persists raw_text
- Partial stop: only violating task is STOP/HITL; other tasks continue
- Logging: JSONL audit log; PII is fully non-persisted (safe_text only)

Key invariants:
- raw_text may contain PII but must never be written to logs/artifacts.
- logs/artifacts must not contain email-like strings.

Version: v1.2.2
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

__version__ = "1.2.2"

JST = timezone(timedelta(hours=9))

# Canonical email regex (exported; tests rely on this)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "HITL", "STOP"]   # per-task decision
OverallDecision = Literal["RUN", "HITL"]    # overall decision for this simulator

# Keep layer vocabulary stable for tests/log consumers
Layer = Literal["meaning", "consistency", "ethics", "orchestrator", "agent"]
KIND = Literal["excel", "word", "ppt"]


# -----------------------------
# Redaction (PII must not persist)
# -----------------------------
def redact_sensitive(text: str) -> str:
    """Redact email-like strings from text."""
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def _deep_redact(obj: Any) -> Any:
    """Deep redaction over dict/list/str."""
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, list):
        return [_deep_redact(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _deep_redact(v) for k, v in obj.items()}
    return obj


def _ts() -> str:
    # ISO strings sort lexicographically if format is stable; tests optionally sort by ts
    return datetime.now(JST).isoformat(timespec="seconds")


# -----------------------------
# Audit logger (PII-safe JSONL)
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a JSONL row.
        Hard guarantee: no email-like strings are persisted.
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy safely (avoid mutating caller data), then redact defensively.
        safe_row = json.loads(json.dumps(row, ensure_ascii=False))
        safe_blob = json.dumps(safe_row, ensure_ascii=False)

        # If anything looks like an email, deep redact before writing.
        if EMAIL_RE.search(safe_blob):
            safe_row = _deep_redact(safe_row)

        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe_row, ensure_ascii=False) + "\n")


# -----------------------------
# Results
# -----------------------------
@dataclass
class TaskResult:
    task_id: str
    kind: KIND
    decision: Decision
    blocked_layer: Optional[Layer]
    reason_code: str = ""
    artifact_path: Optional[str] = None


@dataclass
class SimulationResult:
    run_id: str
    decision: OverallDecision
    tasks: List[TaskResult]
    artifacts_written_task_ids: List[str]


# -----------------------------
# Meaning gate (kind-local)
# -----------------------------
_KIND_TOKENS: Dict[KIND, List[str]] = {
    "excel": ["excel", "xlsx", "表", "列", "columns", "table"],
    "word": ["word", "docx", "見出し", "章", "アウトライン", "outline", "document"],
    "ppt":  ["ppt", "pptx", "powerpoint", "スライド", "slides", "slide"],
}


def _prompt_mentions_any_kind(prompt: str) -> bool:
    p = (prompt or "").lower()
    for toks in _KIND_TOKENS.values():
        for t in toks:
            if t.lower() in p:
                return True
    return False


def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[Layer], str]:
    """
    Meaning gate:
      - If prompt doesn't mention any kind tokens at all -> allow all kinds (RUN).
      - Else, allow only kinds whose tokens are present; missing kind -> HITL (meaning).
    """
    p = (prompt or "")
    pl = p.lower()

    any_kind = _prompt_mentions_any_kind(p)
    if not any_kind:
        return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"

    tokens = _KIND_TOKENS[kind]
    if any(t.lower() in pl for t in tokens):
        return "RUN", None, "MEANING_KIND_MATCH"
    return "HITL", "meaning", "MEANING_KIND_MISSING"


# -----------------------------
# Contract validation (Consistency)
# -----------------------------
def _validate_contract(kind: KIND, draft: Dict[str, Any]) -> Tuple[bool, str]:
    if kind == "excel":
        cols = draft.get("columns")
        rows = draft.get("rows")
        if not (isinstance(cols, list) and all(isinstance(x, str) for x in cols)):
            return False, "CONTRACT_EXCEL_COLUMNS_INVALID"
        if not (isinstance(rows, list) and all(isinstance(x, dict) for x in rows)):
            return False, "CONTRACT_EXCEL_ROWS_INVALID"
        return True, "CONTRACT_OK"

    if kind == "word":
        heads = draft.get("headings")
        if not (isinstance(heads, list) and all(isinstance(x, str) for x in heads)):
            return False, "CONTRACT_WORD_HEADINGS_INVALID"
        return True, "CONTRACT_OK"

    if kind == "ppt":
        slides = draft.get("slides")
        if not (isinstance(slides, list) and all(isinstance(x, str) for x in slides)):
            return False, "CONTRACT_PPT_SLIDES_INVALID"
        return True, "CONTRACT_OK"

    return False, "CONTRACT_UNKNOWN_KIND"


# -----------------------------
# Ethics detection (memory-only raw_text)
# -----------------------------
def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    """Return (hit, reason_code). raw_text is memory-only."""
    if EMAIL_RE.search(raw_text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


# -----------------------------
# Agent generation (raw vs safe; raw never persisted)
# -----------------------------
def _agent_generate(prompt: str, kind: KIND, faults: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    """
    Returns (draft_struct, raw_text, safe_text).
    - raw_text: may contain PII (memory only; never persisted)
    - safe_text: redacted; safe to persist into logs/artifacts
    """
    leak_email = bool((faults or {}).get("leak_email"))
    break_contract = bool((faults or {}).get("break_contract"))

    if kind == "excel":
        draft: Dict[str, Any] = {
            "columns": ["Item", "Owner", "Status"],
            "rows": [
                {"Item": "Task A", "Owner": "Team", "Status": "In Progress"},
                {"Item": "Task B", "Owner": "Team", "Status": "Planned"},
            ],
        }
        raw_text = "Excel Table:\n- Columns: Item | Owner | Status\n- Rows: 2\n"
    elif kind == "word":
        draft = {"headings": ["Title", "Purpose", "Summary", "Next Steps"]}
        raw_text = "Word Outline:\n1) Title\n2) Purpose\n3) Summary\n4) Next Steps\n"
    elif kind == "ppt":
        draft = {"slides": ["Purpose", "Key Points", "Next Steps"]}
        raw_text = "PPT Slides:\n- Slide 1: Purpose\n- Slide 2: Key Points\n- Slide 3: Next Steps\n"
    else:
        draft = {"note": "unknown kind"}
        raw_text = "Unknown kind\n"

    # Fault: break contract (schema mismatch)
    if break_contract:
        if kind == "excel":
            draft = {"cols": "Item,Owner,Status"}  # wrong keys/types
        elif kind == "word":
            draft = {"heading": "Title"}  # wrong key
        elif kind == "ppt":
            draft = {"slides": "Purpose,Key Points"}  # wrong type

    # Fault: leak email into output text (ethics should STOP)
    if leak_email:
        # Note: raw_text must never be persisted; ethics checks raw_text only.
        raw_text += "\nContact: test.user+demo@example.com\n"

    safe_text = redact_sensitive(raw_text)
    return draft, raw_text, safe_text


# -----------------------------
# Artifact writer (safe_text only)
# -----------------------------
def _artifact_ext(kind: KIND) -> str:
    if kind == "excel":
        return "xlsx"
    if kind == "word":
        return "docx"
    if kind == "ppt":
        return "pptx"
    return "txt"


def _write_artifact(artifact_dir: Path, task_id: str, kind: KIND, safe_text: str) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # Simulator uses plain text artifacts for simplicity; tests handle .txt
    path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
    path.write_text(redact_sensitive(safe_text), encoding="utf-8")
    return path


# -----------------------------
# Orchestrator main
# -----------------------------
_TASKS: List[Tuple[str, KIND]] = [
    ("task_word", "word"),
    ("task_excel", "excel"),
    ("task_ppt", "ppt"),
]


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
) -> SimulationResult:
    """
    Run the simulator with a fixed task set (word/excel/ppt).
    Overall decision rule:
      - RUN iff all tasks are RUN
      - HITL otherwise (including STOP/HITL on any task)
    """
    faults = faults or {}
    audit = AuditLog(Path(audit_path))
    out_dir = Path(artifact_dir)

    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task_id, kind in _TASKS:
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "TASK_ASSIGNED",
            "layer": "orchestrator",
            "kind": kind,
        })

        m_dec, m_layer, m_code = _meaning_gate(prompt, kind)
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "GATE_MEANING",
            "layer": "meaning",
            "decision": m_dec,
            "reason_code": m_code,
        })

        if m_dec == "HITL":
            audit.emit({
                "ts": _ts(),
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_SKIPPED",
                "layer": "orchestrator",
                "decision": "HITL",
                "reason_code": m_code,
            })
            task_results.append(TaskResult(
                task_id=task_id,
                kind=kind,
                decision="HITL",
                blocked_layer="meaning",
                reason_code=m_code,
                artifact_path=None,
            ))
            continue

        draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))

        # IMPORTANT: never persist raw_text; log only safe_text preview
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "AGENT_OUTPUT",
            "layer": "agent",
            "preview": safe_text[:200],
        })

        ok, c_code = _validate_contract(kind, draft)
        c_dec: Decision = "RUN" if ok else "HITL"
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "GATE_CONSISTENCY",
            "layer": "consistency",
            "decision": c_dec,
            "reason_code": c_code,
        })

        if not ok:
            audit.emit({
                "ts": _ts(),
                "run_id": run_id,
                "task_id": task_id,
                "event": "REGEN_REQUESTED",
                "layer": "orchestrator",
                "decision": "HITL",
                "reason_code": "REGEN_FOR_CONSISTENCY",
            })
            audit.emit({
                "ts": _ts(),
                "run_id": run_id,
                "task_id": task_id,
                "event": "REGEN_INSTRUCTIONS",
                "layer": "orchestrator",
                "decision": "HITL",
                "reason_code": "REGEN_INSTRUCTIONS_V1",
                "instructions": "Regenerate output to match the contract schema for this kind.",
            })
            audit.emit({
                "ts": _ts(),
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_SKIPPED",
                "layer": "orchestrator",
                "decision": "HITL",
                "reason_code": c_code,
            })
            task_results.append(TaskResult(
                task_id=task_id,
                kind=kind,
                decision="HITL",
                blocked_layer="consistency",
                reason_code=c_code,
                artifact_path=None,
            ))
            continue

        # Ethics uses raw_text ONLY in memory
        pii_hit, e_code = _ethics_detect_pii(raw_text)
        e_dec: Decision = "STOP" if pii_hit else "RUN"
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "GATE_ETHICS",
            "layer": "ethics",
            "decision": e_dec,
            "reason_code": e_code,
        })

        if pii_hit:
            audit.emit({
                "ts": _ts(),
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_SKIPPED",
                "layer": "ethics",
                "reason_code": e_code,
            })
            task_results.append(TaskResult(
                task_id=task_id,
                kind=kind,
                decision="STOP",
                blocked_layer="ethics",
                reason_code=e_code,
                artifact_path=None,
            ))
            continue

        artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
        audit.emit({
            "ts": _ts(),
            "run_id": run_id,
            "task_id": task_id,
            "event": "ARTIFACT_WRITTEN",
            "layer": "orchestrator",
            "decision": "RUN",
            "artifact_path": str(artifact_path),
        })

        artifacts_written.append(task_id)
        task_results.append(TaskResult(
            task_id=task_id,
            kind=kind,
            decision="RUN",
            blocked_layer=None,
            reason_code="OK",
            artifact_path=str(artifact_path),
        ))

    overall: OverallDecision = "RUN" if all(t.decision == "RUN" for t in task_results) else "HITL"
    return SimulationResult(
        run_id=run_id,
        decision=overall,
        tasks=task_results,
        artifacts_written_task_ids=artifacts_written,
    )


__all__ = [
    "EMAIL_RE",
    "run_simulation",
    "AuditLog",
    "SimulationResult",
    "TaskResult",
    "redact_sensitive",
]
