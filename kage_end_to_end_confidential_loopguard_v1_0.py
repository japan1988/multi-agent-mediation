# -*- coding: utf-8 -*-
"""
kage_end_to_end_confidential_loopguard_v1_0.py

End-to-end simulation:
Agent -> Mediator -> Orchestrator -> (HITL notify) -> Agent(revise) ... with loop-guard.

Flow intent:
1) Agent mistakenly includes confidential info in draft.
2) Mediator detects and requests revision (差し戻し).
3) Orchestrator logs events (ARL), triggers agent revision, and notifies user via HITL.
4) Loop-guard:
   - On 3rd same revision request: notify user (warn) and require ACK to continue.
   - On 4th same revision request: end session (STOPPED).

Hard safety:
- Raw confidential text must NEVER be persisted to ARL (only redacted/safe summaries).
- ARL validation fails if email-like strings or secret_token are detected.

Python: 3.9+
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Literal, Optional, Tuple

JST = timezone(timedelta(hours=9))

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["STOP", "CONTINUE", "ACK"]

# ----------------------------
# Reason codes (minimal, explicit)
# ----------------------------
RC_AGENT_DRAFT_CREATED = "AGENT_DRAFT_CREATED"
RC_AGENT_REVISED_CREATED = "AGENT_REVISED_CREATED"

RC_MEDIATOR_OK = "MEDIATOR_OK"
RC_MEDIATOR_REVISION_REQUEST_CONFIDENTIAL = "MEDIATOR_REVISION_REQUEST_CONFIDENTIAL"

RC_HITL_NOTIFY_REVISION = "HITL_NOTIFY_REVISION_REQUEST"
RC_HITL_WARN_REV3 = "HITL_WARN_REV3"
RC_MAX_REV_EXCEEDED = "MAX_REV_EXCEEDED"
RC_HITL_NOTIFY_SESSION_ENDED = "HITL_NOTIFY_SESSION_ENDED"

RC_HITL_ACK = "HITL_ACK"
RC_DISPATCH = "DISPATCH"
RC_FINALIZE = "FINALIZE"
RC_SESSION_END = "SESSION_END"

# ----------------------------
# PII detection (strict, simple)
# ----------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_RE = re.compile(r"secret_token\s*=\s*[^\s]+", re.IGNORECASE)


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ArlEvent:
    ts: str
    run_id: str
    layer: str
    decision: Decision
    sealed: bool
    overrideable: bool
    final_decider: FinalDecider
    reason_code: str
    meta: Dict[str, Any]


class AuditLog:
    """Append-only ARL log for tests; refuses PII in any persisted field."""

    def __init__(self) -> None:
        self.events: List[ArlEvent] = []

    def emit(
        self,
        *,
        run_id: str,
        layer: str,
        decision: Decision,
        reason_code: str,
        sealed: bool,
        overrideable: bool,
        final_decider: FinalDecider,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta = meta or {}
        ev = ArlEvent(
            ts=_utc_iso(datetime.now(timezone.utc)),
            run_id=run_id,
            layer=layer,
            decision=decision,
            sealed=sealed,
            overrideable=overrideable,
            final_decider=final_decider,
            reason_code=reason_code,
            meta=meta,
        )
        # Enforce: no PII in persisted event (including meta)
        self._assert_no_pii_in_event(ev)
        self.events.append(ev)

    def _assert_no_pii_in_event(self, ev: ArlEvent) -> None:
        blob = json.dumps(asdict(ev), ensure_ascii=False, sort_keys=True)
        if EMAIL_RE.search(blob):
            raise ValueError("PII_DETECTED_IN_ARL: email-like string found")
        if SECRET_RE.search(blob):
            raise ValueError("PII_DETECTED_IN_ARL: secret_token found")

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(e), ensure_ascii=False) for e in self.events) + ("\n" if self.events else "")


class Agent:
    """Deterministic 'mistake-prone' agent for simulation."""

    def __init__(self, *, always_leak: bool = True) -> None:
        self.always_leak = always_leak

    def draft(self, attempt: int) -> str:
        # Simulate a confidential leak (email + token) in the agent's draft.
        if self.always_leak:
            return f"Draft v{attempt}: contact=alice@example.com secret_token=sk-demo-{attempt} (DO NOT SHARE)"
        return f"Draft v{attempt}: public summary only."

    def revise(self, attempt: int) -> str:
        # For this loop-guard scenario, keep leaking to force warn+stop within one episode.
        return self.draft(attempt)


class Mediator:
    """Detects confidential content and asks for revision."""

    def review(self, text: str) -> Tuple[bool, str]:
        if EMAIL_RE.search(text) or SECRET_RE.search(text):
            return False, RC_MEDIATOR_REVISION_REQUEST_CONFIDENTIAL
        return True, RC_MEDIATOR_OK


@dataclass(frozen=True)
class EpisodeResult:
    run_id: str
    final_decision: Decision
    revision_count: int


class Orchestrator:
    """Coordinates Agent/Mediator and emits ARL events for HITL and loop-guard."""

    def __init__(self, *, max_same_issue: int = 4) -> None:
        if max_same_issue < 1:
            raise ValueError("max_same_issue must be >= 1")
        self.max_same_issue = max_same_issue

    @staticmethod
    def _safe_summary(reason_code: str, attempt: int) -> str:
        # Must not include any raw draft. Only safe metadata.
        if reason_code == RC_MEDIATOR_REVISION_REQUEST_CONFIDENTIAL:
            return f"confidential_detected attempt={attempt} (redacted)"
        return f"ok attempt={attempt}"

    def run_episode(
        self,
        *,
        run_id: str,
        agent: Agent,
        mediator: Mediator,
        audit: AuditLog,
        hitl_choice_on_warn: HitlChoice = "ACK",
    ) -> EpisodeResult:
        same_issue_count = 0
        attempt = 0

        while True:
            attempt += 1
            draft = agent.draft(attempt) if attempt == 1 else agent.revise(attempt)
            # Log that draft was produced, but NEVER persist draft content.
            audit.emit(
                run_id=run_id,
                layer="agent_draft",
                decision="RUN",
                reason_code=RC_AGENT_DRAFT_CREATED if attempt == 1 else RC_AGENT_REVISED_CREATED,
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                meta={"attempt": attempt},
            )

            ok, med_rc = mediator.review(draft)
            audit.emit(
                run_id=run_id,
                layer="mediator_advice",
                decision="RUN" if ok else "PAUSE_FOR_HITL",
                reason_code=med_rc,
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                meta={"attempt": attempt, "summary": self._safe_summary(med_rc, attempt)},
            )

            if ok:
                audit.emit(
                    run_id=run_id,
                    layer="dispatch",
                    decision="RUN",
                    reason_code=RC_DISPATCH,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"attempt": attempt},
                )
                audit.emit(
                    run_id=run_id,
                    layer="finalize",
                    decision="RUN",
                    reason_code=RC_FINALIZE,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"attempt": attempt},
                )
                return EpisodeResult(run_id=run_id, final_decision="RUN", revision_count=same_issue_count)

            # Issue: confidential revision requested
            if med_rc == RC_MEDIATOR_REVISION_REQUEST_CONFIDENTIAL:
                same_issue_count += 1

            # Loop-guard logic
            if same_issue_count == 3:
                # Warn + require ACK to continue (user report)
                audit.emit(
                    run_id=run_id,
                    layer="rrl_loop_guard",
                    decision="PAUSE_FOR_HITL",
                    reason_code=RC_HITL_WARN_REV3,
                    sealed=False,
                    overrideable=True,
                    final_decider="SYSTEM",
                    meta={"same_issue_count": same_issue_count},
                )
                audit.emit(
                    run_id=run_id,
                    layer="hitl_notify_user",
                    decision="PAUSE_FOR_HITL",
                    reason_code=RC_HITL_WARN_REV3,
                    sealed=False,
                    overrideable=True,
                    final_decider="SYSTEM",
                    meta={"message": "Same confidential issue occurred 3 times; acknowledging and continuing will attempt one more revision."},
                )
                audit.emit(
                    run_id=run_id,
                    layer="hitl_finalize",
                    decision="PAUSE_FOR_HITL" if hitl_choice_on_warn == "ACK" else ("STOPPED" if hitl_choice_on_warn == "STOP" else "RUN"),
                    reason_code=RC_HITL_ACK if hitl_choice_on_warn == "ACK" else f"HITL_{hitl_choice_on_warn}",
                    sealed=False,
                    overrideable=False,
                    final_decider="USER",
                    meta={"choice": hitl_choice_on_warn},
                )
                if hitl_choice_on_warn == "STOP":
                    audit.emit(
                        run_id=run_id,
                        layer="finalize",
                        decision="STOPPED",
                        reason_code=RC_FINALIZE,
                        sealed=False,
                        overrideable=False,
                        final_decider="SYSTEM",
                        meta={"stopped_by": "USER", "same_issue_count": same_issue_count},
                    )
                    audit.emit(
                        run_id=run_id,
                        layer="session_end",
                        decision="STOPPED",
                        reason_code=RC_SESSION_END,
                        sealed=False,
                        overrideable=False,
                        final_decider="SYSTEM",
                        meta={"same_issue_count": same_issue_count},
                    )
                    return EpisodeResult(run_id=run_id, final_decision="STOPPED", revision_count=same_issue_count)
                # ACK or CONTINUE -> proceed

            if same_issue_count >= 4:
                # End session
                audit.emit(
                    run_id=run_id,
                    layer="rrl_loop_guard",
                    decision="STOPPED",
                    reason_code=RC_MAX_REV_EXCEEDED,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"same_issue_count": same_issue_count},
                )
                audit.emit(
                    run_id=run_id,
                    layer="hitl_notify_user",
                    decision="PAUSE_FOR_HITL",
                    reason_code=RC_HITL_NOTIFY_SESSION_ENDED,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"message": "Same confidential issue occurred 4 times; session ended (fail-closed)."},
                )
                audit.emit(
                    run_id=run_id,
                    layer="finalize",
                    decision="STOPPED",
                    reason_code=RC_FINALIZE,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"same_issue_count": same_issue_count},
                )
                audit.emit(
                    run_id=run_id,
                    layer="session_end",
                    decision="STOPPED",
                    reason_code=RC_SESSION_END,
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM",
                    meta={"same_issue_count": same_issue_count},
                )
                return EpisodeResult(run_id=run_id, final_decision="STOPPED", revision_count=same_issue_count)

            # Normal revision request: notify user and loop to agent revise
            audit.emit(
                run_id=run_id,
                layer="hitl_notify_user",
                decision="PAUSE_FOR_HITL",
                reason_code=RC_HITL_NOTIFY_REVISION,
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                meta={"attempt": attempt, "same_issue_count": same_issue_count, "message": "Mediator requested revision due to confidential content (redacted)."},
            )
            # Continue loop


def demo() -> None:
    run_id = "DEMO#CONF_LOOP"
    audit = AuditLog()
    orch = Orchestrator(max_same_issue=4)
    res = orch.run_episode(run_id=run_id, agent=Agent(always_leak=True), mediator=Mediator(), audit=audit, hitl_choice_on_warn="ACK")
    print(f"final_decision={res.final_decision} revision_count={res.revision_count}")
    print(audit.to_jsonl())


if __name__ == "__main__":
    demo()
