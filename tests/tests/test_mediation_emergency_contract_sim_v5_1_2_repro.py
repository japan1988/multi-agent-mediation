
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import mediation_emergency_contract_sim_v5_1_2 as sim  # noqa: E402


def _patch_store_paths(monkeypatch, tmp_path: Path) -> None:
    trust_path = tmp_path / "model_trust_store.json"
    grants_path = tmp_path / "model_grants.json"
    eval_path = tmp_path / "eval_state.json"

    monkeypatch.setattr(sim, "TRUST_STORE_PATH", trust_path, raising=True)
    monkeypatch.setattr(sim, "GRANTS_STORE_PATH", grants_path, raising=True)
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", grants_path, raising=True)
    monkeypatch.setattr(sim, "EVAL_STATE_PATH", eval_path, raising=True)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", eval_path, raising=True)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _reason_sequence(index_rows: list[dict]) -> list[str]:
    return [str(row.get("primary_reason_code")) for row in index_rows]


def test_repro_summary_same_seed_same_contract_summary(tmp_path: Path, monkeypatch) -> None:
    _patch_store_paths(monkeypatch, tmp_path)

    out1 = tmp_path / "arl_out_1"
    out2 = tmp_path / "arl_out_2"

    r1 = sim.run_simulation(
        runs=100,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out1),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=10,
        sample_runs=3,
    )
    r2 = sim.run_simulation(
        runs=100,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out2),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=10,
        sample_runs=3,
    )

    assert "repro_summary" in r1
    assert "repro_summary" in r2

    s1 = r1["repro_summary"]
    s2 = r2["repro_summary"]

    assert s1["sim_version"] == "5.1.2"
    assert s2["sim_version"] == "5.1.2"
    assert s1["runs_requested"] == s2["runs_requested"] == 100
    assert s1["fabricate_rate"] == s2["fabricate_rate"] == 0.1
    assert s1["seed"] == s2["seed"] == 42
    assert s1["reset"] is True and s2["reset"] is True
    assert s1["reset_eval"] is True and s2["reset_eval"] is True
    assert s1["full_context_n"] == s2["full_context_n"] == 0
    assert s1["summary"] == s2["summary"]


def test_incident_index_reason_sequence_same_seed(tmp_path: Path, monkeypatch) -> None:
    _patch_store_paths(monkeypatch, tmp_path)

    out1 = tmp_path / "arl_out_1"
    out2 = tmp_path / "arl_out_2"

    sim.run_simulation(
        runs=100,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out1),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )
    sim.run_simulation(
        runs=100,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out2),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    idx1 = _read_jsonl(out1 / "incident_index.jsonl")
    idx2 = _read_jsonl(out2 / "incident_index.jsonl")

    assert len(idx1) == len(idx2)
    assert _reason_sequence(idx1) == _reason_sequence(idx2)

    states1 = [row.get("final_state") for row in idx1]
    states2 = [row.get("final_state") for row in idx2]
    assert states1 == states2

    sealed1 = [row.get("sealed") for row in idx1]
    sealed2 = [row.get("sealed") for row in idx2]
    assert sealed1 == sealed2


def test_repro_summary_written_inside_results_json(tmp_path: Path, monkeypatch) -> None:
    _patch_store_paths(monkeypatch, tmp_path)

    results = sim.run_simulation(
        runs=50,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(tmp_path / "arl_out"),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=5,
        sample_runs=2,
    )

    out_json = tmp_path / "results.json"
    sim.write_json(out_json, results)
    saved = json.loads(out_json.read_text(encoding="utf-8"))

    assert "repro_summary" in saved
    assert saved["repro_summary"]["sim_version"] == "5.1.2"
    assert saved["repro_summary"]["seed"] == 42
    assert saved["repro_summary"]["fabricate_rate"] == 0.1
    assert saved["repro_summary"]["summary"]["total_runs"] == 50


def test_verify_arl_rows_on_saved_incident_file(tmp_path: Path, monkeypatch) -> None:
    _patch_store_paths(monkeypatch, tmp_path)

    out_dir = tmp_path / "arl_out"

    sim.run_simulation(
        runs=100,
        fabricate=False,
        fabricate_rate=0.1,
        seed=42,
        reset=True,
        reset_eval=True,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out_dir),
        max_arl_files=100,
        full_context_n=0,
        key_mode="demo",
        key_file="",
        key_env="",
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    arl_files = sorted(out_dir.glob("INC#*.arl.jsonl"))
    assert arl_files, "incident ARL file was not generated"

    rows = _read_jsonl(arl_files[0])
    ok, err = sim.verify_arl_rows(
        key=b"DEMO_KEY_DO_NOT_USE_IN_PROD",
        rows=rows,
    )
    assert ok is True
    assert err is None
