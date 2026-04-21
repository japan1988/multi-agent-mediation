# ai_doc_orchestrator_kage3_v1_2_4.py
# -*- coding: utf-8 -*-
"""
Design-oriented orchestrator v1.2.4

Targets:
- AuditLog.start_run(truncate=...) with per-run monotonic ts
- Defensive JSON serialization via default=str
- Deep redaction for both dict keys and values
- emit() auto-fills ts and never raises
- Decision vocabulary fixed to: RUN / PAUSE_FOR_HITL / STOPPED
- HITL traces are explicit: HITL_REQUESTED / HITL_DECIDED
- Ethics sealing uses sealed=True, overrideable=False, final_decider=SYSTEM
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

__version__ = "1.2.4"

JST = timezone(timedelta(hours=9))

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
Layer = Literal["meaning", "consistency", "rfl", "ethics", "orchestrator", "agent"]
KIND = Literal["excel", "word", "ppt"]
HitlChoice = Literal["CONTINUE", "STOP"]
HitlResolver = Callable[[str, str, str, str], HitlChoice]

_AUDIT_MAX_LINE_BYTES = 8192


# -----------------------------
# Redaction
# -----------------------------
def redact_sensitive(text: str) -> str:
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def _deep_redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, list):
        return [_deep_redact(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        seen_counts: Dict[str, int] = {}
        for k, v in obj.items():
            base = redact_sensitive(str(k))
            if base not in out:
                out[base] = _deep_redact(v)
                continue

            n = seen_counts.get(base, 1) + 1
            seen_counts[base] = n
            new_key = f"{base}__DUP{n}"
            while new_key in out:
                n += 1
                seen_counts[base] = n
                new_key = f"{base}__DUP{n}"
            out[new_key] = _deep_redact(v)
        return out
    return obj


# -----------------------------
# Audit logger
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, *, truncate: bool = False) -> None:
        self._last_ts = None
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            if truncate:
                self.audit_path.write_text("", encoding="utf-8")
        except OSError:
            return

    def ts(self) -> str:
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(microseconds=1)
        self._last_ts = now
        return now.isoformat(timespec="microseconds")

    def emit(self, row: Any) -> None:
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        def _truncate_utf8(s: str, max_bytes: int) -> str:
            b = s.encode("utf-8", errors="replace")
            if len(b) <= max_bytes:
                return s
            suffix = b"...<TRUNCATED>"
            cut = b[: max(0, max_bytes - len(suffix))]
            return cut.decode("utf-8", errors="ignore") + "...<TRUNCATED>"

        def _safe_write_line(line: str) -> None:
            try:
                with self.audit_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except OSError:
                return

        try:
            payload: Any = row
            if not isinstance(payload, dict):
                payload = {
                    "event": "AUDIT_NON_DICT_ROW",
                    "value": payload,
                    "decision": "RUN",
                    "reason_code": "AUDIT_NON_DICT_ROW",
                    "sealed": False,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
                    "layer": "orchestrator",
                }

            if "ts" not in payload:
                payload = dict(payload)
                payload["ts"] = self.ts()

            safe_row: Dict[str, Any] = json.loads(
                json.dumps(payload, ensure_ascii=False, default=str)
            )
            safe_row = _deep_redact(safe_row)

            line = json.dumps(safe_row, ensure_ascii=False)
            if len(line.encode("utf-8", errors="replace")) > _AUDIT_MAX_LINE_BYTES:
                minimal = {
                    "ts": safe_row.get("ts", self.ts()),
                    "run_id": safe_row.get("run_id", ""),
                    "task_id": safe_row.get("task_id", ""),
                    "layer": safe_row.get("layer", ""),
                    "event": "AUDIT_LINE_TRUNCATED",
                    "orig_event": safe_row.get("event", ""),
                    "decision": safe_row.get("decision", "RUN"),
                    "reason_code": "AUDIT_LINE_TRUNCATED",
                    "sealed": False,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
                    "max_bytes": _AUDIT_MAX_LINE_BYTES,
                    "truncated": True,
                }
                minimal = _deep_redact(minimal)
                line = json.dumps(minimal, ensure_ascii=False)
                line = _truncate_utf8(line, _AUDIT_MAX_LINE_BYTES)

            _safe_write_line(line)

        except Exception as e:
            fallback = {
                "ts": self.ts(),
                "event": "AUDIT_EMIT_ERROR",
                "layer": "orchestrator",
                "decision": "STOPPED",
                "reason_code": "AUDIT_EMIT_ERROR",
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
                "error_type": type(e).__name__,
                "error": redact_sensitive(str(e)),
            }
            try:
                rr = redact_sensitive(repr(row))
                fallback["row_repr"] = rr[:1024]
            except Exception:
                fallback["row_repr"] = "<UNREPRESENTABLE>"
            fallback = _deep_redact(fallback)
            line = json.dumps(fallback, ensure_ascii=False)
            if len(line.encode("utf-8", errors="replace")) > _AUDIT_MAX_LINE_BYTES:
                line = line.encode("utf-8", errors="replace")[: _AUDIT_MAX_LINE_BYTES - 14].decode(
                    "utf-8", errors="ignore"
                ) + "...<TRUNCATED>"
            _safe_write_line(line)


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
    decision: Decision
    tasks: List[TaskResult]
    artifacts_written_task_ids: List[str]


# -----------------------------
# Meaning gate
# -----------------------------
_KIND_TOKENS: Dict[KIND, List[str]] = {
    "excel": ["excel", "xlsx", "表", "列", "columns", "table"],
    "word": ["word", "docx", "見出し", "章", "アウトライン", "outline", "document"],
    "ppt": ["ppt", "pptx", "powerpoint", "スライド", "slides", "slide"],
}


def _prompt_mentions_any_kind(prompt: str) -> bool:
    p = (prompt or "").lower()
    for toks in _KIND_TOKENS.values():
        for t in toks:
            if t.lower() in p:
                return True
    return False


def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[Layer], str]:
    p = prompt or ""
    pl = p.lower()
    any_kind = _prompt_mentions_any_kind(p)

    if not any_kind:
        return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"

    tokens = _KIND_TOKENS[kind]
    if any(t.lower() in pl for t in tokens):
        return "RUN", None, "MEANING_KIND_MATCH"

    return "PAUSE_FOR_HITL", "meaning", "MEANING_KIND_MISSING"


# -----------------------------
# RFL gate
# -----------------------------
def _rfl_gate(prompt: str) -> Tuple[Decision, Optional[Layer], str]:
    p = prompt or ""
    triggers = ("おすすめ", "どっち", "どちら", "best", "recommend", "which is better")
    if any(t in p.lower() for t in [x.lower() for x in triggers]):
        return "PAUSE_FOR_HITL", "rfl", "REL_BOUNDARY_UNSTABLE"
    return "RUN", None, "RFL_OK"


# -----------------------------
# Contract validation
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
# Ethics
# -----------------------------
def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(raw_text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


# -----------------------------
# Agent generation
# -----------------------------
def _agent_generate(
    prompt: str, kind: KIND, faults: Dict[str, Any]
) -> Tuple[Dict[str, Any], str, str]:
    del prompt

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

    if break_contract:
        if kind == "excel":
            draft = {"cols": "Item,Owner,Status"}
        elif kind == "word":
            draft = {"heading": "Title"}
        elif kind == "ppt":
            draft = {"slides": "Purpose,Key Points"}

    if leak_email:
        raw_text += "\nContact: test.user+demo@example.com\n"

    safe_text = redact_sensitive(raw_text)
    return draft, raw_text, safe_text


# -----------------------------
# Artifact writer
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
    path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
    path.write_text(redact_sensitive(safe_text), encoding="utf-8")
    return path


# -----------------------------
# HITL helper
# -----------------------------
def _resolve_hitl(
    *,
    audit: AuditLog,
    run_id: str,
    task_id: str,
    layer: Layer,
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
            "sealed": False,
            "overrideable": True,
            "final_decider": "SYSTEM",
        }
    )

    choice: HitlChoice = "STOP"
    if hitl_resolver is not None:
        try:
            raw = hitl_resolver(run_id, task_id, layer, reason_code)
            choice = "CONTINUE" if raw == "CONTINUE" else "STOP"
        except Exception:
            choice = "STOP"

    audit.emit(
        {
            "run_id": run_id,
            "task_id": task_id,
            "event": "HITL_DECIDED",
            "layer": layer,
            "decision": "RUN" if choice == "CONTINUE" else "STOPPED",
            "reason_code": "HITL_CONTINUE" if choice == "CONTINUE" else "HITL_STOP",
            "sealed": False,
            "overrideable": False,
            "final_decider": "USER",
        }
    )
    return choice


def _overall_decision(tasks: List[TaskResult]) -> Decision:
    if any(t.decision == "STOPPED" for t in tasks):
        return "STOPPED"
    if any(t.decision == "PAUSE_FOR_HITL" for t in tasks):
        return "PAUSE_FOR_HITL"
    return "RUN"


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
    truncate_audit_on_start: bool = False,
    hitl_resolver: Optional[HitlResolver] = None,
) -> SimulationResult:
    faults = faults or {}
    audit = AuditLog(Path(audit_path))
    audit.start_run(truncate=truncate_audit_on_start)
    out_dir = Path(artifact_dir)

    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task_id, kind in _TASKS:
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "TASK_ASSIGNED",
                "layer": "orchestrator",
                "kind": kind,
                "decision": "RUN",
                "reason_code": "TASK_ASSIGNED",
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        # Meaning
        m_dec, m_layer, m_code = _meaning_gate(prompt, kind)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_MEANING",
                "layer": "meaning",
                "decision": m_dec,
                "reason_code": m_code,
                "sealed": False,
                "overrideable": m_dec == "PAUSE_FOR_HITL",
                "final_decider": "SYSTEM",
            }
        )

        if m_dec == "PAUSE_FOR_HITL" and m_layer is not None:
            choice = _resolve_hitl(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                layer=m_layer,
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
                        "reason_code": m_code,
                        "sealed": False,
                        "overrideable": False,
                        "final_decider": "USER",
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="STOPPED",
                        blocked_layer="meaning",
                        reason_code=m_code,
                        artifact_path=None,
                    )
                )
                continue

        # Agent output
        draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "AGENT_OUTPUT",
                "layer": "agent",
                "preview": safe_text[:200],
                "decision": "RUN",
                "reason_code": "AGENT_OUTPUT",
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        # Consistency
        ok, c_code = _validate_contract(kind, draft)
        c_dec: Decision = "RUN" if ok else "PAUSE_FOR_HITL"
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_CONSISTENCY",
                "layer": "consistency",
                "decision": c_dec,
                "reason_code": c_code,
                "sealed": False,
                "overrideable": c_dec == "PAUSE_FOR_HITL",
                "final_decider": "SYSTEM",
            }
        )

        if not ok:
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "REGEN_REQUESTED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": "REGEN_FOR_CONSISTENCY",
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "REGEN_INSTRUCTIONS",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": "REGEN_INSTRUCTIONS_V1",
                    "instructions": "Regenerate output to match the contract schema for this kind.",
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": c_code,
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
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
        r_dec, r_layer, r_code = _rfl_gate(prompt)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_RFL",
                "layer": "rfl",
                "decision": r_dec,
                "reason_code": r_code,
                "sealed": False,
                "overrideable": r_dec == "PAUSE_FOR_HITL",
                "final_decider": "SYSTEM",
            }
        )

        if r_dec == "PAUSE_FOR_HITL" and r_layer is not None:
            choice = _resolve_hitl(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                layer=r_layer,
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
                        "reason_code": r_code,
                        "sealed": False,
                        "overrideable": False,
                        "final_decider": "USER",
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="STOPPED",
                        blocked_layer="rfl",
                        reason_code=r_code,
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
                "sealed": pii_hit,
                "overrideable": False,
                "final_decider": "SYSTEM",
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
                    "sealed": True,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
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

        # Write artifact
        artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_WRITTEN",
                "layer": "orchestrator",
                "decision": "RUN",
                "reason_code": "ARTIFACT_WRITTEN",
                "artifact_path": str(artifact_path),
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
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

    return SimulationResult(
        run_id=run_id,
        decision=_overall_decision(task_results),
        tasks=task_results,
        artifacts_written_task_ids=artifacts_written,
    )


__all__ = [
    "EMAIL_RE",
    "AuditLog",
    "Decision",
    "HitlChoice",
    "SimulationResult",
    "TaskResult",
    "redact_sensitive",
    "run_simulation",
]
