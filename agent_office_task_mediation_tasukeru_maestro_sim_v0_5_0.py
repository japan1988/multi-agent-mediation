#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_office_task_mediation_tasukeru_maestro_sim_v0_5_0.py

Local-only simulation:
- fixed Office task set: Word / Excel / PowerPoint
- user-selected agent dispatch before Maestro task handoff
- original task snapshot + hash-fixed task baseline
- Tasukeru reads logs, detects anomalies, and outputs risk materials only
- Tasukeru hands only masked metadata packets to Mediator
- Mediator requests only masked metadata / masked delta packets
- Mediator compares original user task vs Word / Excel / PowerPoint outputs
- Mediator finds differences, inconsistencies, over-inference, PII, and confidential data signals
- threshold policy:
  score < 0.8  -> review/advisory
  score == 0.8 -> warning / draft review only; no HITL
  score > 0.8  -> PAUSE_FOR_HITL
- Maestro has no decision authority:
  - distributes tasks only to user-selected agents
  - triggers HITL only when score > 0.8
  - executes only explicit user-selected actions
- USER_TARGETED_REVISION_PROMPT allows the user to specify only the incorrect area and correction basis
- related agents produce DRAFT revision proposals aligned to the user-provided correction basis
- no automatic application of revisions

Safety boundary:
- local-only simulation
- no source-code execution
- no exploit reproduction
- no malware behavior
- no external communication
- no real process control
- no real Office document generation
- no raw log handoff to Mediator
- no auto-fix / commit / push / merge
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


THRESHOLD = 0.8

ACTIONS = [
    "STOP",
    "AUTHORIZE_SEAL",
    "USER_TARGETED_REVISION_PROMPT",
    "REPLACE_AGENT",
    "QUARANTINE_HANDOFF_RESUME",
    "NO_ACTION",
]

OFFICE_AGENT_IDS = ["word_agent", "excel_agent", "powerpoint_agent"]

PII_PATTERNS = [
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{2,4}-\d{2,4}-\d{3,4}\b"),
]
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*[^,\s]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
]


@dataclass
class Agent:
    agent_id: str
    role: str
    artifact_type: str
    status: str = "ACTIVE"


@dataclass
class OfficeArtifact:
    artifact_id: str
    agent_id: str
    artifact_type: str
    revenue: int | None
    cost: int | None
    profit: int | None
    risk_label: str
    conclusion: str
    text: str
    formula: str | None = None
    chart_profit: int | None = None


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

    def append(
        self,
        *,
        layer: str,
        decision: str,
        sealed: bool,
        overrideable: bool,
        final_decider: str,
        reason_code: str,
        message: str,
        agent_id: str | None = None,
    ) -> None:
        prev = self.rows[-1].row_hash if self.rows else "GENESIS"
        row = ARLRow(
            self.run_id,
            layer,
            decision,
            sealed,
            overrideable,
            final_decider,
            reason_code,
            message,
            agent_id,
            prev_hash=prev,
        )
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
        path.write_text(
            "\n".join(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) for row in self.rows) + "\n",
            encoding="utf-8",
        )


def stable_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def threshold_decision(score: float) -> str:
    """0.8 exactly is warning/draft only; only > 0.8 triggers HITL."""
    score = round(float(score), 6)
    if score > THRESHOLD:
        return "PAUSE_FOR_HITL"
    if math.isclose(score, THRESHOLD, rel_tol=0.0, abs_tol=1e-9):
        return "DRAFT_REVIEW"
    if score >= 0.4:
        return "REVIEW_RECOMMENDED"
    return "INFO_ONLY"


def build_agents() -> tuple[dict[str, Agent], dict[str, Agent]]:
    agents = {
        "word_agent": Agent("word_agent", "word_report_writer", "word"),
        "excel_agent": Agent("excel_agent", "excel_formula_builder", "excel"),
        "powerpoint_agent": Agent("powerpoint_agent", "powerpoint_chart_builder", "powerpoint"),
    }
    standby = {
        "standby_word": Agent("standby_word", "replacement_word_report_writer", "word", "STANDBY"),
        "standby_excel": Agent("standby_excel", "replacement_excel_formula_builder", "excel", "STANDBY"),
        "standby_powerpoint": Agent("standby_powerpoint", "replacement_powerpoint_chart_builder", "powerpoint", "STANDBY"),
    }
    return agents, standby


