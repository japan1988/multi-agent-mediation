# -*- coding: utf-8 -*-
"""
Pytest contract tests for v5.1.2 simulator + v5.1-demo.1 codebook + decoder helper.

Goals:
  - Enforce mapping consistency (reason_code, layer, decision, final_decider).
  - Ensure simulator never emits a reason_code not present in the codebook.
  - Validate core invariants are preserved (sealed only by ethics/acc; RFL never sealed).
  - Validate decoder correctly unpacks a packed header in accordance with the codebook pack spec example.

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


# Repo root (…/repo/tests/<this file> -> parents[1] == repo root)
ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

SIM_PATH = ROOT / "mediation_emergency_contract_sim_v5_1_2.py"


def _find_fixture(filename: str) -> Path:
    """
    Resolve fixture path robustly across local/CI.

    Preference order:
      1) tests/<filename>               (co-located with tests)
      2) repo-root/<filename>           (fallback for older layout)
      3) repo-root/tests/<filename>     (belt-and-suspenders)
    """
    candidates = [
        HERE / filename,
        ROOT / filename,
        ROOT / "tests" / filename,
    ]
    for p in candidates:
        if p.exists():
            return p

    tried = "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Missing fixture: {filename}\nTried:\n{tried}")


CODEBOOK_PATH = _find_fixture("log_codebook_v5_1_demo_1.json")
DECODER_PATH = _find_fixture("codebook_decode_demo_1.py")


def _import_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {mod_name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


@pytest.fixture(scope="session")
def sim():
    if not SIM_PATH.exists():
        raise FileNotFoundError(f"Missing simulator: {SIM_PATH}")
    return _import_from_path("sim_v5_1_2", SIM_PATH)


@pytest.fixture(scope="session")
def decoder():
    if not DECODER_PATH.exists():
        raise FileNotFoundError(f"Missing decoder helper: {DECODER_PATH}")
    return _import_from_path("decoder_v5_1", DECODER_PATH)


@pytest.fixture(scope="session")
def codebook() -> Dict[str, Any]:
    if not CODEBOOK_PATH.exists():
        raise FileNotFoundError(f"Missing codebook: {CODEBOOK_PATH}")
    return json.loads(CODEBOOK_PATH.read_text(encoding="utf-8"))


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


def test_decoder_roundtrip_for_known_header(decoder, codebook):
    """Pack -> decode should reproduce the same symbolic fields."""
    # Decoder demo helper is expected to provide Codebook.load(Path|str) and decode_header(codebook, int) APIs.
    cb = decoder.Codebook.load(str(CODEBOOK_PATH))

    packed = _pack_header(
        codebook,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="REL_BOUNDARY_UNSTABLE",
    )
    decoded = decoder.decode_header(cb, packed)

    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def test_simulate_run_emits_only_codebook_reason_codes_and_keeps_invariants(sim, codebook, tmp_path, monkeypatch):
    """
    Execute simulator paths that produce FULL ARL rows and validate:
      - every reason_code in persisted rows exists in codebook
      - sealed only by ethics/acc (enforced by AuditLog.emit; any violation raises)
      - RFL never sealed (enforced by AuditLog.emit; any violation raises)
    """
    # Redirect persistent stores into temp dir to keep test hermetic
    monkeypatch.setattr(sim, "TRUST_STORE_PATH", tmp_path / "model_trust_store.json", raising=True)
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", tmp_path / "model_grants.json", raising=True)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", tmp_path / "eval_state.json", raising=True)

    # Ensure grants exist in temp dir
    sim.ensure_default_grant_exists()

    rc_set = _rc_set_from_codebook(codebook)

    # Case 1: low trust => HITL auth pause + subsequent approval + finalize pause => produces persisted rows
    trust = sim.TrustState(
        trust_score=0.50,
        approval_streak=0,
        cooldown_until=None,
        compliance_score=0.0,
        coaching_sessions=0,
    )
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
    assert rows, "Expected some persisted ARL rows due to PAUSE events"

    for r in rows:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"
        # Invariant checks are enforced inside AuditLog.emit via AssertionError.

    # Case 2: fabricated evidence => ethics sealed => produces persisted rows and must be RC_EVIDENCE_FABRICATION
    trust2 = sim.TrustState(
        trust_score=0.90,
        approval_streak=0,
        cooldown_until=None,
        compliance_score=0.0,
        coaching_sessions=0,
    )
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
    assert rows2, "Expected persisted ARL rows due to SEALED/STOPPED"
    assert any(r["sealed"] is True for r in rows2), "Expected at least one SEALED row"
    for r in rows2:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"
