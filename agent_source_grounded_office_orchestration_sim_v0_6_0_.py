#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_source_grounded_office_orchestration_sim_v0_6_0.py

Local-only simulation:
- source-grounded multi-agent orchestration based on the Office task mediation line
- user-selected agent dispatch before Maestro task handoff
- synthetic source agents create primary / secondary / tertiary source logs
- Tasukeru reads source logs internally and emits Source Evidence Packets only
- Office agents create Word / Excel / PowerPoint-style DRAFT artifacts from source packets
- Tasukeru reads artifact logs internally and emits masked artifact metadata packets only
- Mediator receives only Source Evidence Packets and masked artifact metadata
- Mediator compares original user task, source packets, and Office artifacts
- Maestro has no decision authority and relays HITL only
- 3 or more conflict loops -> ORCHESTRATION_STOPPED
- final outputs are DRAFT_RESULT only

Safety boundary:
- local-only simulation
- synthetic sources only
- no real source fetching
- no exploit reproduction
- no external communication
- no real process control
- no real Office document generation
- no raw source/artifact log handoff to Mediator
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


SIM_VERSION = "0.6.0"
THRESHOLD = 0.8
MAX_RECONCILIATION_LOOPS = 3

DECISION_RUN = "RUN"
DECISION_DRAFT_REVIEW = "DRAFT_REVIEW"
DECISION_REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
DECISION_INFO_ONLY = "INFO_ONLY"
DECISION_PAUSE = "PAUSE_FOR_HITL"
DECISION_STOP = "STOPPED"
DECISION_DRAFT_RESULT = "DRAFT_RESULT"

ACTIONS = [
    "STOP",
    "USER_HITL_RESEARCH_RETRY_APPROVED",
    "USER_HITL_REWRITE_APPROVED",
    "ACCEPT_DRAFT_RESULT",
    "NO_ACTION",
]

SOURCE_AGENT_IDS = [
    "source_agent_primary",
    "source_agent_secondary",
    "source_agent_tertiary",
]
OFFICE_AGENT_IDS = [
    "word_agent",
    "excel_agent",
    "powerpoint_agent",
]
ALL_AGENT_IDS = SOURCE_AGENT_IDS + OFFICE_AGENT_IDS

PII_PATTERNS = [
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{2,4}-\d{2,4}-\d{3,4}\b"),
]
CONFIDENTIAL_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|token|password|credential)\b\s*[:=]\s*[^,\s]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
]


@dataclass
class Agent:
    agent_id: str
    role: str
    artifact_type: str
    status: str = "ACTIVE"


@dataclass
class SourceLog:
    source_log_id: str
    agent_id: str
    source_level: str
    source_title: str
    claim_key: str
    claim_value: Any
    raw_excerpt: str
    fabricated_signal: bool = False
    retrieved_at_unix: float = field(default_factory=time.time)


@dataclass
class SourceEvidencePacket:
    source_packet_id: str
    source_log_id: str
    agent_id: str
    source_level: str
    source_title: str
    source_hash: str
    claim_key: str
    claim_value: Any
    claim_supported: str
    excerpt_hash: str
    redaction_status: str
    redaction_types: list[str]
    fabricated_signal: bool
    raw_source_handoff: bool
    packet_only: bool
    confidence: str
    timestamp_unix: float = field(default_factory=time.time)


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
    source_packet_refs: list[str] = field(default_factory=list)
    formula: str | None = None
    chart_profit: int | None = None
    unsupported_claim: str | None = None


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
    loop_count: int = 0
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
        loop_count: int = 0,
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
            loop_count=loop_count,
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
            if row.sealed and row.final_decider != "SYSTEM":
                violations.append(f"SEALED_FINAL_DECIDER_MUST_BE_SYSTEM:{index}")
            if row.decision == DECISION_PAUSE and row.sealed:
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
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def threshold_decision(score: float) -> str:
    """Exact-threshold policy: only scores strictly greater than THRESHOLD pause.

    Do not round before comparison. Rounding can create a dead zone where
    0.8000001 becomes 0.8 and incorrectly falls into DRAFT_REVIEW.
    Non-finite scores fail closed to PAUSE_FOR_HITL.
    """
    score_value = float(score)
    if not math.isfinite(score_value):
        return DECISION_PAUSE
    if score_value > THRESHOLD:
        return DECISION_PAUSE
    if math.isclose(score_value, THRESHOLD, rel_tol=0.0, abs_tol=1e-12):
        return DECISION_DRAFT_REVIEW
    if score_value >= 0.4:
        return DECISION_REVIEW_RECOMMENDED
    return DECISION_INFO_ONLY


def mask_text(text: str) -> tuple[str, list[str]]:
    redactions: list[str] = []
    masked = text
    for pattern in PII_PATTERNS:
        if pattern.search(masked):
            redactions.append("PII")
            masked = pattern.sub("[MASKED_PII]", masked)
    for pattern in CONFIDENTIAL_PATTERNS:
        if pattern.search(masked):
            redactions.append("CONFIDENTIAL")
            masked = pattern.sub("[MASKED_CONFIDENTIAL]", masked)
    return masked, sorted(set(redactions))


def parse_selected_agents(value: str) -> list[str]:
    if value == "all":
        return ALL_AGENT_IDS[:]
    selected = [item.strip() for item in value.split(",") if item.strip()]
    return selected or ALL_AGENT_IDS[:]


