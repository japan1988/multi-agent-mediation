"""Draft-only evaluator pseudocode for the AI-to-AI Mediation Control Plane.

This file is intentionally side-effect free. It does not call external APIs,
execute candidate code, modify files, approve deployments, or change safety
thresholds. It sketches control-flow only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Level(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"


class Decision(str, Enum):
    CONTINUE = "CONTINUE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    ISOLATED_REVIEW_REQUIRED = "ISOLATED_REVIEW_REQUIRED"
    STOP_AND_PRESERVE = "STOP_AND_PRESERVE"


@dataclass(frozen=True)
class Observation:
    declared_purpose: str
    requested_actions: tuple[str, ...] = ()
    observed_actions: tuple[str, ...] = ()
    read_targets: tuple[str, ...] = ()
    available_tools: tuple[str, ...] = ()
    granted_permissions: tuple[str, ...] = ()
    capability_signals: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Classification:
    level: Level
    decision: Decision
    rationale: tuple[str, ...]
    blocked_actions: tuple[str, ...] = field(default_factory=tuple)


SENSITIVE_READ_TARGETS = frozenset(
    {
        "credentials",
        "api_keys",
        "private_keys",
        "tokens",
        "personal_data",
        "confidential_documents",
        "unpublished_model_specs",
        "vulnerability_details",
        "dangerous_domain_procedures",
    }
)

EXTERNAL_STATE_CHANGE_ACTIONS = frozenset(
    {
        "file_write",
        "code_execution",
        "api_write",
        "database_update",
        "email_send",
        "pull_request_change",
        "ticket_change",
        "ci_cd_trigger",
        "deployment_path_access",
        "credential_use",
    }
)

SELF_IMPROVEMENT_ACTIONS = frozenset(
    {
        "own_prompt_change",
        "own_rule_change",
        "own_evaluator_change",
        "another_ai_capability_change",
        "ai_generation_workflow_change",
        "safety_threshold_change",
    }
)

EVOLUTION_LOOP_SIGNALS = frozenset(
    {
        "iterative_generate_evaluate_select_improve",
        "automatic_next_generation_update",
        "next_generation_creates_further_ai",
        "capability_ceiling_breakthrough_objective",
        "human_review_bypass_in_improvement_loop",
        "evaluator_or_mediation_ai_targeted_for_improvement",
        "audit_evasion_or_capability_delta_hiding",
    }
)


def intersects(values: Iterable[str], markers: frozenset[str]) -> bool:
    return any(value in markers for value in values)


def classify_external_action_level(obs: Observation) -> tuple[Level, list[str]]:
    """Classify observed/requested behavior without approving any action."""
    rationale: list[str] = []
    actions = tuple(obs.requested_actions) + tuple(obs.observed_actions)

    if intersects(obs.capability_signals, EVOLUTION_LOOP_SIGNALS):
        rationale.append("evolution-loop signal detected")
        return Level.L6, rationale

    if intersects(actions, SELF_IMPROVEMENT_ACTIONS):
        rationale.append("self-improvement or evaluator-change action detected")
        return Level.L5, rationale

    if intersects(actions, EXTERNAL_STATE_CHANGE_ACTIONS):
        rationale.append("external state change action detected")
        return Level.L4, rationale

    if obs.read_targets:
        if intersects(obs.read_targets, SENSITIVE_READ_TARGETS):
            rationale.append("sensitive read target detected; L3 escalates to L4")
            return Level.L4, rationale
        rationale.append("external read-only behavior detected")
        return Level.L3, rationale

    if "local_generation" in actions:
        rationale.append("local generation without execution detected")
        return Level.L2, rationale

    if "planning" in actions or "analysis" in actions:
        rationale.append("internal reasoning detected")
        return Level.L1, rationale

    rationale.append("internal response only")
    return Level.L0, rationale


def route(level: Level) -> Decision:
    """Map a level to a review route."""
    if level == Level.L6:
        return Decision.STOP_AND_PRESERVE
    if level == Level.L5:
        return Decision.ISOLATED_REVIEW_REQUIRED
    if level == Level.L4:
        return Decision.HUMAN_REVIEW_REQUIRED
    return Decision.CONTINUE


def classify(obs: Observation) -> Classification:
    level, rationale = classify_external_action_level(obs)
    decision = route(level)
    blocked_actions = (
        "final_approval",
        "production_deployment",
        "external_api_write",
        "credential_use",
        "safety_threshold_change",
        "evaluator_change",
        "training_or_finetuning",
        "self_improvement_loop",
        "log_deletion",
    )
    return Classification(
        level=level,
        decision=decision,
        rationale=tuple(rationale),
        blocked_actions=blocked_actions,
    )


def build_human_review_stub(obs: Observation, classification: Classification) -> dict[str, object]:
    """Return a redacted, review-oriented summary structure."""
    return {
        "declared_purpose": obs.declared_purpose,
        "external_action_level": classification.level.value,
        "decision": classification.decision.value,
        "rationale": list(classification.rationale),
        "unknowns": list(obs.unknowns),
        "prohibited_auto_actions": list(classification.blocked_actions),
        "human_decision_points": [
            "Confirm baseline or parent-AI comparison method.",
            "Confirm whether requested authority is justified.",
            "Confirm isolation requirements before any L5 continuation.",
        ],
    }


if __name__ == "__main__":
    sample = Observation(
        declared_purpose="Draft a review plan for an AI generation workflow.",
        requested_actions=("planning",),
    )
    result = classify(sample)
    print(build_human_review_stub(sample, result))

