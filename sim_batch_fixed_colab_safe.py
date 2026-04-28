# -*- coding: utf-8 -*-
"""
sim_batch_fixed.py

Batch runner:
- Run N trials for two modes: raw / filtered
- Aggregate first-stop-step statistics
- Generate a comparison chart

Dependencies:
- numpy
- pandas
- matplotlib

Supported environments:
- Python 3.9+
- Google Colab
- GitHub Actions
- local PC

Usage:
    python sim_batch_fixed.py --trials 5 --outdir aggregate

Notes:
- This file uses plt.savefig() instead of plt.show().
- The output directory is created automatically.
- run_trial() is a dummy implementation.
- This file intentionally does not call subprocess or any external simulator.
- If a real external simulator is needed later, add an explicit HITL-gated
  launcher instead of silently starting an external process.
"""

from __future__ import annotations

import argparse
import csv
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# === Settings =================================================================

STOP_EVENTS = {
    "mediator_stop",
    "filter_block",
    "defeat_layer_stop",
    "inactive",
}

CSV_READ_ERRORS = (
    OSError,
    ValueError,
    pd.errors.EmptyDataError,
    pd.errors.ParserError,
)

LOGGER = logging.getLogger(__name__)


# === Core functions ===========================================================


def configure_logging() -> None:
    """Configure compact console logging for local and CI runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def compute_first_stop_step(csv_path: Path) -> int:
    """Return the first stop-event step from a CSV file, or -1 if not found."""
    try:
        df = pd.read_csv(csv_path)
    except CSV_READ_ERRORS as exc:
        LOGGER.warning("failed to read CSV for first-stop detection: %s (%s)", csv_path, exc)
        return -1

    if "step" not in df.columns or "event" not in df.columns:
        LOGGER.warning("CSV missing required columns step/event: %s", csv_path)
        return -1

    hit = df[df["event"].isin(STOP_EVENTS)]
    if hit.empty:
        return -1

    try:
        return int(hit.iloc[0]["step"])
    except (TypeError, ValueError) as exc:
        LOGGER.warning("invalid step value in CSV: %s (%s)", csv_path, exc)
        return -1


def run_trial(mode: str, trial_idx: int, out_dir: Path) -> Path:
    """
    Generate one dummy trial CSV and return its path.

    This function intentionally does not call an external simulator.
    It is safe for local batch testing and CI smoke checks.
    """
    csv_path = out_dir / f"{mode}_trial{trial_idx:03d}.csv"

    stop_step = 7 + trial_idx if mode == "raw" else 5 + trial_idx
    rows = [{"step": step, "event": "act_continue"} for step in range(stop_step)]
    rows.append({"step": stop_step, "event": "mediator_stop"})

    with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=["step", "event"])
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def aggregate_results(csv_files: list[Path], out_file: Path) -> None:
    """Aggregate first-stop-step values and write them as metric/value CSV."""
    steps = [compute_first_stop_step(path) for path in csv_files if path.exists()]
    valid_steps = [step for step in steps if step >= 0]

    if not valid_steps:
        LOGGER.warning("no valid results found for %s", out_file.name)
        return

    arr = np.asarray(valid_steps, dtype=float)
    stats = {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=0)),
        "min": int(np.min(arr)),
        "max": int(np.max(arr)),
    }

    with out_file.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(["metric", "value"])
        for key, value in stats.items():
            writer.writerow([key, value])

    LOGGER.info("aggregated -> %s", out_file)


def _read_mean_from_stats(path: Path) -> float:
    """Read the mean value from a metric/value statistics CSV."""
    try:
        df = pd.read_csv(path)
    except CSV_READ_ERRORS as exc:
        LOGGER.warning("failed to read stats CSV: %s (%s)", path, exc)
        return 0.0

    try:
        if "metric" in df.columns and "value" in df.columns:
            hit = df[df["metric"] == "mean"]
            if not hit.empty:
                return float(hit.iloc[0]["value"])

        if "value" in df.columns and not df.empty:
            return float(df.iloc[0]["value"])
    except (TypeError, ValueError) as exc:
        LOGGER.warning("invalid mean value in stats CSV: %s (%s)", path, exc)

    return 0.0


def plot_results(raw_csv: Path, filtered_csv: Path, out_png: Path) -> None:
    """Create a bar chart comparing raw and filtered mean stop steps."""
    raw_mean = _read_mean_from_stats(raw_csv)
    filtered_mean = _read_mean_from_stats(filtered_csv)

    plt.figure()
    plt.bar(["raw", "filtered"], [raw_mean, filtered_mean])
    plt.ylabel("Mean stop step")
    plt.title("Raw vs Filtered Simulation")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

    LOGGER.info("chart saved -> %s", out_png)


def run_trials_for_mode(
    *,
    mode: str,
    trials: int,
    out_dir: Path,
    workers: int,
) -> list[Path]:
    """Run trials for one mode, sequentially or with worker processes."""
    if workers <= 1:
        return [run_trial(mode, idx, out_dir) for idx in range(1, trials + 1)]

    csv_files: list[Path] = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(run_trial, mode, idx, out_dir)
            for idx in range(1, trials + 1)
        ]

        for future in as_completed(futures):
            csv_files.append(future.result())

    return csv_files


# === Main =====================================================================


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of trials per mode.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="aggregate",
        help="Output directory.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes. Use 1 for safest CI/Colab behavior.",
    )

    args = parser.parse_args()

    if args.trials < 1:
        raise ValueError("--trials must be 1 or greater.")

    if args.workers < 1:
        raise ValueError("--workers must be 1 or greater.")

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for mode in ("raw", "filtered"):
        csv_files = run_trials_for_mode(
            mode=mode,
            trials=args.trials,
            out_dir=out_dir,
            workers=args.workers,
        )
        aggregate_results(csv_files, out_dir / f"{mode}_stats.csv")

    plot_results(
        out_dir / "raw_stats.csv",
        out_dir / "filtered_stats.csv",
        out_dir / "comparison.png",
    )

    LOGGER.info("batch completed successfully")


if __name__ == "__main__":
    main()