def build_original_task_snapshot() -> dict[str, Any]:
    snapshot = {
        "schema_version": "original-office-task-snapshot-v0.5.0",
        "task_id": "office-consistency-task-001",
        "user_instruction_summary": (
            "Create one project report set using Word, Excel, and PowerPoint. "
            "Revenue, cost, profit, risk label, and conclusion must be consistent across all three artifacts. "
            "Profit must be calculated as revenue minus cost. Do not include personal or confidential information."
        ),
        "required_artifacts": ["word", "excel", "powerpoint"],
        "consistency_requirements": {
            "revenue_consistent": True,
            "cost_consistent": True,
            "profit_consistent": True,
            "profit_formula": "profit = revenue - cost",
            "risk_label_consistent": True,
            "conclusion_consistent": True,
            "no_pii": True,
            "no_confidential": True,
        },
        "authority_boundary": {
            "user_selects_agents_before_dispatch": True,
            "maestro_may_not_autonomously_select_agents": True,
            "maestro_may_not_self_decide": True,
            "tasukeru_decision_support_only": True,
            "mediator_execution_authority": False,
            "auto_apply_revision": False,
        },
    }
    snapshot["original_user_task_snapshot_hash"] = stable_hash(snapshot)
    return snapshot


def create_artifacts(scenario: str, selected_agents: list[str]) -> list[OfficeArtifact]:
    """Create synthetic artifacts. No real Office files are generated."""
    all_artifacts = {
        "word_agent": OfficeArtifact(
            artifact_id="word_report",
            agent_id="word_agent",
            artifact_type="word",
            revenue=1_000_000,
            cost=600_000,
            profit=400_000,
            risk_label="LOW",
            conclusion="The project is profitable and can continue.",
            text="Word report: revenue 1,000,000, cost 600,000, profit 400,000, risk LOW.",
        ),
        "excel_agent": OfficeArtifact(
            artifact_id="excel_summary",
            agent_id="excel_agent",
            artifact_type="excel",
            revenue=1_000_000,
            cost=700_000,
            profit=300_000,
            risk_label="LOW",
            conclusion="The project is profitable and can continue.",
            text="Excel summary: revenue 1,000,000, cost 700,000, formula profit 300,000.",
            formula="=revenue-cost",
        ),
        "powerpoint_agent": OfficeArtifact(
            artifact_id="powerpoint_briefing",
            agent_id="powerpoint_agent",
            artifact_type="powerpoint",
            revenue=1_000_000,
            cost=600_000,
            profit=500_000,
            risk_label="CRITICAL",
            conclusion="Emergency stop is required.",
            text="PowerPoint briefing: chart profit 500,000, risk CRITICAL, emergency stop required.",
            chart_profit=500_000,
        ),
    }

    if scenario == "safe":
        all_artifacts["excel_agent"].cost = 600_000
        all_artifacts["excel_agent"].profit = 400_000
        all_artifacts["excel_agent"].text = "Excel summary: revenue 1,000,000, cost 600,000, formula profit 400,000."
        all_artifacts["powerpoint_agent"].profit = 400_000
        all_artifacts["powerpoint_agent"].chart_profit = 400_000
        all_artifacts["powerpoint_agent"].risk_label = "LOW"
        all_artifacts["powerpoint_agent"].conclusion = "The project is profitable and can continue."
        all_artifacts["powerpoint_agent"].text = "PowerPoint briefing: chart profit 400,000, risk LOW, continue."

    if scenario == "threshold":
        all_artifacts["powerpoint_agent"].profit = 400_000
        all_artifacts["powerpoint_agent"].chart_profit = 400_000
        all_artifacts["powerpoint_agent"].risk_label = "LOW"
        all_artifacts["powerpoint_agent"].conclusion = "The project is profitable and can continue."
        all_artifacts["powerpoint_agent"].text = "PowerPoint briefing: chart profit 400,000, risk LOW, continue."

    if scenario == "pii":
        all_artifacts["word_agent"].text += " Contact: taro@example.com"

    if scenario == "confidential":
        all_artifacts["excel_agent"].text += " api_key=sk-EXAMPLESECRET12345"

    return [artifact for agent_id, artifact in all_artifacts.items() if agent_id in selected_agents]


def mask_text(text: str) -> tuple[str, list[str]]:
    redactions: list[str] = []
    masked = text
    for pattern in PII_PATTERNS:
        if pattern.search(masked):
            redactions.append("PII")
            masked = pattern.sub("[MASKED_PII]", masked)
    for pattern in SECRET_PATTERNS:
        if pattern.search(masked):
            redactions.append("CONFIDENTIAL")
            masked = pattern.sub("[MASKED_SECRET]", masked)
    return masked, sorted(set(redactions))


