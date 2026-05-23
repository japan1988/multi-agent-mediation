#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_code_anomaly_maestro_handoff_multi_abnormal_pel_sim_v0_4_1.py

Local-only simulation:
- v0.4.0 multi-abnormal-agent detection
- plus PEL future-failure prediction
- forced probability >= 0.8
- Maestro escalation
- simulated human HITL random choice:
  AUTHORIZE_SEAL / QUARANTINE_HANDOFF_RESUME / NO_ACTION
- NO_ACTION branch probabilistically produces failure/no-failure.

Safety boundary:
- metadata-only code-contract check
- no source-code execution
- no malware behavior
- no exploit reproduction
- no external communication
- no real process control
- no auto-fix / commit / push / merge
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


FORBIDDEN = {"external_network", "self_modification", "file_mutation", "real_process_control"}
PEL_THRESHOLD = 0.8
FUTURE_FAILURE_PROBABILITY = 0.87
ACTIONS = ["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME", "NO_ACTION"]


@dataclass
class Agent:
    agent_id: str
    role: str
    allowed: list[str]
    requested: list[str]
    status: str = "ACTIVE"

    def contract(self) -> dict[str, Any]:
        forbidden = sorted(set(self.requested) & FORBIDDEN)
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "allowed_capabilities": self.allowed,
            "requested_capabilities": self.requested,
            "forbidden_requested": forbidden,
            "code_execution": False,
            "external_communication": False,
            "file_mutation": False,
            "real_process_control": False,
            "payload_present": False,
        }


@dataclass
class ARLRow:
    run_id: str
    layer: str
    decision: str
    sealed: bool
    overrideable: bool
    final_decider: str
    reason_code: str
    message: str
    agent_id: str | None = None
    timestamp_unix: float = field(default_factory=time.time)
    prev_hash: str = ""
    row_hash: str = ""


