# tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
# -*- coding: utf-8 -*-
"""
Regression tests for ai_doc_orchestrator_kage3_v1_2_4

Key goals:
- audit.emit() auto-fills ts
- deep redaction: redact BOTH dict keys and values (email-like keys must not persist)
- HITL firepoints observable: HITL_REQUESTED / HITL_DECIDED with ARL-min fields
- RFL gate triggers HITL; CONTINUE allows dispatch
- Ethics email leak is SEALED and never persists '@' in logs
- Consistency mismatch => regen pending + artifact skipped
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure repository root is importable under pytest/CI cwd differences.
_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests/.. (repo root)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import ai_doc_orchestrator_kage3_v1_2_4 as sim


# -----------------------
# helpers
# -----------------------
def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _blob(rows: list[dict]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)


def _find(rows: list[dict], **conds) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        ok = True
        for k, v in conds.items():
            if r.get(k) != v:
                ok = False
                break
        if ok:
            out.append(r)
    return out


def _assert_arl_min_keys(row: dict) -> None:
    # ARL minimal keys (as per your IEP alignment)
    for k in (
        "run_id",
        "ts",
        "layer",
        "decision",
        "reason_code",
        "sealed",
        "overrideable",
        "final_decider",
    ):
        assert k in row, f"missing key: {k}"


# -----------------------
# tests
# -----------------------
def test_audit_emit_autofills_ts_and_redacts_keys_and_values(tmp_path: Path):
    """
    v1.2.4 key guarantee:
    - emit() must auto-fill ts
    - deep redaction must redact BOTH dict keys and values (email-like keys must not persist)
    """
    audit_path = tmp_path / "audit.jsonl"
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
            "evidence": {
                "test.user@example.com": "contact=test.user@example.com",
                "nested": {"k": "demo@example.com"},
            },
        }
    )

    rows = _read_jsonl(audit_path)
    assert len(rows) == 1
    assert "ts" in rows[0] and isinstance(rows[0]["ts"], str) and rows[0]["ts"]

    blob = _blob(rows)
    assert "@" not in blob
    assert "<REDACTED_EMAIL>" in blob


def test_audit_default_str_prevents_crash_on_non_json_types(tmp_path: Path):
    """
    v1.2.4 guarantee:
    - audit must never crash if row includes non-JSON-serializable objects
    """
    audit_path = tmp_path / "audit.jsonl"
    audit = sim.AuditLog(audit_path)
    audit.start_run(truncate=True)

    class NonJson:
        def __str__(self) -> str:
            return "NONJSON"

    audit.emit(
        {
            "run_id": "T#A2",
            "task_id": "task_x",
            "event": "NONJSON",
            "layer": "orchestrator",
            "decision": "RUN",
            "reason_code": "RC",
            "obj": NonJson(),
        }
    )

    rows = _read_jsonl(audit_path)
    assert len(rows) == 1
    assert rows[0]["obj"] == "NONJSON"


def test_hitl_firepoint_events_and_arl_fields_present(tmp_path: Path):
    """
    Core: HITL firepoint must be observable in logs:
    - HITL_REQUESTED (SYSTEM, PAUSE_FOR_HITL, overrideable=True, sealed=False)
    - HITL_DECIDED (USER, RUN or STOPPED, overrideable=False, sealed=False)
    and ARL-min fields must exist.
    """
    audit_path = tmp_path / "audit.jsonl"
    art_dir = tmp_path / "artifacts"

    # Prompt mentions only Excel => word/ppt meaning gate should HITL.
    def resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> sim.HitlChoice:
        return "STOP"

    res = sim.run_simulation(
        prompt="Excelの表を作って",
        run_id="T#HITL",
        audit_path=str(audit_path),
        artifact_dir=str(art_dir),
        truncate_audit_on_start=True,
        hitl_resolver=resolver,
    )

    rows = _read_jsonl(audit_path)
    reqs = _find(rows, event="HITL_REQUESTED")
    decs = _find(rows, event="HITL_DECIDED")

    assert reqs, "HITL_REQUESTED not found"
    assert decs, "HITL_DECIDED not found"

    _assert_arl_min_keys(reqs[0])
    _assert_arl_min_keys(decs[0])

    assert reqs[0]["decision"] == "PAUSE_FOR_HITL"
    assert reqs[0]["final_decider"] == "SYSTEM"
    assert reqs[0]["overrideable"] is True
    assert reqs[0]["sealed"] is False

    assert decs[0]["final_decider"] == "USER"
    assert decs[0]["overrideable"] is False
    assert decs[0]["sealed"] is False

    assert any(t.decision == "STOPPED" and t.blocked_layer == "meaning" for t in res.tasks)


def test_rfl_gate_triggers_hitl_and_continue_allows_dispatch(tmp_path: Path):
    """
    RFL:
    - prompt containing relative boundary triggers should cause PAUSE_FOR_HITL at layer=rfl
    - if HITL CONTINUE, dispatch can proceed and artifacts can be written
    """
    audit_path = tmp_path / "audit.jsonl"
    art_dir = tmp_path / "artifacts"

    prompt = "WordとExcelとPPTを作って。どっちがいい？"

    res = sim.run_simulation(
        prompt=prompt,
        run_id="T#RFL",
        audit_path=str(audit_path),
        artifact_dir=str(art_dir),
        truncate_audit_on_start=True,
        hitl_resolver=lambda *_: "CONTINUE",
    )

    rows = _read_jsonl(audit_path)

    rfl_gate = [
        r
        for r in rows
        if r.get("event") == "GATE_RFL" and r.get("decision") == "PAUSE_FOR_HITL"
    ]
    assert rfl_gate, "RFL gate did not trigger PAUSE_FOR_HITL"

    assert any(r.get("event") == "HITL_REQUESTED" and r.get("layer") == "rfl" for r in rows)

    assert res.artifacts_written_task_ids, "No artifacts were written after HITL_CONTINUE"


def test_ethics_violation_is_sealed_and_no_email_persists_in_logs(tmp_path: Path):
    """
    Ethics:
    - If raw_text contains email, GATE_ETHICS must STOPPED with sealed=True and final_decider=SYSTEM.
    - Logs must never persist '@' anywhere.
    """
    audit_path = tmp_path / "audit.jsonl"
    art_dir = tmp_path / "artifacts"

    res = sim.run_simulation(
        prompt="WordとExcelとPPTを作って",
        run_id="T#PII",
        audit_path=str(audit_path),
        artifact_dir=str(art_dir),
        truncate_audit_on_start=True,
        faults={"word": {"leak_email": True}},  # only word leaks email in raw_text
        hitl_resolver=lambda *_: "CONTINUE",
    )

    rows = _read_jsonl(audit_path)

    ethics_rows = [
        r
        for r in rows
        if r.get("event") == "GATE_ETHICS" and r.get("decision") == "STOPPED"
    ]
    assert ethics_rows, "No STOPPED GATE_ETHICS found"

    hit = ethics_rows[0]
    _assert_arl_min_keys(hit)
    assert hit["sealed"] is True
    assert hit["overrideable"] is False
    assert hit["final_decider"] == "SYSTEM"
    assert hit["reason_code"] == "ETHICS_EMAIL_DETECTED"

    # Ensure at least one task is STOPPED due to ethics
    assert any(t.decision == "STOPPED" and t.blocked_layer == "ethics" for t in res.tasks)

    # Hard guarantee: no email-like strings in logs
    assert "@" not in _blob(rows)


def test_consistency_mismatch_continue_enters_regen_pending_and_skips_artifact(tmp_path: Path):
    """
    Consistency:
    - If contract mismatch occurs, system raises HITL, and on CONTINUE it must:
      - emit REGEN_REQUESTED + REGEN_INSTRUCTIONS
      - keep task as PAUSE_FOR_HITL and skip artifact
    """
    audit_path = tmp_path / "audit.jsonl"
    art_dir = tmp_path / "artifacts"

    # break_contract on excel -> mismatch at consistency
    res = sim.run_simulation(
        prompt="WordとExcelとPPTを作って",
        run_id="T#CONS",
        audit_path=str(audit_path),
        artifact_dir=str(art_dir),
        truncate_audit_on_start=True,
        faults={"excel": {"break_contract": True}},
        hitl_resolver=lambda *_: "CONTINUE",
    )

    rows = _read_jsonl(audit_path)

    assert any(
        (r.get("task_id") == "task_excel" and r.get("event") == "REGEN_REQUESTED")
        for r in rows
    )
    assert any(
        (r.get("task_id") == "task_excel" and r.get("event") == "REGEN_INSTRUCTIONS")
        for r in rows
    )

    excel_skips = [
        r
        for r in rows
        if r.get("task_id") == "task_excel"
        and r.get("event") == "ARTIFACT_SKIPPED"
        and r.get("decision") == "PAUSE_FOR_HITL"
    ]
    assert excel_skips, "Expected excel ARTIFACT_SKIPPED with PAUSE_FOR_HITL after regen pending"

    excel_tr = next(t for t in res.tasks if t.task_id == "task_excel")
    assert excel_tr.decision == "PAUSE_FOR_HITL"
    assert excel_tr.blocked_layer == "consistency"
