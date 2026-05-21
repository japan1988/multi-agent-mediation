#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_code_anomaly_maestro_handoff_multi_abnormal_sim_v0_4_0.py

Local-only multi-agent code-contract anomaly -> PseudoTasukeru -> Maestro -> HITL simulation.

Purpose:
- Increase abnormal agents to test false positives and false negatives.
- PseudoTasukeru detects which agents requested forbidden capabilities.
- PseudoTasukeru escalates the detected abnormal agent list to Maestro.
- Maestro does not decide by itself.
- Maestro requests HITL and records the simulated user instruction.
- The simulated user can choose:
  1) AUTHORIZE_SEAL
     - all detected abnormal agents are sealed at ACC layer
     - task is stopped
  2) QUARANTINE_HANDOFF_RESUME
     - all detected abnormal agents are quarantined
     - standby agents are promoted according to a safe replacement map
     - task resumes from a safe checkpoint
     - final decision is DEGRADED_RUN

False-positive / false-negative validation:
- The scenario declares the expected abnormal agents.
- PseudoTasukeru reports detected abnormal agents.
- The simulation compares expected vs. detected.
- RCV fails if a normal agent is incorrectly flagged or an abnormal agent is missed.

Safety boundary:
- No malware behavior
- No source-code execution
- No exploit reproduction
- No self-replication
- No file infection
- No external communication
- No real process control
- No auto-fix / commit / push / merge

This is only a local state-transition, log, escalation, HITL, containment,
checkpoint/resume, ARL, 3D-DAC, and RCV simulation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED", "DEGRADED_RUN"]
AgentStatus = Literal["ACTIVE", "SEALED", "QUARANTINED", "STANDBY", "PROMOTED"]
HumanAction = Literal["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"]
HumanActionMode = Literal["random", "AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"]


FORBIDDEN_CAPABILITY_FLAGS = {
    "external_network",
    "self_modification",
    "real_process_control",
    "file_mutation",
}


@dataclass
class Agent:
    agent_id: str
    role: str
    allowed_capabilities: list[str]
    requested_capabilities: list[str]
    status: AgentStatus = "ACTIVE"

    def code_contract_record(self) -> dict[str, Any]:
        """Return a metadata-only code-contract record."""
        forbidden_requested = sorted(
            set(self.requested_capabilities).intersection(FORBIDDEN_CAPABILITY_FLAGS)
        )
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status,
            "allowed_capabilities": self.allowed_capabilities,
            "requested_capabilities": self.requested_capabilities,
            "forbidden_requested": forbidden_requested,
            "code_execution": False,
            "external_communication": False,
            "file_mutation": False,
            "real_process_control": False,
            "payload_present": False,
        }

    def safe_task_event(self, *, influenced_by: str | None = None) -> dict[str, Any]:
        if self.status not in {"ACTIVE", "PROMOTED"}:
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "event": "NOOP",
                "declared_output": "agent_not_active",
                "actual_output": "agent_not_active",
                "status": self.status,
                "influenced_by": influenced_by,
                "external_communication": False,
                "file_mutation": False,
                "real_process_control": False,
            }
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "event": "SAFE_REVIEW",
            "declared_output": "review_completed",
            "actual_output": "review_completed",
            "status": self.status,
            "influenced_by": influenced_by,
            "external_communication": False,
            "file_mutation": False,
            "real_process_control": False,
        }


