# tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import ai_doc_orchestrator_kage3_v1_2_4 as sim


# ----------------------------
# Generic helpers
# ----------------------------
def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        _fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _require_is_not_none(value: Any, message: str) -> None:
    if value is None:
        _fail(message)


# ----------------------------
# Utilities
# ----------------------------
def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _audit_paths(tmp_path: Path) -> Dict[str, Path]:
    return {
        "audit": tmp_path / "out" / "audit_v1_2_4.jsonl",
        "artifacts": tmp_path / "out" / "artifacts_v1_2_4",
    }


def _run(
    *,
    tmp_path: Path,
    prompt: str,
    run_id: str,
    hitl_choice: str | None,
    faults: Dict[str, Dict[str, Any]] | None = None,
    truncate: bool = True,
) -> sim.SimulationResult:
    paths = _audit_paths(tmp_path)

    def resolver(_run_id: str, _task_id: str, _layer: str, _reason_code: str) -> sim.HitlChoice:
        valid = hitl_choice in ("CONTINUE", "STOP")
        _require(valid, f"Unexpected hitl_choice: {hitl_choice!r}")
        return hitl_choice  # type: ignore[return-value]

    return sim.run_simulation(
        prompt=prompt,
        run_id=run_id,
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        faults=faults or {},
        truncate_audit_on_start=truncate,
        hitl_resolver=(resolver if hitl_choice is not None else None),
    )


def _get_task(out: sim.SimulationResult, task_id: str) -> sim.TaskResult:
    for task in out.tasks:
        if task.task_id == task_id:
            return task
    _fail(f"Task not found: {task_id}")
    raise AssertionError("unreachable")


def _assert_no_at_sign_persisted(audit_path: Path) -> None:
    txt = audit_path.read_text(encoding="utf-8", errors="replace") if audit_path.exists() else ""
    _require("@" not in txt, f"PII-like token '@' leaked into audit log: {audit_path}")


def _assert_arl_min_keys_row(row: Dict[str, Any]) -> None:
    for key in ("sealed", "overrideable", "final_decider"):
        _require(key in row, f"Missing ARL minimal key: {key!r} in row event={row.get('event')!r}")


def _assert_arl_minimal_keys(events: List[Dict[str, Any]]) -> None:
    must = {"sealed", "overrideable", "final_decider"}
    for i, event in enumerate(events):
        missing = must.difference(event.keys())
        _require(
            not missing,
            f"ARL minimal keys missing at row#{i}: {missing} (event={event.get('event')})",
        )


def _assert_decision_vocab(events: List[Dict[str, Any]]) -> None:
    allowed = {"RUN", "PAUSE_FOR_HITL", "STOPPED"}
    for i, event in enumerate(events):
        decision = event.get("decision")
        _require(isinstance(decision, str), f"decision is not str at row#{i}: {decision!r}")
        _require(decision in allowed, f"decision vocab mismatch at row#{i}: {decision!r}")


# ----------------------------
# Tests: HITL semantics
# ----------------------------
def test_meaning_hitl_continue_propagates_and_writes_artifacts(tmp_path: Path) -> None:
    """
    Prompt mentions only Excel, choose CONTINUE:
    - non-Excel tasks should pass through meaning HITL -> CONTINUE
    - at least one artifact should be written
    """
    paths = _audit_paths(tmp_path)
    prompt = "Excelで表を作ってください。"
    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#MEANING_CONTINUE",
        hitl_choice="CONTINUE",
        truncate=True,
    )

    _require(out.run_id == "TEST#MEANING_CONTINUE", "Unexpected run_id")
    _require(
        out.decision in ("RUN", "PAUSE_FOR_HITL", "STOPPED"),
        f"Unexpected overall decision: {out.decision!r}",
    )
    _require(
        bool(out.artifacts_written_task_ids),
        "Expected some artifacts to be written after HITL CONTINUE",
    )

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    saw_req = any(
        e.get("event") == "HITL_REQUESTED" and e.get("final_decider") == "SYSTEM"
        for e in rows
    )
    saw_dec = any(
        e.get("event") == "HITL_DECIDED" and e.get("final_decider") == "USER"
        for e in rows
    )
    saw_written = any(e.get("event") == "ARTIFACT_WRITTEN" for e in rows)

    _require(saw_req, "Missing HITL_REQUESTED (SYSTEM) event")
    _require(saw_dec, "Missing HITL_DECIDED (USER) event")
    _require(saw_written, "Expected ARTIFACT_WRITTEN events after HITL CONTINUE")


