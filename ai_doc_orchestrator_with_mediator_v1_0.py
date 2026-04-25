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

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional, Sequence, Union

DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOPPED = "STOPPED"

HITL_UNSPECIFIED = "unspecified"
HITL_CONTINUE = "CONTINUE"
HITL_STOP = "STOP"

KNOWN_KINDS = {"xlsx", "pptx"}

REASON_MEDIATOR_RUN = "MEDIATOR_RUN_OK"
REASON_MEDIATOR_HITL_CONTINUE = "MEDIATOR_HITL_CONTINUE"
REASON_HITL_CONTINUE = "HITL_CONTINUE"
REASON_HITL_STOP = "HITL_STOP_REQUESTED"

REASON_MEANING_OK = "MEANING_OK"
REASON_MEANING_INVALID_KIND = "MEANING_INVALID_KIND"
REASON_MEANING_EMPTY_PROMPT = "MEANING_EMPTY_PROMPT"

REASON_CONSISTENCY_OK = "CONSISTENCY_OK"
REASON_CONSISTENCY_MISMATCH = "CONSISTENCY_KIND_PROMPT_MISMATCH"

REASON_RFL_OK = "RFL_OK"
REASON_RFL_RELATIVE = "RFL_RELATIVE_REQUEST"

REASON_ETHICS_OK = "ETHICS_OK"
REASON_ETHICS_PII = "ETHICS_PII_DETECTED"

REASON_ACC_OK = "ACC_OK"
REASON_ACC_EXTERNAL_SIDE_EFFECT = "ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL"

REASON_DISPATCH_OK = "ORCH_RUN_OK"
REASON_HITL_WAIT = "HITL_UNSPECIFIED_WAIT"

LAYER_MEDIATOR = "mediator_advice"
LAYER_MEANING = "meaning_gate"
LAYER_CONSISTENCY = "consistency_gate"
LAYER_RFL = "relativity_gate"
LAYER_HITL = "hitl_finalize"
LAYER_ETHICS = "ethics_gate"
LAYER_ACC = "acc_gate"
LAYER_DISPATCH = "dispatch"

RFL_PATTERNS = (
    r"いい感じ",
    r"\bbest\b",
    r"おまかせ",
)

SPREADSHEET_PATTERNS = (
    r"表",
    r"表計算",
    r"集計",
    r"サマリー",
    r"一覧",
    r"csv",
    r"excel",
    r"xlsx",
)

SLIDE_PATTERNS = (
    r"スライド",
    r"発表",
    r"プレゼン",
    r"ppt",
    r"pptx",
    r"deck",
    r"資料",
    r"まとめ",
)

SIDE_EFFECT_PATTERNS = (
    r"\bemail\b",
    r"\bsend\b",
    r"\bupload\b",
    r"メール",
    r"送信",
    r"アップロード",
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}"
)
AT_PATTERN = re.compile(r"@")

JSONScalar = Union[str, int, float, bool, None]
JSONValue = Union[JSONScalar, Dict[str, Any], List[Any]]



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

    kind: str
    prompt: str
    hitl: str = HITL_UNSPECIFIED



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

    decision: str
    reason_code: str
    artifact_preview: Optional[str]


@dataclass
class AuditEvent:
    ts: str
    run_id: str
    session_id: str
    task_id: str
    layer: str
    decision: str
    reason_code: str
    sealed: Optional[bool] = None
    artifact_preview: Optional[str] = None
    safe_context: Optional[Dict[str, JSONValue]] = None


def utc_ts() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def sanitize_string(text: str) -> str:
    value = ensure_text(text)
    if not value:
        return value
    value = EMAIL_PATTERN.sub("[REDACTED]", value)
    value = PHONE_PATTERN.sub("[REDACTED]", value)
    value = AT_PATTERN.sub("[REDACTED]", value)
    return value


def sanitize_json_value(value: JSONValue) -> JSONValue:
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, list):
        return [sanitize_json_value(v) for v in value]
    if isinstance(value, dict):
        sanitized: Dict[str, JSONValue] = {}
        for key, item in value.items():
            if str(key) == "raw_text":
                continue
            sanitized[sanitize_string(str(key))] = sanitize_json_value(item)
        return sanitized
    return value


