# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_with_mediator_v1_0.py

Agent -> Mediator -> Orchestrator pipeline (research simulator)

Fixed gate order:
  Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH

Invariants:
- Mediator has no STOP authority. It returns only RUN or PAUSE_FOR_HITL.
- Orchestrator always evaluates gates in fixed order.
- sealed=True appears only at Ethics/ACC.
- raw_text is never persisted.
- logs never contain '@' after sanitization.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

JST = timezone(timedelta(hours=9))

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

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
    r"どっち",
    r"どちら",
    r"どれ",
    r"\?",
    r"？",
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
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}"
)
AT_PATTERN = re.compile(r"@")
RELATIVE_TERMS = re.compile("|".join(RFL_PATTERNS), re.IGNORECASE)
EXTERNAL_SIDE_EFFECT_HINTS = re.compile("|".join(SIDE_EFFECT_PATTERNS), re.IGNORECASE)
_TASKS: Tuple[str, ...] = ("excel", "word", "ppt")

JSONScalar = Union[str, int, float, bool, None]
JSONValue = Union[JSONScalar, Dict[str, Any], List[Any]]


@dataclass
class Task:
    task_id: str
    kind: str
    prompt: str
    hitl: str = HITL_UNSPECIFIED


@dataclass
class AgentProposal:
    task_id: str
    kind: str
    spec: Dict[str, Any]
    raw_text: str


@dataclass
class MediatorReview:
    task_id: str
    decision: Literal["RUN", "PAUSE_FOR_HITL"]
    reason_code: str
    revised_spec: Optional[Dict[str, Any]] = None
    safe_preview: str = ""
    kind: str = ""
    prompt: str = ""
    hitl: str = HITL_UNSPECIFIED


@dataclass
class OrchestratorResult:
    task_id: str
    decision: str
    reason_code: str
    artifact_preview: Optional[str] = None


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
    overrideable: Optional[bool] = None
    final_decider: Optional[str] = None
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


def _sha256_text(s: str) -> str:
    return hashlib.sha256(ensure_text(s).encode("utf-8", errors="ignore")).hexdigest()


def safe_prompt_digest(prompt: str) -> str:
    return _sha256_text(prompt)[:12]


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
            if str(key).lower() in {"raw_text", "raw", "prompt_raw"}:
                continue
            sanitized[sanitize_string(str(key))] = sanitize_json_value(item)
        return sanitized
    return value


def _pii_like(s: str) -> bool:
    s = ensure_text(s)
    return bool(EMAIL_PATTERN.search(s) or PHONE_PATTERN.search(s))


def _contains_external_side_effect_request(s: str) -> bool:
    return bool(EXTERNAL_SIDE_EFFECT_HINTS.search(ensure_text(s)))


def _rfl_hit(s: str) -> bool:
    return bool(RELATIVE_TERMS.search(ensure_text(s)))


def _redact_email_like(s: str) -> str:
    return sanitize_string(s)


def _build_artifact_preview(spec: Dict[str, Any]) -> str:
    return sanitize_string(json.dumps(spec, ensure_ascii=False)[:240])


def contains_pattern(patterns: Sequence[str], text: str) -> bool:
    text = ensure_text(text)
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


