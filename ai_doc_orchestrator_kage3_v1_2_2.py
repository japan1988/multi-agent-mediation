# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_2_2.py  (v1.2.4; filename kept for tests)

IEP-aligned pipeline:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH

Key properties:
- Fail-closed: unsafe/unstable -> STOPPED (sealed) or PAUSE_FOR_HITL (overrideable).
- RFL gate NEVER seals; always escalates to HITL with REL_* reason codes.
- HITL decision is recorded:
    HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
- ARL minimal keys emitted on every audit row:
    run_id, layer, decision, sealed, overrideable, final_decider, reason_code
- Audit hard invariant:
    No email-like tokens ("@") are persisted to disk (values AND dict keys).

Python: 3.9+
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

__version__ = "1.2.4"

# -----------------------------
# Timezone / Regex
# -----------------------------
JST = timezone(timedelta(hours=9))

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# -----------------------------
# Decisions / Layers (IEP)
# -----------------------------
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
# Tasks
# -----------------------------
_TASKS: List[Tuple[str, KIND]] = [
    ("task_excel", "excel"),
    ("task_word", "word"),
    ("task_ppt", "ppt"),
]

_KIND_TOKENS: Dict[KIND, List[str]] = {
    "excel": ["excel", "xlsx", "csv", "sheet", "spreadsheet", "エクセル", "スプレッドシート"],
    "word": ["word", "doc", "docx", "document", "文章", "文書"],
    "ppt": ["ppt", "pptx", "powerpoint", "slide", "slides", "プレゼン", "スライド"],
}

# -----------------------------
# Redaction (PII must not persist)
# -----------------------------
def redact_sensitive(text: str) -> str:
    """Redact email-like strings from text."""
    if not text:
        return text
    return EMAIL_RE.sub("[REDACTED_EMAIL]", text)


