# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_2_2.py  (implemented as v1.2.4 semantics)

Design goals (IEP-aligned):
- Pipeline: Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH
- Fail-closed: unsafe/unstable never silently RUN.
- RFL never seals; it escalates to HITL (human-in-the-loop).
- HITL events:
    HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
- ARL minimal keys on every audit row:
    run_id, layer, decision, sealed, overrideable, final_decider, reason_code

Decision vocabulary:
- RUN / PAUSE_FOR_HITL / STOPPED

Notes:
- "Hard guarantee": audit JSONL must not persist email-like strings nor "@".
- Artifacts are written from safe_text only (PII redacted).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

__version__ = "1.2.4"

# ===== Timezone =====
JST = timezone(timedelta(hours=9))

# ===== Patterns =====
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
Layer = Literal[
    "meaning",
    "consistency",
    "rfl",
    "ethics",
    "acc",
    "dispatch",
    "orchestrator",
    "agent",
    "hitl_finalize",
]

KIND = Literal["excel", "word", "ppt"]
HITLAction = Literal["CONTINUE", "STOP"]

FINAL_DECIDER_SYSTEM = "SYSTEM"
FINAL_DECIDER_USER = "USER"

# ===== Tasks =====
_TASKS: List[Tuple[str, KIND]] = [
    ("t_excel", "excel"),
    ("t_word", "word"),
    ("t_ppt", "ppt"),
]

_KIND_TOKENS: Dict[KIND, List[str]] = {
    "excel": ["excel", "xlsx", "spreadsheet", "sheet", "表", "スプレッドシート", "エクセル"],
    "word": ["word", "docx", "document", "文章", "ドキュメント", "ワード"],
    "ppt": ["ppt", "pptx", "powerpoint", "slide", "slides", "スライド", "パワポ"],
}


# -----------------------------
# Redaction (PII must not persist)
# -----------------------------
def redact_sensitive(text: str) -> str:
    """
    Replace email-like strings. Conservative redaction for persistence safety.
    """
    if not text:
        return text
    return EMAIL_RE.sub("[REDACTED_EMAIL]", text)


def _redact_key_if_needed(key: str) -> str:
    # Hard invariant: never persist "@"
    if "@" in key or EMAIL_RE.search(key):
        return "[REDACTED_KEY]"
    return key


def _deep_redact(obj: Any) -> Any:
    """
    Deep-redact values AND dict keys, ensuring no "@" leaks through keys.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        s = redact_sensitive(obj)
        # Last-ditch: kill any remaining "@"
        return s.replace("@", "[AT]")
    if isinstance(obj, list):
        return [_deep_redact(x) for x in obj]
    if isinstance(obj, tuple):
        return [_deep_redact(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            ks = _redact_key_if_needed(ks)
            out[ks] = _deep_redact(v)
        return out
    # keep other types; JSON serialization will coerce via default=str later
    return obj


# -----------------------------
# Audit Log
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, *, truncate: bool = False) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            self.audit_path.write_text("", encoding="utf-8")
        self._last_ts = None

    def ts(self) -> str:
        """
        Monotonic-ish timestamp string (JST) to keep ordering stable.
        """
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(milliseconds=1)
        self._last_ts = now
        return now.isoformat()

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a JSONL row.
        Hard guarantee: no email-like strings are persisted (values or keys).
        Also: never crash on non-JSON-serializable types (default=str).
        """
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        # auto-fill ts if missing
        base = dict(row)
        if "ts" not in base:
            base["ts"] = self.ts()

        # Enforce ARL minimal keys on every row (fail-closed: never omit)
        base.setdefault("sealed", False)
        base.setdefault("overrideable", True)
        base.setdefault("final_decider", FINAL_DECIDER_SYSTEM)
        base.setdefault("reason_code", "")
        base.setdefault("layer", "orchestrator")
        base.setdefault("decision", "RUN")

        # Deep redact (keys + values), then JSON coerce
        redacted = _deep_redact(base)
        safe_row = json.loads(json.dumps(redacted, ensure_ascii=False, default=str))
        safe_blob = json.dumps(safe_row, ensure_ascii=False)

        # Absolute last-ditch guarantee
        safe_blob = redact_sensitive(safe_blob).replace("@", "[AT]")

        # Write
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(safe_blob + "\n")


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
# Gates
# -----------------------------
def _prompt_mentions_any_kind(prompt: str) -> bool:
    pl = (prompt or "").lower()
    for toks in _KIND_TOKENS.values():
        if any(t.lower() in pl for t in toks):
            return True
    return False


