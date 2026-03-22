# -*- coding: utf-8 -*-
"""
ai_doc_orchestrator_kage3_v1_3_5.py

Doc Orchestrator Simulator (KAGE3-style gates, memory-first benchmark friendly)

Pipeline (conceptual):
  Agent (excel/word/ppt) -> Orchestrator gates:
    Meaning -> Consistency -> RFL -> Ethics -> ACC -> Dispatch

Key properties:
- Fail-closed: unsafe/unstable -> STOPPED (never silently RUN).
- RFL does NOT seal; it escalates to HITL (human-in-the-loop).
- Memory-first core: run_simulation_mem returns rows in-memory.
- Optional file-mode compatibility wrapper: run_simulation writes audit JSONL + artifacts.
- '@' invariant: audit rows are sanitized so no email-like tokens are persisted.

Decision vocabulary:
  RUN / PAUSE_FOR_HITL / STOPPED

Python: 3.9+
"""

from __future__ import annotations

import hashlib
import json


JST_OFFSET = "+09:00"

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
HitlChoice = Literal["CONTINUE", "STOP"]

__version__ = "1.3.5"


    *,
    prompt: str,
    run_id: str,
    faults: Dict[str, Dict[str, Any]],
    hitl_resolver: Optional[Callable[[Dict[str, Any]], HitlChoice]],
    enable_runaway_seal: bool,
    runaway_threshold: int,
    max_attempts_per_task: int,
) -> Tuple[OrchestratorResult, List[Dict[str, Any]]]:
    """
    Core simulation that returns (OrchestratorResult, rows) without writing files.
    """

        prompt=prompt,
        run_id=run_id,
        faults=faults,
        hitl_resolver=hitl_resolver,
        enable_runaway_seal=enable_runaway_seal,
        runaway_threshold=runaway_threshold,
        max_attempts_per_task=max_attempts_per_task,
    )



        sealed = any(
            row.get("event") in ("AGENT_SEALED", "ETHICS_SEALED", "ACC_RUNAWAY_SEAL")
            and row.get("task") == task
            for row in rows
        )


        if paused:
            decision: Decision = "PAUSE_FOR_HITL"
            reason_code = "HITL_PENDING"
        elif ethics_stop:
            decision = "STOPPED"
            reason_code = "SEALED_BY_ETHICS"
        elif sealed and not done:
            decision = "STOPPED"
            reason_code = "SEALED_BY_ACC"
        elif done:
            decision = "RUN"
            reason_code = "OK"
        else:
            decision = orch_res.decision
            reason_code = orch_res.reason_code

        artifact_path: Optional[str] = None
        if decision == "RUN":
            artifact_root = Path(artifact_dir)
            artifact_root.mkdir(parents=True, exist_ok=True)
            artifact_path = str(artifact_root / f"{task_id}.txt")
            artifact_text = f"{task} artifact (run_id={run_id})"
            Path(artifact_path).write_text(artifact_text, encoding="utf-8")
            artifacts_written.append(task_id)

        tasks_out.append(
            TaskResult(
                task_id=task_id,
                task=task,
                decision=decision,
                sealed=bool(sealed),
                artifact_path=artifact_path,
                reason_code=reason_code,
            )
        )

    _write_jsonl(Path(audit_path), rows, truncate=bool(truncate_audit_on_start))

    return SimulationResult(
        decision=orch_res.decision,
        tasks=tasks_out,
        artifacts_written_task_ids=artifacts_written,
    )

    hitl_rate, counts = _derive_from_report(report, int(sample_cfg["runs"]))
    normalized_counts: Dict[str, int] = {k: 0 for k in CANON_DECISIONS}
    for key, value in counts.items():
        nk = _normalize_decision(str(key))
        normalized_counts[nk] = normalized_counts.get(nk, 0) + int(value)

    sample_digest, sample_decision = _sample_digest_and_decision(
        prompt=sample_cfg["prompt"],
        seed=sample_cfg["seed"],
        p_continue=sample_cfg["p_continue"],
        faults=sample_cfg["faults"],
        enable_runaway_seal=sample_cfg["enable_runaway_seal"],
        runaway_threshold=sample_cfg["runaway_threshold"],
        max_attempts_per_task=sample_cfg["max_attempts_per_task"],
    )


    }
    crash_count = 0
    pii_leak_count = 0
    hitl_requested_count = 0
    seal_event_count = 0
    sample_rows: List[Dict[str, Any]] = []
    runs_data: List[Dict[str, Any]] = []

    for i in range(int(runs)):
        run_id = f"SIM#{i:05d}"
        # deterministic but per-run varied resolver
        resolver_seed = rng.randint(0, 10**9)
        resolver = make_random_hitl_resolver(seed=resolver_seed, p_continue=p_continue)

        try:
            orch_res, rows = run_simulation_mem(
                prompt=prompt,
                run_id=run_id,
                faults=faults,
                hitl_resolver=resolver,
                enable_runaway_seal=enable_runaway_seal,
                runaway_threshold=runaway_threshold,
                max_attempts_per_task=max_attempts_per_task,
            )
        except Exception as exc:  # pragma: no cover - benchmark should remain crash-safe
            crash_count += 1
            rows = []
            orch_res = OrchestratorResult(
                decision="STOPPED",
                reason_code=f"EXC:{type(exc).__name__}",
                sealed=False,
                overrideable=False,
                final_decider="SYSTEM",
                hitl_requested=False,
            )

        decision = _normalize_decision(orch_res.decision)
        overall_decision_counts[decision] = overall_decision_counts.get(decision, 0) + 1



