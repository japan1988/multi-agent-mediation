# tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
# -*- coding: utf-8 -*-
"""
Merged regression tests for ai_doc_orchestrator_kage3_v1_2_4

Coverage:
- CI-friendly import path handling
- audit.emit() auto-fills ts
- deep redaction: BOTH dict keys and values
- defensive JSON serialization (default=str)
- HITL firepoints observable in logs
- meaning HITL CONTINUE / STOP behavior
- RFL HITL CONTINUE / STOP behavior
- ethics email leak is SEALED and '@' never persists
- consistency mismatch => regen pending + artifact skipped
- start_run(truncate=True) truncates and ts stays monotonic

Notes:
- Avoid bare `assert` to reduce Bandit B101 findings under strict operation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is importable under pytest/CI cwd differences.
_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests/.. (repo root)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import ai_doc_orchestrator_kage3_v1_2_4 as sim  # noqa: E402


def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        _fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _blob(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)


def _find(rows: list[dict[str, Any]], **conds: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ok = True
        for key, value in conds.items():
            if row.get(key) != value:
                ok = False
                break
        if ok:
            out.append(row)
    return out


def _audit_paths(tmp_path: Path) -> dict[str, Path]:
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
    faults: dict[str, dict[str, Any]] | None = None,
    truncate: bool = True,
) -> sim.SimulationResult:
    paths = _audit_paths(tmp_path)

    def resolver(_run_id: str, _task_id: str, _layer: str, _reason_code: str) -> sim.HitlChoice:
        if hitl_choice not in ("CONTINUE", "STOP"):
            _fail(f"invalid hitl_choice for resolver: {hitl_choice!r}")
        return hitl_choice

    return sim.run_simulation(
        prompt=prompt,
        run_id=run_id,
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        faults=faults or {},
        truncate_audit_on_start=truncate,
        hitl_resolver=(resolver if hitl_choice is not None else None),
    )


def _assert_no_at_sign_persisted(audit_path: Path) -> None:
    txt = audit_path.read_text(encoding="utf-8", errors="replace") if audit_path.exists() else ""
    _require("@" not in txt, f"PII-like token '@' leaked into audit log: {audit_path}")


def _assert_arl_min_keys_row(row: dict[str, Any]) -> None:
    for key in (
        "run_id",
        "ts",
        "layer",
        "decision",
        "reason_code",
        "sealed",
        "overrideable",
        "final_decider",
    ):
        _require(key in row, f"missing ARL key: {key}")


def _assert_arl_minimal_keys(events: list[dict[str, Any]]) -> None:
    for i, row in enumerate(events):
        missing = {"sealed", "overrideable", "final_decider"}.difference(row.keys())
        _require(not missing, f"ARL minimal keys missing at row#{i}: {missing} (event={row.get('event')})")


def _assert_decision_vocab(events: list[dict[str, Any]]) -> None:
    allowed = {"RUN", "PAUSE_FOR_HITL", "STOPPED"}
    for i, row in enumerate(events):
        decision = row.get("decision")
        _require(isinstance(decision, str), f"decision is not str at row#{i}: {decision!r}")
        _require(decision in allowed, f"decision vocab mismatch at row#{i}: {decision!r}")


def _get_task(res: sim.SimulationResult, task_id: str) -> Any:
    for task in res.tasks:
        if task.task_id == task_id:
            return task
    _fail(f"task not found: {task_id}")
    return None


def test_audit_emit_autofills_ts_and_redacts_keys_and_values(tmp_path: Path) -> None:
    """
    emit() must auto-fill ts.
    Deep redaction must redact BOTH dict keys and values.
    Email-like keys and values must never persist.
    """
    audit_path = tmp_path / "audit_keys.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)

    audit.emit(
        {
            "run_id": "T#A1",
            "task_id": "task_x",
            "event": "EVIDENCE",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "evidence": {
                "test.user@example.com": "contact=test.user@example.com",
                "nested": {"k": "demo@example.com"},
            },
        }
    )

    rows = _read_jsonl(audit_path)
    _require_equal(len(rows), 1, "Expected exactly one audit row")

    ts = rows[0].get("ts")
    _require(isinstance(ts, str) and bool(ts), "Expected non-empty auto-filled ts")

    blob = _blob(rows)
    _require("@" not in blob, "Expected no '@' in persisted audit blob")
    _require("<REDACTED_EMAIL>" in blob, "Expected redaction marker in persisted audit blob")


def test_audit_default_str_prevents_crash_on_non_json_types(tmp_path: Path) -> None:
    """
    audit must not crash if row includes non-JSON-serializable objects.
    """

    class NonJson:
        def __str__(self) -> str:
            return "NONJSON"

    audit_path = tmp_path / "audit_nonjson.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)

    audit.emit(
        {
            "run_id": "T#A2",
            "task_id": "task_x",
            "event": "NONJSON",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "obj": NonJson(),
            "non_json": {"a_set": {1, 2, 3}},
        }
    )

    rows = _read_jsonl(audit_path)
    _require_equal(len(rows), 1, "Expected exactly one audit row")
    _require_equal(rows[0].get("obj"), "NONJSON", "Expected default=str serialization for object")
    _require("non_json" in rows[0], "Expected non_json field to persist")
    _require(
        isinstance(rows[0]["non_json"]["a_set"], str),
        "Expected set to be serialized via default=str",
    )


def test_start_run_truncate_and_ts_monotonicity(tmp_path: Path) -> None:
    """
    start_run(truncate=True) must truncate the file.
    Per-run ts monotonicity should hold.
    """
    audit_path = tmp_path / "audit_ts.jsonl"
    audit = sim.AuditLog(audit_path)

    # Run A
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
    _require_equal(len(rows_a), 2, "Expected two rows for run A")
    _require(rows_a[0]["ts"] < rows_a[1]["ts"], "Expected monotonic ts within a run")

    # Run B: truncate
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
    _require_equal(rows_b[0]["run_id"], "B", "Expected only run B to remain after truncation")


def test_hitl_firepoint_events_and_arl_fields_present(tmp_path: Path) -> None:
    """
    HITL firepoint must be observable in logs:
    - HITL_REQUESTED (SYSTEM, PAUSE_FOR_HITL, overrideable=True, sealed=False)
    - HITL_DECIDED (USER, RUN or STOPPED, overrideable=False, sealed=False)

    and ARL-min fields must exist.
    """
    audit_path = tmp_path / "audit.jsonl"
    art_dir = tmp_path / "artifacts"

    # Prompt mentions only Excel => word/ppt meaning gate should HITL.
    def resolver(
        run_id: str,
        task_id: str,
        layer: str,
        reason_code: str,

    """
    paths = _audit_paths(tmp_path)

    def resolver(
        _run_id: str,
        _task_id: str,
        _layer: str,
        _reason_code: str,

    ) -> sim.HitlChoice:
        return "STOP"

    res = sim.run_simulation(
        prompt="Excelの表を作って",
        run_id="T#HITL",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=resolver,
    )

    rows = _read_jsonl(paths["audit"])
    reqs = _find(rows, event="HITL_REQUESTED")
    decs = _find(rows, event="HITL_DECIDED")

    _require(bool(reqs), "HITL_REQUESTED not found")
    _require(bool(decs), "HITL_DECIDED not found")

    _assert_arl_min_keys_row(reqs[0])
    _assert_arl_min_keys_row(decs[0])

    _require_equal(reqs[0]["decision"], "PAUSE_FOR_HITL", "Expected HITL_REQUESTED decision")
    _require_equal(reqs[0]["final_decider"], "SYSTEM", "Expected SYSTEM final_decider for request")
    _require(reqs[0]["overrideable"] is True, "Expected overrideable=True for HITL_REQUESTED")
    _require(reqs[0]["sealed"] is False, "Expected sealed=False for HITL_REQUESTED")

    _require_equal(decs[0]["final_decider"], "USER", "Expected USER final_decider for decision")
    _require(decs[0]["overrideable"] is False, "Expected overrideable=False for HITL_DECIDED")
    _require(decs[0]["sealed"] is False, "Expected sealed=False for HITL_DECIDED")

    _require(
        any(task.decision == "STOPPED" and task.blocked_layer == "meaning" for task in res.tasks),
        "Expected at least one meaning-stopped task after HITL STOP",
    )


