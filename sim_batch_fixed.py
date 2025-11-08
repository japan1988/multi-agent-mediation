# -*- coding: utf-8 -*-
"""
sim_batch.py (fixed)

Batch runner for raw vs filtered modes.

- Runs N trials sequentially.
- For each trial:
    - Runs both "raw" and "filtered" modes via main.py with different configs.
    - Copies the produced CSV logs into:
        out/<run>/trials/trial-XXXXXX/{raw,filtered}.csv
- Aggregates:
    - steps / interventions / sealed flags → out/<run>/aggregate/stats.csv
    - first stop step → out/<run>/aggregate/first_stop.csv
- Draws simple charts with matplotlib:
    - sealed_ratio.png
    - hist_first_stop.png

Notes:
- No seaborn.
- One figure per chart.
- Uses default matplotlib colors.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUT_DIR_DEFAULT = BASE_DIR / "out"

MODES = [
    ("raw", str(BASE_DIR / "configs" / "ai_config_raw.json")),
    ("filtered", str(BASE_DIR / "configs" / "ai_config_filtered.json")),
]

STOP_EVENTS = {
    "mediator_stop",
    "filter_block",
    "defeat_layer_stop",
    "inactive",
}


# === Helpers =================================================================


def newest_file(dirpath: Path) -> Path | None:
    """Return newest *.csv in dirpath, or None if not found."""
    files = sorted(dirpath.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def derive_seed(master_seed: int, trial_id: int, mode_id: int) -> int:
    """Deterministic per-(trial, mode) seed."""
    return (
        master_seed * 1315423911
        + trial_id * 2654435761
        + mode_id * 97531
    ) & 0xFFFFFFFF


def compute_first_stop_step(csv_path: Path) -> int:
    """Return first stop step from CSV; -1 if not found/invalid."""
    if not csv_path.exists():
        return -1

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return -1

    if "event" not in df.columns or "step" not in df.columns:
        return -1

    mask = df["event"].isin(STOP_EVENTS)
    if not mask.any():
        return -1

    idx = mask.idxmax()
    try:
        return int(df.loc[idx, "step"])
    except Exception:
        return -1


def run_one_trial(
    trial_id: int,
    master_seed: int,
    out_trial: Path,
    retries: int = 2,
) -> List[Dict]:
    """
    Run one trial for all modes.

    - Calls main.py with different configs & seeds.
    - Collects logs from LOGS_DIR.
    - Writes normalized CSVs to out_trial.
    - Returns per-mode stats rows.
    """
    out_trial.mkdir(parents=True, exist_ok=True)
    stats_rows: List[Dict] = []

    for mode_id, (mode_key, cfg_path) in enumerate(MODES):
        seed = derive_seed(master_seed, trial_id, mode_id)
        tries = 0

        while True:
            try:
                before = set(glob.glob(str(LOGS_DIR / "*.csv")))

                env = os.environ.copy()
                env["AI_CONFIG_PATH"] = str(cfg_path)
                env["AI_MASTER_SEED"] = str(master_seed)
                env["AI_TRIAL_SEED"] = str(seed)

                # Optional: external step limit
                step_max = os.environ.get("STEP_MAX")
                if step_max is not None:
                    env["AI_STEP_MAX"] = step_max

                subprocess.run(
                    ["python", "main.py"],
                    cwd=str(BASE_DIR),
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                after = set(glob.glob(str(LOGS_DIR / "*.csv")))
                new_files = list(after - before)

                src_csv: Path | None
                if new_files:
                    src_csv = Path(new_files[0])
                else:
                    src_csv = newest_file(LOGS_DIR)

                if src_csv is None or not src_csv.exists():
                    raise RuntimeError("No CSV log found after running main.py")

                dst_csv = out_trial / f"{mode_key}.csv"
                df = pd.read_csv(src_csv)

                # enrich columns
                df["trial_id"] = trial_id
                df["mode"] = mode_key
                df["seed"] = seed

                if "event" in df.columns:
                    df["seal_flag"] = df["event"].isin(STOP_EVENTS).astype(int)
                    df["halt_reason"] = df["event"].where(
                        df["event"].isin(STOP_EVENTS),
                        "",
                    )
                else:
                    df["seal_flag"] = 0
                    df["halt_reason"] = ""

                # ensure expected columns exist
                for col in ["timestamp", "step", "emotion", "event"]:
                    if col not in df.columns:
                        if col == "event":
                            df[col] = ""
                        else:
                            df[col] = 0

                df.to_csv(dst_csv, index=False, encoding="utf-8")

                steps = int(df["step"].max()) if "step" in df.columns else 0
                interventions = int(
                    (df.get("event", pd.Series([])) == "mediator_stop").sum()
                )
                sealed = int(
                    df.get("event", pd.Series([])).isin(STOP_EVENTS).any()
                )

                stats_rows.append(
                    {
                        "trial_id": trial_id,
                        "mode": mode_key,
                        "steps": steps,
                        "interventions": interventions,
                        "sealed": sealed,
                    }
                )
                break

            except Exception as exc:
                tries += 1
                if tries > retries:
                    # write minimal CSV so pipeline continues deterministically
                    dst_csv = out_trial / f"{mode_key}.csv"
                    with dst_csv.open(
                        "w",
                        encoding="utf-8",
                        newline="",
                    ) as fp:
                        writer = csv.writer(fp)
                        writer.writerow(
                            [
                                "trial_id",
                                "mode",
                                "step",
                                "emotion",
                                "event",
                                "timestamp",
                                "seed",
                                "seal_flag",
                                "halt_reason",
                            ]
                        )
                        writer.writerow(
                            [
                                trial_id,
                                mode_key,
                                0,
                                0,
                                f"error:{exc}",
                                time.time(),
                                seed,
                                0,
                                "error",
                            ]
                        )

                    stats_rows.append(
                        {
                            "trial_id": trial_id,
                            "mode": mode_key,
                            "steps": 0,
                            "interventions": 0,
                            "sealed": 0,
                        }
                    )
                    break

                # simple backoff
                time.sleep(0.3 * (2 ** (tries - 1)))

    return stats_rows


def aggregate(outdir: Path, num_trials: int) -> None:
    """Aggregate per-trial CSV into stats & first-stop CSV + charts."""
    trials_dir = outdir / "trials"
    agg_dir = outdir / "aggregate"
    agg_dir.mkdir(parents=True, exist_ok=True)

    # --- stats.csv ---
    stats: List[Dict] = []

    for trial_id in range(num_trials):
        for mode in ("raw", "filtered"):
            csv_path = trials_dir / f"trial-{trial_id:06d}" / f"{mode}.csv"
            if not csv_path.exists():
                continue

            try:
                df = pd.read_csv(csv_path)
            except Exception:
                continue

            steps = int(df["step"].max()) if "step" in df.columns else 0
            interventions = int(
                (df.get("event", pd.Series([])) == "mediator_stop").sum()
            )
            sealed = int(
                df.get("event", pd.Series([])).isin(STOP_EVENTS).any()
            )

            stats.append(
                {
                    "trial_id": trial_id,
                    "mode": mode,
                    "steps": steps,
                    "interventions": interventions,
                    "sealed": sealed,
                }
            )

    stats_df = pd.DataFrame(stats)
    stats_df.to_csv(
        agg_dir / "stats.csv",
        index=False,
        encoding="utf-8",
    )

    # --- first_stop.csv ---
    first_rows: List[Dict] = []

    for trial_id in range(num_trials):
        for mode in ("raw", "filtered"):
            csv_path = trials_dir / f"trial-{trial_id:06d}" / f"{mode}.csv"
            first_rows.append(
                {
                    "trial_id": trial_id,
                    "mode": mode,
                    "first_stop_step": compute_first_stop_step(csv_path),
                }
            )

    first_df = pd.DataFrame(first_rows)
    first_df.to_csv(
        agg_dir / "first_stop.csv",
        index=False,
        encoding="utf-8",
    )

    # --- charts ---
    try:
        plt.figure()
        if not stats_df.empty:
            pivot = (
                stats_df.pivot_table(
                    index="mode",
                    values="sealed",
                    aggfunc="mean",
                )
                .reset_index()
            )
            plt.bar(pivot["mode"], pivot["sealed"])
            plt.title("Sealed ratio by mode")
            plt.xlabel("Mode")
            plt.ylabel("Ratio")
            plt.tight_layout()
            plt.savefig(agg_dir / "sealed_ratio.png")
        plt.close()
    except Exception:
        plt.close()

    try:
        plt.figure()
        for mode in ("raw", "filtered"):
            data = first_df[
                (first_df["mode"] == mode)
                & (first_df["first_stop_step"] >= 0)
            ]["first_stop_step"].to_numpy()

            if data.size > 0:
                plt.hist(data, bins=50, alpha=0.5, label=mode)

        plt.title("First stop step histogram")
        plt.xlabel("Step")
        plt.ylabel("Count")
        plt.legend()
        plt.tight_layout()
        plt.savefig(agg_dir / "hist_first_stop.png")
        plt.close()
    except Exception:
        plt.close()


def write_manifest(outdir: Path, meta: Dict) -> None:
    (outdir / "manifest.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(root: Path) -> None:
    manifest: Dict[str, str] = {}

    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            manifest[rel] = sha256_file(path)

    (root / "checksums.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(
            OUT_DIR_DEFAULT / time.strftime("run-%Y%m%d-%H%M%S")
        ),
    )
    parser.add_argument(
        "--trials",
        "-n",
        dest="N",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--retries",
        "-r",
        dest="R",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "trials").mkdir(parents=True, exist_ok=True)

    all_stats: List[Dict] = []

    for trial_id in range(args.N):
        stats_rows = run_one_trial(
            trial_id,
            args.seed,
            outdir / "trials" / f"trial-{trial_id:06d}",
            retries=args.R,
        )
        all_stats.extend(stats_rows)

    aggregate(outdir, args.N)

    write_manifest(
        outdir,
        {
            "created_at": time.time(),
            "trials": args.N,
            "retries": args.R,
            "seed": args.seed,
        },
    )
    write_checksums(outdir)


if __name__ == "__main__":
    main()
