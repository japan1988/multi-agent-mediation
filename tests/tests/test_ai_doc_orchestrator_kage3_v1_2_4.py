# tests/test_ai_doc_orchestrator_kage3_v1_2_4.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

import ai_doc_orchestrator_kage3_v1_2_4 as sim


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
        # fail-closed behavior in code is STOP when resolver=None,
        # but for deterministic tests we supply a resolver explicitly.
        assert hitl_choice in ("CONTINUE", "STOP")
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


def _assert_no_at_sign_persisted(audit_path: Path) -> None:
    # Hard invariant: no email-like '@' in persisted logs (values OR keys).
    txt = audit_path.read_text(encoding="utf-8", errors="replace") if audit_path.exists() else ""
    assert "@" not in txt, f"PII-like token '@' leaked into audit log: {audit_path}"


def _assert_arl_minimal_keys(events: List[Dict[str, Any]]) -> None:
    must = {"sealed", "overrideable", "final_decider"}
    for i, e in enumerate(events):
        missing = must.difference(e.keys())
        assert not missing, f"ARL minimal keys missing at row#{i}: {missing} (event={e.get('event')})"


def _assert_decision_vocab(events: List[Dict[str, Any]]) -> None:
    allowed = {"RUN", "PAUSE_FOR_HITL", "STOPPED"}
    for i, e in enumerate(events):
        d = e.get("decision")
        assert isinstance(d, str), f"decision is not str at row#{i}: {d!r}"
        assert d in allowed, f"decision vocab mismatch at row#{i}: {d!r}"


# ----------------------------
# Tests: HITL semantics (post-HITL defined)
# ----------------------------
def test_meaning_hitl_continue_propagates_and_writes_artifacts(tmp_path: Path):
    """
    Trigger meaning HITL for some kinds (prompt mentions only Excel),
    choose CONTINUE, and confirm artifacts are written for non-blocked tasks.

    Expected:
    - word/ppt tasks: meaning gate => PAUSE_FOR_HITL => CONTINUE => proceed => RUN => artifact written
    - excel task: meaning gate => RUN (kind match)
    - No '@' in logs
    - ARL minimal keys exist for all events
    """
    paths = _audit_paths(tmp_path)

    # Mentions Excel tokens only -> word/ppt meaning gate should HITL
    prompt = "Excelで表を作ってください。"
    out = _run(tmp_path=tmp_path, prompt=prompt, run_id="TEST#MEANING_CONTINUE", hitl_choice="CONTINUE", truncate=True)

    assert out.run_id == "TEST#MEANING_CONTINUE"
    assert out.decision in ("RUN", "PAUSE_FOR_HITL", "STOPPED")

    # At least one artifact should be written in this scenario (no ethics stop, no rfl hit).
    assert out.artifacts_written_task_ids, "Expected some artifacts to be written after HITL CONTINUE."

    events = _read_jsonl(paths["audit"])
    assert events, "Audit log should not be empty."

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    # Confirm HITL firepoint exists (REQUESTED by SYSTEM, DECIDED by USER)
    saw_req = any(e.get("event") == "HITL_REQUESTED" and e.get("final_decider") == "SYSTEM" for e in events)
    saw_dec = any(e.get("event") == "HITL_DECIDED" and e.get("final_decider") == "USER" for e in events)
    assert saw_req, "Missing HITL_REQUESTED (SYSTEM) event."
    assert saw_dec, "Missing HITL_DECIDED (USER) event."

    # Confirm some artifacts written events exist
    saw_written = any(e.get("event") == "ARTIFACT_WRITTEN" for e in events)
    assert saw_written, "Expected ARTIFACT_WRITTEN events after HITL CONTINUE."


def test_meaning_hitl_stop_blocks_tasks_and_skips_artifacts(tmp_path: Path):
    """
    Trigger meaning HITL (prompt mentions only Excel), choose STOP.
    Expected:
    - word/ppt tasks stop at meaning with ARTIFACT_SKIPPED + decision STOPPED
    - excel may still run (meaning ok), but overall decision becomes STOPPED because any STOPPED exists
    """
    paths = _audit_paths(tmp_path)

    prompt = "Excelで表を作ってください。"
    out = _run(tmp_path=tmp_path, prompt=prompt, run_id="TEST#MEANING_STOP", hitl_choice="STOP", truncate=True)

    assert out.decision == "STOPPED", "Overall should be STOPPED if any task is STOPPED."

    events = _read_jsonl(paths["audit"])
    assert events, "Audit log should not be empty."

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    # Verify user STOP trace exists
    assert any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in events
    ), "Missing post-HITL STOP trace (HITL_DECIDED USER -> STOPPED)."

    # Verify artifacts were skipped for STOP path
    assert any(e.get("event") == "ARTIFACT_SKIPPED" and e.get("decision") == "STOPPED" for e in events), (
        "Expected ARTIFACT_SKIPPED with STOPPED decision in STOP path."
    )


