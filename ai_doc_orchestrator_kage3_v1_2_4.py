# ai_doc_orchestrator_kage3_v1_2_4.py (v1.2.4)
# -*- coding: utf-8 -*-
"""
(ai_doc_orchestrator_kage3_v1_2_2.py に対する設計寄り改修 + IEP寄せ + HITL分岐)

Changes (design-oriented + IEP-aligned):
- AuditLog gains start_run(truncate=...) to control log lifecycle per run.
- AuditLog owns ts_state (monotonic timestamp) instead of module-global _LAST_TS.
- Defensive JSON serialization: default=str so audit never crashes on non-JSON types.
- Deep redaction also redacts dict keys (prevents email-like keys from persisting).
- emit() auto-fills "ts" if missing.
- Decision vocabulary aligned (gates/audit): RUN / PAUSE_FOR_HITL / STOPPED
- ARL minimal keys always emitted: sealed, overrideable, final_decider
- HITL branching implemented as a fixed firepoint:
  HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> downstream events branch.
- Optional RFL gate stub (prompt-based) placed per fixed order:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Compatibility note:
- This module supports `overall_policy`:
    * "legacy": overall is "RUN" if all tasks RUN else "HITL"
    * "iep" (default): overall is STOPPED if any STOPPED else
      PAUSE_FOR_HITL if any pause else RUN
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
OverallPolicy = Literal["legacy", "iep"]
OverallDecision = Literal["RUN", "HITL", "PAUSE_FOR_HITL", "STOPPED"]
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
        return {redact_sensitive(str(k)): _deep_redact(v) for k, v in obj.items()}
    return obj


@dataclass
class AuditLog:
    audit_path: Path
    _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)

    def start_run(self, *, truncate: bool = False) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            with self.audit_path.open("w", encoding="utf-8"):
                pass
        self._last_ts = None

    def ts(self) -> str:
        now = datetime.now(JST)
        if self._last_ts is not None and now <= self._last_ts:
            now = self._last_ts + timedelta(microseconds=1)
        self._last_ts = now
        return now.isoformat(timespec="microseconds")

    def emit(self, row: Dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        if "ts" not in row:
            row = dict(row)
            row["ts"] = self.ts()

        safe_row = json.loads(json.dumps(row, ensure_ascii=False, default=str))
        safe_blob = json.dumps(safe_row, ensure_ascii=False)

        if EMAIL_RE.search(safe_blob):
            safe_row = _deep_redact(safe_row)

        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe_row, ensure_ascii=False) + "\n")


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
        "decision": "RUN",
        "reason_code": reason_code,
        **_arl_base(sealed=False, overrideable=False, final_decider="SYSTEM"),
    }
    if extra:
        row.update(extra)
    audit.emit(row)


def _hitl_fire_and_decide(
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
            **_arl_base(sealed=False, overrideable=True, final_decider="SYSTEM"),
        }
    )

    choice: HitlChoice = "STOP" if hitl_resolver is None else hitl_resolver(
        run_id, task_id, layer, reason_code
    )

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
    p = prompt or ""
    if any(t in p for t in _RFL_TRIGGERS):
        return "PAUSE_FOR_HITL", "rfl", "REL_BOUNDARY_UNSTABLE"
    return "RUN", None, "REL_OK"


def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(raw_text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


def _acc_gate(_: str) -> Tuple[Decision, Optional[Layer], str]:
    return "RUN", None, "ACC_OK"


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
    overall_policy: OverallPolicy = "iep",
) -> SimulationResult:
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

        m_dec, _, m_code = _meaning_gate(prompt, kind)
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
                **_arl_base(
                    sealed=False,
                    overrideable=(c_dec == "PAUSE_FOR_HITL"),
                    final_decider="SYSTEM",
                ),
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

        r_dec, _, r_code = _rfl_gate(prompt)
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
                    sealed=bool(pii_hit),
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


def interactive_hitl_resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> HitlChoice:
    q = (
        f"[HITL] run_id={run_id} task_id={task_id} "
        f"layer={layer} reason={reason_code} -> (c=CONTINUE / s=STOP): "
    )
    for _ in range(5):
        ans = input(q).strip().lower()
        if ans in ("c", "continue"):
            return "CONTINUE"
        if ans in ("s", "stop"):
            return "STOP"
        print("Invalid input. Please enter 'c' or 's'.")
    return "STOP"


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


if __name__ == "__main__":
    result = run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        run_id="RUN#LOCAL",
        audit_path="out/audit_v1_2_4.jsonl",
        artifact_dir="out/artifacts_v1_2_4",
        truncate_audit_on_start=True,
        hitl_resolver=interactive_hitl_resolver,
        overall_policy="iep",
    )
    print(result)
