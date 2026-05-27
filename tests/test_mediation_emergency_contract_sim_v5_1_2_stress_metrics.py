# tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is importable under pytest/CI cwd differences.
# The canonical repository target is mediation_emergency_contract_sim_v5_1_2.py.
# The fixed5 fallback exists only so this file can be verified before the source
# file is renamed/replaced during local review.
import importlib
import importlib.util

_REPO_ROOT = Path(__file__).resolve().parents[1]
_THIS_DIR = Path(__file__).resolve().parent
for _p in (_REPO_ROOT, _THIS_DIR, Path.cwd()):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _load_sim_module():
    for module_name in (
        "mediation_emergency_contract_sim_v5_1_2",
        "mediation_emergency_contract_sim_v5_1_2_fixed5",
    ):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            pass

    for base in (_REPO_ROOT, _THIS_DIR, Path.cwd()):
        for filename in (
            "mediation_emergency_contract_sim_v5_1_2.py",
            "mediation_emergency_contract_sim_v5_1_2_fixed5.py",
        ):
            path = base / filename
            if path.exists():
                spec = importlib.util.spec_from_file_location(
                    "_mediation_emergency_contract_sim_v5_1_2_under_test",
                    path,
                )
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module

    raise ModuleNotFoundError(
        "Could not load mediation_emergency_contract_sim_v5_1_2.py "
        "or mediation_emergency_contract_sim_v5_1_2_fixed5.py"
    )


sim = _load_sim_module()  # noqa: E402


def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        _fail(f"{message} (actual={actual!r}, expected={expected!r})")


def _require_ge(actual: int, threshold: int, message: str) -> None:
    if actual < threshold:
        _fail(f"{message} (actual={actual!r}, threshold={threshold!r})")


def _require_in_range(value: float, low: float, high: float, message: str) -> None:
    if not (low <= value <= high):
        _fail(f"{message} (actual={value!r}, low={low!r}, high={high!r})")


def _patch_store_paths(monkeypatch, tmp_path: Path) -> None:
    """
    テストごとに永続化先を隔離する。
    リポジトリ直下の実ファイルを汚さない。
    """
    trust_path = tmp_path / "model_trust_store.json"
    grants_path = tmp_path / "model_grants.json"
    eval_path = tmp_path / "eval_state.json"

    monkeypatch.setattr(sim, "TRUST_STORE_PATH", trust_path, raising=False)
    monkeypatch.setattr(sim, "GRANTS_STORE_PATH", grants_path, raising=False)
    monkeypatch.setattr(sim, "EVAL_STATE_PATH", eval_path, raising=False)

    # 後方互換 alias も揃える
    monkeypatch.setattr(sim, "GRANT_STORE_PATH", grants_path, raising=False)
    monkeypatch.setattr(sim, "EVAL_STORE_PATH", eval_path, raising=False)


def _queue_counts(results: Dict[str, Any]) -> Dict[str, Any]:
    return (((results or {}).get("hitl_queue") or {}).get("counts") or {})


def _abnormal(results: Dict[str, Any]) -> Dict[str, Any]:
    return (results or {}).get("abnormal_arl_persistence", {}) or {}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _assert_sealed_only_ethics_or_acc(results: Dict[str, Any]) -> None:
    runs = results.get("runs", []) or []
    for run in runs:
        for row in (run.get("arl", []) or []):
            layer = row.get("layer")
            decision = row.get("decision")
            sealed = bool(row.get("sealed", False))
            if decision == sim.DECISION_PAUSE:
                _require(sealed is False, "PAUSE_FOR_HITL rows must not be sealed")
            if sealed:
                _require(
                    layer in (sim.LAYER_ETHICS, sim.LAYER_ACC),
                    f"sealed row must be ethics/acc only (layer={layer!r})",
                )
            if layer == sim.LAYER_RFL:
                _require(sealed is False, "RFL rows must never be sealed")


def _audit_for_unit_test() -> sim.AuditLog:
    return sim.AuditLog(key=b"TEST_KEY_DO_NOT_USE", key_id="test-key")


def _state_for_unit_test(run_id: str = "TEST#V512") -> sim.OrchestratorState:
    return sim.OrchestratorState(run_id=run_id)


def _draft_with_required_footer(body: str) -> str:
    """
    draft_lint_gate() の required_lines を満たした上で、
    境界文だけを検証するための最小ドラフト。
    """
    return f"""# Unit Test Draft

{body}

This document is a draft.
This document has no operational effect.
AI is used for drafting only.
ADMIN approval is required.
"""


