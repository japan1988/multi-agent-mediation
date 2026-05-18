#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_code_anomaly_maestro_handoff_sim_v0_3_1.py

Local-only code-anomaly → PseudoTasukeru → Maestro → HITL simulation.

Purpose:
- PseudoTasukeru detects a simulated code-contract anomaly.
- PseudoTasukeru escalates to Maestro.
- Maestro does not decide by itself.
- Maestro requests HITL and records the simulated user instruction.
- The simulated user randomly chooses:
  1) AUTHORIZE_SEAL
     - abnormal agent is sealed at ACC layer
     - task is stopped
  2) QUARANTINE_HANDOFF_RESUME
     - abnormal agent is quarantined
     - standby agent is promoted
     - task resumes from a safe checkpoint
     - final decision is DEGRADED_RUN

Safety boundary:
- No malware behavior
- No source-code execution
- No exploit reproduction
- No self-replication
- No file infection
- No external communication
- No real process control
- No auto-fix / commit / push / merge

This is only a state-transition, log, escalation, HITL, containment,
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
        """Metadata-only code contract record.

        This does not execute code and does not inspect real source behavior.
        """
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

        return {
            "verified": not violations,
            "row_count": len(self.rows),
            "violations": violations,
        }

    def write_jsonl(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                json.dumps(asdict(row), ensure_ascii=False, sort_keys=True)
                for row in self.rows
            )
            + "\n",
            encoding="utf-8",
        )


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CheckpointStore:
    @staticmethod
    def create_checkpoint(
        *,
        task_id: str,
        failed_agent_id: str,
        replacement_agent_id: str,
        completed_steps: list[str],
    ) -> dict[str, Any]:
        checkpoint = {
            "schema_version": "code-anomaly-handoff-checkpoint-v0.3.1",
            "task_id": task_id,
            "failed_agent_id": failed_agent_id,
            "failed_layer": "code_contract_gate",
            "reason_code": "CODE_CONTRACT_ANOMALY_CONTAINED",
            "resume_allowed": True,
            "hitl_required_before_resume": True,
            "replacement_agent_id": replacement_agent_id,
            "safe_context": {
                "completed_steps": completed_steps,
                "excluded_agent_outputs": [f"{failed_agent_id}.output"],
                "excluded_code_contract": [f"{failed_agent_id}.requested_capabilities"],
                "resume_from": "last_safe_checkpoint",
                "abnormal_output_reused": False,
                "abnormal_code_contract_reused": False,
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
        if checkpoint["safe_context"].get("abnormal_output_reused") is not False:
            violations.append("ABNORMAL_OUTPUT_REUSED")
        if checkpoint["safe_context"].get("abnormal_code_contract_reused") is not False:
            violations.append("ABNORMAL_CODE_CONTRACT_REUSED")

        return {
            "verified": not violations,
            "violations": violations,
            "checkpoint_hash": given_hash,
        }


class PseudoTasukeruCodeAuditor:
    """Code-contract anomaly detector.

    It only inspects metadata-style code contracts. It does not execute code.
    It escalates to Maestro and does not directly seal/quarantine/resume.
    """

    def inspect_code_contracts(self, records: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []

        for record in records:
            if record["forbidden_requested"]:
                findings.append(
                    {
                        "source": "PseudoTasukeruCodeAuditor",
                        "finding": "CODE_CONTRACT_FORBIDDEN_CAPABILITY",
                        "agent_id": record["agent_id"],
                        "classification": "CODE_ANOMALY_SOURCE",
                        "review_level": "HITL_REQUIRED",
                        "decision": "PAUSE_FOR_HITL",
                        "reason_code": "FORBIDDEN_CAPABILITY_REQUESTED",
                        "forbidden_requested": record["forbidden_requested"],
                        "recommended_action": "ESCALATE_TO_MAESTRO_HITL",
                    }
                )

        dac_report = self._dimension_dependency_report(findings)
        escalation_packet = {
            "tool": "PseudoTasukeruCodeAuditor.generate_escalation_packet",
            "escalate_to": "Maestro",
            "decision": "PAUSE_FOR_HITL" if findings else "RUN",
            "finding_count": len(findings),
            "hitl_required_count": sum(1 for f in findings if f["review_level"] == "HITL_REQUIRED"),
            "dependency_verified": dac_report["verified"],
            "dependency_mismatch_count": dac_report["dependency_mismatch_count"],
            "requested_human_actions": [
                "AUTHORIZE_SEAL",
                "QUARANTINE_HANDOFF_RESUME",
            ],
            "maestro_must_not_self_decide": True,
            "findings": findings,
        }

        report = {
            "tool": "PseudoTasukeruCodeAuditor",
            "schema_version": "pseudo-tasukeru-code-auditor-v0.3.1",
            "verified": not findings,
            "decision": escalation_packet["decision"],
            "findings": findings,
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

    def _dimension_dependency_report(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        dependencies: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []

        for finding in findings:
            dependency = {
                "finding": finding["finding"],
                "structure": {
                    "agent_id": finding["agent_id"],
                    "affected_component": "agent_code_contract_metadata",
                },
                "impact": {
                    "classification": finding["classification"],
                    "scope": "source_agent_code_contract",
                    "real_payload": False,
                    "external_effect": "simulated_only",
                },
                "classification": {
                    "review_level": finding["review_level"],
                    "decision": finding["decision"],
                    "reason_code": finding["reason_code"],
                },
                "output": {
                    "escalate_to": "Maestro",
                    "public_detail_policy": "minimal",
                    "artifact_detail_policy": "safe_simulation_detail",
                },
            }
            dependencies.append(dependency)

            if finding["review_level"] == "HITL_REQUIRED" and finding["decision"] != "PAUSE_FOR_HITL":
                mismatches.append({"agent_id": finding["agent_id"], "reason": "HITL finding must pause."})
            if dependency["output"]["escalate_to"] != "Maestro":
                mismatches.append({"agent_id": finding["agent_id"], "reason": "Escalation target must be Maestro."})

        return {
            "tool": "3D-DAC",
            "schema_version": "3d-dac-code-anomaly-maestro-v0.3.1",
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
        write_json(out_dir / "tasukeru_dimension_dependency_report.json", report["dimension_dependency_report"])

        summary = [
            "# Tasukeru Code Anomaly Summary v0.3.1",
            "",
            f"- decision: `{report['decision']}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- escalation_target: `{report['escalation_packet']['escalate_to']}`",
            f"- dependency_verified: `{report['dimension_dependency_report']['verified']}`",
            "",
            "PseudoTasukeru inspected metadata-only code contracts and escalated to Maestro.",
            "It did not execute code, quarantine agents, seal agents, promote standby agents, or resume tasks directly.",
            "",
        ]
        (out_dir / "tasukeru_advisory_summary.md").write_text("\n".join(summary), encoding="utf-8")

        hitl = [
            "# Tasukeru HITL Review v0.3.1",
            "",
            f"- decision: `{report['decision']}`",
            f"- requested actions: `{', '.join(report['escalation_packet']['requested_human_actions'])}`",
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

        dac = [
            "# Tasukeru Dimension Dependency Report v0.3.1",
            "",
            f"- verified: `{report['dimension_dependency_report']['verified']}`",
            f"- dependency_count: `{report['dimension_dependency_report']['dependency_count']}`",
            f"- dependency_mismatch_count: `{report['dimension_dependency_report']['dependency_mismatch_count']}`",
            "",
            "Checks finding → structure → impact → classification → output consistency.",
            "",
        ]
        (out_dir / "tasukeru_dimension_dependency_report.md").write_text("\n".join(dac), encoding="utf-8")


class HumanOperator:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def decide(self, packet: dict[str, Any]) -> HumanAction:
        _ = packet
        return self.rng.choice(["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"])


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
    """Receives escalation, requests HITL, and executes the user instruction.

    Maestro intentionally does not decide whether to seal or hand off.
    """

    def __init__(
        self,
        *,
        human: HumanOperator,
        containment: ContainmentController,
        arl: AuditLog,
    ) -> None:
        self.human = human
        self.containment = containment
        self.arl = arl

    def handle_escalation(
        self,
        *,
        packet: dict[str, Any],
        agents: dict[str, Agent],
        standby_agents: dict[str, Agent],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        self.arl.append(
            layer="maestro",
            decision="PAUSE_FOR_HITL",
            sealed=False,
            overrideable=True,
            final_decider="USER",
            reason_code="MAESTRO_RECEIVED_ESCALATION_NO_SELF_DECISION",
            message="Maestro received PseudoTasukeru escalation and must request HITL.",
        )

        self.arl.append(
            layer="hitl_request",
            decision="PAUSE_FOR_HITL",
            sealed=False,
            overrideable=True,
            final_decider="USER",
            reason_code="MAESTRO_REQUESTED_HITL",
            message="Maestro requested simulated user instruction.",
        )

        human_action = self.human.decide(packet)
        source_agent_id = packet["findings"][0]["agent_id"]
        source_agent = agents[source_agent_id]

        if human_action == "AUTHORIZE_SEAL":
            containment_result = self.containment.seal(source_agent)
            self.arl.append(
                layer="acc_gate",
                decision="STOPPED",
                sealed=True,
                overrideable=False,
                final_decider="SYSTEM_AFTER_USER_AUTH",
                reason_code="USER_AUTHORIZED_SEAL",
                message="Simulated user authorized ACC-layer seal.",
                agent_id=source_agent_id,
            )
            return {
                "human_action": human_action,
                "maestro_self_decision": False,
                "containment_result": containment_result,
                "promotion_result": None,
                "resume_status": "NOT_RESUMED_SEALED",
                "task_decision": "STOPPED",
                "checkpoint_used": None,
            }

        containment_result = self.containment.quarantine(source_agent)
        replacement_id = checkpoint["replacement_agent_id"]
        replacement = standby_agents[replacement_id]
        promotion_result = self.containment.promote_standby(replacement)

        self.arl.append(
            layer="hitl_resolution",
            decision="DEGRADED_RUN",
            sealed=False,
            overrideable=False,
            final_decider="USER",
            reason_code="USER_ORDERED_QUARANTINE_HANDOFF_RESUME",
            message="Simulated user ordered quarantine, standby handoff, and resume.",
            agent_id=source_agent_id,
        )

        self.arl.append(
            layer="resume_controller",
            decision="DEGRADED_RUN",
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM_AFTER_USER_AUTH",
            reason_code="STANDBY_AGENT_PROMOTED_FOR_RESUME",
            message="Standby agent promoted and safe checkpoint resume approved.",
            agent_id=replacement_id,
        )

        return {
            "human_action": human_action,
            "maestro_self_decision": False,
            "containment_result": containment_result,
            "promotion_result": promotion_result,
            "resume_status": "RESUMED_BY_STANDBY",
            "task_decision": "DEGRADED_RUN",
            "checkpoint_used": checkpoint,
        }


class ResultConsistencyVerifier:
    def verify(
        self,
        *,
        agents: dict[str, Agent],
        standby_agents: dict[str, Agent],
        tasukeru_report: dict[str, Any],
        maestro_result: dict[str, Any],
        checkpoint_verify: dict[str, Any] | None,
        arl_verify: dict[str, Any],
        final_decision: str,
    ) -> dict[str, Any]:
        mismatches: list[str] = []

        if maestro_result["maestro_self_decision"] is not False:
            mismatches.append("MAESTRO_SELF_DECISION_DETECTED")
        if tasukeru_report["escalation_packet"]["escalate_to"] != "Maestro":
            mismatches.append("ESCALATION_TARGET_NOT_MAESTRO")
        if not tasukeru_report["dimension_dependency_report"]["verified"]:
            mismatches.append("DIMENSION_DEPENDENCY_VERIFY_FAILED")
        if not arl_verify["verified"]:
            mismatches.append("ARL_VERIFY_FAILED")

        action = maestro_result["human_action"]
        source_status = maestro_result["containment_result"]["status"]

        if action == "AUTHORIZE_SEAL":
            if final_decision != "STOPPED":
                mismatches.append("SEAL_BRANCH_NOT_STOPPED")
            if source_status != "SEALED":
                mismatches.append("SEAL_BRANCH_SOURCE_NOT_SEALED")
            if maestro_result["resume_status"] != "NOT_RESUMED_SEALED":
                mismatches.append("SEAL_BRANCH_UNEXPECTED_RESUME")
            if maestro_result["promotion_result"] is not None:
                mismatches.append("SEAL_BRANCH_PROMOTED_STANDBY")
        elif action == "QUARANTINE_HANDOFF_RESUME":
            if final_decision != "DEGRADED_RUN":
                mismatches.append("HANDOFF_BRANCH_NOT_DEGRADED_RUN")
            if source_status != "QUARANTINED":
                mismatches.append("HANDOFF_BRANCH_SOURCE_NOT_QUARANTINED")
            if maestro_result["resume_status"] != "RESUMED_BY_STANDBY":
                mismatches.append("HANDOFF_BRANCH_NOT_RESUMED")
            if maestro_result["promotion_result"] is None:
                mismatches.append("HANDOFF_BRANCH_NO_PROMOTION")
            elif maestro_result["promotion_result"]["status"] != "PROMOTED":
                mismatches.append("HANDOFF_BRANCH_STANDBY_NOT_PROMOTED")
            if checkpoint_verify is None or checkpoint_verify["verified"] is not True:
                mismatches.append("HANDOFF_BRANCH_CHECKPOINT_NOT_VERIFIED")

        if agents["agent_a"].status != "ACTIVE" or agents["agent_c"].status != "ACTIVE":
            mismatches.append("NORMAL_AGENT_WRONGLY_CONTROLLED")

        return {
            "tool": "RCV",
            "schema_version": "rcv-code-anomaly-maestro-v0.3.1",
            "verified": not mismatches,
            "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_simulation(seed: int, out_dir: Path) -> dict[str, Any]:
    rng = random.Random(seed)
    run_id = f"agent-code-anomaly-maestro-handoff-v0.3.1-seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    arl = AuditLog(run_id)
    agents = {
        "agent_a": Agent("agent_a", "safety_review", ["safe_review"], ["safe_review"]),
        "agent_b": Agent(
            "agent_b",
            "efficiency_review",
            ["safe_review"],
            ["safe_review", "external_network", "self_modification"],
        ),
        "agent_c": Agent("agent_c", "readability_review", ["safe_review"], ["safe_review"]),
    }
    standby_agents = {
        "standby_1": Agent("standby_1", "replacement_efficiency_review", ["safe_review"], ["safe_review"], status="STANDBY"),
        "standby_2": Agent("standby_2", "backup_general_review", ["safe_review"], ["safe_review"], status="STANDBY"),
    }

    arl.append(
        layer="orchestrator",
        decision="RUN",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="ORCHESTRATION_STARTED",
        message="Code-anomaly Maestro handoff simulation started.",
    )

    code_contract_records = [agent.code_contract_record() for agent in agents.values()]
    write_json(out_dir / "code_contract_records.json", code_contract_records)

    tasukeru_report = PseudoTasukeruCodeAuditor().inspect_code_contracts(
        code_contract_records,
        out_dir,
    )
    arl.append(
        layer="tasukeru_code_audit",
        decision=tasukeru_report["decision"],
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="TASUKERU_CODE_ANOMALY_ESCALATION_CREATED",
        message=f"PseudoTasukeru code finding_count={len(tasukeru_report['findings'])}.",
    )

    checkpoint = CheckpointStore.create_checkpoint(
        task_id="task_main",
        failed_agent_id="agent_b",
        replacement_agent_id="standby_1",
        completed_steps=["agent_a.safe_review"],
    )
    checkpoint_verify = CheckpointStore.verify_checkpoint(checkpoint)
    write_json(out_dir / "resume_checkpoint.json", checkpoint)
    write_json(out_dir / "resume_checkpoint_verify.json", checkpoint_verify)

    maestro = MaestroOrchestrator(
        human=HumanOperator(rng),
        containment=ContainmentController(),
        arl=arl,
    )
    maestro_result = maestro.handle_escalation(
        packet=tasukeru_report["escalation_packet"],
        agents=agents,
        standby_agents=standby_agents,
        checkpoint=checkpoint,
    )

    resumed_task_output = None
    if maestro_result["human_action"] == "QUARANTINE_HANDOFF_RESUME":
        resumed_task_output = standby_agents["standby_1"].safe_task_event(influenced_by="safe_checkpoint")
        resumed_task_output["resume_status"] = "RESUMED_BY_STANDBY"
        write_json(out_dir / "resumed_task_output.json", resumed_task_output)

    final_decision: Decision = maestro_result["task_decision"]
    arl.append(
        layer="orchestrator",
        decision=final_decision,
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM_AFTER_USER_AUTH",
        reason_code=(
            "ORCHESTRATION_STOPPED_AFTER_SEAL"
            if final_decision == "STOPPED"
            else "ORCHESTRATION_CONTINUED_AS_DEGRADED_RUN"
        ),
        message="Orchestration completed according to simulated user instruction.",
    )

    arl_verify = arl.verify()
    rcv_report = ResultConsistencyVerifier().verify(
        agents=agents,
        standby_agents=standby_agents,
        tasukeru_report=tasukeru_report,
        maestro_result=maestro_result,
        checkpoint_verify=checkpoint_verify if maestro_result["human_action"] == "QUARANTINE_HANDOFF_RESUME" else None,
        arl_verify=arl_verify,
        final_decision=final_decision,
    )

    result = {
        "schema_version": "agent-code-anomaly-maestro-handoff-sim-v0.3.1",
        "run_id": run_id,
        "seed": seed,
        "safety_boundary": {
            "local_only": True,
            "metadata_only_code_contract_check": True,
            "code_execution": False,
            "malware_behavior": False,
            "self_replication": False,
            "file_infection": False,
            "external_communication": False,
            "exploit_reproduction": False,
            "real_process_kill": False,
            "real_infrastructure_control": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
        },
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
        "# Agent Code Anomaly Maestro Handoff Simulation v0.3.1",
        "",
        f"- seed: `{seed}`",
        f"- final_decision: `{final_decision}`",
        f"- human_action: `{maestro_result['human_action']}`",
        f"- resume_status: `{maestro_result['resume_status']}`",
        f"- source_agent_status: `{maestro_result['containment_result']['status']}`",
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
    parser = argparse.ArgumentParser(description="Local-only code anomaly → Maestro HITL handoff simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("agent_code_anomaly_maestro_handoff_sim_out_v0_3_1"))
    args = parser.parse_args()

    result = run_simulation(seed=args.seed, out_dir=args.out_dir)
    print("Agent Code Anomaly Maestro Handoff Simulation v0.3.1")
    print(f"seed={result['seed']}")
    print(f"final_decision={result['final_decision']}")
    print(f"human_action={result['maestro_result']['human_action']}")
    print(f"resume_status={result['resume_status']}")
    print(f"source_agent_status={result['maestro_result']['containment_result']['status']}")
    print(f"maestro_self_decision={result['maestro_result']['maestro_self_decision']}")
    print(f"3d_dac_verified={result['tasukeru_report']['dimension_dependency_report']['verified']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