def build_agents() -> tuple[dict[str, Agent], dict[str, Agent]]:
    agents = {
        "source_agent_primary": Agent("source_agent_primary", "primary_source_researcher", "source_primary"),
        "source_agent_secondary": Agent("source_agent_secondary", "secondary_source_checker", "source_secondary"),
        "source_agent_tertiary": Agent("source_agent_tertiary", "tertiary_source_checker", "source_tertiary"),
        "word_agent": Agent("word_agent", "word_report_writer", "word"),
        "excel_agent": Agent("excel_agent", "excel_formula_builder", "excel"),
        "powerpoint_agent": Agent("powerpoint_agent", "powerpoint_chart_builder", "powerpoint"),
    }
    standby = {
        "standby_source": Agent("standby_source", "replacement_source_researcher", "source", "STANDBY"),
        "standby_word": Agent("standby_word", "replacement_word_report_writer", "word", "STANDBY"),
        "standby_excel": Agent("standby_excel", "replacement_excel_formula_builder", "excel", "STANDBY"),
        "standby_powerpoint": Agent("standby_powerpoint", "replacement_powerpoint_chart_builder", "powerpoint", "STANDBY"),
    }
    return agents, standby


def build_original_task_snapshot() -> dict[str, Any]:
    snapshot = {
        "schema_version": "source-grounded-office-task-snapshot-v0.6.0",
        "task_id": "source-grounded-office-task-001",
        "user_instruction_summary": (
            "Create one project report set using source-grounded Word, Excel, and PowerPoint DRAFT artifacts. "
            "Revenue, cost, profit, risk label, and conclusion must be grounded in Source Evidence Packets. "
            "Primary, secondary, and tertiary source checks may be used when contradictions appear. "
            "Do not include personal or confidential information. "
            "No artifact may be finalized without User HITL."
        ),
        "required_artifacts": ["word", "excel", "powerpoint"],
        "required_source_levels": ["primary"],
        "consistency_requirements": {
            "source_grounded": True,
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
            "source_agent_final_authority": False,
            "office_agent_final_authority": False,
            "auto_apply_revision": False,
            "final_output_is_draft_only": True,
        },
    }
    snapshot["original_user_task_snapshot_hash"] = stable_hash(snapshot)
    return snapshot


def _base_claims_for_attempt(scenario: str, loop_count: int) -> dict[str, Any]:
    return {
        "revenue": 1_000_000,
        "cost": 600_000,
        "profit": 400_000,
        "risk_label": "LOW",
        "conclusion": "The project is profitable and can continue.",
    }


def create_source_logs(scenario: str, selected_agents: list[str], loop_count: int) -> list[SourceLog]:
    claims = _base_claims_for_attempt(scenario, loop_count)
    logs: list[SourceLog] = []

    include_primary = "source_agent_primary" in selected_agents and scenario != "primary_source_missing"
    include_secondary = "source_agent_secondary" in selected_agents
    include_tertiary = "source_agent_tertiary" in selected_agents

    def add(agent_id: str, level: str, key: str, value: Any, fabricated: bool = False) -> None:
        raw = f"{level.title()} synthetic source states {key} = {value} for project Alpha."
        if scenario == "pii" and key == "conclusion" and level == "primary":
            raw += " Contact: taro@example.com"
        if scenario == "confidential" and key == "risk_label" and level == "primary":
            raw += " api_key=sk-EXAMPLECONFIDENTIAL12345"
        logs.append(
            SourceLog(
                source_log_id=f"{level.upper()}#{key}",
                agent_id=agent_id,
                source_level=level,
                source_title=f"Synthetic {level} source for {key}",
                claim_key=key,
                claim_value=value,
                raw_excerpt=raw,
                fabricated_signal=fabricated,
            )
        )

    if include_primary:
        for key, value in claims.items():
            add("source_agent_primary", "primary", key, value, fabricated=(scenario == "fabricated_source_signal"))

    if include_secondary:
        secondary_claims = dict(claims)
        if scenario == "secondary_source_conflict" and loop_count == 0:
            secondary_claims["revenue"] = 900_000
            secondary_claims["profit"] = 300_000
        for key, value in secondary_claims.items():
            add("source_agent_secondary", "secondary", key, value)

    if include_tertiary:
        for key, value in claims.items():
            add("source_agent_tertiary", "tertiary", key, value)

    return logs


def tasukeru_analyze_source_logs(
    *,
    run_id: str,
    original_task_snapshot: dict[str, Any],
    raw_source_logs: list[SourceLog],
    out_dir: Path,
) -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for item in raw_source_logs:
        masked_excerpt, redactions = mask_text(item.raw_excerpt)
        if redactions:
            findings.append(
                {
                    "source_log_id": item.source_log_id,
                    "agent_id": item.agent_id,
                    "finding": "SOURCE_REDACTION_APPLIED",
                    "redaction_types": redactions,
                    "risk_material": "source excerpt contained redacted signal",
                    "score_material": 1.0,
                }
            )
        if item.fabricated_signal:
            findings.append(
                {
                    "source_log_id": item.source_log_id,
                    "agent_id": item.agent_id,
                    "finding": "SOURCE_EVIDENCE_FABRICATION_SIGNAL",
                    "risk_material": "synthetic source packet marked with fabrication signal",
                    "score_material": 1.0,
                }
            )

        packet = SourceEvidencePacket(
            source_packet_id=f"SRC-PACKET#{len(packets) + 1:03d}",
            source_log_id=item.source_log_id,
            agent_id=item.agent_id,
            source_level=item.source_level,
            source_title=item.source_title,
            source_hash=stable_hash(
                {
                    "source_log_id": item.source_log_id,
                    "source_level": item.source_level,
                    "claim_key": item.claim_key,
                    "claim_value": item.claim_value,
                }
            ),
            claim_key=item.claim_key,
            claim_value=item.claim_value,
            claim_supported=f"{item.claim_key} is {item.claim_value}",
            excerpt_hash=stable_hash(masked_excerpt),
            redaction_status="verified",
            redaction_types=redactions,
            fabricated_signal=item.fabricated_signal,
            raw_source_handoff=False,
            packet_only=True,
            confidence="reference_only",
        )
        packets.append(asdict(packet))

    levels = {packet["source_level"] for packet in packets}
    required_levels = set(original_task_snapshot.get("required_source_levels", []))
    missing_levels = sorted(required_levels - levels)
    if missing_levels:
        findings.append(
            {
                "finding": "SOURCE_EVIDENCE_MISSING",
                "missing_source_levels": missing_levels,
                "risk_material": "required source level missing",
                "score_material": 1.0,
            }
        )

    report = {
        "schema_version": "tasukeru-source-evidence-report-v0.6.0",
        "role_boundary": "Tasukeru reads source logs internally and outputs Source Evidence Packets only.",
        "raw_source_log_handoff_to_mediator": False,
        "source_evidence_packet_only": True,
        "task_id": original_task_snapshot["task_id"],
        "original_user_task_snapshot_hash": original_task_snapshot["original_user_task_snapshot_hash"],
        "findings": findings,
        "source_evidence_packets": packets,
    }
    write_json(out_dir / "tasukeru_source_evidence_report.json", report)
    return report


