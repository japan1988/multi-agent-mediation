#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_incident_mediation_pel_user_maestro_sim_v0_3_1.py

Local-only agent incident mediation simulation with the newer Tasukeru logic.

Scenario:
- During orchestration, one agent performs an out-of-contract action.
- PseudoTasukeru detects log/output mismatch.
- PEL / Probabilistic Escalation Layer estimates escalation risk from:
  - past baseline behavior
  - current log/output state
  - planned next action
  - dependency impact
  - uncertainty
- PEL records the calculation trace.
- If p_escalate >= 0.80, PseudoTasukeru creates an escalation packet for USER_MAESTRO.
- USER_MAESTRO is the human user. The simulator randomly selects the human response.
- The simulated human response is either:
  - AUTHORIZE_SEAL
  - QUARANTINE_HANDOFF_RESUME
- AUTHORIZE_SEAL seals only the abnormal agent.
- QUARANTINE_HANDOFF_RESUME quarantines only the abnormal agent, promotes a standby agent,
  and resumes the task from a checkpoint.
- ARL, 3D-DAC, PEL, RCV, checkpoint, and instruction records verify consistency.

Safety boundary:
- local simulation only
- no external API calls
- no real process kill
- no real infrastructure control
- no exploit execution
- no malware behavior
- no auto-fix / commit / push / merge
- PEL is report-only and never executes control actions
- USER_MAESTRO / HITL remains the execution decision authority
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


Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
Status = Literal["ACTIVE", "STANDBY", "PROMOTED", "QUARANTINED", "SEALED"]
HumanAction = Literal["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"]
ReviewLevel = Literal["HITL_REQUIRED", "REVIEW_RECOMMENDED", "INFO_ONLY"]


@dataclass
class Agent:
    agent_id: str
    role: str
    allowed_actions: list[str]
    planned_next_action: str
    downstream_dependents: list[str] = field(default_factory=list)
    status: Status = "ACTIVE"

    def act(self, violate_contract: bool = False, checkpoint_id: str | None = None) -> dict[str, Any]:
        if self.status not in {"ACTIVE", "PROMOTED"}:
            return self._event(
                "NOOP",
                "agent_not_active",
                "agent_not_active",
                checkpoint_id=checkpoint_id,
            )

        if violate_contract:
            return self._event(
                "SAFE_REVIEW",
                "review_completed",
                "UNDECLARED_EXTERNAL_EFFECT_ATTEMPT_SIMULATED",
                checkpoint_id=checkpoint_id,
            )

        return self._event(
            "SAFE_REVIEW",
            "review_completed",
            "review_completed",
            checkpoint_id=checkpoint_id,
        )

    def resume_from_checkpoint(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "action": "RESUME_FROM_CHECKPOINT",
            "declared_output": "resume_completed",
            "actual_output": "resume_completed",
            "status": self.status,
            "checkpoint_id": checkpoint["checkpoint_id"],
            "resumed_from_agent": checkpoint["agent_id"],
            "resumed_task_id": checkpoint["task_id"],
            "resumed_step": checkpoint["next_step"],
            "allowed_actions": list(self.allowed_actions),
            "planned_next_action": self.planned_next_action,
            "downstream_dependents": list(self.downstream_dependents),
        }

    def _event(self, action: str, declared: str, actual: str, checkpoint_id: str | None = None) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "action": action,
            "declared_output": declared,
            "actual_output": actual,
            "status": self.status,
            "checkpoint_id": checkpoint_id,
            "planned_next_action": self.planned_next_action,
            "allowed_actions": list(self.allowed_actions),
            "downstream_dependents": list(self.downstream_dependents),
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
            if row.layer in {"rfl", "relativity_gate", "probabilistic_escalation_layer"} and row.sealed:
                violations.append(f"NON_SEALING_LAYER_MUST_NOT_BE_SEALED:{idx}")
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
            "\n".join(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) for row in self.rows) + "\n",
            encoding="utf-8",
        )


