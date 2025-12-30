# tests/test_ai_doc_orchestrator_kage3_v1_2_4_regression.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

import ai_doc_orchestrator_kage3_v1_2_4 as sim


# ----------------------------
# Helpers
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


def _paths(tmp_path: Path) -> Dict[str, Path]:
    return {
        "audit": tmp_path / "out" / "audit_v1_2_4.jsonl",
        "artifacts": tmp_path / "out" / "artifacts_v1_2_4",
    }


def _resolver_map(map_: Dict[str, str]):
    """
    map_ example:
      {"meaning": "STOP", "rfl": "CONTINUE", "consistency": "CONTINUE"}
    """
    def _resolver(run_id: str, task_id: str, layer: str, reason_code: str) -> str:
        return map_.get(layer, "STOP")  # fail-closed default
    return _resolver


def _assert_arl_min_fields(rows: List[Dict[str, Any]]) -> None:
    # IEP/ARL minimal keys must exist for every emitted row
    for r in rows:
        assert "sealed" in r
        assert "overrideable" in r
        assert "final_decider" in r


def _assert_no_email_persisted(blob: str) -> None:
    # strict: nothing that looks like an email should persist
    assert sim.EMAIL_RE.search(blob) is None
    # pragmatic extra guard (covers key/value too)
    assert "@" not in blob


