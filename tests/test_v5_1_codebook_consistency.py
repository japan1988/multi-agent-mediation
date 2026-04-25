
# -*- coding: utf-8 -*-
"""
tests/test_v5_1_codebook_consistency.py

Consistency checks between the v5.1 codebook and the simulator vocabulary.

Run:
    pytest -q
"""


# tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import json
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



import mediation_emergency_contract_sim_v5_1_2 as sim


def _patch_store_paths(monkeypatch, tmp_path: Path) -> None:
    """
    テストごとに永続化先を隔離する。
    リポジトリ直下の実ファイルを汚さない。
    """
    trust_path = tmp_path / "model_trust_store.json"
    grants_path = tmp_path / "model_grants.json"
    eval_path = tmp_path / "eval_state.json"

    monkeypatch.setattr(sim, "TRUST_STORE_PATH", trust_path, raising=False)
    monkeypatch.setattr(sim, "GRANTS_STORE_PATH", grants_path, raising=False)
    monkeypatch.setattr(sim, "EVAL_STATE_PATH", eval_path, raising=False)

    # 後方互換 alias も揃える
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", grants_path, raising=False)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", eval_path, raising=False)


def _queue_counts(results: dict) -> dict:
    return (((results or {}).get("hitl_queue") or {}).get("counts") or {})


def _abnormal(results: dict) -> dict:
    return (results or {}).get("abnormal_arl_persistence", {}) or {}


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _assert_sealed_only_ethics_or_acc(results: dict) -> None:
    runs = results.get("runs", []) or []
    for run in runs:
        for row in (run.get("arl", []) or []):
            layer = row.get("layer")
            sealed = bool(row.get("sealed", False))
            if sealed:
                assert layer in (sim.LAYER_ETHICS, sim.LAYER_ACC)
            if layer == sim.LAYER_RFL:
                assert sealed is False


def test_v512_operational_resilience_clean_runs_large(
    monkeypatch, tmp_path: Path
) -> None:
    """
    clean run 大量反復での運用耐性確認。
    keep_runs=False でメモリ肥大を避けつつ、
    queue / trust / eval / abnormal persistence の整合を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    r = sim.run_simulation(
        runs=1000,
        fabricate=False,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    counts = _queue_counts(r)
    abnormal = _abnormal(r)

    assert counts.get("total_runs") == 1000
    assert counts.get("by_state", {}).get("CONTRACT_EFFECTIVE", 0) == 1000
    assert counts.get("queue_size", 0) == 0

    assert abnormal.get("abnormal_total", 0) == 0
    assert abnormal.get("saved", 0) == 0
    assert abnormal.get("skipped_by_cap", 0) == 0

    eval_after = r.get("eval_after", {})
    assert eval_after.get("clean_completion_count") == 1000
    assert eval_after.get("multiplier") == sim.EVAL_MULTIPLIER_CAP

    trust_after = r.get("trust_after", {})
    assert sim.TRUST_MIN <= trust_after.get("trust_score", -1) <= sim.TRUST_MAX


def test_v512_mixed_mode_deterministic_under_reset(
    monkeypatch, tmp_path: Path
) -> None:
    """
    fabricate-rate 混在時でも、
    reset + seed 固定なら queue / trust / eval が再現することを確認。
    cooldown_until は壁時計依存なので完全一致比較から除外する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    params = dict(
        runs=500,
        fabricate=False,
        fabricate_rate=0.10,
        seed=42,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    r1 = sim.run_simulation(**params)
    r2 = sim.run_simulation(**params)

    c1 = _queue_counts(r1)
    c2 = _queue_counts(r2)
    assert c1 == c2

    a1 = _abnormal(r1)
    a2 = _abnormal(r2)
    assert a1 == a2

    t1 = dict(r1.get("trust_after", {}))
    t2 = dict(r2.get("trust_after", {}))
    cd1 = t1.pop("cooldown_until", None)
    cd2 = t2.pop("cooldown_until", None)



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
=======
    # 壁時計依存の cooldown_until を除けば一致すること
    assert t1 == t2

    # cooldown が必要なケースなら、両方とも値を持つことだけ確認

    assert t1 == t2



    if cd1 is not None or cd2 is not None:
        assert cd1 is not None
        assert cd2 is not None


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

    assert r1.get("eval_after") == r2.get("eval_after")
    assert a1.get("abnormal_total", 0) > 0


def test_v512_abnormal_arl_persistence_and_incident_index(
    monkeypatch, tmp_path: Path
) -> None:
    """
    異常時のみ ARL 保存 + incident index / counter の整合確認。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    out_dir = tmp_path / "arl_out"
    r = sim.run_simulation(
        runs=200,
        fabricate=False,
        fabricate_rate=0.20,
        seed=7,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out_dir),
        max_arl_files=30,
        full_context_n=5,

    )


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

    abnormal = _abnormal(r)
    saved = int(abnormal.get("saved", 0))
    abnormal_total = int(abnormal.get("abnormal_total", 0))
    skipped = int(abnormal.get("skipped_by_cap", 0))

    assert abnormal_total > 0
    assert saved == min(abnormal_total, 30)
    assert skipped == max(0, abnormal_total - 30)

    arl_files = sorted(out_dir.glob("INC#*.arl.jsonl"))
    assert len(arl_files) == saved

    index_path = out_dir / "incident_index.jsonl"
    counter_path = out_dir / "incident_counter.txt"

    assert index_path.exists()
    assert counter_path.exists()

    index_rows = _read_jsonl(index_path)
    assert len(index_rows) == saved

    # incident_counter は次回発行番号なので saved + 1
    counter_value = int(counter_path.read_text(encoding="utf-8").strip())
    assert counter_value == saved + 1

    incident_ids = set()
    for row in index_rows:
        incident_id = row.get("incident_id")
        arl_path = Path(row.get("arl_path", ""))

        assert incident_id
        assert incident_id not in incident_ids
        assert arl_path.exists()

        incident_ids.add(incident_id)


def test_v512_sealed_invariants_under_mixed_load(
    monkeypatch, tmp_path: Path
) -> None:
    """
    keep_runs=True の中規模 runs で、
    sealed は ethics / acc のみ、
    RFL は sealed にならない不変条件を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    r = sim.run_simulation(
        runs=200,
        fabricate=False,
        fabricate_rate=0.15,
        seed=99,
        reset=True,
        reset_eval=True,
        keep_runs=True,
        queue_max_items=50,
        sample_runs=0,
    )

    assert "runs" in r and isinstance(r["runs"], list)
    assert len(r["runs"]) == 200


    _assert_sealed_only_ethics_or_acc(r)

    _assert_sealed_only_ethics_or_acc(r)


