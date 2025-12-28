# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_with_mediator_v1_0.py  (final)

Agent -> Mediator -> Orchestrator pipeline (research simulator)

KAGE-ish gates fixed order:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH

Invariants:
- Mediator has NO execution authority: returns only RUN or PAUSE_FOR_HITL (never STOPPED).
- Orchestrator always evaluates gates in fixed order (no early return based on Mediator).
- sealed=True may appear ONLY at Ethics/ACC.
- raw_text must NEVER be persisted.
- logs must NEVER contain '@' (hard fail-closed redaction).

Outputs:
- JSONL audit log (ARL-min + safe context)

Run:
  python ai_doc_orchestrator_with_mediator_v1_0.py
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

# ----------------------------
# Time / types
# ----------------------------

JST = timezone(timedelta(hours=9))

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]

# ----------------------------
# Patterns
# ----------------------------

EMAIL_LIKE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_LIKE = re.compile(r"\b(?:\+?\d{1,3}[- ]?)?(?:\d{2,4}[- ]?)?\d{2,4}[- ]?\d{3,4}\b")


# External side-effect intents (EN + JA)
EXTERNAL_SIDE_EFFECT_HINTS = re.compile(
    r"\b(send|email|dm|upload|post|publish|payment|buy|purchase|execute|run command|shell)\b"
    r"|"
    r"(メール|送って|送信|送付|投稿|公開|アップロード|支払い|購入|決済|実行|コマンド|シェル)",
    re.IGNORECASE,
)

# Relativity / subjective / underspecified terms (RFL)
RELATIVE_TERMS = re.compile(
    r"(いい感じ|適当|よしなに|なるべく|できるだけ|最適|最善|うまく|良い感じ|asap|best|optimal|nicely)",
    re.IGNORECASE,
)

# --- FAIL-CLOSED '@' ban (hard invariant) ---
_AT_FORBIDDEN = re.compile(r"@")

# ----------------------------
# Helpers
# ----------------------------

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def _pii_like(s: str) -> bool:
    return bool(EMAIL_LIKE.search(s) or PHONE_LIKE.search(s))


def _contains_external_side_effect_request(s: str) -> bool:
    return bool(EXTERNAL_SIDE_EFFECT_HINTS.search(s))


def _rfl_hit(s: str) -> bool:
    return bool(RELATIVE_TERMS.search(s))


def _redact_email_like(s: str) -> str:
    # Hard fail-closed: if it contains '@' at all, redact
    if _AT_FORBIDDEN.search(s):
        return "[REDACTED]"
    return s


def _build_artifact_preview(spec: Dict[str, Any]) -> str:
    return _redact_email_like(json.dumps(spec, ensure_ascii=False)[:240])


# Decision precedence: STOPPED(sealed only) > PAUSE_FOR_HITL > RUN
_DECISION_RANK = {"RUN": 0, "PAUSE_FOR_HITL": 1, "STOPPED": 2}


def _pick_stronger(curr: Tuple[Decision, str], cand: Tuple[Decision, str]) -> Tuple[Decision, str]:
    if _DECISION_RANK[cand[0]] > _DECISION_RANK[curr[0]]:
        return cand
    return curr


# ----------------------------
# Data models
# ----------------------------

@dataclass
class Task:
    task_id: str
    kind: Literal["xlsx", "pptx"]
    prompt: str


@dataclass
class AgentProposal:
    task_id: str
    kind: str
    spec: Dict[str, Any]
    raw_text: str  # may contain PII; MUST NOT be persisted


@dataclass
class MediatorReview:
    task_id: str
    decision: Literal["RUN", "PAUSE_FOR_HITL"]  # mediator never STOPPED
    reason_code: str
    revised_spec: Optional[Dict[str, Any]] = None
    safe_preview: str = ""


@dataclass
class OrchestratorResult:
    task_id: str
    decision: Decision
    reason_code: str
    artifact_preview: str = ""


@dataclass
class ARLEvent:
    # Minimal required keys:
    run_id: str
    layer: str
    decision: str
    sealed: bool
    overrideable: bool
    final_decider: str
    reason_code: str
    # Extra safe context:
    ts: str = ""
    session_id: str = ""
    task_id: str = ""
    kind: str = ""
    prompt_sha256: str = ""