def _claims_from_source_packets(source_report: dict[str, Any]) -> dict[str, Any]:
    packets = source_report.get("source_evidence_packets", [])
    claims_by_level: dict[str, dict[str, Any]] = {"primary": {}, "secondary": {}, "tertiary": {}}
    for packet in packets:
        level = packet.get("source_level")
        key = packet.get("claim_key")
        if level in claims_by_level and key:
            claims_by_level[level][key] = packet.get("claim_value")
    for level in ["primary", "secondary", "tertiary"]:
        if claims_by_level[level]:
            return claims_by_level[level]
    return {}


def create_office_artifacts(
    *,
    scenario: str,
    selected_agents: list[str],
    source_report: dict[str, Any],
    loop_count: int,
) -> list[OfficeArtifact]:
    claims = _claims_from_source_packets(source_report)
    revenue = int(claims.get("revenue", 1_000_000))
    cost = int(claims.get("cost", 600_000))
    profit = int(claims.get("profit", revenue - cost))
    risk_label = str(claims.get("risk_label", "LOW"))
    conclusion = str(claims.get("conclusion", "The project is profitable and can continue."))
    packet_refs = [packet["source_packet_id"] for packet in source_report.get("source_evidence_packets", [])]

    word_profit = profit
    excel_cost = cost
    excel_profit = profit
    ppt_profit = profit
    ppt_chart_profit = profit
    ppt_risk = risk_label
    ppt_conclusion = conclusion
    unsupported_claim = None

    unresolved_conflict = scenario in {"artifact_conflict", "loop_limit"} and not (loop_count > 0 and scenario == "artifact_conflict")
    if unresolved_conflict:
        excel_cost = cost + 100_000
        excel_profit = revenue - excel_cost
        ppt_profit = profit + 100_000
        ppt_chart_profit = profit + 100_000
        ppt_risk = "CRITICAL"
        ppt_conclusion = "Emergency stop is required."

    if scenario == "over_inference" and loop_count == 0:
        unsupported_claim = "The project is guaranteed to double next year."

    all_artifacts = {
        "word_agent": OfficeArtifact(
            artifact_id="word_report",
            agent_id="word_agent",
            artifact_type="word",
            revenue=revenue,
            cost=cost,
            profit=word_profit,
            risk_label=risk_label,
            conclusion=conclusion,
            text=f"Word report DRAFT: revenue {revenue}, cost {cost}, profit {word_profit}, risk {risk_label}.",
            source_packet_refs=packet_refs,
            unsupported_claim=unsupported_claim if "word_agent" in selected_agents else None,
        ),
        "excel_agent": OfficeArtifact(
            artifact_id="excel_summary",
            agent_id="excel_agent",
            artifact_type="excel",
            revenue=revenue,
            cost=excel_cost,
            profit=excel_profit,
            risk_label=risk_label,
            conclusion=conclusion,
            text=f"Excel summary DRAFT: revenue {revenue}, cost {excel_cost}, formula profit {excel_profit}.",
            formula="=revenue-cost",
            source_packet_refs=packet_refs,
        ),
        "powerpoint_agent": OfficeArtifact(
            artifact_id="powerpoint_briefing",
            agent_id="powerpoint_agent",
            artifact_type="powerpoint",
            revenue=revenue,
            cost=cost,
            profit=ppt_profit,
            risk_label=ppt_risk,
            conclusion=ppt_conclusion,
            text=f"PowerPoint briefing DRAFT: chart profit {ppt_chart_profit}, risk {ppt_risk}.",
            chart_profit=ppt_chart_profit,
            source_packet_refs=packet_refs,
        ),
    }
    return [artifact for agent_id, artifact in all_artifacts.items() if agent_id in selected_agents]


def make_raw_artifact_logs(artifacts: list[OfficeArtifact]) -> list[dict[str, Any]]:
    logs = []
    for artifact in artifacts:
        text = artifact.text
        if artifact.unsupported_claim:
            text += " " + artifact.unsupported_claim
        logs.append(
            {
                "agent_id": artifact.agent_id,
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "raw_text": text,
                "numeric_claims": {
                    "revenue": artifact.revenue,
                    "cost": artifact.cost,
                    "profit": artifact.profit,
                    "chart_profit": artifact.chart_profit,
                },
                "formula": artifact.formula,
                "risk_label": artifact.risk_label,
                "conclusion": artifact.conclusion,
                "source_packet_refs": artifact.source_packet_refs,
                "unsupported_claim": artifact.unsupported_claim,
            }
        )
    return logs