class AuditLog:
    """
    JSONL audit writer with safety guards:
    - Never persists raw_text.
    - Never persists any '@' character.
    """

    def __init__(self, log_path: str, run_id: str = "", session_id: str = "") -> None:
        self.log_path = log_path
        self.run_id = ensure_text(run_id)
        self.session_id = ensure_text(session_id)

    def start_run(self, truncate: bool = False) -> None:
        path = Path(self.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            path.write_text("", encoding="utf-8")

    def _sanitize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = sanitize_json_value(event)
        if not isinstance(sanitized, dict):
            raise TypeError("sanitized audit event must be a dict")
        return sanitized

    def emit(self, event: Dict[str, Any]) -> None:
        safe = self._sanitize_event(event)
        path = Path(self.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            line = json.dumps(safe, ensure_ascii=False, default=str)
            if "@" in line:
                line = line.replace("@", "[REDACTED]")
            f.write(line + "\n")

    def log(self, event: Union[AuditEvent, Dict[str, Any]]) -> None:
        payload: Dict[str, Any]
        if is_dataclass(event):
            payload = asdict(event)
        else:
            payload = dict(event)
        if not payload.get("ts"):
            payload["ts"] = utc_ts()
        if not payload.get("run_id"):
            payload["run_id"] = self.run_id
        if not payload.get("session_id"):
            payload["session_id"] = self.session_id
        self.emit(payload)


AuditLogger = AuditLog


def _arl_min(
    run_id: str,
    session_id: str,
    task: Task,
    layer: str,
    decision: str,
    reason_code: str,
    sealed: bool,
    overrideable: bool,
    final_decider: FinalDecider,
) -> Dict[str, Any]:
    return {
        "ts": datetime.now(JST).isoformat(),
        "run_id": run_id,
        "session_id": session_id,
        "task_id": task.task_id,
        "layer": layer,
        "decision": decision,
        "reason_code": reason_code,
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
        "kind": task.kind,
        "prompt_sha256": _sha256_text(task.prompt),
    }


def agent_generate(task: Task) -> AgentProposal:
    if task.kind == "xlsx":
        spec = {
            "format": "xlsx",
            "sheet_name": "Summary",
            "rows": [
                ["Title", "Value"],
                ["Task", task.prompt[:80]],
            ],
        }
        raw_text = "Generated XLSX spec."
    elif task.kind == "pptx":
        spec = {
            "format": "pptx",
            "slides": [
                {"title": "Overview", "bullets": [task.prompt[:80]]},
            ],
        }
        raw_text = "Generated PPTX spec."
    else:
        spec = {"format": task.kind, "content": task.prompt[:80]}
        raw_text = "Generated generic spec."
    return AgentProposal(task_id=task.task_id, kind=task.kind, spec=spec, raw_text=raw_text)


def mediator_review(task: Task, proposal: AgentProposal) -> MediatorReview:
    if _contains_external_side_effect_request(task.prompt):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_EXTERNAL_SIDE_EFFECT_AMBIGUOUS",
            safe_preview="Prompt suggests external side effects; escalate to HITL.",
            kind=task.kind,
            prompt=task.prompt,
            hitl=task.hitl,
        )

    if _rfl_hit(task.prompt):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_REL_BOUNDARY_UNSTABLE",
            safe_preview="Relativity terms detected; request clarification via HITL.",
            kind=task.kind,
            prompt=task.prompt,
            hitl=task.hitl,
        )

    if _pii_like(task.prompt) or _pii_like(proposal.raw_text):
        return MediatorReview(
            task_id=task.task_id,
            decision="PAUSE_FOR_HITL",
            reason_code="MEDIATOR_PII_LIKE_DETECTED",
            safe_preview="PII-like pattern detected; escalate to HITL.",
            kind=task.kind,
            prompt=task.prompt,
            hitl=task.hitl,
        )

    revised = dict(proposal.spec)
    if proposal.kind == "xlsx":
        revised.setdefault("format", "xlsx")
        revised.setdefault("rows", [])
    elif proposal.kind == "pptx":
        revised.setdefault("format", "pptx")
        revised.setdefault("slides", [])

    return MediatorReview(
        task_id=task.task_id,
        decision="RUN",
        reason_code="MEDIATOR_OK",
        revised_spec=revised,
        safe_preview="Mediator OK; forwarding to Orchestrator.",
        kind=task.kind,
        prompt=task.prompt,
        hitl=task.hitl,
    )


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
    def __init__(self, audit: AuditLog) -> None:
        self.audit = audit

    def evaluate(self, task: Task) -> Dict[str, str]:
        proposal = agent_generate(task)
        review = mediator_review(task, proposal)
        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                run_id=self.audit.run_id,
                session_id=self.audit.session_id,
                task_id=task.task_id,
                layer=LAYER_MEDIATOR,
                decision=review.decision,
                reason_code=review.reason_code,
                sealed=False,
                overrideable=True if review.decision == "PAUSE_FOR_HITL" else False,
                final_decider="SYSTEM",
                safe_context={
                    "kind": task.kind,
                    "hitl": task.hitl,
                    "prompt_digest": safe_prompt_digest(task.prompt),
                    "safe_preview": review.safe_preview,
                },
            )
        )
        return {"decision": review.decision, "reason_code": review.reason_code}


