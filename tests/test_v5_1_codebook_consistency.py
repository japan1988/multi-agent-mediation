# tests/test_v5_1_codebook_consistency.py
# -*- coding: utf-8 -*-
"""
Codebook consistency tests for mediation_emergency_contract_sim_v5_1_2.py

Goals:
  - Enforce mapping consistency (reason_code, layer, decision, final_decider).
  - Ensure simulator never emits a reason_code not present in the codebook.
  - Validate core invariants are preserved
    (sealed only by ethics/acc; RFL never sealed).

Run:
  pytest -q
"""

from __future__ import annotations

import importlib.util
import inspect
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


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def sim_path(repo_root: Path) -> Path:
    return repo_root / "mediation_emergency_contract_sim_v5_1_2.py"


@pytest.fixture(scope="session")
def codebook_path(repo_root: Path) -> Path:
    return repo_root / "log_codebook_v5_1_demo_1.json"


@pytest.fixture(scope="session")
def sim(sim_path: Path):
    if not sim_path.exists():
        raise FileNotFoundError(f"Missing simulator: {sim_path}")
    return _import_from_path("sim_v5_1_2", sim_path)


@pytest.fixture(scope="session")
def codebook(codebook_path: Path) -> Dict[str, Any]:
    if not codebook_path.exists():
        raise FileNotFoundError(f"Missing codebook: {codebook_path}")
    return json.loads(codebook_path.read_text(encoding="utf-8"))


def _rc_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["reason_code_to_id"].keys())


def _layer_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["layer_to_id"].keys())


def _decision_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["decision_to_id"].keys())


def _decider_set_from_codebook(cb: Dict[str, Any]) -> Set[str]:
    return set(cb["maps"]["final_decider_to_id"].keys())


def test_codebook_reverse_maps_are_inverses(codebook):
    """Sanity: forward maps and reverse maps must be mutual inverses."""
    maps = codebook["maps"]
    rev = codebook["reverse_maps"]

    def assert_inverse(forward: Dict[str, int], reverse: Dict[str, str]):
        for key, value in forward.items():
            assert str(value) in reverse, f"reverse missing id {value} for key {key}"
            assert reverse[str(value)] == key, f"reverse mismatch for id {value}: {reverse[str(value)]} != {key}"

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
    missing = sorted({value for value in rc_values if value not in rc_set})
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
    assert not (used_decisions - decision_set), f"Decisions missing in codebook: {sorted(used_decisions - decision_set)}"
    assert not (used_deciders - decider_set), f"Deciders missing in codebook: {sorted(used_deciders - decider_set)}"


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


def _unpack_header_local(cb: Dict[str, Any], packed: int) -> Dict[str, Any]:
    """Local unpack helper so this test does not depend on simulator-side decoder names."""
    rev = cb["reverse_maps"]

    rc_id = packed & 0xFF
    packed >>= 8
    decider_id = packed & 0x3
    packed >>= 2
    overrideable = bool(packed & 0x1)
    packed >>= 1
    sealed = bool(packed & 0x1)
    packed >>= 1
    decision_id = packed & 0x3
    packed >>= 2
    layer_id = packed & 0x3F

    return {
        "layer": rev["id_to_layer"][str(layer_id)],
        "decision": rev["id_to_decision"][str(decision_id)],
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": rev["id_to_final_decider"][str(decider_id)],
        "reason_code": rev["id_to_reason_code"][str(rc_id)],
    }


def test_pack_example_round_trip(codebook):
    packed = _pack_header(
        codebook,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="REL_BOUNDARY_UNSTABLE",
    )

    decoded = _unpack_header_local(codebook, packed)

    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def _make_trust_object(sim, *, seed_value: int = 0):
    """
    Best-effort trust object constructor.
    Tries simulator-specific classes first, then dict fallback.
    """
    for cls_name in ("TrustState", "Trust", "TrustRecord"):
        cls = getattr(sim, cls_name, None)
        if cls is None:
            continue

        try:
            return cls()
        except TypeError:
            pass

        try:
            sig = inspect.signature(cls)
            kwargs: Dict[str, Any] = {}
            for name, param in sig.parameters.items():
                if name == "score":
                    kwargs[name] = seed_value
                elif name == "streak":
                    kwargs[name] = 0
                elif name == "cooldown":
                    kwargs[name] = 0
                elif param.default is not inspect._empty:
                    kwargs[name] = param.default
                else:
                    kwargs[name] = 0
            return cls(**kwargs)
        except Exception:
            continue

    return {"score": seed_value, "streak": 0, "cooldown": 0}


def _rows_from_audit(audit: Any):
    if hasattr(audit, "export_rows"):
        return audit.export_rows()
    if isinstance(audit, list):
        return audit
    raise TypeError(f"Unsupported audit object: {type(audit)!r}")


def test_simulate_run_emits_only_codebook_reason_codes_and_keeps_invariants(sim, codebook, tmp_path, monkeypatch):
    """
    Smoke-run two simulations and ensure:
    - every emitted reason_code exists in the codebook
    - sealed rows are only emitted by ethics/acc layers
    - relativity_gate rows are never sealed
    """
    monkeypatch.setattr(sim, "TRUST_STORE_PATH", tmp_path / "model_trust_store.json", raising=True)
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", tmp_path / "model_grants.json", raising=True)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", tmp_path / "eval_state.json", raising=True)

    rc_set = _rc_set_from_codebook(codebook)

    trust = _make_trust_object(sim, seed_value=0)
    trust2 = _make_trust_object(sim, seed_value=1)

    _st, audit, _trust_out = sim.simulate_run(
        run_id="RUN#T1",
        dummy_auth_id="EMG-ABCDEF123456",
        trust=trust,
        fabricate_evidence=False,
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        key_id="demo",
        full_context_n=10,
        persist=False,
    )
    rows = _rows_from_audit(audit)

    _st2, audit2, _trust2_out = sim.simulate_run(
        run_id="RUN#T2",
        dummy_auth_id="EMG-ABCDEF123456",
        trust=trust2,
        fabricate_evidence=True,
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        key_id="demo",
        full_context_n=10,
        persist=False,
    )
    rows2 = _rows_from_audit(audit2)

    for row in rows:
        assert row["reason_code"] in rc_set, f"Unknown reason_code in ARL: {row['reason_code']}"
        if row["sealed"] is True:
            assert row["layer"] in {"ethics_gate", "acc_gate"}, f"sealed row emitted by {row['layer']}"
        if row["layer"] == "relativity_gate":
            assert row["sealed"] is False, "RFL row must never be sealed"

    assert any(row["sealed"] is True for row in rows2), "Expected at least one SEALED row"
    for row in rows2:
        assert row["reason_code"] in rc_set, f"Unknown reason_code in ARL: {row['reason_code']}"
        if row["sealed"] is True:
            assert row["layer"] in {"ethics_gate", "acc_gate"}, f"sealed row emitted by {row['layer']}"
        if row["layer"] == "relativity_gate":
            assert row["sealed"] is False, "RFL row must never be sealed"