def test_rfl_hitl_continue_allows_dispatch(tmp_path: Path):
    """
    Trigger RFL HITL without triggering meaning HITL by using a generic prompt (no kind tokens),
    and include a relativity trigger ("おすすめ") to fire REL_BOUNDARY_UNSTABLE.

    Expected:
    - meaning gate: generic allow all
    - consistency ok
    - rfl gate: PAUSE_FOR_HITL with reason_code REL_BOUNDARY_UNSTABLE
    - CONTINUE -> proceed to dispatch -> artifacts written
    """
    paths = _audit_paths(tmp_path)

    prompt = "おすすめはどっち？"  # RFL trigger, no explicit kind tokens -> meaning generic allow all
    out = _run(tmp_path=tmp_path, prompt=prompt, run_id="TEST#RFL_CONTINUE", hitl_choice="CONTINUE", truncate=True)

    events = _read_jsonl(paths["audit"])
    assert events, "Audit log should not be empty."

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    assert any(
        e.get("event") == "GATE_RFL"
        and e.get("decision") == "PAUSE_FOR_HITL"
        and e.get("reason_code") == "REL_BOUNDARY_UNSTABLE"
        for e in events
    ), "Expected RFL gate to PAUSE_FOR_HITL with REL_BOUNDARY_UNSTABLE."

    assert any(e.get("event") == "HITL_DECIDED" and e.get("reason_code") == "HITL_CONTINUE" for e in events), (
        "Expected HITL_CONTINUE decision after RFL HITL."
    )

    assert out.artifacts_written_task_ids, "Expected artifacts written after RFL HITL CONTINUE."
    assert any(e.get("event") == "ARTIFACT_WRITTEN" for e in events), "Expected ARTIFACT_WRITTEN after CONTINUE."


def test_rfl_hitl_stop_blocks_dispatch(tmp_path: Path):
    """
    Same as above but STOP.
    Expected:
    - after RFL HITL STOP -> ARTIFACT_SKIPPED STOPPED
    - overall STOPPED
    """
    paths = _audit_paths(tmp_path)

    prompt = "おすすめはどっち？"
    out = _run(tmp_path=tmp_path, prompt=prompt, run_id="TEST#RFL_STOP", hitl_choice="STOP", truncate=True)

    assert out.decision == "STOPPED"

    events = _read_jsonl(paths["audit"])
    assert events, "Audit log should not be empty."

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    assert any(
        e.get("event") == "HITL_DECIDED"
        and e.get("final_decider") == "USER"
        and e.get("reason_code") == "HITL_STOP"
        and e.get("decision") == "STOPPED"
        for e in events
    ), "Missing HITL_STOP trace at RFL path."


# ----------------------------
# Tests: Ethics sealing (PII in raw_text must never persist)
# ----------------------------
def test_ethics_email_detected_seals_and_never_persists_at_sign(tmp_path: Path):
    """
    Force agent raw_text to include an email by fault injection on a single kind.
    Expected:
    - ethics gate emits STOPPED with sealed=true, final_decider=SYSTEM
    - ARTIFACT_SKIPPED for that task
    - persisted audit log contains no '@'
    """
    paths = _audit_paths(tmp_path)

    # Avoid meaning HITL: keep prompt generic (no kind tokens), and avoid RFL triggers.
    prompt = "ドキュメントを作ってください。"

    faults = {
        "word": {"leak_email": True},  # raw_text gets test.user+demo@example.com
        "excel": {"leak_email": False},
        "ppt": {"leak_email": False},
    }

    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#ETHICS_SEAL",
        hitl_choice="CONTINUE",  # irrelevant; ethics is SYSTEM-sealed
        faults=faults,
        truncate=True,
    )

    events = _read_jsonl(paths["audit"])
    assert events, "Audit log should not be empty."

    # Hard guarantee: no '@' persisted
    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    # Verify sealed STOP at ethics for at least one task
    assert any(
        e.get("event") == "GATE_ETHICS"
        and e.get("decision") == "STOPPED"
        and e.get("sealed") is True
        and e.get("final_decider") == "SYSTEM"
        and e.get("reason_code") == "ETHICS_EMAIL_DETECTED"
        for e in events
    ), "Expected sealed ethics STOPPED event for email leak."

    # Verify artifact skipped due to ethics
    assert any(
        e.get("event") == "ARTIFACT_SKIPPED"
        and e.get("layer") == "ethics"
        and e.get("decision") == "STOPPED"
        and e.get("sealed") is True
        and e.get("final_decider") == "SYSTEM"
        for e in events
    ), "Expected ARTIFACT_SKIPPED under ethics with sealed=true."

    # Overall should be STOPPED if any task STOPPED exists
    assert out.decision == "STOPPED"


