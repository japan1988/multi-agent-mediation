# -*- coding: utf-8 -*-
"""
sim_batch_fixed.py
Batch runner: run multiple trials (raw/unfiltered and filtered),
collect logs, compute stats, and generate charts.
"""

import os
import sys
import time
import json
import csv
import math
import glob
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_first_stop_step(csv_path: Path) -> int:
    """Return first stop step from a log CSV."""
    if not csv_path.exists():
        return -1
    try:
        df = pd.read_csv(csv_path)
        if "event" not in df.columns or "step" not in df.columns:
            return -1
        stop_events = {"mediator_stop", "filter_block", "defeat_layer_stop", "inactive"}
        stop_df = df[df["event"].isin(stop_events)]
        if stop_df.empty:
            return -1
        return int(stop_df["step"].min())
    except Exception:
        return -1


def run_trial(mode: str, idx: int, script_name: str, out_dir: Path) -> Path:
    """Run one simulation trial."""
    out_csv = out_dir / f"{mode}_run_{idx:03d}.csv"
    cmd = [sys.executable, script_name, "--mode", mode, "--out", str(out_csv)]
    start = time.time()
    subprocess.run(cmd, check=False)
    elapsed = time.time() - start
    print(f"[{mode}] trial {idx:03d} done ({elapsed:.1f}s)")
    return out_csv


def aggregate_results(csv_files: list[Path], out_file: Path) -> None:
    """Aggregate stop steps and basic stats."""
    steps = [compute_first_stop_step(p) for p in csv_files if p.exists()]
    steps = [s for s in steps if s >= 0]
    if not steps:
        print("No valid results found.")
        return
    stats = {
        "count": len(steps),
        "mean": float(np.mean(steps)),
        "std": float(np.std(steps)),
        "min": int(np.min(steps)),
        "max": int(np.max(steps)),
    }
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in stats.items():
            writer.writerow([k, v])
    print(f"Aggregated → {out_file}")


def plot_results(raw_csv: Path, filtered_csv: Path, out_png: Path) -> None:
    """Plot comparison of raw vs filtered."""
    raw_df = pd.read_csv(raw_csv)
    filt_df = pd.read_csv(filtered_csv)
    plt.figure()
    plt.bar(["raw", "filtered"], [raw_df.loc[0, "value"], filt_df.loc[0, "value"]])
    plt.ylabel("Mean stop step")
    plt.title("Raw vs Filtered Simulation")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    print(f"Chart saved → {out_png}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--script", type=str, default="ai_mediation_all_in_one.py")
    parser.add_argument("--outdir", type=str, default="aggregate")
    args = parser.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(exist_ok=True)

    all_modes = ["raw", "filtered"]
    for mode in all_modes:
        csv_files = []
        with ProcessPoolExecutor() as ex:
            futures = [
                ex.submit(run_trial, mode, i, args.script, out_dir)
                for i in range(1, args.trials + 1)
            ]
            for fut in as_completed(futures):
                csv_files.append(fut.result())

        out_file = out_dir / f"{mode}_stats.csv"
        aggregate_results(csv_files, out_file)

    # Plot comparison
    plot_results(
        out_dir / "raw_stats.csv",
        out_dir / "filtered_stats.csv",
        out_dir / "comparison.png",
    )


if __name__ == "__main__":
    main()