def _sanitize_obj(obj: Any) -> Any:
    """
    Deep sanitize:
    - Redact email-like tokens in strings
    - Redact dict KEYS as well (critical for '@' invariant)
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_sanitize_obj(x) for x in obj]
    if isinstance(obj, tuple):
        return [_sanitize_obj(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            ks = redact_sensitive(ks)
            out[ks] = _sanitize_obj(v)
        return out
    # fallback for non-JSON types:
    return redact_sensitive(str(obj))


# -----------------------------
# Audit Log (JSONL, monotonic ts)
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, truncate: bool = False) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            self.audit_path.write_text("", encoding="utf-8")
        self._last_ts = None

    def ts(self) -> str:
        now = datetime.now(JST)
        if self._last_ts is None:
            self._last_ts = now
            return now.isoformat()
        # monotonic: +1ms if time goes backwards or equal
        if now <= self._last_ts:
            now = self._last_ts + timedelta(milliseconds=1)
        self._last_ts = now
        return now.isoformat()

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a JSONL row.
        Hard guarantee:
          - No email-like tokens are persisted (values AND keys).
          - Never crash on non-JSON-serializable types (default=str via conversion).
        Also enforce ARL minimal keys on every row.
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        r = dict(row)

        # auto-fill ts
        r.setdefault("ts", self.ts())

        # ARL minimal keys (always)
        r.setdefault("run_id", "")
        r.setdefault("layer", "orchestrator")
        r.setdefault("decision", "RUN")
        r.setdefault("sealed", False)
        r.setdefault("overrideable", True)
        r.setdefault("final_decider", FINAL_DECIDER_SYSTEM)
        r.setdefault("reason_code", "")

        # deep sanitize (keys + values)
        safe_obj = _sanitize_obj(r)

        # final invariant check (fail-closed)
        blob = json.dumps(safe_obj, ensure_ascii=False, default=str)
        if "@" in blob or EMAIL_RE.search(blob):
            # If we ever reach here, sanitize failed — do not write.
            raise ValueError("Audit invariant violated: '@' / email-like token would be persisted.")

        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(blob + "\n")


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
# Helpers
# -----------------------------
def _prompt_mentions_any_kind(prompt: str) -> bool:
    pl = (prompt or "").lower()
    for toks in _KIND_TOKENS.values():
        for t in toks:
            if t.lower() in pl:
                return True
    return False


# -----------------------------
# Gates
# -----------------------------
def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[Layer], str]:
    p = (prompt or "")
    pl = p.lower()
    any_kind = _prompt_mentions_any_kind(p)

    if not any_kind:
        return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"

    tokens = _KIND_TOKENS.get(kind, [])
    if any(t.lower() in pl for t in tokens):
        return "RUN", None, "MEANING_KIND_MATCH"

    return "PAUSE_FOR_HITL", "meaning", "MEANING_KIND_MISSING"


def _validate_contract(kind: KIND, draft: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(draft, dict):
        return False, "CONTRACT_NOT_DICT"

    if kind == "excel":
        sheets = draft.get("sheets")
        if isinstance(sheets, list) and sheets:
            return True, "CONTRACT_OK_EXCEL"
        return False, "CONTRACT_BAD_EXCEL"

    if kind == "word":
        sections = draft.get("sections")
        if isinstance(sections, list) and sections:
            return True, "CONTRACT_OK_WORD"
        return False, "CONTRACT_BAD_WORD"

    if kind == "ppt":
        slides = draft.get("slides")
        if isinstance(slides, list) and slides:
            return True, "CONTRACT_OK_PPT"
        return False, "CONTRACT_BAD_PPT"

    return False, "CONTRACT_UNKNOWN_KIND"


def _rfl_gate(prompt: str, kind: KIND, draft: Dict[str, Any]) -> Tuple[Decision, Optional[Layer], str]:
    """
    RFL (Relativity Filter) gate:
    - MUST NOT seal
    - On hit: PAUSE_FOR_HITL with REL_* reason code
    Heuristics are intentionally simple and conservative.
    """
    p = (prompt or "").strip()
    pl = p.lower()

    # REL_REF_MISSING: comparative / optimization words without concrete reference
    rel_words = [
        "better", "best", "improve", "optimize", "faster", "cheaper", "more", "less",
        "高い", "低い", "早く", "速く", "安く", "良く", "最適", "改善", "増や", "減ら",
    ]
    has_rel = any(w in pl for w in rel_words)
    has_number = bool(re.search(r"\d", p))
    has_baseline_hint = any(x in pl for x in ["baseline", "reference", "kpi", "target", "目標", "基準", "指標"])
    if has_rel and not (has_number or has_baseline_hint):
        return "PAUSE_FOR_HITL", "rfl", "REL_REF_MISSING"

    # REL_BOUNDARY_UNSTABLE: hard tradeoffs requested simultaneously (quality vs speed vs cost)
    tradeoff_fast = any(x in pl for x in ["fast", "faster", "asap", "速", "早"])
    tradeoff_quality = any(x in pl for x in ["accurate", "perfect", "high quality", "精度", "完璧", "高品質"])
    tradeoff_cost = any(x in pl for x in ["cheap", "low cost", "無料", "安"])
    if (tradeoff_fast and tradeoff_quality) or (tradeoff_quality and tradeoff_cost) or (tradeoff_fast and tradeoff_cost):
        return "PAUSE_FOR_HITL", "rfl", "REL_BOUNDARY_UNSTABLE"

    # REL_SYMMETRY_BREAK: prompt mentions exactly one kind but this task is another kind.
    kinds_mentioned: List[KIND] = []
    for k, toks in _KIND_TOKENS.items():
        if any(t.lower() in pl for t in toks):
            kinds_mentioned.append(k)
    if len(set(kinds_mentioned)) == 1 and kind not in set(kinds_mentioned):
        return "PAUSE_FOR_HITL", "rfl", "REL_SYMMETRY_BREAK"

    return "RUN", None, "RFL_OK"


def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if not raw_text:
        return False, "ETHICS_NO_TEXT"
    if EMAIL_RE.search(raw_text):
        return True, "ETHICS_PII_EMAIL_DETECTED"
    return False, "ETHICS_OK"


def _artifact_ext(kind: KIND) -> str:
    if kind == "excel":
        return "xlsx"
    if kind == "word":
        return "docx"
    if kind == "ppt":
        return "pptx"
    return "txt"


def _acc_gate(
    *,
    kind: KIND,
    safe_text: str,
    contract_ok: bool,
    artifact_dir: Path,
    task_id: str,
) -> Tuple[Decision, Optional[Layer], str]:
    """
    ACC (pre-dispatch correctness/safety gate).
    - Sealing/STOPPED is allowed here if unsafe to write artifacts.
    """
    if not contract_ok:
        return "STOPPED", "acc", "ACC_CONTRACT_INVALID"

    if EMAIL_RE.search(safe_text or ""):
        return "STOPPED", "acc", "ACC_PII_REMAINED"

    ext = _artifact_ext(kind)
    candidate = (artifact_dir / f"{task_id}.{ext}.txt").resolve()
    base = artifact_dir.resolve()
    if base not in candidate.parents and candidate != base:
        return "STOPPED", "acc", "ACC_PATH_TRAVERSAL"

    return "RUN", None, "ACC_OK"


# -----------------------------
# Agent (simple deterministic-ish generator)
# -----------------------------
def _agent_generate(prompt: str, kind: KIND, faults: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    """
    Returns:
      draft: structured output (may be faulty)
      raw_text: may include PII (ethics checks raw)
      safe_text: redacted for logs/artifacts
    faults can inject:
      - {"break_contract": True}
      - {"inject_email": "user@example.com"}
    """
    break_contract = bool(faults.get("break_contract", False))
    inject_email = faults.get("inject_email")

    # raw_text may carry injected PII (to test ethics)
    raw_text = f"Generated {kind} artifact based on prompt: {prompt}"
    if inject_email:
        raw_text += f" contact={inject_email}"

    # draft
    if break_contract:
        draft = {"oops": "no_contract_here"}
    else:
        if kind == "excel":
            draft = {"sheets": [{"name": "Sheet1", "rows": [["A1", "B1"], ["A2", "B2"]]}]}
        elif kind == "word":
            draft = {"sections": [{"title": "Intro", "body": "Hello"}, {"title": "Body", "body": "..." }]}
        else:
            draft = {"slides": [{"title": "Title", "bullets": ["a", "b"]}, {"title": "End", "bullets": ["thanks"]}]}

    safe_text = redact_sensitive(raw_text)
    return draft, raw_text, safe_text


# -----------------------------
# Artifact writer (safe_text only)
# -----------------------------
def _write_artifact(artifact_dir: Path, task_id: str, kind: KIND, safe_text: str) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
    path.write_text(redact_sensitive(safe_text), encoding="utf-8")
    return path


# -----------------------------
# Simulation runner
# -----------------------------
def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
    hitl_actions: Optional[Dict[str, HITLAction]] = None,
    hitl_default: HITLAction = "STOP",
    truncate_audit_on_start: bool = False,
) -> SimulationResult:
    """
    Orchestrate 3 doc tasks with IEP gates.

    hitl_actions:
      dict(task_id -> "CONTINUE"|"STOP") for deterministic HITL decisions in tests.
    hitl_default:
      fallback action when not specified per task_id.
    """
    faults = faults or {}
    hitl_actions = hitl_actions or {}

    audit = AuditLog(Path(audit_path))
    audit.start_run(truncate=truncate_audit_on_start)
    out_dir = Path(artifact_dir)

    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    def _hitl_resolve(task_id: str, *, gate_layer: Layer, reason_code: str) -> HITLAction:
        """
        HITL flow (only allowed when sealed=False):
          HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
        """
        audit.emit({
            "run_id": run_id,
            "task_id": task_id,
            "event": "HITL_REQUESTED",
            "layer": "orchestrator",
            "decision": "PAUSE_FOR_HITL",
            "sealed": False,
            "overrideable": True,
            "final_decider": FINAL_DECIDER_SYSTEM,
            "reason_code": reason_code,
            "blocked_layer": gate_layer,
        })

        action: HITLAction = hitl_actions.get(task_id, hitl_default)

        audit.emit({
            "run_id": run_id,
            "task_id": task_id,
            "event": "HITL_DECIDED",
            "layer": "hitl_finalize",
            "decision": "RUN" if action == "CONTINUE" else "STOPPED",
            "sealed": False,  # HITL itself does not seal
            "overrideable": False,
            "final_decider": FINAL_DECIDER_USER,
            "reason_code": "HITL_CONTINUE" if action == "CONTINUE" else "HITL_STOP",
            "blocked_layer": gate_layer,
        })
        return action

    for task_id, kind in _TASKS:
        # assignment
        audit.emit({
            "run_id": run_id,
            "task_id": task_id,
            "event": "TASK_ASSIGNED",
            "layer": "orchestrator",
            "kind": kind,
            "decision": "RUN",
            "sealed": False,
            "overrideable": True,
            "final_decider": FINAL_DECIDER_SYSTEM,
            "reason_code": "TASK_ASSIGNED",
        })

        # Meaning
        m_dec, m_layer, m_code = _meaning_gate(prompt, kind)
        audit.emit({
            "run_id": run_id,
            "task_id": task_id,
            "event": "GATE_MEANING",
            "layer": "meaning",
            "decision": m_dec,
            "sealed": False,
            "overrideable": (m_dec == "PAUSE_FOR_HITL"),
            "final_decider": FINAL_DECIDER_SYSTEM,
            "reason_code": m_code,
        })
        if m_dec == "PAUSE_FOR_HITL":
            action = _hitl_resolve(task_id, gate_layer="meaning", reason_code=m_code)
            if action == "STOP":
                audit.emit({
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": FINAL_DECIDER_SYSTEM,
                    "reason_code": m_code,
                })
                task_results.append(TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="PAUSE_FOR_HITL",
                    blocked_layer="meaning",
                    reason_code=m_code,
                    artifact_path=None,
                ))
                continue

        # Agent
        draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))
        audit.emit({
            "run_id": run_id,
            "task_id": task_id,
            "event": "AGENT_OUTPUT",
            "layer": "agent",
            "decision": "RUN",
            "sealed": False,
            "overrideable": True,
            "final_decider": FINAL_DECIDER_SYSTEM,
            "reason_code": "AGENT_OUTPUT_SAFE_PREVIEW",
            "preview": safe_text[:200],
        })

        # Consistency
        ok, c_code = _validate_contract(kind, draft)
        c_dec: Decision = "RUN" if ok else "PAUSE_FOR_HITL"
        audit.emit({
            "run_id": run_id,