def tasukeru_analyze_artifact_logs(
    *,
    run_id: str,
    original_task_snapshot: dict[str, Any],
    raw_artifact_logs: list[dict[str, Any]],
    out_dir: Path,
    loop_count: int,
) -> dict[str, Any]:
    masked_packets: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for item in raw_artifact_logs:
        masked_text, redactions = mask_text(item["raw_text"])
        if "PII" in redactions:
            findings.append({"agent_id": item["agent_id"], "artifact_id": item["artifact_id"], "finding": "PII_DETECTED_IN_ARTIFACT_TEXT", "score_material": 1.0})
        if "CONFIDENTIAL" in redactions:
            findings.append({"agent_id": item["agent_id"], "artifact_id": item["artifact_id"], "finding": "CONFIDENTIAL_SIGNAL_DETECTED_IN_ARTIFACT_TEXT", "score_material": 1.0})
        if item.get("unsupported_claim"):
            findings.append(
                {
                    "agent_id": item["agent_id"],
                    "artifact_id": item["artifact_id"],
                    "finding": "ARTIFACT_UNSUPPORTED_CLAIM",
                    "risk_material": "artifact contains a claim not grounded in source evidence packets",
                    "score_material": 0.85,
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
                "layer": "tasukeru_artifact_log_analysis",
                "decision": DECISION_RUN,
                "reason_code": "MASKED_ARTIFACT_METADATA_PACKET_CREATED",
                "masked_text_preview": masked_text[:180],
                "numeric_claims": item["numeric_claims"],
                "formula": item["formula"],
                "risk_label": item["risk_label"],
                "conclusion": item["conclusion"],
                "source_packet_refs": item["source_packet_refs"],
                "unsupported_claim": item.get("unsupported_claim"),
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
                        "source_packet_refs": item["source_packet_refs"],
                    }
                ),
                "loop_count": loop_count,
                "timestamp_unix": time.time(),
            }
        )
    report = {
        "schema_version": "tasukeru-masked-artifact-analysis-v0.6.0",
        "role_boundary": "Tasukeru reads artifact logs internally and outputs masked metadata packets only.",
        "raw_artifact_log_handoff_to_mediator": False,
        "masked_metadata_packet_only": True,
        "loop_count": loop_count,
        "findings": findings,
        "masked_metadata_packets": masked_packets,
    }
    write_json(out_dir / f"tasukeru_masked_artifact_analysis_loop_{loop_count}.json", report)
    return report


def mediator_request_packet(*, run_id: str, task_id: str, loop_count: int) -> dict[str, Any]:
    request = {
        "schema_version": "mediator-request-v0.6.0",
        "run_id": run_id,
        "task_id": task_id,
        "loop_count": loop_count,
        "requested_packet_type": "source_evidence_packet_and_masked_artifact_metadata",
        "raw_log_requested": False,
        "raw_source_log_requested": False,
        "raw_artifact_log_requested": False,
        "raw_prompt_requested": False,
        "raw_output_requested": False,
        "confidential_payload_requested": False,
        "pii_requested": False,
        "request_policy_verified": True,
    }
    request["request_hash"] = stable_hash(request)
    return request


def verify_mediator_request(request: dict[str, Any]) -> dict[str, Any]:
    violations = []
    for key, reason in {
        "raw_log_requested": "MEDIATOR_RAW_LOG_REQUEST",
        "raw_source_log_requested": "MEDIATOR_RAW_SOURCE_LOG_REQUEST",
        "raw_artifact_log_requested": "MEDIATOR_RAW_ARTIFACT_LOG_REQUEST",
        "raw_prompt_requested": "MEDIATOR_RAW_PROMPT_REQUEST",
        "raw_output_requested": "MEDIATOR_RAW_OUTPUT_REQUEST",
        "confidential_payload_requested": "MEDIATOR_CONFIDENTIAL_PAYLOAD_REQUEST",
        "pii_requested": "MEDIATOR_PII_REQUEST",
    }.items():
        if request.get(key) is not False:
            violations.append(reason)
    body = dict(request)
    given = body.pop("request_hash", None)
    if given != stable_hash(body):
        violations.append("MEDIATOR_REQUEST_HASH_MISMATCH")
    return {"verified": not violations, "violations": violations, "request_hash": given}