def test_meaning_hitl_continue_propagates_and_writes_artifacts(tmp_path: Path) -> None:
    """
    Prompt mentions only Excel:
    - word/ppt should meaning-hitl
    - CONTINUE should allow progress
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

    _require_equal(out.run_id, "TEST#MEANING_CONTINUE", "Unexpected run_id")
    _require(
        out.decision in ("RUN", "PAUSE_FOR_HITL", "STOPPED"),
        f"Unexpected overall decision: {out.decision!r}",
    )
    _require(bool(out.artifacts_written_task_ids), "Expected artifacts after HITL CONTINUE")

    events = _read_jsonl(paths["audit"])
    _require(bool(events), "Audit log should not be empty")

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    saw_req = any(e.get("event") == "HITL_REQUESTED" and e.get("final_decider") == "SYSTEM" for e in events)
    saw_dec = any(e.get("event") == "HITL_DECIDED" and e.get("final_decider") == "USER" for e in events)
    saw_written = any(e.get("event") == "ARTIFACT_WRITTEN" for e in events)

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

    events = _read_jsonl(paths["audit"])
    _require(bool(events), "Audit log should not be empty")

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    hitl_stop = any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in events
    )
    skipped = any(
        e.get("event") == "ARTIFACT_SKIPPED" and e.get("decision") == "STOPPED"
        for e in events
    )

    _require(hitl_stop, "Missing post-HITL STOP trace")
    _require(skipped, "Expected ARTIFACT_SKIPPED with STOPPED decision in STOP path")


def test_rfl_gate_triggers_hitl_and_continue_allows_dispatch(tmp_path: Path) -> None:
    """
    RFL:
    - relative prompt should cause PAUSE_FOR_HITL at layer=rfl
    - CONTINUE should allow dispatch and artifact writing
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


    rows = _read_jsonl(audit_path)
    rfl_gate = [
        r
        for r in rows
        if r.get("event") == "GATE_RFL" and r.get("decision") == "PAUSE_FOR_HITL"
    ]

    assert rfl_gate, "RFL gate did not trigger PAUSE_FOR_HITL"
    assert any(
        r.get("event") == "HITL_REQUESTED" and r.get("layer") == "rfl"
        for r in rows
    )
    assert res.artifacts_written_task_ids, "No artifacts were written after HITL_CONTINUE"

    rows = _read_jsonl(paths["audit"])
    _require(bool(rows), "Audit log should not be empty")

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(rows)
    _assert_decision_vocab(rows)

    rfl_gate = any(
        r.get("event") == "GATE_RFL"
        and r.get("decision") == "PAUSE_FOR_HITL"
        and r.get("reason_code") == "REL_BOUNDARY_UNSTABLE"
        for r in rows
    )
    hitl_continue = any(
        r.get("event") == "HITL_DECIDED" and r.get("reason_code") == "HITL_CONTINUE"
        for r in rows
    )
    artifacts_written = any(r.get("event") == "ARTIFACT_WRITTEN" for r in rows)

    _require(rfl_gate, "Expected RFL gate to PAUSE_FOR_HITL with REL_BOUNDARY_UNSTABLE")
    _require(hitl_continue, "Expected HITL_CONTINUE decision after RFL HITL")
    _require(bool(out.artifacts_written_task_ids), "Expected artifacts written after RFL HITL CONTINUE")
    _require(artifacts_written, "Expected ARTIFACT_WRITTEN after CONTINUE")



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


    rows = _read_jsonl(audit_path)
    ethics_rows = [
        r
        for r in rows
        if r.get("event") == "GATE_ETHICS" and r.get("decision") == "STOPPED"
    ]

    assert ethics_rows, "No STOPPED GATE_ETHICS found"

    _require_equal(out.decision, "STOPPED", "Expected STOPPED after RFL HITL STOP")


    events = _read_jsonl(paths["audit"])
    _require(bool(events), "Audit log should not be empty")

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    hitl_stop = any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in events
    )
    _require(hitl_stop, "Missing HITL_STOP trace at RFL path")


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
        hitl_choice="CONTINUE",  # irrelevant; ethics is SYSTEM-sealed
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
    _require(
        any(task.decision == "STOPPED" and task.blocked_layer == "ethics" for task in out.tasks),
        "Expected at least one ethics-blocked task",
    )


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
            "excel": {"break_contract": True},
            "word": {"break_contract": False},
            "ppt": {"break_contract": False},
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

    ]
    assert excel_skips, (
        "Expected excel ARTIFACT_SKIPPED with PAUSE_FOR_HITL after regen pending"

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
    _require_equal(excel_task.blocked_layer, "consistency", "Expected consistency blocked_layer")
    _require(
        out.decision in ("PAUSE_FOR_HITL", "STOPPED"),
        f"Unexpected overall decision: {out.decision!r}",
    )
