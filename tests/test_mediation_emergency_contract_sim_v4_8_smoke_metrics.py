# tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter

import mediation_emergency_contract_sim_v4_8 as sim


def _aggregate(results: dict) -> dict:
    """Compute deterministic aggregates (ignore timestamps / ids)."""
    runs = results.get("runs", []) or []
    by_state = Counter(r.get("final_state") for r in runs)

    coaching = {
        "auth_required": 0,
        "approved": 0,
        "check_passed": 0,
        "skipped": 0,
    }
    sealed_by_layer = Counter()

    for r in runs:
        arl = r.get("arl", []) or []
        for row in arl:
            layer = row.get("layer")
            rc = row.get("reason_code")
            sealed = bool(row.get("sealed", False))
            if sealed:
                sealed_by_layer[layer] += 1

            if rc == sim.RC_COACHING_AUTH_REQUIRED:
                coaching["auth_required"] += 1
            elif rc == sim.RC_COACHING_APPROVE:
                coaching["approved"] += 1
            elif rc == sim.RC_COACHING_CHECK_PASSED:
                coaching["check_passed"] += 1
            elif rc == sim.RC_COACHING_SKIPPED:
                coaching["skipped"] += 1

    return {
        "by_state": dict(by_state),
        "coaching": coaching,
        "sealed_by_layer": dict(sealed_by_layer),
        "trust_after": results.get("trust_after", {}),
        "eval_after": results.get("eval_after", {}),
    }


def test_v48_run_simulation_smoke_and_invariants():
    # Reset makes the run reproducible wrt stored state.
    r = sim.run_simulation(runs=50, fabricate=False, reset=True, reset_eval=True)

    assert "runs" in r and isinstance(r["runs"], list)
    assert len(r["runs"]) == 50

    agg = _aggregate(r)

    # Core invariants should hold: sealed only by ethics/acc.
    for layer, cnt in agg["sealed_by_layer"].items():
        assert layer in (sim.LAYER_ETHICS, sim.LAYER_ACC)

    # With fabricate=False and current pipeline, runs should reach CONTRACT_EFFECTIVE.
    # (If you later add mutations / failure injection, this may change and should be
    # asserted more flexibly.)
    assert agg["by_state"].get("CONTRACT_EFFECTIVE", 0) == 50

    # Coaching should trigger at least once early because TRUST_INIT=0.90 < COACHING_TRUST_BELOW=0.93.
    assert agg["coaching"]["auth_required"] > 0
    assert agg["coaching"]["approved"] > 0
    assert agg["coaching"]["check_passed"] > 0


def test_v48_determinism_of_key_aggregates_under_reset():
    r1 = sim.run_simulation(runs=80, fabricate=False, reset=True, reset_eval=True)
    r2 = sim.run_simulation(runs=80, fabricate=False, reset=True, reset_eval=True)

    a1 = _aggregate(r1)
    a2 = _aggregate(r2)

    assert a1["by_state"] == a2["by_state"]
    assert a1["coaching"] == a2["coaching"]

    # Trust & eval after should also match (they are deterministic here).
    assert a1["trust_after"] == a2["trust_after"]
    assert a1["eval_after"] == a2["eval_after"]
