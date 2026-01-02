# loop_policy_stage3.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple


# =========================
# Decision / Kind
# =========================

class Decision(str, Enum):
    PAUSE_FOR_HITL = "PAUSE_FOR_HITL"
    STOPPED = "STOPPED"
    END_SESSION_RECOMMENDED = "END_SESSION_RECOMMENDED"


# P0: kind values are distinct from Decision values (avoid log/analytics collisions)
K_HITL_PAUSE = "K_HITL_PAUSE"                 # counts
K_PLAN_REQUESTED = "K_PLAN_REQUESTED"         # does NOT count
K_PLAN_REQ_DISPATCH = "K_PLAN_REQ_DISPATCH"   # does NOT count
K_PLAN_PROPOSED = "K_PLAN_PROPOSED"           # does NOT count
K_PLAN_RECEIVED = "K_PLAN_RECEIVED"           # does NOT count
K_END_RECOMMENDED = "K_END_RECOMMENDED"       # must pair with decision=END_SESSION_RECOMMENDED
K_STOPPED = "K_STOPPED"                       # must pair with decision=STOPPED

_DECISION_VALUES = {d.value for d in Decision}
_KIND_VALUES = {
    K_HITL_PAUSE,
    K_PLAN_REQUESTED,
    K_PLAN_REQ_DISPATCH,
    K_PLAN_PROPOSED,
    K_PLAN_RECEIVED,
    K_END_RECOMMENDED,
    K_STOPPED,
}
if not _KIND_VALUES.isdisjoint(_DECISION_VALUES):
    raise ValueError(f"SPEC_INVALID: kind values collide with Decision values: {_KIND_VALUES & _DECISION_VALUES}")


# =========================
# Fail-Closed (P0 fixed)
# =========================

RC_SPEC_INVALID_INPUT = "SPEC_INVALID_INPUT"
RC_SPEC_MISSING_KEYS = "SPEC_MISSING_KEYS"

FINAL_SYSTEM = "SYSTEM"


# =========================
# Spec (frozen) + validation
# =========================

@dataclass(frozen=True)
class ResetRulesSpec:
    reset_on: Tuple[str, ...] = (
        "conflict_fingerprint_change",
        "explicit_new_session_start",
        "user_provides_required_info_for_blocking_fields",
    )
    never_reset_within_same_conflict: bool = True


@dataclass(frozen=True)
class TerminalSpec:
    decision: Decision = Decision.STOPPED
    requires_sealed: bool = True
    requires_overrideable: bool = False
    enforce_at: str = "maestro"
    no_further_transitions_in_same_session: bool = True


@dataclass(frozen=True)
class LoopPolicySpec:
    hitl_max_rounds: int = 4
    plan_request_round: int = 3

    # P0: conflict-level keying
    counter_key_format: str = "session_id|conflict_fingerprint"

    reset_rules: ResetRulesSpec = field(default_factory=ResetRulesSpec)
    terminal: TerminalSpec = field(default_factory=TerminalSpec)

    def __post_init__(self) -> None:
        if self.hitl_max_rounds < 1:
            raise ValueError("SPEC_INVALID: hitl_max_rounds must be >= 1")
        if not (1 <= self.plan_request_round < self.hitl_max_rounds):
            raise ValueError("SPEC_INVALID: require 1 <= plan_request_round < hitl_max_rounds")


# =========================
# Event / State
# =========================

@dataclass(frozen=True)
class Event:
    event_id: str
    timestamp: str
    session_id: str
    run_id: str
    layer: str
    decision: Decision
    kind: str
    reason_code: str
    conflict_fingerprint: str
    sealed: bool
    overrideable: bool
    final_decider: str
    payload: Optional[Dict[str, Any]] = None


@dataclass
class SessionState:
    session_id: str
    is_stopped: bool = False
    stop_issued: bool = False

    # Plan-flow idempotency (conflict unit)
    plan_request_dispatched_keys: Set[str] = field(default_factory=set)
    plan_proposed_keys: Set[str] = field(default_factory=set)
    plan_received_keys: Set[str] = field(default_factory=set)


