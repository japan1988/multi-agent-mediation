# -*- coding: utf-8 -*-
"""
Pytest flow tests for the v1.2.7 task-contract dispatch Doc Orchestrator.

Core workflow under test:
- Dispatch Gate separates normal chat from task-contract events.
- Normal chat exits without task execution.
- Task contract request drafts a contract and pauses for HITL.
- Task contract approval runs Word / Excel / PPT tasks through gates.
- Gate decisions are recorded in the HMAC audit hash chain.
- Consistency, ethics, audit tamper, checkpoint, and artifact tamper paths fail closed.

Import settings:
- Default candidates are tried automatically.
- If your module filename differs, set one of:
    DOC_ORCH_MODULE=your_module_name
    DOC_ORCH_MODULE_PATH=/path/to/your_file.py
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


MODULE_CANDIDATES = (
    os.environ.get("DOC_ORCH_MODULE", ""),
    "ai_doc_orchestrator_kage3_v1_2_7_task_contract_dispatch",
    "doc_orchestrator_v1_2_7_task_contract_dispatch",
    "doc_orchestrator_task_contract_dispatch_v1_2_7",
)


def load_module_under_test() -> ModuleType:
    module_path = os.environ.get("DOC_ORCH_MODULE_PATH")
    if module_path:
        path = Path(module_path)
        if not path.exists():
            raise AssertionError(f"DOC_ORCH_MODULE_PATH does not exist: {path}")
        spec = importlib.util.spec_from_file_location("doc_orch_under_test", path)
        if spec is None or spec.loader is None:
            raise AssertionError(f"Could not load module from path: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    errors: list[str] = []
    for name in MODULE_CANDIDATES:
        if not name:
            continue
        try:
            return importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - diagnostic only
            errors.append(f"{name}: {exc!r}")

    raise AssertionError(
        "Could not import the orchestrator module. "
        "Set DOC_ORCH_MODULE or DOC_ORCH_MODULE_PATH. "
        f"Tried: {errors}"
    )


orch = load_module_under_test()


@pytest.fixture()
def hmac_key() -> bytes:
    return b"pytest-doc-orchestrator-hmac-key"


@pytest.fixture()
def paths(tmp_path: Path) -> dict[str, str]:
    return {
        "audit_path": str(tmp_path / "audit.jsonl"),
        "artifact_dir": str(tmp_path / "artifacts"),
        "checkpoint_path": str(tmp_path / "checkpoint.json"),
    }


@pytest.fixture()
def valid_task_contract() -> dict[str, Any]:
    return {
        "priority_order": [
            "safety",
            "consistency",
            "evidence",
            "minimal_change",
            "human_review",
        ],
        "allowed_actions": [
            "read",
            "analyze",
            "summarize",
            "propose",
            "generate_diff_candidate",
            "temporary_verification",
        ],
        "prohibited_actions": [
            "external_api_call_without_approval",
            "submit_without_user_approval",
            "file_delete",
            "persist_raw_text",
            "persist_pii",
            "weaken_tests",
            "seal_rfl",
            "sealed_overrideable_true",
            "seal_outside_ethics_or_acc",
        ],
        "output_mode": "summary",
        "completion_criteria": [
            "word artifact generated",
            "excel artifact generated",
            "ppt artifact generated",
            "audit chain is verifiable",
        ],
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_orchestrator(
    *,
    prompt: str,
    run_id: str,
    hmac_key: bytes,
    paths: dict[str, str],
    task_contract: dict[str, Any] | None = None,
    require_task_contract: bool = False,
    enable_task_contract_dispatch: bool = False,
    task_contract_approved: bool = False,
    faults: dict[str, dict[str, Any]] | None = None,
    resume_from_checkpoint: bool = False,
    resume_confirmed: bool = False,
):
    return orch.run_simulation(
        prompt=prompt,
        run_id=run_id,
        audit_path=paths["audit_path"],
        artifact_dir=paths["artifact_dir"],
        checkpoint_path=paths["checkpoint_path"],
        hmac_key=hmac_key,
        key_id="pytest",
        chain_id="pytest-doc-orchestrator",
        task_contract=task_contract,
        require_task_contract=require_task_contract,
        enable_task_contract_dispatch=enable_task_contract_dispatch,
        task_contract_approved=task_contract_approved,
        faults=faults or {},
        resume_from_checkpoint=resume_from_checkpoint,
        resume_confirmed=resume_confirmed,
        stop_on_interruption=True,
    )


def assert_audit_chain_valid(audit_path: str, hmac_key: bytes) -> None:
    rows = read_jsonl(audit_path)
    last_hash, row_count = orch.verify_audit_hash_chain(Path(audit_path), hmac_key)
    assert row_count == len(rows)
    assert isinstance(last_hash, str)
    assert len(last_hash) == 64


# ---------------------------------------------------------------------------
# Dispatch Gate
# ---------------------------------------------------------------------------

def test_chat_message_does_not_execute_tasks(hmac_key: bytes, paths: dict[str, str]) -> None:
    result = run_orchestrator(
        prompt="こんにちは。今日は通常の相談だけです。",
        run_id="R#CHAT_ONLY",
        hmac_key=hmac_key,
        paths=paths,
        enable_task_contract_dispatch=True,
    )

    assert result.decision == "RUN"
    assert result.dispatch_event == "CHAT_MESSAGE"
    assert result.tasks == []
    assert result.artifacts_written_task_ids == []
    assert not Path(paths["artifact_dir"]).exists() or not list(Path(paths["artifact_dir"]).glob("*"))

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("layer") == "dispatch_gate" for row in rows)
    assert any(row.get("reason_code") == "CHAT_MODE_SELECTED" for row in rows)
    assert not any(row.get("event") == "TASK_ASSIGNED" for row in rows)
    assert_audit_chain_valid(paths["audit_path"], hmac_key)


def test_task_contract_request_generates_draft_and_pauses(hmac_key: bytes, paths: dict[str, str]) -> None:
    result = run_orchestrator(
        prompt="タスク契約: Excelで進捗表を作り、Wordで要約し、PPTでスライド化する",
        run_id="R#CONTRACT_REQUEST",
        hmac_key=hmac_key,
        paths=paths,
        enable_task_contract_dispatch=True,
    )

    assert result.decision == "PAUSE_FOR_HITL"
    assert result.dispatch_event == "TASK_CONTRACT_REQUEST"
    assert result.contract_id
    assert result.contract_hash
    assert result.task_contract_draft is not None
    assert result.task_contract_draft["contract_hash"] == result.contract_hash
    assert result.artifacts_written_task_ids == []

    rows = read_jsonl(paths["audit_path"])
    reason_codes = {row.get("reason_code") for row in rows}
    assert "TASK_CONTRACT_REQUESTED" in reason_codes
    assert "TASK_CONTRACT_DRAFTED" in reason_codes
    assert not any(row.get("event") == "TASK_ASSIGNED" for row in rows)
    assert_audit_chain_valid(paths["audit_path"], hmac_key)


def test_task_contract_rejection_stops_without_artifacts(hmac_key: bytes, paths: dict[str, str]) -> None:
    result = run_orchestrator(
        prompt="タスク契約 拒否",
        run_id="R#CONTRACT_REJECT",
        hmac_key=hmac_key,
        paths=paths,
        enable_task_contract_dispatch=True,
    )

    assert result.decision == "STOPPED"
    assert result.dispatch_event == "TASK_CONTRACT_REJECTION"
    assert result.tasks == []
    assert result.artifacts_written_task_ids == []

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "TASK_CONTRACT_REJECTED" for row in rows)
    assert not any(row.get("event") == "TASK_ASSIGNED" for row in rows)


def test_task_contract_approval_executes_all_tasks_after_gate(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    result = run_orchestrator(
        prompt="タスク契約 承認",
        run_id="R#CONTRACT_APPROVED",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        enable_task_contract_dispatch=True,
        task_contract_approved=True,
    )

    assert result.decision == "RUN"
    assert result.dispatch_event == "TASK_CONTRACT_APPROVAL"
    assert {task.task_id for task in result.tasks} == {"task_word", "task_excel", "task_ppt"}
    assert set(result.artifacts_written_task_ids) == {"task_word", "task_excel", "task_ppt"}

    artifact_dir = Path(paths["artifact_dir"])
    assert (artifact_dir / "task_word.docx.txt").exists()
    assert (artifact_dir / "task_excel.xlsx.txt").exists()
    assert (artifact_dir / "task_ppt.pptx.txt").exists()

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "TASK_CONTRACT_APPROVED" for row in rows)
    assert any(row.get("reason_code") == "TASK_CONTRACT_CONFIRMED" for row in rows)
    assert any(row.get("event") == "RUN_SUMMARY" for row in rows)
    assert_audit_chain_valid(paths["audit_path"], hmac_key)


# ---------------------------------------------------------------------------
# Gate recording
# ---------------------------------------------------------------------------

def test_gate_results_are_recorded_in_audit_log(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    result = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#GATE_RECORDS",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        enable_task_contract_dispatch=True,
        task_contract_approved=True,
    )

    assert result.decision == "RUN"
    rows = read_jsonl(paths["audit_path"])
    layers = {row.get("layer") for row in rows}
    events = {row.get("event") for row in rows}

    assert {"dispatch_gate", "task_contract_gate", "meaning_gate", "consistency_gate", "ethics_gate", "checkpoint_gate", "orchestrator"}.issubset(layers)
    assert {"TASK_ASSIGNED", "AGENT_OUTPUT", "ARTIFACT_WRITTEN", "TASK_CHECKPOINT_SAVED", "RUN_SUMMARY"}.issubset(events)

    for row in rows:
        assert "row_index" in row
        assert "prev_hash" in row
        assert "row_hash" in row
        assert row.get("sealed") is False
        assert row.get("final_decider") in {"SYSTEM", "USER"}

    assert_audit_chain_valid(paths["audit_path"], hmac_key)


# ---------------------------------------------------------------------------
# Task Contract Gate abnormal paths
# ---------------------------------------------------------------------------

def test_missing_task_contract_pauses_when_required(hmac_key: bytes, paths: dict[str, str]) -> None:
    result = run_orchestrator(
        prompt="Word / Excel / PPT を作成してください。",
        run_id="R#MISSING_CONTRACT",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=None,
        require_task_contract=True,
    )

    assert result.decision == "PAUSE_FOR_HITL"
    assert result.tasks == []
    assert result.token_estimate is not None

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "TASK_CONTRACT_REQUIRED" for row in rows)
    assert any(row.get("event") == "TOKEN_ESTIMATE" for row in rows)


def test_invalid_output_mode_pauses_for_hitl(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    invalid_contract = dict(valid_task_contract)
    invalid_contract["output_mode"] = "dangerous_auto_apply"

    result = run_orchestrator(
        prompt="Word / Excel / PPT を作成してください。",
        run_id="R#INVALID_OUTPUT_MODE",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=invalid_contract,
        require_task_contract=True,
    )

    assert result.decision == "PAUSE_FOR_HITL"
    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "TASK_CONTRACT_OUTPUT_MODE_INVALID" for row in rows)


# ---------------------------------------------------------------------------
# Meaning / Consistency / Ethics Gates
# ---------------------------------------------------------------------------

def test_excel_only_prompt_pauses_on_first_non_matching_task(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    result = run_orchestrator(
        prompt="Excelで進捗表を作成してください。",
        run_id="R#MEANING_EXCEL_ONLY",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
    )

    assert result.decision == "PAUSE_FOR_HITL"
    assert result.tasks[0].task_id == "task_word"
    assert result.tasks[0].blocked_layer == "meaning_gate"
    assert result.tasks[0].reason_code == "MEANING_KIND_MISSING"

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "MEANING_KIND_MISSING" for row in rows)


def test_consistency_gate_pauses_when_agent_breaks_contract(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    result = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#CONSISTENCY_FAULT",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        faults={"excel": {"break_contract": True}},
    )

    assert result.decision == "PAUSE_FOR_HITL"
    excel = next(task for task in result.tasks if task.task_id == "task_excel")
    assert excel.decision == "PAUSE_FOR_HITL"
    assert excel.blocked_layer == "consistency_gate"
    assert excel.reason_code == "CONTRACT_EXCEL_COLUMNS_INVALID"

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "REGEN_FOR_CONSISTENCY" for row in rows)


def test_ethics_gate_stops_on_email_and_redacts_audit_preview(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    result = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#ETHICS_EMAIL",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        faults={"word": {"leak_email": True}},
    )

    assert result.decision == "PAUSE_FOR_HITL"
    assert result.tasks[0].task_id == "task_word"
    assert result.tasks[0].decision == "STOPPED"
    assert result.tasks[0].blocked_layer == "ethics_gate"
    assert result.tasks[0].reason_code == "ETHICS_EMAIL_DETECTED"

    audit_text = Path(paths["audit_path"]).read_text(encoding="utf-8")
    assert "test.user+demo@example.com" not in audit_text
    assert "<REDACTED_EMAIL>" in audit_text


# ---------------------------------------------------------------------------
# Integrity / tamper evidence
# ---------------------------------------------------------------------------

def test_audit_tamper_is_detected_before_append(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    first = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#AUDIT_TAMPER",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
    )
    assert first.decision == "RUN"

    audit_path = Path(paths["audit_path"])
    rows = audit_path.read_text(encoding="utf-8").splitlines()
    first_row = json.loads(rows[0])
    first_row["reason_code"] = "TAMPERED_REASON_CODE"
    rows[0] = json.dumps(first_row, ensure_ascii=False, sort_keys=True)
    audit_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    second = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#AUDIT_TAMPER",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
    )

    assert second.decision == "PAUSE_FOR_HITL"
    assert second.integrity_status.startswith("TAMPER_EVIDENCE_DETECTED")


def test_checkpoint_resume_requires_hitl_after_interruption(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    interrupted = run_orchestrator(
        prompt="Excelで進捗表を作成してください。",
        run_id="R#RESUME_HITL",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
    )
    assert interrupted.decision == "PAUSE_FOR_HITL"

    resumed_without_confirmation = run_orchestrator(
        prompt="Excelで進捗表を作成してください。",
        run_id="R#RESUME_HITL",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        resume_from_checkpoint=True,
        resume_confirmed=False,
    )

    assert resumed_without_confirmation.decision == "PAUSE_FOR_HITL"
    assert resumed_without_confirmation.integrity_status == "VERIFIED"

    rows = read_jsonl(paths["audit_path"])
    assert any(row.get("reason_code") == "RESUME_REQUIRES_HITL_CONFIRMATION" for row in rows)


def test_completed_artifact_tamper_is_detected_on_resume(
    hmac_key: bytes,
    paths: dict[str, str],
    valid_task_contract: dict[str, Any],
) -> None:
    first = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#ARTIFACT_TAMPER",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
    )
    assert first.decision == "RUN"

    artifact_path = Path(paths["artifact_dir"]) / "task_word.docx.txt"
    artifact_path.write_text("tampered artifact body\n", encoding="utf-8")

    resumed = run_orchestrator(
        prompt="Wordで要約し、Excelで進捗表を作り、PPTでスライドを作成してください。",
        run_id="R#ARTIFACT_TAMPER",
        hmac_key=hmac_key,
        paths=paths,
        task_contract=valid_task_contract,
        require_task_contract=True,
        resume_from_checkpoint=True,
        resume_confirmed=True,
    )

    assert resumed.decision == "PAUSE_FOR_HITL"
    assert resumed.integrity_status.startswith("TAMPER_EVIDENCE_DETECTED")
