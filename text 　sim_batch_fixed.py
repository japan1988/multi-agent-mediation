# -*- coding: utf-8 -*-
"""
sim_batch_fixed_final.py

Batch runner:
- Run N trials for two modes (raw / filtered)
- Aggregate 'first stop step' statistics
- Generate comparison chart

依存: numpy, pandas, matplotlib
動作環境: Python 3.9+ / Google Colab / GitHub Actions / ローカルPC

使用例:
    python sim_batch_fixed_final.py --trials 5 --outdir aggregate

メモ:
- Colabでは plt.show() の代わりに plt.savefig() を使用。
- aggregate ディレクトリが無ければ自動生成。
- run_trial() 内はダミー実装。実際に外部シミュレータを呼ぶ場合は subprocess.run に差し替え可。
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


# === 設定 ============================================================
STOP_EVENTS = {"mediator_stop", "filter_block", "defeat_layer_stop", "inactive"}


# === 関数群 ==========================================================
def compute_first_stop_step(csv_path: Path) -> int:
    """CSVから最初の停止イベントのstepを返す。見つからなければ-1。"""
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return -1
    if "step" not in df.columns or "event" not in df.columns:
        return -1
    hit = df[df["event"].isin(STOP_EVENTS)]
    if hit.empty:
        return -1
    return int(hit.iloc[0]["step"])


def run_trial(mode: str, trial_idx: int, out_dir: Path) -> Path:
    """
    各トライアルのダミーCSVを生成してパスを返す。
    実シミュレーションを呼ぶ場合は subprocess.run に差し替える。
    """
    csv_path = out_dir / f"{mode}_trial{trial_idx:03d}.csv"

    # --- ダミーデータ生成 ---
    stop_step = 7 + trial_idx if mode == "raw" else 5 + trial_idx
    rows = [{"step": s, "event": "act_continue"} for s in range(stop_step)]
    rows.append({"step": stop_step, "event": "mediator_stop"})
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "event"])
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def aggregate_results(csv_files: List[Path], out_file: Path) -> None:
    """first stop step を集計し、'metric,value' 形式で保存。"""
    steps = [compute_first_stop_step(p) for p in csv_files if p.exists()]
    steps = [s for s in steps if s >= 0]
    if not steps:
        print(f"[WARN] No valid results found for {out_file.name}")
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
    print(f"[INFO] Aggregated → {out_file}")


def plot_results(raw_csv: Path, filtered_csv: Path, out_png: Path) -> None:
    """raw と filtered の平均停止ステップを棒グラフで比較。"""
    def read_mean(p: Path) -> float:
        try:
            df = pd.read_csv(p)
            hit = df[df["metric"] == "mean"]
            if not hit.empty:
                return float(hit.iloc[0]["value"])
            return float(df.iloc[0]["value"])
        except Exception:
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
    print(f"[INFO] Chart saved → {out_png}")


# === メイン処理 =======================================================
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5, help="モードごとのトライアル回数")
    parser.add_argument("--outdir", type=str, default="aggregate", help="出力ディレクトリ")
    args = parser.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_modes = ["raw", "filtered"]
    for mode in all_modes:
        csv_files: List[Path] = []
        # Colab/Windows対応: __main__ ガードを使用して安全に並列実行
        with ProcessPoolExecutor() as ex:
            futures = [ex.submit(run_trial, mode, i, out_dir) for i in range(1, args.trials + 1)]
            for fut in as_completed(futures):
                csv_files.append(fut.result())

        out_file = out_dir / f"{mode}_stats.csv"
        aggregate_results(csv_files, out_file)

    # 比較チャート生成
    plot_results(
        out_dir / "raw_stats.csv",
        out_dir / "filtered_stats.csv",
        out_dir / "comparison.png",
    )

    print("[INFO] Batch completed successfully.")


if __name__ == "__main__":
    main()