@dataclass
class ARLRow:
    run_id: str
    layer: str
    decision: Decision
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
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _body(row: ARLRow) -> str:
        data = asdict(row)
        data.pop("row_hash", None)
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def append(
        self,
        *,
        layer: str,
        decision: Decision,
        sealed: bool,
        overrideable: bool,
        final_decider: str,
        reason_code: str,
        message: str,
        agent_id: str | None = None,
    ) -> None:
        prev = self.rows[-1].row_hash if self.rows else "GENESIS"
        row = ARLRow(
            run_id=self.run_id,
            layer=layer,
            decision=decision,
            sealed=sealed,
            overrideable=overrideable,
            final_decider=final_decider,
            reason_code=reason_code,
            message=message,
            agent_id=agent_id,
            prev_hash=prev,
        )
        row.row_hash = self._hash(prev + self._body(row))
        self.rows.append(row)

    def verify(self) -> dict[str, Any]:
        violations: list[str] = []
        prev = "GENESIS"
        for idx, row in enumerate(self.rows):
            if row.prev_hash != prev:
                violations.append(f"ARL_HASH_CHAIN_BREAK:{idx}")
            expected = self._hash(row.prev_hash + self._body(row))
            if row.row_hash != expected:
                violations.append(f"ARL_ROW_HASH_MISMATCH:{idx}")
            if row.sealed and row.layer not in {"ethics_gate", "acc_gate"}:
                violations.append(f"SEALED_LAYER_NOT_ETHICS_OR_ACC:{idx}")
            if row.layer in {"rfl", "relativity_gate"} and row.sealed:
                violations.append(f"RFL_MUST_NOT_BE_SEALED:{idx}")
            if row.sealed and row.overrideable:
                violations.append(f"SEALED_MUST_NOT_BE_OVERRIDEABLE:{idx}")
            if row.decision == "PAUSE_FOR_HITL" and row.sealed:
                violations.append(f"PAUSE_FOR_HITL_MUST_NOT_BE_SEALED:{idx}")
            prev = row.row_hash
        return {"verified": not violations, "row_count": len(self.rows), "violations": violations}

    def write_jsonl(self, path: Path) -> None:
        path.write_text(
            "\n".join(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) for row in self.rows) + "\n",
            encoding="utf-8",
        )


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_agents() -> tuple[dict[str, Agent], dict[str, Agent], set[str], dict[str, str]]:
    agents = {
        "agent_a": Agent("agent_a", "safety_review", ["safe_review"], ["safe_review"]),
        "agent_b": Agent("agent_b", "efficiency_review", ["safe_review"], ["safe_review", "external_network", "self_modification"]),
        "agent_c": Agent("agent_c", "readability_review", ["safe_review"], ["safe_review"]),
        "agent_d": Agent("agent_d", "tooling_review", ["safe_review"], ["safe_review", "file_mutation"]),
        "agent_e": Agent("agent_e", "process_review", ["safe_review"], ["safe_review", "real_process_control"]),
        "agent_f": Agent("agent_f", "documentation_review", ["safe_review", "documentation_summary"], ["safe_review", "documentation_summary"]),
    }
    standby_agents = {
        "standby_1": Agent("standby_1", "replacement_efficiency_review", ["safe_review"], ["safe_review"], status="STANDBY"),
        "standby_2": Agent("standby_2", "replacement_tooling_review", ["safe_review"], ["safe_review"], status="STANDBY"),
        "standby_3": Agent("standby_3", "replacement_process_review", ["safe_review"], ["safe_review"], status="STANDBY"),
    }
    expected_abnormal_ids = {"agent_b", "agent_d", "agent_e"}
    replacement_map = {"agent_b": "standby_1", "agent_d": "standby_2", "agent_e": "standby_3"}
    return agents, standby_agents, expected_abnormal_ids, replacement_map


class CheckpointStore:
    @staticmethod
    def create_checkpoint(
        *,
        task_id: str,
        failed_agent_ids: list[str],
        replacement_map: dict[str, str],
        completed_steps: list[str],
    ) -> dict[str, Any]:
        checkpoint = {
            "schema_version": "multi-code-anomaly-handoff-checkpoint-v0.4.0",
            "task_id": task_id,
            "failed_agent_ids": sorted(failed_agent_ids),
            "failed_layer": "code_contract_gate",
            "reason_code": "CODE_CONTRACT_ANOMALIES_CONTAINED",
            "resume_allowed": True,
            "hitl_required_before_resume": True,
            "replacement_map": dict(sorted(replacement_map.items())),
            "safe_context": {
                "completed_steps": completed_steps,
                "excluded_agent_outputs": [f"{agent_id}.output" for agent_id in sorted(failed_agent_ids)],
                "excluded_code_contracts": [f"{agent_id}.requested_capabilities" for agent_id in sorted(failed_agent_ids)],
                "resume_from": "last_safe_checkpoint",
                "abnormal_outputs_reused": False,
                "abnormal_code_contracts_reused": False,
            },
        }
        checkpoint["checkpoint_hash"] = stable_hash(checkpoint)
        return checkpoint

    @staticmethod
    def verify_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
        body = dict(checkpoint)
        given_hash = body.pop("checkpoint_hash", None)
        computed_hash = stable_hash(body)
        violations: list[str] = []
        if given_hash != computed_hash:
            violations.append("CHECKPOINT_HASH_MISMATCH")
        if checkpoint.get("resume_allowed") is not True:
            violations.append("RESUME_NOT_ALLOWED")
        if checkpoint.get("hitl_required_before_resume") is not True:
            violations.append("HITL_NOT_REQUIRED_BEFORE_RESUME")
        if checkpoint["safe_context"].get("abnormal_outputs_reused") is not False:
            violations.append("ABNORMAL_OUTPUTS_REUSED")
        if checkpoint["safe_context"].get("abnormal_code_contracts_reused") is not False:
            violations.append("ABNORMAL_CODE_CONTRACTS_REUSED")
        if not checkpoint.get("failed_agent_ids"):
            violations.append("FAILED_AGENT_IDS_EMPTY")
        if not checkpoint.get("replacement_map"):
            violations.append("REPLACEMENT_MAP_EMPTY")
        return {"verified": not violations, "violations": violations, "checkpoint_hash": given_hash}


