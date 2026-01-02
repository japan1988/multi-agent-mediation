# tests/test_stage3_loop_policy.py
import pytest

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


def test_kind_and_decision_values_do_not_collide():
    assert _KIND_VALUES.isdisjoint(_DECISION_VALUES)


def test_two_stage_firing_and_stop_and_terminal_guard():
    spec = LoopPolicySpec(hitl_max_rounds=4, plan_request_round=3)
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")

    fp = "fp:X"
    plan_events = []
    end_events = []

    for i in range(1, 5):
        e = mk_event(event_id=f"E{i}", conflict_fingerprint=fp, kind=K_HITL_PAUSE, decision=Decision.PAUSE_FOR_HITL)
        count, plan_req, end_rec = counter.maybe_increment_and_emit(e)
        assert count == i
        if plan_req:
            plan_events.append(plan_req)
        if end_rec:
            end_events.append(end_rec)

    assert len(plan_events) == 1
    assert plan_events[0].kind == K_PLAN_REQUESTED
    assert plan_events[0].decision == Decision.PAUSE_FOR_HITL

    assert len(end_events) == 1
    assert end_events[0].kind == K_END_RECOMMENDED
    assert end_events[0].decision == Decision.END_SESSION_RECOMMENDED

    stop = maestro_maybe_stop(spec, state, end_events[0])
    assert stop is not None
    assert stop.kind == K_STOPPED
    assert stop.decision == Decision.STOPPED
    assert stop.sealed is True
    assert stop.overrideable is False

    after = mk_event(event_id="E_after", conflict_fingerprint=fp, kind=K_HITL_PAUSE)
    guarded = enforce_terminal_guard(spec, state, after)
    assert guarded is not None
    assert guarded.decision == Decision.STOPPED
    assert guarded.kind == K_STOPPED


def test_plan_flow_idempotent_and_does_not_pollute_hitl_count():
    spec = LoopPolicySpec()
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")
    fp = "fp:plan"

    plan_req = None
    for i in range(1, 4):
        e = mk_event(event_id=f"H{i}", conflict_fingerprint=fp, kind=K_HITL_PAUSE)
        count, pr, end_rec = counter.maybe_increment_and_emit(e)
        assert count == i
        if pr:
            plan_req = pr
        assert end_rec is None

    assert plan_req is not None
    assert plan_req.kind == K_PLAN_REQUESTED

    d1 = maestro_dispatch_plan_request(state=state, base_event=plan_req)
    d2 = maestro_dispatch_plan_request(state=state, base_event=plan_req)
    assert d1 is not None and d1.kind == K_PLAN_REQ_DISPATCH
    assert d2 is None

    p1 = mediation_propose_plan(state=state, base_event=d1, plan_text="p")
    p2 = mediation_propose_plan(state=state, base_event=d1, plan_text="p")
    assert p1 is not None and p1.kind == K_PLAN_PROPOSED
    assert p2 is None

    a1 = maestro_ack_plan_received(state=state, base_event=p1)
    a2 = maestro_ack_plan_received(state=state, base_event=p1)
    assert a1 is not None and a1.kind == K_PLAN_RECEIVED
    assert a2 is None

    before = counter._counts.get(f"S1|{fp}", 0)
    for ev in [plan_req, d1, p1, a1]:
        c, pr, er = counter.maybe_increment_and_emit(ev)
        assert c == before
        assert pr is None
        assert er is None


def test_fail_closed_on_missing_keys():
    state = SessionState(session_id="S1")

    bogus = mk_event(event_id="", session_id="", conflict_fingerprint="", kind=K_PLAN_REQUESTED)
    out = maestro_dispatch_plan_request(state=state, base_event=bogus)
    assert out is not None
    assert out.decision == Decision.PAUSE_FOR_HITL
    assert out.reason_code == RC_SPEC_MISSING_KEYS
    assert out.sealed is False
    assert out.overrideable is True


def test_fail_closed_on_invalid_kind_decision_pair():
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
    assert out is not None
    assert out.decision == Decision.PAUSE_FOR_HITL
    assert out.reason_code == RC_SPEC_INVALID_INPUT
    assert out.sealed is False
    assert out.overrideable is True
    # fail-closed kind must be non-counting and pairing-safe
    assert out.kind == K_PLAN_RECEIVED


def test_explicit_new_session_start_pair_action():
    spec = LoopPolicySpec()
    counter = HitlCounter(spec)
    state = SessionState(session_id="S1")

    old_fp = "fp_old"
    new_fp = "fp_new"

    for i in range(1, 4):
        e = mk_event(event_id=f"E{i}", conflict_fingerprint=old_fp, kind=K_HITL_PAUSE)
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

    assert state.is_stopped is False
    assert state.stop_issued is False
    assert len(state.plan_request_dispatched_keys) == 0
    assert len(state.plan_proposed_keys) == 0
    assert len(state.plan_received_keys) == 0