def test_meaning_hitl_stop_blocks_tasks_and_skips_artifacts(tmp_path: Path) -> None:
    """
    Prompt mentions only Excel, choose STOP:
    - some tasks should stop at meaning
    - artifacts should be skipped
    - overall should be STOPPED
    """
    paths = _audit_paths(tmp_path)
    prompt = "Excelで表を作ってください。"
    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#MEANING_STOP",
        hitl_choice="STOP",
        truncate=True,
    )

    _require_equal(out.decision, "STOPPED", "Overall should be STOPPED if any task is STOPPED")

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    stop_trace = any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in rows
    )
    skipped = any(
        e.get("event") == "ARTIFACT_SKIPPED" and e.get("decision") == "STOPPED"
        for e in rows
    )

    _require(stop_trace, "Missing post-HITL STOP trace")
    _require(skipped, "Expected ARTIFACT_SKIPPED with STOPPED decision in STOP path")


def test_rfl_hitl_continue_allows_dispatch(tmp_path: Path) -> None:
    """
    Generic prompt with relativity trigger:
    - meaning gate should not block
    - RFL should PAUSE_FOR_HITL with REL_BOUNDARY_UNSTABLE
    - CONTINUE should allow artifact writing
    """
    paths = _audit_paths(tmp_path)
    prompt = "おすすめはどっち？"
    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#RFL_CONTINUE",
        hitl_choice="CONTINUE",
        truncate=True,
    )

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    rfl_pause = any(
        e.get("event") == "GATE_RFL"
        and e.get("decision") == "PAUSE_FOR_HITL"
        and e.get("reason_code") == "REL_BOUNDARY_UNSTABLE"
        for e in rows
    )
    continued = any(
        e.get("event") == "HITL_DECIDED" and e.get("reason_code") == "HITL_CONTINUE"
        for e in rows
    )
    wrote = any(e.get("event") == "ARTIFACT_WRITTEN" for e in rows)

    _require(rfl_pause, "Expected RFL gate to PAUSE_FOR_HITL with REL_BOUNDARY_UNSTABLE")
    _require(continued, "Expected HITL_CONTINUE decision after RFL HITL")
    _require(bool(out.artifacts_written_task_ids), "Expected artifacts written after RFL HITL CONTINUE")
    _require(wrote, "Expected ARTIFACT_WRITTEN after CONTINUE")


def test_rfl_hitl_stop_blocks_dispatch(tmp_path: Path) -> None:
    """
    Same RFL trigger but STOP:
    - overall STOPPED
    - HITL STOP trace should exist
    """
    paths = _audit_paths(tmp_path)
    prompt = "おすすめはどっち？"
    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#RFL_STOP",
        hitl_choice="STOP",
        truncate=True,
    )

    _require_equal(out.decision, "STOPPED", "Expected STOPPED after RFL HITL STOP")

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    stop_trace = any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in rows
    )
    _require(stop_trace, "Missing HITL_STOP trace at RFL path")


# ----------------------------
# Ethics sealing
# ----------------------------
def test_ethics_violation_is_sealed_and_no_email_persists_in_logs(tmp_path: Path) -> None:
    """
    If raw_text contains email:
    - GATE_ETHICS must STOPPED with sealed=True and final_decider=SYSTEM
    - logs must never persist '@'
    """
    paths = _audit_paths(tmp_path)
    out = _run(
        tmp_path=tmp_path,
        prompt="ドキュメントを作ってください。",
        run_id="TEST#ETHICS_SEAL",
        hitl_choice="CONTINUE",
        faults={
            "word": {"leak_email": True},
            "excel": {"leak_email": False},
            "ppt": {"leak_email": False},
        },
        truncate=True,
    )

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    ethics_rows = [
        row
        for row in rows
        if row.get("event") == "GATE_ETHICS"
        and row.get("decision") == "STOPPED"
        and row.get("reason_code") == "ETHICS_EMAIL_DETECTED"
    ]
    _require(bool(ethics_rows), "Expected sealed ethics STOPPED event for email leak")

    hit = ethics_rows[0]
    _assert_arl_min_keys_row(hit)
    _require(hit["sealed"] is True, "Expected sealed=True for ethics stop")
    _require(hit["overrideable"] is False, "Expected overrideable=False for ethics stop")
    _require_equal(hit["final_decider"], "SYSTEM", "Expected SYSTEM final_decider for ethics stop")

    skipped = any(
        e.get("event") == "ARTIFACT_SKIPPED"
        and e.get("layer") == "ethics"
        and e.get("decision") == "STOPPED"
        and e.get("sealed") is True
        and e.get("final_decider") == "SYSTEM"
        for e in rows
    )
    _require(skipped, "Expected ARTIFACT_SKIPPED under ethics with sealed=true")
    _require_equal(out.decision, "STOPPED", "Overall should be STOPPED if any task STOPPED exists")


