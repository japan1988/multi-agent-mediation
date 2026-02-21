# tests/test_mediation_emergency_contract_sim_v5_1_2_stress_runs.py
# -*- coding: utf-8 -*-
"""
Stress smoke test for v5.1.2 (subprocess run)

Goal:
- Verify the simulator completes a large number of runs in aggregation-only mode
  (no per-run retention by default).
- Emit compact results JSON for counters inspection.
- Optionally persist ARL only on abnormal runs (capped).
- v5.1.2: ARL filenames include incident prefix + incident index/counter artifacts.

Defaults (override via env vars):
- MAESTRO_STRESS_RUNS=10000
- MAESTRO_STRESS_SEED=42
- MAESTRO_STRESS_TIMEOUT_SEC=1800
- MAESTRO_SIM_SCRIPT=/path/to/mediation_emergency_contract_sim_v5_1_2.py

Run:
  pytest -q -m slow
Or heavier:
  MAESTRO_STRESS_RUNS=100000 pytest -q -m slow
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.slow
def test_stress_runs_completes(tmp_path: Path) -> None:
    runs = int(os.environ.get("MAESTRO_STRESS_RUNS", "10000"))
    seed = int(os.environ.get("MAESTRO_STRESS_SEED", "42"))
    timeout_sec = int(os.environ.get("MAESTRO_STRESS_TIMEOUT_SEC", "1800"))

    env_script = os.environ.get("MAESTRO_SIM_SCRIPT", "").strip()
    if env_script:
        script = Path(env_script).expanduser().resolve()
    else:
        repo_root = Path(__file__).resolve().parents[1]
        script = (repo_root / "mediation_emergency_contract_sim_v5_1_2.py").resolve()

    assert script.exists(), f"simulator script not found: {script}"

    results_json = tmp_path / "results_stress.json"
    arl_dir = tmp_path / "arl_out"
    arl_dir.mkdir(parents=True, exist_ok=True)

    # v5.1.2: aggregation-only by default (keep_runs=False). No --stress flag required/assumed.
    cmd = [
        sys.executable,
        str(script),
        "--runs",
        str(runs),
        "--seed",
        str(seed),
        "--queue-max-items",
        "0",
        "--sample-runs",
        "0",
        "--results-json",
        str(results_json),
        "--save-arl-on-abnormal",
        "--arl-out-dir",
        str(arl_dir),
        "--max-arl-files",
        "50",
        "--full-context-n",
        "0",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(tmp_path),  # isolate local store files (eval_state.json etc.)
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )

    if proc.returncode != 0:
        raise AssertionError(
            "stress run failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"returncode: {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )

    assert results_json.exists(), "results JSON was not created"
    data = json.loads(results_json.read_text(encoding="utf-8"))

    meta = data.get("meta", {}) or {}
    assert meta.get("version") == "5.1.2"
    # v5.1.2 default is aggregation-only (keep_runs=False)
    assert bool(meta.get("keep_runs")) is False

    # Count sanity
    hitl_counts = (data.get("hitl_queue", {}) or {}).get("counts", {}) or {}
    total_runs = int(hitl_counts.get("total_runs", -1))
    assert total_runs == runs

    # Abnormal ARL persistence sanity (bounded + consistent)
    arl_persist = data.get("abnormal_arl_persistence", {}) or {}
    abnormal_total = int(arl_persist.get("abnormal_total", 0))
    saved = int(arl_persist.get("saved", 0))
    skipped = int(arl_persist.get("skipped_by_cap", 0))

    assert saved <= abnormal_total
    if abnormal_total == 0:
        assert saved == 0 and skipped == 0

    # v5.1.2 filename pattern: INC#000001__SIM#B000001.arl.jsonl
    arl_files = sorted(arl_dir.glob("INC#*__SIM#B*.arl.jsonl"))
    assert len(arl_files) == saved
    assert len(arl_files) <= 50

    # v5.1.2: incident index artifacts exist iff at least one file was saved
    index_path = arl_dir / "incident_index.jsonl"
    counter_path = arl_dir / "incident_counter.txt"
    if saved > 0:
        assert index_path.exists(), "incident_index.jsonl should exist when incidents were saved"
        assert counter_path.exists(), "incident_counter.txt should exist when incidents were saved"

        # Best-effort: index lines count equals saved files count
        lines = index_path.read_text(encoding="utf-8").strip().splitlines()
        nonempty = [x for x in lines if x.strip()]
        assert len(nonempty) == saved
