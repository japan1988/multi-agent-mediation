
```python
#!/usr/bin/env python3
# Emergency contract mediation simulator (v5.1.2 compatible CLI scaffold)
# Stdlib-only implementation per SPEC_PACK.

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import random
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple


# ---------- Utilities ----------

def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def stable_sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- Key management (demo/file/env) ----------

def load_key(mode: str, key_file: Optional[str], key_env: Optional[str]) -> bytes:
    mode = (mode or "").strip().lower()
    if mode == "demo":
        # Demo-only tamper detection key (NOT secret in real operations)
        return b"DEMO_KEY_NOT_FOR_PROD__v5_1_2"
    if mode == "file":
        if not key_file:
            raise ValueError("key-mode=file requires --key-file")
        p = Path(key_file)
        # Spec: missing key-file => FileNotFoundError
        data = p.read_bytes()
        if not data:
            raise ValueError("key-file is empty")
        return data
    if mode == "env":
        if not key_env:
            raise ValueError("key-mode=env requires --key-env")
        v = os.environ[key_env]  # KeyError if missing is acceptable as "鍵未取得"
        b = v.encode("utf-8")
        if not b:
            raise ValueError("key-env is empty")
        return b
    raise ValueError(f"unknown key-mode: {mode!r}")


def hmac_hex(key: bytes, payload: Dict[str, Any]) -> str:
    # ensure stable canonicalization
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


# ---------- HITL Queue ----------

@dataclass
class HitlQueueItem:
    incident_id: int
    run_id: int
    ts: str
    reason_code: str
    final_state: str
    sealed: bool
    arl_path: Optional[str] = None


@dataclass
class HitlQueue:
    max_items: int
    items: Deque[HitlQueueItem]

    def push(self, item: HitlQueueItem) -> None:
        self.items.append(item)
        while len(self.items) > self.max_items:
            self.items.popleft()

    @property
    def size(self) -> int:
        return len(self.items)

    def to_json(self) -> Dict[str, Any]:
        return {
            "max_items": self.max_items,
            "size": self.size,
            "items": [asdict(x) for x in list(self.items)],
        }


# ---------- Persistent stores ----------

TRUST_STORE_PATH = Path("model_trust_store.json")
GRANTS_PATH = Path("model_grants.json")
EVAL_STATE_PATH = Path("eval_state.json")

INCIDENT_COUNTER_PATH = Path("incident_counter.txt")
INCIDENT_INDEX_PATH = Path("incident_index.jsonl")


def reset_stores(no_reset: bool, no_reset_eval: bool) -> None:
    if no_reset:
        return
    for p in [TRUST_STORE_PATH, GRANTS_PATH]:
        if p.exists():
            p.unlink()
    if not no_reset_eval and EVAL_STATE_PATH.exists():
        EVAL_STATE_PATH.unlink()
    # Keep experiments reproducible: reset incident tracking too.
    for p in [INCIDENT_COUNTER_PATH, INCIDENT_INDEX_PATH]:
        if p.exists():
            p.unlink()


def load_or_init_trust_store() -> Dict[str, Any]:
    if TRUST_STORE_PATH.exists():
        return read_json(TRUST_STORE_PATH)
    return {
        "version": "v5.1.2",
        "updated_at": iso_utc_now(),
        "models": {},  # model_id -> {"trust": float, "seen": int, "last_ts": str}
    }


def load_or_init_grants() -> Dict[str, Any]:
    if GRANTS_PATH.exists():
        return read_json(GRANTS_PATH)
    return {
        "version": "v5.1.2",
        "updated_at": iso_utc_now(),
        "reason_code_counts": {},  # reason_code -> count
    }


def load_or_init_eval_state() -> Dict[str, Any]:
    if EVAL_STATE_PATH.exists():
        return read_json(EVAL_STATE_PATH)
    return {
        "version": "v5.1.2",
        "updated_at": iso_utc_now(),
        "total_runs": 0,
        "by_state": {},
        "last_run_ts": None,
    }


def persist_stores(trust: Dict[str, Any], grants: Dict[str, Any], eval_state: Dict[str, Any]) -> None:
    trust["updated_at"] = iso_utc_now()
    grants["updated_at"] = iso_utc_now()
    eval_state["updated_at"] = iso_utc_now()
    write_json(TRUST_STORE_PATH, trust)
    write_json(GRANTS_PATH, grants)
    write_json(EVAL_STATE_PATH, eval_state)


# ---------- Incident ID ----------

def next_incident_id() -> int:
    # Spec: simple increment counter.txt; concurrency may conflict (R).
    if INCIDENT_COUNTER_PATH.exists():
        raw = read_text(INCIDENT_COUNTER_PATH).strip()
        n = int(raw) if raw else 0
    else:
        n = 0
    n += 1
    write_text(INCIDENT_COUNTER_PATH, f"{n}\n")
    return n


# ---------- ARL saving ----------

def list_arl_files(out_dir: Path) -> List[Path]:
    if not out_dir.exists():
        return []
    return [p for p in out_dir.glob("*.arl.jsonl") if p.is_file()]


def maybe_save_arl(
    *,
    enabled: bool,
    out_dir: Optional[str],
    max_files: int,
    incident_id: int,
    run_id: int,
    arl_events: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str], str]:
    """
    Returns: (saved, arl_path_str, status_msg)
    """
    if not enabled:
        return (False, None, "disabled")
    if not out_dir:
        raise ValueError("--save-arl-on-abnormal requires --arl-out-dir")
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    existing = list_arl_files(d)
    if max_files >= 0 and len(existing) >= max_files:
        return (False, None, f"skipped(cap={max_files})")
    path = d / f"{incident_id}__{run_id}.arl.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for ev in arl_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return (True, str(path), "saved")


# ---------- Simulation core ----------

def is_abnormal_run(*, fabricate_rate: float, rng: random.Random) -> bool:
    return rng.random() < fabricate_rate


def pick_reason_code(rng: random.Random) -> str:
    pool = ["POLICY_VIOLATION", "RISK_HIGH", "MISSING_CONSENT", "CONFLICTING_TERMS"]
    return pool[rng.randrange(0, len(pool))]


def run_simulation(
    *,
    runs: int,
    fabricate_rate: float,
    seed: Optional[int],
    no_reset: bool,
    no_reset_eval: bool,
    save_arl_on_abnormal: bool,
    arl_out_dir: Optional[str],
    max_arl_files: int,
    full_context_n: int,
    key_mode: str,
    key_file: Optional[str],
    key_env: Optional[str],
    keep_runs: bool,
    queue_max_items: int,
    sample_runs: int,
    no_incident_index: bool,
) -> Dict[str, Any]:
    if runs < 0:
        raise ValueError("--runs must be >= 0")
    if not (0.0 <= fabricate_rate <= 1.0):
        raise ValueError("--fabricate-rate must be within [0,1]")
    if queue_max_items < 0:
        raise ValueError("--queue-max-items must be >= 0")
    if sample_runs < 0:
        raise ValueError("--sample-runs must be >= 0")
    if full_context_n < 0:
        raise ValueError("--full-context-n must be >= 0")
    if max_arl_files < -1:
        raise ValueError("--max-arl-files must be >= -1 (use -1 for unlimited)")

    reset_stores(no_reset=no_reset, no_reset_eval=no_reset_eval)

    key = load_key(key_mode, key_file, key_env)
    rng = random.Random(seed)

    trust = load_or_init_trust_store()
    grants = load_or_init_grants()
    eval_state = load_or_init_eval_state()

    hitl_queue = HitlQueue(max_items=queue_max_items, items=deque())

    by_state: Dict[str, int] = {}
    top_reason_counts: Dict[str, int] = {}
    abnormal_saved = 0
    abnormal_skipped = 0

    # recent context (bounded)
    recent_context: List[Dict[str, Any]] = []

    # output runs: only if keep_runs
    runs_list: List[Dict[str, Any]] = []
    samples: List[Dict[str, Any]] = []

    model_id = "mediation-sim"  # local-only identifier

    for run_id in range(1, runs + 1):
        ts = iso_utc_now()
        abnormal = is_abnormal_run(fabricate_rate=fabricate_rate, rng=rng)
        final_state = "STOPPED" if abnormal else "COMPLETED"
        sealed = True if abnormal else False  # per T: STOPPED/ sealed=True must occur
        reason_code = pick_reason_code(rng) if abnormal else "OK"

        by_state[final_state] = by_state.get(final_state, 0) + 1
        if abnormal:
            top_reason_counts[reason_code] = top_reason_counts.get(reason_code, 0) + 1

        run_context = {
            "run_id": run_id,
            "ts": ts,
            "final_state": final_state,
            "sealed": sealed,
            "reason_code": reason_code,
        }
        if full_context_n > 0:
            recent_context.append(run_context)
            if len(recent_context) > full_context_n:
                recent_context = recent_context[-full_context_n:]

        # Update persistent stores
        m = trust["models"].get(model_id, {"trust": 0.5, "seen": 0, "last_ts": None})
        m["seen"] = int(m.get("seen", 0)) + 1
        cur_trust = float(m.get("trust", 0.5))
        if abnormal:
            cur_trust = max(0.0, cur_trust - 0.02)
        else:
            cur_trust = min(1.0, cur_trust + 0.005)
        m["trust"] = cur_trust
        m["last_ts"] = ts
        trust["models"][model_id] = m

        if abnormal:
            grants["reason_code_counts"][reason_code] = int(grants["reason_code_counts"].get(reason_code, 0)) + 1

        eval_state["total_runs"] = int(eval_state.get("total_runs", 0)) + 1
        eval_state["by_state"][final_state] = int(eval_state["by_state"].get(final_state, 0)) + 1
        eval_state["last_run_ts"] = ts

        arl_path: Optional[str] = None
        arl_status = "n/a"
        incident_id: Optional[int] = None

        if abnormal:
            incident_id = next_incident_id()

            arl_events: List[Dict[str, Any]] = []
            base_event: Dict[str, Any] = {
                "type": "incident",
                "incident_id": incident_id,
                "run_id": run_id,
                "ts": ts,
                "final_state": final_state,
                "sealed": sealed,
                "reason_code": reason_code,
                "context": (recent_context[-full_context_n:] if full_context_n > 0 else []),
            }
            base_event["integrity_hmac_sha256"] = hmac_hex(key, base_event)
            arl_events.append(base_event)

            saved, arl_path, arl_status = maybe_save_arl(
                enabled=save_arl_on_abnormal,
                out_dir=arl_out_dir,
                max_files=max_arl_files,
                incident_id=incident_id,
                run_id=run_id,
                arl_events=arl_events,
            )
            if saved:
                abnormal_saved += 1
            else:
                abnormal_skipped += 1

            idx = {
                "incident_id": incident_id,
                "run_id": run_id,
                "ts": ts,
                "final_state": final_state,
                "sealed": sealed,
                "reason_code": reason_code,
                "arl_path": arl_path,
                "run_summary_sha256": stable_sha256(
                    json.dumps(run_context, ensure_ascii=False, sort_keys=True)
                ),
            }
            if not no_incident_index:
                append_jsonl(INCIDENT_INDEX_PATH, idx)

            hitl_queue.push(
                HitlQueueItem(
                    incident_id=incident_id,
                    run_id=run_id,
                    ts=ts,
                    reason_code=reason_code,
                    final_state=final_state,
                    sealed=sealed,
                    arl_path=arl_path,
                )
            )

        run_record = {
            "run_id": run_id,
            "ts": ts,
            "final_state": final_state,
            "sealed": sealed,
            "reason_code": reason_code,
            "incident_id": incident_id,
            "arl_status": arl_status,
            "arl_path": arl_path,
        }
        if keep_runs:
            runs_list.append(run_record)
        else:
            if sample_runs > 0 and len(samples) < sample_runs:
                samples.append(run_record)

    persist_stores(trust, grants, eval_state)

    top_reason_code = None
    if top_reason_counts:
        top_reason_code = sorted(top_reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    results = {
        "version": "v5.1.2",
        "ts": iso_utc_now(),
        "params": {
            "runs": runs,
            "fabricate_rate": fabricate_rate,
            "seed": seed,
            "no_reset": no_reset,
            "no_reset_eval": no_reset_eval,
            "save_arl_on_abnormal": save_arl_on_abnormal,
            "arl_out_dir": arl_out_dir,
            "max_arl_files": max_arl_files,
            "full_context_n": full_context_n,
            "key_mode": key_mode,
            "keep_runs": keep_runs,
            "queue_max_items": queue_max_items,
            "sample_runs": sample_runs,
            "no_incident_index": no_incident_index,
        },
        "summary": {
            "runs": runs,
            "by_state": {
                "total_runs": runs,
                "counts": dict(sorted(by_state.items())),
            },
            "top_reason_code": top_reason_code,
            "abnormal_arl": {
                "saved": abnormal_saved,
                "skipped": abnormal_skipped,
                "enabled": save_arl_on_abnormal,
                "out_dir": arl_out_dir,
                "cap": max_arl_files,
            },
            "queue_size": hitl_queue.size,
        },
        "hitl_queue": hitl_queue.to_json(),
        "stores": {
            "trust_store_path": str(TRUST_STORE_PATH),
            "grants_path": str(GRANTS_PATH),
            "eval_state_path": str(EVAL_STATE_PATH),
        },
        "runs": runs_list if keep_runs else [],
        "samples": samples if (not keep_runs and sample_runs > 0) else [],
    }
    return results


# ---------- Outputs ----------

def write_queue_csv(path: Path, queue: Dict[str, Any]) -> None:
    items = queue.get("items", [])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # Header row required by T
        w.writerow(["incident_id", "run_id", "ts", "reason_code", "final_state", "sealed", "arl_path"])
        for it in items:
            w.writerow([
                it.get("incident_id"),
                it.get("run_id"),
                it.get("ts"),
                it.get("reason_code"),
                it.get("final_state"),
                it.get("sealed"),
                it.get("arl_path"),
            ])


def print_summary(results: Dict[str, Any]) -> None:
    s = results["summary"]
    by_state = s["by_state"]
    abnormal = s["abnormal_arl"]
    print(f"runs={s['runs']}")
    print(f"by_state.total_runs={by_state['total_runs']}")
    print(f"by_state.counts={json.dumps(by_state['counts'], ensure_ascii=False)}")
    print(f"top_reason_code={s['top_reason_code']}")
    print(
        "abnormal_arl="
        + json.dumps(
            {
                "enabled": abnormal["enabled"],
                "saved": abnormal["saved"],
                "skipped": abnormal["skipped"],
                "out_dir": abnormal["out_dir"],
                "cap": abnormal["cap"],
            },
            ensure_ascii=False,
        )
    )
    print(f"queue_size={s['queue_size']}")


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sim.py", description="Emergency contract mediation simulator(v5.1.2) CLI")
    p.add_argument("--runs", type=int, required=True)
    p.add_argument("--fabricate", action="store_true", help="Enable abnormal fabrication (optional; rate>0 implies on).")
    p.add_argument("--fabricate-rate", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--no-reset", action="store_true")
    p.add_argument("--no-reset-eval", action="store_true")
    p.add_argument("--save-arl-on-abnormal", action="store_true")
    p.add_argument("--arl-out-dir", type=str, default=None)
    p.add_argument("--max-arl-files", type=int, default=1000)
    p.add_argument("--full-context-n", type=int, default=0)
    p.add_argument("--key-mode", type=str, choices=["demo", "file", "env"], default="demo")
    p.add_argument("--key-file", type=str, default=None)
    p.add_argument("--key-env", type=str, default=None)
    p.add_argument("--keep-runs", action="store_true")
    p.add_argument("--queue-max-items", type=int, default=200)
    p.add_argument("--sample-runs", type=int, default=0)
    p.add_argument("--results-json", type=str, default=None)
    p.add_argument("--queue-json", type=str, default=None)
    p.add_argument("--queue-csv", type=str, default=None)
    p.add_argument("--no-incident-index", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Behavior: if --fabricate not provided but fabricate-rate>0, fabricate is effectively enabled.
    effective_fabricate_rate = args.fabricate_rate if (args.fabricate or args.fabricate_rate > 0) else 0.0

    results = run_simulation(
        runs=args.runs,
        fabricate_rate=effective_fabricate_rate,
        seed=args.seed,
        no_reset=args.no_reset,
        no_reset_eval=args.no_reset_eval,
        save_arl_on_abnormal=args.save_arl_on_abnormal,
        arl_out_dir=args.arl_out_dir,
        max_arl_files=args.max_arl_files,
        full_context_n=args.full_context_n,
        key_mode=args.key_mode,
        key_file=args.key_file,
        key_env=args.key_env,
        keep_runs=args.keep_runs,
        queue_max_items=args.queue_max_items,
        sample_runs=args.sample_runs,
        no_incident_index=args.no_incident_index,
    )

    # stdout summary
    print_summary(results)

    # Optional file outputs
    if args.results_json:
        write_json(Path(args.results_json), results)
    if args.queue_json:
        write_json(Path(args.queue_json), results["hitl_queue"])
    if args.queue_csv:
        write_queue_csv(Path(args.queue_csv), results["hitl_queue"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

VERIFY:

1. `python sim.py --runs 3 --fabricate-rate 0 --seed 42`
2. `python sim.py --runs 10 --fabricate-rate 1.0 --seed 42 --save-arl-on-abnormal --arl-out-dir out`
3. `python sim.py --runs 5 --fabricate-rate 1.0 --seed 1 --save-arl-on-abnormal --arl-out-dir out --results-json out/results.json --queue-json out/queue.json --queue-csv out/queue.csv`
4. `python sim.py --runs 1 --key-mode file --key-file DOES_NOT_EXIST.key`
5. `python sim.py --runs 5 --fabricate-rate 1.0 --seed 1 --no-incident-index`

NOTES:

* `--no-reset` 未指定時は `reset_stores()` が incident counter/index も削除（実験再現性優先の固定仕様）

QUESTIONS:
NONE
