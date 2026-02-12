# -*- coding: utf-8 -*-
"""pytest tests for mediation_emergency_contract_sim_v4_1.py

How to run ONLY this file (do not run other tests):
  pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py

Run a single test by node id:
  pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py::test_normal_run_reaches_effective_and_is_not_sealed

Filter within this file:
  pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py -k "fabricated or rfl"

Tip: confirm collection scope:
  pytest -q --collect-only tests/test_mediation_emergency_contract_sim_v4_1.py
"""

import pytest

import mediation_emergency_contract_sim_v4_1 as sim


def _extract_layers(arl):
    return [r["layer"] for r in arl]


def _find_rows(arl, layer=None, reason_code=None, decision=None):
    out = []
    for r in arl:
        if layer is not None and r["layer"] != layer:
            continue
        if reason_code is not None and r["reason_code"] != reason_code:
            continue
        if decision is not None and r["decision"] != decision:
            continue
        out.append(r)
    return out


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    # The simulation writes trust/grant stores to CWD. Isolate per test.
    monkeypatch.chdir(tmp_path)
    yield


def test_normal_run_reaches_effective_and_is_not_sealed():
    sim.ensure_default_grant_exists()
    trust = sim.load_trust_state()
    st, audit, trust = sim.simulate_run(
        run_id="SIM#B001",
        trust=trust,
        fabricate_evidence=False,
        hitl_rfl="continue",
    )

    assert st.state == "CONTRACT_EFFECTIVE"
    assert st.sealed is False

    layers = _extract_layers(audit.rows)

    # Layer existence check
    must_exist = [
        sim.LAYER_MEANING,
        sim.LAYER_CONSISTENCY,
        sim.LAYER_RFL,
        sim.LAYER_EVIDENCE,
        sim.LAYER_ETHICS,
        sim.LAYER_ACC,
        sim.LAYER_TRUST,
        sim.LAYER_HITL_AUTH,
        sim.LAYER_DOC_DRAFT,
        sim.LAYER_DRAFT_LINT,
        sim.LAYER_HITL_FINALIZE,
        sim.LAYER_TRUST_UPDATE,
        sim.LAYER_CONTRACT_EFFECT,
    ]
    for lay in set(must_exist):
        assert lay in layers

    lint_ok = _find_rows(
        audit.rows,
        layer=sim.LAYER_DRAFT_LINT,
        reason_code=sim.RC_DRAFT_LINT_OK,
    )
    assert lint_ok and lint_ok[-1]["decision"] == sim.DECISION_RUN

    # Trust positive cap: +0.01 (auth) +0.02 (finalize) == 0.03 max per run
    assert pytest.approx(trust.trust_score, rel=1e-9, abs=1e-9) == sim.TRUST_INIT + 0.03


def test_fabricated_evidence_seals_at_ethics_not_at_evidence():
    sim.ensure_default_grant_exists()
    trust = sim.load_trust_state()
    st, audit, trust = sim.simulate_run(
        run_id="SIM#B001",
        trust=trust,
        fabricate_evidence=True,
        hitl_rfl="continue",
    )

    assert st.state == "STOPPED"
    assert st.sealed is True

    # Evidence gate flags fabrication but must NOT seal
    ev_rows = _find_rows(
        audit.rows,
        layer=sim.LAYER_EVIDENCE,
        reason_code=sim.RC_EVIDENCE_FABRICATION,
    )
    assert ev_rows, "expected evidence fabrication row"
    assert ev_rows[-1]["sealed"] is False
    assert ev_rows[-1]["decision"] == sim.DECISION_RUN

    # Ethics gate seals
    eth_rows = _find_rows(
        audit.rows,
        layer=sim.LAYER_ETHICS,
        reason_code=sim.RC_EVIDENCE_FABRICATION,
    )
    assert eth_rows, "expected ethics fabrication row"
    assert eth_rows[-1]["sealed"] is True
    assert eth_rows[-1]["decision"] == sim.DECISION_STOP
    assert eth_rows[-1]["overrideable"] is False
    assert eth_rows[-1]["final_decider"] == sim.DECIDER_SYSTEM

    # Trust should decrease by DELTA_INVALID_EVENT
    assert pytest.approx(trust.trust_score, rel=1e-9, abs=1e-9) == sim.TRUST_INIT + sim.DELTA_INVALID_EVENT


def test_rfl_pause_then_user_stop_ends_without_seal():
    sim.ensure_default_grant_exists()
    trust = sim.load_trust_state()
    st, audit, trust = sim.simulate_run(
        run_id="SIM#B002",
        trust=trust,
        fabricate_evidence=False,
        hitl_rfl="stop",
    )

    assert st.state == "STOPPED"
    assert st.sealed is False

    rfl = _find_rows(
        audit.rows,
        layer=sim.LAYER_RFL,
        reason_code=sim.RC_REL_BOUNDARY_UNSTABLE,
    )
    assert rfl and rfl[-1]["decision"] == sim.DECISION_PAUSE
    assert rfl[-1]["sealed"] is False
    assert rfl[-1]["overrideable"] is True

    fin = _find_rows(
        audit.rows,
        layer=sim.LAYER_HITL_RFL_FINALIZE,
        reason_code=sim.RC_HITL_STOP,
    )
    assert fin and fin[-1]["final_decider"] == sim.DECIDER_USER
    assert fin[-1]["sealed"] is False
    assert fin[-1]["decision"] == sim.DECISION_STOP
