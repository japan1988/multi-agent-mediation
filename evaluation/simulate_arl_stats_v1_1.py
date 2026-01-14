# -*- coding: utf-8 -*-
'''simulate_arl_stats.py

KAGE v1.7-IEP ARLログ 600件シミュレーション用スクリプト（拡張クリーン版 v1.1）

機能:
- JSONL(ARLログ) を読み込み
- Threat 別の SEALED/WARNING/ALLOW/OTHERS 統計を集計
- violation コードの頻度分布を集計
- Threat×Violation のクロス集計を出力
- 全体メタ指標（SEALED率/WARNING率/ALLOW率/OTHERS件数など）をJSONで出力
- タイムラインや円グラフ・積み上げ棒グラフをPNGで出力

想定JSONLフォーマット(1行ごとに1レコード):
    {
        "timestamp": "2025-01-01T12:34:56",
        "threat_id": "M1",
        "seal_status": "SEALED" | "WARNING" | "ALLOW" など,
        "mitig_steps": 3,
        "violations": ["ARL-001", "ARL-007"]
    }

使い方:
    python simulate_arl_stats.py --input data/arl_sim600.jsonl --outdir outputs
'''

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ==========================================================
# create_dummy_jsonl
# ==========================================================
def create_dummy_jsonl(path: Path, n: int = 600, seed: Optional[int] = None) -> None:
    '''
    指定パスにダミーARLログ(JSONL)を n件生成する。
    '''
    path.parent.mkdir(parents=True, exist_ok=True)

    rnd = random.Random(seed)

    threats = ["M1", "M2", "M3", "M4", "M5", "M6"]
    seal_status_choices = ["SEALED", "WARNING", "ALLOW"]
    violations_pool = [
        "ARL-001",
        "ARL-002",
        "ARL-003",
        "ARL-004",
        "ARL-005",
        "ARL-006",
        "ARL-007",
    ]

    base_time = datetime(2025, 1, 1, 0, 0, 0)

    with path.open("w", encoding="utf-8") as f:
        for i in range(n):
            ts = base_time + timedelta(minutes=i)
            threat_id = rnd.choice(threats)
            seal_status = rnd.choices(
                seal_status_choices, weights=[0.4, 0.3, 0.3], k=1
            )[0]
            mitig_steps = rnd.randint(0, 5)

            # violation は 0〜3個くらいランダムに付与
            v_count = rnd.randint(0, 3)
            v_list = rnd.sample(violations_pool, v_count) if v_count > 0 else []

            record = {
                "timestamp": ts.isoformat(timespec="seconds"),
                "threat_id": threat_id,
                "seal_status": seal_status,
                "mitig_steps": mitig_steps,
                "violations": v_list,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[INFO] Dummy JSONL generated: {path} (n={n}, seed={seed})")


# ==========================================================
# load_jsonl
# ==========================================================
def load_jsonl(path: Path) -> pd.DataFrame:
    '''
    JSONLファイルを1行ずつ読み込み、DataFrame に変換する。
    壊れた行はスキップし、警告ログを出す。
    '''
    records = []
    if not path.exists():
        raise FileNotFoundError(f"JSONL not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(obj)
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON decode error at line {lineno}: {e}")

    if not records:
        print("[WARN] No valid records loaded from JSONL.")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 型の補正
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    if "mitig_steps" in df.columns:
        df["mitig_steps"] = pd.to_numeric(df["mitig_steps"], errors="coerce").fillna(0)

    if "violations" in df.columns:
        def ensure_list(x):
            if isinstance(x, list):
                return x
            if pd.isna(x):
                return []
            return [x]

        df["violations"] = df["violations"].apply(ensure_list)
    else:
        df["violations"] = [[] for _ in range(len(df))]

    if "seal_status" not in df.columns:
        df["seal_status"] = "UNKNOWN"

    if "threat_id" not in df.columns:
        df["threat_id"] = "UNKNOWN"

    return df


# ==========================================================
# explode_list_column
# ==========================================================
def explode_list_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    '''
    リスト型のカラムを explode するヘルパー。
    '''
    if col not in df.columns:
        return pd.DataFrame(columns=df.columns)

    exploded = df.explode(col).reset_index(drop=True)
    return exploded


# ==========================================================
# summarize_threats（ALLOW/OTHERS 付き拡張版）
# ==========================================================
def summarize_threats(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Threatごとの SEALED/WARNING/ALLOW/OTHERS 件数や、
    mitig_steps の統計を集計する。
    '''
    if "threat_id" not in df.columns:
        raise ValueError("Column 'threat_id' not found in DataFrame.")

    if "seal_status" not in df.columns:
        df["seal_status"] = "UNKNOWN"

    if "mitig_steps" not in df.columns:
        df["mitig_steps"] = 0

    grp = df.groupby("threat_id")

    records = []
    for tid, g in grp:
        total = len(g)
        seal_count = g["seal_status"].value_counts().to_dict()

        sealed = seal_count.get("SEALED", 0)
        warning = seal_count.get("WARNING", 0)
        allow = seal_count.get("ALLOW", 0)
        others = total - sealed - warning - allow

        mitig_arr = g["mitig_steps"].to_numpy()
        if len(mitig_arr) == 0:
            avg_mitig = 0.0
            median_mitig = 0.0
            mode_mitig = 0
        else:
            avg_mitig = float(mitig_arr.mean())
            median_mitig = float(np.median(mitig_arr))
            mode_mitig = int(pd.Series(mitig_arr).mode()[0])

        records.append(
            {
                "Threat": tid,
                "Total": total,
                "SEALED": sealed,
                "WARNING": warning,
                "ALLOW": allow,
                "OTHERS": others,
                "SEALED_rate": sealed / total * 100.0 if total else 0.0,
                "WARNING_rate": warning / total * 100.0 if total else 0.0,
                "ALLOW_rate": allow / total * 100.0 if total else 0.0,
                "avg_mitig": avg_mitig,
                "median_mitig": median_mitig,
                "mode_mitig": mode_mitig,
            }
        )

    return pd.DataFrame(records).sort_values("Threat")


# ==========================================================
# summarize_violations
# ==========================================================
def summarize_violations(df: pd.DataFrame) -> pd.DataFrame:
    '''
    violation コードの出現頻度を集計する（全 violation 発生数に対する割合）。
    '''
    if "violations" not in df.columns:
        return pd.DataFrame(columns=["Violation", "Count", "Ratio"])

    exploded = explode_list_column(df, "violations")
    if exploded.empty:
        return pd.DataFrame(columns=["Violation", "Count", "Ratio"])

    exploded = exploded.dropna(subset=["violations"])

    total = len(exploded)
    if total == 0:
        return pd.DataFrame(columns=["Violation", "Count", "Ratio"])

    vc = exploded["violations"].value_counts().reset_index()
    vc.columns = ["Violation", "Count"]
    vc["Ratio"] = vc["Count"] / total * 100.0
    return vc.sort_values("Count", ascending=False)


# ==========================================================
# summarize_violation_by_threat（Threat×Violationクロス集計）
# ==========================================================
def summarize_violation_by_threat(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Threat × Violation のクロス集計（赤旗候補確認用）。
    '''
    if "violations" not in df.columns or "threat_id" not in df.columns:
        return pd.DataFrame(columns=["Threat", "Violation", "Count"])

    exploded = explode_list_column(df, "violations")
    if exploded.empty:
        return pd.DataFrame(columns=["Threat", "Violation", "Count"])

    exploded = exploded.dropna(subset=["violations"])

    grp = exploded.groupby(["threat_id", "violations"]).size().reset_index(name="Count")
    grp.rename(columns={"threat_id": "Threat", "violations": "Violation"}, inplace=True)
    return grp.sort_values(["Count", "Threat"], ascending=[False, True])


# ==========================================================
# summarize_overall（全体メタ指標）
# ==========================================================
def summarize_overall(df: pd.DataFrame) -> Dict[str, Any]:
    '''
    全体メタ指標（SEALED率/WARNING率/ALLOW率/OTHERS件数など）を返す。
    '''
    total = len(df)
    status_counts = (
        df["seal_status"].value_counts().to_dict()
        if "seal_status" in df.columns
        else {}
    )

    sealed = int(status_counts.get("SEALED", 0))
    warning = int(status_counts.get("WARNING", 0))
    allow = int(status_counts.get("ALLOW", 0))
    others = int(total - sealed - warning - allow)

    def rate(key: str) -> float:
        return status_counts.get(key, 0) / total * 100.0 if total else 0.0

    return {
        "total_records": int(total),
        "sealed_count": sealed,
        "warning_count": warning,
        "allow_count": allow,
        "others_count": others,
        "sealed_rate": rate("SEALED"),
        "warning_rate": rate("WARNING"),
        "allow_rate": rate("ALLOW"),
    }


# ==========================================================
# plot_threat_pie
# ==========================================================
def plot_threat_pie(df_threat: pd.DataFrame, outdir: Path, prefix: str = "") -> None:
    '''
    Threat別の SEALED 件数の比率を円グラフで保存する。
    '''
    if df_threat.empty or df_threat["SEALED"].sum() == 0:
        print("[WARN] No SEALED data to plot pie chart.")
        return

    plt.figure(figsize=(6, 6))
    plt.pie(df_threat["SEALED"], labels=df_threat["Threat"], autopct="%1.1f%%")
    plt.title("SEALED Ratio by Threat")

    fname = f"{prefix}threat_sealed_pie.png" if prefix else "threat_sealed_pie.png"
    outdir.mkdir(parents=True, exist_ok=True)
    plt.savefig(outdir / fname, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Saved pie chart: {outdir / fname}")


# ==========================================================
# plot_seal_stacked_bar
# ==========================================================
def plot_seal_stacked_bar(df_threat: pd.DataFrame, outdir: Path, prefix: str = "") -> None:
    '''
    Threat別の SEALED/WARNING/ALLOW の積み上げ棒グラフを保存する。
    '''
    if df_threat.empty:
        print("[WARN] Empty threat summary; skip stacked bar.")
        return

    x = np.arange(len(df_threat["Threat"]))
    width = 0.6

    sealed = df_threat["SEALED"]
    warning = df_threat["WARNING"]
    allow = df_threat["ALLOW"] if "ALLOW" in df_threat.columns else np.zeros_like(sealed)

    plt.figure(figsize=(8, 5))
    plt.bar(x, sealed, width, label="SEALED")
    plt.bar(x, warning, width, bottom=sealed, label="WARNING")
    plt.bar(x, allow, width, bottom=sealed + warning, label="ALLOW")

    plt.xticks(x, df_threat["Threat"])
    plt.legend()
    plt.title("SEALED/WARNING/ALLOW Distribution by Threat")

    fname = (
        f"{prefix}threat_sealed_warning_allow_bar.png"
        if prefix
        else "threat_sealed_warning_allow_bar.png"
    )
    outdir.mkdir(parents=True, exist_ok=True)
    plt.savefig(outdir / fname, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Saved stacked bar chart: {outdir / fname}")


# ==========================================================
# plot_timeline
# ==========================================================
def plot_timeline(df: pd.DataFrame, outdir: Path, prefix: str = "") -> None:
    '''
    timestamp 列を用いて、時間経過に対する SEALED/WARNING/ALLOW 件数の推移を描画する。
    日単位で集計。
    '''
    if "timestamp" not in df.columns:
        print("[WARN] No 'timestamp' in df; skip timeline.")
        return

    if df["timestamp"].isna().all():
        print("[WARN] All timestamps are NaT; skip timeline.")
        return

    df_day = df.copy()
    df_day["day"] = df_day["timestamp"].dt.floor("D")

    sealed_per_day = (
        df_day[df_day["seal_status"] == "SEALED"].groupby("day").size().rename("SEALED")
    )
    warning_per_day = (
        df_day[df_day["seal_status"] == "WARNING"].groupby("day").size().rename("WARNING")
    )
    allow_per_day = (
        df_day[df_day["seal_status"] == "ALLOW"].groupby("day").size().rename("ALLOW")
    )

    timeline = pd.concat(
        [sealed_per_day, warning_per_day, allow_per_day], axis=1
    ).fillna(0)

    if timeline.empty:
        print("[WARN] Empty timeline after grouping; skip timeline plot.")
        return

    plt.figure(figsize=(10, 4))
    plt.plot(timeline.index, timeline["SEALED"], marker="o", label="SEALED")
    plt.plot(timeline.index, timeline["WARNING"], marker="x", label="WARNING")
    plt.plot(timeline.index, timeline["ALLOW"], marker="s", label="ALLOW")
    plt.title("SEALED/WARNING/ALLOW Counts Over Time")
    plt.xlabel("Day")
    plt.ylabel("Count")
    plt.legend()

    fname = (
        f"{prefix}sealed_warning_allow_timeline.png"
        if prefix
        else "sealed_warning_allow_timeline.png"
    )
    outdir.mkdir(parents=True, exist_ok=True)
    plt.savefig(outdir / fname, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Saved timeline chart: {outdir / fname}")


# ==========================================================
# analyze_logs
# ==========================================================
def analyze_logs(df: pd.DataFrame, outdir: Path, prefix: str = "") -> None:
    '''
    ログDataFrameから Threat集計 / violation集計 / クロス集計 /
    メタ指標 / 各種プロット を実行する。
    '''
    outdir.mkdir(parents=True, exist_ok=True)

    # 全体メタ指標
    overall = summarize_overall(df)
    overall_name = f"{prefix}overall_summary.json" if prefix else "overall_summary.json"
    with (outdir / overall_name).open("w", encoding="utf-8") as f:
        json.dump(overall, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved overall summary JSON: {outdir / overall_name}")

    # Threat集計
    df_threat = summarize_threats(df)
    if not df_threat.empty:
        csv_name = f"{prefix}threat_summary.csv" if prefix else "threat_summary.csv"
        df_threat.to_csv(outdir / csv_name, index=False)
        print(f"[INFO] Saved threat summary CSV: {outdir / csv_name}")
    else:
        print("[WARN] Threat summary is empty; CSV not saved.")

    # violation集計
    df_violation = summarize_violations(df)
    if not df_violation.empty:
        csv_name = (
            f"{prefix}violation_summary.csv" if prefix else "violation_summary.csv"
        )
        df_violation.to_csv(outdir / csv_name, index=False)
        print(f"[INFO] Saved violation summary CSV: {outdir / csv_name}")
    else:
        print("[WARN] Violation summary is empty; CSV not saved.")

    # Threat × Violation クロス集計
    df_v_by_t = summarize_violation_by_threat(df)
    if not df_v_by_t.empty:
        csv_name = (
            f"{prefix}violation_by_threat.csv"
            if prefix
            else "violation_by_threat.csv"
        )
        df_v_by_t.to_csv(outdir / csv_name, index=False)
        print(f"[INFO] Saved violation-by-threat CSV: {outdir / csv_name}")
    else:
        print("[WARN] Violation-by-threat summary is empty; CSV not saved.")

    # プロット群
    plot_threat_pie(df_threat, outdir, prefix=prefix)
    plot_seal_stacked_bar(df_threat, outdir, prefix=prefix)
    plot_timeline(df, outdir, prefix=prefix)


# ==========================================================
# main
# ==========================================================
def main(argv: Optional[Tuple[str, ...]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="KAGE v1.7-IEP ARLログ 600件シミュレーション用スクリプト（拡張クリーン版 v1.1）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="入力JSONLファイルパス（例: data/arl_sim600.jsonl）",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="outputs",
        help="結果の出力ディレクトリ",
    )
    parser.add_argument(
        "--generate-dummy",
        action="store_true",
        help="ダミーJSONL (arl_sim600.jsonl) を生成してから解析する",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=600,
        help="ダミー生成時の件数（--generate-dummy使用時）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="ダミー生成時の乱数シード（--generate-dummy使用時）",
    )

    if argv is None:
        argv = tuple(sys.argv[1:])

    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.input:
        input_path = Path(args.input)
    else:
        input_path = Path("data/arl_sim600.jsonl")

    if args.generate_dummy:
        create_dummy_jsonl(input_path, n=args.n, seed=args.seed)

    df = load_jsonl(input_path)
    if df.empty:
        print("[WARN] No data loaded. Abort analysis.")
        return

    analyze_logs(df, outdir)


if __name__ == "__main__":
    main()