def safe_prompt_digest(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()[:12]


def contains_pattern(patterns: Sequence[str], text: str) -> bool:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


class AuditLogger:
    def __init__(
        self,
        path: str,
        run_id: str = "",
        session_id: str = "",
    ) -> None:
        self.path = path
        self.run_id = ensure_text(run_id)
        self.session_id = ensure_text(session_id)

    def log(self, event: AuditEvent) -> None:
        payload = asdict(event)
        sanitized = sanitize_json_value(payload)
        line = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":"))
        if "@" in line:
            line = line.replace("@", "[REDACTED]")
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


class Agent:
    def normalize(
        self,
        tasks: Union[Task, Dict[str, Any], Sequence[Union[Task, Dict[str, Any]]]],
    ) -> List[Task]:
        if isinstance(tasks, (Task, dict)):
            return [self._to_task(tasks)]
        return [self._to_task(item) for item in tasks]

    def _to_task(self, item: Union[Task, Dict[str, Any]]) -> Task:
        if isinstance(item, Task):
            return item
        hitl = ensure_text(item.get("hitl") or HITL_UNSPECIFIED)
        return Task(
            task_id=ensure_text(item.get("task_id")),
            kind=ensure_text(item.get("kind")),
            prompt=ensure_text(item.get("prompt")),
            hitl=hitl or HITL_UNSPECIFIED,
        )


class Mediator:
    def __init__(self, audit: AuditLogger) -> None:
        self.audit = audit

    def evaluate(self, task: Task) -> Dict[str, str]:
        if task.hitl == HITL_STOP:
            decision = DECISION_PAUSE
            reason_code = REASON_HITL_STOP
        elif task.hitl == HITL_CONTINUE:
            decision = DECISION_RUN
            reason_code = REASON_MEDIATOR_HITL_CONTINUE
        else:
            decision = DECISION_RUN
            reason_code = REASON_MEDIATOR_RUN

        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                run_id=self.audit.run_id,
                session_id=self.audit.session_id,
                task_id=task.task_id,
                layer=LAYER_MEDIATOR,
                decision=decision,
                reason_code=reason_code,
                safe_context={
                    "kind": task.kind,
                    "hitl": task.hitl,
                    "prompt_digest": safe_prompt_digest(task.prompt),
                },
            )
        )
        return {"decision": decision, "reason_code": reason_code}