# ----------------------------
# Regression tests
# ----------------------------
def test_meaning_gate_hitl_stop_blocks_only_mismatched_kinds(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    res = sim.run_simulation(
        prompt="Wordを作って。",  # mentions one kind only => others hit Meaning HITL
        run_id="TEST#MEANING_HITL_STOP",
        audit_path=str(p["audit"]),
        artifact_dir=str(p["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=_resolver_map({"meaning": "STOP"}),
    )

    # task_word should RUN; excel/ppt should STOPPED due to Meaning HITL stop
    by_id = {t.task_id: t for t in res.tasks}
    assert by_id["task_word"].decision == "RUN"
    assert by_id["task_excel"].decision == "STOPPED"
    assert by_id["task_ppt"].decision == "STOPPED"
    assert by_id["task_excel"].blocked_layer == "meaning"
    assert by_id["task_ppt"].blocked_layer == "meaning"

    # artifacts: only word should be written
    assert set(res.artifacts_written_task_ids) == {"task_word"}
    assert (p["artifacts"] / "task_word.docx.txt").exists()
    assert not (p["artifacts"] / "task_excel.xlsx.txt").exists()
    assert not (p["artifacts"] / "task_ppt.pptx.txt").exists()

    rows = _read_jsonl(p["audit"])
    _assert_arl_min_fields(rows)

    # Must contain HITL_REQUESTED + HITL_DECIDED for excel/ppt meaning
    hitl_req = [r for r in rows if r.get("event") == "HITL_REQUESTED" and r.get("layer") == "meaning"]
    hitl_dec = [r for r in rows if r.get("event") == "HITL_DECIDED" and r.get("layer") == "hitl_finalize"]
    assert len(hitl_req) >= 2
    assert len(hitl_dec) >= 2

    # Requested must be overrideable and not sealed (SYSTEM)
    for r in hitl_req:
        assert r["decision"] == "PAUSE_FOR_HITL"
        assert r["sealed"] is False
        assert r["overrideable"] is True
        assert r["final_decider"] == "SYSTEM"

    # Decided must be USER and non-overrideable
    for r in hitl_dec:
        assert r["sealed"] is False
        assert r["overrideable"] is False
        assert r["final_decider"] == "USER"


def test_rfl_gate_hitl_continue_allows_dispatch(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    res = sim.run_simulation(
        prompt="WordとExcelとPPTを作って。どっちがいい？",  # RFL trigger: どっち
        run_id="TEST#RFL_HITL_CONTINUE",
        audit_path=str(p["audit"]),
        artifact_dir=str(p["artifacts"]),
        truncate_audit_on_start=True,
        hitl_resolver=_resolver_map({"rfl": "CONTINUE"}),
    )

    # All tasks should RUN and write artifacts
    assert res.decision == "RUN"
    assert set(res.artifacts_written_task_ids) == {"task_word", "task_excel", "task_ppt"}

    rows = _read_jsonl(p["audit"])
    _assert_arl_min_fields(rows)

    # RFL gate should request HITL, and then user CONTINUE is recorded
    rfl_gate_rows = [r for r in rows if r.get("event") == "GATE_RFL"]
    assert rfl_gate_rows, "GATE_RFL must be emitted"
    assert any(r["decision"] == "PAUSE_FOR_HITL" for r in rfl_gate_rows)

    decided = [r for r in rows if r.get("event") == "HITL_DECIDED" and r.get("reason_code") == "HITL_CONTINUE"]
    assert decided, "HITL_CONTINUE must be logged when resolver returns CONTINUE"


def test_ethics_sealed_blocks_and_no_pii_persisted(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    res = sim.run_simulation(
        prompt="WordとExcelとPPTを作って。",
        run_id="TEST#ETHICS_SEALED",
        audit_path=str(p["audit"]),
        artifact_dir=str(p["artifacts"]),
        truncate_audit_on_start=True,
        faults={"word": {"leak_email": True}},  # inject email into raw_text
        hitl_resolver=_resolver_map({}),  # unused
    )

    by_id = {t.task_id: t for t in res.tasks}
    assert by_id["task_word"].decision == "STOPPED"
    assert by_id["task_word"].blocked_layer == "ethics"
    assert by_id["task_word"].reason_code == "ETHICS_EMAIL_DETECTED"

    # Artifacts must not be written for the sealed task
    assert "task_word" not in set(res.artifacts_written_task_ids)

    rows = _read_jsonl(p["audit"])
    _assert_arl_min_fields(rows)

    ethics_rows = [r for r in rows if r.get("event") == "GATE_ETHICS" and r.get("task_id") == "task_word"]
    assert ethics_rows
    assert ethics_rows[-1]["decision"] == "STOPPED"
    assert ethics_rows[-1]["sealed"] is True
    assert ethics_rows[-1]["overrideable"] is False
    assert ethics_rows[-1]["final_decider"] == "SYSTEM"

    # Hard guarantee: no email-like strings in audit, including dict keys
    audit_blob = p["audit"].read_text(encoding="utf-8")
    _assert_no_email_persisted(audit_blob)

    # Also ensure any written artifacts do not contain emails
    for task_id in res.artifacts_written_task_ids:
        # filenames are deterministic in the simulator
        # task_word is not written here; others are safe_text only
        for fp in p["artifacts"].glob(f"{task_id}.*.txt"):
            _assert_no_email_persisted(fp.read_text(encoding="utf-8"))


def test_contract_mismatch_hitl_continue_logs_regen_and_stays_pending(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    res = sim.run_simulation(
        prompt="WordとExcelとPPTを作って。",
        run_id="TEST#CONTRACT_MISMATCH",
        audit_path=str(p["audit"]),
        artifact_dir=str(p["artifacts"]),
        truncate_audit_on_start=True,
        faults={"excel": {"break_contract": True}},  # violate contract schema
        hitl_resolver=_resolver_map({"consistency": "CONTINUE"}),  # choose CONTINUE at consistency HITL
    )

    by_id = {t.task_id: t for t in res.tasks}
    assert by_id["task_excel"].decision == "PAUSE_FOR_HITL"
    assert by_id["task_excel"].blocked_layer == "consistency"
    assert "task_excel" not in set(res.artifacts_written_task_ids)

    # other tasks should still run
    assert by_id["task_word"].decision == "RUN"
    assert by_id["task_ppt"].decision == "RUN"
    assert res.decision == "PAUSE_FOR_HITL"

    rows = _read_jsonl(p["audit"])
    _assert_arl_min_fields(rows)

    # Regen signals must exist for the contract mismatch path
    assert any(r.get("event") == "REGEN_REQUESTED" and r.get("task_id") == "task_excel" for r in rows)
    assert any(r.get("event") == "REGEN_INSTRUCTIONS" and r.get("task_id") == "task_excel" for r in rows)
    assert any(
        r.get("event") ==