def _lint_result(body: str) -> tuple[bool, str]:
    audit = _audit_for_unit_test()
    st = _state_for_unit_test()
    return sim.draft_lint_gate(audit, st, _draft_with_required_footer(body))


def _assert_lint_rejects(body: str, expected_reason: str) -> None:
    ok, reason = _lint_result(body)
    _require(ok is False, f"draft_lint should reject: {body!r}")
    _require_equal(reason, expected_reason, f"draft_lint reason mismatch for: {body!r}")


def _assert_lint_ok(body: str) -> None:
    ok, reason = _lint_result(body)
    _require(ok is True, f"draft_lint should pass: {body!r}")
    _require_equal(reason, sim.RC_DRAFT_LINT_OK, f"draft_lint OK reason mismatch for: {body!r}")


def test_v512_pause_for_hitl_must_not_be_sealed() -> None:
    """
    fixed5 regression:
    PAUSE_FOR_HITL は HITL へ戻す一時停止であり、sealed=True と両立しない。
    """
    audit = _audit_for_unit_test()

    try:
        audit.emit(
            run_id="TEST#PAUSE#SEALED",
            layer=sim.LAYER_ACC,
            decision=sim.DECISION_PAUSE,
            sealed=True,
            overrideable=True,
            final_decider=sim.DECIDER_SYSTEM,
            reason_code=sim.RC_ADMIN_FINALIZE_REQUIRED,
        )
    except AssertionError as exc:
        _require(
            "PAUSE_FOR_HITL" in str(exc) and "sealed" in str(exc),
            "unexpected AssertionError for sealed PAUSE_FOR_HITL",
        )
        return

    _fail("PAUSE_FOR_HITL + sealed=True must be rejected")


def test_v512_arl_invariant_rejections_are_enforced() -> None:
    """
    fixed5 regression:
    RFL sealed 禁止、sealed は ethics/acc のみ、という不変条件を直接固定する。
    """
    audit = _audit_for_unit_test()

    try:
        audit.emit(
            run_id="TEST#RFL#SEALED",
            layer=sim.LAYER_RFL,
            decision=sim.DECISION_RUN,
            sealed=True,
            overrideable=True,
            final_decider=sim.DECIDER_SYSTEM,
            reason_code=sim.RC_REL_REF_MISSING,
        )
    except AssertionError:
        pass
    else:
        _fail("RFL sealed must be rejected")

    try:
        audit.emit(
            run_id="TEST#MEANING#SEALED",
            layer=sim.LAYER_MEANING,
            decision=sim.DECISION_STOP,
            sealed=True,
            overrideable=False,
            final_decider=sim.DECIDER_SYSTEM,
            reason_code=sim.RC_OK,
        )
    except AssertionError:
        pass
    else:
        _fail("sealed rows outside ethics/acc must be rejected")


def test_v512_draft_lint_rejects_repeated_and_clause_boundary_unsafe_claims() -> None:
    """
    fixed5 regression:
    最初の一致が否定されていても、後続の非否定一致を見逃さない。
    カンマや but 後の節転換でも、前半の否定を後半に効かせない。
    """
    legal_cases = [
        "No delay is expected. This contract is binding.",
        "This is not legally binding. It is legally binding.",
        "This is not legally binding, it is legally binding.",
        "This is not legally binding but it is legally binding.",
    ]
    for body in legal_cases:
        _assert_lint_rejects(body, sim.RC_SAFETY_LEGAL_BINDING_CLAIM)

    discrimination_cases = [
        "This is not racist. This text is racist.",
        "This is not racist, this text is racist.",
    ]
    for body in discrimination_cases:
        _assert_lint_rejects(body, sim.RC_SAFETY_DISCRIMINATION_TERM)


def test_v512_draft_lint_allows_direct_negation_cases() -> None:
    """
    fixed5 regression:
    直接否定されている安全な説明は DRAFT_LINT_OK のまま維持する。
    """
    ok_cases = [
        "This draft is not legally binding.",
        "This document is non-binding.",
        "This text is not racist.",
        "This document does not create legal effect.",
        "This document has no binding effect.",
    ]
    for body in ok_cases:
        _assert_lint_ok(body)


