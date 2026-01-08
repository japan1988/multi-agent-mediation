# ai_doc_orchestrator_kage3_v1_2_4.py  (v1.2.4)  ※ファイル名は維持でもOK
# -*- coding: utf-8 -*-
"""
(ai_doc_orchestrator_kage3_v1_2_2.py に対する設計寄り改修 + IEP寄せ)

Changes (design-oriented):
- AuditLog gains start_run(truncate=...) to control log lifecycle per run.
- AuditLog owns ts_state (monotonic timestamp) instead of module-global _LAST_TS.
- Defensive JSON serialization: default=str so audit never crashes on non-JSON types.
- Deep redaction also redacts dict keys (prevents email-like keys from persisting).
- emit() auto-fills "ts" if missing.

v1.2.4 (IEP-aligned additions):
- Pipeline aligned: Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH
- Decision vocabulary aligned: RUN / PAUSE_FOR_HITL / STOPPED
- RFL gate added (never seals; always escalates to HITL):
    REL_BOUNDARY_UNSTABLE / REL_REF_MISSING / REL_SYMMETRY_BREAK
- HITL decision events recorded:
    HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
- ARL minimal keys emitted on every audit row:
    run_id, layer, decision, sealed, overrideable, final_decider, reason_code

Notes:
- Sealing is allowed ONLY in Ethics / ACC (STOPPED + sealed=True).
- RFL must NEVER seal (PAUSE_FOR_HITL only; sealed=False).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

__version__ = "1.2.4"

JST = timezone(timedelta(hours=9))

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
Layer = Literal[
    "meaning",
    "consistency",
    "rfl",
    "ethics",
    "acc",
    "orchestrator",
    "agent",
    "hitl_finalize",
    "dispatch",
]
KIND = Literal["excel", "word", "ppt"]
HITLAction = Literal["CONTINUE", "STOP"]

FINAL_DECIDER_SYSTEM = "SYSTEM"
FINAL_DECIDER_USER = "USER"


# -----------------------------
# Redaction (PII must not persist)
# -----------------------------
def redact_sensitive(text: str) -> str:
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def _deep_redact(obj: Any) -> Any:
    """Deep redaction over dict/list/str (includes dict keys)."""
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, list):
        return [_deep_redact(x) for x in obj]
    if isinstance(obj, dict):
        # IMPORTANT: redact keys too (keys can contain email-like strings)
        return {redact_sensitive(str(k)): _deep_redact(v) for k, v in obj.items()}
    return obj


# -----------------------------
# Audit logger (PII-safe JSONL) with run lifecycle + ts_state
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, *, truncate: bool = False) -> None:
        """
        Start a run:
        - Optionally truncate the audit file (truncate=True).
        - Reset ts_state so monotonic timestamps are per-run (test-friendly).
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            with self.audit_path.open("w", encoding="utf-8"):
                pass
        self._last_ts = None

    def ts(self) -> str:
        """
        Monotonic timestamp (microseconds), scoped to this AuditLog instance.
        """
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(microseconds=1)
        self._last_ts = now
        return now.isoformat(timespec="microseconds")

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a JSONL row.
        Hard guarantee: no email-like strings are persisted.
        Also: never crash on non-JSON-serializable types (default=str).

        Additionally enforces ARL minimal keys on every row:
          run_id, layer, decision, sealed, overrideable, final_decider, reason_code
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        # auto-fill ts if missing (callers may still pass explicit ts)
        if "ts" not in row:
            row = dict(row)
            row["ts"] = self.ts()

        # Enforce ARL minimal keys on every row (fail-closed: never omit)
        # Defaults are conservative and non-breaking for callers.
        row = dict(row)
        row.setdefault("run_id", "UNKNOWN_RUN")
        row.setdefault("layer", "orchestrator")
        row.setdefault("decision", "RUN")
        row.setdefault("sealed", False)
        row.setdefault("overrideable", True)
        row.setdefault("final_decider", FINAL_DECIDER_SYSTEM)
        row.setdefault("reason_code", "")

        # Safe copy (no mutation), tolerate non-JSON types
        safe_row = json.loads(json.dumps(row, ensure_ascii=False, default=str))
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
    "ppt": ["ppt", "pptx]()