# =========================
# Helpers
# =========================

def conflict_key(session_id: str, conflict_fingerprint: str) -> str:
    return f"{session_id}|{conflict_fingerprint}"


def validate_min_keys(e: Event) -> bool:
    return bool(e.session_id) and bool(e.conflict_fingerprint) and bool(e.event_id)


def validate_kind_decision_pairing(e: Event) -> bool:
    """
    P0 pairing rules (Stage3):
      - K_END_RECOMMENDED <-> decision=END_SESSION_RECOMMENDED
      - K_STOPPED         <-> decision=STOPPED
      - K_PLAN_* kinds    -> decision=PAUSE_FOR_HITL
      - K_HITL_PAUSE      -> decision=PAUSE_FOR_HITL
    """
    if e.kind == K_END_RECOMMENDED:
        return e.decision == Decision.END_SESSION_RECOMMENDED
    if e.kind == K_STOPPED:
        return e.decision == Decision.STOPPED
    if e.kind in {K_HITL_PAUSE, K_PLAN_REQUESTED, K_PLAN_REQ_DISPATCH, K_PLAN_PROPOSED, K_PLAN_RECEIVED}:
        return e.decision == Decision.PAUSE_FOR_HITL
    return False  # unknown kind


def fail_closed_event(*, base: Optional[Event], reason_code: str, layer: str) -> Event:
    """
    P0: Standard Fail-Closed response is fixed:
      - decision=PAUSE_FOR_HITL
      - sealed=false
      - overrideable=true
      - final_decider=SYSTEM
      - reason_code in {SPEC_INVALID_INPUT, SPEC_MISSING_KEYS}
    P0 compatibility:
      - The returned event MUST satisfy pairing rules.
      - Therefore, fail-closed kind is fixed to a non-counting plan kind, and the original is preserved in payload.
    """
    # Use a non-counting kind that pairs with PAUSE_FOR_HITL.
    safe_kind = K_PLAN_RECEIVED

    if base is None:
        return Event(
            event_id="fail_closed",
            timestamp="",
            session_id="",
            run_id="",
            layer=layer,
            decision=Decision.PAUSE_FOR_HITL,
            kind=safe_kind,
            reason_code=reason_code,
            conflict_fingerprint="",
            sealed=False,
            overrideable=True,
            final_decider=FINAL_SYSTEM,
            payload={"note": "fail-closed", "original": None},
        )

    return Event(
        event_id=f"{base.event_id}::fail_closed",
        timestamp=base.timestamp,
        session_id=base.session_id,
        run_id=base.run_id,
        layer=layer,
        decision=Decision.PAUSE_FOR_HITL,
        kind=safe_kind,  # enforce pairing + avoid HITL count pollution
        reason_code=reason_code,
        conflict_fingerprint=base.conflict_fingerprint,
        sealed=False,
        overrideable=True,
        final_decider=FINAL_SYSTEM,
        payload={
            "note": "fail-closed",
            "original_kind": base.kind,
            "original_decision": base.decision.value,
            "original_reason_code": base.reason_code,
        },
    )


# =========================
# Counter (Table B) : two-stage firing
# =========================

