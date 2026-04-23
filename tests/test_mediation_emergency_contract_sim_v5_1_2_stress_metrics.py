# tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import mediation_emergency_contract_sim_v5_1_2 as sim


def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        _fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _require_ge(actual: int, threshold: int, message: str) -> None:
    if actual < threshold:
        _fail(f"{message} (actual={actual!r}, threshold={threshold!r})")


def _require_in_range(value: float, low: float, high: float, message: str) -> None:
    if not (low <= value <= high):
        _fail(f"{message} (actual={value!r}, low={low!r}, high={high!r})")


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


def _queue_counts(results: Dict[str, Any]) -> Dict[str, Any]:
    return (((results or {}).get("hitl_queue") or {}).get("counts") or {})


def _abnormal(results: Dict[str, Any]) -> Dict[str, Any]:
    return (results or {}).get("abnormal_arl_persistence", {}) or {}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _assert_sealed_only_ethics_or_acc(results: Dict[str, Any]) -> None:
    runs = results.get("runs", []) or []
    for run in runs:
        for row in (run.get("arl", []) or []):
            layer = row.get("layer")
            sealed = bool(row.get("sealed", False))
            if sealed:
                _require(
                    layer in (sim.LAYER_ETHICS, sim.LAYER_ACC),
                    f"sealed row must be ethics/acc only (layer={layer!r})",
                )
            if layer == sim.LAYER_RFL:
                _require(sealed is False, "RFL rows must never be sealed")


def test_v512_operational_resilience_clean_runs_large(
    monkeypatch, tmp_path: Path
) -> None:
    """
    clean run 大量反復での運用耐性確認。
    keep_runs=False でメモリ肥大を避けつつ、
    queue / trust / eval / abnormal persistence の整合を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    results = sim.run_simulation(
        runs=1000,
        fabricate=False,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    counts = _queue_counts(results)
    abnormal = _abnormal(results)

    _require_equal(counts.get("total_runs"), 1000, "total_runs mismatch")
    _require_equal(
        counts.get("by_state", {}).get("CONTRACT_EFFECTIVE", 0),
        1000,
        "CONTRACT_EFFECTIVE count mismatch",
    )
    _require_equal(counts.get("queue_size", 0), 0, "queue_size mismatch")
    _require_equal(abnormal.get("abnormal_total", 0), 0, "abnormal_total mismatch")
    _require_equal(abnormal.get("saved", 0), 0, "saved mismatch")
    _require_equal(abnormal.get("skipped_by_cap", 0), 0, "skipped_by_cap mismatch")

    eval_after = results.get("eval_after", {})
    _require_equal(
        eval_after.get("clean_completion_count"),
        1000,
        "clean_completion_count mismatch",
    )
    _require_equal(
        eval_after.get("multiplier"),
        sim.EVAL_MULTIPLIER_CAP,
        "multiplier mismatch",
    )

    trust_after = results.get("trust_after", {})
    _require_in_range(
        trust_after.get("trust_score", -1),
        sim.TRUST_MIN,
        sim.TRUST_MAX,
        "trust_score out of range",
    )


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

    result_1 = sim.run_simulation(**params)
    result_2 = sim.run_simulation(**params)

    counts_1 = _queue_counts(result_1)
    counts_2 = _queue_counts(result_2)
    _require_equal(counts_1, counts_2, "queue counts must be deterministic")

    abnormal_1 = _abnormal(result_1)
    abnormal_2 = _abnormal(result_2)
    _require_equal(
        abnormal_1,
        abnormal_2,
        "abnormal persistence summary must be deterministic",
    )

    trust_1 = dict(result_1.get("trust_after", {}))
    trust_2 = dict(result_2.get("trust_after", {}))
    cooldown_1 = trust_1.pop("cooldown_until", None)
    cooldown_2 = trust_2.pop("cooldown_until", None)

    _require_equal(
        trust_1,
        trust_2,
        "trust_after must match except for cooldown_until",
    )

    if cooldown_1 is not None or cooldown_2 is not None:
        _require(cooldown_1 is not None, "cooldown_1 must exist if either cooldown exists")
        _require(cooldown_2 is not None, "cooldown_2 must exist if either cooldown exists")

    _require_equal(
        result_1.get("eval_after"),
        result_2.get("eval_after"),
        "eval_after must be deterministic",
    )
    _require_ge(
        abnormal_1.get("abnormal_total", 0),
        1,
        "abnormal_total should be positive in mixed mode",
    )


def test_v512_abnormal_arl_persistence_and_incident_index(
    monkeypatch, tmp_path: Path
) -> None:
    """
    異常時のみ ARL 保存 + incident index / counter の整合確認。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    out_dir = tmp_path / "arl_out"
    results = sim.run_simulation(
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

    abnormal = _abnormal(results)
    saved = int(abnormal.get("saved", 0))
    abnormal_total = int(abnormal.get("abnormal_total", 0))
    skipped = int(abnormal.get("skipped_by_cap", 0))

    _require_ge(abnormal_total, 1, "abnormal_total should be positive")
    _require_equal(saved, min(abnormal_total, 30), "saved count mismatch")
    _require_equal(skipped, max(0, abnormal_total - 30), "skipped_by_cap mismatch")

    arl_files = sorted(out_dir.glob("INC#*.arl.jsonl"))
    _require_equal(len(arl_files), saved, "saved ARL file count mismatch")

    index_path = out_dir / "incident_index.jsonl"
    counter_path = out_dir / "incident_counter.txt"

    _require(index_path.exists(), "incident_index.jsonl should exist")
    _require(counter_path.exists(), "incident_counter.txt should exist")

    index_rows = _read_jsonl(index_path)
    _require_equal(len(index_rows), saved, "incident_index row count mismatch")

    counter_value = int(counter_path.read_text(encoding="utf-8").strip())
    _require_equal(counter_value, saved + 1, "incident_counter next value mismatch")

    incident_ids = set()
    for row in index_rows:
        incident_id = row.get("incident_id")
        arl_path = Path(row.get("arl_path", ""))

        _require(bool(incident_id), "incident_id should not be empty")
        _require(
            incident_id not in incident_ids,
            f"duplicate incident_id: {incident_id!r}",
        )
        _require(arl_path.exists(), f"arl_path should exist: {arl_path!s}")

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

    results = sim.run_simulation(
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

    _require("runs" in results, "results must contain 'runs'")
    _require(isinstance(results["runs"], list), "'runs' must be a list")
    _require_equal(len(results["runs"]), 200, "runs length mismatch")

    _assert_sealed_only_ethics_or_acc(results)