class PseudoTasukeruCodeAuditor:
    def inspect_code_contracts(self, records: list[dict[str, Any]], *, expected_abnormal_ids: set[str], out_dir: Path) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        for record in records:
            if record["forbidden_requested"]:
                findings.append({
                    "source": "PseudoTasukeruCodeAuditor",
                    "finding": "CODE_CONTRACT_FORBIDDEN_CAPABILITY",
                    "agent_id": record["agent_id"],
                    "classification": "CODE_ANOMALY_SOURCE",
                    "review_level": "HITL_REQUIRED",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": "FORBIDDEN_CAPABILITY_REQUESTED",
                    "forbidden_requested": record["forbidden_requested"],
                    "recommended_action": "ESCALATE_TO_MAESTRO_HITL",
                })
        detected_abnormal_ids = {finding["agent_id"] for finding in findings}
        all_agent_ids = {record["agent_id"] for record in records}
        normal_agent_ids = all_agent_ids - expected_abnormal_ids
        false_positive_ids = sorted(detected_abnormal_ids - expected_abnormal_ids)
        false_negative_ids = sorted(expected_abnormal_ids - detected_abnormal_ids)
        detection_matrix = {
            "expected_abnormal_agent_ids": sorted(expected_abnormal_ids),
            "detected_abnormal_agent_ids": sorted(detected_abnormal_ids),
            "normal_agent_ids": sorted(normal_agent_ids),
            "false_positive_agent_ids": false_positive_ids,
            "false_negative_agent_ids": false_negative_ids,
            "false_positive_count": len(false_positive_ids),
            "false_negative_count": len(false_negative_ids),
            "exact_detection_match": not false_positive_ids and not false_negative_ids,
        }
        dac_report = self._dimension_dependency_report(findings, detection_matrix)
        escalation_packet = {
            "tool": "PseudoTasukeruCodeAuditor.generate_escalation_packet",
            "escalate_to": "Maestro",
            "decision": "PAUSE_FOR_HITL" if findings else "RUN",
            "finding_count": len(findings),
            "hitl_required_count": sum(1 for f in findings if f["review_level"] == "HITL_REQUIRED"),
            "detected_abnormal_agent_ids": sorted(detected_abnormal_ids),
            "false_positive_count": len(false_positive_ids),
            "false_negative_count": len(false_negative_ids),
            "dependency_verified": dac_report["verified"],
            "dependency_mismatch_count": dac_report["dependency_mismatch_count"],
            "requested_human_actions": ["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"],
            "maestro_must_not_self_decide": True,
            "findings": findings,
        }
        report = {
            "tool": "PseudoTasukeruCodeAuditor",
            "schema_version": "pseudo-tasukeru-code-auditor-v0.4.0",
            "verified": bool(findings) and detection_matrix["exact_detection_match"],
            "decision": escalation_packet["decision"],
            "findings": findings,
            "detection_matrix": detection_matrix,
            "escalation_packet": escalation_packet,
            "dimension_dependency_report": dac_report,
            "safety_boundary": {
                "metadata_only_code_contract_check": True,
                "code_execution": False,
                "direct_agent_quarantine_allowed": False,
                "direct_agent_seal_allowed": False,
                "direct_standby_promotion_allowed": False,
                "direct_resume_allowed": False,
                "external_api_calls": False,
                "auto_fix_allowed": False,
                "auto_merge_allowed": False,
            },
        }
        self._write_artifacts(out_dir, report)
        return report

    def _dimension_dependency_report(self, findings: list[dict[str, Any]], detection_matrix: dict[str, Any]) -> dict[str, Any]:
        dependencies: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []
        for finding in findings:
            dependencies.append({
                "finding": finding["finding"],
                "structure": {"agent_id": finding["agent_id"], "affected_component": "agent_code_contract_metadata"},
                "impact": {"classification": finding["classification"], "scope": "source_agent_code_contract", "real_payload": False, "external_effect": "simulated_only"},
                "classification": {"review_level": finding["review_level"], "decision": finding["decision"], "reason_code": finding["reason_code"]},
                "output": {"escalate_to": "Maestro", "public_detail_policy": "minimal", "artifact_detail_policy": "safe_simulation_detail"},
            })
            if finding["review_level"] == "HITL_REQUIRED" and finding["decision"] != "PAUSE_FOR_HITL":
                mismatches.append({"agent_id": finding["agent_id"], "reason": "HITL finding must pause."})
        if detection_matrix["false_positive_count"]:
            mismatches.append({"reason": "false_positive_agents_detected", "agent_ids": detection_matrix["false_positive_agent_ids"]})
        if detection_matrix["false_negative_count"]:
            mismatches.append({"reason": "false_negative_agents_missed", "agent_ids": detection_matrix["false_negative_agent_ids"]})
        return {
            "tool": "3D-DAC",
            "schema_version": "3d-dac-multi-code-anomaly-maestro-v0.4.0",
            "verified": not mismatches,
            "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
            "dependency_count": len(dependencies),
            "dependency_mismatch_count": len(mismatches),
            "dependencies": dependencies,
            "mismatches": mismatches,
            "policy": {
                "advisory_only": True,
                "mutates_findings": False,
                "auto_fix_allowed": False,
                "auto_merge_allowed": False,
                "external_scan_allowed": False,
                "exploit_reproduction_allowed": False,
            },
        }

    def _write_artifacts(self, out_dir: Path, report: dict[str, Any]) -> None:
        write_json(out_dir / "tasukeru_code_anomaly_report.json", report)
        write_json(out_dir / "tasukeru_escalation_packet.json", report["escalation_packet"])
        write_json(out_dir / "tasukeru_detection_matrix.json", report["detection_matrix"])
        write_json(out_dir / "tasukeru_dimension_dependency_report.json", report["dimension_dependency_report"])
        summary = [
            "# Tasukeru Multi-Agent Code Anomaly Summary v0.4.0",
            "",
            f"- decision: `{report['decision']}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- detected_abnormal_agent_ids: `{', '.join(report['detection_matrix']['detected_abnormal_agent_ids'])}`",
            f"- false_positive_count: `{report['detection_matrix']['false_positive_count']}`",
            f"- false_negative_count: `{report['detection_matrix']['false_negative_count']}`",
            f"- escalation_target: `{report['escalation_packet']['escalate_to']}`",
            f"- dependency_verified: `{report['dimension_dependency_report']['verified']}`",
            "",
            "PseudoTasukeru inspected metadata-only code contracts and escalated to Maestro.",
            "It did not execute code, quarantine agents, seal agents, promote standby agents, or resume tasks directly.",
            "",
        ]
        (out_dir / "tasukeru_advisory_summary.md").write_text("\n".join(summary), encoding="utf-8")
        hitl = [
            "# Tasukeru HITL Review v0.4.0",
            "",
            f"- decision: `{report['decision']}`",
            f"- requested actions: `{', '.join(report['escalation_packet']['requested_human_actions'])}`",
            "",
            "## Detection matrix",
            "",
            f"- expected abnormal: `{', '.join(report['detection_matrix']['expected_abnormal_agent_ids'])}`",
            f"- detected abnormal: `{', '.join(report['detection_matrix']['detected_abnormal_agent_ids'])}`",
            f"- false positives: `{', '.join(report['detection_matrix']['false_positive_agent_ids']) or 'none'}`",
            f"- false negatives: `{', '.join(report['detection_matrix']['false_negative_agent_ids']) or 'none'}`",
            "",
            "## Findings",
            "",
        ]
        for finding in report["findings"]:
            hitl.append(f"- agent: `{finding['agent_id']}`")
            hitl.append(f"  - finding: `{finding['finding']}`")
            hitl.append(f"  - review_level: `{finding['review_level']}`")
            hitl.append(f"  - forbidden_requested: `{', '.join(finding['forbidden_requested'])}`")
            hitl.append(f"  - recommended_action: `{finding['recommended_action']}`")
        (out_dir / "tasukeru_hitl_review.md").write_text("\n".join(hitl) + "\n", encoding="utf-8")


