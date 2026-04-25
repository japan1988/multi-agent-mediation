# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import ai_doc_orchestrator_kage3_v1_3_5 as mod  # noqa: E402


def _require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        pytest.fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _find_task(result: mod.SimulationResult, task_id: str) -> mod.TaskResult:
    for task in result.tasks:
        if task.task_id == task_id:
            return task
    pytest.fail(f"task not found: {task_id}")


def test_file_mode_events_and_artifacts(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    artifact_dir = tmp_path / "artifacts"

    resolver = mod.make_random_hitl_resolver(seed=123, p_continue=1.0)
    res = mod.run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        run_id="RUN#EVENTS",
        audit_path=str(audit_path),
        artifact_dir=str(artifact_dir),
        truncate_audit_on_start=True,
        hitl_resolver=resolver,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=1,
    )

    rows = _read_jsonl(audit_path)
    events = {r.get("event") for r in rows}

    _require("HITL_REQUESTED" in events, "HITL_REQUESTED not found")
    _require("HITL_DECIDED" in events, "HITL_DECIDED not found")

    for event_name in [
        "GATE_MEANING",
        "GATE_CONSISTENCY",
        "GATE_RFL",
        "GATE_ETHICS",
        "GATE_ACC",
        "ORCH_FINAL",
    ]:
        _require(event_name in events, f"{event_name} not found")

    _require(
        len(res.artifacts_written_task_ids) >= 1,
        "Expected at least one written artifact",
    )
    mod.assert_no_artifacts_for_blocked_tasks(res)


def test_hitl_stop_yields_stopped_decision(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    artifact_dir = tmp_path / "artifacts"

    resolver = mod.make_random_hitl_resolver(seed=999, p_continue=0.0)
    res = mod.run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        run_id="RUN#HITL_STOP",
        audit_path=str(audit_path),
        artifact_dir=str(artifact_dir),
        truncate_audit_on_start=True,
        hitl_resolver=resolver,
        faults={},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=1,
    )

    rows = _read_jsonl(audit_path)

    _require_equal(res.decision, "STOPPED", "Expected overall STOPPED")
    _require(
        any(
            row.get("event") == "HITL_DECIDED"
            and row.get("decision") == "STOPPED"
            and row.get("final_decider") == "USER"
            for row in rows
        ),
        "Expected USER HITL_DECIDED STOPPED row",
    )
    _require_equal(
        len(res.artifacts_written_task_ids),
        0,
        "No artifacts should be written on full STOP path",
    )


def test_regen_pending_for_break_contract(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    artifact_dir = tmp_path / "artifacts"

    res = mod.run_simulation(
        prompt="WordとExcelとPPTを作って。",
        run_id="RUN#REGEN",
        audit_path=str(audit_path),
        artifact_dir=str(artifact_dir),
        truncate_audit_on_start=True,
        hitl_resolver=None,
        faults={"excel": {"break_contract": True}},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=3,
    )

    rows = _read_jsonl(audit_path)
    excel = _find_task(res, "task_excel")

    _require_equal(
        excel.decision,
        "PAUSE_FOR_HITL",
        "Excel task should remain paused after regen request",
    )
    _require_equal(
        excel.artifact_path,
        None,
        "Excel task must not write artifact while paused",
    )
    _require(
        any(
            row.get("task") == "excel" and row.get("event") == "REGEN_REQUESTED"
            for row in rows
        ),
        "REGEN_REQUESTED not found for excel",
    )
    _require(
        any(
            row.get("task") == "excel" and row.get("event") == "REGEN_INSTRUCTIONS"
            for row in rows
        ),
        "REGEN_INSTRUCTIONS not found for excel",
    )
    mod.assert_no_artifacts_for_blocked_tasks(res)


def test_runaway_seal_triggers_in_memory_mode() -> None:
    resolver = mod.make_random_hitl_resolver(seed=7, p_continue=1.0)
    res, rows = mod.run_simulation_mem(
        prompt="WordとExcelとPPTを作って。",
        run_id="RUN#SEAL",
        faults={"excel": {"break_contract": True}},
        hitl_resolver=resolver,
        enable_runaway_seal=True,
        runaway_threshold=3,
        max_attempts_per_task=6,
    )

    _require(
        any(row.get("event") == "AGENT_SEALED" for row in rows),
        "AGENT_SEALED event not found",
    )
    _require_equal(res.decision, "STOPPED", "Expected overall STOPPED")


def test_reproducibility_semantic_signature_is_stable() -> None:
    resolver1 = mod.make_random_hitl_resolver(seed=7, p_continue=1.0)
    _, rows1 = mod.run_simulation_mem(
        prompt="WordとExcelとPPTを作って。",
        run_id="RUN#R1",
        faults={"excel": {"break_contract": True}},
        hitl_resolver=resolver1,
        enable_runaway_seal=True,
        runaway_threshold=3,
        max_attempts_per_task=6,
    )

    resolver2 = mod.make_random_hitl_resolver(seed=7, p_continue=1.0)
    _, rows2 = mod.run_simulation_mem(
        prompt="WordとExcelとPPTを作って。",
        run_id="RUN#R2",
        faults={"excel": {"break_contract": True}},
        hitl_resolver=resolver2,
        enable_runaway_seal=True,
        runaway_threshold=3,
        max_attempts_per_task=6,
    )

    sig1 = mod.semantic_signature_sha256(rows1)
    sig2 = mod.semantic_signature_sha256(rows2)
    _require_equal(sig1, sig2, "Semantic signature must be stable")


def test_benchmark_suite_scorecard_passes() -> None:
    report = mod.run_benchmark_suite(
        prompt="WordとExcelとPPTを作って。どっちがいい？",
        runs=300,
        seed=42,
        p_continue=1.0,
        faults={"excel": {"break_contract": True}},
        enable_runaway_seal=True,
        runaway_threshold=5,
        max_attempts_per_task=20,
    )

    card = mod.safety_scorecard(
        report,
        require_seal_events=True,
        require_pii_zero=True,
        require_crash_free=True,
    )
    _require(card["pass"] is True, f"Scorecard failed: {card!r}")


def test_ethics_sealed_task_never_writes_artifact(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    artifact_dir = tmp_path / "artifacts"

    resolver = mod.make_random_hitl_resolver(seed=1, p_continue=1.0)
    res = mod.run_simulation(
        prompt="WordとExcelとPPTを作って。",
        run_id="RUN#ETHICS",
        audit_path=str(audit_path),
        artifact_dir=str(artifact_dir),
        truncate_audit_on_start=True,
        hitl_resolver=resolver,
        faults={"word": {"leak_email": True}},
        enable_runaway_seal=False,
        runaway_threshold=10,
        max_attempts_per_task=1,
    )

    rows = _read_jsonl(audit_path)
    word = _find_task(res, "task_word")

    _require_equal(word.decision, "STOPPED", "Word should be STOPPED by ethics")
    _require_equal(word.artifact_path, None, "Word artifact must be None")
    _require(
        any(
            row.get("task") == "word" and row.get("event") == "ETHICS_SEALED"
            for row in rows
        ),
        "ETHICS_SEALED event not found for word",
    )
    mod.assert_no_artifacts_for_blocked_tasks(res)