class Orchestrator:
    def __init__(self, audit: AuditLogger) -> None:
        self.audit = audit

    def run(self, task: Task, mediator_state: Dict[str, str]) -> OrchestratorResult:
        current_decision = mediator_state["decision"]
        current_reason = mediator_state["reason_code"]

        outcome = self._gate_meaning(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_consistency(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_rfl(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        if current_decision == DECISION_PAUSE:
            current_decision, current_reason = self._resolve_hitl_after_pause(
                task, current_decision, current_reason
            )

        outcome = self._gate_ethics(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_acc(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        if current_decision == DECISION_PAUSE:
            current_decision, current_reason = self._resolve_hitl_after_pause(
                task, current_decision, current_reason
            )

        dispatch = self._gate_dispatch(task, current_decision, current_reason)
        return OrchestratorResult(
            task_id=task.task_id,
            decision=dispatch["decision"],
            reason_code=dispatch["reason_code"],
            artifact_preview=dispatch["artifact_preview"],
        )

    def _audit_event(
        self,
        task_id: str,
        layer: str,
        decision: str,
        reason_code: str,
        *,
        sealed: Optional[bool] = None,
        artifact_preview: Optional[str] = None,
        safe_context: Optional[Dict[str, JSONValue]] = None,
    ) -> AuditEvent:
        return AuditEvent(
            ts=utc_ts(),
            run_id=self.audit.run_id,
            session_id=self.audit.session_id,
            task_id=task_id,
            layer=layer,
            decision=decision,
            reason_code=reason_code,
            sealed=sealed,
            artifact_preview=artifact_preview,
            safe_context=safe_context,
        )

    def _gate_meaning(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        if current_decision != DECISION_RUN:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_MEANING,
                    current_decision,
                    current_reason,
                    safe_context={"skipped": True},
                )
            )
            return {"decision": current_decision, "reason_code": current_reason}

        if not task.prompt.strip():
            decision = DECISION_PAUSE
            reason = REASON_MEANING_EMPTY_PROMPT
        elif task.kind not in KNOWN_KINDS:
            decision = DECISION_PAUSE
            reason = REASON_MEANING_INVALID_KIND
        else:
            decision = DECISION_RUN
            reason = REASON_MEANING_OK

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_MEANING,
                decision,
                reason,
                safe_context={
                    "kind": task.kind,
                    "prompt_digest": safe_prompt_digest(task.prompt),
                },
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_consistency(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        if current_decision != DECISION_RUN:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_CONSISTENCY,
                    current_decision,
                    current_reason,
                    safe_context={"skipped": True},
                )
            )
            return {"decision": current_decision, "reason_code": current_reason}

        prompt = task.prompt
        if task.kind == "xlsx":
            ok = contains_pattern(SPREADSHEET_PATTERNS, prompt)
        elif task.kind == "pptx":
            ok = contains_pattern(SLIDE_PATTERNS, prompt)
        else:
            ok = False

        if ok:
            decision = DECISION_RUN
            reason = REASON_CONSISTENCY_OK
        else:
            decision = DECISION_PAUSE
            reason = REASON_CONSISTENCY_MISMATCH

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_CONSISTENCY,
                decision,
                reason,
                safe_context={
                    "kind": task.kind,
                    "prompt_digest": safe_prompt_digest(prompt),
                },
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_rfl(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        if current_decision != DECISION_RUN:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_RFL,
                    current_decision,
                    current_reason,
                    sealed=False,
                    safe_context={"skipped": True},
                )
            )
            return {"decision": current_decision, "reason_code": current_reason}

        if contains_pattern(RFL_PATTERNS, task.prompt):
            decision = DECISION_PAUSE
            reason = REASON_RFL_RELATIVE
        else:
            decision = DECISION_RUN
            reason = REASON_RFL_OK

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_RFL,
                decision,
                reason,
                sealed=False,
                safe_context={"prompt_digest": safe_prompt_digest(task.prompt)},
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _resolve_hitl_after_pause(
        self, task: Task, current_decision: str, current_reason: str
    ) -> tuple[str, str]:
        if current_decision != DECISION_PAUSE:
            return current_decision, current_reason

        if task.hitl == HITL_CONTINUE:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_HITL,
                    DECISION_RUN,
                    REASON_HITL_CONTINUE,
                    safe_context={
                        "hitl": task.hitl,
                        "from_reason": current_reason,
                    },
                )
            )
            return DECISION_RUN, REASON_HITL_CONTINUE

        if task.hitl == HITL_STOP:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_HITL,
                    DECISION_PAUSE,
                    REASON_HITL_STOP,
                    safe_context={
                        "hitl": task.hitl,
                        "from_reason": current_reason,
                    },
                )
            )
            return DECISION_PAUSE, REASON_HITL_STOP

        wait_reason = (
            REASON_HITL_WAIT
            if current_reason == REASON_RFL_RELATIVE
            else current_reason
        )
        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_HITL,
                DECISION_PAUSE,
                wait_reason,
                safe_context={
                    "hitl": task.hitl,
                    "from_reason": current_reason,
                },
            )
        )
        return DECISION_PAUSE, wait_reason

    def _gate_ethics(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        contains_pii = self._contains_pii(task.prompt)

        if contains_pii:
            decision = DECISION_STOPPED
            reason = REASON_ETHICS_PII
            sealed = True
        else:
            decision = current_decision
            if current_decision == DECISION_RUN:
                reason = REASON_ETHICS_OK
            else:
                reason = current_reason
            sealed = None

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_ETHICS,
                decision,
                reason,
                sealed=sealed,
                safe_context={
                    "prompt_digest": safe_prompt_digest(task.prompt),
                    "contains_pii": contains_pii,
                },
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_acc(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        contains_side_effect = contains_pattern(SIDE_EFFECT_PATTERNS, task.prompt)

        if current_decision != DECISION_RUN:
            decision = current_decision
            reason = current_reason
        elif contains_side_effect:
            decision = DECISION_PAUSE
            reason = REASON_ACC_EXTERNAL_SIDE_EFFECT
        else:
            decision = DECISION_RUN
            reason = REASON_ACC_OK

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_ACC,
                decision,
                reason,
                safe_context={
                    "acc_mode": "pass_through",
                    "contains_external_side_effect": contains_side_effect,
                },
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_dispatch(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, Any]:
        if current_decision != DECISION_RUN:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_DISPATCH,
                    current_decision,
                    current_reason,
                    artifact_preview=None,
                    safe_context={"kind": task.kind, "skipped": True},
                )
            )
            return {
                "decision": current_decision,
                "reason_code": current_reason,
                "artifact_preview": None,
            }

        artifact_preview = self._build_artifact_preview(task)
        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_DISPATCH,
                DECISION_RUN,
                REASON_DISPATCH_OK,
                artifact_preview=artifact_preview,
                safe_context={"kind": task.kind},
            )
        )
        return {
            "decision": DECISION_RUN,
            "reason_code": REASON_DISPATCH_OK,
            "artifact_preview": artifact_preview,
        }

    def _build_artifact_preview(self, task: Task) -> str:
        base = sanitize_string(task.prompt.strip())
        preview = f"{task.kind} artifact preview: {base[:80]}"
        return sanitize_string(preview)

    def _contains_pii(self, text: str) -> bool:
        return bool(EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text))