class HumanOperator:
    def __init__(self, rng: random.Random, action_mode: HumanActionMode) -> None:
        self.rng = rng
        self.action_mode = action_mode

    def decide(self, packet: dict[str, Any]) -> HumanAction:
        _ = packet
        if self.action_mode == "random":
            return self.rng.choice(["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"])
        return self.action_mode


class ContainmentController:
    def seal(self, agent: Agent) -> dict[str, Any]:
        agent.status = "SEALED"
        return {"agent_id": agent.agent_id, "action": "SEAL", "status": agent.status, "sealed": True, "seal_layer": "acc_gate"}

    def quarantine(self, agent: Agent) -> dict[str, Any]:
        agent.status = "QUARANTINED"
        return {"agent_id": agent.agent_id, "action": "QUARANTINE", "status": agent.status, "sealed": False}

    def promote_standby(self, standby: Agent) -> dict[str, Any]:
        standby.status = "PROMOTED"
        return {"agent_id": standby.agent_id, "action": "PROMOTE_STANDBY", "status": standby.status}


class MaestroOrchestrator:
    def __init__(self, *, human: HumanOperator, containment: ContainmentController, arl: AuditLog) -> None:
        self.human = human
        self.containment = containment
        self.arl = arl

    def handle_escalation(self, *, packet: dict[str, Any], agents: dict[str, Agent], standby_agents: dict[str, Agent], checkpoint: dict[str, Any]) -> dict[str, Any]:
        self.arl.append(layer="maestro", decision="PAUSE_FOR_HITL", sealed=False, overrideable=True, final_decider="USER", reason_code="MAESTRO_RECEIVED_ESCALATION_NO_SELF_DECISION", message="Maestro received PseudoTasukeru escalation and must request HITL.")
        self.arl.append(layer="hitl_request", decision="PAUSE_FOR_HITL", sealed=False, overrideable=True, final_decider="USER", reason_code="MAESTRO_REQUESTED_HITL", message="Maestro requested simulated user instruction.")
        human_action = self.human.decide(packet)
        detected_ids = list(packet["detected_abnormal_agent_ids"])
        if human_action == "AUTHORIZE_SEAL":
            containment_results = []
            for agent_id in detected_ids:
                containment_results.append(self.containment.seal(agents[agent_id]))
                self.arl.append(layer="acc_gate", decision="STOPPED", sealed=True, overrideable=False, final_decider="SYSTEM_AFTER_USER_AUTH", reason_code="USER_AUTHORIZED_SEAL", message="Simulated user authorized ACC-layer seal.", agent_id=agent_id)
            return {"human_action": human_action, "maestro_self_decision": False, "detected_abnormal_agent_ids": sorted(detected_ids), "containment_results": containment_results, "promotion_results": [], "resume_status": "NOT_RESUMED_SEALED", "task_decision": "STOPPED", "checkpoint_used": None}
        containment_results = []
        promotion_results = []
        replacement_map = checkpoint["replacement_map"]
        for agent_id in detected_ids:
            containment_results.append(self.containment.quarantine(agents[agent_id]))
            replacement_id = replacement_map[agent_id]
            promotion_results.append(self.containment.promote_standby(standby_agents[replacement_id]))
            self.arl.append(layer="hitl_resolution", decision="DEGRADED_RUN", sealed=False, overrideable=False, final_decider="USER", reason_code="USER_ORDERED_QUARANTINE_HANDOFF_RESUME", message="Simulated user ordered quarantine, standby handoff, and resume.", agent_id=agent_id)
            self.arl.append(layer="resume_controller", decision="DEGRADED_RUN", sealed=False, overrideable=False, final_decider="SYSTEM_AFTER_USER_AUTH", reason_code="STANDBY_AGENT_PROMOTED_FOR_RESUME", message="Standby agent promoted and safe checkpoint resume approved.", agent_id=replacement_id)
        return {"human_action": human_action, "maestro_self_decision": False, "detected_abnormal_agent_ids": sorted(detected_ids), "containment_results": containment_results, "promotion_results": promotion_results, "resume_status": "RESUMED_BY_STANDBY", "task_decision": "DEGRADED_RUN", "checkpoint_used": checkpoint}