def _source_claims_by_level(source_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {"primary": {}, "secondary": {}, "tertiary": {}}
    for packet in source_report.get("source_evidence_packets", []):
        level = packet.get("source_level")
        key = packet.get("claim_key")
        if level in out and key:
            out[level][key] = packet.get("claim_value")
    return out


def mediator_reconcile(
    *,
    original_task_snapshot: dict[str, Any],
    source_report: dict[str, Any],
    artifact_report: dict[str, Any],
    request_verify: dict[str, Any],
    out_dir: Path,
    loop_count: int,
) -> dict[str, Any]:
    source_packets = source_report.get("source_evidence_packets", [])
    artifact_packets = artifact_report.get("masked_metadata_packets", [])
    by_type = {packet["artifact_type"]: packet for packet in artifact_packets}
    source_by_level = _source_claims_by_level(source_report)
    differences: list[dict[str, Any]] = []

    source_missing = any(finding.get("finding") == "SOURCE_EVIDENCE_MISSING" for finding in source_report.get("findings", []))
    source_fabrication_signal = any(finding.get("finding") == "SOURCE_EVIDENCE_FABRICATION_SIGNAL" for finding in source_report.get("findings", []))
    artifact_unsupported_claim = any(finding.get("finding") == "ARTIFACT_UNSUPPORTED_CLAIM" for finding in artifact_report.get("findings", []))
    combined_findings = artifact_report.get("findings", []) + source_report.get("findings", [])
    pii_signal = any("PII" in finding.get("redaction_types", []) or finding.get("finding", "").startswith("PII_") for finding in combined_findings)
    confidential_signal = any("CONFIDENTIAL" in finding.get("redaction_types", []) or finding.get("finding", "").startswith("CONFIDENTIAL_") for finding in combined_findings)

    if source_missing:
        differences.append({"difference_type": "SOURCE_EVIDENCE_MISSING", "description": "Required primary source evidence packet is missing."})
    if source_fabrication_signal:
        differences.append({"difference_type": "SOURCE_EVIDENCE_FABRICATION_SIGNAL", "description": "A synthetic source packet is marked with fabrication signal."})

    for key in ["revenue", "cost", "profit", "risk_label", "conclusion"]:
        values = {level: claims.get(key) for level, claims in source_by_level.items() if key in claims}
        if len(set(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in values.values())) > 1:
            differences.append(
                {
                    "difference_type": "SOURCE_EVIDENCE_CONFLICT",
                    "description": f"Source evidence packets disagree for {key}.",
                    "observed_values": values,
                }
            )

    preferred_source_claims = _claims_from_source_packets(source_report)
    for artifact_type, packet in by_type.items():
        claims = packet.get("numeric_claims", {})
        artifact_claims = {
            "revenue": claims.get("revenue"),
            "cost": claims.get("cost"),
            "profit": first_not_none(claims.get("chart_profit"), claims.get("profit")),
            "risk_label": packet.get("risk_label"),
            "conclusion": packet.get("conclusion"),
        }
        for key, artifact_value in artifact_claims.items():
            if key not in preferred_source_claims or artifact_value is None:
                continue
            if artifact_value != preferred_source_claims[key]:
                differences.append(
                    {
                        "difference_type": "ARTIFACT_SOURCE_MISMATCH",
                        "description": f"{artifact_type} artifact does not match source packet claim for {key}.",
                        "artifact_type": artifact_type,
                        "claim_key": key,
                        "artifact_value": artifact_value,
                        "source_value": preferred_source_claims[key],
                    }
                )

    profits = {
        artifact_type: first_not_none(packet["numeric_claims"].get("chart_profit"), packet["numeric_claims"].get("profit"))
        for artifact_type, packet in by_type.items()
    }
    risk_labels = {artifact_type: packet["risk_label"] for artifact_type, packet in by_type.items()}
    conclusions = {artifact_type: packet["conclusion"] for artifact_type, packet in by_type.items()}

    if len(set(value for value in profits.values() if value is not None)) > 1:
        differences.append({"difference_type": "PROFIT_MISMATCH", "description": "Office artifact profit values are not consistent.", "observed_values": profits})

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
                }
            )
    if len(set(risk_labels.values())) > 1:
        differences.append({"difference_type": "RISK_LABEL_MISMATCH", "description": "Risk labels differ across artifacts.", "observed_values": risk_labels})
    if len(set(conclusions.values())) > 1:
        differences.append({"difference_type": "CONCLUSION_MISMATCH", "description": "Conclusions differ across artifacts.", "observed_values": conclusions})
    if artifact_unsupported_claim:
        differences.append({"difference_type": "ARTIFACT_UNSUPPORTED_CLAIM", "description": "An artifact contains a claim not grounded in source evidence."})

    risk_components = {
        "source_missing_score": 1.0 if source_missing else 0.0,
        "source_conflict_score": 0.7 if any(d["difference_type"] == "SOURCE_EVIDENCE_CONFLICT" for d in differences) else 0.0,
        "source_fabrication_score": 1.0 if source_fabrication_signal else 0.0,
        "artifact_source_mismatch_score": 0.55 if any(d["difference_type"] == "ARTIFACT_SOURCE_MISMATCH" for d in differences) else 0.0,
        "artifact_conflict_score": 0.45 if any(d["difference_type"] in {"PROFIT_MISMATCH", "RISK_LABEL_MISMATCH", "CONCLUSION_MISMATCH"} for d in differences) else 0.0,
        # Unsupported claims should not sit exactly on the no-HITL boundary.
        # They require reconciliation because an artifact asserted something not grounded in source evidence.
        "unsupported_claim_score": 0.85 if artifact_unsupported_claim else 0.0,
        "pii_score": 1.0 if pii_signal else 0.0,
        "confidential_score": 1.0 if confidential_signal else 0.0,
    }
    # Preserve non-difference risk components such as PII/confidential/source fabrication.
    # Do not reset the score to 0 merely because `differences` is empty.
    collision_score = min(1.0, sum(risk_components.values()))
    decision = threshold_decision(collision_score)
    high_risk_signal = bool(pii_signal or confidential_signal or source_fabrication_signal or source_missing)
    requires_reconciliation = bool(differences or high_risk_signal) and collision_score > THRESHOLD
    mediation = {
        "schema_version": "mediator-source-grounded-reconciliation-v0.6.0",
        "role_boundary": "Mediator reconciles source-grounded artifact differences and returns a DRAFT proposal only.",
        "original_user_task_snapshot_hash": original_task_snapshot["original_user_task_snapshot_hash"],
        "raw_source_log_used": False,
        "raw_artifact_log_used": False,
        "request_verified": request_verify["verified"],
        "loop_count": loop_count,
        "source_packet_count": len(source_packets),
        "artifact_packet_count": len(artifact_packets),
        "differences": differences,
        "risk_components": risk_components,
        "collision_score": collision_score,
        "threshold": THRESHOLD,
        "decision": decision,
        "requires_reconciliation": requires_reconciliation,
        "draft_mediation_proposal": {
            "proposal_type": "DRAFT_SOURCE_GROUNDED_MEDIATION_PROPOSAL",
            "summary": "Source-grounded differences were found between source evidence packets and Office DRAFT artifacts.",
            "recommended_user_options": ["Approve source re-check", "Approve targeted rewrite", "Stop orchestration", "Accept DRAFT_RESULT only if differences are acceptable"],
            "auto_apply": False,
        },
    }
    write_json(out_dir / f"mediator_source_grounded_reconciliation_loop_{loop_count}.json", mediation)
    return mediation