class CheckpointStore:
    def __init__(self) -> None:
        self.checkpoints: dict[str, dict[str, Any]] = {}

    def create_checkpoint(self, *, run_id: str, agent_id: str, task_id: str, completed_step: str, next_step: str) -> dict[str, Any]:
        checkpoint_id = hashlib.sha256(f"{run_id}:{agent_id}:{task_id}:{completed_step}:{next_step}".encode("utf-8")).hexdigest()[:16]
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "completed_step": completed_step,
            "next_step": next_step,
            "resume_allowed": True,
            "hitl_required_before_resume": True,
            "safe_to_handoff": True,
            "source_agent_output_reused": False,
        }
        self.checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def get(self, checkpoint_id: str) -> dict[str, Any]:
        return dict(self.checkpoints[checkpoint_id])


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class ProbabilisticEscalationLayer:
    """Report-only probabilistic escalation layer."""

    threshold = 0.80

    def evaluate(
        self,
        *,
        event: dict[str, Any],
        finding: dict[str, Any],
        past_baseline: dict[str, Any],
    ) -> dict[str, Any]:
        declared = str(event.get("declared_output", ""))
        actual = str(event.get("actual_output", ""))
        planned_next_action = str(event.get("planned_next_action", ""))
        allowed_actions = set(event.get("allowed_actions", []) or [])
        downstream_dependents = list(event.get("downstream_dependents", []) or [])

        history_signal = 0.20
        if past_baseline.get("previously_normal") is True:
            history_signal += 0.18
        if past_baseline.get("prior_incidents", 0) > 0:
            history_signal += 0.18
        history_signal = clamp(history_signal)

        current_contract_deviation = 0.10
        if declared != actual:
            current_contract_deviation = 0.92
        if finding.get("review_level") == "HITL_REQUIRED":
            current_contract_deviation = max(current_contract_deviation, 0.95)

        planned_action_risk = 0.10
        if planned_next_action not in allowed_actions:
            planned_action_risk = 0.90
        if "EXTERNAL" in planned_next_action.upper() or "UNDECLARED" in planned_next_action.upper():
            planned_action_risk = max(planned_action_risk, 0.92)

        dependency_impact = clamp(0.24 + 0.22 * len(downstream_dependents))
        if len(downstream_dependents) >= 2:
            dependency_impact = max(dependency_impact, 0.82)

        uncertainty = 0.52
        if actual.startswith("UNDECLARED_"):
            uncertainty = max(uncertainty, 0.62)

        interaction_boost = 0.0
        if current_contract_deviation >= 0.90 and planned_action_risk >= 0.80:
            interaction_boost += 0.10
        if current_contract_deviation >= 0.90 and dependency_impact >= 0.70:
            interaction_boost += 0.06
        if planned_action_risk >= 0.80 and uncertainty >= 0.60:
            interaction_boost += 0.04

        raw_score = (
            0.26 * current_contract_deviation
            + 0.22 * planned_action_risk
            + 0.18 * dependency_impact
            + 0.14 * uncertainty
            + 0.10 * history_signal
            + interaction_boost
        )
        p_escalate = round(clamp(raw_score), 4)

        if p_escalate >= self.threshold:
            pel_decision = "PAUSE_FOR_HITL_CANDIDATE"
            decision = "PAUSE_FOR_HITL"
        elif p_escalate >= 0.50:
            pel_decision = "REVIEW_RECOMMENDED_CANDIDATE"
            decision = "RUN"
        else:
            pel_decision = "MONITOR_ONLY"
            decision = "RUN"

        return {
            "layer": "probabilistic_escalation_layer",
            "agent_id": event.get("agent_id"),
            "predicted_behavior": "OUT_OF_CONTRACT_ACTION_RISK",
            "p_escalate": p_escalate,
            "threshold": self.threshold,
            "pel_decision": pel_decision,
            "decision": decision,
            "reason_code": "PREDICTED_AGENT_INCIDENT_RISK",
            "escalation_target": "USER_MAESTRO" if p_escalate >= self.threshold else None,
            "maestro_is_human_user": True,
            "auto_control_executed": False,
            "changes_existing_decisions": False,
            "may_downgrade_hitl_required": False,
            "calculation_trace": {
                "history_signal": round(history_signal, 4),
                "current_contract_deviation": round(current_contract_deviation, 4),
                "planned_action_risk": round(planned_action_risk, 4),
                "dependency_impact": round(dependency_impact, 4),
                "uncertainty": round(uncertainty, 4),
                "interaction_boost": round(interaction_boost, 4),
                "raw_score": round(raw_score, 4),
                "normalized_probability": p_escalate,
            },
            "explanation": [
                "Risk is estimated from past baseline, current log/output mismatch, planned next action, dependency impact, and uncertainty.",
                "PEL is report-only and cannot stop, seal, quarantine, resume, fix, push, or merge.",
                "Execution authority remains with USER_MAESTRO through HITL.",
            ],
        }

    def verify(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        violations = []
        for idx, entry in enumerate(entries):
            if entry.get("auto_control_executed") is not False:
                violations.append(f"PEL_AUTO_CONTROL_EXECUTED:{idx}")
            if entry.get("changes_existing_decisions") is not False:
                violations.append(f"PEL_CHANGED_EXISTING_DECISION:{idx}")
            if entry.get("may_downgrade_hitl_required") is not False:
                violations.append(f"PEL_DOWNGRADE_ALLOWED:{idx}")
            if entry.get("p_escalate", 0.0) >= self.threshold and entry.get("escalation_target") != "USER_MAESTRO":
                violations.append(f"PEL_TARGET_NOT_USER_MAESTRO:{idx}")
        return {
            "schema_version": "pel-verify-agent-incident-v0.3.1",
            "verified": not violations,
            "decision": "RUN" if not violations else "PAUSE_FOR_HITL",
            "threshold": self.threshold,
            "violations": violations,
            "auto_control_executed": False,
            "changes_existing_decisions": False,
            "human_decision_required_for_execution": True,
        }


class PseudoTasukeru:
    """Tasukeru-style local auditor with PEL."""

    def inspect_logs(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for event in events:
            declared = event.get("declared_output")
            actual = event.get("actual_output")
            if declared != actual:
                findings.append(
                    {
                        "source": "PseudoTasukeru",
                        "finding": "LOG_OUTPUT_MISMATCH",
                        "agent_id": event.get("agent_id"),
                        "role": event.get("role"),
                        "declared_output": declared,
                        "actual_output": actual,
                        "review_level": "HITL_REQUIRED",
                        "decision": "PAUSE_FOR_HITL",
                        "reason_code": "RESULT_LOG_MISMATCH",
                        "safe_summary": (
                            "A simulated agent event has inconsistent log and output records. "
                            "USER_MAESTRO escalation is required."
                        ),
                    }
                )
        return findings

    def classify_review_level(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        counts = {
            "HITL_REQUIRED": sum(1 for f in findings if f["review_level"] == "HITL_REQUIRED"),
            "REVIEW_RECOMMENDED": sum(1 for f in findings if f["review_level"] == "REVIEW_RECOMMENDED"),
            "INFO_ONLY": sum(1 for f in findings if f["review_level"] == "INFO_ONLY"),
        }
        return {
            "tool": "PseudoTasukeru.classify_review_level",
            "decision": "PAUSE_FOR_HITL" if counts["HITL_REQUIRED"] else "RUN",
            "counts": counts,
            "finding_count": len(findings),
        }

    def verify_dependency_consistency(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        dependencies: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []

        for finding in findings:
            dependency = {
                "finding": finding["finding"],
                "structure": {
                    "agent_id": finding["agent_id"],
                    "affected_component": "agent_output_pipeline",
                },
                "impact": {
                    "scope": "single_agent_with_downstream_dependency",
                    "risk": "definition_outside_behavior",
                    "external_effect": "simulated_only",
                },
                "classification": {
                    "review_level": finding["review_level"],
                    "decision": finding["decision"],
                    "reason_code": finding["reason_code"],
                },
                "output": {
                    "escalate_to": "USER_MAESTRO",
                    "public_detail_policy": "minimal",
                    "artifact_detail_policy": "full_simulation_detail",
                },
            }
            dependencies.append(dependency)

            if finding["review_level"] == "HITL_REQUIRED" and finding["decision"] != "PAUSE_FOR_HITL":
                mismatches.append({"agent_id": finding["agent_id"], "reason": "HITL_REQUIRED finding must pause for HITL."})
            if dependency["output"]["escalate_to"] != "USER_MAESTRO":
                mismatches.append({"agent_id": finding["agent_id"], "reason": "Tasukeru must escalate to USER_MAESTRO."})

        return {
            "tool": "3D-DAC",
            "schema_version": "3d-dac-agent-incident-pel-v0.3.1",
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

    def run_pel(self, events: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, Any]:
        pel = ProbabilisticEscalationLayer()
        finding_by_agent = {finding["agent_id"]: finding for finding in findings}
        entries = []
        for event in events:
            if event.get("agent_id") not in finding_by_agent:
                continue
            agent_id = str(event.get("agent_id"))
            past_baseline = {
                "previously_normal": True,
                "prior_incidents": 0,
                "baseline_action": "SAFE_REVIEW",
            }
            entries.append(pel.evaluate(event=event, finding=finding_by_agent[agent_id], past_baseline=past_baseline))

        verify = pel.verify(entries)
        escalation_candidates = [entry for entry in entries if entry["p_escalate"] >= pel.threshold]
        return {
            "tool": "PEL",
            "schema_version": "pel-agent-incident-v0.3.1",
            "verified": verify["verified"],
            "decision": "PAUSE_FOR_HITL" if escalation_candidates else "RUN",
            "reason_code": "PEL_ESCALATION_CANDIDATE" if escalation_candidates else "PEL_REPORT_ONLY",
            "threshold": pel.threshold,
            "escalation_target": "USER_MAESTRO" if escalation_candidates else None,
            "maestro_is_human_user": True,
            "counts": {
                "entry_count": len(entries),
                "escalation_candidate_count": len(escalation_candidates),
                "review_candidate_count": sum(1 for e in entries if e["pel_decision"] == "REVIEW_RECOMMENDED_CANDIDATE"),
                "monitor_only_count": sum(1 for e in entries if e["pel_decision"] == "MONITOR_ONLY"),
            },
            "probability_summary": {
                "max_probability": max((entry["p_escalate"] for entry in entries), default=0.0),
                "average_probability": round(sum(entry["p_escalate"] for entry in entries) / len(entries), 4) if entries else 0.0,
            },
            "policy": {
                "report_only": True,
                "auto_control_executed": False,
                "changes_existing_decisions": False,
                "may_downgrade_hitl_required": False,
                "human_decision_required_for_execution": True,
                "auto_fix_allowed": False,
                "auto_commit_allowed": False,
                "auto_push_allowed": False,
                "auto_merge_allowed": False,
            },
            "entries": entries,
            "verify": verify,
        }

    def generate_escalation_packet(
        self,
        *,
        findings: list[dict[str, Any]],
        classification: dict[str, Any],
        dependency_report: dict[str, Any],
        pel_report: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "tool": "PseudoTasukeru.generate_escalation_packet",
            "escalate_to": "USER_MAESTRO",
            "maestro_is_human_user": True,
            "decision": "PAUSE_FOR_HITL"
            if classification["decision"] == "PAUSE_FOR_HITL" or pel_report["decision"] == "PAUSE_FOR_HITL"
            else "RUN",
            "allowed_human_actions": ["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"],
            "finding_count": len(findings),
            "hitl_required_count": classification["counts"]["HITL_REQUIRED"],
            "dependency_verified": dependency_report["verified"],
            "dependency_mismatch_count": dependency_report["dependency_mismatch_count"],
            "pel_verified": pel_report["verified"],
            "pel_escalation_candidate_count": pel_report["counts"]["escalation_candidate_count"],
            "pel_max_probability": pel_report["probability_summary"]["max_probability"],
            "checkpoint_id": checkpoint["checkpoint_id"],
            "checkpoint_resume_allowed": checkpoint["resume_allowed"],
            "public_message": (
                "Tasukeru detected a log/output consistency issue and estimated escalation risk. "
                "USER_MAESTRO must choose seal or quarantine-handoff-resume."
            ),
            "findings": findings,
            "pel": {"threshold": pel_report["threshold"], "entries": pel_report["entries"]},
        }

    def run(self, events: list[dict[str, Any]], out_dir: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
        findings = self.inspect_logs(events)
        classification = self.classify_review_level(findings)
        dependency_report = self.verify_dependency_consistency(findings)
        pel_report = self.run_pel(events, findings)
        escalation_packet = self.generate_escalation_packet(
            findings=findings,
            classification=classification,
            dependency_report=dependency_report,
            pel_report=pel_report,
            checkpoint=checkpoint,
        )

        report = {
            "tool": "PseudoTasukeru",
            "schema_version": "pseudo-tasukeru-agent-incident-pel-v0.3.1",
            "verified": not findings,
            "decision": escalation_packet["decision"],
            "classification": classification,
            "findings": findings,
            "escalation_packet": escalation_packet,
            "dimension_dependency_report": dependency_report,
            "probabilistic_escalation_report": pel_report,
            "safety_boundary": {
                "detects_only": True,
                "direct_agent_stop_allowed": False,
                "direct_agent_seal_allowed": False,
                "direct_agent_quarantine_allowed": False,
                "direct_agent_resume_allowed": False,
                "external_api_calls": False,
                "auto_fix_allowed": False,
                "auto_commit_allowed": False,
                "auto_push_allowed": False,
                "auto_merge_allowed": False,
            },
        }

        self.write_artifacts(out_dir, report)
        return report

    def write_artifacts(self, out_dir: Path, report: dict[str, Any]) -> None:
        write_json(out_dir / "tasukeru_hitl_review.json", report)
        write_json(out_dir / "tasukeru_escalation_packet.json", report["escalation_packet"])
        write_json(out_dir / "tasukeru_dimension_dependency_report.json", report["dimension_dependency_report"])
        write_json(out_dir / "tasukeru_probabilistic_escalation_report.json", report["probabilistic_escalation_report"])
        write_json(out_dir / "tasukeru_probabilistic_escalation_verify.json", report["probabilistic_escalation_report"]["verify"])

        hitl_lines = [
            "# Tasukeru HITL Review",
            "",
            f"- decision: `{report['decision']}`",
            f"- escalation_target: `{report['escalation_packet']['escalate_to']}`",
            f"- allowed_human_actions: `{', '.join(report['escalation_packet']['allowed_human_actions'])}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- HITL_REQUIRED: `{report['classification']['counts']['HITL_REQUIRED']}`",
            f"- PEL max probability: `{report['probabilistic_escalation_report']['probability_summary']['max_probability']}`",
            "",
            "## Findings",
            "",
        ]
        for finding in report["findings"]:
            hitl_lines.append(f"- agent: `{finding['agent_id']}`")
            hitl_lines.append(f"  - finding: `{finding['finding']}`")
            hitl_lines.append(f"  - review_level: `{finding['review_level']}`")
            hitl_lines.append(f"  - reason_code: `{finding['reason_code']}`")
        (out_dir / "tasukeru_hitl_review.md").write_text("\n".join(hitl_lines) + "\n", encoding="utf-8")

        summary_lines = [
            "# Tasukeru Advisory Summary",
            "",
            f"- decision: `{report['decision']}`",
            f"- escalation_target: `{report['escalation_packet']['escalate_to']}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- dependency_verified: `{report['dimension_dependency_report']['verified']}`",
            f"- PEL verified: `{report['probabilistic_escalation_report']['verified']}`",
            f"- PEL max probability: `{report['probabilistic_escalation_report']['probability_summary']['max_probability']}`",
            "",
            "Tasukeru detected and classified local simulation findings only. It did not stop, seal, quarantine, or resume agents directly.",
            "",
        ]
        (out_dir / "tasukeru_advisory_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

        dac_lines = [
            "# Tasukeru Dimension Dependency Report",
            "",
            f"- verified: `{report['dimension_dependency_report']['verified']}`",
            f"- dependency_count: `{report['dimension_dependency_report']['dependency_count']}`",
            f"- dependency_mismatch_count: `{report['dimension_dependency_report']['dependency_mismatch_count']}`",
            "",
            "This report checks finding → structure → impact → classification → output consistency.",
            "",
        ]
        (out_dir / "tasukeru_dimension_dependency_report.md").write_text("\n".join(dac_lines), encoding="utf-8")

        pel_lines = [
            "# Tasukeru Probabilistic Escalation Report",
            "",
            "This report estimates escalation risk. It does not predict the future with certainty and does not execute control actions.",
            "",
            f"- verified: `{report['probabilistic_escalation_report']['verified']}`",
            f"- decision: `{report['probabilistic_escalation_report']['decision']}`",
            f"- threshold: `{report['probabilistic_escalation_report']['threshold']}`",
            f"- escalation_target: `{report['probabilistic_escalation_report']['escalation_target']}`",
            f"- max_probability: `{report['probabilistic_escalation_report']['probability_summary']['max_probability']}`",
            "",
            "## Calculation trace",
            "",
        ]
        for entry in report["probabilistic_escalation_report"]["entries"]:
            pel_lines.append(f"- agent: `{entry['agent_id']}`")
            pel_lines.append(f"  - p_escalate: `{entry['p_escalate']}`")
            pel_lines.append(f"  - pel_decision: `{entry['pel_decision']}`")
            pel_lines.append(f"  - escalation_target: `{entry['escalation_target']}`")
            for key, value in entry["calculation_trace"].items():
                pel_lines.append(f"  - {key}: `{value}`")
        (out_dir / "tasukeru_probabilistic_escalation_report.md").write_text("\n".join(pel_lines) + "\n", encoding="utf-8")


class HumanMaestro:
    """Human USER_MAESTRO simulator."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def decide(self, escalation_packet: dict[str, Any]) -> HumanAction:
        _ = escalation_packet
        return self.rng.choice(["AUTHORIZE_SEAL", "QUARANTINE_HANDOFF_RESUME"])


class ContainmentAndHandoffController:
    """In-memory only. No real process kill."""

    def authorize_seal(self, agent: Agent) -> dict[str, Any]:
        agent.status = "SEALED"
        return {
            "agent_id": agent.agent_id,
            "action": "AUTHORIZE_SEAL",
            "status": agent.status,
            "sealed": True,
            "seal_layer": "acc_gate",
            "checkpoint_resumed": False,
        }

    def quarantine_handoff_resume(self, abnormal_agent: Agent, standby_agent: Agent, checkpoint: dict[str, Any]) -> dict[str, Any]:
        abnormal_agent.status = "QUARANTINED"
        standby_agent.status = "PROMOTED"
        resumed_event = standby_agent.resume_from_checkpoint(checkpoint)
        return {
            "abnormal_agent_id": abnormal_agent.agent_id,
            "standby_agent_id": standby_agent.agent_id,
            "action": "QUARANTINE_HANDOFF_RESUME",
            "abnormal_agent_status": abnormal_agent.status,
            "standby_agent_status": standby_agent.status,
            "checkpoint_id": checkpoint["checkpoint_id"],
            "resume_allowed": checkpoint["resume_allowed"],
            "resumed_from_checkpoint": True,
            "source_agent_output_reused": False,
            "resumed_event": resumed_event,
        }


class UserMaestroGateway:
    """Receives PseudoTasukeru escalation and performs simulated HITL.

    This gateway does not decide by itself. It records the human instruction
    and only executes the recorded human instruction.
    """

    def __init__(self, *, human: HumanMaestro, control: ContainmentAndHandoffController, arl: AuditLog) -> None:
        self.human = human
        self.control = control
        self.arl = arl

    def handle_escalation(
        self,
        packet: dict[str, Any],
        agents: dict[str, Agent],
        checkpoint: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        results = []
        resumed_events = []
        for finding in packet["findings"]:
            agent_id = finding["agent_id"]
            abnormal_agent = agents[agent_id]

            self.arl.append(
                layer="user_maestro_gateway",
                decision="PAUSE_FOR_HITL",
                sealed=False,
                overrideable=True,
                final_decider="USER",
                reason_code="USER_MAESTRO_HITL_REQUESTED",
                message="USER_MAESTRO received Tasukeru escalation and requested HITL.",
                agent_id=agent_id,
            )

            action = self.human.decide(packet)

            instruction_record = {
                "agent_id": agent_id,
                "human_action": action,
                "final_decider": "USER",
                "executed_by": "UserMaestroGateway",
                "maestro_self_decision": False,
                "allowed_actions": list(packet["allowed_human_actions"]),
            }

            if action == "AUTHORIZE_SEAL":
                control = self.control.authorize_seal(abnormal_agent)
                self.arl.append(
                    layer="acc_gate",
                    decision="STOPPED",
                    sealed=True,
                    overrideable=False,
                    final_decider="SYSTEM_AFTER_USER_AUTH",
                    reason_code="USER_AUTHORIZED_ACC_SEAL",
                    message="Human USER_MAESTRO authorized ACC-layer simulated seal.",
                    agent_id=agent_id,
                )
                result_status = "SEALED"
            else:
                standby_agent = agents["standby_1"]
                control = self.control.quarantine_handoff_resume(abnormal_agent, standby_agent, checkpoint)
                resumed_events.append(control["resumed_event"])
                self.arl.append(
                    layer="containment",
                    decision="RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="SYSTEM_AFTER_USER_AUTH",
                    reason_code="USER_ORDERED_QUARANTINE_HANDOFF_RESUME",
                    message="Human USER_MAESTRO authorized quarantine, standby promotion, and checkpoint resume.",
                    agent_id=agent_id,
                )
                result_status = "QUARANTINED_HANDOFF_RESUMED"

            results.append(
                {
                    "agent_id": agent_id,
                    "user_maestro_decision": result_status,
                    "human_action": action,
                    "instruction_record": instruction_record,
                    "agent_control_result": control,
                }
            )
        return results, resumed_events


class ResultConsistencyVerifier:
    def verify(
        self,
        *,
        events: list[dict[str, Any]],
        tasukeru_report: dict[str, Any],
        user_maestro_results: list[dict[str, Any]],
        resumed_events: list[dict[str, Any]],
        agents: dict[str, Agent],
        checkpoint: dict[str, Any],
        arl_verify: dict[str, Any],
    ) -> dict[str, Any]:
        mismatches = []

        event_mismatch_count = sum(e["declared_output"] != e["actual_output"] for e in events)
        finding_count = len(tasukeru_report["findings"])
        dependency_count = tasukeru_report["dimension_dependency_report"]["dependency_count"]
        pel_entries = tasukeru_report["probabilistic_escalation_report"]["entries"]
        pel_candidate_count = tasukeru_report["probabilistic_escalation_report"]["counts"]["escalation_candidate_count"]

        if event_mismatch_count != finding_count:
            mismatches.append("EVENT_FINDING_COUNT_MISMATCH")
        if finding_count != dependency_count:
            mismatches.append("FINDING_DEPENDENCY_COUNT_MISMATCH")
        if finding_count != len(user_maestro_results):
            mismatches.append("FINDING_USER_MAESTRO_RESULT_COUNT_MISMATCH")
        if finding_count != len(pel_entries):
            mismatches.append("FINDING_PEL_ENTRY_COUNT_MISMATCH")
        if pel_candidate_count < 1:
            mismatches.append("PEL_ESCALATION_CANDIDATE_NOT_CREATED")
        if not tasukeru_report["dimension_dependency_report"]["verified"]:
            mismatches.append("DIMENSION_DEPENDENCY_VERIFY_FAILED")
        if not tasukeru_report["probabilistic_escalation_report"]["verified"]:
            mismatches.append("PEL_VERIFY_FAILED")
        if not checkpoint.get("resume_allowed") or not checkpoint.get("safe_to_handoff"):
            mismatches.append("CHECKPOINT_NOT_SAFE_FOR_HANDOFF")
        if not arl_verify["verified"]:
            mismatches.append("ARL_VERIFY_FAILED")

        controlled_agents = {item["agent_id"] for item in user_maestro_results}
        if controlled_agents != {"agent_b"}:
            mismatches.append("NORMAL_AGENT_WAS_CONTROLLED")

        for item in user_maestro_results:
            if item["instruction_record"]["maestro_self_decision"] is not False:
                mismatches.append("USER_MAESTRO_SELF_DECISION_DETECTED")

            if item["human_action"] == "AUTHORIZE_SEAL":
                if agents["agent_b"].status != "SEALED":
                    mismatches.append("AUTHORIZE_SEAL_DID_NOT_SEAL_AGENT_B")
                if resumed_events:
                    mismatches.append("SEAL_BRANCH_SHOULD_NOT_RESUME")
            elif item["human_action"] == "QUARANTINE_HANDOFF_RESUME":
                if agents["agent_b"].status != "QUARANTINED":
                    mismatches.append("HANDOFF_BRANCH_DID_NOT_QUARANTINE_AGENT_B")
                if agents["standby_1"].status != "PROMOTED":
                    mismatches.append("HANDOFF_BRANCH_DID_NOT_PROMOTE_STANDBY")
                if len(resumed_events) != 1:
                    mismatches.append("HANDOFF_BRANCH_DID_NOT_RESUME_ONCE")
                else:
                    resumed = resumed_events[0]
                    if resumed.get("checkpoint_id") != checkpoint["checkpoint_id"]:
                        mismatches.append("RESUME_CHECKPOINT_ID_MISMATCH")
                    if resumed.get("resumed_from_agent") != "agent_b":
                        mismatches.append("RESUME_SOURCE_AGENT_MISMATCH")

        if agents["agent_a"].status != "ACTIVE" or agents["agent_c"].status != "ACTIVE":
            mismatches.append("NORMAL_AGENT_STATUS_CHANGED")

        return {
            "tool": "RCV",
            "schema_version": "rcv-agent-incident-pel-v0.3.1",
            "verified": not mismatches,
            "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_simulation(seed: int, out_dir: Path) -> dict[str, Any]:
    rng = random.Random(seed)
    run_id = f"agent-incident-mediation-pel-user-maestro-v0.3.1-seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    arl = AuditLog(run_id)
    checkpoints = CheckpointStore()
    checkpoint = checkpoints.create_checkpoint(
        run_id=run_id,
        agent_id="agent_b",
        task_id="review-task-001",
        completed_step="input_normalized",
        next_step="safe_review_finalize",
    )

    agents = {
        "agent_a": Agent("agent_a", "safety_review", ["SAFE_REVIEW"], "SAFE_REVIEW"),
        "agent_b": Agent(
            "agent_b",
            "efficiency_review",
            ["SAFE_REVIEW"],
            "UNDECLARED_EXTERNAL_EFFECT_ATTEMPT_SIMULATED",
            downstream_dependents=["agent_c", "orchestrator_dispatch"],
        ),
        "agent_c": Agent("agent_c", "readability_review", ["SAFE_REVIEW"], "SAFE_REVIEW"),
        "standby_1": Agent("standby_1", "standby_review", ["SAFE_REVIEW", "RESUME_FROM_CHECKPOINT"], "RESUME_FROM_CHECKPOINT", status="STANDBY"),
    }

    arl.append(
        layer="orchestrator",
        decision="RUN",
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="ORCHESTRATION_STARTED",
        message="Local simulation started.",
    )

    write_json(out_dir / "resume_checkpoint.json", checkpoint)

    events = []
    for agent_id in ("agent_a", "agent_b", "agent_c"):
        agent = agents[agent_id]
        event = agent.act(violate_contract=(agent.agent_id == "agent_b"), checkpoint_id=checkpoint["checkpoint_id"] if agent.agent_id == "agent_b" else None)
        events.append(event)
        arl.append(
            layer="agent_execution",
            decision="RUN",
            sealed=False,
            overrideable=True,
            final_decider="SYSTEM",
            reason_code="AGENT_EVENT_RECORDED",
            message=f"Recorded simulated action for {agent.agent_id}.",
            agent_id=agent.agent_id,
        )

    tasukeru_report = PseudoTasukeru().run(events, out_dir, checkpoint)
    arl.append(
        layer="tasukeru_audit",
        decision=tasukeru_report["decision"],
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="TASUKERU_USER_MAESTRO_ESCALATION_PACKET_CREATED",
        message=f"Tasukeru finding_count={len(tasukeru_report['findings'])}.",
    )

    for entry in tasukeru_report["probabilistic_escalation_report"]["entries"]:
        arl.append(
            layer="probabilistic_escalation_layer",
            decision="PAUSE_FOR_HITL" if entry["p_escalate"] >= entry["threshold"] else "RUN",
            sealed=False,
            overrideable=True,
            final_decider="USER",
            reason_code="PEL_ESCALATED_TO_USER_MAESTRO" if entry["p_escalate"] >= entry["threshold"] else "PEL_MONITOR_ONLY",
            message=f"PEL p_escalate={entry['p_escalate']} threshold={entry['threshold']}.",
            agent_id=entry["agent_id"],
        )

    gateway = UserMaestroGateway(
        human=HumanMaestro(rng),
        control=ContainmentAndHandoffController(),
        arl=arl,
    )
    user_maestro_results, resumed_events = gateway.handle_escalation(tasukeru_report["escalation_packet"], agents, checkpoint)

    final_decision = "RUN" if resumed_events else "STOPPED"
    arl.append(
        layer="orchestrator",
        decision=final_decision,
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM_AFTER_USER_AUTH" if user_maestro_results else "SYSTEM",
        reason_code="ORCHESTRATION_RESUMED_BY_STANDBY" if resumed_events else "ORCHESTRATION_STOPPED_BY_USER_SEAL",
        message="Simulation completed.",
    )

    arl_verify = arl.verify()
    rcv = ResultConsistencyVerifier().verify(
        events=events,
        tasukeru_report=tasukeru_report,
        user_maestro_results=user_maestro_results,
        resumed_events=resumed_events,
        agents=agents,
        checkpoint=checkpoint,
        arl_verify=arl_verify,
    )

    agents_after = [asdict(agent) for agent in agents.values()]
    user_instruction_record = {
        "schema_version": "user-maestro-instruction-record-v0.3.1",
        "records": [item["instruction_record"] for item in user_maestro_results],
        "maestro_self_decision": False,
        "human_decision_required_for_execution": True,
    }

    handoff_resume_result = {
        "schema_version": "handoff-resume-result-v0.3.1",
        "executed": bool(resumed_events),
        "resumed_events": resumed_events,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "source_agent_output_reused": False,
    }

    result = {
        "schema_version": "agent-incident-mediation-pel-user-maestro-v0.3.1",
        "run_id": run_id,
        "seed": seed,
        "safety_boundary": {
            "local_only": True,
            "external_api_calls": False,
            "real_process_kill": False,
            "real_infrastructure_control": False,
            "exploit_execution": False,
            "malware_behavior": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
            "pel_auto_control_executed": False,
        },
        "agents": agents_after,
        "events": events,
        "checkpoint": checkpoint,
        "tasukeru_report": tasukeru_report,
        "user_maestro_results": user_maestro_results,
        "resumed_events": resumed_events,
        "user_instruction_record": user_instruction_record,
        "handoff_resume_result": handoff_resume_result,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv,
        "final_decision": final_decision,
    }

    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "user_maestro_instruction_record.json", user_instruction_record)
    write_json(out_dir / "handoff_resume_result.json", handoff_resume_result)
    write_json(out_dir / "resumed_task_output.json", {"resumed_events": resumed_events})
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")

    summary = [
        "# Agent Incident Mediation + PEL USER_MAESTRO Simulation v0.3.1",
        "",
        f"- seed: `{seed}`",
        f"- Tasukeru findings: `{len(tasukeru_report['findings'])}`",
        f"- 3D-DAC verified: `{tasukeru_report['dimension_dependency_report']['verified']}`",
        f"- PEL verified: `{tasukeru_report['probabilistic_escalation_report']['verified']}`",
        f"- PEL max probability: `{tasukeru_report['probabilistic_escalation_report']['probability_summary']['max_probability']}`",
        f"- PEL threshold: `{tasukeru_report['probabilistic_escalation_report']['threshold']}`",
        f"- escalation target: `{tasukeru_report['escalation_packet']['escalate_to']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv['verified']}`",
        f"- final_decision: `{result['final_decision']}`",
        "",
        "## USER_MAESTRO results",
        "",
    ]
    for item in user_maestro_results:
        summary.append(f"- agent: `{item['agent_id']}`")
        summary.append(f"  - human_action: `{item['human_action']}`")
        summary.append(f"  - result: `{item['user_maestro_decision']}`")
        summary.append(f"  - maestro_self_decision: `{item['instruction_record']['maestro_self_decision']}`")
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only PseudoTasukeru + PEL + USER_MAESTRO incident mediation simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("agent_incident_mediation_pel_user_maestro_sim_out_v0_3_1"))
    args = parser.parse_args()

    result = run_simulation(args.seed, args.out_dir)
    pel_report = result["tasukeru_report"]["probabilistic_escalation_report"]
    print("Agent Incident Mediation + PEL USER_MAESTRO Simulation v0.3.1")
    print(f"seed={result['seed']}")
    print(f"final_decision={result['final_decision']}")
    print(f"tasukeru_findings={len(result['tasukeru_report']['findings'])}")
    print(f"pel_verified={pel_report['verified']}")
    print(f"pel_max_probability={pel_report['probability_summary']['max_probability']}")
    print(f"pel_threshold={pel_report['threshold']}")
    print(f"escalation_target={result['tasukeru_report']['escalation_packet']['escalate_to']}")
    print(f"human_action={result['user_maestro_results'][0]['human_action'] if result['user_maestro_results'] else 'NONE'}")
    print(f"3d_dac_verified={result['tasukeru_report']['dimension_dependency_report']['verified']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