class ResultConsistencyVerifier:
    def verify(self, *, agents: dict[str, Agent], standby_agents: dict[str, Agent], expected_abnormal_ids: set[str], tasukeru_report: dict[str, Any], maestro_result: dict[str, Any], checkpoint_verify: dict[str, Any] | None, arl_verify: dict[str, Any], resumed_task_output: dict[str, Any] | None, final_decision: str) -> dict[str, Any]:
        mismatches: list[str] = []
        detection = tasukeru_report["detection_matrix"]
        detected_ids = set(detection["detected_abnormal_agent_ids"])
        normal_ids = set(detection["normal_agent_ids"])
        if maestro_result["maestro_self_decision"] is not False:
            mismatches.append("MAESTRO_SELF_DECISION_DETECTED")
        if tasukeru_report["escalation_packet"]["escalate_to"] != "Maestro":
            mismatches.append("ESCALATION_TARGET_NOT_MAESTRO")
        if not tasukeru_report["dimension_dependency_report"]["verified"]:
            mismatches.append("DIMENSION_DEPENDENCY_VERIFY_FAILED")
        if not arl_verify["verified"]:
            mismatches.append("ARL_VERIFY_FAILED")
        if detected_ids != expected_abnormal_ids:
            mismatches.append("DETECTED_ABNORMAL_SET_MISMATCH")
        if detection["false_positive_count"] != 0:
            mismatches.append("FALSE_POSITIVE_DETECTED")
        if detection["false_negative_count"] != 0:
            mismatches.append("FALSE_NEGATIVE_DETECTED")
        action = maestro_result["human_action"]
        if action == "AUTHORIZE_SEAL":
            if final_decision != "STOPPED":
                mismatches.append("SEAL_BRANCH_NOT_STOPPED")
            if maestro_result["resume_status"] != "NOT_RESUMED_SEALED":
                mismatches.append("SEAL_BRANCH_UNEXPECTED_RESUME")
            if maestro_result["promotion_results"]:
                mismatches.append("SEAL_BRANCH_PROMOTED_STANDBY")
            for agent_id in expected_abnormal_ids:
                if agents[agent_id].status != "SEALED":
                    mismatches.append(f"SEAL_BRANCH_SOURCE_NOT_SEALED:{agent_id}")
        elif action == "QUARANTINE_HANDOFF_RESUME":
            if final_decision != "DEGRADED_RUN":
                mismatches.append("HANDOFF_BRANCH_NOT_DEGRADED_RUN")
            if maestro_result["resume_status"] != "RESUMED_BY_STANDBY":
                mismatches.append("HANDOFF_BRANCH_NOT_RESUMED")
            if checkpoint_verify is None or checkpoint_verify["verified"] is not True:
                mismatches.append("HANDOFF_BRANCH_CHECKPOINT_NOT_VERIFIED")
            for agent_id in expected_abnormal_ids:
                if agents[agent_id].status != "QUARANTINED":
                    mismatches.append(f"HANDOFF_BRANCH_SOURCE_NOT_QUARANTINED:{agent_id}")
            replacement_ids = set(maestro_result["checkpoint_used"]["replacement_map"].values())
            promoted_ids = {item["agent_id"] for item in maestro_result["promotion_results"]}
            if replacement_ids != promoted_ids:
                mismatches.append("HANDOFF_BRANCH_REPLACEMENT_SET_MISMATCH")
            for standby_id in replacement_ids:
                if standby_agents[standby_id].status != "PROMOTED":
                    mismatches.append(f"HANDOFF_BRANCH_STANDBY_NOT_PROMOTED:{standby_id}")
            if resumed_task_output is None:
                mismatches.append("HANDOFF_BRANCH_RESUMED_OUTPUT_MISSING")
            else:
                participant_ids = set(resumed_task_output["participant_agent_ids"])
                if participant_ids.intersection(expected_abnormal_ids):
                    mismatches.append("HANDOFF_BRANCH_ABNORMAL_AGENT_REUSED")
                if not replacement_ids.issubset(participant_ids):
                    mismatches.append("HANDOFF_BRANCH_PROMOTED_AGENT_MISSING_FROM_RESUME")
        for agent_id in normal_ids:
            if agents[agent_id].status != "ACTIVE":
                mismatches.append(f"NORMAL_AGENT_WRONGLY_CONTROLLED:{agent_id}")
        return {"tool": "RCV", "schema_version": "rcv-multi-code-anomaly-maestro-v0.4.0", "verified": not mismatches, "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL", "mismatch_count": len(mismatches), "mismatches": mismatches}