def test_v512_arl_hmac_verifies_normal_rows_and_rejects_tamper() -> None:
    """
    ARL/HMAC の正常系と改ざん検出を直接固定する。
    """
    key = b"TEST_KEY_DO_NOT_USE"
    audit = sim.AuditLog(key=key, key_id="test-key")
    audit.emit(
        run_id="TEST#ARL#HMAC",
        layer=sim.LAYER_ETHICS,
        decision=sim.DECISION_STOP,
        sealed=True,
        overrideable=False,
        final_decider=sim.DECIDER_SYSTEM,
        reason_code=sim.RC_EVIDENCE_FABRICATION,
    )

    rows = audit.export_rows()
    ok, err = sim.verify_arl_rows(key=key, rows=rows)
    _require(ok is True, f"ARL rows should verify, err={err!r}")

    tampered = [dict(row) for row in rows]
    tampered[0]["reason_code"] = sim.RC_OK
    ok_tampered, err_tampered = sim.verify_arl_rows(key=key, rows=tampered)
    _require(ok_tampered is False, "tampered ARL rows must not verify")
    _require(err_tampered is not None, "tampered ARL verification should return an error")



def test_v512_fabricated_evidence_stops_and_seals_direct(
    monkeypatch, tmp_path: Path
) -> None:
    """
    fabricated evidence は、通常経路に乗せず STOPPED + sealed へ落ちることを直接確認する。
    mixed/stress の間接確認だけに依存しない。
    """
    _patch_store_paths(monkeypatch, tmp_path)
    sim.ensure_default_grant_exists()

    key, key_id = sim.load_key_bytes("demo")
    trust = sim.TrustState()

    st, audit, _trust_after = sim.simulate_run(
        run_id="TEST#FABRICATED",
        dummy_auth_id="EMG-7K3P9Q",
        trust=trust,
        fabricate_evidence=True,
        key=key,
        key_id=key_id,
        full_context_n=0,
        persist=False,
    )

    _require_equal(st.state, "STOPPED", "fabricated evidence must stop the run")
    _require(st.sealed is True, "fabricated evidence must seal the stopped state")

    rows = audit.rows
    _require(
        any(
            row.get("layer") == sim.LAYER_ETHICS
            and row.get("decision") == sim.DECISION_STOP
            and row.get("sealed") is True
            and row.get("reason_code") == sim.RC_EVIDENCE_FABRICATION
            for row in rows
        ),
        "fabricated evidence must emit an ethics sealed STOP row",
    )

    ok, err = sim.verify_arl_rows(key=key, rows=rows)
    _require(ok, f"ARL rows must verify after fabricated evidence stop: {err}")


def test_v512_operational_resilience_clean_runs_large(
    monkeypatch, tmp_path: Path
) -> None:
    """
    clean run 大量反復での運用耐性確認。
    keep_runs=False でメモリ肥大を避けつつ、
    queue / trust / eval / abnormal persistence の整合を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    results = sim.run_simulation(
        runs=1000,
        fabricate=False,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    counts = _queue_counts(results)
    abnormal = _abnormal(results)

    _require_equal(counts.get("total_runs"), 1000, "total_runs mismatch")
    _require_equal(
        counts.get("by_state", {}).get("CONTRACT_EFFECTIVE", 0),
        1000,
        "CONTRACT_EFFECTIVE count mismatch",
    )
    _require_equal(counts.get("queue_size", 0), 0, "queue_size mismatch")

    _require_equal(abnormal.get("abnormal_total", 0), 0, "abnormal_total mismatch")
    _require_equal(abnormal.get("saved", 0), 0, "saved mismatch")
    _require_equal(abnormal.get("skipped_by_cap", 0), 0, "skipped_by_cap mismatch")

    eval_after = results.get("eval_after", {})
    _require_equal(
        eval_after.get("clean_completion_count"),
        1000,
        "clean_completion_count mismatch",
    )
    _require_equal(
        eval_after.get("multiplier"),
        sim.EVAL_MULTIPLIER_CAP,
        "multiplier mismatch",
    )

    trust_after = results.get("trust_after", {})
    _require_in_range(
        trust_after.get("trust_score", -1),
        sim.TRUST_MIN,
        sim.TRUST_MAX,
        "trust_score out of range",
    )


def test_v512_mixed_mode_deterministic_under_reset(
    monkeypatch, tmp_path: Path
) -> None:
    """
    fabricate-rate 混在時でも、
    reset + seed 固定なら queue / trust / eval が再現することを確認。
    cooldown_until は壁時計依存なので完全一致比較から除外する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    params = dict(
        runs=500,
        fabricate=False,
        fabricate_rate=0.10,
        seed=42,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
    )

    result_1 = sim.run_simulation(**params)
    result_2 = sim.run_simulation(**params)

    counts_1 = _queue_counts(result_1)
    counts_2 = _queue_counts(result_2)
    _require_equal(counts_1, counts_2, "queue counts must be deterministic")

    abnormal_1 = _abnormal(result_1)
    abnormal_2 = _abnormal(result_2)
    _require_equal(
        abnormal_1,
        abnormal_2,
        "abnormal persistence summary must be deterministic",
    )

    trust_1 = dict(result_1.get("trust_after", {}))
    trust_2 = dict(result_2.get("trust_after", {}))
    cooldown_1 = trust_1.pop("cooldown_until", None)
    cooldown_2 = trust_2.pop("cooldown_until", None)

    _require_equal(
        trust_1,
        trust_2,
        "trust_after must match except for cooldown_until",
    )

    if cooldown_1 is not None or cooldown_2 is not None:
        _require(cooldown_1 is not None, "cooldown_1 must exist if either cooldown exists")
        _require(cooldown_2 is not None, "cooldown_2 must exist if either cooldown exists")

    _require_equal(
        result_1.get("eval_after"),
        result_2.get("eval_after"),
        "eval_after must be deterministic",
    )

    _require_ge(
        abnormal_1.get("abnormal_total", 0),
        1,
        "abnormal_total should be positive in mixed mode",
    )