class Pipeline:
    def __init__(
        self,
        audit_log_path: str = "audit.jsonl",
        run_id: str = "",
        session_id: str = "",
    ) -> None:
        self.audit = AuditLogger(
            audit_log_path,
            run_id=run_id,
            session_id=session_id,
        )
        self.agent = Agent()
        self.mediator = Mediator(self.audit)
        self.orchestrator = Orchestrator(self.audit)

    def run(
        self,
        tasks: Union[Task, Dict[str, Any], Sequence[Union[Task, Dict[str, Any]]]],
    ) -> Union[OrchestratorResult, List[OrchestratorResult]]:
        normalized = self.agent.normalize(tasks)
        results: List[OrchestratorResult] = []
        for task in normalized:
            mediator_state = self.mediator.evaluate(task)
            result = self.orchestrator.run(task, mediator_state)
            results.append(result)

        if isinstance(tasks, (Task, dict)):
            return results[0]
        return results


def run_pipeline(
    tasks: Union[Task, Dict[str, Any], Sequence[Union[Task, Dict[str, Any]]]],
    run_id: str,
    session_id: str,
    log_path: str,
    hitl_choices: Optional[Dict[str, str]] = None,
) -> List[OrchestratorResult]:
    agent = Agent()
    normalized = agent.normalize(tasks)

    choices = hitl_choices or {}
    patched: List[Task] = []
    for task in normalized:
        hitl = choices.get(task.task_id, task.hitl)
        patched.append(
            Task(
                task_id=task.task_id,
                kind=task.kind,
                prompt=task.prompt,
                hitl=hitl,
            )
        )

    pipeline = Pipeline(
        audit_log_path=log_path,
        run_id=run_id,
        session_id=session_id,
    )
    results = pipeline.run(patched)
    return results if isinstance(results, list) else [results]


def run_demo() -> None:
    results = run_pipeline(
        tasks=[
            {"task_id": "T1", "kind": "xlsx", "prompt": "売上サマリーを表にして"},
            {"task_id": "T2", "kind": "xlsx", "prompt": "売上をいい感じでまとめて"},
            {
                "task_id": "T3",
                "kind": "xlsx",
                "prompt": "売上表を作ってメール送信して",
                "hitl": HITL_CONTINUE,
            },
            {
                "task_id": "T4",
                "kind": "xlsx",
                "prompt": "顧客連絡先 test@example.com と 090-1234-5678 を含めて",
            },
        ],
        run_id="DEMO",
        session_id="DEMO_SESSION",
        log_path="audit.jsonl",
    )
    for item in results:
        print(json.dumps(asdict(item), ensure_ascii=False))


if __name__ == "__main__":
    run_demo()

