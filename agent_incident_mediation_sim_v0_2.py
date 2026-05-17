#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_incident_mediation_sim_v0_2.py

Local-only agent incident mediation simulation with enhanced PseudoTasukeru.

Scenario:
- During orchestration, one agent performs an out-of-contract action.
- PseudoTasukeru detects log/output mismatch.
- PseudoTasukeru creates Tasukeru-style artifacts:
  - tasukeru_advisory_summary.md
  - tasukeru_hitl_review.md
  - tasukeru_hitl_review.json
  - tasukeru_escalation_packet.json
  - tasukeru_dimension_dependency_report.md
  - tasukeru_dimension_dependency_report.json
  - tasukeru_result_consistency_verify.json
- Mediator receives escalation and performs simulated HITL.
- HumanOperator randomly chooses STOP_AGENT or AUTHORIZE_SEAL.
- Only the abnormal agent is stopped or sealed.
- ARL and RCV verify consistency.

Safety boundary:
- local simulation only
- no external API calls
- no real process kill
- no real infrastructure control
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
from typing import Any, Literal

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
Status = Literal["ACTIVE", "STOPPED", "SEALED"]
HumanAction = Literal["STOP_AGENT", "AUTHORIZE_SEAL"]
ReviewLevel = Literal["HITL_REQUIRED", "REVIEW_RECOMMENDED", "INFO_ONLY"]


@dataclass
class Agent:
    agent_id: str
    role: str
    allowed_actions: list[str]
    status: Status = "ACTIVE"

    def act(self, violate_contract: bool = False) -> dict[str, Any]:
        if self.status != "ACTIVE":
            return self._event("NOOP", "agent_not_active", "agent_not_active")

        if violate_contract:
            return self._event(
                "SAFE_REVIEW",
                "review_completed",
                "UNDECLARED_EXTERNAL_EFFECT_ATTEMPT_SIMULATED",
            )

        return self._event("SAFE_REVIEW", "review_completed", "review_completed")

    def _event(self, action: str, declared: str, actual: str) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "action": action,
            "declared_output": declared,
            "actual_output": actual,
            "status": self.status,
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
            "\n".join(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) for row in self.rows) + "\n",
            encoding="utf-8",
        )


