# -*- coding: utf-8 -*-
"""
sim_batch.py (fixed)
Batch runner for raw vs filtered modes.
- Runs N trials (sequential by default; optional processes via --proc).
- Copies the produced CSV logs into out/<run>/trials/trial-XXXXXX/{raw,filtered}.csv
- Aggregates stats and first-stop metrics into out/<run>/aggregate/*.csv
- Draws simple charts with matplotlib (no seaborn, one figure per chart, default colors)
"""

import os, sys, time, json, csv, glob, hashlib, argparse, subprocess
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUT_DIR_DEFAULT = BASE_DIR / "out"
MODES = [
    ("raw",      str(BASE_DIR / "configs" / "ai_config_raw.json")),
    ("filtered", str(BASE_DIR / "configs" / "ai_config_filtered.json")),
]
STOP_EVENTS = {"mediator_stop","filter_block","defeat_layer_stop","inactive"}

def newest_file(dirpath: Path) -> Path | None:
    files = sorted(Path(dirpath).glob("*.csv"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None

def derive_seed(master_seed: int, trial_id: int, mode_id: int) -> int:
    return (master_seed * 1315423911 + trial_id * 2654435761 + mode_id * 97531) & 0xFFFFFFFF

def compute_first_stop_step(csv_path: Path) -> int:
    if not csv_path.exists():
        return -1
    try:
        df = pd.read_csv(csv_path)
        if "event" not in df.columns or "step" not in df.columns:
            return -1
        mask = df["event"].isin(STOP_EVENTS)
        idx = mask.idxmax() if mask.any() else None
        return int(df.loc[idx, "step"]) if idx is not None else -1
    except Exception:
        return -1

def run_one_trial(trial_id: int, master_seed: int, out_trial: Path, retries: int = 2) -> list[dict]:
    out_trial.mkdir(parents=True, exist_ok=True)
    stats_rows: list[dict] = []
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
                # optional: max step from env
                if "STEP_MAX" in os.environ:
                    env["AI_STEP_MAX"] = os.environ["STEP_MAX"]
                subprocess.run(["python", "main.py"], cwd=str(BASE_DIR), env=env, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                after = set(glob.glob(str(LOGS_DIR / "*.csv")))
                new_files = list(after - before)
                src_csv = Path(new_files[0]) if new_files else newest_file(LOGS_DIR)
                if not src_csv or not src_csv.exists():
                    raise RuntimeError("No CSV log found after running main.py")
                dst_csv = out_trial / f"{mode_key}.csv"
                df = pd.read_csv(src_csv)
                # enrich
                df["trial_id"] = trial_id
                df["mode"] = mode_key
                df["seed"] = seed
                if "event" in df.columns:
                    df["seal_flag"] = df["event"].isin(STOP_EVENTS).astype(int)
                    stop_set = STOP_EVENTS
                    df["halt_reason"] = df["event"].where(df["event"].isin(stop_set), "")
                else:
                    df["seal_flag"] = 0
                    df["halt_reason"] = ""
                # normalize cols if missing
                for col in ["timestamp","step","emotion","event"]:
                    if col not in df.columns:
                        df[col] = "" if col in {"event"} else 0
                df.to_csv(dst_csv, index=False, encoding="utf-8")

                steps = int(df["step"].max()) if "step" in df.columns else 0
                interventions = int((df["event"]=="mediator_stop").sum()) if "event" in df.columns else 0
                sealed = int(df["event"].isin(STOP_EVENTS).any()) if "event" in df.columns else 0
                stats_rows.append({"trial_id": trial_id, "mode": mode_key,
                                   "steps": steps, "interventions": interventions, "sealed": sealed})
                break
            except Exception as e:
                tries += 1
                if tries > retries:
                    # write a minimal CSV so pipeline continues
                    dst_csv = out_trial / f"{mode_key}.csv"
                    with open(dst_csv, "w", encoding="utf-8", newline="") as f:
                        w = csv.writer(f)
                        w.writerow(["trial_id","mode","step","emotion","event","timestamp","seed","seal_flag","halt_reason"])
                        w.writerow([trial_id, mode_key, 0, 0, f"error:{e}", time.time(), seed, 0, "error"])
                    stats_rows.append({"trial_id": trial_id, "mode": mode_key,
                                       "steps": 0, "interventions": 0, "sealed": 0})
                    break
                time.sleep(0.3 * (2**(tries-1)))
    return stats_rows

def aggregate(outdir: Path, N: int):
    trials_dir = outdir / "trials"
    agg_dir = outdir / "aggregate"
    agg_dir.mkdir(parents=True, exist_ok=True)

    # stats
    stats: list[dict] = []
    for t in range(N):
        for mode in ["raw","filtered"]:
            p = trials_dir / f"trial-{t:06d}" / f"{mode}.csv"
            if not p.exists():
                continue
            try:
                df = pd.read_csv(p)
            except Exception:
                continue
            steps = int(df["step"].max()) if "step" in df.columns else 0
            interventions = int((df["event"]=="mediator_stop").sum()) if "event" in df.columns else 0
            sealed = int(df["event"].isin(STOP_EVENTS).any()) if "event" in df.columns else 0
            stats.append({"trial_id": t, "mode": mode, "steps": steps, "interventions": interventions, "sealed": sealed})
    stats_df = pd.DataFrame(stats)
    stats_df.to_csv(agg_dir / "stats.csv", index=False, encoding="utf-8")

    # first stop
    first_rows = []
    for t in range(N):
        for mode in ["raw","filtered"]:
            p = trials_dir / f"trial-{t:06d}" / f"{mode}.csv"
            first_rows.append({"trial_id": t, "mode": mode, "first_stop_step": compute_first_stop_step(p)})
    first_df = pd.DataFrame(first_rows)
    first_df.to_csv(agg_dir / "first_stop.csv", index=False, encoding="utf-8")

    # charts
    try:
        plt.figure(figsize=(6,4))
        if not stats_df.empty:
            pivot = stats_df.pivot_table(index="mode", values="sealed", aggfunc="mean").reset_index()
            plt.bar(pivot["mode"], pivot["sealed"])
            plt.title("Sealed ratio by mode")
            plt.xlabel("Mode"); plt.ylabel("Ratio")
            plt.grid(True, axis="y")
            plt.savefig(agg_dir / "sealed_ratio.png", bbox_inches="tight")
            plt.close()
    except Exception:
        pass

    try:
        plt.figure(figsize=(6,4))
        for mode in ["raw","filtered"]:
            d = first_df[(first_df["mode"]==mode) & (first_df["first_stop_step"]>=0)]["first_stop_step"].to_numpy()
            if d.size > 0:
                plt.hist(d, bins=50, alpha=0.5, label=mode)
        plt.title("First stop step histogram")
        plt.xlabel("Step"); plt.ylabel("Count")
        plt.legend(); plt.grid(True)
        plt.savefig(agg_dir / "hist_first_stop.png", bbox_inches="tight")
        plt.close()
    except Exception:
        pass

def write_manifest(outdir: Path, meta: dict):
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def write_checksums(root: Path):
    manifest = {}
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            manifest[rel] = sha256_file(p)
    (root / "checksums.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default=str(OUT_DIR_DEFAULT / time.strftime("run-%Y%m%d-%H%M%S")))
    ap.add_argument("--trials", "-n", dest="N", type=int, default=10)
    ap.add_argument("--retries", "-r", dest="R", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    (outdir / "trials").mkdir(parents=True, exist_ok=True)

    all_stats = []
    for t in range(args.N):
        stats_rows = run_one_trial(t, args.seed, outdir / "trials" / f"trial-{t:06d}", retries=args.R)
        all_stats.extend(stats_rows)

    aggregate(outdir, args.N)
    write_manifest(outdir, {"created_at": time.time(), "trials": args.N, "retries": args.R, "seed": args.seed})
    write_checksums(outdir)

if __name__ == "__main__":
    main()
