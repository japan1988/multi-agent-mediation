


Run:
    pytest -q
"""


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


            else:
                raise AssertionError(
                    f"Unexpected decision on RFL row: {r['decision']}"
                )


def test_codebook_reverse_maps_are_inverses(codebook):
    """Sanity: forward maps and reverse maps must be mutual inverses."""
    maps = codebook["maps"]
    rev = codebook["reverse_maps"]

    def assert_inverse(forward: Dict[str, int], reverse: Dict[str, str]):


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



    rc_set = _rc_set_from_codebook(codebook)

    trust = _make_trust_object(sim, seed_value=0)
    trust2 = _make_trust_object(sim, seed_value=1)


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


        run_id="RUN#T2",
        dummy_auth_id="EMG-ABCDEF123456",
        trust=trust2,
        fabricate_evidence=True,
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        key_id="demo",
        full_context_n=10,
        persist=False,
    )