class AuditLog:
    """
    JSONL audit writer with safety guards:
    - Never persists raw_text.
    - Never persists any '@' character (hard invariant).
    """

    def __init__(self, log_path: str):
        self.log_path = log_path

    def emit(self, event: Dict[str, Any]) -> None:
        safe = self._sanitize_event(event)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")

    def _sanitize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        def walk(x: Any) -> Any:
            if isinstance(x, str):
                # fail-closed: no '@' anywhere in logs
                if _AT_FORBIDDEN.search(x) or EMAIL_LIKE.search(x):
                    return "[REDACTED]"
                return x
            if isinstance(x, list):
                return [walk(v) for v in x]
            if isinstance(x, dict):
                out: Dict[str, Any] = {}
                for k, v in x.items():
                    if str(k).lower() in ("raw_text", "raw", "prompt_raw"):
                        out[k] = "[REDACTED]"
                    else:
                        out[k] = walk(v)
                return out
            return x

        return walk(event)


# ----------------------------
# Agent stub
# ----------------------------

def agent_generate(task: Task) -> AgentProposal:
    if task.kind == "xlsx":
        spec = {
            "format": "xlsx",
            "sheet_name": "Summary",
            "rows": [
                ["Title", "Value"],
                ["Project", "multi-agent-mediation"],
                ["Task", task.prompt[:60]],
            ],
        }
        raw_text = "Generated XLSX spec."
    else:
        spec = {
            "format": "pptx",
            "slides": [
                {"title": "Overview", "bullets": ["Purpose", task.prompt[:80]]},
                {"title": "Plan", "bullets": ["Step 1", "Step 2", "Step 3"]},
            ],
        }
        raw_text = "Generated PPTX spec."
    return AgentProposal(task_id=task.task_id, kind=task.kind, spec=spec, raw_text=raw_text)


# ----------------------------
# Mediator (NO STOPPED)
# ----------------------------

def mediator_review(task: Task, proposal: AgentProposal) -> MediatorReview:
    """
    Mediator:
    - normalize / mitigate / escalate only
    - never decides STOPPED (no stop authority)
    """

    # External side effects -> HITL
    if _contains_external_side_effect_request(task.prompt):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_EXTERNAL_SIDE_EFFECT_AMBIGUOUS",
            safe_preview="Prompt suggests external side effects; escalate to HITL.",
        )

    # Relativity terms -> HITL
    if _rfl_hit(task.prompt):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_REL_BOUNDARY_UNSTABLE",
            safe_preview="Relativity terms detected; request clarification via HITL.",
        )

    # PII-like -> HITL (do NOT stop here)
    if _pii_like(task.prompt) or _pii_like(proposal.raw_text):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_PII_LIKE_DETECTED",
            safe_preview="PII-like pattern detected; escalate to HITL.",
        )

    revised = dict(proposal.spec)

    # Minimal schema check
    if proposal.kind == "xlsx":
        if revised.get("format") != "xlsx":
            revised["format"] = "xlsx"
        if "rows" not in revised or not isinstance(revised["rows"], list):
            return MediatorReview(
                task_id=task.task_id,
                decision="PAUSE_FOR_HITL",
                reason_code="MEDIATOR_SCHEMA_UNCLEAR_XLSX",
                safe_preview="XLSX schema missing/invalid rows; escalate.",
            )
    elif proposal.kind == "pptx":
        if revised.get("format") != "pptx":
            revised["format"] = "pptx"
        if "slides" not in revised or not isinstance(revised["slides"], list):
            return MediatorReview(
                task_id=task.task_id,
                decision="PAUSE_FOR_HITL",
                reason_code="MEDIATOR_SCHEMA_UNCLEAR_PPTX",
                safe_preview="PPTX schema missing/invalid slides; escalate.",
            )
    else:
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_UNKNOWN_KIND",
            safe_preview="Unknown kind; escalate to HITL.",
        )

    return MediatorReview(
        task_id=task.task_id,
        decision="RUN",
        reason_code="MEDIATOR_OK",
        revised_spec=revised,
        safe_preview="Mediator OK; forwarding to Orchestrator.",
    )


# ----------------------------
# ARL helpers
# ----------------------------

def _arl_min(
    run_id: str,
    session_id: str,
    task: Task,
    layer: str,
    decision: str,  # <- str to avoid future type wobble
    reason_code: str,
    sealed: bool,
    overrideable: bool,
    final_decider: FinalDecider,
) -> Dict[str, Any]:
    ev = ARLEvent(
        run_id=run_id,
        layer=layer,
        decision=decision,
        sealed=sealed,
        overrideable=overrideable,
        final_decider=final_decider,
        reason_code=reason_code,
        ts=datetime.now(JST).isoformat(),
        session_id=session_id,
        task_id=task.task_id,
        kind=task.kind,
        prompt_sha256=_sha256_text(task.prompt),
    )
    return asdict(ev)


# ----------------------------
# Orchestrator (always runs gates in fixed order)
# ----------------------------

