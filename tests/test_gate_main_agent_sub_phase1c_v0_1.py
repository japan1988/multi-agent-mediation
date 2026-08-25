from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C_PATH = ROOT / "experiments" / "phase1" / "gate_main_agent_sub_phase1c_v0_1.py"


def _load_c():
    spec = importlib.util.spec_from_file_location("phase1c_under_test", C_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase1c_full_complementarity_simulation(tmp_path):
    c = _load_c()
    summary = c.run_full_simulation(tmp_path)

    assert summary["a_regression"]["total"] == 17
    assert summary["a_regression"]["passed"] == 17
    assert summary["a_regression"]["failed"] == 0

    assert summary["b_regression"]["total"] == 17
    assert summary["b_regression"]["passed"] == 17
    assert summary["b_regression"]["failed"] == 0

    # A/B are intentionally same-logic controls, so they should expose
    # the same targeted upstream/schema gaps rather than complement each other.
    assert summary["ab_gap_analysis"]["same_logic_gap_behavior"] is True
    assert summary["ab_gap_analysis"]["all_targeted_shared_gaps_exposed"] is True
    assert summary["ab_gap_analysis"]["a_b_are_complementary"] is False

    assert summary["c_specific"]["total"] == 17
    assert summary["c_specific"]["passed"] == 17
    assert summary["c_specific"]["failed"] == 0

    assert all(summary["precedence_checks"].values())
    assert all(summary["safety_checks"].values())

    assert summary["complementarity"]["a_b_complementary"] is False
    assert (
        summary["complementarity"]["c_agent_gate_complementarity_established"]
        is True
    )
    assert summary["decision"] == "ALLOW"