def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[Layer], str]:
    p = (prompt or "")
    pl = p.lower()
    any_kind = _prompt_mentions_any_kind(p)

    if not any_kind:
        return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"

    tokens = _KIND_TOKENS[kind]
    if any(t.lower() in pl for t in tokens):
        return "RUN", None, "MEANING_KIND_MATCH"

    return "PAUSE_FOR_HITL", "meaning", "MEANING_KIND_MISSING"


def _validate_contract(kind: KIND, draft: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Very small, explicit schemas to keep tests deterministic.
    """
    if kind == "excel":
        cells = draft.get("cells")
        if isinstance(cells, list) and all(isinstance(x, dict) for x in cells):
            return True, "CONTRACT_OK"
        return False, "CONTRACT_EXCEL_INVALID"

    if kind == "word":
        paras = draft.get("paragraphs")
        if isinstance(paras, list) and all(isinstance(x, str) for x in paras):
            return True, "CONTRACT_OK"
        return False, "CONTRACT_WORD_INVALID"

    if kind == "ppt":
        slides = draft.get("slides")
        if isinstance(slides, list) and all(isinstance(x, dict) for x in slides):
            return True, "CONTRACT_OK"
        return False, "CONTRACT_PPT_INVALID"

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

    # REL_SYMMETRY_BREAK: prompt mentions exactly one kind but current task differs
    kinds_mentioned: List[KIND] = []
    for k, toks in _KIND_TOKENS.items():
        if any(t.lower() in pl for t in toks):
            kinds_mentioned.append(k)
    if len(set(kinds_mentioned)) == 1 and kind not in set(kinds_mentioned):
        return "PAUSE_FOR_HITL", "rfl", "REL_SYMMETRY_BREAK"

    return "RUN", None, "RFL_OK"


def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(raw_text or ""):
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
    - Sealing is allowed here (STOPPED) if unsafe to write artifacts.
    """
    if not contract_ok:
        return "STOPPED", "acc", "ACC_CONTRACT_INVALID"

    # safe_text must not contain email-like tokens.
    if EMAIL_RE.search(safe_text or ""):
        return "STOPPED", "acc", "ACC_PII_REMAINED"

    # Path traversal guard: ensure resolved path stays under artifact_dir.
    ext = _artifact_ext(kind)
    candidate = (artifact_dir / f"{task_id}.{ext}.txt").resolve()
    base = artifact_dir.resolve()
    if candidate != base and base not in candidate.parents:
        return "STOPPED", "acc", "ACC_PATH_TRAVERSAL"

    return "RUN", None, "ACC_OK"


def _write_artifact(artifact_dir: Path, task_id: str, kind: KIND, safe_text: str) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
    path.write_text(redact_sensitive(safe_text).replace("@", "[AT]"), encoding="utf-8")
    return path


# -----------------------------
# Agent (toy generator for tests)
# -----------------------------
def _agent_generate(
    prompt: str,
    kind: KIND,
    faults: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, str]:
    """
    Returns:
      draft: contract-checked structure
      raw_text: may contain PII for ethics test
      safe_text: redacted string for logging/artifact
    """
    base_text = f"Generated content for {kind}. prompt={prompt[:60]!r}"

    # Fault injection knobs (optional)
    inject_pii = bool(faults.get("inject_pii"))
    break_schema = bool(faults.get("break_schema"))

    raw_text = base_text
    if inject_pii:
        raw_text += " contact: user@example.com"

    safe_text = redact_sensitive(raw_text).replace("@", "[AT]")

    if break_schema:
        # deliberately invalid
        return {"oops": True}, raw_text, safe_text

    if kind == "excel":
        draft = {"cells": [{"row": 1, "col": 1, "value": "Hello"}]}
    elif kind == "word":
        draft = {"paragraphs": ["Hello", "World"]}
    else:
        draft = {"slides": [{"title": "Hello", "bullets": ["World"]}]}

    return draft, raw_text, safe_text


# -----------------------------
# Simulation
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
    faults: per-kind fault injection dict, e.g.:
      {
        "excel": {"inject_pii": True},
        "ppt": {"break_schema": True},
      }
    hitl_actions: per-task_id HITL action override, e.g. {"t_excel": "CONTINUE"}
    """
    faults = faults or {}
    hitl_actions = hitl_actions or {}

    audit = AuditLog(Path(audit_path))
    audit.start_run(truncate=truncate_audit_on_start)

    out_dir = Path(artifact_dir)
    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    def _hitl_resolve(task_id: str, *, gate_layer: Layer, reason_code: str) -> HITLAction:
        # Request (SYSTEM)
        audit.emit(
            {
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
            }
        )

        action: HITLAction = hitl_actions.get(task_id, hitl_default)

        # Decision (USER)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "HITL_DECIDED",
                "layer": "hitl_finalize",
                "decision": "RUN" if action == "CONTINUE" else "STOPPED",
                "sealed": False,  # HITL itself is not sealing
                "overrideable": False,
                "final_decider": FINAL_DECIDER_USER,
                "reason_code": "HITL_CONTINUE" if action == "CONTINUE" else "HITL_STOP",
                "blocked_layer": gate_layer,
            }
        )
        return action

    for task_id, kind in _TASKS:
        audit.emit(
            {
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
            }
        )

        # ---- Meaning gate ----
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
                "overrideable": (m_dec == "PAUSE_FOR_HITL"),
                "final_decider": FINAL_DECIDER_SYSTEM,
            }
        )

        if m_dec == "PAUSE_FOR_HITL":
            action = _hitl_resolve(task_id, gate_layer="meaning", reason_code=m_code)
            if action == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "PAUSE_FOR_HITL",
                        "sealed": False,
                        "overrideable": True,
                        "final_decider": FINAL_DECIDER_SYSTEM,
                        "reason_code": m_code,
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="PAUSE_FOR_HITL",
                        blocked_layer="meaning",
                        reason_code=m_code,
                        artifact_path=None,
                    )
                )
                continue
            # CONTINUE -> proceed

        # ---- Agent output ----
        draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "AGENT_OUTPUT",
                "layer": "agent",
                "preview": safe_text[:200],
                "decision": "RUN",
                "sealed": False,
                "overrideable": True,
                "final_decider": FINAL_DECIDER_SYSTEM,
                "reason_code": "AGENT_OUTPUT_SAFE_PREVIEW",
            }
        )

        # ---- Consistency gate ----
        contract_ok, c_code = _validate_contract(kind, draft)
        c_dec: Decision = "RUN" if contract_ok else "PAUSE_FOR_HITL"
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_CONSISTENCY",
                "layer": "consistency",
                "decision": c_dec,
                "reason_code": c_code,
                "sealed": False,
                "overrideable": (c_dec == "PAUSE_FOR_HITL"),
                "final_decider": FINAL_DECIDER_SYSTEM,
            }
        )

        if not contract_ok:
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
                    "final_decider": FINAL_DECIDER_SYSTEM,
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
                    "final_decider": FINAL_DECIDER_SYSTEM,
                }
            )

            action = _hitl_resolve(task_id, gate_layer="consistency", reason_code=c_code)
            if action == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "PAUSE_FOR_HITL",
                        "sealed": False,
                        "overrideable": True,
                        "final_decider": FINAL_DECIDER_SYSTEM,
                        "reason_code": c_code,
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
            # CONTINUE -> proceed, but ACC will STOPPED due to contract invalid

        # ---- RFL gate (never seals) ----
        r_dec, r_layer, r_code = _rfl_gate(prompt, kind, draft)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_RFL",
                "layer": "rfl",
                "decision": r_dec,
                "reason_code": r_code,
                "sealed": False,
                "overrideable": (r_dec == "PAUSE_FOR_HITL"),
                "final_decider": FINAL_DECIDER_SYSTEM,
            }
        )

        if r_dec == "PAUSE_FOR_HITL":
            action = _hitl_resolve(task_id, gate_layer="rfl", reason_code=r_code)
            if action == "STOP":
                audit.emit(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "event": "ARTIFACT_SKIPPED",
                        "layer": "orchestrator",
                        "decision": "PAUSE_FOR_HITL",
                        "sealed": False,
                        "overrideable": True,
                        "final_decider": FINAL_DECIDER_SYSTEM,
                        "reason_code": r_code,
                    }
                )
                task_results.append(
                    TaskResult(
                        task_id=task_id,
                        kind=kind,
                        decision="PAUSE_FOR_HITL",
                        blocked_layer="rfl",
                        reason_code=r_code,
                        artifact_path=None,
                    )
                )
                continue
            # CONTINUE -> proceed

        # ---- Ethics gate (can seal) ----
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
                "sealed": bool(pii_hit),
                "overrideable": False if pii_hit else True,
                "final_decider": FINAL_DECIDER_SYSTEM,
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
                    "final_decider": FINAL_DECIDER_SYSTEM,
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

        # ---- ACC gate (can seal) ----
        a_dec, a_layer, a_code = _acc_gate(
            kind=kind,
            safe_text=safe_text,
            contract_ok=contract_ok,
            artifact_dir=out_dir,
            task_id=task_id,
        )
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "GATE_ACC",
                "layer": "acc",
                "decision": a_dec,
                "reason_code": a_code,
                "sealed": (a_dec == "STOPPED"),
                "overrideable": False if a_dec == "STOPPED" else True,
                "final_decider": FINAL_DECIDER_SYSTEM,
            }
        )
        if a_dec == "STOPPED":
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "ARTIFACT_SKIPPED",
                    "layer": "acc",
                    "decision": "STOPPED",
                    "sealed": True,
                    "overrideable": False,
                    "final_decider": FINAL_DECIDER_SYSTEM,
                    "reason_code": a_code,
                }
            )
            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="STOPPED",
                    blocked_layer="acc",
                    reason_code=a_code,
                    artifact_path=None,
                )
            )
            continue

        # ---- DISPATCH ----
        artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "DISPATCHED",
                "layer": "dispatch",
                "decision": "RUN",
                "artifact_path": str(artifact_path),
                "sealed": False,
                "overrideable": True,
                "final_decider": FINAL_DECIDER_SYSTEM,
                "reason_code": "DISPATCH_OK",
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

    # Overall decision
    if any(t.decision == "STOPPED" for t in task_results):
        overall: OverallDecision = "STOPPED"
    elif all(t.decision == "RUN" for t in task_results):
        overall = "RUN"
    else:
        overall = "PAUSE_FOR_HITL"

    audit.emit(
        {
            "run_id": run_id,
            "event": "RUN_SUMMARY",
            "layer": "orchestrator",
            "decision": overall,
            "sealed": False,
            "overrideable": False,
            "final_decider": FINAL_DECIDER_SYSTEM,
            "reason_code": "RUN_COMPLETE",
            "artifacts_written_task_ids": list(artifacts_written),
        }
    )

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

