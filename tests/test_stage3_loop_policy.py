# tests/test_stage3_loop_policy.py

from __future__ import annotations

from typing import Any, Optional


from loop_policy_stage3 import (
    Decision,
    LoopPolicySpec,
    SessionState,
    HitlCounter,
    enforce_terminal_guard,
    maestro_maybe_stop,
    maestro_dispatch_plan_request,
    mediation_propose_plan,
    maestro_ack_plan_received,
    maestro_reset_session_state_on_new_session,
    mk_event,
    conflict_key,
    # kinds
    K_HITL_PAUSE,
    K_PLAN_REQUESTED,
    K_PLAN_REQ_DISPATCH,
    K_PLAN_PROPOSED,
    K_PLAN_RECEIVED,
    K_END_RECOMMENDED,
    K_STOPPED,
    _KIND_VALUES,
    _DECISION_VALUES,
    RC_SPEC_INVALID_INPUT,
    RC_SPEC_MISSING_KEYS,
)


def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        _fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _require_is_not_none(value: Any, message: str) -> None:
    if value is None:
        _fail(message)


def test_kind_and_decision_values_do_not_collide() -> None:
    _require(
        _KIND_VALUES.isdisjoint(_DECISION_VALUES),
        "Expected kind values and decision values to be disjoint",
    )


def test_two_stage_firing_and_stop_and_terminal_guard() -> None:
    spec = LoopPolicySpec(hitl_max_rounds=4, plan_request_round=3)
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")
    fp = "fp:X"
    plan_events = []
    end_events = []

    for i in range(1, 5):
        e = mk_event(
            event_id=f"E{i}",
            conflict_fingerprint=fp,
            kind=K_HITL_PAUSE,
            decision=Decision.PAUSE_FOR_HITL,
        )
        count, plan_req, end_rec = counter.maybe_increment_and_emit(e)
        _require_equal(count, i, "Expected count to match loop index")
        if plan_req:
            plan_events.append(plan_req)
        if end_rec:
            end_events.append(end_rec)

    _require_equal(len(plan_events), 1, "Expected exactly one plan request event")
    _require_equal(plan_events[0].kind, K_PLAN_REQUESTED, "Unexpected plan request kind")
    _require_equal(
        plan_events[0].decision,
        Decision.PAUSE_FOR_HITL,
        "Unexpected plan request decision",
    )

    _require_equal(len(end_events), 1, "Expected exactly one end recommendation event")
    _require_equal(end_events[0].kind, K_END_RECOMMENDED, "Unexpected end recommendation kind")
    _require_equal(
        end_events[0].decision,
        Decision.END_SESSION_RECOMMENDED,
        "Unexpected end recommendation decision",
    )

    stop = maestro_maybe_stop(spec, state, end_events[0])

    assert stop is not None
    assert stop.kind == K_STOPPED
    assert stop.decision == Decision.STOPPED
    assert stop.sealed is True
    assert stop.overrideable is False

    _require_is_not_none(stop, "Expected maestro_maybe_stop to return a stop event")
    _require_equal(stop.kind, K_STOPPED, "Unexpected stop kind")
    _require_equal(stop.decision, Decision.STOPPED, "Unexpected stop decision")
    _require(stop.sealed is True, "Expected stop event to be sealed")
    _require(stop.overrideable is False, "Expected sealed stop to be non-overrideable")


    after = mk_event(
        event_id="E_after",
        conflict_fingerprint=fp,
        kind=K_HITL_PAUSE,
    )
    guarded = enforce_terminal_guard(spec, state, after)
    _require_is_not_none(guarded, "Expected terminal guard to fire after stop")
    _require_equal(guarded.decision, Decision.STOPPED, "Unexpected guarded decision")
    _require_equal(guarded.kind, K_STOPPED, "Unexpected guarded kind")


