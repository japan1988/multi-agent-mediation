# ai_doc_orchestrator_kage3_v1_2_4.py (v1.2.4) ※ファイル名は維持でもOK
# -*- coding: utf-8 -*-
"""
(ai_doc_orchestrator_kage3_v1_2_2.py に対する設計寄り改修 + IEP寄せ + HITL分岐)

Changes (design-oriented + IEP-aligned):
- AuditLog gains start_run(truncate=...) to control log lifecycle per run.
- AuditLog owns ts_state (monotonic timestamp) instead of module-global _LAST_TS.
- Defensive JSON serialization: default=str so audit never crashes on non-JSON types.
- Deep redaction also redacts dict keys (prevents email-like keys from persisting).
- emit() auto-fills "ts" if missing.
- Decision vocabulary aligned: RUN / PAUSE_FOR_HITL / STOPPED
- ARL minimal keys always emitted: sealed, overrideable, final_decider
- HITL branching implemented as a fixed firepoint:
  HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> downstream events branch.
- Optional RFL gate stub (prompt-based) placed per fixed order:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch
- RFL relcode branching (KAGE v1.7-IEP):
  REL_BOUNDARY_UNSTABLE / REL_REF_MISSING / REL_SYMMETRY_BREAK
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

# IEP-aligned decisions
Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]

# IEP-aligned final decider
FinalDecider = Literal["SYSTEM", "USER"]

# Layers (expanded)
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


def _emit_info(
    *,
    audit: AuditLog,
    run_id: str,
    task_id: str,
    event: str,
    layer: Layer,
    reason_code: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "event": event,
        "layer": layer,
        "decision": "RUN",  # informational events keep ARL-minimal key presence
        "reason_code": reason_code,
        **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
    }
    if extra:
        row.update(extra)
    audit.emit(row)


# -----------------------------
# HITL firepoint (branch point)
# -----------------------------
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
# RFL (Relativity Filter) - prompt-based stub with relcode branching
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

_RFL_CRITERIA_HINTS = [
    # 基準/目的/制約ヒント
    "目的",
    "用途",
    "要件",
    "条件",
    "前提",
    "制約",
    "基準",
    "優先",
    "重視",
    "予算",
    "コスト",
    "価格",
    "金額",
    "期限",
    "納期",
    "締切",
    "スケジュール",
    "性能",
    "速度",
    "品質",
    "安全",
    "リスク",
    "互換",
    "運用",
    # EN minimal
    "goal",
    "purpose",
    "use case",
    "requirements",
    "constraints",
    "criteria",
    "priority",
    "budget",
    "cost",
    "deadline",
    "quality",
    "risk",
]

_RFL_STEER_HINTS = [
    # 誘導/決め打ち（対称性破れ）
    "一択",
    "絶対",
    "確実",
    "で決まり",
    "にして",
    "の方がいいよね",
    "が正解",
    "bにして",
    "bがいい",
    "bのほう",
    # EN minimal
    "obviously",
    "clearly",
    "must be",
    "definitely",
]


def _rfl_gate(prompt: str) -> Tuple[Decision, Optional[Layer], str]:
    """
    RFL (Relativity Filter):
    - Detects relative/subjective boundary prompts and escalates to HITL without sealing.
    - Branches reason_code:
      - REL_SYMMETRY_BREAK: leading/steering phrasing detected
      - REL_REF_MISSING: comparative question without criteria/constraints
      - REL_BOUNDARY_UNSTABLE: default relative boundary case
    """
    p = prompt or ""
    pl = p.lower()

    if any(t in p for t in _RFL_TRIGGERS):
        if any(t in pl for t in _RFL_STEER_HINTS):
            return "PAUSE_FOR_HITL", "rfl", "REL_SYMMETRY_BREAK"
        if not any(t in pl for t in _RFL_CRITERIA_HINTS):
            return "PAUSE_FOR_HITL", "rfl", "REL_REF_MISSING"
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
# ACC gate (placeholder; non-sealing in this prototype)
# -----------------------------
def _acc_gate(_: str) -> Tuple[Decision, Optional[Layer], str]:
    # Placeholder: keep ordering compatibility; does not seal
    return "RUN", None, "ACC_OK"


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
    """
    truncate_audit_on_start:
    - True: start_run(truncate=True) で run ごとに監査ログを初期化
    - False: append 継続（従来互換。ただし ts_state は run ごとにリセット）
    hitl_resolver:
    - (run_id, task_id, layer, reason_code) -> "CONTINUE" or "STOP"
    - None の場合は fail-closed で STOP
    """
    faults = faults or {}

    audit = AuditLog(Path(audit_path))
    audit.start_run(truncate=truncate_audit_on_start)
    out_dir = Path(artifact_dir)

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
            extra={"preview": safe_text[:200]},
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

            # CONTINUE:
            # In this prototype, contract mismatch still cannot produce a valid artifact.
            # We log regen requests and keep the task as PAUSE_FOR_HITL (pending human-driven regen loop).
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
            # CONTINUE -> proceed

        # -----------------
        # Ethics gate (sealed on violation)
        # -----------------
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
                # Ethics violation is sealed (non-overrideable)
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

        # -----------------
        # ACC gate (placeholder)
        # -----------------
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
            # In this prototype, ACC does not seal; treat as HITL if introduced later.
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
        if ans in ("c", "continue"):
            return "CONTINUE"
        if ans in ("s", "stop"):
            return "STOP"
        print("Invalid input. Please enter 'c' or 's'.")
    return "STOP"  # fail-closed


__all__ = [
    "EMAIL_RE",
    "run_simulation",
    "AuditLog",
    "SimulationResult",
    "TaskResult",
    "HitlResolver",
    "interactive_hitl_resolver",
    "redact_sensitive",
]


# -----------------------------
# Reference: review_result (NOT used by runtime)
# - Keep as a python object for inspection/export
# -----------------------------
REVIEW_RESULT_EXAMPLE: Dict[str, Any] = {
    "meta": {
        "review_target": "ai_doc_orchestrator_kage3_v1_2_3.py",
        "version": "1.2.3",
        "mode": {"STRICT": False},
        "rulebook": {
            "banned_phrases_yml": "unavailable_in_this_session",
            "dev_terms_yml": "unavailable_in_this_session",
            "red_flags_yml": "unavailable_in_this_session",
            "note": "辞書ファイルを参照できないため、ルールIDは本レビュー内の暫定IDで付与",
        },
    },
    "gate_progress": {
        "stage_1_purpose_scope": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S1-001",
                    "type": "scope_gap",
                    "statement": "目的(PIIを永続化しない)は明確だが、対象PIIの定義がメールアドレスのみ。",
                    "evidence": ["EMAIL_RE のみで検出/マスク", "_ethics_detect_pii は EMAIL_RE のみ"],
                    "impact": "メール以外(電話番号、住所、氏名、社員ID等)が監査ログ/成果物に残る可能性。",
                },
                {
                    "id": "S1-002",
                    "type": "non_goal_missing",
                    "statement": "並行実行/複数プロセス同時書き込みの非目標・制約が未記載。",
                    "evidence": [
                        "AuditLog.emit はファイルロックなしで追記",
                        "start_run(truncate=True) は同一パス共有時に他Runを破壊可能",
                    ],
                    "impact": "監査ログ欠損、相互上書き、法務監査の完全性毀損。",
                },
            ],
        },
        "stage_2_requirements_constraints": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S2-001",
                    "type": "contract_incomplete",
                    "statement": "Excel契約検証が 'columns' と 'rows' の型検証のみで、列名と行キー整合が未検証。",
                    "evidence": ["_validate_contract(excel) は rows の各dictキー検証なし"],
                    "impact": "後段(実ファイル生成や集計)でKeyError/欠損列が発生しうる。",
                },
                {
                    "id": "S2-002",
                    "type": "artifact_format_mismatch",
                    "statement": "成果物拡張子が xlsx/docx/pptx を名乗るが、実体は .txt。",
                    "evidence": ['_write_artifact: f"{task_id}.{_artifact_ext(kind)}.txt"'],
                    "impact": "利用者・後続処理が誤認し、誤処理/取り込み失敗を誘発。",
                },
            ],
        },
        "stage_3_design_specifics": {
            "status": "PASS_WITH_ISSUES",
            "findings": [
                {
                    "id": "S3-001",
                    "type": "log_integrity_risk",
                    "statement": "start_run(truncate=True) が同一 audit_path を共有する複数runで破壊的。",
                    "evidence": ["truncate=True で open('w') により全消去"],
                    "impact": "他runのログ消失(監査証跡の不可逆破壊)。",
                },
                {
                    "id": "S3-002",
                    "type": "pii_detection_gap",
                    "statement": "Ethics gateは raw_text でのみ検出し、draft(構造データ)内のPIIを未検出。",
                    "evidence": ["_ethics_detect_pii(raw_text) のみ", "draft は検査対象外"],
                    "impact": "draft→safe_text化の過程を変えると、構造側PIIが成果物に混入し得る。",
                },
                {
                    "id": "S3-003",
                    "type": "meaning_gate_overproduction",
                    "statement": "promptにkind言及が無い場合、3タスクすべてRUNになり成果物が過剰生成される。",
                    "evidence": ["if not any_kind: return RUN for all kinds"],
                    "impact": "ユーザー意図とズレた成果物生成(情報最小化に反する運用になりやすい)。",
                },
            ],
        },
        "stage_4_verification_threats": {
            "status": "FAIL",
            "findings": [
                {
                    "id": "S4-001",
                    "type": "missing_tests",
                    "statement": "境界/異常/並行/回帰テスト観点がコード内にも仕様にも具体化されていない。",
                    "impact": "PII非永続の保証・ログ完全性の保証が設計主張に留まる。",
                }
            ],
        },
    },
    "overall_assessment": {
        "decision": "HITL",
        "pass_rate_estimate": {
            "value": 0.62,
            "basis": [
                "PII対策(メール)は強いが範囲が狭い",
                "ログ完全性(truncate/並行)が未封止",
                "契約検証が浅い",
                "拡張子偽装(実体txt)が運用事故を誘発",
            ],
        },
    },
}

if __name__ == "__main__":
    # Minimal local smoke run (manual HITL)
    result = run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        run_id="RUN#LOCAL",
        audit_path="out/audit_v1_2_4.jsonl",
        artifact_dir="out/artifacts_v1_2_4",
        truncate_audit_on_start=True,
        hitl_resolver=interactive_hitl_resolver,
    )
    print(result)

    # If you want JSON for review_result:
    # print(json.dumps(REVIEW_RESULT_EXAMPLE, ensure_ascii=False, indent=2))
