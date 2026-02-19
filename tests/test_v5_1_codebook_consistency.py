# -*- coding: utf-8 -*-
"""
Pytest contract tests for v5.1.2 simulator + v5.1-demo.1 codebook.

Goals:
  - Enforce mapping consistency (reason_code, layer, decision, final_decider).
  - Ensure simulator never emits a reason_code not present in the codebook.
  - Validate core invariants are preserved (sealed only by ethics/acc; RFL never sealed).
  - Validate a packed header can be decoded back to symbols using codebook reverse_maps.

Run:
  pytest -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

import pytest


# Repo root: (repo)/tests/this_file.py -> parents[1] == repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent

SIM_FILENAME = "mediation_emergency_contract_sim_v5_1_2.py"
CODEBOOK_FILENAME = "log_codebook_v5_1_demo_1.json"


def _rank_path(p: Path) -> Tuple[int, int, int]:
    """
    Lower is better.
      1) Prefer tests/fixtures
      2) Prefer tests/
      3) Prefer shorter paths
    """
    pstr = str(p.as_posix())
    in_fixtures = 0 if f"{TESTS_DIR.as_posix()}/fixtures/" in pstr else 1
    in_tests = 0 if f"{TESTS_DIR.as_posix()}/" in pstr else 1
    depth = len(p.resolve().parts)
    return (in_fixtures, in_tests, depth)


def _resolve_file(
    *,
    exact_name: str,
    candidate_relpaths: Iterable[Path],
    glob_patterns: Iterable[str] = (),
    required: bool = True,
) -> Path:
    """
    Resolve a file in a hermetic way:
      1) Try explicit candidate paths (relative to repo root)
      2) Try exact rglob by filename
      3) Try rglob by patterns
    """
    tried: List[Path] = []

    for rel in candidate_relpaths:
        p = (REPO_ROOT / rel).resolve()
        tried.append(p)
        if p.exists():
            return p

    hits = list(REPO_ROOT.rglob(exact_name))
    if hits:
        return sorted(hits, key=_rank_path)[0].resolve()

    for pat in glob_patterns:
        pat_hits = list(REPO_ROOT.rglob(pat))
        if pat_hits:
            return sorted(pat_hits, key=_rank_path)[0].resolve()

    if required:
        tried_str = "\n".join(f"  - {p}" for p in tried)
        raise FileNotFoundError(
            f"Missing fixture: {exact_name}\nTried:\n{tried_str}\n"
            f"Also searched recursively under repo root for:\n"
            f"  - {exact_name}\n"
            + "".join(f"  - {pat}\n" for pat in glob_patterns)
        )
    return (REPO_ROOT / exact_name).resolve()


def _import_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {mod_name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


@pytest.fixture(scope="session")
def sim_path() -> Path:
    return _resolve_file(
        exact_name=SIM_FILENAME,
        candidate_relpaths=[
            Path(SIM_FILENAME),
            Path("src") / SIM_FILENAME,
            Path("scripts") / SIM_FILENAME,
        ],
        glob_patterns=[
            "mediation_emergency_contract_sim_v5_1_2.py",
            "mediation_emergency_contract_sim_v5_1_2*.py",
        ],
        required=True,
    )


@pytest.fixture(scope="session")
def codebook_path() -> Path:
    return _resolve_file(
        exact_name=CODEBOOK_FILENAME,
        candidate_relpaths=[
            Path(CODEBOOK_FILENAME),
            Path("tests") / CODEBOOK_FILENAME,
            Path("tests") / "fixtures" / CODEBOOK_FILENAME,
            Path("fixtures") / CODEBOOK_FILENAME,
        ],
        glob_patterns=[
            "log_codebook_v5_1_demo_1.json",
            "log_codebook_v5_1*.json",
            "*codebook*demo_1*.json",
        ],
        required=True,
    )


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
        for k, v in forward.items():
            assert str(v) in reverse, f"reverse missing id {v} for key {k}"
            assert reverse[str(v)] == k, f"reverse mismatch for id {v}: {reverse[str(v)]} != {k}"

    assert_inverse(maps["layer_to_id"], rev["id_to_layer"])
    assert_inverse(maps["decision_to_id"], rev["id_to_decision"])
    assert_inverse(maps["final_decider_to_id"], rev["id_to_final_decider"])
    assert_inverse(maps["reason_code_to_id"], rev["id_to_reason_code"])


def test_simulator_constants_are_all_in_codebook(sim, codebook):
    """Every RC_* constant value in the simulator must exist in the codebook."""
    rc_values: List[str] = []
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


def _decode_header_local(cb: Dict[str, Any], packed: int) -> Dict[str, Any]:
    """
    Decode 20-bit header (big-endian pack) using codebook reverse_maps.
    Layout (MSB->LSB):
      layer_id:6 | decision_id:2 | sealed:1 | overrideable:1 | decider_id:2 | rc_id:8
    """
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

    layer = rev["id_to_layer"][str(layer_id)]
    decision = rev["id_to_decision"][str(decision_id)]
    final_decider = rev["id_to_final_decider"][str(decider_id)]
    reason_code = rev["id_to_reason_code"][str(rc_id)]

    return {
        "layer": layer,
        "decision": decision,
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
        "reason_code": reason_code,
    }


def test_local_decoder_roundtrip_for_known_header(codebook):
    """Pack -> local decode should reproduce the same symbolic fields."""
    packed = _pack_header(
        codebook,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="REL_BOUNDARY_UNSTABLE",
    )
    decoded = _decode_header_local(codebook, packed)

    assert decoded["layer"] == "relativity_gate"
    assert decoded["decision"] == "PAUSE_FOR_HITL"
    assert decoded["sealed"] is False
    assert decoded["overrideable"] is True
    assert decoded["final_decider"] == "SYSTEM"
    assert decoded["reason_code"] == "REL_BOUNDARY_UNSTABLE"


def test_simulate_run_emits_only_codebook_reason_codes_and_keeps_invariants(sim, codebook, tmp_path, monkeypatch):
    """
    Execute simulator paths that produce ARL rows and validate:
      - every reason_code in exported rows exists in codebook
      - sealed only by ethics/acc (enforced by AuditLog.emit; any violation raises)
      - RFL never sealed (enforced by AuditLog.emit; any violation raises)
    """
    monkeypatch.setattr(sim, "TRUST_STORE_PATH", tmp_path / "model_trust_store.json", raising=True)
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", tmp_path / "model_grants.json", raising=True)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", tmp_path / "eval_state.json", raising=True)

    sim.ensure_default_grant_exists()
    rc_set = _rc_set_from_codebook(codebook)

    trust = sim.TrustState(trust_score=0.50, approval_streak=0, cooldown_until=None, compliance_score=0.0, coaching_sessions=0)
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
    assert rows, "Expected some ARL rows due to PAUSE/contract events"

    for r in rows:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"

    trust2 = sim.TrustState(trust_score=0.90, approval_streak=0, cooldown_until=None, compliance_score=0.0, coaching_sessions=0)
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
    assert rows2, "Expected ARL rows due to SEALED/STOPPED"
    assert any(r["sealed"] is True for r in rows2), "Expected at least one SEALED row"
    for r in rows2:
        assert r["reason_code"] in rc_set, f"Unknown reason_code in ARL: {r['reason_code']}"
