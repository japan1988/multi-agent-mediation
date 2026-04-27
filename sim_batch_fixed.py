# -*- coding: utf-8 -*-
"""
sim_batch_fixed.py

Batch runner for raw vs filtered modes.

- Runs N trials sequentially.
- For each trial:
    - Runs both "raw" and "filtered" modes via target simulation script
      (default: ai_mediation_all_in_one.py, overridable by SIM_MAIN env).
    - Copies the produced CSV logs into:
        out/<run>/trials/trial-XXXXXX/{raw,filtered}.csv
- Aggregates:
    - steps / interventions / sealed flags -> out/<run>/aggregate/stats.csv
    - first stop step -> out/<run>/aggregate/first_stop.csv
- Draws simple charts with matplotlib:
    - sealed_ratio.png
    - hist_first_stop.png

Notes:
- No seaborn.
- One figure per chart.
- Uses default matplotlib colors.
- Subprocess execution is HITL-gated via --hitl-approved or
  SIM_BATCH_HITL_APPROVED=1.
- The target script is resolved and constrained to this repository directory.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# === Config ===================================================================

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUT_DIR_DEFAULT = BASE_DIR / "out"

# 実行対象スクリプト:
# 環境変数 SIM_MAIN があればそれを優先、なければ既定のメインスクリプトを使う
TARGET_SCRIPT = os.environ.get("SIM_MAIN", "ai_mediation_all_in_one.py")

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

HITL_APPROVAL_ENV = "SIM_BATCH_HITL_APPROVED"
HITL_APPROVED_VALUES = {"1", "true", "yes", "y", "approved"}


# === HITL guard ================================================================


class HitlApprovalError(PermissionError):
    """Raised when subprocess execution lacks explicit HITL approval."""


def _env_hitl_approved() -> bool:
    value = os.environ.get(HITL_APPROVAL_ENV, "")
    return value.strip().lower() in HITL_APPROVED_VALUES


def require_hitl_approval_for_subprocess(
    *,
    approved: bool,
    command: list[str],
    target_script: str,
) -> None:
    """
    Require explicit HITL approval before subprocess execution.

    This batch runner starts another Python process. Even though the default
    target is a local simulation script, process execution is treated as a
    side-effect boundary and must be explicitly approved.
    """
    if approved:
        return

    command_text = " ".join(command)
    raise HitlApprovalError(
        "HITL approval required before subprocess execution. "
        f"Set --hitl-approved or {HITL_APPROVAL_ENV}=1. "
        f"target_script={target_script!r} command={command_text!r}"
    )


# === Helpers ==================================================================


def resolve_target_script(target_script: str) -> Path:
    """
    Resolve and validate the local target simulation script.

    The target must:
    - be a Python file
    - exist
    - be located under BASE_DIR
    """
    raw_path = Path(target_script)

    if raw_path.is_absolute():
        target_path = raw_path.resolve()
    else:
        target_path = (BASE_DIR / raw_path).resolve()

    if target_path.suffix != ".py":
        raise ValueError(f"target script must be a .py file: {target_script!r}")

    if not target_path.exists():
        raise FileNotFoundError(f"target script not found: {target_path}")

    try:
        target_path.relative_to(BASE_DIR)
    except ValueError as exc:
        raise ValueError(
            f"target script must be under BASE_DIR: {target_path}"
        ) from exc

    return target_path


def newest_file(dirpath: Path) -> Path | None:
    """Return the newest *.csv file in dirpath, or None if not found."""
    candidates = list(dirpath.glob("*.csv"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def derive_seed(master_seed: int, trial_id: int, mode_index: int) -> int:
    """
    Derive a stable per-(trial, mode) seed from a master seed.

    Use a simple hash mix to avoid collisions between modes/trials.
    """
    h = hashlib.sha256()
    h.update(str(master_seed).encode("utf-8"))
    h.update(str(trial_id).encode("utf-8"))
    h.update(str(mode_index).encode("utf-8"))
    return int.from_bytes(h.digest()[:4], "big")


def compute_first_stop_step(csv_path: Path) -> int:
    """
    Return the step of the first STOP_EVENTS in a log CSV.

    If not found or invalid, return -1.
    """
    if not csv_path.exists():
        return -1

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


def run_one_trial(
    trial_id: int,
    master_seed: int,
    out_trial_dir: Path,
    retries: int = 2,
    *,
    hitl_approved: bool = False,
) -> list[dict[str, object]]:
    """
    Run one trial for both raw/filtered modes.

    - Executes TARGET_SCRIPT with different configs and seeds.
    - Copies and enriches CSV logs into out_trial_dir.
    - Returns per-mode summary stats.
    """
    out_trial_dir.mkdir(parents=True, exist_ok=True)
    stats_rows: list[dict[str, object]] = []

    effective_hitl_approved = hitl_approved or _env_hitl_approved()
    target_path = resolve_target_script(TARGET_SCRIPT)
    command = [sys.executable, str(target_path)]

    require_hitl_approval_for_subprocess(
        approved=effective_hitl_approved,
        command=command,
        target_script=str(target_path),
    )

    for mode_index, (mode_key, cfg_path) in enumerate(MODES):
        seed = derive_seed(master_seed, trial_id, mode_index)
        attempt = 0

        while True:
            try:
                before = set(glob.glob(str(LOGS_DIR / "*.csv")))

                env = os.environ.copy()
                env["AI_CONFIG_PATH"] = cfg_path
                env["AI_MASTER_SEED"] = str(master_seed)
                env["AI_TRIAL_SEED"] = str(seed)

                # 任意の最大ステップを外部から渡したい場合に対応
                if "STEP_MAX" in os.environ:
                    env["AI_STEP_MAX"] = os.environ["STEP_MAX"]

                subprocess.run(  # nosec B603 - HITL-gated local simulator execution; shell=False.
                    command,
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
                    src_csv = Path(max(new_files, key=os.path.getmtime))
                else:
                    src_csv = newest_file(LOGS_DIR)

                if src_csv is None or not src_csv.exists():
                    raise RuntimeError("No CSV log found after simulation run.")

                df = pd.read_csv(src_csv)

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

                if "step" not in df.columns:
                    df["step"] = 0
                if "timestamp" not in df.columns:
                    df["timestamp"] = 0.0

                dst_csv = out_trial_dir / f"{mode_key}.csv"
                df.to_csv(dst_csv, index=False, encoding="utf-8")

                steps = int(df["step"].max()) if "step" in df.columns else 0
                event_series = df.get("event", pd.Series([], dtype=str))
                interventions = int((event_series == "mediator_stop").sum())
                sealed = int(event_series.isin(STOP_EVENTS).any())

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
            except HitlApprovalError:
                raise
            except Exception as exc:  # noqa: BLE001
                attempt += 1

                if attempt > retries:
                    dst_csv = out_trial_dir / f"{mode_key}.csv"
                    with dst_csv.open("w", encoding="utf-8", newline="") as file_obj:
                        writer = csv.writer(file_obj)
                        writer.writerow(
                            [
                                "trial_id",
                                "mode",
                                "step",
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

                time.sleep(0.3 * (2 ** (attempt - 1)))

    return stats_rows


def aggregate(outdir: Path, num_trials: int) -> None:
    """Aggregate all trial CSVs into summary CSVs and charts."""
    trials_dir = outdir / "trials"
    agg_dir = outdir / "aggregate"
    agg_dir.mkdir(parents=True, exist_ok=True)

    # ---- stats.csv -----------------------------------------------------------

    stats: list[dict[str, object]] = []

    for trial_id in range(num_trials):
        for mode in ("raw", "filtered"):
            path = trials_dir / f"trial-{trial_id:06d}" / f"{mode}.csv"
            if not path.exists():
                continue

            try:
                df = pd.read_csv(path)
            except Exception:
                continue

            steps = int(df.get("step", pd.Series([0])).max())
            event_series = df.get("event", pd.Series([], dtype=str))
            interventions = int((event_series == "mediator_stop").sum())
            sealed = int(event_series.isin(STOP_EVENTS).any())

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

    # ---- first_stop.csv ------------------------------------------------------

    first_rows: list[dict[str, object]] = []

    for trial_id in range(num_trials):
        for mode in ("raw", "filtered"):
            path = trials_dir / f"trial-{trial_id:06d}" / f"{mode}.csv"
            first_rows.append(
                {
                    "trial_id": trial_id,
                    "mode": mode,
                    "first_stop_step": compute_first_stop_step(path),
                }
            )

    first_df = pd.DataFrame(first_rows)
    first_df.to_csv(
        agg_dir / "first_stop.csv",
        index=False,
        encoding="utf-8",
    )

    # ---- charts --------------------------------------------------------------

    try:
        if not stats_df.empty:
            pivot = (
                stats_df.groupby("mode")["sealed"]
                .mean()
                .reindex(["raw", "filtered"])
            )

            plt.figure()
            plt.bar(pivot.index, pivot.values)
            plt.title("Sealed ratio by mode")
            plt.xlabel("Mode")
            plt.ylabel("Ratio (0-1)")
            plt.tight_layout()
            plt.savefig(agg_dir / "sealed_ratio.png")
            plt.close()
    except Exception:
        # Chart generation failure is non-critical for batch aggregation.
        pass

    try:
        plt.figure()
        for mode in ("raw", "filtered"):
            data = first_df[
                (first_df["mode"] == mode) & (first_df["first_stop_step"] >= 0)
            ]["first_stop_step"].to_numpy()

            if data.size > 0:
                counts, bins = np.histogram(data, bins=40)
                centers = (bins[:-1] + bins[1:]) / 2.0
                plt.plot(centers, counts, marker="o", linestyle="-", label=mode)

        plt.title("First stop step distribution")
        plt.xlabel("Step")
        plt.ylabel("Count")
        plt.legend()
        plt.tight_layout()
        plt.savefig(agg_dir / "hist_first_stop.png")
        plt.close()
    except Exception:
        # Chart generation failure is non-critical for batch aggregation.
        pass


def write_manifest(outdir: Path, meta: dict[str, object]) -> None:
    """Write run metadata as manifest.json."""
    (outdir / "manifest.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    """Return SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(root: Path) -> None:
    """Write checksums.json for all files under root."""
    manifest: dict[str, str] = {}

    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            manifest[rel] = sha256_file(path)

    (root / "checksums.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


# === Main =====================================================================


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(OUT_DIR_DEFAULT / time.strftime("run-%Y%m%d-%H%M%S")),
        help="Output root directory.",
    )
    parser.add_argument(
        "--trials",
        "-n",
        dest="num_trials",
        type=int,
        default=10,
        help="Number of trials to run.",
    )
    parser.add_argument(
        "--retries",
        "-r",
        dest="retries",
        type=int,
        default=2,
        help="Max retries per (mode, trial) on failure.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Master random seed.",
    )
    parser.add_argument(
        "--hitl-approved",
        action="store_true",
        help=(
            "Explicit HITL approval for local subprocess execution. "
            f"Equivalent to setting {HITL_APPROVAL_ENV}=1."
        ),
    )

    args = parser.parse_args()

    if args.num_trials < 1:
        raise ValueError("--trials must be 1 or greater.")

    if args.retries < 0:
        raise ValueError("--retries must be 0 or greater.")

    outdir = Path(args.outdir)
    (outdir / "trials").mkdir(parents=True, exist_ok=True)

    all_stats: list[dict[str, object]] = []

    for trial_id in range(args.num_trials):
        trial_dir = outdir / "trials" / f"trial-{trial_id:06d}"
        rows = run_one_trial(
            trial_id=trial_id,
            master_seed=args.seed,
            out_trial_dir=trial_dir,
            retries=args.retries,
            hitl_approved=args.hitl_approved,
        )
        all_stats.extend(rows)

    aggregate(outdir, args.num_trials)

    write_manifest(
        outdir,
        {
            "created_at": time.time(),
            "trials": args.num_trials,
            "retries": args.retries,
            "seed": args.seed,
            "target_script": str(resolve_target_script(TARGET_SCRIPT)),
            "hitl_approved": bool(args.hitl_approved or _env_hitl_approved()),
            "stats_rows": len(all_stats),
        },
    )

    write_checksums(outdir)


if __name__ == "__main__":
    main()