# ----------------------------
# AuditLog guarantees
# ----------------------------
def test_auditlog_deep_redacts_dict_keys_and_values(tmp_path: Path) -> None:
    """
    Deep redaction must include dict keys, not only values.
    """
    audit_path = tmp_path / "audit_keys.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)

    row = {
        "run_id": "TEST#KEY_REDACT",
        "task_id": "t1",
        "event": "CUSTOM",
        "layer": "orchestrator",
        "decision": "RUN",
        "reason_code": "CUSTOM",
        "sealed": False,
        "overrideable": False,
        "final_decider": "SYSTEM",
        "user@example.com": "ok",
        "note": "contact me at admin@example.com",
    }
    audit.emit(row)

    txt = audit_path.read_text(encoding="utf-8")
    _require(
        "@" not in txt,
        "Expected no '@' in persisted log even when dict key contains email-like token",
    )
    _require("<REDACTED_EMAIL>" in txt, "Expected redaction marker to appear in persisted log")


def test_auditlog_defensive_json_serialization_does_not_crash(tmp_path: Path) -> None:
    """
    default=str should prevent audit.emit from crashing on non-JSON types.
    """
    audit_path = tmp_path / "audit_nonjson.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)

    row = {
        "run_id": "TEST#NONJSON",
        "task_id": "t1",
        "event": "CUSTOM",
        "layer": "orchestrator",
        "decision": "RUN",
        "reason_code": "CUSTOM",
        "sealed": False,
        "overrideable": False,
        "final_decider": "SYSTEM",
        "non_json": {"a_set": {1, 2, 3}},
    }
    audit.emit(row)

    rows = _read_jsonl(audit_path)
    _require_equal(len(rows), 1, "Expected exactly one audit row")
    _require("non_json" in rows[0], "Expected non_json key to persist")
    _require(
        isinstance(rows[0]["non_json"]["a_set"], str),
        "Expected set to be stringified by default=str",
    )


def test_start_run_truncate_and_ts_monotonicity(tmp_path: Path) -> None:
    """
    - start_run(truncate=True) should truncate
    - timestamps should be monotonic within a run
    """
    audit_path = tmp_path / "audit_ts.jsonl"
    audit = sim.AuditLog(audit_path)

    audit.start_run(truncate=True)
    audit.emit(
        {
            "run_id": "A",
            "task_id": "t",
            "event": "E1",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "E1",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
        }
    )
    audit.emit(
        {
            "run_id": "A",
            "task_id": "t",
            "event": "E2",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "E2",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
        }
    )

    rows_a = _read_jsonl(audit_path)
    _require_equal(len(rows_a), 2, "Expected two rows in first run")
    _require(rows_a[0]["ts"] < rows_a[1]["ts"], "Expected monotonic ts within a run")

    audit.start_run(truncate=True)
    audit.emit(
        {
            "run_id": "B",
            "task_id": "t",
            "event": "E1",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "E1",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
        }
    )

    rows_b = _read_jsonl(audit_path)
    _require_equal(len(rows_b), 1, "Expected truncate=True to reset file content")
    _require_equal(rows_b[0]["run_id"], "B", "Expected second run to overwrite first run content")


# ----------------------------
# Consistency / regen path
# ----------------------------
def test_consistency_mismatch_continue_enters_regen_pending_and_skips_artifact(tmp_path: Path) -> None:
    """
    If contract mismatch occurs and user CONTINUE:
    - emit REGEN_REQUESTED + REGEN_INSTRUCTIONS
    - keep broken task in PAUSE_FOR_HITL
    - skip artifact for that task
    """
    paths = _audit_paths(tmp_path)
    out = _run(
        tmp_path=tmp_path,
        prompt="ドキュメントを作ってください。",
        run_id="TEST#CONSISTENCY_CONTINUE",
        hitl_choice="CONTINUE",
        faults={
            "excel": {"break_contract": True, "leak_email": False},
            "word": {"break_contract": False, "leak_email": False},
            "ppt": {"break_contract": False, "leak_email": False},
        },
        truncate=True,
    )

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Expected non-empty audit rows")
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    regen_requested = any(
        r.get("task_id") == "task_excel" and r.get("event") == "REGEN_REQUESTED"
        for r in rows
    )
    regen_instructions = any(
        r.get("task_id") == "task_excel" and r.get("event") == "REGEN_INSTRUCTIONS"
        for r in rows
    )
    skipped_paused = any(
        r.get("task_id") == "task_excel"
        and r.get("event") == "ARTIFACT_SKIPPED"
        and r.get("decision") == "PAUSE_FOR_HITL"
        for r in rows
    )

    _require(regen_requested, "Expected REGEN_REQUESTED on contract mismatch")
    _require(regen_instructions, "Expected REGEN_INSTRUCTIONS on contract mismatch")
    _require(
        skipped_paused,
        "Expected excel ARTIFACT_SKIPPED with PAUSE_FOR_HITL after regen pending",
    )

    excel_task = _get_task(out, "task_excel")
    _require_equal(excel_task.decision, "PAUSE_FOR_HITL", "Expected excel task to remain paused")
    _require_equal(
        excel_task.blocked_layer,
        "consistency",
        "Expected consistency blocked_layer",
    )
    _require(
        out.decision in ("PAUSE_FOR_HITL", "STOPPED"),
        f"Unexpected overall decision: {out.decision!r}",
    )