def orchestrator_eval(
    task: Task,
    mediator: MediatorReview,
    run_id: str,
    session_id: str,
    audit: AuditLog,
    hitl_choice: Optional[Literal["STOP", "CONTINUE"]] = None,
) -> OrchestratorResult:
    """
    Always:
      mediator_advice (non-sealing)
      Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch
    Final decision synthesis:
      sealed STOPPED (Ethics/ACC only) > PAUSE_FOR_HITL > RUN
    """

    # 0) Mediator advice logged; never seals and never early-returns.
    audit.emit(
        _arl_min(
            run_id,
            session_id,
            task,
            layer="mediator_advice",
            decision=mediator.decision,
            reason_code=mediator.reason_code,
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
        )
    )

    spec = mediator.revised_spec or {}

    agg: Tuple[Decision, str] = ("RUN", "AGG_INIT")
    if mediator.decision == "PAUSE_FOR_HITL":
        agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", mediator.reason_code))

    # 1) Meaning gate
    if task.kind not in ("xlsx", "pptx"):
        audit.emit(_arl_min(run_id, session_id, task, "meaning_gate", "PAUSE_FOR_HITL", "MEANING_UNKNOWN_KIND", False, True, "SYSTEM"))
        agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "MEANING_UNKNOWN_KIND"))
    else:
        audit.emit(_arl_min(run_id, session_id, task, "meaning_gate", "RUN", "MEANING_PASS", False, False, "SYSTEM"))

    # 2) Consistency gate
    if task.kind == "xlsx":
        ok = (spec.get("format") == "xlsx" and isinstance(spec.get("rows"), list))
        if not ok:
            audit.emit(_arl_min(run_id, session_id, task, "consistency_gate", "PAUSE_FOR_HITL", "CONS_CONTRACT_FAIL_XLSX", False, True, "SYSTEM"))
            agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "CONS_CONTRACT_FAIL_XLSX"))
        else:
            audit.emit(_arl_min(run_id, session_id, task, "consistency_gate", "RUN", "CONS_PASS", False, False, "SYSTEM"))
    elif task.kind == "pptx":
        ok = (spec.get("format") == "pptx" and isinstance(spec.get("slides"), list))
        if not ok:
            audit.emit(_arl_min(run_id, session_id, task, "consistency_gate", "PAUSE_FOR_HITL", "CONS_CONTRACT_FAIL_PPTX", False, True, "SYSTEM"))
            agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "CONS_CONTRACT_FAIL_PPTX"))
        else:
            audit.emit(_arl_min(run_id, session_id, task, "consistency_gate", "RUN", "CONS_PASS", False, False, "SYSTEM"))
    else:
        audit.emit(_arl_min(run_id, session_id, task, "consistency_gate", "PAUSE_FOR_HITL", "CONS_SKIPPED_UNKNOWN_KIND", False, True, "SYSTEM"))
        agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "CONS_SKIPPED_UNKNOWN_KIND"))

    # 3) RFL gate (must not seal)
    if _rfl_hit(task.prompt):
        audit.emit(_arl_min(run_id, session_id, task, "relativity_gate", "PAUSE_FOR_HITL", "REL_BOUNDARY_UNSTABLE", False, True, "SYSTEM"))
        agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "REL_BOUNDARY_UNSTABLE"))
    else:
        audit.emit(_arl_min(run_id, session_id, task, "relativity_gate", "RUN", "REL_PASS", False, False, "SYSTEM"))

    # 4) Ethics gate (CAN seal)
    if _pii_like(task.prompt):
        audit.emit(_arl_min(run_id, session_id, task, "ethics_gate", "STOPPED", "SEALED_BY_ETHICS_PII_LIKE", True, False, "SYSTEM"))
        audit.emit(_arl_min(run_id, session_id, task, "acc_gate", "STOPPED", "ACC_SKIPPED_BY_ETHICS_SEAL", False, False, "SYSTEM"))
        audit.emit(_arl_min(run_id, session_id, task, "dispatch", "STOPPED", "DISPATCH_SKIPPED_BY_ETHICS_SEAL", False, False, "SYSTEM"))
        return OrchestratorResult(task_id=task.task_id, decision="STOPPED", reason_code="SEALED_BY_ETHICS_PII_LIKE")

    audit.emit(_arl_min(run_id, session_id, task, "ethics_gate", "RUN", "ETHICS_PASS", False, False, "SYSTEM"))

    # 5) ACC gate (CAN seal; here we pause on external side-effect requests)
    if _contains_external_side_effect_request(task.prompt):
        audit.emit(_arl_min(run_id, session_id, task, "acc_gate", "PAUSE_FOR_HITL", "ACC_EXTERNAL_SIDE_EFFECT_REQUEST", False, True, "SYSTEM"))
        agg = _pick_stronger(agg, ("PAUSE_FOR_HITL", "ACC_EXTERNAL_SIDE_EFFECT_REQUEST"))
    else:
        audit.emit(_arl_min(run_id, session_id, task, "acc_gate", "RUN", "ACC_PASS", False, False, "SYSTEM"))

    # 6) HITL finalize if needed
    if agg[0] == "PAUSE_FOR_HITL":
        if hitl_choice is None:
            audit.emit(_arl_min(run_id, session_id, task, "hitl_finalize", "PAUSE_FOR_HITL", "HITL_REQUIRED", False, True, "SYSTEM"))
            audit.emit(_arl_min(run_id, session_id, task, "dispatch", "PAUSE_FOR_HITL", "DISPATCH_SKIPPED_BY_HITL_REQUIRED", False, True, "SYSTEM"))
            return OrchestratorResult(task_id=task.task_id, decision="PAUSE_FOR_HITL", reason_code=agg[1])

        if hitl_choice == "STOP":
            audit.emit(_arl_min(run_id, session_id, task, "hitl_finalize", "STOPPED", "HITL_STOP", False, False, "USER"))
            audit.emit(_arl_min(run_id, session_id, task, "dispatch", "STOPPED", "DISPATCH_SKIPPED_BY_HITL_STOP", False, False, "SYSTEM"))
            return OrchestratorResult(task_id=task.task_id, decision="STOPPED", reason_code="HITL_STOP")

        audit.emit(_arl_min(run_id, session_id, task, "hitl_finalize", "RUN", "HITL_CONTINUE", False, False, "USER"))
        preview = _build_artifact_preview(spec)
        audit.emit(_arl_min(run_id, session_id, task, "dispatch", "RUN", "DISPATCH_OK", False, False, "SYSTEM"))
        return OrchestratorResult(task_id=task.task_id, decision="RUN", reason_code="HITL_CONTINUE", artifact_preview=preview)

    # 7) Dispatch
    preview = _build_artifact_preview(spec)
    audit.emit(_arl_min(run_id, session_id, task, "dispatch", "RUN", "DISPATCH_OK", False, False, "SYSTEM"))
    return OrchestratorResult(task_id=task.task_id, decision="RUN", reason_code="ORCH_RUN_OK", artifact_preview=preview)


