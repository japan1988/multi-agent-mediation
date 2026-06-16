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

    def resolver(
        _run_id: str,
        _task_id: str,
        _layer: str,
        _reason_code: str,
    ) -> sim.HitlChoice:
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
    txt = (
        audit_path.read_text(encoding="utf-8", errors="replace")
        if audit_path.exists()
        else ""
    )
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
        _require(
            not missing,
            f"ARL minimal keys missing at row#{i}: {missing} (event={row.get('event')})",
        )


def _assert_decision_vocab(events: list[dict[str, Any]]) -> None:
    allowed = {"RUN", "PAUSE_FOR_HITL", "STOPPED"}
    for i, row in enumerate(events):
        decision = row.get("decision")
        _require(
            isinstance(decision, str),
            f"decision is not str at row#{i}: {decision!r}",
        )
        _require(
            decision in allowed,
            f"decision vocab mismatch at row#{i}: {decision!r}",
        )


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
    _require(
        "<REDACTED_EMAIL>" in blob,
        "Expected redaction marker in persisted audit blob",
    )


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
    _require_equal(
        rows[0].get("obj"),
        "NONJSON",
        "Expected default=str serialization for object",
    )
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
    _require_equal(
        rows_b[0]["run_id"],
        "B",
        "Expected only run B to remain after truncation",
    )