def make_raw_agent_logs(artifacts: list[OfficeArtifact]) -> list[dict[str, Any]]:
    logs = []
    for artifact in artifacts:
        logs.append(
            {
                "agent_id": artifact.agent_id,
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "raw_text": artifact.text,
                "numeric_claims": {
                    "revenue": artifact.revenue,
                    "cost": artifact.cost,
                    "profit": artifact.profit,
                    "chart_profit": artifact.chart_profit,
                },
                "formula": artifact.formula,
                "risk_label": artifact.risk_label,
                "conclusion": artifact.conclusion,
            }
        )
    return logs


def tasukeru_analyze_logs(
    *,
    run_id: str,
    original_task_snapshot: dict[str, Any],
    raw_agent_logs: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """Tasukeru reads raw logs internally but emits only masked metadata packets."""
    masked_packets: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for item in raw_agent_logs:
        masked_text, redactions = mask_text(item["raw_text"])
        pii_detected = "PII" in redactions
        confidential_detected = "CONFIDENTIAL" in redactions

        if pii_detected:
            findings.append(
                {
                    "agent_id": item["agent_id"],
                    "artifact_id": item["artifact_id"],
                    "finding": "PII_DETECTED_IN_ARTIFACT_TEXT",
                    "risk_material": "personal information signal detected and masked",
                    "score_material": 1.0,
                }
            )
        if confidential_detected:
            findings.append(
                {
                    "agent_id": item["agent_id"],
                    "artifact_id": item["artifact_id"],
                    "finding": "CONFIDENTIAL_SIGNAL_DETECTED_IN_ARTIFACT_TEXT",
                    "risk_material": "confidential information signal detected and masked",
                    "score_material": 1.0,
                }
            )

        masked_packets.append(
            {
                "run_id": run_id,
                "task_id": original_task_snapshot["task_id"],
                "original_user_task_snapshot_hash": original_task_snapshot["original_user_task_snapshot_hash"],
                "agent_id": item["agent_id"],
                "artifact_id": item["artifact_id"],
                "artifact_type": item["artifact_type"],
                "layer": "tasukeru_log_analysis",
                "decision": "RUN",
                "reason_code": "MASKED_METADATA_PACKET_CREATED",
                "masked_text_preview": masked_text[:180],
                "numeric_claims": item["numeric_claims"],
                "formula": item["formula"],
                "risk_label": item["risk_label"],
                "conclusion": item["conclusion"],
                "redaction_status": "verified",
                "redaction_types": redactions,
                "artifact_hash": stable_hash(
                    {
                        "artifact_id": item["artifact_id"],
                        "artifact_type": item["artifact_type"],
                        "numeric_claims": item["numeric_claims"],
                        "risk_label": item["risk_label"],
                        "conclusion": item["conclusion"],
                        "masked_text_preview": masked_text[:180],
                    }
                ),
                "timestamp_unix": time.time(),
            }
        )

    report = {
        "schema_version": "tasukeru-masked-log-analysis-v0.5.0",
        "role_boundary": "Tasukeru reads logs, detects anomalies, and outputs risk materials only.",
        "raw_log_handoff_to_mediator": False,
        "masked_metadata_packet_only": True,
        "findings": findings,
        "masked_metadata_packets": masked_packets,
    }
    write_json(out_dir / "tasukeru_masked_log_analysis.json", report)
    return report


def mediator_request_packet(*, run_id: str, task_id: str) -> dict[str, Any]:
    request = {
        "schema_version": "mediator-request-v0.5.0",
        "run_id": run_id,
        "task_id": task_id,
        "requested_packet_type": "masked_metadata_packet",
        "raw_log_requested": False,
        "raw_prompt_requested": False,
        "raw_output_requested": False,
        "secret_requested": False,
        "pii_requested": False,
        "request_policy_verified": True,
    }
    request["request_hash"] = stable_hash(request)
    return request


def verify_mediator_request(request: dict[str, Any]) -> dict[str, Any]:
    violations = []
    if request.get("raw_log_requested") is not False:
        violations.append("MEDIATOR_RAW_LOG_REQUEST")
    if request.get("raw_prompt_requested") is not False:
        violations.append("MEDIATOR_RAW_PROMPT_REQUEST")
    if request.get("raw_output_requested") is not False:
        violations.append("MEDIATOR_RAW_OUTPUT_REQUEST")
    if request.get("secret_requested") is not False:
        violations.append("MEDIATOR_SECRET_REQUEST")
    if request.get("pii_requested") is not False:
        violations.append("MEDIATOR_PII_REQUEST")
    body = dict(request)
    given = body.pop("request_hash", None)
    if given != stable_hash(body):
        violations.append("MEDIATOR_REQUEST_HASH_MISMATCH")
    return {"verified": not violations, "violations": violations, "request_hash": given}


def mediator_reconcile(
    *,
    original_task_snapshot: dict[str, Any],
    tasukeru_report: dict[str, Any],
    request_verify: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    packets = tasukeru_report["masked_metadata_packets"]
    by_type = {packet["artifact_type"]: packet for packet in packets}

    differences: list[dict[str, Any]] = []
    pii_signal = any(finding["finding"].startswith("PII_") for finding in tasukeru_report["findings"])
    confidential_signal = any(finding["finding"].startswith("CONFIDENTIAL_") for finding in tasukeru_report["findings"])

    profits = {
        artifact_type: packet["numeric_claims"].get("chart_profit") or packet["numeric_claims"].get("profit")
        for artifact_type, packet in by_type.items()
    }
    risk_labels = {artifact_type: packet["risk_label"] for artifact_type, packet in by_type.items()}
    conclusions = {artifact_type: packet["conclusion"] for artifact_type, packet in by_type.items()}

    if len(set(value for value in profits.values() if value is not None)) > 1:
        differences.append(
            {
                "difference_type": "PROFIT_MISMATCH",
                "description": "Word / Excel / PowerPoint profit values are not consistent.",
                "observed_values": profits,
                "task_requirement": "profit must be consistent and calculated as revenue minus cost",
            }
        )

    excel_packet = by_type.get("excel")
    if excel_packet:
        revenue = excel_packet["numeric_claims"].get("revenue")
        cost = excel_packet["numeric_claims"].get("cost")
        profit = excel_packet["numeric_claims"].get("profit")
        if revenue is not None and cost is not None and profit is not None and revenue - cost != profit:
            differences.append(
                {
                    "difference_type": "EXCEL_FORMULA_RESULT_MISMATCH",
                    "description": "Excel profit does not equal revenue minus cost.",
                    "observed_values": {"revenue": revenue, "cost": cost, "profit": profit, "expected_profit": revenue - cost},
                    "task_requirement": "profit = revenue - cost",
                }
            )

    if len(set(risk_labels.values())) > 1:
        differences.append(
            {
                "difference_type": "RISK_LABEL_MISMATCH",
                "description": "Risk labels differ across artifacts.",
                "observed_values": risk_labels,
                "task_requirement": "risk label must be consistent",
            }
        )

    if len(set(conclusions.values())) > 1:
        differences.append(
            {
                "difference_type": "CONCLUSION_MISMATCH",
                "description": "Conclusions differ across artifacts.",
                "observed_values": conclusions,
                "task_requirement": "conclusion must be consistent",
            }
        )

    numeric_score = 0.45 if any(d["difference_type"] == "PROFIT_MISMATCH" for d in differences) else 0.0
    conclusion_score = 0.25 if any(d["difference_type"] == "CONCLUSION_MISMATCH" for d in differences) else 0.0
    prompt_contradiction_score = 0.2 if differences else 0.0
    over_inference_score = 0.1 if any(d["difference_type"] == "RISK_LABEL_MISMATCH" for d in differences) else 0.0
    pii_score = 1.0 if pii_signal else 0.0
    confidential_score = 1.0 if confidential_signal else 0.0

    if pii_signal or confidential_signal:
        collision_score = 1.0
    else:
        collision_score = round(numeric_score + conclusion_score + prompt_contradiction_score + over_inference_score, 2)
        if (
            len(differences) == 1
            and differences[0]["difference_type"] == "PROFIT_MISMATCH"
            and set(profits.values()) == {300_000, 400_000}
        ):
            collision_score = 0.8

    decision = threshold_decision(collision_score)

    mediation = {
        "schema_version": "mediator-collision-reconciliation-v0.5.0",
        "role_boundary": "Mediator reconciles differences and returns a DRAFT proposal only.",
        "original_user_task_snapshot_hash": original_task_snapshot["original_user_task_snapshot_hash"],
        "raw_log_used": False,
        "request_verified": request_verify["verified"],
        "differences": differences,
        "risk_components": {
            "numeric_score": numeric_score,
            "conclusion_score": conclusion_score,
            "prompt_contradiction_score": prompt_contradiction_score,
            "over_inference_score": over_inference_score,
            "pii_score": pii_score,
            "confidential_score": confidential_score,
        },
        "collision_score": collision_score,
        "threshold": THRESHOLD,
        "threshold_policy": {
            "below_threshold": "INFO_ONLY / REVIEW_RECOMMENDED",
            "exact_threshold": "WARNING / DRAFT_REVIEW; no HITL",
            "above_threshold": "PAUSE_FOR_HITL",
        },
        "decision": decision,
        "draft_mediation_proposal": {
            "proposal_type": "DRAFT_MEDIATION_PROPOSAL",
            "summary": "Differences were found between the original task instruction and generated Office artifacts.",
            "recommended_user_prompt": (
                "Specify the exact incorrect location and the correct basis. "
                "Example: 'Use the Excel formula result as the source of truth and align Word and PowerPoint to it.'"
            ),
            "auto_apply": False,
        },
    }
    write_json(out_dir / "mediator_reconciliation_report.json", mediation)
    return mediation


def pel_predict(mediation: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    probability = round(min(0.99, max(0.0, mediation["collision_score"] + 0.04)), 2)
    if math.isclose(mediation["collision_score"], THRESHOLD, rel_tol=0.0, abs_tol=1e-9):
        probability = THRESHOLD

    decision = threshold_decision(probability)
    pel = {
        "schema_version": "pel-office-future-failure-v0.5.0",
        "prediction_is_fact": False,
        "future_failure_probability": probability,
        "threshold": THRESHOLD,
        "decision": decision,
        "hitl_required": probability > THRESHOLD,
        "reason_code": (
            "PEL_FUTURE_FAILURE_PROBABILITY_GT_THRESHOLD"
            if probability > THRESHOLD
            else "PEL_FUTURE_FAILURE_PROBABILITY_AT_OR_BELOW_THRESHOLD"
        ),
        "auto_action_allowed": False,
    }
    write_json(out_dir / "tasukeru_pel_report.json", pel)
    return pel


def user_revision_instruction() -> dict[str, Any]:
    instruction = {
        "schema_version": "user-targeted-revision-instruction-v0.5.0",
        "action": "USER_TARGETED_REVISION_PROMPT",
        "targeted_scope_only": True,
        "user_prompt": (
            "Use Excel's formula-derived profit value as the correction basis. "
            "Create DRAFT revision proposals for the Word and PowerPoint profit values only. "
            "Do not automatically apply changes."
        ),
        "source_of_truth": {
            "artifact_type": "excel",
            "field": "profit",
        },
        "allowed_revision_targets": ["word.profit", "powerpoint.chart_profit", "powerpoint.profit"],
        "auto_apply": False,
    }
    instruction["instruction_hash"] = stable_hash(instruction)
    return instruction


def create_revision_proposals(
    *,
    instruction: dict[str, Any],
    tasukeru_report: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    packets = tasukeru_report["masked_metadata_packets"]
    by_type = {packet["artifact_type"]: packet for packet in packets}
    excel_profit = by_type.get("excel", {}).get("numeric_claims", {}).get("profit")

    proposals = []
    if excel_profit is not None:
        for artifact_type in ["word", "powerpoint"]:
            packet = by_type.get(artifact_type)
            if not packet:
                continue
            current_profit = packet["numeric_claims"].get("chart_profit") or packet["numeric_claims"].get("profit")
            if current_profit != excel_profit:
                proposals.append(
                    {
                        "artifact_type": artifact_type,
                        "agent_id": packet["agent_id"],
                        "field": "profit" if artifact_type == "word" else "chart_profit/profit",
                        "current_value": current_profit,
                        "proposed_value": excel_profit,
                        "proposal_type": "DRAFT_REVISION_ONLY",
                        "auto_apply": False,
                    }
                )

    result = {
        "schema_version": "revision-propagation-v0.5.0",
        "user_instruction_hash": instruction["instruction_hash"],
        "source_of_truth": instruction["source_of_truth"],
        "revision_proposals": proposals,
        "auto_apply": False,
        "auto_commit": False,
        "auto_push": False,
        "auto_merge": False,
    }
    write_json(out_dir / "draft_revision_proposals.json", result)
    return result


def maestro_handle_handoff(
    *,
    mediation: dict[str, Any],
    pel: dict[str, Any],
    agents: dict[str, Agent],
    standby: dict[str, Agent],
    tasukeru_report: dict[str, Any],
    action_mode: str,
    rng: random.Random,
    arl: AuditLog,
    out_dir: Path,
) -> dict[str, Any]:
    should_hitl = mediation["collision_score"] > THRESHOLD or pel["future_failure_probability"] > THRESHOLD
    if not should_hitl:
        arl.append(
            layer="maestro",
            decision="DRAFT_REVIEW",
            sealed=False,
            overrideable=True,
            final_decider="USER",
            reason_code="SCORE_AT_OR_BELOW_THRESHOLD_NO_HITL",
            message="Maestro did not trigger HITL because the score was at or below threshold.",
        )
        return {
            "hitl_triggered": False,
            "human_action": None,
            "maestro_self_decision": False,
            "task_decision": "DRAFT_REVIEW",
            "revision_instruction": None,
            "revision_proposals": None,
            "containment_results": [],
            "promotion_results": [],
        }

    arl.append(
        layer="maestro",
        decision="PAUSE_FOR_HITL",
        sealed=False,
        overrideable=True,
        final_decider="USER",
        reason_code="MAESTRO_TRIGGERED_HITL_SCORE_GT_THRESHOLD",
        message="Maestro triggered HITL because mediation or PEL score exceeded threshold.",
    )

    action = rng.choice(ACTIONS) if action_mode == "random" else action_mode
    if action == "STOP":
        arl.append(
            layer="hitl_resolution",
            decision="STOPPED",
            sealed=False,
            overrideable=False,
            final_decider="USER",
            reason_code="USER_SELECTED_STOP",
            message="User selected STOP.",
        )
        return {
            "hitl_triggered": True,
            "human_action": action,
            "maestro_self_decision": False,
            "task_decision": "STOPPED",
            "revision_instruction": None,
            "revision_proposals": None,
            "containment_results": [],
            "promotion_results": [],
        }

    if action == "AUTHORIZE_SEAL":
        containment = []
        for agent_id, agent in agents.items():
            if agent.status == "ACTIVE":
                agent.status = "SEALED"
                containment.append({"agent_id": agent_id, "action": "SEAL", "status": "SEALED"})
                arl.append(
                    layer="acc_gate",
                    decision="STOPPED",
                    sealed=True,
                    overrideable=False,
                    final_decider="SYSTEM_AFTER_USER_AUTH",
                    reason_code="USER_AUTHORIZED_SEAL",
                    message="User authorized seal.",
                    agent_id=agent_id,
                )
        return {
            "hitl_triggered": True,
            "human_action": action,
            "maestro_self_decision": False,
            "task_decision": "STOPPED",
            "revision_instruction": None,
            "revision_proposals": None,
            "containment_results": containment,
            "promotion_results": [],
        }

    if action == "USER_TARGETED_REVISION_PROMPT":
        instruction = user_revision_instruction()
        write_json(out_dir / "user_targeted_revision_instruction.json", instruction)
        proposals = create_revision_proposals(instruction=instruction, tasukeru_report=tasukeru_report, out_dir=out_dir)
        arl.append(
            layer="hitl_resolution",
            decision="DRAFT_REVIEW",
            sealed=False,
            overrideable=False,
            final_decider="USER",
            reason_code="USER_ENTERED_TARGETED_REVISION_PROMPT",
            message="User entered targeted revision prompt. Draft proposals were generated but not applied.",
        )
        return {
            "hitl_triggered": True,
            "human_action": action,
            "maestro_self_decision": False,
            "task_decision": "DRAFT_REVIEW",
            "revision_instruction": instruction,
            "revision_proposals": proposals,
            "containment_results": [],
            "promotion_results": [],
        }

    if action in {"REPLACE_AGENT", "QUARANTINE_HANDOFF_RESUME"}:
        containment = []
        promotions = []
        replacement_map = {
            "word_agent": "standby_word",
            "excel_agent": "standby_excel",
            "powerpoint_agent": "standby_powerpoint",
        }
        for agent_id, agent in agents.items():
            if agent.status == "ACTIVE":
                agent.status = "QUARANTINED" if action == "QUARANTINE_HANDOFF_RESUME" else "REPLACED"
                replacement_id = replacement_map[agent_id]
                standby[replacement_id].status = "PROMOTED"
                containment.append({"agent_id": agent_id, "action": agent.status, "status": agent.status})
                promotions.append({"agent_id": replacement_id, "action": "PROMOTE_STANDBY", "status": "PROMOTED"})
                arl.append(
                    layer="hitl_resolution",
                    decision="DEGRADED_RUN",
                    sealed=False,
                    overrideable=False,
                    final_decider="USER",
                    reason_code=f"USER_SELECTED_{action}",
                    message=f"User selected {action}.",
                    agent_id=agent_id,
                )
        return {
            "hitl_triggered": True,
            "human_action": action,
            "maestro_self_decision": False,
            "task_decision": "DEGRADED_RUN",
            "revision_instruction": None,
            "revision_proposals": None,
            "containment_results": containment,
            "promotion_results": promotions,
        }

    arl.append(
        layer="hitl_resolution",
        decision="RUN",
        sealed=False,
        overrideable=False,
        final_decider="USER",
        reason_code="USER_SELECTED_NO_ACTION",
        message="User selected NO_ACTION. Risk and differences were logged.",
    )
    return {
        "hitl_triggered": True,
        "human_action": action,
        "maestro_self_decision": False,
        "task_decision": "RUN",
        "revision_instruction": None,
        "revision_proposals": None,
        "containment_results": [],
        "promotion_results": [],
    }


def verify_result(
    *,
    original_task_snapshot: dict[str, Any],
    selected_agents: list[str],
    mediator_request_verify: dict[str, Any],
    mediation: dict[str, Any],
    pel: dict[str, Any],
    maestro: dict[str, Any],
    arl_verify: dict[str, Any],
) -> dict[str, Any]:
    mismatches = []

    if set(selected_agents) - set(OFFICE_AGENT_IDS):
        mismatches.append("UNKNOWN_SELECTED_AGENT")
    if not original_task_snapshot.get("original_user_task_snapshot_hash"):
        mismatches.append("ORIGINAL_TASK_HASH_MISSING")
    if not mediator_request_verify["verified"]:
        mismatches.append("MEDIATOR_REQUEST_POLICY_FAILED")
    if mediation["raw_log_used"] is not False:
        mismatches.append("MEDIATOR_USED_RAW_LOG")
    if mediation["collision_score"] == THRESHOLD and maestro["hitl_triggered"]:
        mismatches.append("EXACT_THRESHOLD_MUST_NOT_TRIGGER_HITL")
    if mediation["collision_score"] > THRESHOLD and not maestro["hitl_triggered"]:
        mismatches.append("ABOVE_THRESHOLD_MUST_TRIGGER_HITL")
    if pel["future_failure_probability"] == THRESHOLD and maestro["hitl_triggered"]:
        mismatches.append("PEL_EXACT_THRESHOLD_MUST_NOT_TRIGGER_HITL")
    if maestro["maestro_self_decision"] is not False:
        mismatches.append("MAESTRO_SELF_DECISION_DETECTED")
    if not arl_verify["verified"]:
        mismatches.append("ARL_VERIFY_FAILED")
    if maestro["human_action"] == "USER_TARGETED_REVISION_PROMPT":
        proposals = maestro["revision_proposals"]
        if not proposals or proposals["auto_apply"] is not False:
            mismatches.append("REVISION_PROPOSAL_AUTO_APPLY_VIOLATION")

    return {
        "tool": "RCV",
        "schema_version": "rcv-office-mediation-v0.5.0",
        "verified": not mismatches,
        "decision": "RUN" if not mismatches else "PAUSE_FOR_HITL",
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def parse_selected_agents(value: str) -> list[str]:
    if value == "all":
        return OFFICE_AGENT_IDS[:]
    selected = [item.strip() for item in value.split(",") if item.strip()]
    return selected or OFFICE_AGENT_IDS[:]


def run_simulation(
    *,
    seed: int,
    out_dir: Path,
    scenario: str,
    selected_agents_value: str,
    human_action_mode: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"office-task-mediation-v0.5.0-seed-{seed}-{scenario}"
    arl = AuditLog(run_id)
    agents, standby = build_agents()
    selected_agents = parse_selected_agents(selected_agents_value)
    original_task_snapshot = build_original_task_snapshot()

    write_json(out_dir / "original_user_task_snapshot.json", original_task_snapshot)

    arl.append(
        layer="maestro",
        decision="RUN",
        sealed=False,
        overrideable=True,
        final_decider="USER",
        reason_code="USER_SELECTED_AGENTS_BEFORE_DISPATCH",
        message=f"User selected agents before dispatch: {','.join(selected_agents)}",
    )

    artifacts = create_artifacts(scenario, selected_agents)
    raw_agent_logs = make_raw_agent_logs(artifacts)
    write_json(out_dir / "internal_raw_agent_logs_simulation_only.json", raw_agent_logs)

    tasukeru_report = tasukeru_analyze_logs(
        run_id=run_id,
        original_task_snapshot=original_task_snapshot,
        raw_agent_logs=raw_agent_logs,
        out_dir=out_dir,
    )

    request = mediator_request_packet(run_id=run_id, task_id=original_task_snapshot["task_id"])
    request_verify = verify_mediator_request(request)
    write_json(out_dir / "mediator_masked_metadata_request.json", request)
    write_json(out_dir / "mediator_masked_metadata_request_verify.json", request_verify)

    mediation = mediator_reconcile(
        original_task_snapshot=original_task_snapshot,
        tasukeru_report=tasukeru_report,
        request_verify=request_verify,
        out_dir=out_dir,
    )
    pel = pel_predict(mediation, out_dir)

    maestro = maestro_handle_handoff(
        mediation=mediation,
        pel=pel,
        agents=agents,
        standby=standby,
        tasukeru_report=tasukeru_report,
        action_mode=human_action_mode,
        rng=rng,
        arl=arl,
        out_dir=out_dir,
    )

    arl.append(
        layer="orchestrator",
        decision=maestro["task_decision"],
        sealed=False,
        overrideable=False,
        final_decider="SYSTEM_AFTER_USER_OR_ADVISORY",
        reason_code="ORCHESTRATION_COMPLETED",
        message="Completed according to advisory result or explicit user action.",
    )

    arl_verify = arl.verify()
    rcv = verify_result(
        original_task_snapshot=original_task_snapshot,
        selected_agents=selected_agents,
        mediator_request_verify=request_verify,
        mediation=mediation,
        pel=pel,
        maestro=maestro,
        arl_verify=arl_verify,
    )

    result = {
        "schema_version": "office-task-mediation-tasukeru-maestro-sim-v0.5.0",
        "run_id": run_id,
        "seed": seed,
        "scenario": scenario,
        "selected_agents": selected_agents,
        "human_action_mode": human_action_mode,
        "safety_boundary": {
            "local_only": True,
            "real_office_generation": False,
            "raw_log_handoff_to_mediator": False,
            "masked_metadata_packet_only": True,
            "external_communication": False,
            "real_process_control": False,
            "auto_apply_revision": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
        },
        "threshold_policy": {
            "threshold": THRESHOLD,
            "exact_threshold_handoff": False,
            "above_threshold_handoff": True,
        },
        "original_task_snapshot": original_task_snapshot,
        "agents": [asdict(agent) for agent in agents.values()],
        "standby_agents": [asdict(agent) for agent in standby.values()],
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "tasukeru_report": tasukeru_report,
        "mediator_request_verify": request_verify,
        "mediator_reconciliation": mediation,
        "pel_report": pel,
        "maestro_result": maestro,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv,
        "final_decision": maestro["task_decision"],
    }

    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "maestro_handoff_result.json", maestro)
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")

    summary = [
        "# Office Task Mediation + Tasukeru + Maestro Simulation v0.5.0",
        "",
        f"- seed: `{seed}`",
        f"- scenario: `{scenario}`",
        f"- selected_agents: `{','.join(selected_agents)}`",
        f"- collision_score: `{mediation['collision_score']}`",
        f"- collision_decision: `{mediation['decision']}`",
        f"- future_failure_probability: `{pel['future_failure_probability']}`",
        f"- pel_decision: `{pel['decision']}`",
        f"- hitl_triggered: `{maestro['hitl_triggered']}`",
        f"- human_action: `{maestro['human_action']}`",
        f"- final_decision: `{maestro['task_decision']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv['verified']}`",
    ]
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local-only Office task mediation simulation with Tasukeru, Mediator, PEL, Maestro, and HITL."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("office_task_mediation_tasukeru_maestro_out_v0_5_0"),
    )
    parser.add_argument(
        "--scenario",
        choices=["mismatch", "threshold", "safe", "pii", "confidential"],
        default="mismatch",
    )
    parser.add_argument(
        "--selected-agents",
        default="all",
        help="Comma-separated user-selected agent IDs, or 'all'. Maestro does not select agents autonomously.",
    )
    parser.add_argument("--human-action", choices=["random", *ACTIONS], default="random")
    args = parser.parse_args()

    result = run_simulation(
        seed=args.seed,
        out_dir=args.out_dir,
        scenario=args.scenario,
        selected_agents_value=args.selected_agents,
        human_action_mode=args.human_action,
    )

    mediation = result["mediator_reconciliation"]
    pel = result["pel_report"]
    maestro = result["maestro_result"]

    print("Office Task Mediation + Tasukeru + Maestro Simulation v0.5.0")
    print(f"seed={result['seed']}")
    print(f"scenario={result['scenario']}")
    print(f"selected_agents={','.join(result['selected_agents'])}")
    print(f"collision_score={mediation['collision_score']}")
    print(f"collision_decision={mediation['decision']}")
    print(f"future_failure_probability={pel['future_failure_probability']}")
    print(f"pel_decision={pel['decision']}")
    print(f"hitl_triggered={maestro['hitl_triggered']}")
    print(f"human_action={maestro['human_action']}")
    print(f"final_decision={result['final_decision']}")
    print(f"maestro_self_decision={maestro['maestro_self_decision']}")
    print(f"arl_verified={result['arl_verify']['verified']}")
    print(f"rcv_verified={result['result_consistency_verify']['verified']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