class Orchestrator:
    def __init__(self, audit: AuditLog) -> None:
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

        if current_decision == "PAUSE_FOR_HITL":
            current_decision, current_reason = self._resolve_hitl_after_pause(
                task, current_decision, current_reason
            )

        outcome = self._gate_ethics(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_acc(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        if current_decision == "PAUSE_FOR_HITL":
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
        overrideable: Optional[bool] = None,
        final_decider: Optional[str] = "SYSTEM",
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
            overrideable=overrideable,
            final_decider=final_decider,
            artifact_preview=artifact_preview,
            safe_context=safe_context,
        )

    def _gate_meaning(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        if current_decision != "RUN":
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_MEANING,
                    current_decision,
                    current_reason,
                    sealed=False,
                    overrideable=True if current_decision == "PAUSE_FOR_HITL" else False,
                    safe_context={"skipped": True},
                )
            )
            return {"decision": current_decision, "reason_code": current_reason}

        if not task.prompt.strip():
            decision = "PAUSE_FOR_HITL"
            reason = REASON_MEANING_EMPTY_PROMPT
        elif task.kind not in KNOWN_KINDS:
            decision = "PAUSE_FOR_HITL"
            reason = REASON_MEANING_INVALID_KIND
        else:
            decision = "RUN"
            reason = REASON_MEANING_OK

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_MEANING,
                decision,
                reason,
                sealed=False,
                overrideable=True if decision == "PAUSE_FOR_HITL" else False,
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
        if current_decision != "RUN":
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_CONSISTENCY,
                    current_decision,
                    current_reason,
                    sealed=False,
                    overrideable=True if current_decision == "PAUSE_FOR_HITL" else False,
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
            decision = "RUN"
            reason = REASON_CONSISTENCY_OK
        else:
            decision = "PAUSE_FOR_HITL"
            reason = REASON_CONSISTENCY_MISMATCH

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_CONSISTENCY,
                decision,
                reason,
                sealed=False,
                overrideable=True if decision == "PAUSE_FOR_HITL" else False,
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
        if current_decision != "RUN":
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_RFL,
                    current_decision,
                    current_reason,
                    sealed=False,
                    overrideable=True if current_decision == "PAUSE_FOR_HITL" else False,
                    safe_context={"skipped": True},
                )
            )
            return {"decision": current_decision, "reason_code": current_reason}

        if _rfl_hit(task.prompt):
            decision = "PAUSE_FOR_HITL"
            reason = REASON_RFL_RELATIVE
        else:
            decision = "RUN"
            reason = REASON_RFL_OK

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_RFL,
                decision,
                reason,
                sealed=False,
                overrideable=True if decision == "PAUSE_FOR_HITL" else False,
                safe_context={"prompt_digest": safe_prompt_digest(task.prompt)},
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _resolve_hitl_after_pause(
        self, task: Task, current_decision: str, current_reason: str
    ) -> tuple[str, str]:
        if current_decision != "PAUSE_FOR_HITL":
            return current_decision, current_reason

        if task.hitl == HITL_CONTINUE:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_HITL,
                    "RUN",
                    REASON_HITL_CONTINUE,
                    sealed=False,
                    overrideable=False,
                    final_decider="USER",
                    safe_context={"hitl": task.hitl, "from_reason": current_reason},
                )
            )
            return "RUN", REASON_HITL_CONTINUE

        if task.hitl == HITL_STOP:
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_HITL,
                    "PAUSE_FOR_HITL",
                    REASON_HITL_STOP,
                    sealed=False,
                    overrideable=False,
                    final_decider="USER",
                    safe_context={"hitl": task.hitl, "from_reason": current_reason},
                )
            )
            return "PAUSE_FOR_HITL", REASON_HITL_STOP

        wait_reason = REASON_HITL_WAIT if current_reason == REASON_RFL_RELATIVE else current_reason
        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_HITL,
                "PAUSE_FOR_HITL",
                wait_reason,
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                safe_context={"hitl": task.hitl, "from_reason": current_reason},
            )
        )
        return "PAUSE_FOR_HITL", wait_reason

    def _gate_ethics(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        contains_pii = _pii_like(task.prompt)
        if contains_pii:
            decision = "STOPPED"
            reason = REASON_ETHICS_PII
            sealed = True
            overrideable = False
        else:
            decision = current_decision
            reason = REASON_ETHICS_OK if current_decision == "RUN" else current_reason
            sealed = False
            overrideable = True if decision == "PAUSE_FOR_HITL" else False

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_ETHICS,
                decision,
                reason,
                sealed=sealed,
                overrideable=overrideable,
                final_decider="SYSTEM",
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
        contains_side_effect = _contains_external_side_effect_request(task.prompt)
        if current_decision != "RUN":
            decision = current_decision
            reason = current_reason
            sealed = False
            overrideable = True if decision == "PAUSE_FOR_HITL" else False
        elif contains_side_effect:
            decision = "PAUSE_FOR_HITL"
            reason = REASON_ACC_EXTERNAL_SIDE_EFFECT
            sealed = False
            overrideable = True
        else:
            decision = "RUN"
            reason = REASON_ACC_OK
            sealed = False
            overrideable = False

        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_ACC,
                decision,
                reason,
                sealed=sealed,
                overrideable=overrideable,
                final_decider="SYSTEM",
                safe_context={"contains_external_side_effect": contains_side_effect},
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_dispatch(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, Any]:
        if current_decision != "RUN":
            self.audit.log(
                self._audit_event(
                    task.task_id,
                    LAYER_DISPATCH,
                    current_decision,
                    current_reason,
                    sealed=False,
                    overrideable=True if current_decision == "PAUSE_FOR_HITL" else False,
                    final_decider="SYSTEM",
                    artifact_preview=None,
                    safe_context={"kind": task.kind, "skipped": True},
                )
            )
            return {
                "decision": current_decision,
                "reason_code": current_reason,
                "artifact_preview": None,
            }

        artifact_preview = sanitize_string(f"{task.kind} artifact preview: {task.prompt[:80]}")
        self.audit.log(
            self._audit_event(
                task.task_id,
                LAYER_DISPATCH,
                "RUN",
                REASON_DISPATCH_OK,
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                artifact_preview=artifact_preview,
                safe_context={"kind": task.kind},
            )
        )
        return {
            "decision": "RUN",
            "reason_code": REASON_DISPATCH_OK,
            "artifact_preview": artifact_preview,
        }


class Pipeline:
    def __init__(
        self,
        audit_log_path: str = "audit.jsonl",
        run_id: str = "",
        session_id: str = "",
    ) -> None:
        self.audit = AuditLog(audit_log_path, run_id=run_id, session_id=session_id)
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


def orchestrator_eval(
    task: Task,
    mediator: MediatorReview,
    run_id: str,
    session_id: str,
    audit: AuditLog,
    hitl_choice: Optional[Literal["STOP", "CONTINUE"]] = None,
) -> OrchestratorResult:
    audit.emit(
        _arl_min(
            run_id,
            session_id,
            task,
            layer=LAYER_MEDIATOR,
            decision=mediator.decision,
            reason_code=mediator.reason_code,
            sealed=False,
            overrideable=mediator.decision == "PAUSE_FOR_HITL",
            final_decider="SYSTEM",
        )
    )

    patched_task = Task(
        task_id=task.task_id,
        kind=task.kind,
        prompt=task.prompt,
        hitl=hitl_choice if hitl_choice is not None else task.hitl,
    )
    orchestrator = Orchestrator(audit)
    return orchestrator.run(
        patched_task,
        {"decision": mediator.decision, "reason_code": mediator.reason_code},
    )


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
            {"task_id": "T2", "kind": "pptx", "prompt": "プロジェクト概要スライドを作って"},
            {"task_id": "T3", "kind": "pptx", "prompt": "いい感じにまとめて"},
            {"task_id": "T4", "kind": "pptx", "prompt": "作った資料をメールで送って"},
            {"task_id": "T5", "kind": "xlsx", "prompt": "連絡先は test@example.com に送って"},
        ],
        run_id="RUN#DEMO",
        session_id="SESSION_CREATOR_1848CC59",
        log_path="audit_mediator_pipeline_v1_0.jsonl",
        hitl_choices={"T3": HITL_STOP, "T4": HITL_CONTINUE},
    )
    for item in results:
        print(json.dumps(asdict(item), ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