# ----------------------------
# Tests: AuditLog (deep redaction includes dict keys + defensive JSON)
# ----------------------------
def test_auditlog_deep_redacts_dict_keys_and_values(tmp_path: Path):
    """
    Directly validate v1.2.4 critical fix:
    - Deep redaction includes dict keys, not only values.
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
        # email-like KEY (must not persist)
        "user@example.com": "ok",
        # email-like VALUE (must not persist)
        "note": "contact me at admin@example.com",
    }
    audit.emit(row)

    txt = audit_path.read_text(encoding="utf-8")
    assert "@" not in txt, "Expected no '@' in persisted log even when dict KEY contains email-like token."
    assert "<REDACTED_EMAIL>" in txt, "Expected redaction marker to appear in persisted log."


def test_auditlog_defensive_json_serialization_does_not_crash(tmp_path: Path):
    """
    Defensive JSON serialization: default=str should prevent audit.emit crashing on non-JSON types.
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
        "non_json": {"a_set": {1, 2, 3}},  # set is not JSON-serializable
    }
    audit.emit(row)

    events = _read_jsonl(audit_path)
    assert len(events) == 1
    assert "non_json" in events[0]
    # default=str will convert set to a string representation
    assert isinstance(events[0]["non_json"]["a_set"], str)


def test_start_run_truncate_and_ts_monotonicity(tmp_path: Path):
    """
    Validates:
    - start_run(truncate=True) actually truncates
    - per-run ts monotonicity holds (microseconds)
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
    assert len(rows_a) == 2
    assert rows_a[0]["ts"] < rows_a[1]["ts"], "Expected monotonic ts within a run."

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
    assert len(rows_b) == 1, "Expected truncate=True to reset file content."
    assert rows_b[0]["run_id"] == "B"


# ----------------------------
# Optional: Contract mismatch path (consistency HITL) sanity
# ----------------------------
def test_consistency_mismatch_continue_results_in_pause_for_hitl_and_skips_artifact(tmp_path: Path):
    """
    If break_contract=True, consistency gate should PAUSE_FOR_HITL.
    If user CONTINUE, this prototype logs regen requests and keeps task in PAUSE_FOR_HITL,
    and must NOT write an artifact for that task.
    """
    paths = _audit_paths(tmp_path)

    prompt = "ドキュメントを作ってください。"  # meaning generic allow all, no RFL trigger
    faults = {
        "excel": {"break_contract": True},
        "word": {"break_contract": False},
        "ppt": {"break_contract": False},
    }
    out = _run(
        tmp_path=tmp_path,
        prompt=prompt,
        run_id="TEST#CONSISTENCY_CONTINUE",
        hitl_choice="CONTINUE",
        faults=faults,
        truncate=True,
    )

    events = _read_jsonl(paths["audit"])
    assert events

    _assert_no_at_sign_persisted(paths["audit"])
    _assert_arl_minimal_keys(events)
    _assert_decision_vocab(events)

    # Expect REGEN_REQUESTED / ARTIFACT_SKIPPED with PAUSE_FOR_HITL for the broken contract task
    assert any(e.get("event") == "REGEN_REQUESTED" for e in events), "Expected REGEN_REQUESTED on contract mismatch."
    assert any(
        e.get("event") == "ARTIFACT_SKIPPED" and e.get("decision") == "PAUSE_FOR_HITL" for e in events
    ), "Expected ARTIFACT_SKIPPED with PAUSE_FOR_HITL on contract mismatch CONTINUE path."

    # Overall decision should be PAUSE_FOR_HITL (since at least one task is PAUSE_FOR_HITL, and no STOPPED necessarily)
    assert out.decision in ("PAUSE_FOR_HITL", "STOPPED")
