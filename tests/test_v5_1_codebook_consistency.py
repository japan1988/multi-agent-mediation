# -*- coding: utf-8 -*-
"""
tests/test_v5_1_codebook_consistency.py

Consistency checks between the v5.1 codebook and the simulator vocabulary.

Run:
    pytest -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, Set

import pytest


SIM_MODULE_NAME = "mediation_emergency_contract_sim_v5_1_2"
SIM_FILE_NAME = f"{SIM_MODULE_NAME}.py"


def _import_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {mod_name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _find_codebook_path(repo_root: Path) -> Path:
    candidates = [
        repo_root / "v5_1_codebook.json",
        repo_root / "codebook_v5_1.json",
        repo_root / "codebook-v5_1.json",
        repo_root / "docs" / "v5_1_codebook.json",
        repo_root / "docs" / "codebook_v5_1.json",
        repo_root / "artifacts" / "v5_1_codebook.json",
        repo_root / "artifacts" / "codebook_v5_1.json",
    ]
    for path in candidates:
        if path.exists():
            return path

    globs = [
        "**/*v5*codebook*.json",
        "**/*codebook*v5*.json",
        "**/*codebook*.json",
    ]
    for pattern in globs:
        matches = sorted(p for p in repo_root.glob(pattern) if p.is_file())
        if matches:
            return matches[0]

    raise FileNotFoundError(f"No codebook JSON found under {repo_root}")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def codebook(repo_root: Path) -> Dict[str, Any]:
    path = _find_codebook_path(repo_root)
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sim(repo_root: Path):
    sim_path = repo_root / SIM_FILE_NAME
    if not sim_path.exists():
        pytest.skip(f"{SIM_FILE_NAME} not found under repo root")
    return _import_from_path(SIM_MODULE_NAME, sim_path)


def _rc_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["reason_code_to_id"].keys())


def _layer_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["layer_to_id"].keys())


def _decision_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["decision_to_id"].keys())


def _decider_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["final_decider_to_id"].keys())


def _pack_header(
    cb: Dict[str, Any],
    *,
    layer: str,
    decision: str,
    sealed: bool,
    overrideable: bool,
    final_decider: str,
    reason_code: str,
) -> int:
    """Pack a 20-bit header using the codebook maps."""
    maps = cb["maps"]
    layer_id = int(maps["layer_to_id"][layer])
    decision_id = int(maps["decision_to_id"][decision])
    decider_id = int(maps["final_decider_to_id"][final_decider])
    rc_id = int(maps["reason_code_to_id"][reason_code])

    packed = 0
    packed = (packed << 6) | (layer_id & 0x3F)
    packed = (packed << 2) | (decision_id & 0x3)
    packed = (packed << 1) | (1 if sealed else 0)
    packed = (packed << 1) | (1 if overrideable else 0)
    packed = (packed << 2) | (decider_id & 0x3)
    packed = (packed << 8) | (rc_id & 0xFF)
    return packed


def _unpack_header(cb: Dict[str, Any], packed: int) -> Dict[str, Any]:
    rev = cb["reverse_maps"]

    rc_id = packed & 0xFF
    decider_id = (packed >> 8) & 0x3
    overrideable = bool((packed >> 10) & 0x1)
    sealed = bool((packed >> 11) & 0x1)
    decision_id = (packed >> 12) & 0x3
    layer_id = (packed >> 14) & 0x3F

    return {
        "layer": rev["id_to_layer"][str(layer_id)],
        "decision": rev["id_to_decision"][str(decision_id)],
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": rev["id_to_final_decider"][str(decider_id)],
        "reason_code": rev["id_to_reason_code"][str(rc_id)],
    }


def _assert_rows_keep_core_invariants(rows) -> None:
    for row in rows:
        assert "reason_code" in row
        assert "layer" in row
        assert "decision" in row
        assert "final_decider" in row
        assert "sealed" in row
        assert "overrideable" in row

        if row["sealed"] is True:
            assert row["layer"] in {"ethics_gate", "acc_gate"}, (
                f"sealed row emitted outside ethics/acc: {row['layer']}"
            )
            assert row["overrideable"] is False, (
                "sealed row must not be overrideable"
            )

        if row["layer"] == "relativity_gate":
            assert row["sealed"] is False, "RFL must never be sealed"
            assert row["decision"] == "PAUSE_FOR_HITL", (
                f"Unexpected decision on RFL row: {row['decision']}"
            )


def test_codebook_reverse_maps_are_inverses(codebook: Dict[str, Any]) -> None:
    """Sanity: forward maps and reverse maps must be mutual inverses."""
    maps = codebook["maps"]
    rev = codebook["reverse_maps"]

    def assert_inverse(forward: Dict[str, int], reverse: Dict[str, str]) -> None:
        for k, v in forward.items():
            assert str(v) in reverse, f"Missing reverse entry for value {v}"
            assert reverse[str(v)] == k, (
                f"Reverse map mismatch: {k} -> {v}, reverse gives {reverse[str(v)]}"
            )

    assert_inverse(maps["layer_to_id"], rev["id_to_layer"])
    assert_inverse(maps["decision_to_id"], rev["id_to_decision"])
    assert_inverse(maps["final_decider_to_id"], rev["id_to_final_decider"])
    assert_inverse(maps["reason_code_to_id"], rev["id_to_reason_code"])


def test_simulator_constants_are_all_in_codebook(
    sim,
    codebook: Dict[str, Any],
) -> None:
    """Every RC_* constant value in the simulator must exist in the codebook."""
    rc_values = []
    for name, value in vars(sim).items():
        if name.startswith("RC_") and isinstance(value, str):
            rc_values.append(value)

    rc_set = _rc_set_from_codebook(codebook)
    missing = sorted({value for value in rc_values if value not in rc_set})
    assert not missing, f"Simulator RC_* not in codebook: {missing}"


def test_simulator_layer_decision_decider_vocab_matches_codebook(
    sim,
    codebook: Dict[str, Any],
) -> None:
    """Layer/decision/decider strings used by simulator must exist in codebook."""
    layer_set = _layer_set_from_codebook(codebook)
    decision_set = _decision_set_from_codebook(codebook)
    decider_set = _decider_set_from_codebook(codebook)

    assert "relativity_gate" in layer_set
    assert "ethics_gate" in layer_set
    assert "acc_gate" in layer_set

    assert "RUN" in decision_set
    assert "PAUSE_FOR_HITL" in decision_set
    assert "STOPPED" in decision_set

    assert "SYSTEM" in decider_set
    assert "USER" in decider_set

    packed = _pack_header(
        codebook,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="REL_BOUNDARY_UNSTABLE",
    )
    decoded = _unpack_header(codebook, packed)

    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def test_required_reason_codes_exist(codebook: Dict[str, Any]) -> None:
    rc_set = _rc_set_from_codebook(codebook)
    required = {
        "REL_BOUNDARY_UNSTABLE",
        "REL_REF_MISSING",
        "REL_SYMMETRY_BREAK",
    }
    missing = sorted(required - rc_set)
    assert not missing, f"Required reason codes missing from codebook: {missing}"


def test_sample_rows_keep_core_invariants() -> None:
    rows = [
        {
            "layer": "relativity_gate",
            "decision": "PAUSE_FOR_HITL",
            "sealed": False,
            "overrideable": True,
            "final_decider": "SYSTEM",
            "reason_code": "REL_BOUNDARY_UNSTABLE",
        },
        {
            "layer": "ethics_gate",
            "decision": "STOPPED",
            "sealed": True,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "reason_code": "SEALED_BY_ETHICS",
        },
    ]
    _assert_rows_keep_core_invariants(rows)
