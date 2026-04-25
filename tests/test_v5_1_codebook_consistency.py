# tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

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

    assert t1 == t2

    if cd1 is not None or cd2 is not None:
        assert cd1 is not None
        assert cd2 is not None

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