# -*- coding: utf-8 -*-
"""
Tests for emergency_contract_kage_orchestrator_v1_0.py.

This test suite checks the minimal integrated simulator:

- normal simulated contract flow
- fabricated evidence pause
- real-world signal control ACC sealed stop
- user auth rejection
- admin finalize stop
- external side-effect pause
- RFL missing-policy pause
- ARL/HMAC tamper detection
- KAGE invariants on sealed / PAUSE_FOR_HITL / RFL rows
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import emergency_contract_kage_orchestrator_v1_0 as mod  # noqa: E402


def _require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        pytest.fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _copy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return json.loads(json.dumps(rows, ensure_ascii=False))


def _find_rows(
    rows: Iterable[dict[str, Any]],
    *,
    layer: str | None = None,
    event: str | None = None,
    decision: str | None = None,
    reason_code: str | None = None,
    sealed: bool | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    for row in rows:
        if layer is not None and row.get("layer") != layer:
            continue
        if event is not None and row.get("event") != event:
            continue
        if decision is not None and row.get("decision") != decision:
            continue
        if reason_code is not None and row.get("reason_code") != reason_code:
            continue
        if sealed is not None and row.get("sealed") is not sealed:
            continue
        found.append(row)

    return found


def _require_row(
    rows: Iterable[dict[str, Any]],
    *,
    layer: str | None = None,
    event: str | None = None,
    decision: str | None = None,
    reason_code: str | None = None,
    sealed: bool | None = None,
) -> dict[str, Any]:
    found = _find_rows(
        rows,
        layer=layer,
        event=event,
        decision=decision,
        reason_code=reason_code,
        sealed=sealed,
    )
    if not found:
        pytest.fail(
            "expected ARL row not found: "
            f"layer={layer!r}, event={event!r}, decision={decision!r}, "
            f"reason_code={reason_code!r}, sealed={sealed!r}"
        )
    return found[0]


def _run(
    tmp_path: Path,
    *,
    run_id: str,
    scenario_input: mod.EmergencyContractInput | None = None,
    **kwargs: Any,
) -> mod.RunResult:
    return mod.run_emergency_contract_kage_orchestration(
        run_id=run_id,
        scenario_input=scenario_input or mod.EmergencyContractInput(),
        hmac_key=mod.default_demo_key(),
        out_dir=str(tmp_path / "artifacts"),
        **kwargs,
    )


def _require_arl_verified(result: mod.RunResult) -> None:
    _require(result.arl_verified, f"result ARL verification failed: {result.arl_verify_reason}")

    ok, reason = mod.verify_arl_rows(
        key=mod.default_demo_key(),
        rows=result.arl_rows,
    )
    _require(ok, f"manual ARL verification failed: {reason}")


def _require_kage_invariants(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        layer = str(row.get("layer", ""))
        decision = str(row.get("decision", ""))
        sealed = bool(row.get("sealed", False))
        overrideable = bool(row.get("overrideable", False))
        final_decider = str(row.get("final_decider", ""))

        if layer == "relativity_gate":
            _require(row.get("sealed") is False, "RFL row must never be sealed")

        if decision == "PAUSE_FOR_HITL":
            _require(row.get("sealed") is False, "PAUSE_FOR_HITL must not be sealed")
            _require(
                row.get("overrideable") is True,
                "PAUSE_FOR_HITL must be overrideable",
            )

        if sealed:
            _require(
                layer in {"ethics_gate", "acc_gate"},
                f"sealed row must be ethics_gate or acc_gate, got {layer!r}",
            )
            _require(
                overrideable is False,
                "sealed row must not be overrideable",
            )
            _require_equal(
                final_decider,
                "SYSTEM",
                "sealed row final_decider must be SYSTEM",
            )


def test_normal_run_generates_simulated_contract_artifact(tmp_path: Path) -> None:
    result = _run(tmp_path, run_id="TEST#NORMAL")

    _require_equal(result.decision, "RUN", "normal run should return RUN")
    _require_equal(
        result.final_state,
        "CONTRACT_EFFECTIVE_SIMULATED",
        "normal run should reach simulated contract effect",
    )
    _require_equal(
        result.reason_code,
        "CONTRACT_EFFECTIVE_SIMULATED",
        "normal run reason_code mismatch",
    )
    _require(result.sealed is False, "normal run must not be sealed")
    _require(result.artifact_path is not None, "normal run should write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    artifact_path = Path(str(result.artifact_path))
    _require(artifact_path.exists(), f"artifact was not created: {artifact_path}")

    artifact_text = artifact_path.read_text(encoding="utf-8")
    _require(
        "Emergency Signal Priority" in artifact_text,
        "artifact should contain the emergency signal priority draft title",
    )
    _require(
        "This is not legally binding" in artifact_text,
        "artifact should state that it is not legally binding",
    )
    _require(
        "This does not control real signals" in artifact_text,
        "artifact should state that it does not control real signals",
    )

    _require_row(
        result.arl_rows,
        layer="meaning_gate",
        decision="RUN",
        reason_code="MEANING_OK",
    )
    _require_row(
        result.arl_rows,
        layer="consistency_gate",
        decision="RUN",
        reason_code="CONSISTENCY_OK",
    )
    _require_row(
        result.arl_rows,
        layer="relativity_gate",
        decision="RUN",
        reason_code="REL_OK",
    )
    _require_row(
        result.arl_rows,
        layer="evidence_gate",
        decision="RUN",
        reason_code="EVIDENCE_OK",
    )
    _require_row(
        result.arl_rows,
        layer="hitl_auth",
        decision="RUN",
        reason_code="AUTH_APPROVE",
    )
    _require_row(
        result.arl_rows,
        layer="doc_draft",
        event="DRAFT_GENERATED",
        decision="RUN",
        reason_code="DRAFT_GENERATED",
    )
    _require_row(
        result.arl_rows,
        layer="ethics_gate",
        decision="RUN",
        reason_code="ETHICS_OK",
    )
    _require_row(
        result.arl_rows,
        layer="draft_lint_gate",
        decision="RUN",
        reason_code="DRAFT_LINT_OK",
    )
    _require_row(
        result.arl_rows,
        layer="acc_gate",
        decision="RUN",
        reason_code="ACC_OK",
    )
    _require_row(
        result.arl_rows,
        layer="hitl_finalize_admin",
        decision="RUN",
        reason_code="FINALIZE_APPROVE",
    )
    _require_row(
        result.arl_rows,
        layer="dispatch",
        event="ARTIFACT_WRITTEN",
        decision="RUN",
        reason_code="DRAFT_GENERATED",
    )
    _require_row(
        result.arl_rows,
        layer="contract_effect",
        event="CONTRACT_EFFECT_SIMULATED",
        decision="RUN",
        reason_code="CONTRACT_EFFECTIVE_SIMULATED",
    )


def test_fabricated_evidence_pauses_with_evidence_fabrication_event(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#FABRICATED",
        fabricated_evidence=True,
    )

    _require_equal(
        result.decision,
        "PAUSE_FOR_HITL",
        "fabricated evidence should pause for HITL",
    )
    _require(result.sealed is False, "fabricated evidence pause must not be sealed")
    _require(result.artifact_path is None, "fabricated evidence must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    row = _require_row(
        result.arl_rows,
        layer="evidence_gate",
        decision="PAUSE_FOR_HITL",
        reason_code="EVIDENCE_FABRICATION",
        sealed=False,
    )
    _require(
        row.get("overrideable") is True,
        "fabricated evidence pause should be overrideable",
    )
    _require_equal(
        row.get("final_decider"),
        "SYSTEM",
        "fabricated evidence gate should be SYSTEM-decided",
    )


def test_real_signal_control_is_sealed_by_acc(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#REAL_SIGNAL",
        scenario_input=mod.EmergencyContractInput(
            requested_real_signal_control=True,
        ),
    )

    _require_equal(
        result.decision,
        "STOPPED",
        "real signal control request should stop",
    )
    _require_equal(
        result.final_state,
        "STOPPED",
        "real signal control request should end in STOPPED",
    )
    _require_equal(
        result.reason_code,
        "ACC_REAL_WORLD_CONTROL_BLOCKED",
        "real signal control should be blocked by ACC",
    )
    _require(result.sealed is True, "real signal control should be sealed")
    _require(result.artifact_path is None, "sealed ACC stop must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    row = _require_row(
        result.arl_rows,
        layer="acc_gate",
        decision="STOPPED",
        reason_code="ACC_REAL_WORLD_CONTROL_BLOCKED",
        sealed=True,
    )
    _require(row.get("overrideable") is False, "sealed ACC row must not be overrideable")
    _require_equal(
        row.get("final_decider"),
        "SYSTEM",
        "sealed ACC row must be SYSTEM-decided",
    )


def test_auth_reject_stops_without_seal(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#AUTH_REJECT",
        auth_approved=False,
    )

    _require_equal(result.decision, "STOPPED", "auth rejection should stop")
    _require_equal(result.final_state, "STOPPED", "auth rejection final_state mismatch")
    _require_equal(result.reason_code, "AUTH_REJECT", "auth rejection reason mismatch")
    _require(result.sealed is False, "auth rejection should not be sealed")
    _require(result.artifact_path is None, "auth rejection must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    _require_row(
        result.arl_rows,
        layer="hitl_auth",
        decision="PAUSE_FOR_HITL",
        reason_code="AUTH_REQUIRED",
        sealed=False,
    )
    reject_row = _require_row(
        result.arl_rows,
        layer="hitl_auth",
        decision="STOPPED",
        reason_code="AUTH_REJECT",
        sealed=False,
    )
    _require_equal(
        reject_row.get("final_decider"),
        "USER",
        "auth reject should be USER-decided",
    )


def test_admin_finalize_stop_stops_without_seal(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#FINALIZE_STOP",
        admin_finalize_approved=False,
    )

    _require_equal(result.decision, "STOPPED", "admin finalize stop should stop")
    _require_equal(
        result.final_state,
        "STOPPED",
        "admin finalize stop final_state mismatch",
    )
    _require_equal(
        result.reason_code,
        "FINALIZE_STOP",
        "admin finalize stop reason mismatch",
    )
    _require(result.sealed is False, "admin finalize stop should not be sealed")
    _require(result.artifact_path is None, "admin finalize stop must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    _require_row(
        result.arl_rows,
        layer="hitl_finalize_admin",
        decision="PAUSE_FOR_HITL",
        reason_code="ADMIN_FINALIZE_REQUIRED",
        sealed=False,
    )
    stop_row = _require_row(
        result.arl_rows,
        layer="hitl_finalize_admin",
        decision="STOPPED",
        reason_code="FINALIZE_STOP",
        sealed=False,
    )
    _require_equal(
        stop_row.get("final_decider"),
        "ADMIN",
        "admin finalize stop should be ADMIN-decided",
    )


def test_external_effect_pauses_without_seal(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#EXTERNAL_EFFECT",
        scenario_input=mod.EmergencyContractInput(
            requested_external_effect=True,
        ),
        allow_external_effects=False,
    )

    _require_equal(
        result.decision,
        "PAUSE_FOR_HITL",
        "external effect request should pause for HITL",
    )
    _require_equal(
        result.final_state,
        "PAUSE_FOR_HITL",
        "external effect final_state mismatch",
    )
    _require_equal(
        result.reason_code,
        "ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL",
        "external effect reason mismatch",
    )
    _require(result.sealed is False, "external effect pause must not be sealed")
    _require(result.artifact_path is None, "external effect pause must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    row = _require_row(
        result.arl_rows,
        layer="acc_gate",
        decision="PAUSE_FOR_HITL",
        reason_code="ACC_EXTERNAL_SIDE_EFFECT_REQUIRES_HITL",
        sealed=False,
    )
    _require(
        row.get("overrideable") is True,
        "external effect pause should be overrideable",
    )


def test_rfl_missing_policy_pauses_without_seal(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        run_id="TEST#RFL_MISSING_POLICY",
        scenario_input=mod.EmergencyContractInput(
            priority_policy="",
        ),
        hitl_continue_on_rfl=False,
    )

    _require_equal(
        result.decision,
        "PAUSE_FOR_HITL",
        "missing priority policy should pause",
    )
    _require(result.sealed is False, "RFL path must not be sealed")
    _require(result.artifact_path is None, "RFL pause must not write artifact")
    _require_arl_verified(result)
    _require_kage_invariants(result.arl_rows)

    rfl_row = _require_row(
        result.arl_rows,
        layer="relativity_gate",
        decision="PAUSE_FOR_HITL",
        reason_code="REL_REF_MISSING",
        sealed=False,
    )
    _require(rfl_row.get("overrideable") is True, "RFL pause must be overrideable")

    hitl_row = _require_row(
        result.arl_rows,
        layer="hitl_auth",
        decision="STOPPED",
        reason_code="REL_BOUNDARY_UNSTABLE",
        sealed=False,
    )
    _require_equal(
        hitl_row.get("final_decider"),
        "USER",
        "RFL stop should be USER-decided",
    )


def test_arl_tamper_detection_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, run_id="TEST#ARL_TAMPER")

    _require_arl_verified(result)

    tampered_rows = _copy_rows(result.arl_rows)
    _require(bool(tampered_rows), "normal run should produce ARL rows")

    tampered_rows[0]["reason_code"] = "TAMPERED"

    ok, reason = mod.verify_arl_rows(
        key=mod.default_demo_key(),
        rows=tampered_rows,
    )

    _require(ok is False, "tampered ARL rows should fail verification")
    _require(
        "row_hash mismatch" in reason,
        f"tamper reason should mention row_hash mismatch, got: {reason!r}",
    )


def test_all_scenarios_preserve_core_kage_invariants(tmp_path: Path) -> None:
    results = [
        _run(tmp_path, run_id="TEST#INV_NORMAL"),
        _run(
            tmp_path,
            run_id="TEST#INV_FABRICATED",
            fabricated_evidence=True,
        ),
        _run(
            tmp_path,
            run_id="TEST#INV_REAL_SIGNAL",
            scenario_input=mod.EmergencyContractInput(
                requested_real_signal_control=True,
            ),
        ),
        _run(
            tmp_path,
            run_id="TEST#INV_AUTH_REJECT",
            auth_approved=False,
        ),
        _run(
            tmp_path,
            run_id="TEST#INV_FINALIZE_STOP",
            admin_finalize_approved=False,
        ),
        _run(
            tmp_path,
            run_id="TEST#INV_EXTERNAL_EFFECT",
            scenario_input=mod.EmergencyContractInput(
                requested_external_effect=True,
            ),
            allow_external_effects=False,
        ),
        _run(
            tmp_path,
            run_id="TEST#INV_RFL_MISSING",
            scenario_input=mod.EmergencyContractInput(
                priority_policy="",
            ),
            hitl_continue_on_rfl=False,
        ),
    ]

    for result in results:
        _require_arl_verified(result)
        _require_kage_invariants(result.arl_rows)