def test_v512_abnormal_arl_persistence_and_incident_index(
    monkeypatch, tmp_path: Path
) -> None:
    """
    異常時のみ ARL 保存 + incident index / counter の整合確認。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    out_dir = tmp_path / "arl_out"
    results = sim.run_simulation(
        runs=200,
        fabricate=False,
        fabricate_rate=0.20,
        seed=7,
        reset=True,
        reset_eval=True,
        keep_runs=False,
        queue_max_items=0,
        sample_runs=0,
        save_arl_on_abnormal=True,
        arl_out_dir=str(out_dir),
        max_arl_files=30,
        full_context_n=5,
    )

    abnormal = _abnormal(results)
    saved = int(abnormal.get("saved", 0))
    abnormal_total = int(abnormal.get("abnormal_total", 0))
    skipped = int(abnormal.get("skipped_by_cap", 0))

    _require_ge(abnormal_total, 1, "abnormal_total should be positive")
    _require_equal(saved, min(abnormal_total, 30), "saved count mismatch")
    _require_equal(skipped, max(0, abnormal_total - 30), "skipped_by_cap mismatch")

    arl_files = sorted(out_dir.glob("INC#*.arl.jsonl"))
    _require_equal(len(arl_files), saved, "saved ARL file count mismatch")

    index_path = out_dir / "incident_index.jsonl"
    counter_path = out_dir / "incident_counter.txt"
    _require(index_path.exists(), "incident_index.jsonl should exist")
    _require(counter_path.exists(), "incident_counter.txt should exist")

    index_rows = _read_jsonl(index_path)
    _require_equal(len(index_rows), saved, "incident_index row count mismatch")

    counter_value = int(counter_path.read_text(encoding="utf-8").strip())
    _require_equal(counter_value, saved + 1, "incident_counter next value mismatch")

    incident_ids = set()
    for row in index_rows:
        incident_id = row.get("incident_id")
        arl_path = Path(row.get("arl_path", ""))

        _require(bool(incident_id), "incident_id should not be empty")
        _require(
            incident_id not in incident_ids,
            f"duplicate incident_id: {incident_id!r}",
        )
        _require(arl_path.exists(), f"arl_path should exist: {arl_path!s}")

        incident_ids.add(incident_id)


def test_v512_sealed_invariants_under_mixed_load(
    monkeypatch, tmp_path: Path
) -> None:
    """
    keep_runs=True の中規模 runs で、
    sealed は ethics / acc のみ、
    RFL は sealed にならない不変条件を確認する。
    """
    _patch_store_paths(monkeypatch, tmp_path)

    results = sim.run_simulation(
        runs=200,
        fabricate=False,
        fabricate_rate=0.15,
        seed=99,
        reset=True,
        reset_eval=True,
        keep_runs=True,
        queue_max_items=50,
        sample_runs=0,
    )

    _require("runs" in results, "results must contain 'runs'")
    _require(isinstance(results["runs"], list), "'runs' must be a list")
    _require_equal(len(results["runs"]), 200, "runs length mismatch")

    _assert_sealed_only_ethics_or_acc(results)
