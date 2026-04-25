# -*- coding: utf-8 -*-
"""

ai_doc_orchestrator_kage3_v1_3_0.py (v1.3.0)

(ai_doc_orchestrator_kage3_v1_2_2.py に対する設計寄り改修 + IEP寄せ + HITL分岐)
v1.3.0 additions:
- Optional runaway loop detection (repeat failures) -> ACC seal (sealed=True) to enforce forced stop
- Optional seeded random HITL resolver helper for stress tests (deterministic with seed)
- Optional per-task attempt loop for consistency failures when user chooses CONTINUE

KAGE-ish gates fixed order:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

IEP notes:
- RFL never seals; it only escalates to HITL (PAUSE_FOR_HITL).
- Sealing is allowed only in Ethics / ACC.

ai_doc_orchestrator_kage3_v1_3_5.py

Self-contained compatibility implementation.

Goals:
- Standalone file
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


import json
import random
import re
import time
import hashlib
from dataclasses import dataclass, field

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


# IEP-aligned decisions
Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]

# IEP-aligned final decider
FinalDecider = Literal["SYSTEM", "USER"]

# Layers (expanded)

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

HitlResolver = Callable[[str, str, str, str], HitlChoice]  # (run_id, task_id, layer, reason_code)


# -----------------------------
# Redaction (PII must not persist)
# -----------------------------
def redact_sensitive(text: str) -> str:
    """Redact email-like strings from a text."""

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
        """Monotonic timestamp (microseconds), scoped to this AuditLog instance."""

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

        return now.isoformat(timespec="microseconds")

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a JSONL row.

        Hard guarantee: no email-like strings are persisted.
        Also: never crash on non-JSON-serializable types (default=str).

        Policy:
        - auto-fill "ts" if missing
        - deep redact if serialized blob contains email-like patterns
        - write as JSONL (one row per line)
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        # auto-fill ts if missing (callers may still pass explicit ts)
        if "ts" not in row:
            row = dict(row)
            row["ts"] = self.ts()

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
# Small helpers (ARL-minimal fields)
# -----------------------------
def _arl_base(*, sealed: bool, overrideable: bool, final_decider: FinalDecider) -> Dict[str, Any]:
    return {
        "sealed": bool(sealed),
        "overrideable": bool(overrideable),
        "final_decider": final_decider,
    }

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

    layer: Layer,

    layer: str,

    reason_code: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "event": event,
        "layer": layer,

        "decision": "RUN",  # informational events keep ARL-minimal key presence

        "decision": "RUN",

        "reason_code": reason_code,
        **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
    }
    if extra:
        row.update(extra)
    audit.emit(row)



# -----------------------------
# HITL firepoint (branch point)
# -----------------------------

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

    layer: Layer,
    reason_code: str,
    hitl_resolver: Optional[HitlResolver],
) -> HitlChoice:
    """
    Firepoint:
    1) SYSTEM logs PAUSE_FOR_HITL (overrideable=True, sealed=False)
    2) USER decides CONTINUE/STOP
    3) USER decision is logged and downstream branches
    """

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


    choice: HitlChoice = "STOP" if hitl_resolver is None else hitl_resolver(run_id, task_id, layer, reason_code)

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



# -----------------------------
# Stress-test helper: seeded random HITL policy
# -----------------------------
def make_random_hitl_resolver(*, seed: int = 42, p_continue: float = 0.85) -> HitlResolver:
    """
    Deterministic stochastic HITL policy (seeded).
    - p_continue: probability of CONTINUE (0.0..1.0)
    """
    if not (0.0 <= p_continue <= 1.0):
        raise ValueError("p_continue must be in [0.0, 1.0]")
    rng = random.Random(seed)

    def _resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> HitlChoice:
        _ = (run_id, task_id, layer, reason_code)  # reserved for future policy features
        return "CONTINUE" if (rng.random() < p_continue) else "STOP"

    return _resolver


# -----------------------------
# Runaway (failure loop) state + sealing (ACC)
# -----------------------------
@dataclass
class RunawayState:
    last_key: Dict[str, Optional[Tuple[str, str]]] = field(default_factory=dict)  # task_id -> (layer, reason_code)
    streak: Dict[str, int] = field(default_factory=dict)  # task_id -> consecutive count
    sealed_tasks: Dict[str, str] = field(default_factory=dict)  # task_id -> seal_reason_code

    def note_failure_and_check(self, *, task_id: str, layer: str, reason_code: str, threshold: int) -> bool:
        key = (layer, reason_code)
        if self.last_key.get(task_id) == key:
            self.streak[task_id] = self.streak.get(task_id, 0) + 1
        else:
            self.last_key[task_id] = key
            self.streak[task_id] = 1
        return self.streak[task_id] >= threshold

    def seal(self, *, task_id: str, reason_code: str) -> None:
        self.sealed_tasks[task_id] = reason_code

    def is_sealed(self, *, task_id: str) -> bool:
        return task_id in self.sealed_tasks

    def seal_reason(self, *, task_id: str) -> str:
        return self.sealed_tasks.get(task_id, "")


# -----------------------------
# Meaning gate (kind-local)
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
# RFL (Relativity Filter) - minimal prompt-based stub
# -----------------------------
_RFL_TRIGGERS = [
    "どっち",
    "どちら",
    "どれが",
    "良いか",
    "いいか",
    "おすすめ",
    "最適",
    "評価",
    "比較",
]


def _rfl_gate(prompt: str) -> Tuple[Decision, Optional[Layer], str]:
    """
    Minimal RFL:
    Detects relative/subjective boundary prompts and escalates to HITL without sealing.
    """
    p = prompt or ""
    if any(t in p for t in _RFL_TRIGGERS):
        return "PAUSE_FOR_HITL", "rfl", "REL_BOUNDARY_UNSTABLE"
    return "RUN", None, "REL_OK"


# -----------------------------
# Ethics detection (memory-only raw_text)
# -----------------------------
def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(raw_text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


# -----------------------------
# ACC gate (seal-aware)
# -----------------------------
def _acc_gate(*, task_id: str, runaway: RunawayState) -> Tuple[Decision, Optional[Layer], str, bool]:
    """
    ACC gate checks seal registry.
    Returns (decision, blocked_layer, reason_code, sealed)
    """
    if runaway.is_sealed(task_id=task_id):
        return "STOPPED", "acc", runaway.seal_reason(task_id=task_id) or "SEALED_BY_ACC", True
    return "RUN", None, "ACC_OK", False


# -----------------------------
# Agent generation (raw vs safe; raw never persisted)
# -----------------------------
def _agent_generate(prompt: str, kind: KIND, faults: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
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
    # Simulator writes text payload; keep kind-ext visible for traceability.
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

    truncate_audit_on_start: bool = False,
    hitl_resolver: Optional[HitlResolver] = None,
    # v1.3.0: optional forced-stop (ACC seal) + per-task retry loop
    enable_runaway_seal: bool = False,
    runaway_threshold: int = 10,
    max_attempts_per_task: int = 1,
) -> SimulationResult:
    """
    truncate_audit_on_start:
    - True: start_run(truncate=True) で run ごとに監査ログを初期化
    - False: append 継続（従来互換。ただし ts_state は run ごとにリセット）

    hitl_resolver:
    - (run_id, task_id, layer, reason_code) -> "CONTINUE" or "STOP"
    - None の場合は fail-closed で STOP

    enable_runaway_seal / runaway_threshold / max_attempts_per_task:
    - enable_runaway_seal=True かつ max_attempts_per_task>=2 の場合、
      consistency 失敗で CONTINUE が続くと attempt を回し、連続失敗が runaway_threshold に達したら
      ACC により sealed=True として強制停止します。
    - 互換性のためデフォルト max_attempts_per_task=1（=従来どおり再試行しない）
    """
    if runaway_threshold <= 0:
        raise ValueError("runaway_threshold must be >= 1")
    if max_attempts_per_task <= 0:
        raise ValueError("max_attempts_per_task must be >= 1")

    faults = faults or {}

    audit = AuditLog(Path(audit_path))
    audit.start_run(truncate=truncate_audit_on_start)
    out_dir = Path(artifact_dir)

    runaway = RunawayState()
    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task_id, kind in _TASKS:
        _emit_info(
            audit=audit,
            run_id=run_id,
            task_id=task_id,
            event="TASK_ASSIGNED",
            layer="orchestrator",
            reason_code="TASK_ASSIGNED",
            extra={"kind": kind},
        )

        # If already sealed in this run (e.g., earlier attempts), block immediately
        a_dec0, a_blk0, a_code0, a_sealed0 = _acc_gate(task_id=task_id, runaway=runaway)
        if a_dec0 == "STOPPED":
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "DISPATCH_BLOCKED_BY_SEAL",
                    "layer": "acc",
                    "decision": "STOPPED",
                    "reason_code": a_code0 or "DISPATCH_BLOCKED_BY_SEAL",
                    **_arl_base(sealed=True, overrideable=False, final_decider="SYSTEM"),
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="STOPPED",
                    blocked_layer="acc",
                    reason_code=a_code0 or "DISPATCH_BLOCKED_BY_SEAL",
                    artifact_path=None,
                )
            )
            continue

        # Attempt loop (used mainly for consistency-failure CONTINUE loop)
        final_task_result: Optional[TaskResult] = None

        for attempt in range(1, max_attempts_per_task + 1):
            _emit_info(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                event="ATTEMPT_START",
                layer="orchestrator",
                reason_code="ATTEMPT_START",
                extra={"attempt": attempt},
            )

            # -----------------
            # Meaning gate
            # -----------------
            m_dec, _, m_code = _meaning_gate(prompt, kind)
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "GATE_MEANING",
                    "layer": "meaning",
                    "decision": m_dec,
                    "reason_code": m_code,
                    **_arl_base(sealed=False, overrideable=(m_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
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
                    final_task_result = TaskResult(
=======
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

                    break
                # CONTINUE -> proceed

            # -----------------
            # Agent output (raw never persisted)
            # -----------------
            draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))

            _emit_info(
                audit=audit,
                run_id=run_id,
                task_id=task_id,
                event="AGENT_OUTPUT",
                layer="agent",
                reason_code="AGENT_OUTPUT_PREVIEW",
                extra={"preview": safe_text[:200], "attempt": attempt},
            )

            # -----------------
            # Consistency gate
            # -----------------
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
                    **_arl_base(sealed=False, overrideable=(c_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
                }
            )

            if not ok:
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
                    final_task_result = TaskResult(

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

                    break

                # CONTINUE: request regen and (optionally) loop attempts
                _emit_info(
                    audit=audit,
                    run_id=run_id,
                    task_id=task_id,
                    event="REGEN_REQUESTED",
                    layer="orchestrator",
                    reason_code="REGEN_FOR_CONSISTENCY",
                    extra={"attempt": attempt},
                )
                _emit_info(
                    audit=audit,
                    run_id=run_id,
                    task_id=task_id,
                    event="REGEN_INSTRUCTIONS",
                    layer="orchestrator",
                    reason_code="REGEN_INSTRUCTIONS_V1",
                    extra={"instructions": "Regenerate output to match the contract schema for this kind.", "attempt": attempt},
                )

                # runaway check / seal (ACC) if enabled
                if enable_runaway_seal and max_attempts_per_task >= 2:
                    is_runaway = runaway.note_failure_and_check(
                        task_id=task_id, layer="consistency", reason_code=c_code, threshold=runaway_threshold
                    )
                    if is_runaway:
                        runaway.seal(task_id=task_id, reason_code="SEALED_BY_ACC_RUNAWAY")
                        audit.emit(
                            {
                                "run_id": run_id,
                                "task_id": task_id,
                                "event": "AGENT_SEALED",
                                "layer": "acc",
                                "decision": "STOPPED",
                                "reason_code": "SEALED_BY_ACC_RUNAWAY",
                                **_arl_base(sealed=True, overrideable=False, final_decider="SYSTEM"),
                            }
                        )
                        final_task_result = TaskResult(
                            task_id=task_id,
                            kind=kind,
                            decision="STOPPED",
                            blocked_layer="acc",
                            reason_code="SEALED_BY_ACC_RUNAWAY",
                            artifact_path=None,
                        )
                        break

                # Not sealed: if we can retry, continue to next attempt; else pause
                if attempt < max_attempts_per_task:
                    continue

                # no more attempts -> stay PAUSE_FOR_HITL
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
                final_task_result = TaskResult(

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

                break

            # -----------------
            # RFL gate (optional stub)
            # -----------------
            r_dec, _, r_code = _rfl_gate(prompt)
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "GATE_RFL",
                    "layer": "rfl",
                    "decision": r_dec,
                    "reason_code": r_code,
                    **_arl_base(sealed=False, overrideable=(r_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
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
                  =======
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

                    break
                # CONTINUE -> proceed

            # -----------------
            # Ethics gate (sealed on violation)
            # -----------------
            pii_hit, e_code = _ethics_detect_pii(raw_text)
            e_dec: Decision = "STOPPED" if pii_hit else "RUN"


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
                    overrideable=False,
                    final_decider="SYSTEM",
                ),
            }
        )

        if pii_hit:

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,

                    "event": "GATE_ETHICS",
                    "layer": "ethics",
                    "decision": e_dec,
                    "reason_code": e_code,
                    **_arl_base(sealed=bool(pii_hit), overrideable=False, final_decider="SYSTEM"),
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
                final_task_result = TaskResult(

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

                break

            # -----------------
            # ACC gate (seal-aware)
            # -----------------
            a_dec, a_blk, a_code, a_sealed = _acc_gate(task_id=task_id, runaway=runaway)

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

                    "event": "GATE_ACC",
                    "layer": "acc",
                    "decision": a_dec,
                    "reason_code": a_code,
                    **_arl_base(sealed=bool(a_sealed), overrideable=False, final_decider="SYSTEM"),
                }
            )

            if a_dec != "RUN":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "acc",
                        "decision": "STOPPED",
                        "reason_code": a_code or "ACC_BLOCKED",
                        **_arl_base(sealed=True, overrideable=False, final_decider="SYSTEM"),
                    }
                )
                final_task_result = TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="STOPPED",
                    blocked_layer="acc",
                    reason_code=a_code or "ACC_BLOCKED",
                    artifact_path=None,
                )
                break

            # -----------------
            # Dispatch / write artifact (safe only)
            # -----------------
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
                    "attempt": attempt,
                }
            )

            artifacts_written.append(task_id)
            final_task_result = TaskResult(

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

            break

        # End attempts: if still None (shouldn't), fail-closed
        if final_task_result is None:
            final_task_result = TaskResult(
                task_id=task_id,
                kind=kind,
                decision="STOPPED",
                blocked_layer="orchestrator",
                reason_code="FAIL_CLOSED_UNEXPECTED_STATE",
                artifact_path=None,
            )
        task_results.append(final_task_result)

    # Overall decision:
    # - If any task STOPPED -> STOPPED
    # - Else if any task PAUSE_FOR_HITL -> PAUSE_FOR_HITL
    # - Else RUN
    if any(t.decision == "STOPPED" for t in task_results):
        overall: OverallDecision = "STOPPED"
    elif any(t.decision == "PAUSE_FOR_HITL" for t in task_results):
        overall = "PAUSE_FOR_HITL"
    else:
        overall = "RUN"

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



# -----------------------------
# Optional: CLI HITL resolver (for manual runs)
# -----------------------------
def interactive_hitl_resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> HitlChoice:
    """Simple interactive resolver for local testing."""
    q = f"[HITL] run_id={run_id} task_id={task_id} layer={layer} reason={reason_code} -> (c=CONTINUE / s=STOP): "
    for _ in range(5):
        ans = input(q).strip().lower()

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

    return "STOP"  # fail-closed



# -----------------------------
# v1.3.1: In-memory audit + benchmark utilities (repro-friendly)
# -----------------------------
@dataclass
class MemoryAuditLog:
    """
    In-memory PII-safe JSONL-equivalent logger.

    Intended use:
    - stress/benchmark runs (avoid disk I/O)
    - reproducibility checks (rows available for hashing)
    """
    rows: List[Dict[str, Any]] = field(default_factory=list)
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, *, truncate: bool = False) -> None:
        # truncate parameter kept for interface symmetry
        if truncate:
            self.rows.clear()
        self._last_ts = None

    def ts(self) -> str:
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(microseconds=1)
        self._last_ts = now
        return now.isoformat(timespec="microseconds")

    def emit(self, row: Dict[str, Any]) -> None:
        # auto-fill ts if missing
        if "ts" not in row:
            row = dict(row)
            row["ts"] = self.ts()

        safe_row = json.loads(json.dumps(row, ensure_ascii=False, default=str))
        safe_blob = json.dumps(safe_row, ensure_ascii=False)
        if EMAIL_RE.search(safe_blob):
            safe_row = _deep_redact(safe_row)

        self.rows.append(safe_row)

    def to_jsonl(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in self.rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def semantic_signature_sha256(rows: List[Dict[str, Any]]) -> str:
    """
    Produce a reproducible semantic signature for audit rows.

    Notes:
    - drops ts and artifact_path (environment-dependent)
    - keeps event/layer/decision/reason_code etc.
    """
    sig = []
    for r in rows:
        sig.append(
            {
                "event": r.get("event"),
                "layer": r.get("layer"),
                "decision": r.get("decision"),
                "reason_code": r.get("reason_code"),
                "task_id": r.get("task_id"),
                "sealed": r.get("sealed"),
                "overrideable": r.get("overrideable"),
                "final_decider": r.get("final_decider"),
                "attempt": r.get("attempt"),
            }
        )
    blob = json.dumps(sig, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()



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

    max_attempts_per_task: int = 1,
) -> Tuple[SimulationResult, List[Dict[str, Any]]]:
    """
    Memory-only variant of run_simulation for stress/benchmarking:
    - no disk audit I/O
    - no artifact writes
    - returns (SimulationResult, audit_rows)
    """
    faults = faults or {}
    audit = MemoryAuditLog()
    audit.start_run(truncate=True)

    runaway = RunawayState()

    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []  # always empty in mem bench mode

    runaway_counts: Dict[str, int] = {}

    for task_id, kind in _TASKS:
        runaway_counts.setdefault(task_id, 0)

        _emit_info(
            audit=audit,  # type: ignore[arg-type]
            run_id=run_id,
            task_id=task_id,
            event="TASK_ASSIGNED",
            layer="orchestrator",
            reason_code="TASK_ASSIGNED",
            extra={"kind": kind},
        )

        # Meaning gate
        m_dec, _, m_code = _meaning_gate(prompt, kind)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_MEANING",
                "layer": "meaning",
                "decision": m_dec,
                "reason_code": m_code,
                **_arl_base(sealed=False, overrideable=(m_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
            }
        )

        if m_dec == "PAUSE_FOR_HITL":
            choice = _hitl_fire_and_decide(
                audit=audit,  # type: ignore[arg-type]
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

        attempts = max(1, int(max_attempts_per_task))
        sealed_by_acc = False

        for attempt in range(1, attempts + 1):
            draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))

            _emit_info(
                audit=audit,  # type: ignore[arg-type]
                run_id=run_id,
                task_id=task_id,
                event="AGENT_OUTPUT",
                layer="agent",
                reason_code="AGENT_OUTPUT_PREVIEW",
                extra={"preview": safe_text[:200], "attempt": attempt},
            )

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
                    "attempt": attempt,
                    **_arl_base(sealed=False, overrideable=(c_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
                }
            )

            if not ok:
                choice = _hitl_fire_and_decide(
                    audit=audit,  # type: ignore[arg-type]
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
                            "attempt": attempt,
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
                    break

                _emit_info(
                    audit=audit,  # type: ignore[arg-type]
                    run_id=run_id,
                    task_id=task_id,
                    event="REGEN_REQUESTED",
                    layer="orchestrator",
                    reason_code="REGEN_FOR_CONSISTENCY",
                    extra={"attempt": attempt},
                )
                _emit_info(
                    audit=audit,  # type: ignore[arg-type]
                    run_id=run_id,
                    task_id=task_id,
                    event="REGEN_INSTRUCTIONS",
                    layer="orchestrator",
                    reason_code="REGEN_INSTRUCTIONS_V1",
                    extra={"instructions": "Regenerate output to match the contract schema for this kind.", "attempt": attempt},
                )

                runaway_counts[task_id] += 1
                if enable_runaway_seal and runaway_counts[task_id] >= int(runaway_threshold):
                    runaway.seal(task_id=task_id, reason_code="SEALED_BY_ACC_RUNAWAY")
                    audit.emit(
                        {
                            "run_id": run_id,
                            "task_id": task_id,
                            "event": "AGENT_SEALED",
                            "layer": "acc",
                            "decision": "STOPPED",
                            "reason_code": "SEALED_BY_ACC_RUNAWAY",
                            "attempt": attempt,
                            **_arl_base(sealed=True, overrideable=False, final_decider="SYSTEM"),
                        }
                    )
                    task_results.append(
                        TaskResult(
                            task_id=task_id,
                            kind=kind,
                            decision="STOPPED",
                            blocked_layer="acc",
                            reason_code="SEALED_BY_ACC_RUNAWAY",
                            artifact_path=None,
                        )
                    )
                    sealed_by_acc = True
                    break

                if attempt < attempts:
                    continue

                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "PAUSE_FOR_HITL",
                        "reason_code": c_code,
                        "attempt": attempt,
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
                break

            # RFL
            r_dec, _, r_code = _rfl_gate(prompt)
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "GATE_RFL",
                    "layer": "rfl",
                    "decision": r_dec,
                    "reason_code": r_code,
                    "attempt": attempt,
                    **_arl_base(sealed=False, overrideable=(r_dec == "PAUSE_FOR_HITL"), final_decider="SYSTEM"),
                }
            )
            if r_dec == "PAUSE_FOR_HITL":
                choice = _hitl_fire_and_decide(
                    audit=audit,  # type: ignore[arg-type]
                    run_id=run_id,
                    task_id=task_id,
                    layer="rfl",
                    reason_code=r_code,
                    hitl_resolver=hitl_resolver,
                )
                if choice == "STOP":
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
                    break

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
                    "attempt": attempt,
                    **_arl_base(sealed=bool(pii_hit), overrideable=False, final_decider="SYSTEM"),
                }
            )
            if pii_hit:
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
                break

            # ACC
            a_dec, _, a_code, _acc_sealed = _acc_gate(task_id=task_id, runaway=runaway)
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "GATE_ACC",
                    "layer": "acc",
                    "decision": a_dec,
                    "reason_code": a_code,
                    "attempt": attempt,
                    **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
                }
            )

            # No artifact writes in mem mode
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "orchestrator",
                    "decision": "RUN",
                    "reason_code": "BENCH_NO_ARTIFACT",
                    "attempt": attempt,
                    **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="RUN",
                    blocked_layer=None,
                    reason_code="OK",
                    artifact_path=None,
                )
            )
            break

        if sealed_by_acc:
            continue

    if any(t.decision == "STOPPED" for t in task_results):
        overall: OverallDecision = "STOPPED"
    elif any(t.decision == "PAUSE_FOR_HITL" for t in task_results):
        overall = "PAUSE_FOR_HITL"
    else:
        overall = "RUN"

    return (
        SimulationResult(run_id=run_id, decision=overall, tasks=task_results, artifacts_written_task_ids=artifacts_written),
        audit.rows,
    )


def run_benchmark_suite(
    *,
    prompt: str,
    runs: int,
    seed: int,
    p_continue: float,
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
    enable_runaway_seal: bool = True,
    runaway_threshold: int = 10,
    max_attempts_per_task: int = 20,
) -> Dict[str, Any]:
    """
    Repro-friendly benchmark runner (memory-only).

    Returns summary metrics:
    - runs/sec, crash-free rate
    - decision distribution
    - seal rate (ACC runaway, ethics)
    - PII invariant check (audit rows contain '@' == 0)
    """
    faults = faults or {}

    resolver = make_random_hitl_resolver(seed=seed, p_continue=p_continue)

    t0 = time.perf_counter()
    crashes = 0
    overall_counts: Dict[str, int] = {"RUN": 0, "PAUSE_FOR_HITL": 0, "STOPPED": 0}
    acc_seal = 0
    ethics_seal = 0
    at_sign_violations = 0

    sig_hasher = hashlib.sha256()

    for i in range(int(runs)):
        try:
            res, rows = run_simulation_mem(
                prompt=prompt,
                run_id=f"BENCH#{i}",
                faults=faults,
                hitl_resolver=resolver,
                enable_runaway_seal=enable_runaway_seal,
                runaway_threshold=runaway_threshold,
                max_attempts_per_task=max_attempts_per_task,
            )
        except Exception:
            crashes += 1
            continue

        overall_counts[res.decision] = overall_counts.get(res.decision, 0) + 1

        for r in rows:
            if r.get("event") == "AGENT_SEALED" and r.get("reason_code") == "SEALED_BY_ACC_RUNAWAY":
                acc_seal += 1
            if r.get("event") == "GATE_ETHICS" and r.get("sealed") is True:
                ethics_seal += 1

        blob = json.dumps(rows, ensure_ascii=False)
        if "@" in blob:
            at_sign_violations += 1

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



# -----------------------------
# Safety scorecard (policy-as-testable-interface)
# -----------------------------
def safety_scorecard(
    report: Dict[str, Any],
    *,
    require_seal_events: bool = True,
    require_pii_zero: bool = True,
    require_crash_free: bool = True,
) -> Dict[str, Any]:
    """
    Convert a benchmark report into a PASS/FAIL decision under "danger => stop; no unsafe output".

    Defaults (recommended for CI in this repo):
    - require_seal_events: True  (fault injection + runaway seal expected to trigger)
    - require_pii_zero: True     (@-like PII never persists in audit rows)
    - require_crash_free: True   (no exceptions in benchmark loop)

    Returns:
      {
        "pass": bool,
        "fail_reasons": [..],
        "observations": {...}
      }
    """
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

    # Observational checks (non-failing by default)
    obs = {
        "runs": runs,
        "crashes": crashes,
        "at_sign_violations": at_viol,
        "acc_seal_events": acc_seal,
        "ethics_seal_events": ethics_seal,
        "overall_decision_counts": counts,
        "repro_semantic_digest_sha256": report.get("repro_semantic_digest_sha256"),
    }

    return {"pass": len(reasons) == 0, "fail_reasons": reasons, "observations": obs}


def assert_no_artifacts_for_blocked_tasks(result: SimulationResult) -> None:
    """
    Policy helper:
      If a task is blocked (STOPPED or PAUSE_FOR_HITL), it must not claim an artifact_path.
    """
    for t in result.tasks:
        if t.decision in ("STOPPED", "PAUSE_FOR_HITL"):
            if t.artifact_path:
                raise AssertionError(f"Blocked task wrote artifact: task_id={t.task_id} path={t.artifact_path}")


__all__ = [
    "EMAIL_RE",
    "run_simulation",
    "AuditLog",
    "SimulationResult",
    "TaskResult",
    "HitlResolver",
    "interactive_hitl_resolver",
    "redact_sensitive",
    "make_random_hitl_resolver",

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

    rng = random.Random(int(seed))  # nosec B311

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
    rng = random.Random(int(seed))  # nosec B311

    overall_decision_counts: Dict[str, int] = {
        "RUN": 0,
        "PAUSE_FOR_HITL": 0,
        "STOPPED": 0,
    }
    reason_counts: Dict[str, int] = {}

    crash_count = 0
    pii_leak_count = 0
    at_sign_violations = 0
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
            at_sign_violations += 1
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
    at_sign_violation_rate = at_sign_violations / total_runs
    hitl_requested_rate = hitl_requested_count / total_runs
    seal_event_rate = seal_event_count / total_runs

    crash_free_rate = 1.0 - crash_rate
    pii_free_rate = 1.0 - pii_leak_rate

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
        "at_sign_violations": at_sign_violations,
        "hitl_requested_count": hitl_requested_count,
        "seal_event_count": seal_event_count,
        "crashes": crash_count,
        "pii_leaks": pii_leak_count,
        "run_rate": run_rate,
        "pause_rate": pause_rate,
        "stop_rate": stop_rate,
        "crash_rate": crash_rate,
        "pii_leak_rate": pii_leak_rate,
        "at_sign_violation_rate": at_sign_violation_rate,
        "hitl_requested_rate": hitl_requested_rate,
        "seal_event_rate": seal_event_rate,
        "crash_free_rate": crash_free_rate,
        "pii_free_rate": pii_free_rate,
        "no_pii_leak_rate": pii_free_rate,
        "summary": {
            "run_rate": run_rate,
            "pause_rate": pause_rate,
            "stop_rate": stop_rate,
            "crash_rate": crash_rate,
            "crash_free_rate": crash_free_rate,
            "pii_leak_rate": pii_leak_rate,
            "pii_free_rate": pii_free_rate,
            "at_sign_violations": at_sign_violations,
            "at_sign_violation_rate": at_sign_violation_rate,
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

    # Minimal local smoke run (manual HITL)
    result = run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        run_id="RUN#LOCAL",
        audit_path="out/audit_v1_3_0.jsonl",
        artifact_dir="out/artifacts_v1_3_0",
        truncate_audit_on_start=True,
        hitl_resolver=interactive_hitl_resolver,
        enable_runaway_seal=True,
        runaway_threshold=10,
        max_attempts_per_task=12,
    )
    print(result)

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

