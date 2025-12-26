# -*- coding: utf-8 -*-
"""
verify_stop_comparator_v1_2.py

A small reproducibility/packaging verifier for one or more Python files.

Usage (repo root):
    python tests/tools/verify_stop_comparator_v1_2.py path/to/stop_comparator_v1.py
    python tests/tools/verify_stop_comparator_v1_2.py path/to/stop_comparator_v1.py path/to/observed_bridge_exactmatch_v1_2.py

What it does (per target file):
  1) SHA256 (byte-level)
  2) py_compile (syntax check)
  3) import by file path and call _self_check() if present
  4) run as script (__main__) and capture stdout/stderr (optional; can be disabled)

Exit code:
  0: all checks passed for all targets
  non-zero: at least one target failed

Note:
  - This is NOT a pytest test file (name does not start with test_), so it won't clash with existing tests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import py_compile
import subprocess
import sys
import traceback
from typing import List


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_from_path(mod_name: str, path: str):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to build import spec for: {path}")
    mod = importlib.util.module_from_spec(spec)
    # register so imports inside the module (if any) can resolve it by name
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_one_target(path: str, *, run_as_script: bool = True) -> int:
    path = os.path.abspath(path)

    print("=" * 80)
    print(f"[TARGET] {path}")

    if not os.path.exists(path):
        print("[FAIL] file not found")
        return 2

    # 1) SHA256
    try:
        digest = sha256_file(path)
        print(f"[OK] sha256={digest}")
    except Exception:
        print("[FAIL] sha256")
        traceback.print_exc()
        return 3

    # 2) Syntax check
    try:
        py_compile.compile(path, doraise=True)
        print("[OK] py_compile")
    except Exception:
        print("[FAIL] py_compile")
        traceback.print_exc()
        return 4

    # 3) Import + _self_check (if exists)
    try:
        mod_name = f"_under_test_{os.path.basename(path).replace('.', '_')}"
        mod = import_from_path(mod_name, path)
        print("[OK] import")

        if hasattr(mod, "_self_check"):
            result = mod._self_check()  # type: ignore[attr-defined]
            print("[OK] _self_check result:")
            print(result)
        else:
            print("[INFO] _self_check not found (skip)")
    except Exception:
        print("[FAIL] import/_self_check")
        traceback.print_exc()
        return 5

    # 4) Run as script (__main__) (optional)
    if run_as_script:
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
            )
            print(f"[INFO] __main__ returncode={proc.returncode}")

            if proc.stdout.strip():
                print("[INFO] __main__ stdout:")
                print(proc.stdout.strip())

            if proc.stderr.strip():
                print("[WARN] __main__ stderr:")
                print(proc.stderr.strip())

            if proc.returncode != 0:
                print("[FAIL] __main__ non-zero return code")
                return proc.returncode  # keep target's exit code
            print("[OK] __main__")
        except Exception:
            print("[WARN] failed to run as script (optional check)")
            traceback.print_exc()
            # optional check: do not fail hard here
            return 0

    print("[PASS] target checks passed")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "paths",
        nargs="+",
        help="one or more python file paths to verify",
    )
    ap.add_argument(
        "--no-main",
        action="store_true",
        help="skip running as __main__ (import/_self_check only)",
    )
    args = ap.parse_args(argv)

    run_as_script = not args.no_main

    for p in args.paths:
        rc = run_one_target(p, run_as_script=run_as_script)
        if rc != 0:
            return rc

    print("[PASS] all targets passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
