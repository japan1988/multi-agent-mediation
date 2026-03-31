# tests/conftest.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

JST = timezone(timedelta(hours=9))

DECISION_RUN = "RUN"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOP = "STOPPED"

DECIDER_SYSTEM = "SYSTEM"

LAYER_TEST_SESSION = "test_session"
LAYER_TEST_COLLECTION = "test_collection"
LAYER_TEST_CASE = "test_case"
LAYER_TEST_BRIDGE = "test_simulation_arl_bridge"

RC_TEST_SESSION_STARTED = "TEST_SESSION_STARTED"
RC_TEST_COLLECTION_FINISHED = "TEST_COLLECTION_FINISHED"
RC_TEST_PASSED = "TEST_PASSED"
RC_TEST_FAILED = "TEST_FAILED"
RC_TEST_SKIPPED = "TEST_SKIPPED"
RC_TEST_SETUP_FAILED = "TEST_SETUP_FAILED"
RC_TEST_TEARDOWN_FAILED = "TEST_TEARDOWN_FAILED"
RC_TEST_XFAILED = "TEST_XFAILED"
RC_TEST_XPASSED = "TEST_XPASSED"
RC_TEST_SESSION_FINISHED = "TEST_SESSION_FINISHED"
RC_TEST_SIM_ARL_APPENDED = "TEST_SIM_ARL_APPENDED"


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _default_test_arl_path() -> Path:
    raw = os.environ.get("TEST_ARL_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path("test_artifacts") / "pytest_test_arl.jsonl"


def _default_sim_arl_path() -> Path:
    raw = os.environ.get("SIM_ARL_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path("test_artifacts") / "pytest_simulation_arl.jsonl"


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _emit_arl(
    path: Path,
    *,
    run_id: str,
    layer: str,
    decision: str,
    sealed: bool,
    overrideable: bool,
    final_decider: str,
    reason_code: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "ts": now_iso(),
        "run_id": run_id,
        "layer": layer,
        "decision": decision,
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
        "reason_code": reason_code,
    }
    if extra:
        row["extra"] = extra

    _append_jsonl(path, row)
    return row


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("arl")
    group.addoption(
        "--test-arl-path",
        action="store",
        default="",
        help="Path to pytest execution ARL JSONL. "
        "Defaults to TEST_ARL_PATH or test_artifacts/pytest_test_arl.jsonl",
    )
    group.addoption(
        "--test-arl-mode",
        action="store",
        choices=["overwrite", "append"],
        default=os.environ.get("TEST_ARL_MODE", "overwrite"),
        help="Whether to overwrite or append the pytest execution ARL file.",
    )
    group.addoption(
        "--sim-arl-path",
        action="store",
        default="",
        help="Path to append simulation raw ARL rows from tests. "
        "Defaults to SIM_ARL_PATH or test_artifacts/pytest_simulation_arl.jsonl",
    )


def pytest_configure(config: pytest.Config) -> None:
    raw_test_path = str(config.getoption("--test-arl-path") or "").strip()
    raw_sim_path = str(config.getoption("--sim-arl-path") or "").strip()
    mode = str(config.getoption("--test-arl-mode") or "overwrite").strip()

    test_arl_path = Path(raw_test_path) if raw_test_path else _default_test_arl_path()
    sim_arl_path = Path(raw_sim_path) if raw_sim_path else _default_sim_arl_path()

    config._test_arl_path = test_arl_path  # type: ignore[attr-defined]
    config._sim_arl_path = sim_arl_path  # type: ignore[attr-defined]
    config._test_arl_run_id = f"TEST#{uuid.uuid4().hex[:12]}"  # type: ignore[attr-defined]
    config._test_arl_primary_outcomes = {}  # type: ignore[attr-defined]
    config._test_arl_teardown_failures = 0  # type: ignore[attr-defined]
    config._test_arl_collection_count = 0  # type: ignore[attr-defined]

    if mode == "overwrite" and test_arl_path.exists():
        test_arl_path.unlink()

    _emit_arl(
        test_arl_path,
        run_id=config._test_arl_run_id,  # type: ignore[attr-defined]
        layer=LAYER_TEST_SESSION,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_TEST_SESSION_STARTED,
        extra={
            "arl_path": str(test_arl_path),
            "sim_arl_path": str(sim_arl_path),
            "mode": mode,
        },
    )


def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    config._test_arl_collection_count = len(session.items)  # type: ignore[attr-defined]

    _emit_arl(
        config._test_arl_path,  # type: ignore[attr-defined]
        run_id=config._test_arl_run_id,  # type: ignore[attr-defined]
        layer=LAYER_TEST_COLLECTION,
        decision=DECISION_RUN,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_TEST_COLLECTION_FINISHED,
        extra={
            "collected": len(session.items),
        },
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()

    config = item.config
    test_arl_path: Path = config._test_arl_path  # type: ignore[attr-defined]
    run_id: str = config._test_arl_run_id  # type: ignore[attr-defined]
    primary_outcomes: Dict[str, str] = config._test_arl_primary_outcomes  # type: ignore[attr-defined]

    nodeid = report.nodeid
    wasxfail = getattr(report, "wasxfail", None)

    # setup で落ちた/skip された場合
    if report.when == "setup":
        if report.failed:
            primary_outcomes.setdefault(nodeid, "failed")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_STOP,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_SETUP_FAILED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "longrepr": str(report.longrepr),
                },
            )
        elif report.skipped:
            primary_outcomes.setdefault(nodeid, "skipped")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_PAUSE,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_SKIPPED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "longrepr": str(report.longrepr),
                },
            )
        return

    # call が本体
    if report.when == "call":
        if wasxfail and report.skipped:
            primary_outcomes.setdefault(nodeid, "xfailed")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_PAUSE,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_XFAILED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "wasxfail": str(wasxfail),
                },
            )
        elif wasxfail and report.passed:
            primary_outcomes.setdefault(nodeid, "xpassed")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_STOP,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_XPASSED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "wasxfail": str(wasxfail),
                },
            )
        elif report.passed:
            primary_outcomes.setdefault(nodeid, "passed")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_RUN,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_PASSED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                },
            )
        elif report.failed:
            primary_outcomes.setdefault(nodeid, "failed")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_STOP,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_FAILED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "longrepr": str(report.longrepr),
                },
            )
        elif report.skipped:
            primary_outcomes.setdefault(nodeid, "skipped")
            _emit_arl(
                test_arl_path,
                run_id=run_id,
                layer=LAYER_TEST_CASE,
                decision=DECISION_PAUSE,
                sealed=False,
                overrideable=False,
                final_decider=DECIDER_SYSTEM,
                reason_code=RC_TEST_SKIPPED,
                extra={
                    "nodeid": nodeid,
                    "when": report.when,
                    "duration_sec": round(report.duration, 6),
                    "longrepr": str(report.longrepr),
                },
            )
        return

    # teardown 失敗は別カウント
    if report.when == "teardown" and report.failed:
        config._test_arl_teardown_failures += 1  # type: ignore[attr-defined]
        _emit_arl(
            test_arl_path,
            run_id=run_id,
            layer=LAYER_TEST_CASE,
            decision=DECISION_STOP,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_TEST_TEARDOWN_FAILED,
            extra={
                "nodeid": nodeid,
                "when": report.when,
                "duration_sec": round(report.duration, 6),
                "longrepr": str(report.longrepr),
            },
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    primary_outcomes: Dict[str, str] = config._test_arl_primary_outcomes  # type: ignore[attr-defined]

    counts = {
        "passed": sum(1 for v in primary_outcomes.values() if v == "passed"),
        "failed": sum(1 for v in primary_outcomes.values() if v == "failed"),
        "skipped": sum(1 for v in primary_outcomes.values() if v == "skipped"),
        "xfailed": sum(1 for v in primary_outcomes.values() if v == "xfailed"),
        "xpassed": sum(1 for v in primary_outcomes.values() if v == "xpassed"),
        "teardown_failed": int(config._test_arl_teardown_failures),  # type: ignore[attr-defined]
        "collected": int(config._test_arl_collection_count),  # type: ignore[attr-defined]
    }

    _emit_arl(
        config._test_arl_path,  # type: ignore[attr-defined]
        run_id=config._test_arl_run_id,  # type: ignore[attr-defined]
        layer=LAYER_TEST_SESSION,
        decision=DECISION_RUN if exitstatus == 0 else DECISION_STOP,
        sealed=False,
        overrideable=False,
        final_decider=DECIDER_SYSTEM,
        reason_code=RC_TEST_SESSION_FINISHED,
        extra={
            "exitstatus": exitstatus,
            **counts,
        },
    )


@pytest.fixture
def append_simulation_arl(request: pytest.FixtureRequest):
    """
    テスト内で run_simulation(..., keep_runs=True) の結果から、
    生の simulation ARL を別 JSONL に追記するための helper。

    使い方:
        def test_xxx(append_simulation_arl):
            results = sim.run_simulation(..., keep_runs=True)
            written = append_simulation_arl(results)
            assert written > 0
    """
    config = request.config
    sim_arl_path: Path = config._sim_arl_path  # type: ignore[attr-defined]
    test_arl_path: Path = config._test_arl_path  # type: ignore[attr-defined]
    run_id: str = config._test_arl_run_id  # type: ignore[attr-defined]
    nodeid = request.node.nodeid

    def _append(results: Dict[str, Any]) -> int:
        runs = (results or {}).get("runs", []) or []
        written = 0

        for run in runs:
            sim_run_id = run.get("run_id")
            for row in (run.get("arl", []) or []):
                row2 = dict(row)
                row2["test_nodeid"] = nodeid
                row2["test_run_id"] = run_id
                row2["simulation_run_id"] = sim_run_id
                _append_jsonl(sim_arl_path, row2)
                written += 1

        _emit_arl(
            test_arl_path,
            run_id=run_id,
            layer=LAYER_TEST_BRIDGE,
            decision=DECISION_RUN,
            sealed=False,
            overrideable=False,
            final_decider=DECIDER_SYSTEM,
            reason_code=RC_TEST_SIM_ARL_APPENDED,
            extra={
                "nodeid": nodeid,
                "simulation_rows_written": written,
                "sim_arl_path": str(sim_arl_path),
            },
        )
        return written

    return _append