def test_hitl_firepoint_events_and_arl_fields_present(tmp_path: Path) -> None:
    """
    HITL firepoint must be observable in logs:
    - HITL_REQUESTED (SYSTEM, PAUSE_FOR_HITL, overrideable=True, sealed=False)
    - HITL_DECIDED (USER, RUN or STOPPED, overrideable=False, sealed=False)
    and ARL-min fields must exist.
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

    _require_equal(
        reqs[0]["decision"],
        "PAUSE_FOR_HITL",
        "Expected HITL_REQUESTED decision",
    )
    _require_equal(
        reqs[0]["final_decider"],
        "SYSTEM",
        "Expected SYSTEM final_decider for request",
    )
    _require(
        reqs[0]["overrideable"] is True,
        "Expected overrideable=True for HITL_REQUESTED",
    )
    _require(reqs[0]["sealed"] is False, "Expected sealed=False for HITL_REQUESTED")

    _require_equal(
        decs[0]["final_decider"],
        "USER",
        "Expected USER final_decider for decision",
    )
    _require(
        decs[0]["overrideable"] is False,
        "Expected overrideable=False for HITL_DECIDED",
    )
    _require(decs[0]["sealed"] is False, "Expected sealed=False for HITL_DECIDED")

    _require(
        any(
            task.decision == "STOPPED" and task.blocked_layer == "meaning"
            for task in res.tasks
        ),
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

    saw_req = any(
        e.get("event") == "HITL_REQUESTED" and e.get("final_decider") == "SYSTEM"
        for e in events
    )
    saw_dec = any(
        e.get("event") == "HITL_DECIDED" and e.get("final_decider") == "USER"
        for e in events
    )
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

    _require_equal(
        out.decision,
        "STOPPED",
        "Overall should be STOPPED if any task is STOPPED",
    )

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
        r.get("event") == "HITL_DECIDED"
        and r.get("reason_code") == "HITL_CONTINUE"
        for r in rows
    )
    artifacts_written = any(r.get("event") == "ARTIFACT_WRITTEN" for r in rows)

    _require(
        rfl_gate,
        "Expected RFL gate to PAUSE_FOR_HITL with REL_BOUNDARY_UNSTABLE",
    )
    _require(hitl_continue, "Expected HITL_CONTINUE decision after RFL HITL")
    _require(
        bool(out.artifacts_written_task_ids),
        "Expected artifacts written after RFL HITL CONTINUE",
    )
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
    _require_equal(
        hit["final_decider"],
        "SYSTEM",
        "Expected SYSTEM final_decider for ethics stop",
    )

    skipped = any(
        e.get("event") == "ARTIFACT_SKIPPED"
        and e.get("layer") == "ethics"
        and e.get("decision") == "STOPPED"
        and e.get("sealed") is True
        and e.get("final_decider") == "SYSTEM"
        for e in rows
    )
    _require(skipped, "Expected ARTIFACT_SKIPPED under ethics with sealed=true")

    _require_equal(
        out.decision,
        "STOPPED",
        "Overall should be STOPPED if any task STOPPED exists",
    )
    _require(
        any(
            task.decision == "STOPPED" and task.blocked_layer == "ethics"
            for task in out.tasks
        ),
        "Expected at least one ethics-blocked task",
    )


def test_consistency_mismatch_continue_enters_regen_pending_and_skips_artifact(
    tmp_path: Path,
) -> None:
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
        for r in rows
    )

    _require(regen_requested, "Expected REGEN_REQUESTED on contract mismatch")
    _require(regen_instructions, "Expected REGEN_INSTRUCTIONS on contract mismatch")
    _require(
        skipped_paused,
        "Expected excel ARTIFACT_SKIPPED with PAUSE_FOR_HITL after regen pending",
    )

    excel_task = _get_task(out, "task_excel")
    _require_equal(
        excel_task.decision,
        "PAUSE_FOR_HITL",
        "Expected excel task to remain paused",
    )
    _require_equal(
        excel_task.blocked_layer,
        "consistency",
        "Expected consistency blocked_layer",
    )
    _require(
        out.decision in ("PAUSE_FOR_HITL", "STOPPED"),
        f"Unexpected overall decision: {out.decision!r}",
    )


def _assert_no_email_like_persisted(root: Path) -> None:
    """Scan all generated text artifacts/logs under root for raw email-like strings."""
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        data = path.read_text(encoding="utf-8", errors="replace")
        _require(
            sim.EMAIL_RE.search(data) is None,
            f"raw email-like string leaked into {path}",
        )
        _require(
            "raw_text" not in data,
            f"raw_text marker leaked into {path}",
        )


def _events_for_task(rows: list[dict[str, Any]], task_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("task_id") == task_id]


def _event_index(events: list[dict[str, Any]], event: str) -> int:
    for i, row in enumerate(events):
        if row.get("event") == event:
            return i
    _fail(f"event not found: {event}")
    return -1


def test_meaning_gate_rejects_alphanumeric_substring_false_positives() -> None:
    """
    English/alphanumeric kind tokens must not match as substrings.
    These were previous regression examples.
    """
    prompt = "documentary wordplay tableau slideware"
    for kind in ("word", "excel", "ppt"):
        decision, layer, reason = sim._meaning_gate(prompt, kind)
        _require_equal(
            decision,
            "RUN",
            f"Expected generic RUN for substring-only prompt kind={kind}",
        )
        _require_equal(layer, None, f"Expected no blocked layer for kind={kind}")
        _require_equal(
            reason,
            "MEANING_GENERIC_ALLOW_ALL",
            f"Expected no kind match for substring-only prompt kind={kind}",
        )


def test_meaning_gate_still_matches_exact_kind_tokens() -> None:
    """
    Boundary matching must not over-harden legitimate exact kind mentions.
    """
    word_decision, _, word_reason = sim._meaning_gate("Create a document.", "word")
    excel_decision, excel_layer, excel_reason = sim._meaning_gate("Create a document.", "excel")

    _require_equal(word_decision, "RUN", "Expected exact document token to match word")
    _require_equal(word_reason, "MEANING_KIND_MATCH", "Expected word kind match")
    _require_equal(
        excel_decision,
        "PAUSE_FOR_HITL",
        "Expected unrelated kind to pause when another kind is mentioned",
    )
    _require_equal(excel_layer, "meaning", "Expected meaning layer pause")
    _require_equal(
        excel_reason,
        "MEANING_KIND_MISSING",
        "Expected missing kind reason",
    )


def test_strict_contract_validation_rejects_invalid_structures() -> None:
    """
    Strict contract validation must reject empty structures, row key drift,
    and nested Excel cell values.
    """
    cases: list[tuple[str, str, dict[str, Any], str]] = [
        ("excel", "empty columns", {"columns": [], "rows": [{"A": 1}]}, "CONTRACT_EXCEL_COLUMNS_INVALID"),
        ("excel", "empty rows", {"columns": ["A"], "rows": []}, "CONTRACT_EXCEL_ROWS_INVALID"),
        ("excel", "row key mismatch", {"columns": ["A"], "rows": [{"B": 1}]}, "CONTRACT_EXCEL_ROW_KEYS_INVALID"),
        ("excel", "nested dict cell", {"columns": ["A"], "rows": [{"A": {"nested": True}}]}, "CONTRACT_EXCEL_CELL_VALUE_INVALID"),
        ("excel", "nested list cell", {"columns": ["A"], "rows": [{"A": [1, 2]}]}, "CONTRACT_EXCEL_CELL_VALUE_INVALID"),
        ("word", "empty headings", {"headings": []}, "CONTRACT_WORD_HEADINGS_INVALID"),
        ("word", "blank heading", {"headings": [""]}, "CONTRACT_WORD_HEADINGS_INVALID"),
        ("ppt", "empty slides", {"slides": []}, "CONTRACT_PPT_SLIDES_INVALID"),
        ("ppt", "blank slide", {"slides": [""]}, "CONTRACT_PPT_SLIDES_INVALID"),
    ]

    for kind, label, draft, expected_reason in cases:
        ok, reason = sim._validate_contract(kind, draft)
        _require(ok is False, f"Expected invalid contract for {label}")
        _require_equal(reason, expected_reason, f"Unexpected reason for {label}")


def test_strict_contract_validation_accepts_valid_structures() -> None:
    valid_cases: list[tuple[str, dict[str, Any]]] = [
        (
            "excel",
            {
                "columns": ["A", "B"],
                "rows": [
                    {"A": "x", "B": 1},
                    {"A": None, "B": False},
                ],
            },
        ),
        ("word", {"headings": ["Title"]}),
        ("ppt", {"slides": ["Title"]}),
    ]
    for kind, draft in valid_cases:
        ok, reason = sim._validate_contract(kind, draft)
        _require(ok is True, f"Expected valid contract for kind={kind}")
        _require_equal(reason, "CONTRACT_OK", f"Unexpected reason for kind={kind}")


def test_artifact_path_traversal_is_rejected(tmp_path: Path) -> None:
    """
    Artifact writing must reject path traversal task IDs and not create outside files.
    """
    artifact_dir = tmp_path / "artifacts"
    outside = tmp_path / "outside" / "pwned.xlsx.txt"

    try:
        sim._write_artifact(artifact_dir, "../outside/pwned", "excel", "safe")
    except ValueError as exc:
        _require(
            "unsafe task_id" in str(exc) or "escapes" in str(exc),
            "Expected unsafe task/path error",
        )
    else:
        _fail("Expected ValueError for path traversal task_id")

    _require(not outside.exists(), "Path traversal created outside artifact file")


def test_artifact_write_redacts_email_and_stays_inside_root(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    path = sim._write_artifact(
        artifact_dir,
        "safe_task",
        "word",
        "Contact: test.user+demo@example.com",
    )
    _require(path.exists(), "Expected artifact to be written")
    _require(
        path.resolve().is_relative_to(artifact_dir.resolve()),
        "Expected artifact to remain inside artifact_dir",
    )
    content = path.read_text(encoding="utf-8")
    _require("@" not in content, "Expected redacted artifact content")
    _require("<REDACTED_EMAIL>" in content, "Expected redaction marker in artifact")


def test_break_contract_and_email_leak_stops_at_ethics_before_consistency(tmp_path: Path) -> None:
    """
    PII must not be masked by consistency failure.
    break_contract + leak_email must classify as STOPPED / ethics.
    """
    paths = _audit_paths(tmp_path)
    out = _run(
        tmp_path=tmp_path,
        prompt="ドキュメントを作ってください。",
        run_id="TEST#ETHICS_BEFORE_CONSISTENCY",
        hitl_choice="CONTINUE",
        faults={
            "word": {"break_contract": True, "leak_email": True},
            "excel": {},
            "ppt": {},
        },
        truncate=True,
    )

    word_task = _get_task(out, "task_word")
    _require_equal(word_task.decision, "STOPPED", "Expected word task STOPPED")
    _require_equal(word_task.blocked_layer, "ethics", "Expected ethics blocked layer")
    _require_equal(
        word_task.reason_code,
        "ETHICS_EMAIL_DETECTED",
        "Expected ethics email reason",
    )

    rows = _read_jsonl(paths["audit"])
    word_events = _events_for_task(rows, "task_word")
    _require(
        any(
            row.get("event") == "GATE_ETHICS"
            and row.get("decision") == "STOPPED"
            and row.get("sealed") is True
            for row in word_events
        ),
        "Expected sealed ethics STOPPED event for task_word",
    )
    _require(
        not any(row.get("event") == "GATE_CONSISTENCY" for row in word_events),
        "GATE_CONSISTENCY should not run after ethics PII preflight STOP",
    )
    _assert_no_email_like_persisted(tmp_path / "out")


def test_auditlog_write_failures_are_no_raise_and_observable(tmp_path: Path) -> None:
    """
    AuditLog intentionally does not raise on I/O failure, but the failure must be observable.
    """
    audit_path = tmp_path / "audit_as_directory.jsonl"
    audit_path.mkdir()
    audit = sim.AuditLog(audit_path)

    audit.start_run(truncate=True)
    audit.emit(
        {
            "run_id": "AUDIT#FAIL",
            "task_id": "task_x",
            "event": "WRITE_FAIL",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
        }
    )

    _require(audit.audit_health.write_failed is True, "Expected audit write failure flag")
    _require(audit.audit_health.failure_count >= 1, "Expected failure_count >= 1")
    _require(
        audit.audit_health.last_error_type in ("IsADirectoryError", "PermissionError", "OSError"),
        f"Unexpected error type: {audit.audit_health.last_error_type!r}",
    )


def test_run_simulation_exposes_audit_health_on_audit_failure(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit_dir.jsonl"
    audit_path.mkdir()
    result = sim.run_simulation(
        prompt="ドキュメントを作ってください。",
        run_id="TEST#AUDIT_HEALTH",
        audit_path=str(audit_path),
        artifact_dir=str(tmp_path / "artifacts"),
        truncate_audit_on_start=True,
        hitl_resolver=None,
    )
    _require(result.audit_health.write_failed is True, "Expected result audit health failure")
    _require(result.audit_health.failure_count >= 1, "Expected observable failure count")


def test_redaction_key_collision_preserves_all_entries(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit_collision.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)
    audit.emit(
        {
            "run_id": "T#COLLISION",
            "task_id": "task_x",
            "event": "COLLISION",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "evidence": {
                "a@example.com": "value-a",
                "b@example.com": "value-b",
            },
        }
    )
    rows = _read_jsonl(audit_path)
    _require_equal(len(rows), 1, "Expected one audit row")
    evidence = rows[0].get("evidence")
    _require(isinstance(evidence, dict), "Expected evidence mapping")
    _require("<REDACTED_EMAIL>" in evidence, "Expected first redacted key")
    _require("<REDACTED_EMAIL>#2" in evidence, "Expected collision-preserved key")
    _require_equal(evidence["<REDACTED_EMAIL>"], "value-a", "Expected first value")
    _require_equal(evidence["<REDACTED_EMAIL>#2"], "value-b", "Expected second value")
    _require("@" not in _blob(rows), "Expected no raw email-like key")


def test_hitl_resolver_invalid_return_and_exception_fail_closed(tmp_path: Path) -> None:
    paths = _audit_paths(tmp_path)

    def invalid_resolver(
        _run_id: str,
        _task_id: str,
        _layer: str,
        _reason_code: str,
    ) -> Any:
        return "MAYBE"

    result_invalid = sim.run_simulation(
        prompt="Excelの表を作ってください。",
        run_id="TEST#HITL_INVALID",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=invalid_resolver,
    )
    rows_invalid = _read_jsonl(paths["audit"])
    _require_equal(result_invalid.decision, "STOPPED", "Expected invalid resolver STOPPED")
    _require(
        any(row.get("event") == "HITL_RESOLVER_FAILED" for row in rows_invalid),
        "Expected HITL_RESOLVER_FAILED for invalid resolver",
    )

    def exception_resolver(
        _run_id: str,
        _task_id: str,
        _layer: str,
        _reason_code: str,
    ) -> sim.HitlChoice:
        raise RuntimeError("do not persist this detail")

    result_exception = sim.run_simulation(
        prompt="Excelの表を作ってください。",
        run_id="TEST#HITL_EXCEPTION",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=exception_resolver,
    )
    rows_exception = _read_jsonl(paths["audit"])
    _require_equal(result_exception.decision, "STOPPED", "Expected exception resolver STOPPED")
    _require(
        any(
            row.get("event") == "HITL_RESOLVER_FAILED"
            and row.get("error_type") == "RuntimeError"
            for row in rows_exception
        ),
        "Expected RuntimeError type without raw exception detail",
    )
    _require(
        "do not persist this detail" not in _blob(rows_exception),
        "Raw exception message should not persist",
    )


def test_hitl_resolver_none_fails_closed_without_artifacts_for_stopped_tasks(tmp_path: Path) -> None:
    paths = _audit_paths(tmp_path)
    result = sim.run_simulation(
        prompt="Excelの表を作ってください。",
        run_id="TEST#HITL_NONE",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=None,
    )
    _require_equal(result.decision, "STOPPED", "Expected None resolver to fail closed")
    rows = _read_jsonl(paths["audit"])
    _require(
        any(
            row.get("event") == "HITL_DECIDED"
            and row.get("decision") == "STOPPED"
            and row.get("reason_code") == "HITL_STOP"
            for row in rows
        ),
        "Expected HITL_STOP decision for None resolver",
    )


def test_long_audit_non_structural_fields_are_truncated(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit_long.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)
    long_note = "X" * (sim.MAX_AUDIT_STRING_LENGTH + 5000)
    long_run_id = "RUN-" + ("Y" * (sim.MAX_AUDIT_STRING_LENGTH + 10))
    audit.emit(
        {
            "run_id": long_run_id,
            "task_id": "task_x",
            "event": "LONG_FIELD",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "note": long_note,
        }
    )
    rows = _read_jsonl(audit_path)
    _require_equal(len(rows), 1, "Expected one audit row")
    _require_equal(rows[0]["run_id"], long_run_id, "Structural run_id should not truncate")
    note = rows[0].get("note")
    _require(isinstance(note, str), "Expected note string")
    _require(sim.TRUNCATION_MARKER in note, "Expected truncation marker")
    _require(len(note) < len(long_note), "Expected shorter truncated note")


def test_rfl_continue_event_order_runs_ethics_acc_before_dispatch(tmp_path: Path) -> None:
    paths = _audit_paths(tmp_path)
    out = _run(
        tmp_path=tmp_path,
        prompt="おすすめはどっち？",
        run_id="TEST#RFL_ORDER",
        hitl_choice="CONTINUE",
        truncate=True,
    )
    _require(bool(out.artifacts_written_task_ids), "Expected artifacts after RFL CONTINUE")
    rows = _read_jsonl(paths["audit"])

    for task_id in ("task_word", "task_excel", "task_ppt"):
        events = _events_for_task(rows, task_id)
        rfl_i = _event_index(events, "GATE_RFL")
        req_i = _event_index(events, "HITL_REQUESTED")
        dec_i = _event_index(events, "HITL_DECIDED")
        ethics_i = _event_index(events, "GATE_ETHICS")
        acc_i = _event_index(events, "GATE_ACC")
        write_i = _event_index(events, "ARTIFACT_WRITTEN")
        _require(
            rfl_i < req_i < dec_i < ethics_i < acc_i < write_i,
            f"Unexpected RFL/HITL/Ethics/ACC/Dispatch order for {task_id}",
        )


def test_overall_policy_iep_and_legacy_compatibility(tmp_path: Path) -> None:
    paths = _audit_paths(tmp_path)

    run_all = sim.run_simulation(
        prompt="ドキュメントを作ってください。",
        run_id="TEST#OVERALL_RUN",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=None,
        overall_policy="iep",
    )
    _require_equal(run_all.decision, "RUN", "Expected all-run IEP decision")

    def continue_resolver(
        _run_id: str,
        _task_id: str,
        _layer: str,
        _reason_code: str,
    ) -> sim.HitlChoice:
        return "CONTINUE"

    run_pause_iep = sim.run_simulation(
        prompt="ドキュメントを作ってください。",
        run_id="TEST#OVERALL_PAUSE_IEP",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        faults={"excel": {"break_contract": True}},
        truncate_audit_on_start=True,
        hitl_resolver=continue_resolver,
        overall_policy="iep",
    )
    _require_equal(
        run_pause_iep.decision,
        "PAUSE_FOR_HITL",
        "Expected paused IEP decision",
    )

    run_pause_legacy = sim.run_simulation(
        prompt="ドキュメントを作ってください。",
        run_id="TEST#OVERALL_PAUSE_LEGACY",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        faults={"excel": {"break_contract": True}},
        truncate_audit_on_start=True,
        hitl_resolver=continue_resolver,
        overall_policy="legacy",
    )
    _require_equal(run_pause_legacy.decision, "HITL", "Expected legacy HITL decision")

    run_stop_iep = sim.run_simulation(
        prompt="ドキュメントを作ってください。",
        run_id="TEST#OVERALL_STOP_IEP",
        audit_path=str(paths["audit"]),
        artifact_dir=str(paths["artifacts"]),
        faults={"word": {"leak_email": True}},
        truncate_audit_on_start=True,
        hitl_resolver=continue_resolver,
        overall_policy="iep",
    )
    _require_equal(run_stop_iep.decision, "STOPPED", "Expected stopped IEP decision")