# ----------------------------
# Pipeline runner
# ----------------------------

def run_pipeline(
    tasks: List[Task],
    run_id: str,
    session_id: str,
    log_path: str,
    hitl_choices: Optional[Dict[str, Literal["STOP", "CONTINUE"]]] = None,
) -> List[OrchestratorResult]:
    audit = AuditLog(log_path=log_path)
    out: List[OrchestratorResult] = []

    for t in tasks:
        proposal = agent_generate(t)
        review = mediator_review(t, proposal)

        choice = hitl_choices.get(t.task_id) if hitl_choices else None

        result = orchestrator_eval(
            task=t,
            mediator=review,
            run_id=run_id,
            session_id=session_id,
            audit=audit,
            hitl_choice=choice,
        )

        # Safe summary (no raw_text, no '@')
        audit.emit(
            {
                "type": "TASK_SUMMARY",
                "ts": datetime.now(JST).isoformat(),
                "run_id": run_id,
                "session_id": session_id,
                "task_id": t.task_id,
                "kind": t.kind,
                "prompt_sha256": _sha256_text(t.prompt),
                "mediator": {
                    "decision": review.decision,
                    "reason_code": review.reason_code,
                    "safe_preview": _redact_email_like(review.safe_preview),
                },
                "orchestrator": {
                    "decision": result.decision,
                    "reason_code": result.reason_code,
                },
            }
        )

        out.append(result)

    return out


if __name__ == "__main__":
    demo_tasks = [
        Task(task_id="T1", kind="xlsx", prompt="売上サマリーを表にして"),
        Task(task_id="T2", kind="pptx", prompt="プロジェクト概要スライドを作って"),
        Task(task_id="T3", kind="pptx", prompt="いい感じにまとめて"),  # RFL -> HITL
        Task(task_id="T4", kind="pptx", prompt="作った資料をメールで送って"),  # ACC -> HITL
        Task(task_id="T5", kind="xlsx", prompt="連絡先は test@example.com に送って"),  # Ethics seal (logged as [REDACTED])
    ]

    results = run_pipeline(
        tasks=demo_tasks,
        run_id="RUN#DEMO",
        session_id="SESSION_CREATOR_1848CC59",
        log_path="audit_mediator_pipeline_v1_0.jsonl",
        hitl_choices={"T3": "STOP", "T4": "CONTINUE"},
    )

    for r in results:
        print(r.task_id, r.decision, r.reason_code)
