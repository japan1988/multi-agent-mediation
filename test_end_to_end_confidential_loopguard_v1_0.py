# -*- coding: utf-8 -*-
"""
tests/test_end_to_end_confidential_loopguard_v1_0.py

End-to-end test:
- Agent leaks confidential info -> Mediator requests revision -> Orchestrator notifies user (HITL)
- Loop-guard:
  - 3rd occurrence -> warn + hitl_finalize ACK
  - 4th occurrence -> STOP session (fail-closed)
- Assert: events are emitted (発火) and ARL never stores PII.
"""

from __future__ import annotations

import json
import re

import pytest

import kage_end_to_end_confidential_loopguard_v1_0 as sim


def _events(audit: sim.AuditLog):
    return [e for e in audit.events]


def _find(audit: sim.AuditLog, *, layer: str, reason_code: str):
    return [e for e in audit.events if e.layer == layer and e.reason_code == reason_code]


def _assert_no_pii_in_arl(audit: sim.AuditLog):
    blob = audit.to_jsonl()
    assert not sim.EMAIL_RE.search(blob), "email-like string leaked into ARL"
    assert not sim.SECRET_RE.search(blob), "secret_token leaked into ARL"
    # Also ensure JSON is well-formed per line
    for line in blob.splitlines():
        json.loads(line)


def test_end_to_end_warn_on_3rd_and_end_on_4th():
    audit = sim.AuditLog()
    orch = sim.Orchestrator(max_same_issue=4)
    res = orch.run_episode(
        run_id="TEST#E2E",
        agent=sim.Agent(always_leak=True),
        mediator=sim.Mediator(),
        audit=audit,
        hitl_choice_on_warn="ACK",
    )

    # Final must be STOPPED due to 4th repeat
    assert res.final_decision == "STOPPED"
    assert res.revision_count >= 4

    # 4 times mediator revision request (PAUSE_FOR_HITL)
    med_reqs = _find(audit, layer="mediator_advice", reason_code=sim.RC_MEDIATOR_REVISION_REQUEST_CONFIDENTIAL)
    assert len(med_reqs) >= 4

    # Loop-guard: warn at 3rd
    warn = _find(audit, layer="rrl_loop_guard", reason_code=sim.RC_HITL_WARN_REV3)
    assert len(warn) == 1
    warn_notify = _find(audit, layer="hitl_notify_user", reason_code=sim.RC_HITL_WARN_REV3)
    assert len(warn_notify) == 1
    ack = _find(audit, layer="hitl_finalize", reason_code=sim.RC_HITL_ACK)
    assert len(ack) == 1

    # Loop-guard: stop at 4th
    stop = _find(audit, layer="rrl_loop_guard", reason_code=sim.RC_MAX_REV_EXCEEDED)
    assert len(stop) == 1
    ended = _find(audit, layer="hitl_notify_user", reason_code=sim.RC_HITL_NOTIFY_SESSION_ENDED)
    assert len(ended) == 1
    session_end = _find(audit, layer="session_end", reason_code=sim.RC_SESSION_END)
    assert len(session_end) == 1

    # Event flow sanity: must contain revision notify events too (attempt 1/2 and possibly 3)
    rev_notify = _find(audit, layer="hitl_notify_user", reason_code=sim.RC_HITL_NOTIFY_REVISION)
    assert len(rev_notify) >= 2

    _assert_no_pii_in_arl(audit)


@pytest.mark.parametrize("choice,expected_final", [("STOP", "STOPPED"), ("ACK", "STOPPED")])
def test_user_can_stop_on_warn(choice, expected_final):
    audit = sim.AuditLog()
    orch = sim.Orchestrator(max_same_issue=4)
    res = orch.run_episode(
        run_id=f"TEST#WARN#{choice}",
        agent=sim.Agent(always_leak=True),
        mediator=sim.Mediator(),
        audit=audit,
        hitl_choice_on_warn=choice,  # STOP ends earlier on 3rd
    )
    assert res.final_decision == expected_final
    _assert_no_pii_in_arl(audit)
