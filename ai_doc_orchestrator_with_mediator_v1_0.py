# ai_doc_orchestrator_with_mediator_v1_0.py
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
REASON_DISPATCH_OK = "ORCH_RUN_OK"
REASON_HITL_WAIT = "HITL_UNSPECIFIED_WAIT"

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
)

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}"
)
AT_PATTERN = re.compile(r"@")

JSONScalar = Union[str, int, float, bool, None]
JSONValue = Union[JSONScalar, Dict[str, Any], List[Any]]


@dataclass
class Task:
    task_id: str
    kind: str
    prompt: str
    hitl: str = HITL_UNSPECIFIED


@dataclass
class OrchestratorResult:
    task_id: str
    decision: str
    reason_code: str
    artifact_preview: Optional[str]


@dataclass
class AuditEvent:
    ts: str
    task_id: str
    layer: str
    decision: str
    reason_code: str
    sealed: Optional[bool] = None
    artifact_preview: Optional[str] = None
    safe_context: Optional[Dict[str, JSONValue]] = None


def utc_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
            if key == "raw_text":
                continue
            sanitized[str(key)] = sanitize_json_value(item)
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
    def __init__(self, path: str) -> None:
        self.path = path

    def log(self, event: AuditEvent) -> None:
        payload = asdict(event)
        payload.pop("raw_text", None)
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
        normalized: List[Task] = []
        for item in tasks:
            normalized.append(self._to_task(item))
        return normalized

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

    def evaluate(self, task: Task) -> Dict[str, Any]:
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
                task_id=task.task_id,
                layer="Mediator",
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

    def run(self, task: Task, mediator_state: Dict[str, Any]) -> OrchestratorResult:
        current_decision = mediator_state["decision"]
        current_reason = mediator_state["reason_code"]

        outcome = self._gate_meaning(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_consistency(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_rfl(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        if current_decision == DECISION_PAUSE:
            current_decision, current_reason = self._resolve_hitl_after_rfl(
                task, current_decision, current_reason
            )

        outcome = self._gate_ethics(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        outcome = self._gate_acc(task, current_decision, current_reason)
        current_decision, current_reason = outcome["decision"], outcome["reason_code"]

        dispatch = self._gate_dispatch(task, current_decision, current_reason)
        return OrchestratorResult(
            task_id=task.task_id,
            decision=dispatch["decision"],
            reason_code=dispatch["reason_code"],
            artifact_preview=dispatch["artifact_preview"],
        )

    def _gate_meaning(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, str]:
        if current_decision != DECISION_RUN:
            self.audit.log(
                AuditEvent(
                    ts=utc_ts(),
                    task_id=task.task_id,
                    layer="Meaning",
                    decision=current_decision,
                    reason_code=current_reason,
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
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="Meaning",
                decision=decision,
                reason_code=reason,
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
                AuditEvent(
                    ts=utc_ts(),
                    task_id=task.task_id,
                    layer="Consistency",
                    decision=current_decision,
                    reason_code=current_reason,
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
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="Consistency",
                decision=decision,
                reason_code=reason,
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
                AuditEvent(
                    ts=utc_ts(),
                    task_id=task.task_id,
                    layer="RFL",
                    decision=current_decision,
                    reason_code=current_reason,
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
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="RFL",
                decision=decision,
                reason_code=reason,
                sealed=False,
                safe_context={"prompt_digest": safe_prompt_digest(task.prompt)},
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _resolve_hitl_after_rfl(
        self, task: Task, current_decision: str, current_reason: str
    ) -> tuple[str, str]:
        if current_reason != REASON_RFL_RELATIVE:
            return current_decision, current_reason

        if task.hitl == HITL_CONTINUE:
            self.audit.log(
                AuditEvent(
                    ts=utc_ts(),
                    task_id=task.task_id,
                    layer="HITL",
                    decision=DECISION_RUN,
                    reason_code=REASON_MEDIATOR_HITL_CONTINUE,
                    safe_context={"hitl": task.hitl},
                )
            )
            return DECISION_RUN, REASON_MEDIATOR_HITL_CONTINUE

        if task.hitl == HITL_STOP:
            self.audit.log(
                AuditEvent(
                    ts=utc_ts(),
                    task_id=task.task_id,
                    layer="HITL",
                    decision=DECISION_PAUSE,
                    reason_code=REASON_HITL_STOP,
                    safe_context={"hitl": task.hitl},
                )
            )
            return DECISION_PAUSE, REASON_HITL_STOP

        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="HITL",
                decision=DECISION_PAUSE,
                reason_code=REASON_HITL_WAIT,
                safe_context={"hitl": task.hitl},
            )
        )
        return DECISION_PAUSE, REASON_HITL_WAIT

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
            reason = (
                REASON_ETHICS_OK if current_decision == DECISION_RUN else current_reason
            )
            sealed = None

        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="Ethics",
                decision=decision,
                reason_code=reason,
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
        decision = current_decision
        reason = REASON_ACC_OK if current_decision == DECISION_RUN else current_reason

        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="ACC",
                decision=decision,
                reason_code=reason,
                sealed=None,
                safe_context={"acc_mode": "pass_through"},
            )
        )
        return {"decision": decision, "reason_code": reason}

    def _gate_dispatch(
        self, task: Task, current_decision: str, current_reason: str
    ) -> Dict[str, Any]:
        if current_decision != DECISION_RUN:
            return {
                "decision": current_decision,
                "reason_code": current_reason,
                "artifact_preview": None,
            }

        artifact_preview = self._build_artifact_preview(task)
        self.audit.log(
            AuditEvent(
                ts=utc_ts(),
                task_id=task.task_id,
                layer="DISPATCH",
                decision=DECISION_RUN,
                reason_code=REASON_DISPATCH_OK,
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
    def __init__(self, audit_log_path: str = "audit.jsonl") -> None:
        self.audit = AuditLogger(audit_log_path)
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


def run_demo() -> None:
    pipeline = Pipeline(audit_log_path="audit.jsonl")
    demo_tasks: List[Dict[str, str]] = [
        {"task_id": "T1", "kind": "xlsx", "prompt": "売上サマリーを表にして"},
        {"task_id": "T2", "kind": "xlsx", "prompt": "売上をいい感じでまとめて"},
        {
            "task_id": "T3",
            "kind": "xlsx",
            "prompt": "売上表を作ってメール送信して",
            "hitl": "CONTINUE",
        },
        {
            "task_id": "T4",
            "kind": "xlsx",
            "prompt": "顧客連絡先 test@example.com と 090-1234-5678 を含めて",
        },
    ]
    results = pipeline.run(demo_tasks)
    for item in results:
        print(json.dumps(asdict(item), ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