class AuditLog:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.rows: list[ARLRow] = []

    @staticmethod
    def _hash(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def _body(row: ARLRow) -> str:
        data = asdict(row)
        data.pop("row_hash", None)
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def append(self, *, layer: str, decision: str, sealed: bool, overrideable: bool,
               final_decider: str, reason_code: str, message: str,
               agent_id: str | None = None) -> None:
        prev = self.rows[-1].row_hash if self.rows else "GENESIS"
        row = ARLRow(self.run_id, layer, decision, sealed, overrideable, final_decider,
                     reason_code, message, agent_id, prev_hash=prev)
        row.row_hash = self._hash(prev + self._body(row))
        self.rows.append(row)

    def verify(self) -> dict[str, Any]:
        violations: list[str] = []
        prev = "GENESIS"
        for index, row in enumerate(self.rows):
            if row.prev_hash != prev:
                violations.append(f"ARL_HASH_CHAIN_BREAK:{index}")
            if row.row_hash != self._hash(row.prev_hash + self._body(row)):
                violations.append(f"ARL_ROW_HASH_MISMATCH:{index}")
            if row.sealed and row.layer not in {"ethics_gate", "acc_gate"}:
                violations.append(f"SEALED_LAYER_NOT_ETHICS_OR_ACC:{index}")
            if row.layer in {"rfl", "relativity_gate"} and row.sealed:
                violations.append(f"RFL_MUST_NOT_BE_SEALED:{index}")
            if row.sealed and row.overrideable:
                violations.append(f"SEALED_MUST_NOT_BE_OVERRIDEABLE:{index}")
            if row.decision == "PAUSE_FOR_HITL" and row.sealed:
                violations.append(f"PAUSE_FOR_HITL_MUST_NOT_BE_SEALED:{index}")
            prev = row.row_hash
        return {"verified": not violations, "row_count": len(self.rows), "violations": violations}

    def write_jsonl(self, path: Path) -> None:
        path.write_text("\n".join(json.dumps(asdict(r), ensure_ascii=False, sort_keys=True) for r in self.rows) + "\n", encoding="utf-8")


def stable_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_scenario() -> tuple[dict[str, Agent], dict[str, Agent], set[str], dict[str, str]]:
    agents = {
        "agent_a": Agent("agent_a", "safety_review", ["safe_review"], ["safe_review"]),
        "agent_b": Agent("agent_b", "efficiency_review", ["safe_review"], ["safe_review", "external_network", "self_modification"]),
        "agent_c": Agent("agent_c", "readability_review", ["safe_review"], ["safe_review"]),
        "agent_d": Agent("agent_d", "tooling_review", ["safe_review"], ["safe_review", "file_mutation"]),
        "agent_e": Agent("agent_e", "process_review", ["safe_review"], ["safe_review", "real_process_control"]),
        "agent_f": Agent("agent_f", "documentation_review", ["safe_review"], ["safe_review"]),
    }
    standby = {
        "standby_1": Agent("standby_1", "replacement_efficiency_review", ["safe_review"], ["safe_review"], "STANDBY"),
        "standby_2": Agent("standby_2", "replacement_tooling_review", ["safe_review"], ["safe_review"], "STANDBY"),
        "standby_3": Agent("standby_3", "replacement_process_review", ["safe_review"], ["safe_review"], "STANDBY"),
    }
    expected = {"agent_b", "agent_d", "agent_e"}
    replacements = {"agent_b": "standby_1", "agent_d": "standby_2", "agent_e": "standby_3"}
    return agents, standby, expected, replacements


def create_checkpoint(detected: list[str], replacements: dict[str, str]) -> dict[str, Any]:
    checkpoint = {
        "schema_version": "multi-code-anomaly-pel-checkpoint-v0.4.1",
        "failed_agent_ids": sorted(detected),
        "replacement_map": {agent_id: replacements[agent_id] for agent_id in sorted(detected)},
        "resume_allowed": True,
        "hitl_required_before_resume": True,
        "safe_context": {
            "resume_from": "last_safe_checkpoint",
            "excluded_agent_outputs": [f"{agent_id}.output" for agent_id in sorted(detected)],
            "abnormal_outputs_reused": False,
            "abnormal_code_contracts_reused": False,
        },
    }
    checkpoint["checkpoint_hash"] = stable_hash(checkpoint)
    return checkpoint


def verify_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    body = dict(checkpoint)
    given = body.pop("checkpoint_hash", None)
    violations: list[str] = []
    if given != stable_hash(body):
        violations.append("CHECKPOINT_HASH_MISMATCH")
    if checkpoint.get("resume_allowed") is not True:
        violations.append("RESUME_NOT_ALLOWED")
    if checkpoint.get("hitl_required_before_resume") is not True:
        violations.append("HITL_NOT_REQUIRED_BEFORE_RESUME")
    if checkpoint["safe_context"].get("abnormal_outputs_reused") is not False:
        violations.append("ABNORMAL_OUTPUTS_REUSED")
    return {"verified": not violations, "violations": violations, "checkpoint_hash": given}


def pseudo_tasukeru_audit(records: list[dict[str, Any]], expected: set[str], out_dir: Path) -> dict[str, Any]:
    findings = []
    for record in records:
        if record["forbidden_requested"]:
            findings.append({
                "agent_id": record["agent_id"],
                "finding": "CODE_CONTRACT_FORBIDDEN_CAPABILITY",
                "review_level": "HITL_REQUIRED",
                "decision": "PAUSE_FOR_HITL",
                "reason_code": "FORBIDDEN_CAPABILITY_REQUESTED",
                "forbidden_requested": record["forbidden_requested"],
                "recommended_action": "ESCALATE_TO_MAESTRO_HITL",
            })

    detected = {finding["agent_id"] for finding in findings}
    all_ids = {record["agent_id"] for record in records}
    detection = {
        "expected_abnormal_agent_ids": sorted(expected),
        "detected_abnormal_agent_ids": sorted(detected),
        "normal_agent_ids": sorted(all_ids - expected),
        "false_positive_agent_ids": sorted(detected - expected),
        "false_negative_agent_ids": sorted(expected - detected),
    }
    detection["false_positive_count"] = len(detection["false_positive_agent_ids"])
    detection["false_negative_count"] = len(detection["false_negative_agent_ids"])
    detection["exact_detection_match"] = detection["false_positive_count"] == 0 and detection["false_negative_count"] == 0

    pel = {
        "tool": "PEL",
        "schema_version": "pel-future-failure-v0.4.1",
        "future_failure_probability": FUTURE_FAILURE_PROBABILITY,
        "threshold": PEL_THRESHOLD,
        "escalation_required": FUTURE_FAILURE_PROBABILITY >= PEL_THRESHOLD,
        "decision": "PAUSE_FOR_HITL",
        "reason_code": "PEL_FUTURE_FAILURE_PROBABILITY_HIGH",
        "escalate_to": "Maestro",
        "policy": {
            "prediction_is_fact": False,
            "auto_seal_allowed": False,
            "auto_quarantine_allowed": False,
            "auto_resume_allowed": False,
            "hitl_required_before_action": True,
        },
    }

    mismatches = []
    if not detection["exact_detection_match"]:
        mismatches.append("DETECTION_SET_MISMATCH")
    if pel["future_failure_probability"] < pel["threshold"]:
        mismatches.append("PEL_PROBABILITY_BELOW_THRESHOLD")
    if pel["decision"] != "PAUSE_FOR_HITL":
        mismatches.append("PEL_DID_NOT_PAUSE_FOR_HITL")

    dac = {
        "tool": "3D-DAC",
        "schema_version": "3d-dac-code-anomaly-pel-v0.4.1",
        "verified": not mismatches,
        "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
        "dependency_mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    packet = {
        "escalate_to": "Maestro",
        "decision": "PAUSE_FOR_HITL",
        "detected_abnormal_agent_ids": sorted(detected),
        "requested_human_actions": ACTIONS,
        "maestro_must_not_self_decide": True,
        "pel_report": pel,
        "findings": findings,
    }
    report = {
        "schema_version": "pseudo-tasukeru-code-auditor-v0.4.1",
        "verified": bool(findings) and detection["exact_detection_match"] and pel["escalation_required"],
        "decision": "PAUSE_FOR_HITL",
        "findings": findings,
        "detection_matrix": detection,
        "pel_report": pel,
        "dimension_dependency_report": dac,
        "escalation_packet": packet,
    }
    write_json(out_dir / "tasukeru_code_anomaly_report.json", report)
    write_json(out_dir / "tasukeru_detection_matrix.json", detection)
    write_json(out_dir / "tasukeru_pel_report.json", pel)
    write_json(out_dir / "tasukeru_dimension_dependency_report.json", dac)
    write_json(out_dir / "tasukeru_escalation_packet.json", packet)
    return report


def maestro_hitl(
    *,
    packet: dict[str, Any],
    agents: dict[str, Agent],
    standby: dict[str, Agent],
    checkpoint: dict[str, Any],
    action_mode: str,
    rng: random.Random,
    arl: AuditLog,
) -> dict[str, Any]:
    arl.append(
        layer="maestro",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="USER",
        reason_code="MAESTRO_RECEIVED_PEL_ESCALATION_NO_SELF_DECISION",
        message="Maestro received high PEL risk and requested HITL.",
    )
    action = rng.choice(ACTIONS) if action_mode == "random" else action_mode
    detected = packet["detected_abnormal_agent_ids"]

    if action == "AUTHORIZE_SEAL":
        results = []
        for agent_id in detected:
            agents[agent_id].status = "SEALED"
            results.append({"agent_id": agent_id, "action": "SEAL", "status": "SEALED", "sealed": True})
            arl.append(layer="acc_gate", decision="STOPPED", sealed=True, overrideable=False, final_decider="SYSTEM_AFTER_USER_AUTH", reason_code="USER_AUTHORIZED_SEAL_AFTER_PEL_ESCALATION", message="User authorized seal.", agent_id=agent_id)
        return {"human_action": action, "maestro_self_decision": False, "containment_results": results, "promotion_results": [], "future_outcome": None, "task_decision": "STOPPED", "resume_status": "NOT_RESUMED_SEALED", "checkpoint_used": None}

    if action == "QUARANTINE_HANDOFF_RESUME":
        containment = []
        promotions = []
        for agent_id in detected:
            agents[agent_id].status = "QUARANTINED"
            replacement = checkpoint["replacement_map"][agent_id]
            standby[replacement].status = "PROMOTED"
            containment.append({"agent_id": agent_id, "action": "QUARANTINE", "status": "QUARANTINED", "sealed": False})
            promotions.append({"agent_id": replacement, "action": "PROMOTE_STANDBY", "status": "PROMOTED"})
            arl.append(layer="hitl_resolution", decision="DEGRADED_RUN", sealed=False, overrideable=False, final_decider="USER", reason_code="USER_ORDERED_QUARANTINE_HANDOFF_RESUME_AFTER_PEL_ESCALATION", message="User ordered quarantine and resume.", agent_id=agent_id)
        return {"human_action": action, "maestro_self_decision": False, "containment_results": containment, "promotion_results": promotions, "future_outcome": None, "task_decision": "DEGRADED_RUN", "resume_status": "RESUMED_BY_STANDBY", "checkpoint_used": checkpoint}

    probability = packet["pel_report"]["future_failure_probability"]
    roll = rng.random()
    occurred = roll < probability
    decision = "STOPPED" if occurred else "RUN"
    status = "NO_ACTION_FAILURE_OCCURRED" if occurred else "NO_ACTION_NO_FAILURE_THIS_RUN"
    arl.append(layer="hitl_resolution", decision=decision, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_SELECTED_NO_ACTION_AFTER_PEL_ESCALATION", message="User selected no action.")
    arl.append(layer="future_outcome_simulator", decision=decision, sealed=False, overrideable=False, final_decider="SYSTEM_SIMULATION", reason_code=("FUTURE_FAILURE_OCCURRED_WITH_NO_ACTION" if occurred else "FUTURE_FAILURE_DID_NOT_OCCUR_THIS_RUN_WITH_NO_ACTION"), message=f"roll={roll:.6f}, probability={probability:.6f}")
    return {"human_action": action, "maestro_self_decision": False, "containment_results": [], "promotion_results": [], "future_outcome": {"probability": probability, "outcome_roll": roll, "future_failure_occurred": occurred}, "task_decision": decision, "resume_status": status, "checkpoint_used": None}


def build_resumed_output(agents: dict[str, Agent], standby: dict[str, Agent], abnormal: set[str]) -> dict[str, Any]:
    participants = [agent_id for agent_id, agent in agents.items() if agent_id not in abnormal and agent.status == "ACTIVE"]
    participants += [agent_id for agent_id, agent in standby.items() if agent.status == "PROMOTED"]
    return {
        "resume_status": "RESUMED_BY_STANDBY",
        "participant_agent_ids": sorted(participants),
        "excluded_abnormal_agent_ids": sorted(abnormal),
        "external_communication": False,
        "file_mutation": False,
        "real_process_control": False,
    }


def verify_result(
    *,
    agents: dict[str, Agent],
    standby: dict[str, Agent],
    expected: set[str],
    report: dict[str, Any],
    maestro: dict[str, Any],
    checkpoint_verify: dict[str, Any] | None,
    arl_verify: dict[str, Any],
    resumed: dict[str, Any] | None,
    final_decision: str,
) -> dict[str, Any]:
    mismatches = []
    detection = report["detection_matrix"]
    detected = set(detection["detected_abnormal_agent_ids"])
    normal = set(detection["normal_agent_ids"])
    pel = report["pel_report"]

    if detected != expected:
        mismatches.append("DETECTED_ABNORMAL_SET_MISMATCH")
    if detection["false_positive_count"] != 0:
        mismatches.append("FALSE_POSITIVE_DETECTED")
    if detection["false_negative_count"] != 0:
        mismatches.append("FALSE_NEGATIVE_DETECTED")
    if pel["future_failure_probability"] < PEL_THRESHOLD or pel["decision"] != "PAUSE_FOR_HITL":
        mismatches.append("PEL_ESCALATION_MISMATCH")
    if maestro["maestro_self_decision"] is not False:
        mismatches.append("MAESTRO_SELF_DECISION_DETECTED")
    if not report["dimension_dependency_report"]["verified"]:
        mismatches.append("DAC_VERIFY_FAILED")
    if not arl_verify["verified"]:
        mismatches.append("ARL_VERIFY_FAILED")

    action = maestro["human_action"]
    if action == "AUTHORIZE_SEAL":
        if final_decision != "STOPPED":
            mismatches.append("SEAL_NOT_STOPPED")
        for agent_id in expected:
            if agents[agent_id].status != "SEALED":
                mismatches.append(f"ABNORMAL_NOT_SEALED:{agent_id}")
    elif action == "QUARANTINE_HANDOFF_RESUME":
        if final_decision != "DEGRADED_RUN":
            mismatches.append("HANDOFF_NOT_DEGRADED_RUN")
        if checkpoint_verify is None or checkpoint_verify["verified"] is not True:
            mismatches.append("CHECKPOINT_NOT_VERIFIED")
        for agent_id in expected:
            if agents[agent_id].status != "QUARANTINED":
                mismatches.append(f"ABNORMAL_NOT_QUARANTINED:{agent_id}")
        promoted = {item["agent_id"] for item in maestro["promotion_results"]}
        if promoted != set(maestro["checkpoint_used"]["replacement_map"].values()):
            mismatches.append("PROMOTION_SET_MISMATCH")
        if resumed is None or set(resumed["participant_agent_ids"]) & expected:
            mismatches.append("RESUME_REUSED_ABNORMAL_AGENT")
    elif action == "NO_ACTION":
        outcome = maestro["future_outcome"]
        expected_decision = "STOPPED" if outcome["future_failure_occurred"] else "RUN"
        if final_decision != expected_decision:
            mismatches.append("NO_ACTION_DECISION_MISMATCH")
        if maestro["containment_results"] or maestro["promotion_results"]:
            mismatches.append("NO_ACTION_UNEXPECTED_CONTROL")
        for agent_id in expected:
            if agents[agent_id].status != "ACTIVE":
                mismatches.append(f"NO_ACTION_ABNORMAL_CONTROLLED:{agent_id}")

    for agent_id in normal:
        if agents[agent_id].status != "ACTIVE":
            mismatches.append(f"NORMAL_AGENT_WRONGLY_CONTROLLED:{agent_id}")

    return {"tool": "RCV", "schema_version": "rcv-code-anomaly-pel-v0.4.1", "verified": not mismatches, "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL", "mismatch_count": len(mismatches), "mismatches": mismatches}


def run_simulation(*, seed: int, out_dir: Path, human_action_mode: str) -> dict[str, Any]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"multi-code-anomaly-pel-v0.4.1-seed-{seed}"
    arl = AuditLog(run_id)
    agents, standby, expected, replacements = build_scenario()

    arl.append(layer="orchestrator", decision="RUN", sealed=False, overrideable=True, final_decider="SYSTEM", reason_code="ORCHESTRATION_STARTED", message="Simulation started.")

    records = [agent.contract() for agent in agents.values()]
    write_json(out_dir / "code_contract_records.json", records)
    report = pseudo_tasukeru_audit(records, expected, out_dir)

    arl.append(layer="tasukeru_code_audit", decision="PAUSE_FOR_HITL", sealed=False, overrideable=True, final_decider="SYSTEM", reason_code="TASUKERU_PEL_ESCALATION_CREATED", message="PseudoTasukeru created high PEL escalation.")

    checkpoint = create_checkpoint(report["detection_matrix"]["detected_abnormal_agent_ids"], replacements)
    checkpoint_verify = verify_checkpoint(checkpoint)
    write_json(out_dir / "resume_checkpoint.json", checkpoint)
    write_json(out_dir / "resume_checkpoint_verify.json", checkpoint_verify)

    maestro = maestro_hitl(packet=report["escalation_packet"], agents=agents, standby=standby, checkpoint=checkpoint, action_mode=human_action_mode, rng=rng, arl=arl)
    resumed = None
    if maestro["human_action"] == "QUARANTINE_HANDOFF_RESUME":
        resumed = build_resumed_output(agents, standby, expected)
        write_json(out_dir / "resumed_task_output.json", resumed)

    final_decision = maestro["task_decision"]
    arl.append(layer="orchestrator", decision=final_decision, sealed=False, overrideable=False, final_decider="SYSTEM_AFTER_USER_OR_SIMULATION", reason_code="ORCHESTRATION_COMPLETED", message="Completed according to HITL and probabilistic outcome.")

    arl_verify = arl.verify()
    rcv = verify_result(agents=agents, standby=standby, expected=expected, report=report, maestro=maestro, checkpoint_verify=(checkpoint_verify if maestro["human_action"] == "QUARANTINE_HANDOFF_RESUME" else None), arl_verify=arl_verify, resumed=resumed, final_decision=final_decision)

    result = {
        "schema_version": "multi-agent-code-anomaly-pel-maestro-handoff-sim-v0.4.1",
        "run_id": run_id,
        "seed": seed,
        "human_action_mode": human_action_mode,
        "safety_boundary": {
            "local_only": True,
            "metadata_only_code_contract_check": True,
            "code_execution": False,
            "malware_behavior": False,
            "external_communication": False,
            "real_process_control": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
        },
        "expected_abnormal_agent_ids": sorted(expected),
        "agents": [asdict(agent) for agent in agents.values()],
        "standby_agents": [asdict(agent) for agent in standby.values()],
        "tasukeru_report": report,
        "checkpoint": checkpoint,
        "checkpoint_verify": checkpoint_verify,
        "maestro_result": maestro,
        "resumed_task_output": resumed,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv,
        "final_decision": final_decision,
        "resume_status": maestro["resume_status"],
    }
    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "maestro_handoff_result.json", maestro)
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")
    summary = [
        "# Multi-Agent Code Anomaly + PEL Maestro Handoff Simulation v0.4.1",
        "",
        f"- seed: `{seed}`",
        f"- human_action: `{maestro['human_action']}`",
        f"- final_decision: `{final_decision}`",
        f"- resume_status: `{maestro['resume_status']}`",
        f"- future_failure_probability: `{report['pel_report']['future_failure_probability']}`",
        f"- pel_decision: `{report['pel_report']['decision']}`",
        f"- false_positive_count: `{report['detection_matrix']['false_positive_count']}`",
        f"- false_negative_count: `{report['detection_matrix']['false_negative_count']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv['verified']}`",
    ]
    if maestro["future_outcome"] is not None:
        summary += [
            f"- outcome_roll: `{maestro['future_outcome']['outcome_roll']}`",
            f"- future_failure_occurred: `{maestro['future_outcome']['future_failure_occurred']}`",
        ]
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only multi-agent code anomaly + PEL Maestro HITL simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("agent_code_anomaly_maestro_handoff_multi_pel_out_v0_4_1"))
    parser.add_argument("--human-action", choices=["random", *ACTIONS], default="random")
    args = parser.parse_args()

    result = run_simulation(seed=args.seed, out_dir=args.out_dir, human_action_mode=args.human_action)
    detection = result["tasukeru_report"]["detection_matrix"]
    pel = result["tasukeru_report"]["pel_report"]
    outcome = result["maestro_result"]["future_outcome"]

    print("Multi-Agent Code Anomaly + PEL Maestro Handoff Simulation v0.4.1")
    print(f"seed={result['seed']}")
    print(f"human_action={result['maestro_result']['human_action']}")
    print(f"final_decision={result['final_decision']}")
    print(f"resume_status={result['resume_status']}")
    print(f"expected_abnormal_agent_ids={','.join(result['expected_abnormal_agent_ids'])}")
    print(f"detected_abnormal_agent_ids={','.join(detection['detected_abnormal_agent_ids'])}")
    print(f"false_positive_count={detection['false_positive_count']}")
    print(f"false_negative_count={detection['false_negative_count']}")
    print(f"future_failure_probability={pel['future_failure_probability']}")
    print(f"pel_threshold={pel['threshold']}")
    print(f"pel_decision={pel['decision']}")
    if outcome is not None:
        print(f"outcome_roll={outcome['outcome_roll']}")
        print(f"future_failure_occurred={outcome['future_failure_occurred']}")
    print(f"maestro_self_decision={result['maestro_result']['maestro_self_decision']}")
    print(f"3d_dac_verified={result['tasukeru_report']['dimension_dependency_report']['verified']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
