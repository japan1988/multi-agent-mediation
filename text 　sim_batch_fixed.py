# -*- coding: utf-8 -*-
"""
Batch runner: run N trials for two modes (raw / filtered),
aggregate 'first stop step' statistics, and make a comparison chart.

- 依存: numpy, pandas, matplotlib
- 使い方例:
    python sim_batch_fixed.py --trials 5 --outdir aggregate
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# === Helpers ================================================================

STOP_EVENTS = {"mediator_stop", "filter_block", "defeat_layer_stop", "inactive"}


def compute_first_stop_step(csv_path: Path) -> int:
    """
    CSV から最初の停止イベントの step を返す。
    対象の CSV は 'step' と 'event' 列を持つことを想定。
    見つからなければ -1。
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return -1

    if "step" not in df.columns or "event" not in df.columns:
        return -1

    hit = df[df["event"].isin(STOP_EVENTS)]
    if hit.empty:
        return -1

    # 最初に発生した停止イベントの step
    return int(hit.iloc[0]["step"])


def run_trial(mode: str, trial_idx: int, out_dir: Path) -> Path:
    """
    1トライアル分のダミーCSVを生成してパスを返す。
    実際に外部スクリプトを呼ぶ場合は、この関数内で subprocess.run などに差し替える。
    """
    csv_path = out_dir / f"{mode}_trial{trial_idx:03d}.csv"

    # ダミーデータ: 0..N のステップを記録し、最後に停止イベントを1つ入れる
    stop_step = 7 + trial_idx if mode == "raw" else 5 + trial_idx
    rows = []
    for s in range(stop_step):
        rows.append({"step": s, "event": "act_continue"})
    rows.append({"step": stop_step, "event": "mediator_stop"})

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "event"])
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def aggregate_results(csv_files: List[Path], out_file: Path) -> None:
    """
    first stop step を集計し、'metric,value' 形式の CSV を出力。
    """
    steps = [compute_first_stop_step(p) for p in csv_files if p.exists()]
    steps = [s for s in steps if s >= 0]

    if not steps:
        print("No valid results found.")
        return

    arr = np.asarray(steps, dtype=float)
    stats = {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=0)),
        "min": int(np.min(arr)),
        "max": int(np.max(arr)),
    }

    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in stats.items():
            writer.writerow([k, v])

    print(f"Aggregated → {out_file}")


def plot_results(raw_csv: Path, filtered_csv: Path, out_png: Path) -> None:
    """
    raw と filtered の平均停止ステップを棒グラフで比較。
    ※色指定なし（ポリシー準拠）
    """
    def read_mean(p: Path) -> float:
        df = pd.read_csv(p)
        if "metric" in df.columns and "value" in df.columns:
            hit = df[df["metric"] == "mean"]
            if not hit.empty:
                return float(hit.iloc[0]["value"])
            # フォールバック: 先頭行の value
            return float(df.iloc[0]["value"])
        # 想定外形式は 0 扱い
        return 0.0

    raw_mean = read_mean(raw_csv)
    filt_mean = read_mean(filtered_csv)

    plt.figure()
    plt.bar(["raw", "filtered"], [raw_mean, filt_mean])
    plt.ylabel("Mean stop step")
    plt.title("Raw vs Filtered Simulation")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    print(f"Chart saved → {out_png}")


# === Main ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--outdir", type=str, default="aggregate")
    args = parser.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(exist_ok=True)

    all_modes = ["raw", "filtered"]

    for mode in all_modes:
        csv_files: List[Path] = []
        with ProcessPoolExecutor() as ex:
            futures = [
                ex.submit(run_trial, mode, i, out_dir)
                for i in range(1, args.trials + 1)
            ]
            for fut in as_completed(futures):
                csv_files.append(fut.result())

        out_file = out_dir / f"{mode}_stats.csv"
        aggregate_results(csv_files, out_file)

    # 比較チャート作成
    plot_results(
        out_dir / "raw_stats.csv",
        out_dir / "filtered_stats.csv",
        out_dir / "comparison.png",
    )


if __name__ == "__main__":
    main()