class HitlCounter:
    """
    P0:
      - Count ONLY if kind == K_HITL_PAUSE
      - Dedupe id = session_id|conflict_fingerprint|event_id (per-session bucket)
      - Emit:
          hitl==3 => K_PLAN_REQUESTED (one-shot, conflict unit)
          hitl==4 => K_END_RECOMMENDED  (one-shot, conflict unit; decision=END_SESSION_RECOMMENDED)
      - Plan-related kinds do NOT count
    Ops P0:
      - dedupe ids are bucketed per session_id; can be dropped on explicit_new_session_start

    P0 invariant (no-op today):
      - Counter-emitted events (PLAN_REQUESTED / END_RECOMMENDED) MUST satisfy kind/decision pairing.
      - Counter never emits fail-closed events; on pairing violation it drops the emit (returns None)
        to avoid audit/log contamination and leaves handling to upper layers.
    """

    def __init__(self, spec: LoopPolicySpec):
        self.spec = spec
        self._seen_by_session: Dict[str, Set[str]] = {}

        self._counts: Dict[str, int] = {}
        self._plan_requested_keys: Set[str] = set()
        self._end_recommended_keys: Set[str] = set()

    @staticmethod
    def _dedupe_id(session_id: str, fp: str, event_id: str) -> str:
        return f"{session_id}|{fp}|{event_id}"

    def _seen(self, session_id: str) -> Set[str]:
        return self._seen_by_session.setdefault(session_id, set())

    def maybe_increment_and_emit(self, e: Event) -> Tuple[int, Optional[Event], Optional[Event]]:
        # caller handles fail-closed; counter stays side-effect-free on invalid keys
        if not validate_min_keys(e):
            return 0, None, None

        ck = conflict_key(e.session_id, e.conflict_fingerprint)

        if e.kind != K_HITL_PAUSE:
            return self._counts.get(ck, 0), None, None

        did = self._dedupe_id(e.session_id, e.conflict_fingerprint, e.event_id)
        seen = self._seen(e.session_id)
        if did in seen:
            return self._counts.get(ck, 0), None, None
        seen.add(did)

        self._counts[ck] = self._counts.get(ck, 0) + 1
        count = self._counts[ck]

        plan_req: Optional[Event] = None
        end_rec: Optional[Event] = None

        if count == self.spec.plan_request_round and ck not in self._plan_requested_keys:
            self._plan_requested_keys.add(ck)
            plan_req = Event(
                event_id=f"{e.event_id}::plan_requested",
                timestamp=e.timestamp,
                session_id=e.session_id,
                run_id=e.run_id,
                layer="mediation",
                decision=Decision.PAUSE_FOR_HITL,
                kind=K_PLAN_REQUESTED,
                reason_code="REL_PLAN_REQUESTED_AFTER_3_HITL",
                conflict_fingerprint=e.conflict_fingerprint,
                sealed=False,
                overrideable=True,
                final_decider=FINAL_SYSTEM,
                payload=None,
            )

        if count == self.spec.hitl_max_rounds and ck not in self._end_recommended_keys:
            self._end_recommended_keys.add(ck)
            end_rec = Event(
                event_id=f"{e.event_id}::end_recommended",
                timestamp=e.timestamp,
                session_id=e.session_id,
                run_id=e.run_id,
                layer="acc_gate",
                decision=Decision.END_SESSION_RECOMMENDED,
                kind=K_END_RECOMMENDED,
                reason_code="ACC_LOOP_BUDGET_EXCEEDED",
                conflict_fingerprint=e.conflict_fingerprint,
                sealed=False,
                overrideable=True,
                final_decider=FINAL_SYSTEM,
                payload=None,
            )

        # P0 no-op insurance: pairing validation for counter-emitted events.
        if plan_req and not validate_kind_decision_pairing(plan_req):
            plan_req = None
        if end_rec and not validate_kind_decision_pairing(end_rec):
            end_rec = None

        return count, plan_req, end_rec

    def reset_if_allowed(self, *, session_id: str, old_fp: str, new_fp: str, reset_reason: str) -> None:
        # P0: explicit_new_session_start overrides "never reset within same conflict"
        if reset_reason == "explicit_new_session_start":
            # drop dedupe bucket
            self._seen_by_session.pop(session_id, None)

            # clear all counters/flags for this session_id
            prefix = f"{session_id}|"
            for ck in list(self._counts.keys()):
                if ck.startswith(prefix):
                    self._counts.pop(ck, None)
                    self._plan_requested_keys.discard(ck)
                    self._end_recommended_keys.discard(ck)
            return

        if self.spec.reset_rules.never_reset_within_same_conflict and old_fp == new_fp:
            return
        if reset_reason not in self.spec.reset_rules.reset_on:
            return

        old_ck = conflict_key(session_id, old_fp)
        self._counts.pop(old_ck, None)
        self._plan_requested_keys.discard(old_ck)
        self._end_recommended_keys.discard(old_ck)