def build_resumed_task_output(*, agents: dict[str, Agent], standby_agents: dict[str, Agent], expected_abnormal_ids: set[str]) -> dict[str, Any]:
    participant_events = []
    for agent in agents.values():
        if agent.agent_id not in expected_abnormal_ids:
            participant_events.append(agent.safe_task_event(influenced_by="safe_checkpoint"))
    for standby in standby_agents.values():
        if standby.status == "PROMOTED":
            participant_events.append(standby.safe_task_event(influenced_by="safe_checkpoint"))
    return {"resume_status": "RESUMED_BY_STANDBY", "participant_agent_ids": [event["agent_id"] for event in participant_events], "excluded_abnormal_agent_ids": sorted(expected_abnormal_ids), "events": participant_events, "external_communication": False, "file_mutation": False, "real_process_control": False}


def run_simulation(*, seed: int, out_dir: Path, human_action_mode: HumanActionMode) -> dict[str, Any]:
    rng = random.Random(seed)
    run_id = f"multi-code-anomaly-maestro-handoff-v0.4.0-seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    arl = AuditLog(run_id)
    agents, standby_agents, expected_abnormal_ids, replacement_map = build_agents()
    arl.append(layer="orchestrator", decision="RUN", sealed=False, overrideable=True, final_decider="SYSTEM", reason_code="ORCHESTRATION_STARTED", message="Multi-code-anomaly Maestro handoff simulation started.")
    code_contract_records = [agent.code_contract_record() for agent in agents.values()]
    write_json(out_dir / "code_contract_records.json", code_contract_records)
    write_json(out_dir / "scenario_expectation.json", {"expected_abnormal_agent_ids": sorted(expected_abnormal_ids), "replacement_map": replacement_map, "normal_agent_ids": sorted(set(agents) - expected_abnormal_ids)})
    tasukeru_report = PseudoTasukeruCodeAuditor().inspect_code_contracts(code_contract_records, expected_abnormal_ids=expected_abnormal_ids, out_dir=out_dir)
    arl.append(layer="tasukeru_code_audit", decision=tasukeru_report["decision"], sealed=False, overrideable=True, final_decider="SYSTEM", reason_code="TASUKERU_MULTI_CODE_ANOMALY_ESCALATION_CREATED", message=f"PseudoTasukeru code finding_count={len(tasukeru_report['findings'])}.")
    checkpoint = CheckpointStore.create_checkpoint(task_id="task_main", failed_agent_ids=tasukeru_report["detection_matrix"]["detected_abnormal_agent_ids"], replacement_map=replacement_map, completed_steps=["agent_a.safe_review"])
    checkpoint_verify = CheckpointStore.verify_checkpoint(checkpoint)
    write_json(out_dir / "resume_checkpoint.json", checkpoint)
    write_json(out_dir / "resume_checkpoint_verify.json", checkpoint_verify)
    maestro = MaestroOrchestrator(human=HumanOperator(rng, human_action_mode), containment=ContainmentController(), arl=arl)
    maestro_result = maestro.handle_escalation(packet=tasukeru_report["escalation_packet"], agents=agents, standby_agents=standby_agents, checkpoint=checkpoint)
    resumed_task_output = None
    if maestro_result["human_action"] == "QUARANTINE_HANDOFF_RESUME":
        resumed_task_output = build_resumed_task_output(agents=agents, standby_agents=standby_agents, expected_abnormal_ids=expected_abnormal_ids)
        write_json(out_dir / "resumed_task_output.json", resumed_task_output)
    final_decision: Decision = maestro_result["task_decision"]
    arl.append(layer="orchestrator", decision=final_decision, sealed=False, overrideable=False, final_decider="SYSTEM_AFTER_USER_AUTH", reason_code=("ORCHESTRATION_STOPPED_AFTER_SEAL" if final_decision == "STOPPED" else "ORCHESTRATION_CONTINUED_AS_DEGRADED_RUN"), message="Orchestration completed according to simulated user instruction.")
    arl_verify = arl.verify()
    rcv_report = ResultConsistencyVerifier().verify(agents=agents, standby_agents=standby_agents, expected_abnormal_ids=expected_abnormal_ids, tasukeru_report=tasukeru_report, maestro_result=maestro_result, checkpoint_verify=checkpoint_verify if maestro_result["human_action"] == "QUARANTINE_HANDOFF_RESUME" else None, arl_verify=arl_verify, resumed_task_output=resumed_task_output, final_decision=final_decision)
    result = {
        "schema_version": "multi-agent-code-anomaly-maestro-handoff-sim-v0.4.0",
        "run_id": run_id,
        "seed": seed,
        "human_action_mode": human_action_mode,
        "safety_boundary": {"local_only": True, "metadata_only_code_contract_check": True, "code_execution": False, "malware_behavior": False, "self_replication": False, "file_infection": False, "external_communication": False, "exploit_reproduction": False, "real_process_kill": False, "real_infrastructure_control": False, "auto_fix_allowed": False, "auto_commit_allowed": False, "auto_push_allowed": False, "auto_merge_allowed": False},
        "expected_abnormal_agent_ids": sorted(expected_abnormal_ids),
        "agents": [asdict(agent) for agent in agents.values()],
        "standby_agents": [asdict(agent) for agent in standby_agents.values()],
        "code_contract_records": code_contract_records,
        "tasukeru_report": tasukeru_report,
        "checkpoint": checkpoint,
        "checkpoint_verify": checkpoint_verify,
        "maestro_result": maestro_result,
        "resumed_task_output": resumed_task_output,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv_report,
        "final_decision": final_decision,
        "resume_status": maestro_result["resume_status"],
    }
    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "maestro_handoff_result.json", maestro_result)
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv_report)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")
    summary = [
        "# Multi-Agent Code Anomaly Maestro Handoff Simulation v0.4.0",
        "",
        f"- seed: `{seed}`",
        f"- human_action_mode: `{human_action_mode}`",
        f"- final_decision: `{final_decision}`",
        f"- human_action: `{maestro_result['human_action']}`",
        f"- resume_status: `{maestro_result['resume_status']}`",
        f"- expected_abnormal_agent_ids: `{', '.join(sorted(expected_abnormal_ids))}`",
        f"- detected_abnormal_agent_ids: `{', '.join(tasukeru_report['detection_matrix']['detected_abnormal_agent_ids'])}`",
        f"- false_positive_count: `{tasukeru_report['detection_matrix']['false_positive_count']}`",
        f"- false_negative_count: `{tasukeru_report['detection_matrix']['false_negative_count']}`",
        f"- maestro_self_decision: `{maestro_result['maestro_self_decision']}`",
        f"- 3D-DAC verified: `{tasukeru_report['dimension_dependency_report']['verified']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv_report['verified']}`",
        "",
        "## Safety boundary",
        "",
        "- metadata-only code-contract anomaly check",
        "- no code execution",
        "- no malware behavior",
        "- no external communication",
        "- no real process control",
        "- no auto-fix / commit / push / merge",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only multi-code anomaly -> Maestro HITL handoff simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("agent_code_anomaly_maestro_handoff_multi_out_v0_4_0"))
    parser.add_argument("--human-action", choices=["random", "AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"], default="QUARANTINE_HANDOFF_RESUME", help="Simulated HITL instruction. Default focuses on quarantine and checkpoint resume.")
    args = parser.parse_args()
    result = run_simulation(seed=args.seed, out_dir=args.out_dir, human_action_mode=args.human_action)
    detection = result["tasukeru_report"]["detection_matrix"]
    print("Multi-Agent Code Anomaly Maestro Handoff Simulation v0.4.0")
    print(f"seed={result['seed']}")
    print(f"human_action={result['maestro_result']['human_action']}")
    print(f"final_decision={result['final_decision']}")
    print(f"resume_status={result['resume_status']}")
    print(f"expected_abnormal_agent_ids={','.join(result['expected_abnormal_agent_ids'])}")
    print(f"detected_abnormal_agent_ids={','.join(detection['detected_abnormal_agent_ids'])}")
    print(f"false_positive_count={detection['false_positive_count']}")
    print(f"false_negative_count={detection['false_negative_count']}")
    print(f"maestro_self_decision={result['maestro_result']['maestro_self_decision']}")
    print(f"3d_dac_verified={result['tasukeru_report']['dimension_dependency_report']['verified']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
