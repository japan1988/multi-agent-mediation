# tests/test_mediation_emergency_contract_sim_v4_1.py
# -*- coding: utf-8 -*-
"""
Pytest for mediation_emergency_contract_sim_v4_1.py

Covers:
- NORMAL -> CONTRACT_EFFECTIVE (not sealed)
- FABRICATE -> STOPPED + sealed=True (sealed in ethics_gate)
- RFL_STOP -> STOPPED + sealed=False (user stops at RFL HITL)

Run only this test file:
  pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
"""

from __future__ import annotations

from pathlib import Path
import pytest

import mediation_emergency_contract_sim_v4_1 as sim


def _patch_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Avoid writing trust/grant json files to repo root during CI.
    The sim module keeps file Paths as module-level constants, so we patch them.
    """
    monkeypatch.setattr(sim, "TRUST_STORE_PATH", tmp_path / "model_trust_store.json", raising=True)
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", tmp_path / "model_grants.json", raising=True)


def test_normal_contract_effective(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stores(tmp_path, monkeypatch)

    # runs=1 => SIM#B001 (no RFL pause trigger)
    results = sim.run_simulation(runs=1, fabricate=False, hitl_rfl="continue")
    r0 = results["runs"][0]

    assert r0["run_id"] == "SIM#B001"
    assert r0["sealed"] is False
    assert r0["final_state"] == "CONTRACT_EFFECTIVE"

    # sanity: ARL contains contract_effect entry
    layers = [row["layer"] for row in r0["arl"]]
    assert sim.LAYER_CONTRACT_EFFECT in layers


def test_fabrication_seals_in_ethics_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stores(tmp_path, monkeypatch)

    results = sim.run_simulation(runs=1, fabricate=True, hitl_rfl="continue")
    r0 = results["runs"][0]

    assert r0["run_id"] == "SIM#B001"
    assert r0["final_state"] == "STOPPED"
    assert r0["sealed"] is True

    # evidence gate must not seal; ethics gate must seal
    ev_rows = [row for row in r0["arl"] if row["layer"] == sim.LAYER_EVIDENCE]
    et_rows = [row for row in r0["arl"] if row["layer"] == sim.LAYER_ETHICS]

    assert ev_rows, "expected evidence_gate row"
    assert et_rows, "expected ethics_gate row"

    assert ev_rows[-1]["reason_code"] == sim.RC_EVIDENCE_FABRICATION
    assert ev_rows[-1]["sealed"] is False  # rule: sealing reserved for Ethics/ACC only

    assert et_rows[-1]["reason_code"] == sim.RC_EVIDENCE_FABRICATION
    assert et_rows[-1]["sealed"] is True   # sealing happens here


def test_rfl_stop_is_non_sealed_user_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stores(tmp_path, monkeypatch)

    # runs=2 includes SIM#B002 => triggers RFL pause
    results = sim.run_simulation(runs=2, fabricate=False, hitl_rfl="stop")
    r1 = results["runs"][1]

    assert r1["run_id"] == "SIM#B002"
    assert r1["final_state"] == "STOPPED"
    assert r1["sealed"] is False  # RFL stop is non-sealed

    rfl_rows = [row for row in r1["arl"] if row["layer"] == sim.LAYER_RFL]
    finalize_rows = [row for row in r1["arl"] if row["layer"] == sim.LAYER_HITL_RFL_FINALIZE]

    assert rfl_rows, "expected relativity_gate row"
    assert finalize_rows, "expected hitl_finalize_rfl row"

    assert rfl_rows[-1]["decision"] == sim.DECISION_PAUSE
    assert rfl_rows[-1]["sealed"] is False
    assert rfl_rows[-1]["overrideable"] is True

    assert finalize_rows[-1]["final_decider"] == sim.DECIDER_USER
    assert finalize_rows[-1]["reason_code"] == sim.RC_HITL_STOP
