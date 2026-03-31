# -*- coding: utf-8 -*-

import kage_definition_hitl_gate_v1 as mod


def test_gray_goes_to_hitl_and_user_approves_logged():
    audit = mod.AuditLog()
    run_id = "TEST#GRAY_APPROVE"

    candidate = {
        # 3/5 => GRAY by thresholds
        "task_decomposition": True,
        "routing": True,
        "guardrails_fail_closed": True,
        "audit_reason_codes": False,
        "hitl_escalation": False,
        # safety flags off
        "autonomous_external_actions": False,
        "pii_seeking_behavior": False,
        "manipulation_or_reeducation_intent": False,
    }

    g = mod.definition_gate(run_id=run_id, candidate=candidate, audit=audit)
    assert g.decision == "PAUSE_FOR_HITL"
    assert g.reason_code == "DEFINITION_AMBIGUOUS"

    g2 = mod.apply_hitl_choice(
        run_id=run_id,
        gate_result=g,
        choice="APPROVE",
        audit=audit,
        user_id="creator",
    )
    assert g2.decision == "RUN"
    assert g2.reason_code == "HITL_APPROVED"

    # Audit: must contain two events (gate + finalize)
    assert len(audit.records) == 2
    assert audit.records[0]["layer"] == "definition_gate"
    assert audit.records[1]["layer"] == "hitl_finalize"
    assert audit.records[1]["evidence"]["final_decider"] == "USER"
    assert audit.records[1]["evidence"]["final_choice"] == "APPROVE"


def test_in_passes_without_hitl():
    audit = mod.AuditLog()
    run_id = "TEST#IN"

    candidate = {
        # 5/5 => IN
        "task_decomposition": True,
        "routing": True,
        "guardrails_fail_closed": True,
        "audit_reason_codes": True,
        "hitl_escalation": True,
        # safety flags off
        "autonomous_external_actions": False,
        "pii_seeking_behavior": False,
        "manipulation_or_reeducation_intent": False,
    }

    g = mod.definition_gate(run_id=run_id, candidate=candidate, audit=audit)
    assert g.decision == "RUN"
    assert g.reason_code == "DEF_IN"
    assert len(audit.records) == 1


def test_out_is_stopped():
    audit = mod.AuditLog()
    run_id = "TEST#OUT"

    candidate = {
        # 2/5 => OUT
        "task_decomposition": True,
        "routing": True,
        "guardrails_fail_closed": False,
        "audit_reason_codes": False,
        "hitl_escalation": False,
        # safety flags off
        "autonomous_external_actions": False,
        "pii_seeking_behavior": False,
        "manipulation_or_reeducation_intent": False,
    }

    g = mod.definition_gate(run_id=run_id, candidate=candidate, audit=audit)
    assert g.decision == "STOPPED"
    assert g.reason_code == "DEF_OUT"


def test_safety_red_flag_is_non_overridable_even_if_user_approves():
    audit = mod.AuditLog()
    run_id = "TEST#SAFETY"

    candidate = {
        # could be IN by definition, but safety blocks
        "task_decomposition": True,
        "routing": True,
        "guardrails_fail_closed": True,
        "audit_reason_codes": True,
        "hitl_escalation": True,
        # safety flags ON
        "autonomous_external_actions": True,
        "pii_seeking_behavior": False,
        "manipulation_or_reeducation_intent": False,
    }

    g = mod.definition_gate(run_id=run_id, candidate=candidate, audit=audit)
    assert g.decision == "STOPPED"
    assert g.reason_code == "SAFETY_RED_FLAG"

    g2 = mod.apply_hitl_choice(
        run_id=run_id,
        gate_result=g,
        choice="APPROVE",
        audit=audit,
        user_id="creator",
    )
    assert g2.decision == "STOPPED"
    assert g2.reason_code == "NON_OVERRIDABLE_SAFETY"

    # Audit: gate + finalize
    assert len(audit.records) == 2
    assert audit.records[1]["evidence"]["final_decider"] == "SYSTEM"
    assert audit.records[1]["reason_code"] == "NON_OVERRIDABLE_SAFETY"
