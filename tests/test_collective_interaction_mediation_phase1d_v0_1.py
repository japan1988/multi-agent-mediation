from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D_PATH = ROOT / "experiments" / "phase1" / "collective_interaction_mediation_phase1d_v0_1.py"


def _load_d():
    spec = importlib.util.spec_from_file_location("phase1d_under_test", D_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase1d_collective_interaction_and_mediation(tmp_path):
    d = _load_d()
    summary = d.run_full_simulation(tmp_path)

    # Phase 1C remains intact.
    assert summary["c_regression"]["decision"] == "ALLOW"
    assert summary["c_regression"]["c_specific_total"] == 17
    assert summary["c_regression"]["c_specific_passed"] == 17
    assert summary["c_regression"]["c_specific_failed"] == 0

    # New composition suite.
    assert summary["composition"]["total"] == 10
    assert summary["composition"]["passed"] == 10
    assert summary["composition"]["failed"] == 0
    assert all(summary["composition"]["emergent_checks"].values())
    assert all(summary["safety_checks"].values())
    assert summary["decision"] == "ALLOW"


def test_phase1d_local_allow_can_become_collective_pause():
    d = _load_d()
    gate = d.CollectiveMediationGate()
    ctx = d.CollectiveContext(
        "TX-TEST-SCOPE",
        (
            d.LocalAction("A1", "AGENT-A", "NORMALIZE", "REQUEST", "REQUEST", 0.2),
            d.LocalAction(
                "B1",
                "AGENT-B",
                "SHARE_SUMMARY",
                "REQUEST",
                "USER_DECISION",
                0.0,
                "BOARD-X",
                "BIND-X",
            ),
        ),
    )

    result = gate.evaluate(ctx)
    assert result.local_all_allowed is True
    assert result.decision == d.PAUSE
    assert result.reason_code == d.COMPOSITE_SCOPE_EXPANSION
    assert result.mediation_plan is not None
    assert result.mediation_plan.auto_apply is False
    assert result.mediation_plan.human_action_required is True


def test_phase1d_repair_requires_explicit_user_approval():
    d = _load_d()
    gate = d.CollectiveMediationGate()
    ctx = d.CollectiveContext(
        "TX-TEST-BUDGET",
        (
            d.LocalAction("A1", "AGENT-A", "NORMALIZE", "REQUEST", "REQUEST", 0.4),
            d.LocalAction("B1", "AGENT-B", "SUMMARIZE", "REQUEST", "REQUEST", 0.4),
            d.LocalAction("C1", "AGENT-C", "NORMALIZE", "REQUEST", "REQUEST", 0.4),
        ),
    )

    paused = gate.evaluate(ctx)
    assert paused.decision == d.PAUSE
    assert paused.reason_code == d.CUMULATIVE_CHANGE_BUDGET_EXCEEDED

    rejected = d.apply_user_repair(
        ctx,
        paused,
        user_decision=d.USER_REJECT_REPAIR,
        approved_action_ids=("A1", "B1"),
    )
    assert rejected == ctx
    assert gate.evaluate(rejected).decision == d.PAUSE

    approved = d.apply_user_repair(
        ctx,
        paused,
        user_decision=d.USER_APPROVE_REPAIR,
        approved_action_ids=("A1", "B1"),
    )
    recovered = gate.evaluate(approved)
    assert recovered.decision == d.ALLOW
    assert recovered.reason_code == d.USER_REPAIR_VALIDATED


def test_phase1d_collective_authority_expansion_fails_closed():
    d = _load_d()
    gate = d.CollectiveMediationGate()
    ctx = d.CollectiveContext(
        "TX-TEST-AUTH",
        (
            d.LocalAction("A1", "AGENT-A", "ADVISE", "POLICY", "POLICY"),
            d.LocalAction("B1", "AGENT-B", "ROUTE_REVIEW", "POLICY", "REVIEW"),
            d.LocalAction("C1", "AGENT-C", "FINALIZE_CANDIDATE", "REVIEW", "USER_DECISION"),
        ),
    )

    result = gate.evaluate(ctx)
    assert result.local_all_allowed is True
    assert result.decision == d.BLOCK
    assert result.reason_code == d.COLLECTIVE_AUTHORITY_EXPANSION
    assert result.final is True
    assert result.retry_allowed is False

    # In-place repair is intentionally unavailable for this class.
    unchanged = d.apply_user_repair(
        ctx,
        result,
        user_decision=d.USER_APPROVE_REPAIR,
    )
    assert unchanged == ctx
