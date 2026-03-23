# -*- coding: utf-8 -*-
"""
Goals:
- Enforce mapping consistency (reason_code, layer, decision, final_decider).
- Ensure simulator never emits a reason_code not present in the codebook.
- Validate core invariants are preserved (sealed only by ethics/acc; RFL never sealed).

Run:
    pytest -q
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, Set

import pytest


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
def sim(repo_root: Path):
    sim_path = repo_root / "mediation_emergency_contract_sim_v5_1_2.py"
    assert sim_path.exists(), f"Simulator file not found: {sim_path}"
    return _import_from_path("mediation_emergency_contract_sim_v5_1_2_under_test", sim_path)


@pytest.fixture(scope="session")
def codebook(repo_root: Path) -> Dict[str, Any]:
    codebook_path = _find_codebook_path(repo_root)
    with codebook_path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    """Pack 20-bit header per codebook pack_spec_example (big-endian)."""
    m = cb["maps"]
    layer_id = int(m["layer_to_id"][layer])
    decision_id = int(m["decision_to_id"][decision])
    decider_id = int(m["final_decider_to_id"][final_decider])
    rc_id = int(m["reason_code_to_id"][reason_code])

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


def _assert_rows_keep_core_invariants(rows):
    for r in rows:
        assert "reason_code" in r
        assert "layer" in r
        assert "decision" in r
        assert "final_decider" in r
        assert "sealed" in r
        assert "overrideable" in r

        if r["sealed"] is True:
            assert r["layer"] in {"ethics_gate", "acc_gate"}, (
                f"sealed row emitted outside ethics/acc: {r['layer']}"
            )
            assert r["overrideable"] is False, "sealed row must not be overrideable"

        if r["layer"] == "relativity_gate":
            assert r["sealed"] is False, "RFL must never be sealed"
            assert r["decision"] == "PAUSE_FOR_HITL", "RFL must pause for HITL"
            assert r["overrideable"] is True, "RFL pause must be overrideable"


def test_codebook_reverse_maps_are_inverses(codebook):
    """Sanity: forward maps and reverse maps must be mutual inverses."""
    maps = codebook["maps"]
    rev = codebook["reverse_maps"]

    def assert_inverse(forward: Dict[str, int], reverse: Dict[str, str]):
        for k, v in forward.items():
            assert str(v) in reverse, f"reverse missing id {v} for key {k}"
            assert reverse[str(v)] == k, f"reverse mismatch for id {v}: {reverse[str(v)]} != {k}"

    assert_inverse(maps["layer_to_id"], rev["id_to_layer"])
    assert_inverse(maps["decision_to_id"], rev["id_to_decision"])
    assert_inverse(maps["final_decider_to_id"], rev["id_to_final_decider"])
    assert_inverse(maps["reason_code_to_id"], rev["id_to_reason_code"])


def test_simulator_constants_are_all_in_codebook(sim, codebook):
    """Every RC_* constant value in the simulator must exist in the codebook."""
    rc_values = []
    for name, value in vars(sim).items():
        if name.startswith("RC_") and isinstance(value, str):
            rc_values.append(value)

    rc_set = _rc_set_from_codebook(codebook)
    missing = sorted({v for v in rc_values if v not in rc_set})
    assert not missing, f"Simulator RC_* not in codebook: {missing}"


def test_simulator_layer_decision_decider_vocab_matches_codebook(sim, codebook):
    """Layer/decision/decider strings used by simulator must exist in codebook."""
    layer_set = _layer_set_from_codebook(codebook)
    decision_set = _decision_set_from_codebook(codebook)
    decider_set = _decider_set_from_codebook(codebook)

    used_layers = {v for k, v in vars(sim).items() if k.startswith("LAYER_") and isinstance(v, str)}
    used_decisions = {v for k, v in vars(sim).items() if k.startswith("DECISION_") and isinstance(v, str)}
    used_deciders = {v for k, v in vars(sim).items() if k.startswith("DECIDER_") and isinstance(v, str)}

    assert not (used_layers - layer_set), f"Layers missing in codebook: {sorted(used_layers - layer_set)}"
    assert not (used_decisions - decision_set), (
        f"Decisions missing in codebook: {sorted(used_decisions - decision_set)}"
    )
    assert not (used_deciders - decider_set), (
        f"Deciders missing in codebook: {sorted(used_deciders - decider_set)}"
    )


def test_pack_spec_example_round_trip(codebook):
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

    assert packed <= 0xFFFFF
    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def test_simulate_run_emits_only_codebook_reason_codes_and_keeps_invariants(
    sim, codebook, tmp_path, monkeypatch
):
    """ARL emitted by simulate_run must stay within the codebook and core invariants."""
    # Patch persistent paths used by the simulator so the test stays hermetic.
    monkeypatch.setattr(sim, "TRUST_STORE_PATH", tmp_path / "model_trust_store.json", raising=True)
    if hasattr(sim, "GRANTS_STORE_PATH"):
        monkeypatch.setattr(sim, "GRANTS_STORE_PATH", tmp_path / "model_grants.json", raising=True)
    if hasattr(sim, "GRANT_STORE_PATH"):
        monkeypatch.setattr(sim, "GRANT_STORE_PATH", tmp_path / "model_grants.json", raising=True)
    if hasattr(sim, "EVAL_STATE_PATH"):
        monkeypatch.setattr(sim, "EVAL_STATE_PATH", tmp_path / "eval_state.json", raising=True)
    if hasattr(sim, "EVAL_STORE_PATH"):
        monkeypatch.setattr(sim, "EVAL_STORE_PATH", tmp_path / "eval_state.json", raising=True)

    rc_set = _rc_set_from_codebook(codebook)

    trust = sim.TrustState()
    st, audit, trust_out = sim.simulate_run(
        run_id="RUN#T1",
        dummy_auth_id="EMG-ABCDEF123456",
        trust=trust,
        fabricate_evidence=False,
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        key_id="demo",
        full_context_n=10,
        persist=False,
    )
    rows = audit.export_rows()

    assert st is not None
    assert trust_out is trust
    assert rows, "Expected non-empty ARL rows for baseline run"
    for r in rows:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"
    _assert_rows_keep_core_invariants(rows)

    trust2 = sim.TrustState()
    st2, audit2, trust2_out = sim.simulate_run(
        run_id="RUN#T2",
        dummy_auth_id="EMG-ABCDEF123456",
        trust=trust2,
        fabricate_evidence=True,
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        key_id="demo",
        full_context_n=10,
        persist=False,
    )
    rows2 = audit2.export_rows()

    assert st2 is not None
    assert trust2_out is trust2
    assert rows2, "Expected non-empty ARL rows for fabricated-evidence run"
    assert any(r["sealed"] is True for r in rows2), "Expected at least one SEALED row"
    for r in rows2:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"
    _assert_rows_keep_core_invariants(rows2)

