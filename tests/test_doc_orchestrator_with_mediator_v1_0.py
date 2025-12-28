# -*- coding: utf-8 -*-
import json
from pathlib import Path

import ai_doc_orchestrator_with_mediator_v1_0 as sim


def _read_jsonl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _layers_in_order(events):
    arl = [e for e in events if isinstance(e, dict) and "layer" in e and "run_id" in e]
    return [e["layer"] for e in arl]


def test_ok_runs_and_logs_no_at(tmp_path):
    log = tmp_path / "audit.jsonl"
    tasks = [sim.Task(task_id="T1", kind="xlsx", prompt="在庫の集計表を作って")]
    out = sim.run_pipeline(tasks=tasks, run_id="TEST#OK", session_id="SESSION_TEST", log_path=str(log))
    assert out[0].decision == "RUN"
    assert out[0].reason_code in ("ORCH_RUN_OK", "HITL_CONTINUE")

    text = log.read_text(encoding="utf-8")
    assert "raw_text" not in text
    assert "@" not in text  # hard invariant


def test_fixed_gate_order_is_logged_even_on_pause(tmp_path):
    log = tmp_path / "audit.jsonl"
    tasks = [sim.Task(task_id="T2", kind="pptx", prompt="いい感じにまとめて")]  # RFL -> PAUSE
    out = sim.run_pipeline(tasks=tasks, run_id="TEST#ORDER", session_id="SESSION_TEST", log_path=str(log))
    assert out[0].decision == "PAUSE_FOR_HITL"

    events = _read_jsonl(log)
    layers = _layers_in_order(events)

    must_appear = ["mediator_advice", "meaning_gate", "consistency_gate", "relativity_gate", "ethics_gate", "acc_gate", "dispatch"]
    for x in must_appear:
        assert x in layers

    idx = {name: layers.index(name) for name in must_appear}
    assert idx["mediator_advice"] < idx["meaning_gate"] < idx["consistency_gate"] < idx["relativity_gate"] < idx["ethics_gate"] < idx["acc_gate"] < idx["dispatch"]


def test_seal_only_ethics_or_acc(tmp_path):
    log = tmp_path / "audit.jsonl"
    tasks = [sim.Task(task_id="T3", kind="xlsx", prompt="連絡先は test@example.com に送って")]
    out = sim.run_pipeline(tasks=tasks, run_id="TEST#SEAL", session_id="SESSION_TEST", log_path=str(log))
    assert out[0].decision == "STOPPED"
    assert out[0].reason_code == "SEALED_BY_ETHICS_PII_LIKE"

    events = _read_jsonl(log)
    arl = [e for e in events if "layer" in e and "sealed" in e]

    sealed_layers = [e["layer"] for e in arl if e["sealed"] is True]
    assert sealed_layers, "Expected at least one sealed event"
    assert set(sealed_layers).issubset({"ethics_gate", "acc_gate"}), f"sealed=True appeared outside ethics/acc: {sealed_layers}"

    text = log.read_text(encoding="utf-8")
    assert "@" not in text  # even redacted logs must not contain '@'


def test_external_side_effect_escalates_to_hitl_and_keeps_order(tmp_path):
    log = tmp_path / "audit.jsonl"
    tasks = [sim.Task(task_id="T4", kind="pptx", prompt="作った資料をメールで送って")]
    out = sim.run_pipeline(tasks=tasks, run_id="TEST#ACC", session_id="SESSION_TEST", log_path=str(log))
    assert out[0].decision == "PAUSE_FOR_HITL"
    assert out[0].reason_code in ("ACC_EXTERNAL_SIDE_EFFECT_REQUEST", "MEDIATOR_EXTERNAL_SIDE_EFFECT_AMBIGUOUS")

    events = _read_jsonl(log)
    layers = _layers_in_order(events)
    assert "acc_gate" in layers
    assert "dispatch" in layers


def test_hitl_continue_turns_pause_into_run(tmp_path):
    log = tmp_path / "audit.jsonl"
    tasks = [sim.Task(task_id="T5", kind="pptx", prompt="いい感じにまとめて")]
    out = sim.run_pipeline(
        tasks=tasks,
        run_id="TEST#HITL",
        session_id="SESSION_TEST",
        log_path=str(log),
        hitl_choices={"T5": "CONTINUE"},
    )
    assert out[0].decision == "RUN"
    assert out[0].reason_code == "HITL_CONTINUE"