# =========================
# Maestro Terminal (Table A)
# =========================

def enforce_terminal_guard(spec: LoopPolicySpec, state: SessionState, incoming: Event) -> Optional[Event]:
    if not state.is_stopped:
        return None

    # Terminal is the only exception to Fail-Closed standard response
    return Event(
        event_id=f"{incoming.event_id}::terminal_guard",
        timestamp=incoming.timestamp,
        session_id=incoming.session_id,
        run_id=incoming.run_id,
        layer="maestro",
        decision=spec.terminal.decision,
        kind=K_STOPPED,
        reason_code="ACC_STOPPED_IS_TERMINAL",
        conflict_fingerprint=incoming.conflict_fingerprint,
        sealed=True,
        overrideable=False,
        final_decider=FINAL_SYSTEM,
        payload=None,
    )


# =========================
# Plan Flow (Table C) : idempotent conflict unit
# =========================

def maestro_dispatch_plan_request(*, state: SessionState, base_event: Event) -> Optional[Event]:
    """
    C1: on K_PLAN_REQUESTED -> emit K_PLAN_REQ_DISPATCH once per conflict
    """
    if not validate_min_keys(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_MISSING_KEYS, layer="maestro")

    if not validate_kind_decision_pairing(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")

    if base_event.kind != K_PLAN_REQUESTED:
        return None

    ck = conflict_key(base_event.session_id, base_event.conflict_fingerprint)
    if ck in state.plan_request_dispatched_keys:
        return None
    state.plan_request_dispatched_keys.add(ck)

    out = Event(
        event_id=f"{base_event.event_id}::plan_req_dispatch",
        timestamp=base_event.timestamp,
        session_id=base_event.session_id,
        run_id=base_event.run_id,
        layer="maestro",
        decision=Decision.PAUSE_FOR_HITL,
        kind=K_PLAN_REQ_DISPATCH,
        reason_code="MAESTRO_PLAN_REQUEST_DISPATCHED",
        conflict_fingerprint=base_event.conflict_fingerprint,
        sealed=False,
        overrideable=True,
        final_decider=FINAL_SYSTEM,
        payload=None,
    )
    if not validate_kind_decision_pairing(out):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")
    return out


def mediation_propose_plan(*, state: SessionState, base_event: Event, plan_text: str) -> Optional[Event]:
    """
    C2: on K_PLAN_REQ_DISPATCH -> emit K_PLAN_PROPOSED once per conflict
    Fail-closed: if wrong pathway, return None (clean audit; do not emit noise).
    """
    if base_event.kind != K_PLAN_REQ_DISPATCH:
        return None

    if not validate_min_keys(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_MISSING_KEYS, layer="mediation")

    if not validate_kind_decision_pairing(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="mediation")

    ck = conflict_key(base_event.session_id, base_event.conflict_fingerprint)
    if ck in state.plan_proposed_keys:
        return None
    state.plan_proposed_keys.add(ck)

    out = Event(
        event_id=f"{base_event.event_id}::plan_proposed",
        timestamp=base_event.timestamp,
        session_id=base_event.session_id,
        run_id=base_event.run_id,
        layer="mediation",
        decision=Decision.PAUSE_FOR_HITL,
        kind=K_PLAN_PROPOSED,
        reason_code="MEDIATION_PLAN_PROPOSED",
        conflict_fingerprint=base_event.conflict_fingerprint,
        sealed=False,
        overrideable=True,
        final_decider=FINAL_SYSTEM,
        payload={"plan": plan_text},
    )
    if not validate_kind_decision_pairing(out):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="mediation")
    return out