def test_plan_flow_idempotent_and_does_not_pollute_hitl_count() -> None:
    spec = LoopPolicySpec()
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")
    fp = "fp:plan"

    plan_req = None

    plan_req: Optional[Any] = None


    for i in range(1, 4):
        e = mk_event(
            event_id=f"H{i}",
            conflict_fingerprint=fp,
            kind=K_HITL_PAUSE,
        )
        count, pr, end_rec = counter.maybe_increment_and_emit(e)
        _require_equal(count, i, "Expected HITL count to increment")
        if pr:
            plan_req = pr
        _require(end_rec is None, "Did not expect end recommendation before threshold")

    _require_is_not_none(plan_req, "Expected a plan request event on round 3")
    _require_equal(plan_req.kind, K_PLAN_REQUESTED, "Unexpected plan request kind")

    d1 = maestro_dispatch_plan_request(state=state, base_event=plan_req)
    d2 = maestro_dispatch_plan_request(state=state, base_event=plan_req)
    _require(d1 is not None and d1.kind == K_PLAN_REQ_DISPATCH, "Expected first dispatch to succeed")
    _require(d2 is None, "Expected second dispatch to be idempotent and return None")

    p1 = mediation_propose_plan(state=state, base_event=d1, plan_text="p")
    p2 = mediation_propose_plan(state=state, base_event=d1, plan_text="p")
    _require(p1 is not None and p1.kind == K_PLAN_PROPOSED, "Expected first plan proposal to succeed")
    _require(p2 is None, "Expected second plan proposal to be idempotent and return None")

    a1 = maestro_ack_plan_received(state=state, base_event=p1)
    a2 = maestro_ack_plan_received(state=state, base_event=p1)
    _require(a1 is not None and a1.kind == K_PLAN_RECEIVED, "Expected first ack to succeed")
    _require(a2 is None, "Expected second ack to be idempotent and return None")

    before = counter._counts.get(f"S1|{fp}", 0)
    for ev in [plan_req, d1, p1, a1]:
        c, pr, er = counter.maybe_increment_and_emit(ev)
        _require_equal(c, before, "Plan-flow events must not increment HITL count")
        _require(pr is None, "Plan-flow events must not emit plan request")
        _require(er is None, "Plan-flow events must not emit end recommendation")


def test_fail_closed_on_missing_keys() -> None:
    state = SessionState(session_id="S1")
    bogus = mk_event(
        event_id="",
        session_id="",
        conflict_fingerprint="",
        kind=K_PLAN_REQUESTED,
    )
    out = maestro_dispatch_plan_request(state=state, base_event=bogus)
    _require_is_not_none(out, "Expected fail-closed output on missing keys")
    _require_equal(out.decision, Decision.PAUSE_FOR_HITL, "Unexpected fail-closed decision")
    _require_equal(out.reason_code, RC_SPEC_MISSING_KEYS, "Unexpected reason_code for missing keys")
    _require(out.sealed is False, "Missing-keys fail-close must not be sealed")
    _require(out.overrideable is True, "Missing-keys fail-close must be overrideable")


def test_fail_closed_on_invalid_kind_decision_pair() -> None:
    spec = LoopPolicySpec()
    state = SessionState(session_id="S1")
    fp = "fp:badpair"
    bad = mk_event(
        event_id="X",
        conflict_fingerprint=fp,
        kind=K_END_RECOMMENDED,
        decision=Decision.PAUSE_FOR_HITL,  # invalid pairing
    )
    out = maestro_maybe_stop(spec, state, bad)
    _require_is_not_none(out, "Expected fail-closed output on invalid pair")
    _require_equal(out.decision, Decision.PAUSE_FOR_HITL, "Unexpected fail-closed decision")
    _require_equal(out.reason_code, RC_SPEC_INVALID_INPUT, "Unexpected reason_code for invalid pair")
    _require(out.sealed is False, "Invalid-pair fail-close must not be sealed")
    _require(out.overrideable is True, "Invalid-pair fail-close must be overrideable")
    _require_equal(out.kind, K_PLAN_RECEIVED, "Unexpected fail-closed kind")


def test_explicit_new_session_start_pair_action() -> None:
    spec = LoopPolicySpec()
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")
    old_fp = "fp_old"
    new_fp = "fp_new"

    for i in range(1, 4):
        e = mk_event(
            event_id=f"E{i}",
            conflict_fingerprint=old_fp,
            kind=K_HITL_PAUSE,
        )
        counter.maybe_increment_and_emit(e)

    ck = conflict_key("S1", old_fp)
    state.plan_request_dispatched_keys.add(ck)
    state.plan_proposed_keys.add(ck)
    state.plan_received_keys.add(ck)
    state.is_stopped = True
    state.stop_issued = True

    counter.reset_if_allowed(
        session_id="S1",
        old_fp=old_fp,
        new_fp=new_fp,
        reset_reason="explicit_new_session_start",
    )
    maestro_reset_session_state_on_new_session(state)

    _require(state.is_stopped is False, "Expected stopped flag to reset")
    _require(state.stop_issued is False, "Expected stop_issued flag to reset")
    _require_equal(
        len(state.plan_request_dispatched_keys),
        0,
        "Expected dispatched key set to reset",
    )
    _require_equal(
        len(state.plan_proposed_keys),
        0,
        "Expected proposed key set to reset",
    )
    _require_equal(
        len(state.plan_received_keys),
        0,
        "Expected received key set to reset",
    )