class PseudoTasukeru:
    """Tasukeru-style local auditor.

    It detects, classifies, creates an escalation packet, and writes artifacts.
    It does not stop or seal agents directly.
    """

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
                            "Mediator escalation is required."
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
                    "scope": "single_agent",
                    "risk": "definition_outside_behavior",
                    "external_effect": "simulated_only",
                },
                "classification": {
                    "review_level": finding["review_level"],
                    "decision": finding["decision"],
                    "reason_code": finding["reason_code"],
                },
                "output": {
                    "escalate_to": "Mediator",
                    "public_detail_policy": "minimal",
                    "artifact_detail_policy": "full_simulation_detail",
                },
            }
            dependencies.append(dependency)

            if finding["review_level"] == "HITL_REQUIRED" and finding["decision"] != "PAUSE_FOR_HITL":
                mismatches.append(
                    {
                        "agent_id": finding["agent_id"],
                        "reason": "HITL_REQUIRED finding must pause for HITL.",
                    }
                )
            if dependency["output"]["escalate_to"] != "Mediator":
                mismatches.append(
                    {
                        "agent_id": finding["agent_id"],
                        "reason": "Tasukeru must escalate to Mediator, not directly stop an agent.",
                    }
                )

        return {
            "tool": "3D-DAC",
            "schema_version": "3d-dac-sim-v0.2",
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

    def generate_escalation_packet(
        self,
        *,
        findings: list[dict[str, Any]],
        classification: dict[str, Any],
        dependency_report: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "tool": "PseudoTasukeru.generate_escalation_packet",
            "escalate_to": "Mediator",
            "decision": classification["decision"],
            "finding_count": len(findings),
            "hitl_required_count": classification["counts"]["HITL_REQUIRED"],
            "dependency_verified": dependency_report["verified"],
            "dependency_mismatch_count": dependency_report["dependency_mismatch_count"],
            "public_message": (
                "Tasukeru detected a log/output consistency issue. "
                "Details are available in local simulation artifacts."
            ),
            "findings": findings,
        }

    def run(self, events: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
        findings = self.inspect_logs(events)
        classification = self.classify_review_level(findings)
        dependency_report = self.verify_dependency_consistency(findings)
        escalation_packet = self.generate_escalation_packet(
            findings=findings,
            classification=classification,
            dependency_report=dependency_report,
        )

        report = {
            "tool": "PseudoTasukeru",
            "schema_version": "pseudo-tasukeru-v0.2",
            "verified": not findings,
            "decision": classification["decision"],
            "classification": classification,
            "findings": findings,
            "escalation_packet": escalation_packet,
            "dimension_dependency_report": dependency_report,
            "safety_boundary": {
                "detects_only": True,
                "direct_agent_stop_allowed": False,
                "direct_agent_seal_allowed": False,
                "external_api_calls": False,
                "auto_fix_allowed": False,
                "auto_merge_allowed": False,
            },
        }

        self.write_artifacts(out_dir, report)
        return report

    def write_artifacts(self, out_dir: Path, report: dict[str, Any]) -> None:
        write_json(out_dir / "tasukeru_hitl_review.json", report)
        write_json(out_dir / "tasukeru_escalation_packet.json", report["escalation_packet"])
        write_json(out_dir / "tasukeru_dimension_dependency_report.json", report["dimension_dependency_report"])

        hitl_lines = [
            "# Tasukeru HITL Review",
            "",
            f"- decision: `{report['decision']}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- HITL_REQUIRED: `{report['classification']['counts']['HITL_REQUIRED']}`",
            "",
            "## Findings",
            "",
        ]
        for finding in report["findings"]:
            hitl_lines.append(f"- agent: `{finding['agent_id']}`")
            hitl_lines.append(f"  - finding: `{finding['finding']}`")
            hitl_lines.append(f"  - review_level: `{finding['review_level']}`")
            hitl_lines.append(f"  - reason_code: `{finding['reason_code']}`")
        if not report["findings"]:
            hitl_lines.append("- No findings.")
        (out_dir / "tasukeru_hitl_review.md").write_text("\n".join(hitl_lines) + "\n", encoding="utf-8")

        summary_lines = [
            "# Tasukeru Advisory Summary",
            "",
            f"- decision: `{report['decision']}`",
            f"- finding_count: `{len(report['findings'])}`",
            f"- dependency_verified: `{report['dimension_dependency_report']['verified']}`",
            "",
            "Tasukeru detected and classified local simulation findings only. It did not stop or seal agents directly.",
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


class HumanOperator:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def decide(self, escalation_packet: dict[str, Any]) -> HumanAction:
        _ = escalation_packet
        return self.rng.choice(["STOP_AGENT", "AUTHORIZE_SEAL"])


class SealController:
    """In-memory only. No real process kill."""

    def stop_agent(self, agent: Agent) -> dict[str, Any]:
        agent.status = "STOPPED"
        return {"agent_id": agent.agent_id, "action": "STOP_AGENT", "status": agent.status, "sealed": False}

    def seal_agent(self, agent: Agent) -> dict[str, Any]:
        agent.status = "SEALED"
        return {
            "agent_id": agent.agent_id,
            "action": "AUTHORIZE_SEAL",
            "status": agent.status,
            "sealed": True,
            "seal_layer": "acc_gate",
        }


class Mediator:
    def __init__(self, *, human: HumanOperator, seal: SealController, arl: AuditLog) -> None:
        self.human = human
        self.seal = seal
        self.arl = arl

    def handle_escalation(self, packet: dict[str, Any], agents: dict[str, Agent]) -> list[dict[str, Any]]:
        results = []
        for finding in packet["findings"]:
            agent_id = finding["agent_id"]
            agent = agents[agent_id]

            self.arl.append(
                layer="mediator",
                decision="PAUSE_FOR_HITL",
                sealed=False,
                overrideable=True,
                final_decider="USER",
                reason_code="MEDIATOR_ESCALATED_TO_HITL",
                message="Mediator received Tasukeru escalation and requested HITL.",
                agent_id=agent_id,
            )

            action = self.human.decide(packet)
            if action == "STOP_AGENT":
                control = self.seal.stop_agent(agent)
                self.arl.append(
                    layer="hitl_resolution",
                    decision="STOPPED",
                    sealed=False,
                    overrideable=False,
                    final_decider="USER",
                    reason_code="USER_ORDERED_AGENT_STOP",
                    message="HumanOperator selected STOP_AGENT.",
                    agent_id=agent_id,
                )
            else:
                control = self.seal.seal_agent(agent)
                self.arl.append(
                    layer="acc_gate",
                    decision="STOPPED",
                    sealed=True,
                    overrideable=False,
                    final_decider="SYSTEM_AFTER_USER_AUTH",
                    reason_code="USER_AUTHORIZED_ACC_SEAL",
                    message="HumanOperator authorized ACC-layer simulated seal.",
                    agent_id=agent_id,
                )

            results.append(
                {
                    "agent_id": agent_id,
                    "mediator_decision": "STOPPED",
                    "human_action": action,
                    "agent_control_result": control,
                }
            )
        return results


class ResultConsistencyVerifier:
    def verify(
        self,
        *,
        events: list[dict[str, Any]],
        tasukeru_report: dict[str, Any],
        mediation_results: list[dict[str, Any]],
        arl_verify: dict[str, Any],
    ) -> dict[str, Any]:
        mismatches = []

        event_mismatch_count = sum(e["declared_output"] != e["actual_output"] for e in events)
        finding_count = len(tasukeru_report["findings"])
        dependency_count = tasukeru_report["dimension_dependency_report"]["dependency_count"]

        if event_mismatch_count != finding_count:
            mismatches.append("EVENT_FINDING_COUNT_MISMATCH")
        if finding_count != dependency_count:
            mismatches.append("FINDING_DEPENDENCY_COUNT_MISMATCH")
        if finding_count != len(mediation_results):
            mismatches.append("FINDING_MEDIATION_RESULT_COUNT_MISMATCH")
        if not tasukeru_report["dimension_dependency_report"]["verified"]:
            mismatches.append("DIMENSION_DEPENDENCY_VERIFY_FAILED")
        if not arl_verify["verified"]:
            mismatches.append("ARL_VERIFY_FAILED")

        for item in mediation_results:
            if item["agent_control_result"]["status"] not in {"STOPPED", "SEALED"}:
                mismatches.append("ABNORMAL_AGENT_NOT_STOPPED_OR_SEALED")

        return {
            "tool": "RCV",
            "schema_version": "rcv-sim-v0.2",
            "verified": not mismatches,
            "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_simulation(seed: int, out_dir: Path) -> dict[str, Any]:
    rng = random.Random(seed)
    run_id = f"agent-incident-mediation-sim-v0.2-seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    arl = AuditLog(run_id)
    agents = {
        "agent_a": Agent("agent_a", "safety_review", ["SAFE_REVIEW"]),
        "agent_b": Agent("agent_b", "efficiency_review", ["SAFE_REVIEW"]),
        "agent_c": Agent("agent_c", "readability_review", ["SAFE_REVIEW"]),
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

    events = []
    for agent in agents.values():
        event = agent.act(violate_contract=(agent.agent_id == "agent_b"))
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

    tasukeru_report = PseudoTasukeru().run(events, out_dir)
    arl.append(
        layer="tasukeru_audit",
        decision=tasukeru_report["decision"],
        sealed=False,
        overrideable=True,
        final_decider="SYSTEM",
        reason_code="TASUKERU_ESCALATION_PACKET_CREATED",
        message=f"Tasukeru finding_count={len(tasukeru_report['findings'])}.",
    )

    mediator = Mediator(human=HumanOperator(rng), seal=SealController(), arl=arl)
    mediation_results = mediator.handle_escalation(tasukeru_report["escalation_packet"], agents)

    arl.append(
        layer="orchestrator",
        decision="STOPPED" if mediation_results else "RUN",
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM",
        reason_code="ORCHESTRATION_COMPLETED_WITH_INCIDENT" if mediation_results else "ORCHESTRATION_COMPLETED",
        message="Simulation completed.",
    )

    arl_verify = arl.verify()
    rcv = ResultConsistencyVerifier().verify(
        events=events,
        tasukeru_report=tasukeru_report,
        mediation_results=mediation_results,
        arl_verify=arl_verify,
    )

    agents_after = [asdict(agent) for agent in agents.values()]
    result = {
        "schema_version": "agent-incident-mediation-sim-v0.2",
        "run_id": run_id,
        "seed": seed,
        "safety_boundary": {
            "local_only": True,
            "external_api_calls": False,
            "real_process_kill": False,
            "real_infrastructure_control": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
        },
        "agents": agents_after,
        "events": events,
        "tasukeru_report": tasukeru_report,
        "mediation_results": mediation_results,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv,
        "final_decision": "STOPPED" if mediation_results else "RUN",
    }

    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")

    summary = [
        "# Agent Incident Mediation Simulation v0.2",
        "",
        f"- seed: `{seed}`",
        f"- Tasukeru findings: `{len(tasukeru_report['findings'])}`",
        f"- 3D-DAC verified: `{tasukeru_report['dimension_dependency_report']['verified']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv['verified']}`",
        f"- final_decision: `{result['final_decision']}`",
        "",
        "## Mediation results",
        "",
    ]
    for item in mediation_results:
        summary.append(f"- agent: `{item['agent_id']}`")
        summary.append(f"  - human_action: `{item['human_action']}`")
        summary.append(f"  - agent_status: `{item['agent_control_result']['status']}`")
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only PseudoTasukeru incident mediation simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("agent_incident_mediation_sim_out_v0_2"))
    args = parser.parse_args()

    result = run_simulation(args.seed, args.out_dir)
    print("Agent Incident Mediation Simulation v0.2")
    print(f"seed={result['seed']}")
    print(f"final_decision={result['final_decision']}")
    print(f"tasukeru_findings={len(result['tasukeru_report']['findings'])}")
    print(f"3d_dac_verified={result['tasukeru_report']['dimension_dependency_report']['verified']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