def maestro_handle_handoff(
    *,
    mediation: dict[str, Any],
    action_mode: str,
    rng: random.Random,
    arl: AuditLog,
    loop_count: int,
) -> dict[str, Any]:
    should_hitl = bool(mediation.get("requires_reconciliation")) or mediation["collision_score"] > THRESHOLD
    if loop_count >= MAX_RECONCILIATION_LOOPS and should_hitl:
        arl.append(layer="orchestration_loop_guard", decision=DECISION_STOP, sealed=False, overrideable=False, final_decider="SYSTEM", reason_code="LOOP_LIMIT_EXCEEDED", message="The reconciliation loop exceeded the maximum retry count.", loop_count=loop_count)
        return {"hitl_triggered": False, "human_action": None, "maestro_self_decision": False, "task_decision": DECISION_STOP, "loop_limit_exceeded": True, "reconciliation_requested": True, "final_artifacts_ready": False}
    if not should_hitl:
        arl.append(layer="maestro", decision=DECISION_DRAFT_RESULT, sealed=False, overrideable=True, final_decider="USER", reason_code="FINAL_ARTIFACTS_READY_FOR_USER_REVIEW", message="Maestro prepared DRAFT_RESULT for User review. No autonomous acceptance or finalization.", loop_count=loop_count)
        return {"hitl_triggered": True, "human_action": None, "maestro_self_decision": False, "task_decision": DECISION_DRAFT_RESULT, "loop_limit_exceeded": False, "reconciliation_requested": False, "final_artifacts_ready": True, "final_user_review_required": True}
    arl.append(layer="maestro", decision=DECISION_PAUSE, sealed=False, overrideable=True, final_decider="USER", reason_code="MEDIATOR_RECONCILIATION_REQUIRED", message="Maestro relayed source-grounded reconciliation requirement to User HITL.", loop_count=loop_count)
    action = rng.choice(ACTIONS) if action_mode == "random" else action_mode  # nosec B311 - simulation branch selection only.
    if action == "STOP":
        arl.append(layer="hitl_resolution", decision=DECISION_STOP, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_HITL_STOP_SELECTED", message="User selected STOP.", loop_count=loop_count)
        return {"hitl_triggered": True, "human_action": action, "maestro_self_decision": False, "task_decision": DECISION_STOP, "loop_limit_exceeded": False, "reconciliation_requested": True, "final_artifacts_ready": False}
    if action == "USER_HITL_RESEARCH_RETRY_APPROVED":
        arl.append(layer="hitl_resolution", decision=DECISION_PAUSE, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_HITL_RESEARCH_RETRY_APPROVED", message="User approved source re-check and reconciliation retry.", loop_count=loop_count)
        return {"hitl_triggered": True, "human_action": action, "maestro_self_decision": False, "task_decision": "RETRY_RESEARCH", "loop_limit_exceeded": False, "reconciliation_requested": True, "final_artifacts_ready": False}
    if action == "USER_HITL_REWRITE_APPROVED":
        arl.append(layer="hitl_resolution", decision=DECISION_PAUSE, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_HITL_REWRITE_APPROVED", message="User approved targeted rewrite and reconciliation retry.", loop_count=loop_count)
        return {"hitl_triggered": True, "human_action": action, "maestro_self_decision": False, "task_decision": "RETRY_REWRITE", "loop_limit_exceeded": False, "reconciliation_requested": True, "final_artifacts_ready": False}
    if action == "ACCEPT_DRAFT_RESULT":
        arl.append(layer="hitl_resolution", decision=DECISION_DRAFT_RESULT, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_ACCEPTED_DRAFT_RESULT", message="User accepted DRAFT_RESULT for review handoff. No finalization.", loop_count=loop_count)
        return {"hitl_triggered": True, "human_action": action, "maestro_self_decision": False, "task_decision": DECISION_DRAFT_RESULT, "loop_limit_exceeded": False, "reconciliation_requested": False, "final_artifacts_ready": True}
    arl.append(layer="hitl_resolution", decision=DECISION_DRAFT_REVIEW, sealed=False, overrideable=False, final_decider="USER", reason_code="USER_SELECTED_NO_ACTION", message="User selected NO_ACTION. Source-grounded differences were logged.", loop_count=loop_count)
    return {"hitl_triggered": True, "human_action": action, "maestro_self_decision": False, "task_decision": DECISION_DRAFT_REVIEW, "loop_limit_exceeded": False, "reconciliation_requested": True, "final_artifacts_ready": False}


def verify_result(
    *,
    original_task_snapshot: dict[str, Any],
    selected_agents: list[str],
    source_report: dict[str, Any],
    artifact_report: dict[str, Any],
    mediator_request_verify: dict[str, Any],
    mediation: dict[str, Any],
    maestro: dict[str, Any],
    arl_verify: dict[str, Any],
    loop_count: int,
) -> dict[str, Any]:
    mismatches = []
    if set(selected_agents) - set(ALL_AGENT_IDS):
        mismatches.append("UNKNOWN_SELECTED_AGENT")
    required_artifacts = set(original_task_snapshot.get("required_artifacts", []))
    artifact_packets = artifact_report.get("masked_metadata_packets", [])
    produced_artifacts = {packet.get("artifact_type") for packet in artifact_packets if isinstance(packet, dict) and packet.get("artifact_type")}
    missing_artifacts = sorted(required_artifacts - produced_artifacts)
    if missing_artifacts:
        mismatches.append("REQUIRED_ARTIFACTS_MISSING:" + ",".join(missing_artifacts))
    if source_report.get("raw_source_log_handoff_to_mediator") is not False:
        mismatches.append("RAW_SOURCE_LOG_HANDOFF_DETECTED")
    if source_report.get("source_evidence_packet_only") is not True:
        mismatches.append("SOURCE_PACKET_ONLY_FALSE")
    if artifact_report.get("raw_artifact_log_handoff_to_mediator") is not False:
        mismatches.append("RAW_ARTIFACT_LOG_HANDOFF_DETECTED")
    if artifact_report.get("masked_metadata_packet_only") is not True:
        mismatches.append("ARTIFACT_MASKED_PACKET_ONLY_FALSE")
    if not mediator_request_verify["verified"]:
        mismatches.append("MEDIATOR_REQUEST_POLICY_FAILED")
    if mediation["raw_source_log_used"] is not False:
        mismatches.append("MEDIATOR_USED_RAW_SOURCE_LOG")
    if mediation["raw_artifact_log_used"] is not False:
        mismatches.append("MEDIATOR_USED_RAW_ARTIFACT_LOG")
    if mediation["collision_score"] == THRESHOLD and mediation["decision"] == DECISION_PAUSE:
        mismatches.append("EXACT_THRESHOLD_MUST_NOT_TRIGGER_HITL")
    if maestro["maestro_self_decision"] is not False:
        mismatches.append("MAESTRO_SELF_DECISION_DETECTED")
    if maestro["task_decision"] == DECISION_DRAFT_RESULT and maestro["final_artifacts_ready"] is not True:
        mismatches.append("DRAFT_RESULT_WITHOUT_READY_FLAG")
    if maestro["task_decision"] == DECISION_STOP and maestro["loop_limit_exceeded"] and loop_count < MAX_RECONCILIATION_LOOPS:
        mismatches.append("LOOP_LIMIT_STOP_BEFORE_THRESHOLD")
    if not arl_verify["verified"]:
        mismatches.append("ARL_VERIFY_FAILED")
    return {"tool": "RCV", "schema_version": "rcv-source-grounded-office-orchestration-v0.6.0", "verified": not mismatches, "decision": DECISION_RUN if not mismatches else DECISION_PAUSE, "mismatch_count": len(mismatches), "mismatches": mismatches}


def run_single_attempt(
    *,
    run_id: str,
    scenario: str,
    selected_agents: list[str],
    original_task_snapshot: dict[str, Any],
    out_dir: Path,
    arl: AuditLog,
    loop_count: int,
) -> dict[str, Any]:
    raw_source_logs = create_source_logs(scenario, selected_agents, loop_count)
    source_report = tasukeru_analyze_source_logs(run_id=run_id, original_task_snapshot=original_task_snapshot, raw_source_logs=raw_source_logs, out_dir=out_dir)
    artifacts = create_office_artifacts(scenario=scenario, selected_agents=selected_agents, source_report=source_report, loop_count=loop_count)
    raw_artifact_logs = make_raw_artifact_logs(artifacts)
    artifact_report = tasukeru_analyze_artifact_logs(run_id=run_id, original_task_snapshot=original_task_snapshot, raw_artifact_logs=raw_artifact_logs, out_dir=out_dir, loop_count=loop_count)
    request = mediator_request_packet(run_id=run_id, task_id=original_task_snapshot["task_id"], loop_count=loop_count)
    request_verify = verify_mediator_request(request)
    write_json(out_dir / f"mediator_packet_request_loop_{loop_count}.json", request)
    write_json(out_dir / f"mediator_packet_request_verify_loop_{loop_count}.json", request_verify)
    mediation = mediator_reconcile(original_task_snapshot=original_task_snapshot, source_report=source_report, artifact_report=artifact_report, request_verify=request_verify, out_dir=out_dir, loop_count=loop_count)
    arl.append(layer="mediator", decision=mediation["decision"], sealed=False, overrideable=True, final_decider="USER" if mediation["requires_reconciliation"] else "SYSTEM", reason_code="MEDIATOR_RECONCILIATION_REQUIRED" if mediation["requires_reconciliation"] else "SOURCE_GROUNDED_RECONCILIATION_OK", message="Mediator completed source-grounded reconciliation.", loop_count=loop_count)
    return {"source_report": source_report, "artifacts": [asdict(artifact) for artifact in artifacts], "artifact_report": artifact_report, "mediator_request_verify": request_verify, "mediator_reconciliation": mediation}


def run_simulation(
    *,
    seed: int,
    out_dir: Path,
    scenario: str,
    selected_agents_value: str,
    human_action_mode: str,
) -> dict[str, Any]:
    rng = random.Random(seed)  # nosec B311 - deterministic simulation RNG; not used for secrets, tokens, auth, or cryptography.
    out_dir.mkdir(parents=True, exist_ok=True)
    if scenario == "random":
        scenario = rng.choice(["safe", "artifact_conflict", "primary_source_missing", "secondary_source_conflict", "fabricated_source_signal", "over_inference", "loop_limit", "pii", "confidential"])  # nosec B311 - simulation branch selection only.
    run_id = f"source-grounded-office-orchestration-v0.6.0-seed-{seed}-{scenario}"
    arl = AuditLog(run_id)
    agents, standby = build_agents()
    selected_agents = parse_selected_agents(selected_agents_value)
    original_task_snapshot = build_original_task_snapshot()
    write_json(out_dir / "original_user_task_snapshot.json", original_task_snapshot)
    arl.append(layer="maestro", decision=DECISION_RUN, sealed=False, overrideable=True, final_decider="USER", reason_code="USER_SELECTED_AGENTS_BEFORE_DISPATCH", message=f"User selected agents before dispatch: {','.join(selected_agents)}", loop_count=0)
    loop_count = 0
    attempts: list[dict[str, Any]] = []
    final_maestro: dict[str, Any] | None = None
    final_attempt: dict[str, Any] | None = None
    while True:
        attempt = run_single_attempt(run_id=run_id, scenario=scenario, selected_agents=selected_agents, original_task_snapshot=original_task_snapshot, out_dir=out_dir, arl=arl, loop_count=loop_count)
        maestro = maestro_handle_handoff(mediation=attempt["mediator_reconciliation"], action_mode=human_action_mode, rng=rng, arl=arl, loop_count=loop_count)
        attempt["maestro_result"] = maestro
        attempts.append(attempt)
        final_attempt = attempt
        final_maestro = maestro
        if maestro["task_decision"] in {DECISION_DRAFT_RESULT, DECISION_STOP, DECISION_DRAFT_REVIEW}:
            break
        if maestro["task_decision"] in {"RETRY_RESEARCH", "RETRY_REWRITE"}:
            loop_count += 1
            continue
        break
    assert final_attempt is not None
    assert final_maestro is not None
    arl.append(layer="orchestrator", decision=final_maestro["task_decision"], sealed=False, overrideable=False, final_decider="SYSTEM_AFTER_USER_OR_ADVISORY", reason_code="ORCHESTRATION_COMPLETED", message="Completed according to advisory result or explicit user action.", loop_count=loop_count)
    arl_verify = arl.verify()
    rcv = verify_result(original_task_snapshot=original_task_snapshot, selected_agents=selected_agents, source_report=final_attempt["source_report"], artifact_report=final_attempt["artifact_report"], mediator_request_verify=final_attempt["mediator_request_verify"], mediation=final_attempt["mediator_reconciliation"], maestro=final_maestro, arl_verify=arl_verify, loop_count=loop_count)
    result = {
        "schema_version": "source-grounded-office-orchestration-sim-v0.6.0",
        "run_id": run_id,
        "seed": seed,
        "scenario": scenario,
        "selected_agents": selected_agents,
        "human_action_mode": human_action_mode,
        "max_reconciliation_loops": MAX_RECONCILIATION_LOOPS,
        "final_loop_count": loop_count,
        "safety_boundary": {
            "local_only": True,
            "synthetic_sources_only": True,
            "real_source_fetching": False,
            "real_office_generation": False,
            "raw_source_log_handoff_to_mediator": False,
            "raw_artifact_log_handoff_to_mediator": False,
            "source_evidence_packet_only": True,
            "masked_metadata_packet_only": True,
            "external_communication": False,
            "real_process_control": False,
            "auto_apply_revision": False,
            "auto_fix_allowed": False,
            "auto_commit_allowed": False,
            "auto_push_allowed": False,
            "auto_merge_allowed": False,
            "final_output_is_draft_only": True,
        },
        "threshold_policy": {"threshold": THRESHOLD, "exact_threshold_handoff": False, "above_threshold_handoff": True},
        "original_task_snapshot": original_task_snapshot,
        "agents": [asdict(agent) for agent in agents.values()],
        "standby_agents": [asdict(agent) for agent in standby.values()],
        "attempts": attempts,
        "final_attempt": final_attempt,
        "maestro_result": final_maestro,
        "arl_verify": arl_verify,
        "result_consistency_verify": rcv,
        "final_decision": final_maestro["task_decision"],
    }
    write_json(out_dir / "simulation_result.json", result)
    write_json(out_dir / "maestro_handoff_result.json", final_maestro)
    write_json(out_dir / "tasukeru_result_consistency_verify.json", rcv)
    write_json(out_dir / "tasukeru_arl_verify.json", arl_verify)
    arl.write_jsonl(out_dir / "tasukeru_arl.jsonl")
    summary = [
        "# Source-Grounded Office Orchestration + Tasukeru + Maestro Simulation v0.6.0",
        "",
        f"- seed: `{seed}`",
        f"- scenario: `{scenario}`",
        f"- selected_agents: `{','.join(selected_agents)}`",
        f"- attempts: `{len(attempts)}`",
        f"- final_loop_count: `{loop_count}`",
        f"- collision_score: `{final_attempt['mediator_reconciliation']['collision_score']}`",
        f"- mediation_decision: `{final_attempt['mediator_reconciliation']['decision']}`",
        f"- reconciliation_required: `{final_attempt['mediator_reconciliation']['requires_reconciliation']}`",
        f"- hitl_triggered: `{final_maestro['hitl_triggered']}`",
        f"- human_action: `{final_maestro['human_action']}`",
        f"- final_decision: `{final_maestro['task_decision']}`",
        f"- ARL verified: `{arl_verify['verified']}`",
        f"- RCV verified: `{rcv['verified']}`",
    ]
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only source-grounded Office orchestration simulation with Tasukeru, Mediator, Maestro, and HITL.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("source_grounded_office_orchestration_out_v0_6_0"))
    parser.add_argument("--scenario", choices=["safe", "artifact_conflict", "primary_source_missing", "secondary_source_conflict", "fabricated_source_signal", "over_inference", "loop_limit", "pii", "confidential", "random"], default="artifact_conflict")
    parser.add_argument("--selected-agents", default="all", help="Comma-separated user-selected agent IDs, or 'all'. Maestro does not select agents autonomously.")
    parser.add_argument("--human-action", choices=["random", *ACTIONS], default="USER_HITL_REWRITE_APPROVED")
    args = parser.parse_args()
    result = run_simulation(seed=args.seed, out_dir=args.out_dir, scenario=args.scenario, selected_agents_value=args.selected_agents, human_action_mode=args.human_action)
    final_attempt = result["final_attempt"]
    mediation = final_attempt["mediator_reconciliation"]
    maestro = result["maestro_result"]
    print("Source-Grounded Office Orchestration + Tasukeru + Maestro Simulation v0.6.0")
    print(f"seed={result['seed']}")
    print(f"scenario={result['scenario']}")
    print(f"selected_agents={','.join(result['selected_agents'])}")
    print(f"attempts={len(result['attempts'])}")
    print(f"final_loop_count={result['final_loop_count']}")
    print(f"collision_score={mediation['collision_score']}")
    print(f"mediation_decision={mediation['decision']}")
    print(f"reconciliation_required={mediation['requires_reconciliation']}")
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