def maestro_ack_plan_received(*, state: SessionState, base_event: Event) -> Optional[Event]:
    """
    C3: on K_PLAN_PROPOSED -> emit K_PLAN_RECEIVED once per conflict
    """
    if base_event.kind != K_PLAN_PROPOSED:
        return None

    if not validate_min_keys(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_MISSING_KEYS, layer="maestro")

    if not validate_kind_decision_pairing(base_event):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")

    ck = conflict_key(base_event.session_id, base_event.conflict_fingerprint)
    if ck in state.plan_received_keys:
        return None
    state.plan_received_keys.add(ck)

    out = Event(
        event_id=f"{base_event.event_id}::plan_received",
        timestamp=base_event.timestamp,
        session_id=base_event.session_id,
        run_id=base_event.run_id,
        layer="maestro",
        decision=Decision.PAUSE_FOR_HITL,
        kind=K_PLAN_RECEIVED,
        reason_code="MAESTRO_PLAN_RECEIVED",
        conflict_fingerprint=base_event.conflict_fingerprint,
        sealed=False,
        overrideable=True,
        final_decider=FINAL_SYSTEM,
        payload=None,
    )
    if not validate_kind_decision_pairing(out):
        return fail_closed_event(base=base_event, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")
    return out


# =========================
# STOP (Table D) : decision+kind gate + idempotent issuance
# =========================

def maestro_maybe_stop(spec: LoopPolicySpec, state: SessionState, e: Event) -> Optional[Event]:
    if not validate_min_keys(e):
        return fail_closed_event(base=e, reason_code=RC_SPEC_MISSING_KEYS, layer="maestro")

    if not validate_kind_decision_pairing(e):
        return fail_closed_event(base=e, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")

    if not (e.decision == Decision.END_SESSION_RECOMMENDED and e.kind == K_END_RECOMMENDED):
        return None

    if state.stop_issued:
        return None

    state.is_stopped = True
    state.stop_issued = True

    stop = Event(
        event_id=f"{e.event_id}::stop",
        timestamp=e.timestamp,
        session_id=e.session_id,
        run_id=e.run_id,
        layer="maestro",
        decision=Decision.STOPPED,
        kind=K_STOPPED,
        reason_code="ACC_END_SESSION_AFTER_4_HITL",
        conflict_fingerprint=e.conflict_fingerprint,
        sealed=True,
        overrideable=False,
        final_decider=FINAL_SYSTEM,
        payload=None,
    )
    if not validate_kind_decision_pairing(stop):
        return fail_closed_event(base=e, reason_code=RC_SPEC_INVALID_INPUT, layer="maestro")
    return stop


# =========================
# Reset semantics (P0 required pair action)
# =========================

def maestro_reset_session_state_on_new_session(state: SessionState) -> None:
    state.is_stopped = False
    state.stop_issued = False
    state.plan_request_dispatched_keys.clear()
    state.plan_proposed_keys.clear()
    state.plan_received_keys.clear()


# =========================
# Minimal Event factory (tests/demo)
# =========================

def mk_event(
    *,
    event_id: str,
    timestamp: str = "2026-01-02T12:00:00+09:00",
    session_id: str = "S1",
    run_id: str = "R1",
    layer: str = "acc_gate",
    decision: Decision = Decision.PAUSE_FOR_HITL,
    kind: str = K_HITL_PAUSE,
    reason_code: str = "SOME_BLOCK",
    conflict_fingerprint: str = "fp1",
) -> Event:
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        session_id=session_id,
        run_id=run_id,
        layer=layer,
        decision=decision,
        kind=kind,
        reason_code=reason_code,
        conflict_fingerprint=conflict_fingerprint,
        sealed=False,
        overrideable=True,
        final_decider=FINAL_SYSTEM,
        payload=None,
    )
