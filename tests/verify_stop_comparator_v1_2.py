# -*- coding: utf-8 -*-
"""
verify_stop_comparator_v1_2.py

A small reproducibility/packaging verifier for one or more Python files.

Usage (repo root):
    python tests/tools/verify_stop_comparator_v1_2.py path/to/stop_comparator_v1.py --hitl-approved
    python tests/tools/verify_stop_comparator_v1_2.py path/to/stop_comparator_v1.py path/to/observed_bridge_exactmatch_v1_2.py --hitl-approved

What it does (per target file):
  1) SHA256 (byte-level)
  2) py_compile (syntax check)
  3) import by file path and call _self_check() if present
  4) run as script (__main__) and capture stdout/stderr
     - can be disabled with --no-main
     - requires explicit HITL approval when enabled

Exit code:
  0: all checks passed for all targets
  non-zero: at least one target failed

Note:
  - This is NOT a pytest test file, so it should not clash with existing tests.
  - Running a target as __main__ starts a child Python process.
    That boundary is intentionally HITL / approval gated.
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

HITL_APPROVAL_ENV = "VERIFY_STOP_COMPARATOR_HITL_APPROVED"
HITL_APPROVED_VALUES = {"1", "true", "yes", "y", "approved"}


class HitlApprovalError(PermissionError):
    """Raised when running a target as __main__ lacks explicit approval."""


def _env_hitl_approved() -> bool:
    """Return True when HITL approval is provided through the environment."""
    value = os.environ.get(HITL_APPROVAL_ENV, "")
    return value.strip().lower() in HITL_APPROVED_VALUES


def require_hitl_approval_for_main_run(
    *,
    approved: bool,
    target_path: str,
) -> None:
    """
    Require explicit approval before running a target file as __main__.

    Importing and compiling are local verification steps. Running a file as a
    script starts a child process and may execute arbitrary top-level behavior
    in the target file, so this step is guarded.
    """
    if approved or _env_hitl_approved():
        return

    raise HitlApprovalError(
        "HITL approval required before running target as __main__. "
        "Use --hitl-approved, set "
        f"{HITL_APPROVAL_ENV}=1, or use --no-main. "
        f"target={target_path!r}"
    )


def sha256_file(path: str) -> str:
    """Return the SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_from_path(mod_name: str, path: str):
    """Import a Python module from a filesystem path."""
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to build import spec for: {path}")

    mod = importlib.util.module_from_spec(spec)

    # Register so imports inside the module, if any, can resolve it by name.
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)

    return mod


def run_one_target(
    path: str,
    *,
    run_as_script: bool = True,
    hitl_approved: bool = False,
) -> int:
    """Run all verifier checks for one target file."""
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

    # 3) Import + _self_check if present
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

    # 4) Run as script (__main__), if enabled
    if run_as_script:
        try:
            require_hitl_approval_for_main_run(
                approved=hitl_approved,
                target_path=path,
            )

            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                check=False,
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
                return proc.returncode

            print("[OK] __main__")
        except HitlApprovalError as exc:
            print(f"[FAIL] {exc}")
            return 6
        except Exception:
            print("[FAIL] failed to run as script (__main__)")
            traceback.print_exc()
            return 7

    print("[PASS] target checks passed")
    return 0


def main(argv: List[str]) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="+",
        help="one or more Python file paths to verify",
    )
    parser.add_argument(
        "--no-main",
        action="store_true",
        help="skip running as __main__ and perform import/_self_check only",
    )
    parser.add_argument(
        "--hitl-approved",
        action="store_true",
        help=(
            "explicit approval for running targets as __main__; "
            f"equivalent to setting {HITL_APPROVAL_ENV}=1"
        ),
    )

    args = parser.parse_args(argv)

    run_as_script = not args.no_main

    for target_path in args.paths:
        rc = run_one_target(
            target_path,
            run_as_script=run_as_script,
            hitl_approved=bool(args.hitl_approved),
        )
        if rc != 0:
            return rc

    print("[PASS] all targets passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
