# SPDX-License-Identifier: MIT
#
# Research / education purpose only.
# This is a local simulation and advisory-only contract prototype.
# It does not execute exploits, access external systems, modify repositories,
# apply remediation, merge code, or provide production safety guarantees.
# Static findings are candidates, not proof of exploitable vulnerabilities.

from __future__ import annotations

"""
Minimal Security Orchestration Simulation
==========================================

DRAFT_SIMULATION_ONLY.

This module implements:

Phase 1 - Minimal Authority Routing Contract
    * USER_DECISION_RECORD
    * DISPATCH_RECORD
    * evaluate_user_decision()
    * route_dispatch()
    * validators

Phase 2 - Common Finding Simulation
    * SEC-PAT-001: hard-coded secret candidate
    * SEC-PAT-002: OS command injection candidate
    * SEC-PAT-003: SQL injection candidate
    * SEC-PAT-004: path traversal candidate
    * SEC-PAT-005: CI/CD auto-merge or excessive-permission candidate
    * static read-only finding agents
    * primary mediator review
    * Maestro presentation result

Non-goals / prohibited behavior:
    * No exploit execution
    * No external scanning or network access
    * No file modification
    * No automatic remediation generation, application, or merge
    * No automatic apply or merge
    * DRAFT_REMEDIATION records are non-executing static proposal records only

The scanners report candidates based on static patterns. A finding is not a
proof that an exploitable vulnerability exists.

DRAFT_FIX-A applied in this file:
    * Harden authority-routing validators against malformed/forged records.

DRAFT_FIX-B applied in this file:
    * Add constrained same-function taint propagation for local variables used
      in command execution candidate detection.
    * Add pathlib Path(...).open/read/write method candidate detection.
    * Add masked token-like unquoted text detection, classified conservatively
      in Python source and as a stronger candidate in configuration-style files.

DRAFT_FIX-C applied in this file:
    * Add PRIMARY_MEDIATION_INPUT so a no-finding result requires completed
      expected-Agent reports for the authorized snapshot and scope.
    * Harden FINDING_REPORT contract validation with a pattern/Agent/type
      allowlist and scope binding.
    * Add explicit primary mediation results for incomplete audits and report
      logic conflicts while preserving safety-boundary priority.

DRAFT_FIX-D applied in this file:
    * Add REMEDIATION_AUTHORIZATION so User HITL can authorize only selected
      Finding IDs and explicit draft/inspection scopes.
    * Keep inspection_scope and draft_change_scope separate and snapshot-bound.
    * Refuse automatic apply/merge or machine-application authority and keep
      isolated verification behind separate User authorization.
    * Do not generate or apply remediation; this phase records permission only.

DRAFT_FIX-E applied in this file:
    * Add DRAFT_REMEDIATION as a static-text proposal record that can be created
      only from a valid, granted REMEDIATION_AUTHORIZATION.
    * Bind proposed diff text to authorized Finding IDs, base snapshot, and
      draft_change_scope using a SHA-256 digest and unified-diff target parsing.
    * Keep the draft non-executing, non-applying, non-merging, and pending
      mandatory secondary mediation and User application decision.

DRAFT_FIX-F applied in this file:
    * Add REMEDIATION_IMPACT_REPORT as a specialist-Agent static review record
      created only from a validated DRAFT_REMEDIATION.
    * Bind each report to the source draft hash, authorized Finding IDs,
      inspection_scope, base snapshot, and reviewed_context_snapshot_id.
    * Permit a report to identify an impact candidate, request scope expansion,
      or return a separate new Finding candidate without modifying the draft or
      granting any execution, apply, merge, or verification capability.

DRAFT_FIX-G applied in this file:
    * Add SECONDARY_MEDIATION_INPUT / SECONDARY_MEDIATION_RESULT so Mediator
      can classify completed specialist impact reports for one bound draft.
    * Require complete expected-Agent reporting, common draft/hash/snapshot
      bindings, and current review-context validity before DRAFT_PRESENTABLE.
    * Keep DRAFT_PRESENTABLE distinct from safety confirmation, verification,
      application permission, merge permission, or workflow progression.

DRAFT_FIX-H applied in this file:
    * Add HITL_DRAFT_DISPOSITION_INPUT / HITL_DRAFT_DISPOSITION_RESULT so User
      HITL can record how a DRAFT_PRESENTABLE draft is handled.
    * Permit acknowledgment, hold, rejection, or a request to consider a
      separate isolated-verification authorization contract.
    * Keep a verification request distinct from verification authorization and
      prohibit application, merge, close, code change, or automatic progression.

DRAFT_FIX-I applied in this file:
    * Add ISOLATED_VERIFICATION_AUTHORIZATION_INPUT / RESULT so User HITL can
      authorize, hold, or reject a bounded isolated-verification plan only.
    * Accept only an H result that recorded a request for a separate isolated-
      verification authorization contract.
    * Restrict planned checks to an enum allowlist and bounded deterministic
      stress parameters; no arbitrary command text is accepted.
    * Keep plan authorization distinct from verification execution and prohibit
      external access, repository writes, apply, merge, close, and post-change
      audit progression.

Still intentionally out of scope:
    * Exploit execution, external scanning, remediation application, or automatic apply.
    * Isolated verification execution, remediation application, or post-change audit.
    * General interprocedural taint analysis.
    * Snapshot resource-limit policy for real-repository deployment.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path, PurePosixPath
import ast
import os
import re
from typing import Iterable, Iterator, Mapping, Sequence


# ---------------------------------------------------------------------------
# Contract primitives
# ---------------------------------------------------------------------------


class ContractViolation(ValueError):
    """Raised when a record or transition violates a fixed invariant."""


class AgentId(str, Enum):
    CODE_SECURITY_FINDING_AGENT = "CODE_SECURITY_FINDING_AGENT"
    SECRET_PII_FINDING_AGENT = "SECRET_PII_FINDING_AGENT"
    CICD_PERMISSION_FINDING_AGENT = "CICD_PERMISSION_FINDING_AGENT"

    # Declared for later phases; not dispatched by this initial scanner.
    DEPENDENCY_SUPPLY_CHAIN_FINDING_AGENT = "DEPENDENCY_SUPPLY_CHAIN_FINDING_AGENT"
    CONFIG_RELEASE_FINDING_AGENT = "CONFIG_RELEASE_FINDING_AGENT"
    REMEDIATION_DRAFT_AGENT = "REMEDIATION_DRAFT_AGENT"
    TASUKERU = "TASUKERU"


class Action(str, Enum):
    READ_ONLY_STATIC_AUDIT = "READ_ONLY_STATIC_AUDIT"

    # Outside the current phase.
    CREATE_DRAFT_REMEDIATION = "CREATE_DRAFT_REMEDIATION"
    RUN_ISOLATED_VERIFICATION = "RUN_ISOLATED_VERIFICATION"

    # Non-dispatchable safety-boundary violations.
    AUTO_APPLY = "AUTO_APPLY"
    AUTO_MERGE = "AUTO_MERGE"
    EXECUTE_EXPLOIT = "EXECUTE_EXPLOIT"
    EXTERNAL_ATTACK = "EXTERNAL_ATTACK"
    DISABLE_AUDIT = "DISABLE_AUDIT"


class AuthorizationEffect(str, Enum):
    GRANTED_WITHIN_BOUNDARY = "GRANTED_WITHIN_BOUNDARY"
    HOLD_REQUIRES_ADDITIONAL_HITL = "HOLD_REQUIRES_ADDITIONAL_HITL"
    NOT_GRANTED_NON_DISPATCHABLE = "NOT_GRANTED_NON_DISPATCHABLE"


class RoutingResult(str, Enum):
    DISPATCH_USER_AUTHORIZED_TASK = "DISPATCH_USER_AUTHORIZED_TASK"
    HOLD_DISPATCH_FOR_HITL = "HOLD_DISPATCH_FOR_HITL"
    NON_DISPATCHABLE_BOUNDARY_VIOLATION = "NON_DISPATCHABLE_BOUNDARY_VIOLATION"


class HoldReasonCode(str, Enum):
    AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
    AGENT_NOT_AUTHORIZED = "AGENT_NOT_AUTHORIZED"
    SCOPE_NOT_AUTHORIZED = "SCOPE_NOT_AUTHORIZED"
    SNAPSHOT_STALE = "SNAPSHOT_STALE"
    ACTION_NOT_IN_CURRENT_PHASE = "ACTION_NOT_IN_CURRENT_PHASE"


class NonDispatchableReasonCode(str, Enum):
    AUTO_APPLY_PROHIBITED = "AUTO_APPLY_PROHIBITED"
    AUTO_MERGE_PROHIBITED = "AUTO_MERGE_PROHIBITED"
    EXPLOIT_EXECUTION_PROHIBITED = "EXPLOIT_EXECUTION_PROHIBITED"
    EXTERNAL_ATTACK_PROHIBITED = "EXTERNAL_ATTACK_PROHIBITED"
    AUDIT_DISABLE_PROHIBITED = "AUDIT_DISABLE_PROHIBITED"


class EvidenceType(str, Enum):
    DIRECT_STATIC_OBSERVATION = "DIRECT_STATIC_OBSERVATION"
    STATIC_PATTERN_CANDIDATE = "STATIC_PATTERN_CANDIDATE"


class SeverityCandidate(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class MediationDecision(str, Enum):
    NO_FINDING_DETECTED_WITHIN_SCOPE = "NO_FINDING_DETECTED_WITHIN_SCOPE"
    FINDING_PRESENT = "FINDING_PRESENT"
    DUPLICATE_FINDING_MERGED = "DUPLICATE_FINDING_MERGED"
    REPORT_LOGIC_CONFLICT = "REPORT_LOGIC_CONFLICT"
    AGENT_OUTPUT_CONFLICT = "AGENT_OUTPUT_CONFLICT"  # Reserved until negative reports exist.
    AUDIT_RESULT_INCOMPLETE = "AUDIT_RESULT_INCOMPLETE"
    SAFETY_BOUNDARY_CONFLICT = "SAFETY_BOUNDARY_CONFLICT"


class PrimaryMediationReasonCode(str, Enum):
    COMPLETED_NO_FINDING = "COMPLETED_NO_FINDING"
    CANDIDATE_FINDING_PRESENT = "CANDIDATE_FINDING_PRESENT"
    DUPLICATE_FINDING_CONSOLIDATED = "DUPLICATE_FINDING_CONSOLIDATED"
    INVALID_FINDING_REPORT = "INVALID_FINDING_REPORT"
    EXPECTED_AGENT_RESULT_MISSING = "EXPECTED_AGENT_RESULT_MISSING"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"
    SNAPSHOT_CONTEXT_MISMATCH = "SNAPSHOT_CONTEXT_MISMATCH"
    SCOPE_CONTEXT_MISMATCH = "SCOPE_CONTEXT_MISMATCH"
    AGENT_REPORT_BOUNDARY_VIOLATION = "AGENT_REPORT_BOUNDARY_VIOLATION"


STATIC_AUDIT_AGENTS = frozenset(
    {
        AgentId.CODE_SECURITY_FINDING_AGENT,
        AgentId.SECRET_PII_FINDING_AGENT,
        AgentId.CICD_PERMISSION_FINDING_AGENT,
    }
)

NON_DISPATCHABLE_ACTIONS: Mapping[Action, NonDispatchableReasonCode] = {
    Action.AUTO_APPLY: NonDispatchableReasonCode.AUTO_APPLY_PROHIBITED,
    Action.AUTO_MERGE: NonDispatchableReasonCode.AUTO_MERGE_PROHIBITED,
    Action.EXECUTE_EXPLOIT: NonDispatchableReasonCode.EXPLOIT_EXECUTION_PROHIBITED,
    Action.EXTERNAL_ATTACK: NonDispatchableReasonCode.EXTERNAL_ATTACK_PROHIBITED,
    Action.DISABLE_AUDIT: NonDispatchableReasonCode.AUDIT_DISABLE_PROHIBITED,
}


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _normalize_relative_path(raw: str) -> str:
    normalized = raw.replace("\\", "/").strip()
    if not normalized:
        raise ContractViolation("Scope path must not be empty.")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ContractViolation(f"Scope path must be relative and contained: {raw!r}")
    return path.as_posix().rstrip("/") or "."


@dataclass(frozen=True)
class Scope:
    """Relative file or directory paths covered by a User authorization."""

    paths: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized = tuple(sorted({_normalize_relative_path(p) for p in self.paths}))
        if not normalized:
            raise ContractViolation("Scope must contain at least one path.")
        object.__setattr__(self, "paths", normalized)

    def covers(self, requested: "Scope") -> bool:
        for target in requested.paths:
            if not any(
                allowed == "."
                or target == allowed
                or target.startswith(f"{allowed}/")
                for allowed in self.paths
            ):
                return False
        return True


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    action: Action
    agent_id: AgentId
    scope: Scope
    snapshot_id: str


@dataclass(frozen=True)
class AuthorizedAction:
    action: Action
    agent_id: AgentId
    scope: Scope
    base_snapshot_id: str
    expires_if_snapshot_changed: bool = True


@dataclass(frozen=True)
class UserDecisionRecord:
    decision_id: str
    requested_action: ActionRequest
    authorization_effect: AuthorizationEffect
    authorized_action: AuthorizedAction | None
    hold_reason_code: HoldReasonCode | None = None
    non_dispatchable_reason_code: NonDispatchableReasonCode | None = None
    decided_by: str = "USER"
    decision_source: str = "USER_HITL"


@dataclass(frozen=True)
class DispatchRequest:
    action: Action
    target_agent: AgentId
    target_scope: Scope
    target_snapshot_id: str


@dataclass(frozen=True)
class DispatchRecord:
    dispatch_id: str
    source_decision_id: str
    requested_dispatch: DispatchRequest
    user_authorized: bool
    snapshot_valid: bool
    within_safety_boundary: bool
    routing_result: RoutingResult
    hold_reason_code: HoldReasonCode | None = None
    non_dispatchable_reason_code: NonDispatchableReasonCode | None = None

    # These flags make Maestro boundary violations explicit and testable.
    maestro_expanded_scope: bool = False
    maestro_modified_action: bool = False
    maestro_started_unapproved_task: bool = False
    maestro_suppressed_escalation: bool = False


# ---------------------------------------------------------------------------
# Phase 1: User decision evaluation and Maestro dispatch
# ---------------------------------------------------------------------------


def _require_enum_instance(value: object, enum_type: type[Enum], field_name: str) -> None:
    """Reject raw strings or unknown values restored into contract records."""
    if not isinstance(value, enum_type):
        raise ContractViolation(
            f"{field_name} must be an instance of {enum_type.__name__}; "
            f"received {value!r}."
        )


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"{field_name} must be a non-empty string.")


def _require_bool(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise ContractViolation(f"{field_name} must be a boolean.")


def validate_action_request(request: ActionRequest) -> None:
    if not isinstance(request, ActionRequest):
        raise ContractViolation("requested_action must be an ActionRequest.")
    _require_text(request.request_id, "requested_action.request_id")
    _require_enum_instance(request.action, Action, "requested_action.action")
    _require_enum_instance(request.agent_id, AgentId, "requested_action.agent_id")
    if not isinstance(request.scope, Scope):
        raise ContractViolation("requested_action.scope must be a Scope.")
    _require_text(request.snapshot_id, "requested_action.snapshot_id")


def validate_authorized_action(action: AuthorizedAction) -> None:
    if not isinstance(action, AuthorizedAction):
        raise ContractViolation("authorized_action must be an AuthorizedAction or null.")
    _require_enum_instance(action.action, Action, "authorized_action.action")
    _require_enum_instance(action.agent_id, AgentId, "authorized_action.agent_id")
    if not isinstance(action.scope, Scope):
        raise ContractViolation("authorized_action.scope must be a Scope.")
    _require_text(action.base_snapshot_id, "authorized_action.base_snapshot_id")
    if action.expires_if_snapshot_changed is not True:
        raise ContractViolation(
            "authorized_action.expires_if_snapshot_changed must remain true."
        )


def validate_dispatch_request(request: DispatchRequest) -> None:
    if not isinstance(request, DispatchRequest):
        raise ContractViolation("requested_dispatch must be a DispatchRequest.")
    _require_enum_instance(request.action, Action, "requested_dispatch.action")
    _require_enum_instance(request.target_agent, AgentId, "requested_dispatch.target_agent")
    if not isinstance(request.target_scope, Scope):
        raise ContractViolation("requested_dispatch.target_scope must be a Scope.")
    _require_text(request.target_snapshot_id, "requested_dispatch.target_snapshot_id")


def _require_dispatch_matches_original_request(
    dispatch: DispatchRequest, original: ActionRequest
) -> None:
    """A routed record must describe the exact request evaluated by USER_HITL."""
    if dispatch.action is not original.action:
        raise ContractViolation("DISPATCH_RECORD changed the requested action.")
    if dispatch.target_agent is not original.agent_id:
        raise ContractViolation("DISPATCH_RECORD changed the requested target agent.")
    if dispatch.target_scope != original.scope:
        raise ContractViolation("DISPATCH_RECORD changed the requested scope.")
    if dispatch.target_snapshot_id != original.snapshot_id:
        raise ContractViolation("DISPATCH_RECORD changed the requested snapshot binding.")


def _require_dispatch_matches_authorized_action(
    dispatch: DispatchRequest, authorized: AuthorizedAction
) -> None:
    if dispatch.action is not authorized.action:
        raise ContractViolation("DISPATCH_RECORD modified the authorized action.")
    if dispatch.target_agent is not authorized.agent_id:
        raise ContractViolation("DISPATCH_RECORD modified the authorized target agent.")
    if dispatch.target_scope != authorized.scope:
        raise ContractViolation("DISPATCH_RECORD expanded or altered authorized scope.")
    if dispatch.target_snapshot_id != authorized.base_snapshot_id:
        raise ContractViolation("DISPATCH_RECORD modified the authorized snapshot binding.")


def evaluate_user_decision(
    request: ActionRequest,
    *,
    user_approved: bool,
    approved_agents: Sequence[AgentId] = (),
    approved_scope: Scope | None = None,
) -> UserDecisionRecord:
    """
    Evaluate a User HITL response against fixed safety boundaries.

    requested_action is recorded whether or not it becomes authorized_action.
    A prohibited request is never converted into an authorization.
    """
    validate_action_request(request)
    for index, agent in enumerate(approved_agents):
        _require_enum_instance(agent, AgentId, f"approved_agents[{index}]")
    if approved_scope is not None and not isinstance(approved_scope, Scope):
        raise ContractViolation("approved_scope must be a Scope or null.")

    decision_id = _stable_id("UDR", request.request_id, request.action.value)

    if request.action in NON_DISPATCHABLE_ACTIONS:
        record = UserDecisionRecord(
            decision_id=decision_id,
            requested_action=request,
            authorization_effect=AuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE,
            authorized_action=None,
            non_dispatchable_reason_code=NON_DISPATCHABLE_ACTIONS[request.action],
        )
        validate_user_decision_record(record)
        return record

    if request.action is not Action.READ_ONLY_STATIC_AUDIT:
        record = UserDecisionRecord(
            decision_id=decision_id,
            requested_action=request,
            authorization_effect=AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            authorized_action=None,
            hold_reason_code=HoldReasonCode.ACTION_NOT_IN_CURRENT_PHASE,
        )
        validate_user_decision_record(record)
        return record

    if not user_approved:
        record = UserDecisionRecord(
            decision_id=decision_id,
            requested_action=request,
            authorization_effect=AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            authorized_action=None,
            hold_reason_code=HoldReasonCode.AUTHORIZATION_MISSING,
        )
        validate_user_decision_record(record)
        return record

    if request.agent_id not in STATIC_AUDIT_AGENTS or request.agent_id not in set(approved_agents):
        record = UserDecisionRecord(
            decision_id=decision_id,
            requested_action=request,
            authorization_effect=AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            authorized_action=None,
            hold_reason_code=HoldReasonCode.AGENT_NOT_AUTHORIZED,
        )
        validate_user_decision_record(record)
        return record

    if approved_scope is None or not approved_scope.covers(request.scope):
        record = UserDecisionRecord(
            decision_id=decision_id,
            requested_action=request,
            authorization_effect=AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            authorized_action=None,
            hold_reason_code=HoldReasonCode.SCOPE_NOT_AUTHORIZED,
        )
        validate_user_decision_record(record)
        return record

    # Least privilege: authorize exactly the requested task, not the broader
    # User-approved envelope.
    record = UserDecisionRecord(
        decision_id=decision_id,
        requested_action=request,
        authorization_effect=AuthorizationEffect.GRANTED_WITHIN_BOUNDARY,
        authorized_action=AuthorizedAction(
            action=request.action,
            agent_id=request.agent_id,
            scope=request.scope,
            base_snapshot_id=request.snapshot_id,
        ),
    )
    validate_user_decision_record(record)
    return record


def validate_user_decision_record(record: UserDecisionRecord) -> None:
    if not isinstance(record, UserDecisionRecord):
        raise ContractViolation("Record must be a USER_DECISION_RECORD.")
    _require_text(record.decision_id, "decision_id")
    validate_action_request(record.requested_action)
    _require_enum_instance(
        record.authorization_effect,
        AuthorizationEffect,
        "authorization_effect",
    )
    if record.hold_reason_code is not None:
        _require_enum_instance(record.hold_reason_code, HoldReasonCode, "hold_reason_code")
    if record.non_dispatchable_reason_code is not None:
        _require_enum_instance(
            record.non_dispatchable_reason_code,
            NonDispatchableReasonCode,
            "non_dispatchable_reason_code",
        )
    if record.authorized_action is not None:
        validate_authorized_action(record.authorized_action)

    if record.decided_by != "USER" or record.decision_source != "USER_HITL":
        raise ContractViolation("USER_DECISION_RECORD must originate from USER_HITL.")

    requested_action = record.requested_action.action
    granted = record.authorization_effect is AuthorizationEffect.GRANTED_WITHIN_BOUNDARY

    if requested_action in NON_DISPATCHABLE_ACTIONS:
        expected_reason = NON_DISPATCHABLE_ACTIONS[requested_action]
        if record.authorization_effect is not AuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE:
            raise ContractViolation(
                "A non-dispatchable requested action must be recorded as "
                "NOT_GRANTED_NON_DISPATCHABLE."
            )
        if record.non_dispatchable_reason_code is not expected_reason:
            raise ContractViolation(
                "Non-dispatchable reason code does not match the prohibited action."
            )

    if not granted and record.authorized_action is not None:
        raise ContractViolation(
            "authorization_effect != GRANTED_WITHIN_BOUNDARY "
            "requires authorized_action to be null."
        )

    if granted:
        authorized = record.authorized_action
        if authorized is None:
            raise ContractViolation("Granted decision must contain authorized_action.")
        if requested_action is not Action.READ_ONLY_STATIC_AUDIT:
            raise ContractViolation("Only READ_ONLY_STATIC_AUDIT may be granted in this phase.")
        if record.hold_reason_code is not None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("Granted decision must not contain rejection reason codes.")
        if authorized.action is not requested_action:
            raise ContractViolation("authorized_action must not change requested_action.")
        if authorized.agent_id is not record.requested_action.agent_id:
            raise ContractViolation("authorized_action must not change the requested agent.")
        if authorized.scope != record.requested_action.scope:
            raise ContractViolation("authorized_action must not expand or alter requested scope.")
        if authorized.base_snapshot_id != record.requested_action.snapshot_id:
            raise ContractViolation("authorized_action must remain bound to requested snapshot.")
    elif record.authorization_effect is AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL:
        if requested_action in NON_DISPATCHABLE_ACTIONS:
            raise ContractViolation("Prohibited actions cannot be downgraded to HOLD.")
        if record.hold_reason_code is None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("HOLD decision requires hold_reason_code only.")
    elif record.authorization_effect is AuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE:
        if requested_action not in NON_DISPATCHABLE_ACTIONS:
            raise ContractViolation(
                "NOT_GRANTED_NON_DISPATCHABLE requires a prohibited requested action."
            )
        if record.non_dispatchable_reason_code is None or record.hold_reason_code is not None:
            raise ContractViolation(
                "Non-dispatchable decision requires non_dispatchable_reason_code only."
            )


def route_dispatch(
    decision: UserDecisionRecord,
    dispatch: DispatchRequest,
    *,
    current_snapshot_id: str,
) -> DispatchRecord:
    """
    Route only an already authorized task.

    Maestro may not expand, replace, or reinterpret an authorized task.
    Such attempts are invariant violations rather than new authorization requests.
    """
    validate_user_decision_record(decision)
    validate_dispatch_request(dispatch)
    _require_text(current_snapshot_id, "current_snapshot_id")
    _require_dispatch_matches_original_request(dispatch, decision.requested_action)
    dispatch_id = _stable_id("DSP", decision.decision_id, dispatch.action.value)

    if decision.authorization_effect is AuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE:
        record = DispatchRecord(
            dispatch_id=dispatch_id,
            source_decision_id=decision.decision_id,
            requested_dispatch=dispatch,
            user_authorized=False,
            snapshot_valid=False,
            within_safety_boundary=False,
            routing_result=RoutingResult.NON_DISPATCHABLE_BOUNDARY_VIOLATION,
            non_dispatchable_reason_code=decision.non_dispatchable_reason_code,
        )
        validate_dispatch_record(record, source_decision=decision)
        return record

    if decision.authorization_effect is AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL:
        record = DispatchRecord(
            dispatch_id=dispatch_id,
            source_decision_id=decision.decision_id,
            requested_dispatch=dispatch,
            user_authorized=False,
            snapshot_valid=dispatch.target_snapshot_id == current_snapshot_id,
            within_safety_boundary=True,
            routing_result=RoutingResult.HOLD_DISPATCH_FOR_HITL,
            hold_reason_code=decision.hold_reason_code,
        )
        validate_dispatch_record(record, source_decision=decision)
        return record

    authorized = decision.authorized_action
    if authorized is None:
        raise ContractViolation("Granted decision is missing authorized_action.")
    _require_dispatch_matches_authorized_action(dispatch, authorized)

    snapshot_valid = (
        dispatch.target_snapshot_id == authorized.base_snapshot_id == current_snapshot_id
    )
    if not snapshot_valid:
        record = DispatchRecord(
            dispatch_id=dispatch_id,
            source_decision_id=decision.decision_id,
            requested_dispatch=dispatch,
            user_authorized=True,
            snapshot_valid=False,
            within_safety_boundary=True,
            routing_result=RoutingResult.HOLD_DISPATCH_FOR_HITL,
            hold_reason_code=HoldReasonCode.SNAPSHOT_STALE,
        )
        validate_dispatch_record(record, source_decision=decision)
        return record

    record = DispatchRecord(
        dispatch_id=dispatch_id,
        source_decision_id=decision.decision_id,
        requested_dispatch=dispatch,
        user_authorized=True,
        snapshot_valid=True,
        within_safety_boundary=True,
        routing_result=RoutingResult.DISPATCH_USER_AUTHORIZED_TASK,
    )
    validate_dispatch_record(record, source_decision=decision)
    return record


def validate_dispatch_record(
    record: DispatchRecord,
    *,
    source_decision: UserDecisionRecord,
) -> None:
    if not isinstance(record, DispatchRecord):
        raise ContractViolation("Record must be a DISPATCH_RECORD.")
    validate_user_decision_record(source_decision)
    _require_text(record.dispatch_id, "dispatch_id")
    _require_text(record.source_decision_id, "source_decision_id")
    validate_dispatch_request(record.requested_dispatch)
    _require_enum_instance(record.routing_result, RoutingResult, "routing_result")
    if record.hold_reason_code is not None:
        _require_enum_instance(record.hold_reason_code, HoldReasonCode, "hold_reason_code")
    if record.non_dispatchable_reason_code is not None:
        _require_enum_instance(
            record.non_dispatchable_reason_code,
            NonDispatchableReasonCode,
            "non_dispatchable_reason_code",
        )

    if record.source_decision_id != source_decision.decision_id:
        raise ContractViolation("DISPATCH_RECORD must reference its USER_DECISION_RECORD.")

    _require_dispatch_matches_original_request(
        record.requested_dispatch, source_decision.requested_action
    )

    if any(
        (
            record.maestro_expanded_scope,
            record.maestro_modified_action,
            record.maestro_started_unapproved_task,
            record.maestro_suppressed_escalation,
        )
    ):
        raise ContractViolation("Maestro boundary flags must remain false.")

    if record.routing_result is RoutingResult.DISPATCH_USER_AUTHORIZED_TASK:
        if source_decision.authorization_effect is not AuthorizationEffect.GRANTED_WITHIN_BOUNDARY:
            raise ContractViolation("Dispatch requires GRANTED_WITHIN_BOUNDARY.")
        authorized = source_decision.authorized_action
        if authorized is None:
            raise ContractViolation("Dispatch requires an authorized_action.")
        _require_dispatch_matches_authorized_action(record.requested_dispatch, authorized)
        if not record.user_authorized or not record.snapshot_valid or not record.within_safety_boundary:
            raise ContractViolation(
                "Dispatch requires user_authorized, snapshot_valid, and "
                "within_safety_boundary to all be true."
            )
        if record.hold_reason_code is not None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("Dispatched record must not contain reason codes.")

    elif record.routing_result is RoutingResult.HOLD_DISPATCH_FOR_HITL:
        if record.hold_reason_code is None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("HOLD dispatch requires hold_reason_code only.")
        if not record.within_safety_boundary:
            raise ContractViolation("HOLD must remain within the safety boundary.")
        if source_decision.authorization_effect is AuthorizationEffect.GRANTED_WITHIN_BOUNDARY:
            authorized = source_decision.authorized_action
            if authorized is None:
                raise ContractViolation("Stale HOLD requires an authorized_action.")
            _require_dispatch_matches_authorized_action(record.requested_dispatch, authorized)
            if record.hold_reason_code is not HoldReasonCode.SNAPSHOT_STALE:
                raise ContractViolation("A held granted action must be stale by snapshot.")
            if not record.user_authorized or record.snapshot_valid:
                raise ContractViolation(
                    "Snapshot-stale HOLD requires prior authorization and invalid snapshot."
                )
        elif source_decision.authorization_effect is AuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL:
            if record.user_authorized:
                raise ContractViolation("A held ungranted request cannot be user_authorized.")
            if record.hold_reason_code is not source_decision.hold_reason_code:
                raise ContractViolation("HOLD routing reason must match USER_DECISION_RECORD.")
        else:
            raise ContractViolation("A non-dispatchable decision cannot be routed as HOLD.")

    elif record.routing_result is RoutingResult.NON_DISPATCHABLE_BOUNDARY_VIOLATION:
        if source_decision.authorization_effect is not AuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE:
            raise ContractViolation(
                "NON_DISPATCHABLE routing requires NOT_GRANTED_NON_DISPATCHABLE source decision."
            )
        if record.non_dispatchable_reason_code is None or record.hold_reason_code is not None:
            raise ContractViolation(
                "Non-dispatchable routing requires non_dispatchable_reason_code only."
            )
        if record.non_dispatchable_reason_code is not source_decision.non_dispatchable_reason_code:
            raise ContractViolation("Non-dispatchable routing reason must match source decision.")
        if record.user_authorized or record.snapshot_valid or record.within_safety_boundary:
            raise ContractViolation(
                "Non-dispatchable action must remain unauthorized, unvalidated, and outside boundary."
            )


# ---------------------------------------------------------------------------
# Snapshot and read-only scope handling
# ---------------------------------------------------------------------------


def _safe_path(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative_path).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ContractViolation(f"Path escaped authorized root: {relative_path!r}")
    return candidate


def _iter_scope_files(root: Path, scope: Scope) -> Iterator[tuple[str, Path]]:
    """Yield authorized regular files only; symlink targets are not scanned."""
    root_resolved = root.resolve()
    seen: set[str] = set()

    for relative in scope.paths:
        target = _safe_path(root_resolved, relative)
        candidates: Iterable[Path]
        if target.is_file() and not target.is_symlink():
            candidates = (target,)
        elif target.is_dir() and not target.is_symlink():
            walked: list[Path] = []
            for directory, dirnames, filenames in os.walk(target, followlinks=False):
                # Do not descend through symlinked directories.
                base = Path(directory)
                dirnames[:] = [
                    name for name in dirnames if not (base / name).is_symlink()
                ]
                walked.extend(base / name for name in filenames)
            candidates = sorted(walked)
        else:
            candidates = ()

        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved != root_resolved and root_resolved not in resolved.parents:
                raise ContractViolation("Scoped scan attempted to leave authorized root.")
            rel = resolved.relative_to(root_resolved).as_posix()
            if rel not in seen:
                seen.add(rel)
                yield rel, resolved


def compute_scope_snapshot(root: Path, scope: Scope) -> str:
    digest = sha256()
    for relative, path in sorted(_iter_scope_files(root, scope)):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _read_text(path: Path, *, max_bytes: int = 1_000_000) -> str:
    if path.stat().st_size > max_bytes:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Phase 2: Static finding reports
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingReport:
    finding_id: str
    pattern_id: str
    agent_id: AgentId
    finding_type: str
    target_file: str
    line_number: int
    severity_candidate: SeverityCandidate
    evidence_type: EvidenceType
    summary: str
    evidence_summary: str
    recommended_next_action: str = "PRESENT_TO_USER_HITL"
    sensitive_value_disclosed: bool = False
    change_performed: bool = False
    exploit_executed: bool = False

    @property
    def fingerprint(self) -> str:
        return _stable_id(
            "FPR",
            self.pattern_id,
            self.target_file,
            str(self.line_number),
            self.finding_type,
        )


FINDING_CONTRACT_ALLOWLIST: Mapping[str, tuple[AgentId, frozenset[str]]] = {
    "SEC-PAT-001": (
        AgentId.SECRET_PII_FINDING_AGENT,
        frozenset({"HARDCODED_SECRET_CANDIDATE", "TOKEN_LIKE_UNQUOTED_TEXT_CANDIDATE"}),
    ),
    "SEC-PAT-002": (
        AgentId.CODE_SECURITY_FINDING_AGENT,
        frozenset({"UNSAFE_SUBPROCESS_CANDIDATE"}),
    ),
    "SEC-PAT-003": (
        AgentId.CODE_SECURITY_FINDING_AGENT,
        frozenset({"SQL_INJECTION_CANDIDATE"}),
    ),
    "SEC-PAT-004": (
        AgentId.CODE_SECURITY_FINDING_AGENT,
        frozenset({"PATH_TRAVERSAL_CANDIDATE"}),
    ),
    "SEC-PAT-005": (
        AgentId.CICD_PERMISSION_FINDING_AGENT,
        frozenset({"AUTO_MERGE_PATH_DETECTED", "EXCESSIVE_WORKFLOW_PERMISSION_CANDIDATE"}),
    ),
}


def _finding_has_safety_boundary_violation(report: FindingReport) -> bool:
    return (
        report.change_performed
        or report.exploit_executed
        or (
            report.agent_id is AgentId.SECRET_PII_FINDING_AGENT
            and report.sensitive_value_disclosed
        )
    )


def validate_finding_report(
    report: FindingReport,
    *,
    audit_scope: Scope | None = None,
) -> None:
    """Validate a static FindingReport without converting it into a decision."""
    if not isinstance(report, FindingReport):
        raise ContractViolation("Finding report must be a FindingReport.")
    _require_text(report.finding_id, "finding_id")
    _require_text(report.pattern_id, "pattern_id")
    _require_enum_instance(report.agent_id, AgentId, "finding_report.agent_id")
    _require_text(report.finding_type, "finding_type")
    _require_text(report.target_file, "target_file")
    if not isinstance(report.line_number, int) or isinstance(report.line_number, bool) or report.line_number < 1:
        raise ContractViolation("finding_report.line_number must be an integer >= 1.")
    _require_enum_instance(report.severity_candidate, SeverityCandidate, "finding_report.severity_candidate")
    _require_enum_instance(report.evidence_type, EvidenceType, "finding_report.evidence_type")
    _require_text(report.summary, "finding_report.summary")
    _require_text(report.evidence_summary, "finding_report.evidence_summary")
    if report.recommended_next_action != "PRESENT_TO_USER_HITL":
        raise ContractViolation("Finding report may only recommend PRESENT_TO_USER_HITL in this phase.")
    _require_bool(report.sensitive_value_disclosed, "finding_report.sensitive_value_disclosed")
    _require_bool(report.change_performed, "finding_report.change_performed")
    _require_bool(report.exploit_executed, "finding_report.exploit_executed")

    if _finding_has_safety_boundary_violation(report):
        raise ContractViolation("Finding Agent must never modify files, execute exploits, or disclose raw secrets.")

    contract = FINDING_CONTRACT_ALLOWLIST.get(report.pattern_id)
    if contract is None:
        raise ContractViolation(f"Unsupported pattern_id: {report.pattern_id!r}.")
    expected_agent, allowed_types = contract
    if report.agent_id is not expected_agent:
        raise ContractViolation(f"{report.pattern_id} must be reported by {expected_agent.value}.")
    if report.finding_type not in allowed_types:
        raise ContractViolation(f"{report.finding_type!r} is not permitted for {report.pattern_id}.")

    target_scope = Scope((report.target_file,))
    if audit_scope is not None and not audit_scope.covers(target_scope):
        raise ContractViolation("Finding target_file is outside the audited scope.")


def _build_finding(
    *,
    pattern_id: str,
    agent_id: AgentId,
    finding_type: str,
    target_file: str,
    line_number: int,
    severity: SeverityCandidate,
    evidence_type: EvidenceType,
    summary: str,
    evidence_summary: str,
) -> FindingReport:
    finding = FindingReport(
        finding_id=_stable_id(
            "FND", pattern_id, agent_id.value, target_file, str(line_number), finding_type
        ),
        pattern_id=pattern_id,
        agent_id=agent_id,
        finding_type=finding_type,
        target_file=target_file,
        line_number=line_number,
        severity_candidate=severity,
        evidence_type=evidence_type,
        summary=summary,
        evidence_summary=evidence_summary,
    )
    validate_finding_report(finding)
    return finding


class StaticFindingAgent:
    agent_id: AgentId

    def scan(self, root: Path, scope: Scope) -> list[FindingReport]:
        raise NotImplementedError


class SecretPiiFindingAgent(StaticFindingAgent):
    agent_id = AgentId.SECRET_PII_FINDING_AGENT

    _secret_pattern = re.compile(
        r"""(?ix)
        \b(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\b
        \s*[:=]\s*
        ["']([^"'\n]{8,})["']
        """
    )
    _unquoted_secret_pattern = re.compile(
        r"""(?ix)
        \b(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\b
        \s*[:=]\s*
        ([a-z][a-z0-9_-]{7,})
        (?=\s*(?:[#;,].*)?$)
        """
    )
    _token_like_value = re.compile(
        r"""(?ix)^(?:
            sk[-_](?:live|test)[-_]?[a-z0-9_-]* |
            gh[pousr]_[a-z0-9_-]+ |
            xox[baprs]-[a-z0-9_-]+ |
            akia[a-z0-9]{8,}
        )$"""
    )
    _suffixes = {".py", ".env", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".txt"}
    _placeholders = ("example", "dummy", "changeme", "replace_me", "your_", "***", "${")

    @staticmethod
    def _mask(value: str) -> str:
        if len(value) <= 4:
            return "****"
        return f"{value[:2]}****{value[-2:]}"

    def scan(self, root: Path, scope: Scope) -> list[FindingReport]:
        findings: list[FindingReport] = []
        for relative, path in _iter_scope_files(root, scope):
            if path.suffix.lower() not in self._suffixes and path.name != ".env":
                continue
            text = _read_text(path)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for match in self._secret_pattern.finditer(line):
                    raw_value = match.group(2)
                    if any(marker in raw_value.lower() for marker in self._placeholders):
                        continue
                    label = match.group(1)
                    masked = self._mask(raw_value)
                    findings.append(
                        _build_finding(
                            pattern_id="SEC-PAT-001",
                            agent_id=self.agent_id,
                            finding_type="HARDCODED_SECRET_CANDIDATE",
                            target_file=relative,
                            line_number=line_no,
                            severity=SeverityCandidate.HIGH,
                            evidence_type=EvidenceType.DIRECT_STATIC_OBSERVATION,
                            summary="固定値として設定された秘密情報候補を検出。",
                            evidence_summary=f"label={label}; value={masked} (masked)",
                        )
                    )
                for match in self._unquoted_secret_pattern.finditer(line):
                    raw_value = match.group(2)
                    if (
                        any(marker in raw_value.lower() for marker in self._placeholders)
                        or not self._token_like_value.match(raw_value)
                    ):
                        continue
                    label = match.group(1)
                    masked = self._mask(raw_value)
                    python_source = path.suffix.lower() == ".py"
                    findings.append(
                        _build_finding(
                            pattern_id="SEC-PAT-001",
                            agent_id=self.agent_id,
                            finding_type=(
                                "TOKEN_LIKE_UNQUOTED_TEXT_CANDIDATE"
                                if python_source
                                else "HARDCODED_SECRET_CANDIDATE"
                            ),
                            target_file=relative,
                            line_number=line_no,
                            severity=(
                                SeverityCandidate.MEDIUM
                                if python_source
                                else SeverityCandidate.HIGH
                            ),
                            evidence_type=(
                                EvidenceType.STATIC_PATTERN_CANDIDATE
                                if python_source
                                else EvidenceType.DIRECT_STATIC_OBSERVATION
                            ),
                            summary=(
                                "Pythonソース内に未引用のtoken風表記候補を検出。"
                                if python_source
                                else "設定形式に未引用の秘密情報候補を検出。"
                            ),
                            evidence_summary=f"label={label}; value={masked} (masked; unquoted)",
                        )
                    )
        return findings


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        parts: list[str] = [function.attr]
        base = function.value
        while isinstance(base, ast.Attribute):
            parts.append(base.attr)
            base = base.value
        if isinstance(base, ast.Name):
            parts.append(base.id)
        return ".".join(reversed(parts))
    return ""


def _contains_name(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(child, ast.Name) and child.id in names for child in ast.walk(node))


def _is_dynamic_expression(node: ast.AST) -> bool:
    return not isinstance(node, ast.Constant)


def _is_dynamic_sql_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr in {"format", "join"}
    return False


def _assigned_names(target: ast.AST) -> set[str]:
    """Collect simple local names from an assignment target."""
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_assigned_names(element))
        return names
    return set()


def _pathlib_receiver_source(node: ast.Call) -> ast.AST | None:
    """Return Path(...) source expression for pathlib file-operation calls."""
    if not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr not in {"open", "read_text", "read_bytes", "write_text", "write_bytes"}:
        return None
    receiver = node.func.value
    if not isinstance(receiver, ast.Call) or not receiver.args:
        return None
    constructor_name = _call_name(receiver)
    if constructor_name not in {"Path", "pathlib.Path"}:
        return None
    return receiver.args[0]


class _CodePatternVisitor(ast.NodeVisitor):
    def __init__(self, target_file: str) -> None:
        self.target_file = target_file
        self.function_parameters: list[set[str]] = []
        self.tainted_local_scopes: list[set[str]] = [set()]
        self.findings: list[FindingReport] = []

    @property
    def active_external_names(self) -> set[str]:
        names: set[str] = set()
        for params in self.function_parameters:
            names.update(params)
        names.update({"request", "args", "argv", "filename", "filepath", "path", "user_path"})
        names.update(self.tainted_local_scopes[-1])
        return names

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        params = {arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if node.args.kwarg:
            params.add(node.args.kwarg.arg)
        self.function_parameters.append(params)
        self.tainted_local_scopes.append(set())
        self.generic_visit(node)
        self.tainted_local_scopes.pop()
        self.function_parameters.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> None:
        # Constrained, same-function local propagation only. This reports
        # candidates and is not a full taint-analysis engine.
        if _is_dynamic_expression(node.value) and _contains_name(node.value, self.active_external_names):
            for target in node.targets:
                self.tainted_local_scopes[-1].update(_assigned_names(target))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if (
            node.value is not None
            and _is_dynamic_expression(node.value)
            and _contains_name(node.value, self.active_external_names)
        ):
            self.tainted_local_scopes[-1].update(_assigned_names(node.target))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        first_arg = node.args[0] if node.args else None
        external_names = self.active_external_names

        # SEC-PAT-002: command execution candidates.
        if first_arg is not None and name == "os.system":
            if _is_dynamic_expression(first_arg) and _contains_name(first_arg, external_names):
                self.findings.append(
                    _build_finding(
                        pattern_id="SEC-PAT-002",
                        agent_id=AgentId.CODE_SECURITY_FINDING_AGENT,
                        finding_type="UNSAFE_SUBPROCESS_CANDIDATE",
                        target_file=self.target_file,
                        line_number=node.lineno,
                        severity=SeverityCandidate.HIGH,
                        evidence_type=EvidenceType.STATIC_PATTERN_CANDIDATE,
                        summary="外部入力候補がOSコマンド実行経路へ渡る構造を検出。",
                        evidence_summary="dynamic argument passed to os.system()",
                    )
                )

        if first_arg is not None and name in {
            "subprocess.run",
            "subprocess.call",
            "subprocess.Popen",
            "subprocess.check_call",
            "subprocess.check_output",
        }:
            shell_true = any(
                kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            )
            if shell_true and _is_dynamic_expression(first_arg) and _contains_name(first_arg, external_names):
                self.findings.append(
                    _build_finding(
                        pattern_id="SEC-PAT-002",
                        agent_id=AgentId.CODE_SECURITY_FINDING_AGENT,
                        finding_type="UNSAFE_SUBPROCESS_CANDIDATE",
                        target_file=self.target_file,
                        line_number=node.lineno,
                        severity=SeverityCandidate.HIGH,
                        evidence_type=EvidenceType.STATIC_PATTERN_CANDIDATE,
                        summary="外部入力候補とshell=Trueの組合せを検出。",
                        evidence_summary=f"dynamic argument passed to {name}(..., shell=True)",
                    )
                )

        # SEC-PAT-003: SQL string construction candidates.
        if first_arg is not None and name.endswith((".execute", ".executemany")):
            if _is_dynamic_sql_expression(first_arg):
                self.findings.append(
                    _build_finding(
                        pattern_id="SEC-PAT-003",
                        agent_id=AgentId.CODE_SECURITY_FINDING_AGENT,
                        finding_type="SQL_INJECTION_CANDIDATE",
                        target_file=self.target_file,
                        line_number=node.lineno,
                        severity=SeverityCandidate.HIGH,
                        evidence_type=EvidenceType.STATIC_PATTERN_CANDIDATE,
                        summary="SQL実行引数に動的な文字列構築候補を検出。",
                        evidence_summary=f"dynamic SQL passed to {name}()",
                    )
                )

        # SEC-PAT-004: path traversal candidates.
        direct_path_arg = first_arg if name == "open" else None
        pathlib_path_arg = _pathlib_receiver_source(node)
        path_arg = direct_path_arg if direct_path_arg is not None else pathlib_path_arg
        if path_arg is not None:
            if _is_dynamic_expression(path_arg) and _contains_name(path_arg, external_names):
                sink_name = name if direct_path_arg is not None else f"Path(...).{node.func.attr}"
                self.findings.append(
                    _build_finding(
                        pattern_id="SEC-PAT-004",
                        agent_id=AgentId.CODE_SECURITY_FINDING_AGENT,
                        finding_type="PATH_TRAVERSAL_CANDIDATE",
                        target_file=self.target_file,
                        line_number=node.lineno,
                        severity=SeverityCandidate.MEDIUM,
                        evidence_type=EvidenceType.STATIC_PATTERN_CANDIDATE,
                        summary="入力由来のパス候補がファイル操作へ渡る構造を検出。",
                        evidence_summary=f"dynamic path passed to {sink_name}()",
                    )
                )

        self.generic_visit(node)


class CodeSecurityFindingAgent(StaticFindingAgent):
    agent_id = AgentId.CODE_SECURITY_FINDING_AGENT

    def scan(self, root: Path, scope: Scope) -> list[FindingReport]:
        findings: list[FindingReport] = []
        for relative, path in _iter_scope_files(root, scope):
            if path.suffix.lower() != ".py":
                continue
            text = _read_text(path)
            if not text:
                continue
            try:
                tree = ast.parse(text, filename=relative)
            except SyntaxError:
                continue
            visitor = _CodePatternVisitor(relative)
            visitor.visit(tree)
            findings.extend(visitor.findings)
        return findings


class CicdPermissionFindingAgent(StaticFindingAgent):
    agent_id = AgentId.CICD_PERMISSION_FINDING_AGENT

    _auto_merge_patterns = (
        re.compile(r"\bgh\s+pr\s+merge\b[^\n]*\s--auto\b", re.IGNORECASE),
        re.compile(r"\benablePullRequestAutoMerge\b", re.IGNORECASE),
        re.compile(r"\bauto[-_ ]?merge\b", re.IGNORECASE),
    )
    _write_all = re.compile(r"^\s*permissions\s*:\s*write-all\s*$", re.IGNORECASE)
    _write_permission = re.compile(
        r"^\s*(contents|actions|pull-requests|packages|deployments)\s*:\s*write\s*$",
        re.IGNORECASE,
    )

    def scan(self, root: Path, scope: Scope) -> list[FindingReport]:
        findings: list[FindingReport] = []
        for relative, path in _iter_scope_files(root, scope):
            if path.suffix.lower() not in {".yml", ".yaml"}:
                continue
            lines = _read_text(path).splitlines()
            for line_no, line in enumerate(lines, start=1):
                if any(pattern.search(line) for pattern in self._auto_merge_patterns):
                    findings.append(
                        _build_finding(
                            pattern_id="SEC-PAT-005",
                            agent_id=self.agent_id,
                            finding_type="AUTO_MERGE_PATH_DETECTED",
                            target_file=relative,
                            line_number=line_no,
                            severity=SeverityCandidate.HIGH,
                            evidence_type=EvidenceType.DIRECT_STATIC_OBSERVATION,
                            summary="CI/CD設定に自動マージ経路の候補を検出。",
                            evidence_summary="workflow line contains an auto-merge indicator",
                        )
                    )
                if self._write_all.search(line) or self._write_permission.search(line):
                    findings.append(
                        _build_finding(
                            pattern_id="SEC-PAT-005",
                            agent_id=self.agent_id,
                            finding_type="EXCESSIVE_WORKFLOW_PERMISSION_CANDIDATE",
                            target_file=relative,
                            line_number=line_no,
                            severity=SeverityCandidate.MEDIUM,
                            evidence_type=EvidenceType.STATIC_PATTERN_CANDIDATE,
                            summary="CI/CD設定に書き込み権限の確認候補を検出。",
                            evidence_summary="workflow line grants write-capable permission",
                        )
                    )
        return findings


AGENT_REGISTRY: Mapping[AgentId, type[StaticFindingAgent]] = {
    AgentId.CODE_SECURITY_FINDING_AGENT: CodeSecurityFindingAgent,
    AgentId.SECRET_PII_FINDING_AGENT: SecretPiiFindingAgent,
    AgentId.CICD_PERMISSION_FINDING_AGENT: CicdPermissionFindingAgent,
}


def run_authorized_static_audit(
    root: Path,
    *,
    decision: UserDecisionRecord,
    dispatch: DispatchRecord,
) -> list[FindingReport]:
    """
    Execute only an already dispatched static read-only audit.

    A snapshot is checked immediately before and after reading. This simulation
    does not attempt to provide filesystem transaction isolation.
    """
    validate_dispatch_record(dispatch, source_decision=decision)
    if dispatch.routing_result is not RoutingResult.DISPATCH_USER_AUTHORIZED_TASK:
        raise ContractViolation("Static audit requires a dispatched authorized task.")
    request = dispatch.requested_dispatch
    if request.action is not Action.READ_ONLY_STATIC_AUDIT:
        raise ContractViolation("Only read-only static audit can execute in this phase.")
    if request.target_agent not in AGENT_REGISTRY:
        raise ContractViolation("Selected Agent has no active scanner in this phase.")

    before = compute_scope_snapshot(root, request.target_scope)
    if before != request.target_snapshot_id:
        raise ContractViolation("Snapshot changed before the authorized audit began.")

    findings = AGENT_REGISTRY[request.target_agent]().scan(root, request.target_scope)

    after = compute_scope_snapshot(root, request.target_scope)
    if after != before:
        raise ContractViolation("Snapshot changed during the read-only audit.")

    for finding in findings:
        validate_finding_report(finding)
    return findings


# ---------------------------------------------------------------------------
# Mediator and Maestro: reporting only, no remediation or execution decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimaryMediationInput:
    """
    Complete input envelope for formal primary mediation.

    A no-finding result is permitted only when every expected Agent completed
    the same authorized scope and snapshot audit round.
    """

    mediation_input_id: str
    source_user_decision_id: str
    source_dispatch_ids: tuple[str, ...]
    audit_round_id: str
    base_snapshot_id: str
    audited_scope: Scope
    expected_agents: tuple[AgentId, ...]
    completed_agents: tuple[AgentId, ...]
    failed_agents: tuple[AgentId, ...] = ()
    finding_reports: tuple[FindingReport, ...] = ()
    snapshot_consistent: bool = True
    scope_consistent: bool = True
    boundary_event_detected: bool = False

    @property
    def missing_agents(self) -> tuple[AgentId, ...]:
        completed_or_failed = set(self.completed_agents) | set(self.failed_agents)
        return tuple(agent for agent in self.expected_agents if agent not in completed_or_failed)

    @property
    def all_expected_agents_completed(self) -> bool:
        return (
            not self.failed_agents
            and not self.missing_agents
            and set(self.completed_agents) == set(self.expected_agents)
        )


def validate_primary_mediation_input(record: PrimaryMediationInput) -> None:
    if not isinstance(record, PrimaryMediationInput):
        raise ContractViolation("Formal primary mediation requires PRIMARY_MEDIATION_INPUT.")
    _require_text(record.mediation_input_id, "mediation_input_id")
    _require_text(record.source_user_decision_id, "source_user_decision_id")
    if not isinstance(record.source_dispatch_ids, tuple) or not record.source_dispatch_ids:
        raise ContractViolation("source_dispatch_ids must be a non-empty tuple.")
    for index, dispatch_id in enumerate(record.source_dispatch_ids):
        _require_text(dispatch_id, f"source_dispatch_ids[{index}]")
    if len(set(record.source_dispatch_ids)) != len(record.source_dispatch_ids):
        raise ContractViolation("source_dispatch_ids must not contain duplicates.")
    _require_text(record.audit_round_id, "audit_round_id")
    _require_text(record.base_snapshot_id, "base_snapshot_id")
    if not isinstance(record.audited_scope, Scope):
        raise ContractViolation("audited_scope must be a Scope.")

    if not isinstance(record.expected_agents, tuple) or not record.expected_agents:
        raise ContractViolation("expected_agents must be a non-empty tuple.")
    if not isinstance(record.completed_agents, tuple) or not isinstance(record.failed_agents, tuple):
        raise ContractViolation("completed_agents and failed_agents must be tuples.")
    for field_name, agents in (
        ("expected_agents", record.expected_agents),
        ("completed_agents", record.completed_agents),
        ("failed_agents", record.failed_agents),
    ):
        for index, agent in enumerate(agents):
            _require_enum_instance(agent, AgentId, f"{field_name}[{index}]")
        if len(set(agents)) != len(agents):
            raise ContractViolation(f"{field_name} must not contain duplicates.")

    expected = set(record.expected_agents)
    if not expected.issubset(STATIC_AUDIT_AGENTS):
        raise ContractViolation("Primary mediation may expect active static Finding Agents only.")
    if not set(record.completed_agents).issubset(expected):
        raise ContractViolation("completed_agents must be a subset of expected_agents.")
    if not set(record.failed_agents).issubset(expected):
        raise ContractViolation("failed_agents must be a subset of expected_agents.")
    if set(record.completed_agents) & set(record.failed_agents):
        raise ContractViolation("An Agent cannot be both completed and failed.")

    if not isinstance(record.finding_reports, tuple):
        raise ContractViolation("finding_reports must be a tuple.")
    for finding in record.finding_reports:
        if not isinstance(finding, FindingReport):
            raise ContractViolation("finding_reports may contain FindingReport records only.")
    _require_bool(record.snapshot_consistent, "snapshot_consistent")
    _require_bool(record.scope_consistent, "scope_consistent")
    _require_bool(record.boundary_event_detected, "boundary_event_detected")


@dataclass(frozen=True)
class PrimaryMediationResult:
    input_id: str
    result_id: str
    decision: MediationDecision
    reason_code: PrimaryMediationReasonCode
    findings: tuple[FindingReport, ...]
    duplicate_count: int
    expected_agents: tuple[AgentId, ...]
    completed_agents: tuple[AgentId, ...]
    missing_agents: tuple[AgentId, ...]
    failed_agents: tuple[AgentId, ...]
    requires_user_hitl: bool
    note: str


def _primary_result(
    input_record: PrimaryMediationInput,
    *,
    decision: MediationDecision,
    reason_code: PrimaryMediationReasonCode,
    findings: tuple[FindingReport, ...],
    duplicate_count: int,
    requires_user_hitl: bool,
    note: str,
) -> PrimaryMediationResult:
    result = PrimaryMediationResult(
        input_id=input_record.mediation_input_id,
        result_id=_stable_id(
            "MED",
            input_record.mediation_input_id,
            decision.value,
            reason_code.value,
            *(finding.finding_id for finding in findings),
        ),
        decision=decision,
        reason_code=reason_code,
        findings=findings,
        duplicate_count=duplicate_count,
        expected_agents=input_record.expected_agents,
        completed_agents=input_record.completed_agents,
        missing_agents=input_record.missing_agents,
        failed_agents=input_record.failed_agents,
        requires_user_hitl=requires_user_hitl,
        note=note,
    )
    validate_primary_mediation_result(result, source_input=input_record)
    return result


def validate_primary_mediation_result(
    result: PrimaryMediationResult,
    *,
    source_input: PrimaryMediationInput,
) -> None:
    if not isinstance(result, PrimaryMediationResult):
        raise ContractViolation("Result must be a PrimaryMediationResult.")
    validate_primary_mediation_input(source_input)
    _require_text(result.input_id, "primary_result.input_id")
    _require_text(result.result_id, "primary_result.result_id")
    _require_enum_instance(result.decision, MediationDecision, "primary_result.decision")
    _require_enum_instance(result.reason_code, PrimaryMediationReasonCode, "primary_result.reason_code")
    _require_bool(result.requires_user_hitl, "primary_result.requires_user_hitl")
    if result.input_id != source_input.mediation_input_id:
        raise ContractViolation("Primary mediation result must reference its input.")
    if result.expected_agents != source_input.expected_agents:
        raise ContractViolation("Result changed expected_agents.")
    if result.completed_agents != source_input.completed_agents:
        raise ContractViolation("Result changed completed_agents.")
    if result.missing_agents != source_input.missing_agents:
        raise ContractViolation("Result changed missing_agents.")
    if result.failed_agents != source_input.failed_agents:
        raise ContractViolation("Result changed failed_agents.")
    if result.duplicate_count < 0:
        raise ContractViolation("duplicate_count must not be negative.")

    if result.decision is MediationDecision.NO_FINDING_DETECTED_WITHIN_SCOPE:
        if result.reason_code is not PrimaryMediationReasonCode.COMPLETED_NO_FINDING:
            raise ContractViolation("NO_FINDING must use COMPLETED_NO_FINDING.")
        if result.findings or result.requires_user_hitl:
            raise ContractViolation("NO_FINDING must contain no findings and require no HITL.")
        if not source_input.all_expected_agents_completed:
            raise ContractViolation("NO_FINDING requires all expected Agents to complete.")
        if source_input.finding_reports:
            raise ContractViolation("NO_FINDING requires an empty finding report set.")
        if not source_input.snapshot_consistent or not source_input.scope_consistent:
            raise ContractViolation("NO_FINDING requires consistent snapshot and scope.")

    elif result.decision is MediationDecision.AUDIT_RESULT_INCOMPLETE:
        if not result.requires_user_hitl:
            raise ContractViolation("Incomplete audit requires User HITL.")
        if (
            source_input.all_expected_agents_completed
            and source_input.snapshot_consistent
            and source_input.scope_consistent
        ):
            raise ContractViolation("AUDIT_RESULT_INCOMPLETE requires an incomplete context.")

    elif result.decision in {
        MediationDecision.FINDING_PRESENT,
        MediationDecision.DUPLICATE_FINDING_MERGED,
        MediationDecision.REPORT_LOGIC_CONFLICT,
        MediationDecision.AGENT_OUTPUT_CONFLICT,
        MediationDecision.SAFETY_BOUNDARY_CONFLICT,
    }:
        if not result.requires_user_hitl:
            raise ContractViolation(f"{result.decision.value} requires User HITL.")


def mediate_primary_findings(input_record: PrimaryMediationInput) -> PrimaryMediationResult:
    """
    Perform formal primary mediation over completed/static Agent report inputs.

    Mediator consumes reports only. It does not scan source, change files,
    produce remediation, or dispatch any next phase.
    """
    validate_primary_mediation_input(input_record)
    reports = input_record.finding_reports

    if input_record.boundary_event_detected or any(
        _finding_has_safety_boundary_violation(report) for report in reports
    ):
        return _primary_result(
            input_record,
            decision=MediationDecision.SAFETY_BOUNDARY_CONFLICT,
            reason_code=PrimaryMediationReasonCode.AGENT_REPORT_BOUNDARY_VIOLATION,
            findings=reports,
            duplicate_count=0,
            requires_user_hitl=True,
            note="Agent output or audit context violated a fixed reporting boundary.",
        )

    if input_record.failed_agents:
        return _primary_result(
            input_record,
            decision=MediationDecision.AUDIT_RESULT_INCOMPLETE,
            reason_code=PrimaryMediationReasonCode.AGENT_EXECUTION_FAILED,
            findings=reports,
            duplicate_count=0,
            requires_user_hitl=True,
            note="At least one expected Agent failed; no no-finding conclusion is permitted.",
        )

    if input_record.missing_agents:
        return _primary_result(
            input_record,
            decision=MediationDecision.AUDIT_RESULT_INCOMPLETE,
            reason_code=PrimaryMediationReasonCode.EXPECTED_AGENT_RESULT_MISSING,
            findings=reports,
            duplicate_count=0,
            requires_user_hitl=True,
            note="At least one expected Agent result is missing.",
        )

    if not input_record.snapshot_consistent:
        return _primary_result(
            input_record,
            decision=MediationDecision.AUDIT_RESULT_INCOMPLETE,
            reason_code=PrimaryMediationReasonCode.SNAPSHOT_CONTEXT_MISMATCH,
            findings=reports,
            duplicate_count=0,
            requires_user_hitl=True,
            note="Agent outputs do not share the authorized base snapshot.",
        )

    if not input_record.scope_consistent:
        return _primary_result(
            input_record,
            decision=MediationDecision.AUDIT_RESULT_INCOMPLETE,
            reason_code=PrimaryMediationReasonCode.SCOPE_CONTEXT_MISMATCH,
            findings=reports,
            duplicate_count=0,
            requires_user_hitl=True,
            note="Agent outputs do not share the authorized audit scope.",
        )

    for report in reports:
        try:
            validate_finding_report(report, audit_scope=input_record.audited_scope)
        except ContractViolation as exc:
            return _primary_result(
                input_record,
                decision=MediationDecision.REPORT_LOGIC_CONFLICT,
                reason_code=PrimaryMediationReasonCode.INVALID_FINDING_REPORT,
                findings=reports,
                duplicate_count=0,
                requires_user_hitl=True,
                note=f"Finding report contract violation: {exc}",
            )
        if (
            report.agent_id not in input_record.expected_agents
            or report.agent_id not in input_record.completed_agents
        ):
            return _primary_result(
                input_record,
                decision=MediationDecision.REPORT_LOGIC_CONFLICT,
                reason_code=PrimaryMediationReasonCode.INVALID_FINDING_REPORT,
                findings=reports,
                duplicate_count=0,
                requires_user_hitl=True,
                note="Finding was submitted by an Agent outside the completed authorized set.",
            )

    unique: dict[str, FindingReport] = {}
    duplicate_count = 0
    for report in reports:
        if report.fingerprint in unique:
            duplicate_count += 1
        else:
            unique[report.fingerprint] = report

    consolidated = tuple(
        sorted(unique.values(), key=lambda report: (report.target_file, report.line_number, report.pattern_id))
    )
    if not consolidated:
        return _primary_result(
            input_record,
            decision=MediationDecision.NO_FINDING_DETECTED_WITHIN_SCOPE,
            reason_code=PrimaryMediationReasonCode.COMPLETED_NO_FINDING,
            findings=(),
            duplicate_count=0,
            requires_user_hitl=False,
            note=(
                "All expected Agents completed the configured scope and snapshot "
                "without reporting configured candidates; this is not proof of safety."
            ),
        )

    if duplicate_count:
        return _primary_result(
            input_record,
            decision=MediationDecision.DUPLICATE_FINDING_MERGED,
            reason_code=PrimaryMediationReasonCode.DUPLICATE_FINDING_CONSOLIDATED,
            findings=consolidated,
            duplicate_count=duplicate_count,
            requires_user_hitl=True,
            note="Duplicate candidate findings were consolidated for User review.",
        )

    return _primary_result(
        input_record,
        decision=MediationDecision.FINDING_PRESENT,
        reason_code=PrimaryMediationReasonCode.CANDIDATE_FINDING_PRESENT,
        findings=consolidated,
        duplicate_count=0,
        requires_user_hitl=True,
        note="Candidate findings require User review; no change has been performed.",
    )


@dataclass(frozen=True)
class MaestroPresentation:
    mediation_result_id: str
    present_to_user: bool
    requires_user_decision: bool
    summary: str


def maestro_present_mediation(result: PrimaryMediationResult) -> MaestroPresentation:
    """
    Present Mediator output only. Maestro does not start another phase.
    """
    if result.decision is MediationDecision.NO_FINDING_DETECTED_WITHIN_SCOPE:
        summary = result.note
    else:
        summary = (
            f"{result.decision.value}/{result.reason_code.value}: "
            f"{len(result.findings)} candidate finding(s). "
            "User HITL is required before any additional phase."
        )
    return MaestroPresentation(
        mediation_result_id=result.result_id,
        present_to_user=True,
        requires_user_decision=result.requires_user_hitl,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Phase 3: Finding-scoped remediation authorization only
# ---------------------------------------------------------------------------


class RemediationAuthorizationEffect(str, Enum):
    """Effect of a User request to create a non-executing remediation draft."""

    GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY = "GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY"
    HOLD_REQUIRES_ADDITIONAL_HITL = "HOLD_REQUIRES_ADDITIONAL_HITL"
    NOT_GRANTED_NON_DISPATCHABLE = "NOT_GRANTED_NON_DISPATCHABLE"


class RemediationHoldReasonCode(str, Enum):
    USER_AUTHORIZATION_MISSING = "USER_AUTHORIZATION_MISSING"
    PRIMARY_MEDIATION_NOT_ELIGIBLE = "PRIMARY_MEDIATION_NOT_ELIGIBLE"
    SOURCE_AUDIT_SNAPSHOT_MISMATCH = "SOURCE_AUDIT_SNAPSHOT_MISMATCH"
    REMEDIATION_SNAPSHOT_STALE = "REMEDIATION_SNAPSHOT_STALE"
    FINDING_NOT_PRESENT_IN_SOURCE_RESULT = "FINDING_NOT_PRESENT_IN_SOURCE_RESULT"
    FINDING_SOURCE_OUTSIDE_INSPECTION_SCOPE = "FINDING_SOURCE_OUTSIDE_INSPECTION_SCOPE"
    DRAFT_SCOPE_OUTSIDE_INSPECTION_SCOPE = "DRAFT_SCOPE_OUTSIDE_INSPECTION_SCOPE"
    ISOLATED_VERIFICATION_REQUIRES_SEPARATE_HITL = (
        "ISOLATED_VERIFICATION_REQUIRES_SEPARATE_HITL"
    )


class RemediationNonDispatchableReasonCode(str, Enum):
    MACHINE_APPLY_PROHIBITED = "MACHINE_APPLY_PROHIBITED"
    AUTO_APPLY_PROHIBITED = "AUTO_APPLY_PROHIBITED"
    AUTO_MERGE_PROHIBITED = "AUTO_MERGE_PROHIBITED"


@dataclass(frozen=True)
class RemediationAuthorizationRequest:
    """
    User request envelope for permitting DRAFT_REMEDIATION creation only.

    `inspection_scope` may be broader than `draft_change_scope` so side-effect
    review can read relevant context without authorizing changes to that
    broader context.  No field in this request grants file modification.
    """

    request_id: str
    source_primary_mediation_result_id: str
    source_audit_snapshot_id: str
    remediation_base_snapshot_id: str
    requested_finding_ids: tuple[str, ...]
    inspection_scope: Scope
    draft_change_scope: Scope
    isolated_verification_requested: bool = False
    machine_apply_requested: bool = False
    auto_apply_requested: bool = False
    auto_merge_requested: bool = False


@dataclass(frozen=True)
class RemediationAuthorization:
    """
    USER_HITL record of whether remediation-draft creation is authorized.

    Even when granted, this record permits only creation of a future static
    DRAFT_REMEDIATION.  It never permits execution, application, merge, or
    isolated verification.
    """

    authorization_id: str
    source_request_id: str
    source_user_decision_id: str
    source_primary_mediation_result_id: str
    source_audit_snapshot_id: str
    base_snapshot_id: str
    authorization_effect: RemediationAuthorizationEffect
    requested_finding_ids: tuple[str, ...]
    requested_inspection_scope: Scope
    requested_draft_change_scope: Scope
    authorized_finding_ids: tuple[str, ...] | None = None
    inspection_scope: Scope | None = None
    draft_change_scope: Scope | None = None
    hold_reason_code: RemediationHoldReasonCode | None = None
    non_dispatchable_reason_code: RemediationNonDispatchableReasonCode | None = None
    isolated_verification_authorized: bool = False
    machine_apply_allowed: bool = False
    auto_apply_allowed: bool = False
    auto_merge_allowed: bool = False
    invalid_if_snapshot_changed: bool = True
    authorized_by: str = "USER"
    authorization_source: str = "USER_HITL"


_ELIGIBLE_REMEDIATION_SOURCE_DECISIONS = frozenset(
    {
        MediationDecision.FINDING_PRESENT,
        MediationDecision.DUPLICATE_FINDING_MERGED,
    }
)


def validate_remediation_authorization_request(
    request: RemediationAuthorizationRequest,
) -> None:
    if not isinstance(request, RemediationAuthorizationRequest):
        raise ContractViolation(
            "Remediation authorization request must be a RemediationAuthorizationRequest."
        )
    _require_text(request.request_id, "remediation_request.request_id")
    _require_text(
        request.source_primary_mediation_result_id,
        "remediation_request.source_primary_mediation_result_id",
    )
    _require_text(
        request.source_audit_snapshot_id,
        "remediation_request.source_audit_snapshot_id",
    )
    _require_text(
        request.remediation_base_snapshot_id,
        "remediation_request.remediation_base_snapshot_id",
    )
    if not isinstance(request.requested_finding_ids, tuple) or not request.requested_finding_ids:
        raise ContractViolation("requested_finding_ids must be a non-empty tuple.")
    for index, finding_id in enumerate(request.requested_finding_ids):
        _require_text(finding_id, f"requested_finding_ids[{index}]")
    if len(set(request.requested_finding_ids)) != len(request.requested_finding_ids):
        raise ContractViolation("requested_finding_ids must not contain duplicates.")
    if not isinstance(request.inspection_scope, Scope):
        raise ContractViolation("inspection_scope must be a Scope.")
    if not isinstance(request.draft_change_scope, Scope):
        raise ContractViolation("draft_change_scope must be a Scope.")
    _require_bool(
        request.isolated_verification_requested,
        "remediation_request.isolated_verification_requested",
    )
    _require_bool(
        request.machine_apply_requested,
        "remediation_request.machine_apply_requested",
    )
    _require_bool(
        request.auto_apply_requested,
        "remediation_request.auto_apply_requested",
    )
    _require_bool(
        request.auto_merge_requested,
        "remediation_request.auto_merge_requested",
    )


def _remediation_non_dispatchable_reason(
    request: RemediationAuthorizationRequest,
) -> RemediationNonDispatchableReasonCode | None:
    if request.machine_apply_requested:
        return RemediationNonDispatchableReasonCode.MACHINE_APPLY_PROHIBITED
    if request.auto_apply_requested:
        return RemediationNonDispatchableReasonCode.AUTO_APPLY_PROHIBITED
    if request.auto_merge_requested:
        return RemediationNonDispatchableReasonCode.AUTO_MERGE_PROHIBITED
    return None


def _eligible_source_finding_ids(result: PrimaryMediationResult) -> frozenset[str]:
    return frozenset(finding.finding_id for finding in result.findings)


def _requested_finding_targets_inside_inspection_scope(
    request: RemediationAuthorizationRequest,
    result: PrimaryMediationResult,
) -> bool:
    requested_ids = set(request.requested_finding_ids)
    return all(
        request.inspection_scope.covers(Scope((finding.target_file,)))
        for finding in result.findings
        if finding.finding_id in requested_ids
    )


def _build_remediation_authorization(
    request: RemediationAuthorizationRequest,
    *,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    authorization_effect: RemediationAuthorizationEffect,
    authorized_finding_ids: tuple[str, ...] | None = None,
    inspection_scope: Scope | None = None,
    draft_change_scope: Scope | None = None,
    hold_reason_code: RemediationHoldReasonCode | None = None,
    non_dispatchable_reason_code: RemediationNonDispatchableReasonCode | None = None,
) -> RemediationAuthorization:
    record = RemediationAuthorization(
        authorization_id=_stable_id(
            "RAU",
            request.request_id,
            source_result.result_id,
            authorization_effect.value,
            *(authorized_finding_ids or request.requested_finding_ids),
        ),
        source_request_id=request.request_id,
        source_user_decision_id=source_input.source_user_decision_id,
        source_primary_mediation_result_id=source_result.result_id,
        source_audit_snapshot_id=source_input.base_snapshot_id,
        base_snapshot_id=request.remediation_base_snapshot_id,
        authorization_effect=authorization_effect,
        requested_finding_ids=request.requested_finding_ids,
        requested_inspection_scope=request.inspection_scope,
        requested_draft_change_scope=request.draft_change_scope,
        authorized_finding_ids=authorized_finding_ids,
        inspection_scope=inspection_scope,
        draft_change_scope=draft_change_scope,
        hold_reason_code=hold_reason_code,
        non_dispatchable_reason_code=non_dispatchable_reason_code,
    )
    validate_remediation_authorization(
        record,
        request=request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    return record


def evaluate_remediation_authorization(
    request: RemediationAuthorizationRequest,
    *,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    user_approved: bool,
) -> RemediationAuthorization:
    """
    Evaluate a User request to permit creation of a static remediation draft.

    This function creates an authorization record only.  It does not create a
    remediation draft, execute verification, apply a change, or merge code.
    """
    validate_remediation_authorization_request(request)
    validate_primary_mediation_result(source_result, source_input=source_input)
    _require_text(current_remediation_snapshot_id, "current_remediation_snapshot_id")
    _require_bool(user_approved, "user_approved")

    if request.source_primary_mediation_result_id != source_result.result_id:
        raise ContractViolation(
            "Remediation request must reference its source PRIMARY_MEDIATION_RESULT."
        )

    prohibited_reason = _remediation_non_dispatchable_reason(request)
    if prohibited_reason is not None:
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE,
            non_dispatchable_reason_code=prohibited_reason,
        )

    if not user_approved:
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.USER_AUTHORIZATION_MISSING,
        )

    if request.isolated_verification_requested:
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=(
                RemediationHoldReasonCode.ISOLATED_VERIFICATION_REQUIRES_SEPARATE_HITL
            ),
        )

    # The source must be an internally complete primary mediation outcome with
    # candidate findings.  This independently protects the authorization phase
    # against forged or incomplete upstream context.
    if (
        source_result.decision not in _ELIGIBLE_REMEDIATION_SOURCE_DECISIONS
        or not source_result.requires_user_hitl
        or not source_input.all_expected_agents_completed
        or not source_input.snapshot_consistent
        or not source_input.scope_consistent
    ):
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.PRIMARY_MEDIATION_NOT_ELIGIBLE,
        )

    if request.source_audit_snapshot_id != source_input.base_snapshot_id:
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.SOURCE_AUDIT_SNAPSHOT_MISMATCH,
        )

    if request.remediation_base_snapshot_id != current_remediation_snapshot_id:
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.REMEDIATION_SNAPSHOT_STALE,
        )

    if not set(request.requested_finding_ids).issubset(_eligible_source_finding_ids(source_result)):
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.FINDING_NOT_PRESENT_IN_SOURCE_RESULT,
        )

    if not _requested_finding_targets_inside_inspection_scope(request, source_result):
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.FINDING_SOURCE_OUTSIDE_INSPECTION_SCOPE,
        )

    if not request.inspection_scope.covers(request.draft_change_scope):
        return _build_remediation_authorization(
            request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            authorization_effect=RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL,
            hold_reason_code=RemediationHoldReasonCode.DRAFT_SCOPE_OUTSIDE_INSPECTION_SCOPE,
        )

    return _build_remediation_authorization(
        request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        authorization_effect=RemediationAuthorizationEffect.GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY,
        authorized_finding_ids=request.requested_finding_ids,
        inspection_scope=request.inspection_scope,
        draft_change_scope=request.draft_change_scope,
    )


def validate_remediation_authorization(
    record: RemediationAuthorization,
    *,
    request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
) -> None:
    """Validate authorization as a non-executing, Finding-scoped User record."""
    if not isinstance(record, RemediationAuthorization):
        raise ContractViolation("Record must be a REMEDIATION_AUTHORIZATION.")
    validate_remediation_authorization_request(request)
    validate_primary_mediation_result(source_result, source_input=source_input)
    _require_text(current_remediation_snapshot_id, "current_remediation_snapshot_id")
    _require_text(record.authorization_id, "remediation_authorization.authorization_id")
    _require_text(record.source_request_id, "remediation_authorization.source_request_id")
    _require_text(
        record.source_user_decision_id,
        "remediation_authorization.source_user_decision_id",
    )
    _require_text(
        record.source_primary_mediation_result_id,
        "remediation_authorization.source_primary_mediation_result_id",
    )
    _require_text(
        record.source_audit_snapshot_id,
        "remediation_authorization.source_audit_snapshot_id",
    )
    _require_text(record.base_snapshot_id, "remediation_authorization.base_snapshot_id")
    _require_enum_instance(
        record.authorization_effect,
        RemediationAuthorizationEffect,
        "remediation_authorization.authorization_effect",
    )
    if record.hold_reason_code is not None:
        _require_enum_instance(
            record.hold_reason_code,
            RemediationHoldReasonCode,
            "remediation_authorization.hold_reason_code",
        )
    if record.non_dispatchable_reason_code is not None:
        _require_enum_instance(
            record.non_dispatchable_reason_code,
            RemediationNonDispatchableReasonCode,
            "remediation_authorization.non_dispatchable_reason_code",
        )
    for field_name, value in (
        ("isolated_verification_authorized", record.isolated_verification_authorized),
        ("machine_apply_allowed", record.machine_apply_allowed),
        ("auto_apply_allowed", record.auto_apply_allowed),
        ("auto_merge_allowed", record.auto_merge_allowed),
        ("invalid_if_snapshot_changed", record.invalid_if_snapshot_changed),
    ):
        _require_bool(value, f"remediation_authorization.{field_name}")

    if record.authorized_by != "USER" or record.authorization_source != "USER_HITL":
        raise ContractViolation("REMEDIATION_AUTHORIZATION must originate from USER_HITL.")
    if record.source_request_id != request.request_id:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed its request reference.")
    if record.source_user_decision_id != source_input.source_user_decision_id:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed its User decision reference.")
    if record.source_primary_mediation_result_id != source_result.result_id:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed its mediation result reference.")
    if request.source_primary_mediation_result_id != source_result.result_id:
        raise ContractViolation("Remediation request does not reference the source mediation result.")
    if record.source_audit_snapshot_id != source_input.base_snapshot_id:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed its source audit snapshot.")
    if record.base_snapshot_id != request.remediation_base_snapshot_id:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed its remediation snapshot binding.")
    if record.requested_finding_ids != request.requested_finding_ids:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed requested Finding IDs.")
    if record.requested_inspection_scope != request.inspection_scope:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed requested inspection_scope.")
    if record.requested_draft_change_scope != request.draft_change_scope:
        raise ContractViolation("REMEDIATION_AUTHORIZATION changed requested draft_change_scope.")

    # No remediation authorization in this phase can grant these capabilities.
    if (
        record.isolated_verification_authorized
        or record.machine_apply_allowed
        or record.auto_apply_allowed
        or record.auto_merge_allowed
        or record.invalid_if_snapshot_changed is not True
    ):
        raise ContractViolation(
            "REMEDIATION_AUTHORIZATION cannot grant verification, application, merge, "
            "or disable snapshot invalidation in this phase."
        )

    granted = (
        record.authorization_effect
        is RemediationAuthorizationEffect.GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY
    )
    if not granted and (
        record.authorized_finding_ids is not None
        or record.inspection_scope is not None
        or record.draft_change_scope is not None
    ):
        raise ContractViolation(
            "Non-granted remediation authorization must not contain authorized scope or Findings."
        )

    if granted:
        if record.hold_reason_code is not None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("Granted remediation authorization must not contain reason codes.")
        if record.authorized_finding_ids != request.requested_finding_ids:
            raise ContractViolation("Granted authorization must preserve authorized Finding IDs.")
        if record.inspection_scope != request.inspection_scope:
            raise ContractViolation("Granted authorization must preserve inspection_scope.")
        if record.draft_change_scope != request.draft_change_scope:
            raise ContractViolation("Granted authorization must preserve draft_change_scope.")
        if source_result.decision not in _ELIGIBLE_REMEDIATION_SOURCE_DECISIONS:
            raise ContractViolation("Draft authorization requires a candidate Finding result.")
        if not source_result.requires_user_hitl:
            raise ContractViolation("Draft authorization requires a HITL-eligible source result.")
        if (
            not source_input.all_expected_agents_completed
            or not source_input.snapshot_consistent
            or not source_input.scope_consistent
        ):
            raise ContractViolation("Draft authorization requires a complete primary context.")
        if request.source_audit_snapshot_id != source_input.base_snapshot_id:
            raise ContractViolation("Source audit snapshot is stale or mismatched.")
        if request.remediation_base_snapshot_id != current_remediation_snapshot_id:
            raise ContractViolation("Remediation authorization snapshot is stale.")
        if not set(request.requested_finding_ids).issubset(_eligible_source_finding_ids(source_result)):
            raise ContractViolation("Authorization includes a Finding absent from primary mediation.")
        if not _requested_finding_targets_inside_inspection_scope(request, source_result):
            raise ContractViolation("inspection_scope omits the authorized Finding target.")
        if not request.inspection_scope.covers(request.draft_change_scope):
            raise ContractViolation("draft_change_scope exceeds inspection_scope.")
        if (
            request.isolated_verification_requested
            or request.machine_apply_requested
            or request.auto_apply_requested
            or request.auto_merge_requested
        ):
            raise ContractViolation("Granted draft authorization contains prohibited requested powers.")

    elif record.authorization_effect is RemediationAuthorizationEffect.HOLD_REQUIRES_ADDITIONAL_HITL:
        if record.hold_reason_code is None or record.non_dispatchable_reason_code is not None:
            raise ContractViolation("Held remediation authorization requires hold_reason_code only.")
    elif record.authorization_effect is RemediationAuthorizationEffect.NOT_GRANTED_NON_DISPATCHABLE:
        expected_reason = _remediation_non_dispatchable_reason(request)
        if expected_reason is None:
            raise ContractViolation("Non-dispatchable remediation result requires a prohibited request.")
        if record.non_dispatchable_reason_code is not expected_reason or record.hold_reason_code is not None:
            raise ContractViolation("Non-dispatchable remediation reason does not match request.")

# ---------------------------------------------------------------------------
# Phase 4: Static DRAFT_REMEDIATION creation contract only
# ---------------------------------------------------------------------------


class DraftRemediationFormat(str, Enum):
    """Permitted non-executing representation for a remediation proposal."""

    UNIFIED_DIFF_TEXT = "UNIFIED_DIFF_TEXT"


@dataclass(frozen=True)
class DraftRemediation:
    """
    Static remediation proposal bound to a granted REMEDIATION_AUTHORIZATION.

    This record is review material only. `proposed_diff` is retained as text;
    it is never applied, executed, verified, merged, or written by this module.
    """

    draft_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    base_snapshot_id: str
    prepared_by: AgentId
    authorized_finding_ids: tuple[str, ...]
    inspection_scope: Scope
    draft_change_scope: Scope
    target_files: tuple[str, ...]
    diff_format: DraftRemediationFormat
    proposed_diff: str
    proposed_diff_sha256: str
    rationale: str
    expected_effect: str
    known_side_effects: tuple[str, ...] = ()
    unknown_side_effects: tuple[str, ...] = ()
    proposed_diff_is_static_text: bool = True
    content_safety_review_required: bool = True
    change_performed: bool = False
    isolated_verification_performed: bool = False
    machine_apply_allowed: bool = False
    auto_apply_allowed: bool = False
    auto_merge_allowed: bool = False
    manual_application_requires_user: bool = True
    secondary_mediation_required: bool = True


_FORBIDDEN_STATIC_DIFF_METADATA = re.compile(
    r"(?m)^(?:GIT binary patch|Binary files\s|rename from\s|rename to\s|"
    r"new file mode\s|deleted file mode\s|old mode\s|new mode\s)"
)


def _validate_text_tuple(values: tuple[str, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ContractViolation(f"{field_name} must be a tuple.")
    for index, value in enumerate(values):
        _require_text(value, f"{field_name}[{index}]")


def _normalize_declared_target_files(target_files: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(target_files, (tuple, list)) or not target_files:
        raise ContractViolation("draft_remediation.target_files must be a non-empty sequence.")
    normalized = tuple(_normalize_relative_path(value) for value in target_files)
    if len(set(normalized)) != len(normalized):
        raise ContractViolation("draft_remediation.target_files must not contain duplicates.")
    return tuple(sorted(normalized))


def _diff_header_path(header: str) -> str:
    token = header.strip().split("\t", 1)[0].strip()
    if token == "/dev/null":
        raise ContractViolation(
            "Static DRAFT_REMEDIATION does not authorize file creation or deletion."
        )
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    return _normalize_relative_path(token)


def _extract_unified_diff_target_files(proposed_diff: str) -> tuple[str, ...]:
    """Parse only changed-file headers; this does not apply or execute a patch."""
    _require_text(proposed_diff, "draft_remediation.proposed_diff")
    if _FORBIDDEN_STATIC_DIFF_METADATA.search(proposed_diff):
        raise ContractViolation(
            "DRAFT_REMEDIATION may not include binary, rename, creation, deletion, or mode-change metadata."
        )
    lines = proposed_diff.splitlines()
    targets: list[str] = []
    has_hunk = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("--- "):
            if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
                raise ContractViolation("Unified diff old-file header must be followed by a new-file header.")
            old_path = _diff_header_path(line[4:])
            new_path = _diff_header_path(lines[index + 1][4:])
            if old_path != new_path:
                raise ContractViolation(
                    "DRAFT_REMEDIATION does not authorize rename or cross-file replacement."
                )
            targets.append(new_path)
            index += 2
            continue
        if line.startswith("@@"):
            has_hunk = True
        index += 1
    if not targets:
        raise ContractViolation("DRAFT_REMEDIATION must contain at least one unified diff file header.")
    if not has_hunk:
        raise ContractViolation("DRAFT_REMEDIATION must contain at least one unified diff hunk.")
    if len(set(targets)) != len(targets):
        raise ContractViolation("DRAFT_REMEDIATION must not contain duplicate target-file sections.")
    return tuple(sorted(targets))


def create_draft_remediation(
    *,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    target_files: Sequence[str],
    proposed_diff: str,
    rationale: str,
    expected_effect: str,
    known_side_effects: tuple[str, ...] = (),
    unknown_side_effects: tuple[str, ...] = (),
) -> DraftRemediation:
    """
    Create a static DRAFT_REMEDIATION record only.

    The function validates the existing User authorization and returns text for
    later secondary mediation. It never writes source files or runs the diff.
    """
    validate_remediation_authorization(
        authorization,
        request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    if (
        authorization.authorization_effect
        is not RemediationAuthorizationEffect.GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY
    ):
        raise ContractViolation("DRAFT_REMEDIATION requires granted draft-creation authorization.")
    if authorization.authorized_finding_ids is None:
        raise ContractViolation("Granted authorization is missing authorized Finding IDs.")
    if authorization.inspection_scope is None or authorization.draft_change_scope is None:
        raise ContractViolation("Granted authorization is missing authorized draft scopes.")
    _require_text(rationale, "draft_remediation.rationale")
    _require_text(expected_effect, "draft_remediation.expected_effect")
    _validate_text_tuple(known_side_effects, "draft_remediation.known_side_effects")
    _validate_text_tuple(unknown_side_effects, "draft_remediation.unknown_side_effects")
    normalized_targets = _normalize_declared_target_files(target_files)
    parsed_targets = _extract_unified_diff_target_files(proposed_diff)
    if parsed_targets != normalized_targets:
        raise ContractViolation(
            "DRAFT_REMEDIATION diff target files must exactly match its declared target_files."
        )
    for target_file in normalized_targets:
        if not authorization.draft_change_scope.covers(Scope((target_file,))):
            raise ContractViolation("DRAFT_REMEDIATION target file exceeds authorized draft_change_scope.")
    diff_hash = sha256(proposed_diff.encode("utf-8")).hexdigest()
    record = DraftRemediation(
        draft_id=_stable_id(
            "DRF",
            authorization.authorization_id,
            authorization.base_snapshot_id,
            diff_hash,
            *authorization.authorized_finding_ids,
        ),
        source_remediation_authorization_id=authorization.authorization_id,
        source_primary_mediation_result_id=authorization.source_primary_mediation_result_id,
        base_snapshot_id=authorization.base_snapshot_id,
        prepared_by=AgentId.REMEDIATION_DRAFT_AGENT,
        authorized_finding_ids=authorization.authorized_finding_ids,
        inspection_scope=authorization.inspection_scope,
        draft_change_scope=authorization.draft_change_scope,
        target_files=normalized_targets,
        diff_format=DraftRemediationFormat.UNIFIED_DIFF_TEXT,
        proposed_diff=proposed_diff,
        proposed_diff_sha256=diff_hash,
        rationale=rationale,
        expected_effect=expected_effect,
        known_side_effects=known_side_effects,
        unknown_side_effects=unknown_side_effects,
    )
    validate_draft_remediation(
        record,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    return record


def validate_draft_remediation(
    record: DraftRemediation,
    *,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
) -> None:
    """Validate static draft provenance, scope and non-execution invariants."""
    if not isinstance(record, DraftRemediation):
        raise ContractViolation("Record must be a DRAFT_REMEDIATION.")
    validate_remediation_authorization(
        authorization,
        request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    if (
        authorization.authorization_effect
        is not RemediationAuthorizationEffect.GRANTED_DRAFT_CREATION_WITHIN_BOUNDARY
    ):
        raise ContractViolation("DRAFT_REMEDIATION cannot originate from non-granted authorization.")
    _require_text(record.draft_id, "draft_remediation.draft_id")
    _require_text(
        record.source_remediation_authorization_id,
        "draft_remediation.source_remediation_authorization_id",
    )
    _require_text(
        record.source_primary_mediation_result_id,
        "draft_remediation.source_primary_mediation_result_id",
    )
    _require_text(record.base_snapshot_id, "draft_remediation.base_snapshot_id")
    _require_enum_instance(record.prepared_by, AgentId, "draft_remediation.prepared_by")
    _require_enum_instance(record.diff_format, DraftRemediationFormat, "draft_remediation.diff_format")
    _require_text(record.proposed_diff, "draft_remediation.proposed_diff")
    _require_text(record.proposed_diff_sha256, "draft_remediation.proposed_diff_sha256")
    _require_text(record.rationale, "draft_remediation.rationale")
    _require_text(record.expected_effect, "draft_remediation.expected_effect")
    _validate_text_tuple(record.known_side_effects, "draft_remediation.known_side_effects")
    _validate_text_tuple(record.unknown_side_effects, "draft_remediation.unknown_side_effects")
    for field_name, value in (
        ("proposed_diff_is_static_text", record.proposed_diff_is_static_text),
        ("content_safety_review_required", record.content_safety_review_required),
        ("change_performed", record.change_performed),
        ("isolated_verification_performed", record.isolated_verification_performed),
        ("machine_apply_allowed", record.machine_apply_allowed),
        ("auto_apply_allowed", record.auto_apply_allowed),
        ("auto_merge_allowed", record.auto_merge_allowed),
        ("manual_application_requires_user", record.manual_application_requires_user),
        ("secondary_mediation_required", record.secondary_mediation_required),
    ):
        _require_bool(value, f"draft_remediation.{field_name}")

    if record.source_remediation_authorization_id != authorization.authorization_id:
        raise ContractViolation("DRAFT_REMEDIATION changed its authorization reference.")
    if record.source_primary_mediation_result_id != authorization.source_primary_mediation_result_id:
        raise ContractViolation("DRAFT_REMEDIATION changed its primary mediation reference.")
    if record.base_snapshot_id != authorization.base_snapshot_id:
        raise ContractViolation("DRAFT_REMEDIATION changed its authorized base snapshot.")
    if record.base_snapshot_id != current_remediation_snapshot_id:
        raise ContractViolation("DRAFT_REMEDIATION snapshot is stale.")
    if record.prepared_by is not AgentId.REMEDIATION_DRAFT_AGENT:
        raise ContractViolation("Only REMEDIATION_DRAFT_AGENT may prepare DRAFT_REMEDIATION.")
    if record.authorized_finding_ids != authorization.authorized_finding_ids:
        raise ContractViolation("DRAFT_REMEDIATION changed authorized Finding IDs.")
    if record.inspection_scope != authorization.inspection_scope:
        raise ContractViolation("DRAFT_REMEDIATION changed authorized inspection_scope.")
    if record.draft_change_scope != authorization.draft_change_scope:
        raise ContractViolation("DRAFT_REMEDIATION changed authorized draft_change_scope.")
    normalized_targets = _normalize_declared_target_files(record.target_files)
    if normalized_targets != record.target_files:
        raise ContractViolation("DRAFT_REMEDIATION target_files must be normalized and sorted.")
    for target_file in record.target_files:
        if not record.draft_change_scope.covers(Scope((target_file,))):
            raise ContractViolation("DRAFT_REMEDIATION includes a target outside draft_change_scope.")
    if _extract_unified_diff_target_files(record.proposed_diff) != record.target_files:
        raise ContractViolation("DRAFT_REMEDIATION diff headers do not match authorized targets.")
    expected_hash = sha256(record.proposed_diff.encode("utf-8")).hexdigest()
    if record.proposed_diff_sha256 != expected_hash:
        raise ContractViolation("DRAFT_REMEDIATION proposed_diff hash is invalid.")
    if record.diff_format is not DraftRemediationFormat.UNIFIED_DIFF_TEXT:
        raise ContractViolation("Only unified static diff text is permitted in this phase.")
    if (
        record.proposed_diff_is_static_text is not True
        or record.content_safety_review_required is not True
        or record.change_performed
        or record.isolated_verification_performed
        or record.machine_apply_allowed
        or record.auto_apply_allowed
        or record.auto_merge_allowed
        or record.manual_application_requires_user is not True
        or record.secondary_mediation_required is not True
    ):
        raise ContractViolation(
            "DRAFT_REMEDIATION must remain static, unexecuted, unapplied, "
            "unmerged, and pending secondary mediation plus User decision."
        )


# ---------------------------------------------------------------------------
# Phase 5: REMEDIATION_IMPACT_REPORT contract only
# ---------------------------------------------------------------------------


class RemediationImpactDecision(str, Enum):
    """Permitted specialist-Agent conclusions for static draft impact review."""

    NO_IMPACT_CANDIDATE_REPORTED = "NO_IMPACT_CANDIDATE_REPORTED"
    IMPACT_CANDIDATE_PRESENT = "IMPACT_CANDIDATE_PRESENT"
    SCOPE_EXPANSION_REQUIRED = "SCOPE_EXPANSION_REQUIRED"
    NEW_FINDING_CANDIDATE_REQUIRES_HITL = "NEW_FINDING_CANDIDATE_REQUIRES_HITL"
    DRAFT_SAFETY_BOUNDARY_CONFLICT = "DRAFT_SAFETY_BOUNDARY_CONFLICT"


class RemediationImpactReasonCode(str, Enum):
    REVIEW_COMPLETED_NO_CANDIDATE = "REVIEW_COMPLETED_NO_CANDIDATE"
    RELATED_IMPACT_CANDIDATE_IDENTIFIED = "RELATED_IMPACT_CANDIDATE_IDENTIFIED"
    OUTSIDE_INSPECTION_SCOPE_REQUIRED = "OUTSIDE_INSPECTION_SCOPE_REQUIRED"
    SEPARATE_FINDING_REVIEW_REQUIRED = "SEPARATE_FINDING_REVIEW_REQUIRED"
    DRAFT_CONTENT_SAFETY_BOUNDARY_CONCERN = "DRAFT_CONTENT_SAFETY_BOUNDARY_CONCERN"


IMPACT_REVIEW_AGENTS = STATIC_AUDIT_AGENTS


@dataclass(frozen=True)
class RemediationImpactReport:
    """
    Static specialist-Agent review of a DRAFT_REMEDIATION.

    This record is an observation for a later secondary Mediator. It never
    changes the draft, writes files, performs verification, applies a patch,
    merges code, or authorizes any of those operations.
    """

    impact_report_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    reviewed_by: AgentId
    authorized_finding_ids: tuple[str, ...]
    inspection_scope: Scope
    draft_change_scope: Scope
    reviewed_files: tuple[str, ...]
    decision: RemediationImpactDecision
    reason_code: RemediationImpactReasonCode
    impact_summary: str
    evidence_summary: str
    new_finding_reports: tuple[FindingReport, ...] = ()
    required_scope_expansion: Scope | None = None
    operation_mode: str = "IMPACT_REVIEW"
    requires_secondary_mediation: bool = True
    draft_modified: bool = False
    change_performed: bool = False
    exploit_executed: bool = False
    isolated_verification_performed: bool = False
    machine_apply_allowed: bool = False
    auto_apply_allowed: bool = False
    auto_merge_allowed: bool = False


_IMPACT_DECISION_REASON: Mapping[
    RemediationImpactDecision, RemediationImpactReasonCode
] = {
    RemediationImpactDecision.NO_IMPACT_CANDIDATE_REPORTED: (
        RemediationImpactReasonCode.REVIEW_COMPLETED_NO_CANDIDATE
    ),
    RemediationImpactDecision.IMPACT_CANDIDATE_PRESENT: (
        RemediationImpactReasonCode.RELATED_IMPACT_CANDIDATE_IDENTIFIED
    ),
    RemediationImpactDecision.SCOPE_EXPANSION_REQUIRED: (
        RemediationImpactReasonCode.OUTSIDE_INSPECTION_SCOPE_REQUIRED
    ),
    RemediationImpactDecision.NEW_FINDING_CANDIDATE_REQUIRES_HITL: (
        RemediationImpactReasonCode.SEPARATE_FINDING_REVIEW_REQUIRED
    ),
    RemediationImpactDecision.DRAFT_SAFETY_BOUNDARY_CONFLICT: (
        RemediationImpactReasonCode.DRAFT_CONTENT_SAFETY_BOUNDARY_CONCERN
    ),
}


def _normalize_reviewed_files(files: Sequence[str]) -> tuple[str, ...]:
    if isinstance(files, (str, bytes)) or not isinstance(files, Sequence):
        raise ContractViolation("reviewed_files must be a sequence of relative paths.")
    normalized = tuple(sorted({_normalize_relative_path(path) for path in files}))
    if not normalized:
        raise ContractViolation("REMEDIATION_IMPACT_REPORT must identify reviewed files.")
    return normalized


def create_remediation_impact_report(
    *,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    reviewing_agent: AgentId,
    reviewed_context_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
    reviewed_files: Sequence[str],
    decision: RemediationImpactDecision,
    reason_code: RemediationImpactReasonCode,
    impact_summary: str,
    evidence_summary: str,
    new_finding_reports: tuple[FindingReport, ...] = (),
    required_scope_expansion: Scope | None = None,
) -> RemediationImpactReport:
    """
    Create one specialist-Agent impact report for later secondary mediation.

    This function creates a report record only. It does not inspect files by
    itself, alter DRAFT_REMEDIATION, run a patch, or start a later phase.
    """
    validate_draft_remediation(
        draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    _require_enum_instance(reviewing_agent, AgentId, "impact_report.reviewed_by")
    if reviewing_agent not in IMPACT_REVIEW_AGENTS:
        raise ContractViolation(
            "Only specialist Finding Agents may produce REMEDIATION_IMPACT_REPORT."
        )
    _require_text(reviewed_context_snapshot_id, "impact_report.reviewed_context_snapshot_id")
    _require_text(
        current_reviewed_context_snapshot_id,
        "current_reviewed_context_snapshot_id",
    )
    if reviewed_context_snapshot_id != current_reviewed_context_snapshot_id:
        raise ContractViolation("Impact-review context snapshot is stale.")
    _require_enum_instance(decision, RemediationImpactDecision, "impact_report.decision")
    _require_enum_instance(reason_code, RemediationImpactReasonCode, "impact_report.reason_code")
    _require_text(impact_summary, "impact_report.impact_summary")
    _require_text(evidence_summary, "impact_report.evidence_summary")
    if not isinstance(new_finding_reports, tuple):
        raise ContractViolation("new_finding_reports must be a tuple.")

    normalized_reviewed_files = _normalize_reviewed_files(reviewed_files)
    record = RemediationImpactReport(
        impact_report_id=_stable_id(
            "RIR",
            draft.draft_id,
            reviewing_agent.value,
            reviewed_context_snapshot_id,
            decision.value,
            *normalized_reviewed_files,
        ),
        source_draft_remediation_id=draft.draft_id,
        source_remediation_authorization_id=draft.source_remediation_authorization_id,
        source_primary_mediation_result_id=draft.source_primary_mediation_result_id,
        source_proposed_diff_sha256=draft.proposed_diff_sha256,
        base_snapshot_id=draft.base_snapshot_id,
        reviewed_context_snapshot_id=reviewed_context_snapshot_id,
        reviewed_by=reviewing_agent,
        authorized_finding_ids=draft.authorized_finding_ids,
        inspection_scope=draft.inspection_scope,
        draft_change_scope=draft.draft_change_scope,
        reviewed_files=normalized_reviewed_files,
        decision=decision,
        reason_code=reason_code,
        impact_summary=impact_summary,
        evidence_summary=evidence_summary,
        new_finding_reports=new_finding_reports,
        required_scope_expansion=required_scope_expansion,
    )
    validate_remediation_impact_report(
        record,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    return record


def validate_remediation_impact_report(
    record: RemediationImpactReport,
    *,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """
    Validate impact-report provenance, read scope, separation, and non-execution.

    The report may request broader User authorization, but it cannot itself
    expand readable scope or modify the source draft.
    """
    if not isinstance(record, RemediationImpactReport):
        raise ContractViolation("Record must be a REMEDIATION_IMPACT_REPORT.")
    validate_draft_remediation(
        draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    _require_text(record.impact_report_id, "impact_report.impact_report_id")
    _require_text(record.source_draft_remediation_id, "impact_report.source_draft_remediation_id")
    _require_text(
        record.source_remediation_authorization_id,
        "impact_report.source_remediation_authorization_id",
    )
    _require_text(
        record.source_primary_mediation_result_id,
        "impact_report.source_primary_mediation_result_id",
    )
    _require_text(record.source_proposed_diff_sha256, "impact_report.source_proposed_diff_sha256")
    _require_text(record.base_snapshot_id, "impact_report.base_snapshot_id")
    _require_text(record.reviewed_context_snapshot_id, "impact_report.reviewed_context_snapshot_id")
    _require_text(current_reviewed_context_snapshot_id, "current_reviewed_context_snapshot_id")
    _require_enum_instance(record.reviewed_by, AgentId, "impact_report.reviewed_by")
    _require_enum_instance(record.decision, RemediationImpactDecision, "impact_report.decision")
    _require_enum_instance(record.reason_code, RemediationImpactReasonCode, "impact_report.reason_code")
    _require_text(record.impact_summary, "impact_report.impact_summary")
    _require_text(record.evidence_summary, "impact_report.evidence_summary")
    for field_name, value in (
        ("requires_secondary_mediation", record.requires_secondary_mediation),
        ("draft_modified", record.draft_modified),
        ("change_performed", record.change_performed),
        ("exploit_executed", record.exploit_executed),
        ("isolated_verification_performed", record.isolated_verification_performed),
        ("machine_apply_allowed", record.machine_apply_allowed),
        ("auto_apply_allowed", record.auto_apply_allowed),
        ("auto_merge_allowed", record.auto_merge_allowed),
    ):
        _require_bool(value, f"impact_report.{field_name}")

    if record.operation_mode != "IMPACT_REVIEW":
        raise ContractViolation("REMEDIATION_IMPACT_REPORT operation_mode must remain IMPACT_REVIEW.")
    if record.reviewed_by not in IMPACT_REVIEW_AGENTS:
        raise ContractViolation("Only specialist Finding Agents may submit impact reports.")
    if record.source_draft_remediation_id != draft.draft_id:
        raise ContractViolation("Impact report changed its DRAFT_REMEDIATION reference.")
    if record.source_remediation_authorization_id != draft.source_remediation_authorization_id:
        raise ContractViolation("Impact report changed its authorization reference.")
    if record.source_primary_mediation_result_id != draft.source_primary_mediation_result_id:
        raise ContractViolation("Impact report changed its primary mediation reference.")
    if record.source_proposed_diff_sha256 != draft.proposed_diff_sha256:
        raise ContractViolation("Impact report changed or detached from the proposed_diff hash.")
    if record.base_snapshot_id != draft.base_snapshot_id:
        raise ContractViolation("Impact report changed its draft base snapshot binding.")
    if record.reviewed_context_snapshot_id != current_reviewed_context_snapshot_id:
        raise ContractViolation("Impact-review context snapshot is stale.")
    if record.authorized_finding_ids != draft.authorized_finding_ids:
        raise ContractViolation("Impact report changed authorized Finding IDs.")
    if record.inspection_scope != draft.inspection_scope:
        raise ContractViolation("Impact report changed inspection_scope.")
    if record.draft_change_scope != draft.draft_change_scope:
        raise ContractViolation("Impact report changed draft_change_scope.")

    normalized_reviewed_files = _normalize_reviewed_files(record.reviewed_files)
    if normalized_reviewed_files != record.reviewed_files:
        raise ContractViolation("Impact report reviewed_files must be normalized and sorted.")
    for reviewed_file in record.reviewed_files:
        if not record.inspection_scope.covers(Scope((reviewed_file,))):
            raise ContractViolation("Impact report reviewed a file outside inspection_scope.")

    expected_reason = _IMPACT_DECISION_REASON.get(record.decision)
    if record.reason_code is not expected_reason:
        raise ContractViolation("Impact-report reason_code does not match its decision.")

    if not isinstance(record.new_finding_reports, tuple):
        raise ContractViolation("impact_report.new_finding_reports must be a tuple.")
    new_finding_ids: set[str] = set()
    for finding in record.new_finding_reports:
        validate_finding_report(finding, audit_scope=record.inspection_scope)
        if finding.finding_id in new_finding_ids:
            raise ContractViolation("Impact report must not contain duplicate new Finding IDs.")
        new_finding_ids.add(finding.finding_id)
        if finding.finding_id in set(record.authorized_finding_ids):
            raise ContractViolation(
                "A new Finding report must remain separate from already authorized Finding IDs."
            )

    if record.decision is RemediationImpactDecision.SCOPE_EXPANSION_REQUIRED:
        if record.required_scope_expansion is None:
            raise ContractViolation("SCOPE_EXPANSION_REQUIRED must identify requested additional scope.")
        if record.inspection_scope.covers(record.required_scope_expansion):
            raise ContractViolation("Required scope expansion must be outside existing inspection_scope.")
        if record.new_finding_reports:
            raise ContractViolation("Scope-expansion request must not forge new Finding reports.")
    elif record.required_scope_expansion is not None:
        raise ContractViolation("Only SCOPE_EXPANSION_REQUIRED may identify additional scope.")

    if record.decision is RemediationImpactDecision.NEW_FINDING_CANDIDATE_REQUIRES_HITL:
        if not record.new_finding_reports:
            raise ContractViolation(
                "NEW_FINDING_CANDIDATE_REQUIRES_HITL requires separate Finding report candidate(s)."
            )
    elif record.new_finding_reports:
        raise ContractViolation(
            "New Finding report candidates require NEW_FINDING_CANDIDATE_REQUIRES_HITL."
        )

    if (
        record.requires_secondary_mediation is not True
        or record.draft_modified
        or record.change_performed
        or record.exploit_executed
        or record.isolated_verification_performed
        or record.machine_apply_allowed
        or record.auto_apply_allowed
        or record.auto_merge_allowed
    ):
        raise ContractViolation(
            "REMEDIATION_IMPACT_REPORT must remain a non-executing, "
            "non-modifying input for mandatory secondary mediation."
        )


# ---------------------------------------------------------------------------
# Phase 6: SECONDARY_MEDIATION_INPUT / RESULT contract only
# ---------------------------------------------------------------------------


class SecondaryMediationDecision(str, Enum):
    """Formal Mediator disposition of specialist impact-review records."""

    DRAFT_PRESENTABLE = "DRAFT_PRESENTABLE"
    IMPACT_REVIEW_INCOMPLETE = "IMPACT_REVIEW_INCOMPLETE"
    REMEDIATION_CONFLICT_DETECTED = "REMEDIATION_CONFLICT_DETECTED"
    SCOPE_EXPANSION_REQUIRED = "SCOPE_EXPANSION_REQUIRED"
    NEW_FINDING_REQUIRES_HITL = "NEW_FINDING_REQUIRES_HITL"
    REVIEW_CONTEXT_STALE = "REVIEW_CONTEXT_STALE"
    SAFETY_BOUNDARY_CONFLICT = "SAFETY_BOUNDARY_CONFLICT"


class SecondaryMediationReasonCode(str, Enum):
    """Reason codes for secondary mediation outcomes."""

    COMPLETE_NO_IMPACT_CANDIDATE = "COMPLETE_NO_IMPACT_CANDIDATE"
    EXPECTED_IMPACT_AGENT_RESULT_MISSING = "EXPECTED_IMPACT_AGENT_RESULT_MISSING"
    IMPACT_AGENT_EXECUTION_FAILED = "IMPACT_AGENT_EXECUTION_FAILED"
    IMPACT_CANDIDATE_REPORTED = "IMPACT_CANDIDATE_REPORTED"
    IMPACT_SCOPE_EXPANSION_REQUESTED = "IMPACT_SCOPE_EXPANSION_REQUESTED"
    NEW_FINDING_CANDIDATE_REPORTED = "NEW_FINDING_CANDIDATE_REPORTED"
    REVIEW_CONTEXT_SNAPSHOT_STALE = "REVIEW_CONTEXT_SNAPSHOT_STALE"
    IMPACT_REPORT_BOUNDARY_CONFLICT = "IMPACT_REPORT_BOUNDARY_CONFLICT"


@dataclass(frozen=True)
class SecondaryMediationInput:
    """
    Complete input envelope for formal secondary mediation.

    All specialist reports must refer to one static draft, one proposed-diff
    hash, one remediation base snapshot, and one reviewed context snapshot.
    No report may be absent when a DRAFT_PRESENTABLE outcome is considered.
    """

    secondary_input_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    authorized_finding_ids: tuple[str, ...]
    inspection_scope: Scope
    draft_change_scope: Scope
    expected_impact_agents: tuple[AgentId, ...]
    completed_impact_agents: tuple[AgentId, ...]
    failed_impact_agents: tuple[AgentId, ...] = ()
    impact_reports: tuple[RemediationImpactReport, ...] = ()
    boundary_event_detected: bool = False

    @property
    def missing_impact_agents(self) -> tuple[AgentId, ...]:
        completed_or_failed = set(self.completed_impact_agents) | set(self.failed_impact_agents)
        return tuple(
            agent
            for agent in self.expected_impact_agents
            if agent not in completed_or_failed
        )

    @property
    def all_expected_impact_agents_completed(self) -> bool:
        return (
            not self.failed_impact_agents
            and not self.missing_impact_agents
            and set(self.completed_impact_agents) == set(self.expected_impact_agents)
        )


@dataclass(frozen=True)
class SecondaryMediationResult:
    """
    Mediator output for a static draft after specialist impact review.

    Even DRAFT_PRESENTABLE is presentation-only: it is not verification,
    safety confirmation, application permission, merge permission, or close.
    """

    secondary_input_id: str
    result_id: str
    source_draft_remediation_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    decision: SecondaryMediationDecision
    reason_code: SecondaryMediationReasonCode
    considered_impact_reports: tuple[RemediationImpactReport, ...]
    expected_impact_agents: tuple[AgentId, ...]
    completed_impact_agents: tuple[AgentId, ...]
    missing_impact_agents: tuple[AgentId, ...]
    failed_impact_agents: tuple[AgentId, ...]
    requires_user_hitl: bool
    draft_presentable: bool
    note: str
    isolated_verification_authorized: bool = False
    change_performed: bool = False
    machine_apply_allowed: bool = False
    auto_apply_allowed: bool = False
    auto_merge_allowed: bool = False
    close_allowed: bool = False


def validate_secondary_mediation_input(
    record: SecondaryMediationInput,
    *,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
) -> None:
    """
    Validate a complete secondary-mediation input envelope.

    Impact reports are validated against the context snapshot at which they
    were created. A later change to that context is classified by secondary
    mediation as REVIEW_CONTEXT_STALE rather than silently reusing results.
    """
    if not isinstance(record, SecondaryMediationInput):
        raise ContractViolation("Formal secondary mediation requires SECONDARY_MEDIATION_INPUT.")
    validate_draft_remediation(
        draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    _require_text(record.secondary_input_id, "secondary_input.secondary_input_id")
    _require_text(
        record.source_draft_remediation_id,
        "secondary_input.source_draft_remediation_id",
    )
    _require_text(
        record.source_remediation_authorization_id,
        "secondary_input.source_remediation_authorization_id",
    )
    _require_text(
        record.source_primary_mediation_result_id,
        "secondary_input.source_primary_mediation_result_id",
    )
    _require_text(
        record.source_proposed_diff_sha256,
        "secondary_input.source_proposed_diff_sha256",
    )
    _require_text(record.base_snapshot_id, "secondary_input.base_snapshot_id")
    _require_text(
        record.reviewed_context_snapshot_id,
        "secondary_input.reviewed_context_snapshot_id",
    )
    if not isinstance(record.inspection_scope, Scope):
        raise ContractViolation("secondary_input.inspection_scope must be a Scope.")
    if not isinstance(record.draft_change_scope, Scope):
        raise ContractViolation("secondary_input.draft_change_scope must be a Scope.")
    _require_bool(
        record.boundary_event_detected,
        "secondary_input.boundary_event_detected",
    )

    if record.source_draft_remediation_id != draft.draft_id:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed its draft reference.")
    if record.source_remediation_authorization_id != draft.source_remediation_authorization_id:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed its authorization reference.")
    if record.source_primary_mediation_result_id != draft.source_primary_mediation_result_id:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed its primary mediation reference.")
    if record.source_proposed_diff_sha256 != draft.proposed_diff_sha256:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed its proposed_diff hash binding.")
    if record.base_snapshot_id != draft.base_snapshot_id:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed its draft base snapshot.")
    if record.authorized_finding_ids != draft.authorized_finding_ids:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed authorized Finding IDs.")
    if record.inspection_scope != draft.inspection_scope:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed inspection_scope.")
    if record.draft_change_scope != draft.draft_change_scope:
        raise ContractViolation("SECONDARY_MEDIATION_INPUT changed draft_change_scope.")

    if not isinstance(record.expected_impact_agents, tuple) or not record.expected_impact_agents:
        raise ContractViolation("expected_impact_agents must be a non-empty tuple.")
    if not isinstance(record.completed_impact_agents, tuple) or not isinstance(
        record.failed_impact_agents, tuple
    ):
        raise ContractViolation("completed_impact_agents and failed_impact_agents must be tuples.")
    for field_name, agents in (
        ("expected_impact_agents", record.expected_impact_agents),
        ("completed_impact_agents", record.completed_impact_agents),
        ("failed_impact_agents", record.failed_impact_agents),
    ):
        for index, agent in enumerate(agents):
            _require_enum_instance(agent, AgentId, f"{field_name}[{index}]")
        if len(set(agents)) != len(agents):
            raise ContractViolation(f"{field_name} must not contain duplicates.")

    expected = set(record.expected_impact_agents)
    completed = set(record.completed_impact_agents)
    failed = set(record.failed_impact_agents)
    if not expected.issubset(IMPACT_REVIEW_AGENTS):
        raise ContractViolation("Secondary mediation may expect specialist Finding Agents only.")
    if not completed.issubset(expected):
        raise ContractViolation("completed_impact_agents must be a subset of expected_impact_agents.")
    if not failed.issubset(expected):
        raise ContractViolation("failed_impact_agents must be a subset of expected_impact_agents.")
    if completed & failed:
        raise ContractViolation("An impact-review Agent cannot be both completed and failed.")

    if not isinstance(record.impact_reports, tuple):
        raise ContractViolation("impact_reports must be a tuple.")
    report_agents: list[AgentId] = []
    for report in record.impact_reports:
        if not isinstance(report, RemediationImpactReport):
            raise ContractViolation("impact_reports may contain REMEDIATION_IMPACT_REPORT records only.")
        validate_remediation_impact_report(
            report,
            draft=draft,
            authorization=authorization,
            authorization_request=authorization_request,
            source_input=source_input,
            source_result=source_result,
            current_remediation_snapshot_id=current_remediation_snapshot_id,
            current_reviewed_context_snapshot_id=record.reviewed_context_snapshot_id,
        )
        if report.reviewed_context_snapshot_id != record.reviewed_context_snapshot_id:
            raise ContractViolation("Impact reports do not share the secondary review context snapshot.")
        if report.reviewed_by not in expected or report.reviewed_by not in completed:
            raise ContractViolation(
                "Impact report was submitted by an Agent outside the completed expected set."
            )
        report_agents.append(report.reviewed_by)

    if len(set(report_agents)) != len(report_agents):
        raise ContractViolation("Secondary mediation permits one impact report per completed Agent.")
    if set(report_agents) != completed:
        raise ContractViolation(
            "Each completed impact-review Agent must submit exactly one impact report."
        )


def _secondary_expected_outcome(
    record: SecondaryMediationInput,
    *,
    current_reviewed_context_snapshot_id: str,
) -> tuple[SecondaryMediationDecision, SecondaryMediationReasonCode, bool]:
    """
    Derive the only permissible secondary decision for a validated input.

    Precedence is fixed: recorded safety-boundary concerns are surfaced first;
    then stale context, incomplete review, scope/new-finding routes, ordinary
    impact conflicts, and only finally a presentable draft.
    """
    _require_text(
        current_reviewed_context_snapshot_id,
        "current_reviewed_context_snapshot_id",
    )
    if record.boundary_event_detected or any(
        report.decision is RemediationImpactDecision.DRAFT_SAFETY_BOUNDARY_CONFLICT
        for report in record.impact_reports
    ):
        return (
            SecondaryMediationDecision.SAFETY_BOUNDARY_CONFLICT,
            SecondaryMediationReasonCode.IMPACT_REPORT_BOUNDARY_CONFLICT,
            False,
        )

    if record.reviewed_context_snapshot_id != current_reviewed_context_snapshot_id:
        return (
            SecondaryMediationDecision.REVIEW_CONTEXT_STALE,
            SecondaryMediationReasonCode.REVIEW_CONTEXT_SNAPSHOT_STALE,
            False,
        )

    if record.failed_impact_agents:
        return (
            SecondaryMediationDecision.IMPACT_REVIEW_INCOMPLETE,
            SecondaryMediationReasonCode.IMPACT_AGENT_EXECUTION_FAILED,
            False,
        )

    if record.missing_impact_agents:
        return (
            SecondaryMediationDecision.IMPACT_REVIEW_INCOMPLETE,
            SecondaryMediationReasonCode.EXPECTED_IMPACT_AGENT_RESULT_MISSING,
            False,
        )

    if any(
        report.decision is RemediationImpactDecision.SCOPE_EXPANSION_REQUIRED
        for report in record.impact_reports
    ):
        return (
            SecondaryMediationDecision.SCOPE_EXPANSION_REQUIRED,
            SecondaryMediationReasonCode.IMPACT_SCOPE_EXPANSION_REQUESTED,
            False,
        )

    if any(
        report.decision is RemediationImpactDecision.NEW_FINDING_CANDIDATE_REQUIRES_HITL
        for report in record.impact_reports
    ):
        return (
            SecondaryMediationDecision.NEW_FINDING_REQUIRES_HITL,
            SecondaryMediationReasonCode.NEW_FINDING_CANDIDATE_REPORTED,
            False,
        )

    if any(
        report.decision is RemediationImpactDecision.IMPACT_CANDIDATE_PRESENT
        for report in record.impact_reports
    ):
        return (
            SecondaryMediationDecision.REMEDIATION_CONFLICT_DETECTED,
            SecondaryMediationReasonCode.IMPACT_CANDIDATE_REPORTED,
            False,
        )

    if not record.all_expected_impact_agents_completed:
        return (
            SecondaryMediationDecision.IMPACT_REVIEW_INCOMPLETE,
            SecondaryMediationReasonCode.EXPECTED_IMPACT_AGENT_RESULT_MISSING,
            False,
        )

    if not record.impact_reports or any(
        report.decision is not RemediationImpactDecision.NO_IMPACT_CANDIDATE_REPORTED
        for report in record.impact_reports
    ):
        raise ContractViolation(
            "Secondary mediation input contains an unsupported impact-report combination."
        )

    return (
        SecondaryMediationDecision.DRAFT_PRESENTABLE,
        SecondaryMediationReasonCode.COMPLETE_NO_IMPACT_CANDIDATE,
        True,
    )


def _secondary_result(
    input_record: SecondaryMediationInput,
    *,
    current_reviewed_context_snapshot_id: str,
    decision: SecondaryMediationDecision,
    reason_code: SecondaryMediationReasonCode,
    draft_presentable: bool,
    note: str,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
) -> SecondaryMediationResult:
    result = SecondaryMediationResult(
        secondary_input_id=input_record.secondary_input_id,
        result_id=_stable_id(
            "SMR",
            input_record.secondary_input_id,
            input_record.source_proposed_diff_sha256,
            decision.value,
            reason_code.value,
        ),
        source_draft_remediation_id=input_record.source_draft_remediation_id,
        source_proposed_diff_sha256=input_record.source_proposed_diff_sha256,
        base_snapshot_id=input_record.base_snapshot_id,
        reviewed_context_snapshot_id=input_record.reviewed_context_snapshot_id,
        decision=decision,
        reason_code=reason_code,
        considered_impact_reports=input_record.impact_reports,
        expected_impact_agents=input_record.expected_impact_agents,
        completed_impact_agents=input_record.completed_impact_agents,
        missing_impact_agents=input_record.missing_impact_agents,
        failed_impact_agents=input_record.failed_impact_agents,
        requires_user_hitl=True,
        draft_presentable=draft_presentable,
        note=note,
    )
    validate_secondary_mediation_result(
        result,
        source_input_record=input_record,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=source_input,
        primary_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    return result


def validate_secondary_mediation_result(
    result: SecondaryMediationResult,
    *,
    source_input_record: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """Reject forged or authority-expanding secondary mediation results."""
    if not isinstance(result, SecondaryMediationResult):
        raise ContractViolation("Result must be a SECONDARY_MEDIATION_RESULT.")
    validate_secondary_mediation_input(
        source_input_record,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=primary_input,
        source_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    _require_text(result.secondary_input_id, "secondary_result.secondary_input_id")
    _require_text(result.result_id, "secondary_result.result_id")
    _require_text(
        result.source_draft_remediation_id,
        "secondary_result.source_draft_remediation_id",
    )
    _require_text(
        result.source_proposed_diff_sha256,
        "secondary_result.source_proposed_diff_sha256",
    )
    _require_text(result.base_snapshot_id, "secondary_result.base_snapshot_id")
    _require_text(
        result.reviewed_context_snapshot_id,
        "secondary_result.reviewed_context_snapshot_id",
    )
    _require_enum_instance(result.decision, SecondaryMediationDecision, "secondary_result.decision")
    _require_enum_instance(
        result.reason_code,
        SecondaryMediationReasonCode,
        "secondary_result.reason_code",
    )
    _require_text(result.note, "secondary_result.note")
    for field_name, value in (
        ("requires_user_hitl", result.requires_user_hitl),
        ("draft_presentable", result.draft_presentable),
        ("isolated_verification_authorized", result.isolated_verification_authorized),
        ("change_performed", result.change_performed),
        ("machine_apply_allowed", result.machine_apply_allowed),
        ("auto_apply_allowed", result.auto_apply_allowed),
        ("auto_merge_allowed", result.auto_merge_allowed),
        ("close_allowed", result.close_allowed),
    ):
        _require_bool(value, f"secondary_result.{field_name}")

    if result.secondary_input_id != source_input_record.secondary_input_id:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed its input reference.")
    if result.source_draft_remediation_id != source_input_record.source_draft_remediation_id:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed its draft reference.")
    if result.source_proposed_diff_sha256 != source_input_record.source_proposed_diff_sha256:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed its proposed_diff hash.")
    if result.base_snapshot_id != source_input_record.base_snapshot_id:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed its base snapshot.")
    if result.reviewed_context_snapshot_id != source_input_record.reviewed_context_snapshot_id:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed its review context snapshot.")
    if result.considered_impact_reports != source_input_record.impact_reports:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed considered impact reports.")
    if result.expected_impact_agents != source_input_record.expected_impact_agents:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed expected impact Agents.")
    if result.completed_impact_agents != source_input_record.completed_impact_agents:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed completed impact Agents.")
    if result.missing_impact_agents != source_input_record.missing_impact_agents:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed missing impact Agents.")
    if result.failed_impact_agents != source_input_record.failed_impact_agents:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT changed failed impact Agents.")

    expected_decision, expected_reason, expected_presentable = _secondary_expected_outcome(
        source_input_record,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    if result.decision is not expected_decision or result.reason_code is not expected_reason:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT does not match the bound impact-review inputs.")
    if result.draft_presentable is not expected_presentable:
        raise ContractViolation("SECONDARY_MEDIATION_RESULT forged draft_presentable status.")
    if result.requires_user_hitl is not True:
        raise ContractViolation("Every secondary mediation outcome must be presented to User HITL.")
    if (
        result.isolated_verification_authorized
        or result.change_performed
        or result.machine_apply_allowed
        or result.auto_apply_allowed
        or result.auto_merge_allowed
        or result.close_allowed
    ):
        raise ContractViolation(
            "SECONDARY_MEDIATION_RESULT cannot authorize verification, modification, "
            "application, merge, or close."
        )


def mediate_secondary_remediation(
    input_record: SecondaryMediationInput,
    *,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    source_input: PrimaryMediationInput,
    source_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> SecondaryMediationResult:
    """
    Classify already-produced specialist impact reports only.

    Mediator does not inspect code, alter the draft, execute verification,
    apply changes, merge, close, or dispatch another phase.
    """
    validate_secondary_mediation_input(
        input_record,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )
    decision, reason_code, draft_presentable = _secondary_expected_outcome(
        input_record,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    notes: Mapping[SecondaryMediationDecision, str] = {
        SecondaryMediationDecision.DRAFT_PRESENTABLE: (
            "All expected impact-review Agents completed without reporting configured "
            "impact candidates. The draft may be presented to User; this is not "
            "safety confirmation, verification, or application permission."
        ),
        SecondaryMediationDecision.IMPACT_REVIEW_INCOMPLETE: (
            "Required impact-review inputs are incomplete; the draft cannot be presented "
            "as review-complete."
        ),
        SecondaryMediationDecision.REMEDIATION_CONFLICT_DETECTED: (
            "At least one specialist Agent reported an impact candidate requiring User review."
        ),
        SecondaryMediationDecision.SCOPE_EXPANSION_REQUIRED: (
            "An impact review requires additional inspection scope; no scope was expanded."
        ),
        SecondaryMediationDecision.NEW_FINDING_REQUIRES_HITL: (
            "A separate new Finding candidate was reported and must remain outside the existing draft."
        ),
        SecondaryMediationDecision.REVIEW_CONTEXT_STALE: (
            "Reviewed context changed after impact review; existing impact conclusions are stale."
        ),
        SecondaryMediationDecision.SAFETY_BOUNDARY_CONFLICT: (
            "An impact-report boundary concern was reported; no further progression is authorized."
        ),
    }
    return _secondary_result(
        input_record,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
        decision=decision,
        reason_code=reason_code,
        draft_presentable=draft_presentable,
        note=notes[decision],
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        source_input=source_input,
        source_result=source_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
    )

# ---------------------------------------------------------------------------
# Phase 7: HITL_DRAFT_DISPOSITION_INPUT / RESULT contract only
# ---------------------------------------------------------------------------


class HitlDraftDispositionAction(str, Enum):
    """
    Explicit User choices after receiving a DRAFT_PRESENTABLE result.

    A request for separate verification authorization is not authorization.
    """

    ACKNOWLEDGE_DRAFT_PRESENTATION = "ACKNOWLEDGE_DRAFT_PRESENTATION"
    HOLD_DRAFT = "HOLD_DRAFT"
    REJECT_DRAFT = "REJECT_DRAFT"
    REQUEST_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "REQUEST_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION"
    )


class HitlDraftDispositionDecision(str, Enum):
    """Recorded outcome of the User's handling of a presentable draft."""

    PRESENTATION_ACKNOWLEDGED = "PRESENTATION_ACKNOWLEDGED"
    DRAFT_HELD = "DRAFT_HELD"
    DRAFT_REJECTED = "DRAFT_REJECTED"
    VERIFICATION_AUTHORIZATION_REQUEST_RECORDED = (
        "VERIFICATION_AUTHORIZATION_REQUEST_RECORDED"
    )


class HitlDraftDispositionReasonCode(str, Enum):
    """Reason codes for a User HITL draft-disposition record."""

    USER_ACKNOWLEDGED_PRESENTATION = "USER_ACKNOWLEDGED_PRESENTATION"
    USER_HELD_DRAFT = "USER_HELD_DRAFT"
    USER_REJECTED_DRAFT = "USER_REJECTED_DRAFT"
    USER_REQUESTED_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "USER_REQUESTED_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION"
    )


@dataclass(frozen=True)
class HitlDraftDispositionInput:
    """
    User HITL input for handling one DRAFT_PRESENTABLE result only.

    This input records a User instruction. It does not grant verification,
    application, merge, close, or post-change-audit authority.
    """

    disposition_input_id: str
    source_secondary_mediation_result_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    user_action: HitlDraftDispositionAction
    disposition_actor: str = "USER"
    disposition_source: str = "USER_HITL"


@dataclass(frozen=True)
class HitlDraftDispositionResult:
    """
    Immutable record of the User's disposition of a presentable draft.

    Even when the User requests consideration of isolated verification, this
    result remains a request record only. A separate future contract would be
    required to authorize any isolated verification.
    """

    disposition_input_id: str
    result_id: str
    source_secondary_mediation_result_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    user_action: HitlDraftDispositionAction
    decision: HitlDraftDispositionDecision
    reason_code: HitlDraftDispositionReasonCode
    disposition_recorded: bool
    requires_user_hitl_for_any_further_action: bool
    separate_verification_authorization_requested: bool
    note: str

    # Fixed no-authority boundary for this phase.
    isolated_verification_authorized: bool = False
    verification_executed: bool = False
    application_authorized: bool = False
    change_performed: bool = False
    machine_apply_allowed: bool = False
    auto_apply_allowed: bool = False
    merge_allowed: bool = False
    auto_merge_allowed: bool = False
    close_allowed: bool = False
    post_change_audit_started: bool = False


def validate_hitl_draft_disposition_input(
    record: HitlDraftDispositionInput,
    *,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """
    Validate User handling input for a single DRAFT_PRESENTABLE result.

    Results from incomplete review, conflicts, scope expansion, new findings,
    stale context, or safety-boundary conflict are not eligible for this
    ordinary draft-disposition flow.
    """
    if not isinstance(record, HitlDraftDispositionInput):
        raise ContractViolation(
            "Formal User draft disposition requires HITL_DRAFT_DISPOSITION_INPUT."
        )

    validate_secondary_mediation_result(
        source_secondary_result,
        source_input_record=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )

    if (
        source_secondary_result.decision is not SecondaryMediationDecision.DRAFT_PRESENTABLE
        or source_secondary_result.draft_presentable is not True
        or source_secondary_result.requires_user_hitl is not True
    ):
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT requires a User-HITL-bound DRAFT_PRESENTABLE source result."
        )

    _require_text(record.disposition_input_id, "disposition_input.disposition_input_id")
    _require_text(
        record.source_secondary_mediation_result_id,
        "disposition_input.source_secondary_mediation_result_id",
    )
    _require_text(
        record.source_draft_remediation_id,
        "disposition_input.source_draft_remediation_id",
    )
    _require_text(
        record.source_remediation_authorization_id,
        "disposition_input.source_remediation_authorization_id",
    )
    _require_text(
        record.source_primary_mediation_result_id,
        "disposition_input.source_primary_mediation_result_id",
    )
    _require_text(
        record.source_proposed_diff_sha256,
        "disposition_input.source_proposed_diff_sha256",
    )
    _require_text(record.base_snapshot_id, "disposition_input.base_snapshot_id")
    _require_text(
        record.reviewed_context_snapshot_id,
        "disposition_input.reviewed_context_snapshot_id",
    )
    _require_enum_instance(
        record.user_action,
        HitlDraftDispositionAction,
        "disposition_input.user_action",
    )

    if record.disposition_actor != "USER" or record.disposition_source != "USER_HITL":
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT must originate from USER_HITL."
        )

    if record.source_secondary_mediation_result_id != source_secondary_result.result_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its secondary mediation result reference."
        )
    if record.source_draft_remediation_id != source_secondary_result.source_draft_remediation_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its draft reference."
        )
    if record.source_remediation_authorization_id != source_secondary_input.source_remediation_authorization_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its remediation authorization reference."
        )
    if record.source_primary_mediation_result_id != source_secondary_input.source_primary_mediation_result_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its primary mediation reference."
        )
    if record.source_proposed_diff_sha256 != source_secondary_result.source_proposed_diff_sha256:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its proposed_diff hash binding."
        )
    if record.base_snapshot_id != source_secondary_result.base_snapshot_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its base snapshot binding."
        )
    if record.reviewed_context_snapshot_id != source_secondary_result.reviewed_context_snapshot_id:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_INPUT changed its reviewed-context snapshot binding."
        )


def _hitl_draft_disposition_expected_outcome(
    action: HitlDraftDispositionAction,
) -> tuple[
    HitlDraftDispositionDecision,
    HitlDraftDispositionReasonCode,
    bool,
    str,
]:
    if action is HitlDraftDispositionAction.ACKNOWLEDGE_DRAFT_PRESENTATION:
        return (
            HitlDraftDispositionDecision.PRESENTATION_ACKNOWLEDGED,
            HitlDraftDispositionReasonCode.USER_ACKNOWLEDGED_PRESENTATION,
            False,
            (
                "User acknowledged the presented draft. No verification, application, "
                "merge, close, or automatic workflow progression is authorized."
            ),
        )
    if action is HitlDraftDispositionAction.HOLD_DRAFT:
        return (
            HitlDraftDispositionDecision.DRAFT_HELD,
            HitlDraftDispositionReasonCode.USER_HELD_DRAFT,
            False,
            (
                "User placed the draft on hold. No further phase is authorized "
                "without a new User HITL decision."
            ),
        )
    if action is HitlDraftDispositionAction.REJECT_DRAFT:
        return (
            HitlDraftDispositionDecision.DRAFT_REJECTED,
            HitlDraftDispositionReasonCode.USER_REJECTED_DRAFT,
            False,
            (
                "User rejected the draft. No verification, application, merge, "
                "close, or automatic restart is authorized."
            ),
        )
    if (
        action
        is HitlDraftDispositionAction.REQUEST_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION
    ):
        return (
            HitlDraftDispositionDecision.VERIFICATION_AUTHORIZATION_REQUEST_RECORDED,
            HitlDraftDispositionReasonCode.USER_REQUESTED_SEPARATE_ISOLATED_VERIFICATION_AUTHORIZATION,
            True,
            (
                "User requested consideration of a separate isolated-verification "
                "authorization contract. Verification is not authorized or executed."
            ),
        )
    raise ContractViolation("Unsupported User draft-disposition action.")


def _hitl_draft_disposition_result(
    input_record: HitlDraftDispositionInput,
    *,
    decision: HitlDraftDispositionDecision,
    reason_code: HitlDraftDispositionReasonCode,
    separate_verification_authorization_requested: bool,
    note: str,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> HitlDraftDispositionResult:
    result = HitlDraftDispositionResult(
        disposition_input_id=input_record.disposition_input_id,
        result_id=_stable_id(
            "HDD",
            input_record.disposition_input_id,
            input_record.source_secondary_mediation_result_id,
            input_record.source_proposed_diff_sha256,
            decision.value,
            reason_code.value,
        ),
        source_secondary_mediation_result_id=input_record.source_secondary_mediation_result_id,
        source_draft_remediation_id=input_record.source_draft_remediation_id,
        source_remediation_authorization_id=input_record.source_remediation_authorization_id,
        source_primary_mediation_result_id=input_record.source_primary_mediation_result_id,
        source_proposed_diff_sha256=input_record.source_proposed_diff_sha256,
        base_snapshot_id=input_record.base_snapshot_id,
        reviewed_context_snapshot_id=input_record.reviewed_context_snapshot_id,
        user_action=input_record.user_action,
        decision=decision,
        reason_code=reason_code,
        disposition_recorded=True,
        requires_user_hitl_for_any_further_action=True,
        separate_verification_authorization_requested=(
            separate_verification_authorization_requested
        ),
        note=note,
    )
    validate_hitl_draft_disposition_result(
        result,
        source_input_record=input_record,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    return result


def validate_hitl_draft_disposition_result(
    result: HitlDraftDispositionResult,
    *,
    source_input_record: HitlDraftDispositionInput,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """Reject forged or authority-expanding User draft-disposition results."""
    if not isinstance(result, HitlDraftDispositionResult):
        raise ContractViolation("Result must be a HITL_DRAFT_DISPOSITION_RESULT.")

    validate_hitl_draft_disposition_input(
        source_input_record,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )

    for field_name, value in (
        ("disposition_input_id", result.disposition_input_id),
        ("result_id", result.result_id),
        ("source_secondary_mediation_result_id", result.source_secondary_mediation_result_id),
        ("source_draft_remediation_id", result.source_draft_remediation_id),
        ("source_remediation_authorization_id", result.source_remediation_authorization_id),
        ("source_primary_mediation_result_id", result.source_primary_mediation_result_id),
        ("source_proposed_diff_sha256", result.source_proposed_diff_sha256),
        ("base_snapshot_id", result.base_snapshot_id),
        ("reviewed_context_snapshot_id", result.reviewed_context_snapshot_id),
        ("note", result.note),
    ):
        _require_text(value, f"disposition_result.{field_name}")

    _require_enum_instance(
        result.user_action,
        HitlDraftDispositionAction,
        "disposition_result.user_action",
    )
    _require_enum_instance(
        result.decision,
        HitlDraftDispositionDecision,
        "disposition_result.decision",
    )
    _require_enum_instance(
        result.reason_code,
        HitlDraftDispositionReasonCode,
        "disposition_result.reason_code",
    )
    for field_name, value in (
        ("disposition_recorded", result.disposition_recorded),
        (
            "requires_user_hitl_for_any_further_action",
            result.requires_user_hitl_for_any_further_action,
        ),
        (
            "separate_verification_authorization_requested",
            result.separate_verification_authorization_requested,
        ),
        ("isolated_verification_authorized", result.isolated_verification_authorized),
        ("verification_executed", result.verification_executed),
        ("application_authorized", result.application_authorized),
        ("change_performed", result.change_performed),
        ("machine_apply_allowed", result.machine_apply_allowed),
        ("auto_apply_allowed", result.auto_apply_allowed),
        ("merge_allowed", result.merge_allowed),
        ("auto_merge_allowed", result.auto_merge_allowed),
        ("close_allowed", result.close_allowed),
        ("post_change_audit_started", result.post_change_audit_started),
    ):
        _require_bool(value, f"disposition_result.{field_name}")

    if result.disposition_input_id != source_input_record.disposition_input_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its input reference.")
    if result.source_secondary_mediation_result_id != source_input_record.source_secondary_mediation_result_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its secondary result reference.")
    if result.source_draft_remediation_id != source_input_record.source_draft_remediation_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its draft reference.")
    if result.source_remediation_authorization_id != source_input_record.source_remediation_authorization_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its authorization reference.")
    if result.source_primary_mediation_result_id != source_input_record.source_primary_mediation_result_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its primary mediation reference.")
    if result.source_proposed_diff_sha256 != source_input_record.source_proposed_diff_sha256:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its proposed_diff hash.")
    if result.base_snapshot_id != source_input_record.base_snapshot_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its base snapshot.")
    if result.reviewed_context_snapshot_id != source_input_record.reviewed_context_snapshot_id:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed its review-context snapshot.")
    if result.user_action is not source_input_record.user_action:
        raise ContractViolation("HITL_DRAFT_DISPOSITION_RESULT changed the recorded User action.")

    (
        expected_decision,
        expected_reason,
        expected_verification_request,
        _expected_note,
    ) = _hitl_draft_disposition_expected_outcome(source_input_record.user_action)
    if result.decision is not expected_decision or result.reason_code is not expected_reason:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_RESULT does not match the User HITL input."
        )
    if (
        result.separate_verification_authorization_requested
        is not expected_verification_request
    ):
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_RESULT forged separate-verification request status."
        )
    if result.disposition_recorded is not True:
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_RESULT must record a completed User disposition."
        )
    if result.requires_user_hitl_for_any_further_action is not True:
        raise ContractViolation(
            "Any further phase after draft disposition requires separate User HITL."
        )
    if (
        result.isolated_verification_authorized
        or result.verification_executed
        or result.application_authorized
        or result.change_performed
        or result.machine_apply_allowed
        or result.auto_apply_allowed
        or result.merge_allowed
        or result.auto_merge_allowed
        or result.close_allowed
        or result.post_change_audit_started
    ):
        raise ContractViolation(
            "HITL_DRAFT_DISPOSITION_RESULT cannot authorize or perform verification, "
            "application, modification, merge, close, or post-change audit."
        )


def record_hitl_draft_disposition(
    input_record: HitlDraftDispositionInput,
    *,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> HitlDraftDispositionResult:
    """
    Record User treatment of a DRAFT_PRESENTABLE draft only.

    This function records User disposition; it does not inspect code, alter a
    draft, execute isolated verification, authorize application, apply changes,
    merge, close, or dispatch any subsequent phase.
    """
    validate_hitl_draft_disposition_input(
        input_record,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    (
        decision,
        reason_code,
        separate_verification_authorization_requested,
        note,
    ) = _hitl_draft_disposition_expected_outcome(input_record.user_action)

    return _hitl_draft_disposition_result(
        input_record,
        decision=decision,
        reason_code=reason_code,
        separate_verification_authorization_requested=(
            separate_verification_authorization_requested
        ),
        note=note,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )

# ---------------------------------------------------------------------------
# Phase 8: ISOLATED_VERIFICATION_AUTHORIZATION_INPUT / RESULT contract only
# ---------------------------------------------------------------------------


class IsolatedVerificationCheckType(str, Enum):
    """Enum-only allowlist for a bounded isolated-verification plan."""

    PYTHON_SYNTAX_CHECK = "PYTHON_SYNTAX_CHECK"
    CONTRACT_TEST_CHECK = "CONTRACT_TEST_CHECK"
    DETERMINISTIC_STRESS_CHECK = "DETERMINISTIC_STRESS_CHECK"


class IsolatedVerificationAuthorizationAction(str, Enum):
    """Explicit User choices concerning one bounded verification plan."""

    AUTHORIZE_BOUNDED_ISOLATED_VERIFICATION_PLAN = (
        "AUTHORIZE_BOUNDED_ISOLATED_VERIFICATION_PLAN"
    )
    HOLD_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "HOLD_ISOLATED_VERIFICATION_AUTHORIZATION"
    )
    REJECT_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "REJECT_ISOLATED_VERIFICATION_AUTHORIZATION"
    )


class IsolatedVerificationAuthorizationDecision(str, Enum):
    """Recorded outcome of User review of one bounded verification plan."""

    VERIFICATION_PLAN_AUTHORIZED = "VERIFICATION_PLAN_AUTHORIZED"
    VERIFICATION_AUTHORIZATION_HELD = "VERIFICATION_AUTHORIZATION_HELD"
    VERIFICATION_AUTHORIZATION_REJECTED = "VERIFICATION_AUTHORIZATION_REJECTED"


class IsolatedVerificationAuthorizationReasonCode(str, Enum):
    """Reason codes for a bounded isolated-verification authorization record."""

    USER_AUTHORIZED_BOUNDED_ISOLATED_VERIFICATION_PLAN = (
        "USER_AUTHORIZED_BOUNDED_ISOLATED_VERIFICATION_PLAN"
    )
    USER_HELD_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "USER_HELD_ISOLATED_VERIFICATION_AUTHORIZATION"
    )
    USER_REJECTED_ISOLATED_VERIFICATION_AUTHORIZATION = (
        "USER_REJECTED_ISOLATED_VERIFICATION_AUTHORIZATION"
    )


@dataclass(frozen=True)
class IsolatedVerificationAuthorizationInput:
    """
    User HITL input for a bounded isolated-verification plan only.

    There is deliberately no free-form command field.  The record cannot
    execute verification, contact external systems, or alter repository data.
    """

    authorization_input_id: str
    source_hitl_disposition_result_id: str
    source_secondary_mediation_result_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    verification_scope: Scope
    requested_check_types: tuple[IsolatedVerificationCheckType, ...]
    user_action: IsolatedVerificationAuthorizationAction
    deterministic_stress_runs: int | None = None
    deterministic_seed: int | None = None

    # Requests that are non-dispatchable within this contract.
    network_access_requested: bool = False
    external_scan_requested: bool = False
    repository_write_requested: bool = False
    source_file_modification_requested: bool = False
    draft_apply_requested: bool = False
    merge_requested: bool = False
    close_requested: bool = False
    post_change_audit_requested: bool = False

    authorization_actor: str = "USER"
    authorization_source: str = "USER_HITL"


@dataclass(frozen=True)
class IsolatedVerificationAuthorizationResult:
    """
    User HITL record for a bounded isolated-verification plan.

    A plan-authorized result remains non-executing.  A separate future contract
    and a new User HITL decision are required before any verification execution.
    """

    authorization_input_id: str
    result_id: str
    source_hitl_disposition_result_id: str
    source_secondary_mediation_result_id: str
    source_draft_remediation_id: str
    source_remediation_authorization_id: str
    source_primary_mediation_result_id: str
    source_proposed_diff_sha256: str
    base_snapshot_id: str
    reviewed_context_snapshot_id: str
    verification_scope: Scope
    requested_check_types: tuple[IsolatedVerificationCheckType, ...]
    deterministic_stress_runs: int | None
    deterministic_seed: int | None
    user_action: IsolatedVerificationAuthorizationAction
    decision: IsolatedVerificationAuthorizationDecision
    reason_code: IsolatedVerificationAuthorizationReasonCode
    authorization_recorded: bool
    bounded_isolated_verification_plan_authorized: bool
    requires_separate_execution_contract: bool
    requires_user_hitl_for_any_further_action: bool
    note: str

    # Fixed no-execution / no-external-side-effect boundary for this phase.
    isolated_verification_execution_authorized: bool = False
    verification_executed: bool = False
    network_access_allowed: bool = False
    external_scan_allowed: bool = False
    repository_write_allowed: bool = False
    source_file_modification_allowed: bool = False
    draft_apply_allowed: bool = False
    application_authorized: bool = False
    change_performed: bool = False
    merge_allowed: bool = False
    auto_merge_allowed: bool = False
    close_allowed: bool = False
    post_change_audit_started: bool = False
    automatic_progression_allowed: bool = False


def _validate_bounded_isolated_verification_plan(
    record: IsolatedVerificationAuthorizationInput,
    *,
    authorization: RemediationAuthorization,
) -> None:
    """Validate allowlisted checks, bounded stress settings, and read scope."""
    if not isinstance(record.verification_scope, Scope):
        raise ContractViolation("verification_input.verification_scope must be a Scope.")
    if authorization.inspection_scope is None:
        raise ContractViolation(
            "Bounded verification planning requires an authorized inspection_scope."
        )
    if not authorization.inspection_scope.covers(record.verification_scope):
        raise ContractViolation(
            "verification_scope must remain within the authorized inspection_scope."
        )

    if (
        not isinstance(record.requested_check_types, tuple)
        or not record.requested_check_types
    ):
        raise ContractViolation("requested_check_types must be a non-empty tuple.")
    for index, check_type in enumerate(record.requested_check_types):
        _require_enum_instance(
            check_type,
            IsolatedVerificationCheckType,
            f"verification_input.requested_check_types[{index}]",
        )
    if len(set(record.requested_check_types)) != len(record.requested_check_types):
        raise ContractViolation("requested_check_types must not contain duplicates.")

    includes_stress = (
        IsolatedVerificationCheckType.DETERMINISTIC_STRESS_CHECK
        in record.requested_check_types
    )
    if includes_stress:
        if (
            not isinstance(record.deterministic_stress_runs, int)
            or isinstance(record.deterministic_stress_runs, bool)
            or not (1 <= record.deterministic_stress_runs <= 10_000)
        ):
            raise ContractViolation(
                "DETERMINISTIC_STRESS_CHECK requires runs in the range 1..10000."
            )
        if (
            not isinstance(record.deterministic_seed, int)
            or isinstance(record.deterministic_seed, bool)
            or not (0 <= record.deterministic_seed <= 2**32 - 1)
        ):
            raise ContractViolation(
                "DETERMINISTIC_STRESS_CHECK requires a bounded integer seed."
            )
    elif (
        record.deterministic_stress_runs is not None
        or record.deterministic_seed is not None
    ):
        raise ContractViolation(
            "Stress parameters may be supplied only with DETERMINISTIC_STRESS_CHECK."
        )


def validate_isolated_verification_authorization_input(
    record: IsolatedVerificationAuthorizationInput,
    *,
    source_disposition_result: HitlDraftDispositionResult,
    source_disposition_input: HitlDraftDispositionInput,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """Validate User HITL treatment of one bounded isolated-verification plan."""
    if not isinstance(record, IsolatedVerificationAuthorizationInput):
        raise ContractViolation(
            "Formal isolated-verification authorization requires "
            "ISOLATED_VERIFICATION_AUTHORIZATION_INPUT."
        )

    validate_hitl_draft_disposition_result(
        source_disposition_result,
        source_input_record=source_disposition_input,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )

    if (
        source_disposition_result.decision
        is not HitlDraftDispositionDecision.VERIFICATION_AUTHORIZATION_REQUEST_RECORDED
        or source_disposition_result.separate_verification_authorization_requested
        is not True
        or source_disposition_result.requires_user_hitl_for_any_further_action
        is not True
    ):
        raise ContractViolation(
            "ISOLATED_VERIFICATION_AUTHORIZATION_INPUT requires an H result "
            "that recorded a separate verification-authorization request."
        )

    _require_text(record.authorization_input_id, "verification_input.authorization_input_id")
    for field_name, value in (
        ("source_hitl_disposition_result_id", record.source_hitl_disposition_result_id),
        ("source_secondary_mediation_result_id", record.source_secondary_mediation_result_id),
        ("source_draft_remediation_id", record.source_draft_remediation_id),
        ("source_remediation_authorization_id", record.source_remediation_authorization_id),
        ("source_primary_mediation_result_id", record.source_primary_mediation_result_id),
        ("source_proposed_diff_sha256", record.source_proposed_diff_sha256),
        ("base_snapshot_id", record.base_snapshot_id),
        ("reviewed_context_snapshot_id", record.reviewed_context_snapshot_id),
    ):
        _require_text(value, f"verification_input.{field_name}")
    _require_enum_instance(
        record.user_action,
        IsolatedVerificationAuthorizationAction,
        "verification_input.user_action",
    )
    for field_name, value in (
        ("network_access_requested", record.network_access_requested),
        ("external_scan_requested", record.external_scan_requested),
        ("repository_write_requested", record.repository_write_requested),
        ("source_file_modification_requested", record.source_file_modification_requested),
        ("draft_apply_requested", record.draft_apply_requested),
        ("merge_requested", record.merge_requested),
        ("close_requested", record.close_requested),
        ("post_change_audit_requested", record.post_change_audit_requested),
    ):
        _require_bool(value, f"verification_input.{field_name}")

    if record.authorization_actor != "USER" or record.authorization_source != "USER_HITL":
        raise ContractViolation(
            "ISOLATED_VERIFICATION_AUTHORIZATION_INPUT must originate from USER_HITL."
        )

    expected_bindings = {
        "source_hitl_disposition_result_id": source_disposition_result.result_id,
        "source_secondary_mediation_result_id": source_disposition_result.source_secondary_mediation_result_id,
        "source_draft_remediation_id": source_disposition_result.source_draft_remediation_id,
        "source_remediation_authorization_id": source_disposition_result.source_remediation_authorization_id,
        "source_primary_mediation_result_id": source_disposition_result.source_primary_mediation_result_id,
        "source_proposed_diff_sha256": source_disposition_result.source_proposed_diff_sha256,
        "base_snapshot_id": source_disposition_result.base_snapshot_id,
        "reviewed_context_snapshot_id": source_disposition_result.reviewed_context_snapshot_id,
    }
    for field_name, expected_value in expected_bindings.items():
        if getattr(record, field_name) != expected_value:
            raise ContractViolation(
                f"Verification authorization input changed bound field: {field_name}."
            )

    if (
        record.network_access_requested
        or record.external_scan_requested
        or record.repository_write_requested
        or record.source_file_modification_requested
        or record.draft_apply_requested
        or record.merge_requested
        or record.close_requested
        or record.post_change_audit_requested
    ):
        raise ContractViolation(
            "Verification-plan authorization cannot request network access, external scan, "
            "repository writes, source changes, apply, merge, close, or post-change audit."
        )

    _validate_bounded_isolated_verification_plan(record, authorization=authorization)


def _isolated_verification_expected_outcome(
    action: IsolatedVerificationAuthorizationAction,
) -> tuple[
    IsolatedVerificationAuthorizationDecision,
    IsolatedVerificationAuthorizationReasonCode,
    bool,
    str,
]:
    if (
        action
        is IsolatedVerificationAuthorizationAction.AUTHORIZE_BOUNDED_ISOLATED_VERIFICATION_PLAN
    ):
        return (
            IsolatedVerificationAuthorizationDecision.VERIFICATION_PLAN_AUTHORIZED,
            IsolatedVerificationAuthorizationReasonCode.USER_AUTHORIZED_BOUNDED_ISOLATED_VERIFICATION_PLAN,
            True,
            (
                "User authorized a bounded isolated-verification plan record. "
                "No verification has executed and a separate execution contract is required."
            ),
        )
    if (
        action
        is IsolatedVerificationAuthorizationAction.HOLD_ISOLATED_VERIFICATION_AUTHORIZATION
    ):
        return (
            IsolatedVerificationAuthorizationDecision.VERIFICATION_AUTHORIZATION_HELD,
            IsolatedVerificationAuthorizationReasonCode.USER_HELD_ISOLATED_VERIFICATION_AUTHORIZATION,
            False,
            (
                "User held the isolated-verification authorization request. "
                "No verification or downstream phase is authorized."
            ),
        )
    if (
        action
        is IsolatedVerificationAuthorizationAction.REJECT_ISOLATED_VERIFICATION_AUTHORIZATION
    ):
        return (
            IsolatedVerificationAuthorizationDecision.VERIFICATION_AUTHORIZATION_REJECTED,
            IsolatedVerificationAuthorizationReasonCode.USER_REJECTED_ISOLATED_VERIFICATION_AUTHORIZATION,
            False,
            (
                "User rejected the isolated-verification authorization request. "
                "No verification or downstream phase is authorized."
            ),
        )
    raise ContractViolation("Unsupported isolated-verification authorization action.")


def _isolated_verification_authorization_result(
    input_record: IsolatedVerificationAuthorizationInput,
    *,
    decision: IsolatedVerificationAuthorizationDecision,
    reason_code: IsolatedVerificationAuthorizationReasonCode,
    bounded_isolated_verification_plan_authorized: bool,
    note: str,
    source_disposition_result: HitlDraftDispositionResult,
    source_disposition_input: HitlDraftDispositionInput,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> IsolatedVerificationAuthorizationResult:
    result = IsolatedVerificationAuthorizationResult(
        authorization_input_id=input_record.authorization_input_id,
        result_id=_stable_id(
            "IVA",
            input_record.authorization_input_id,
            input_record.source_hitl_disposition_result_id,
            input_record.source_proposed_diff_sha256,
            decision.value,
            reason_code.value,
        ),
        source_hitl_disposition_result_id=input_record.source_hitl_disposition_result_id,
        source_secondary_mediation_result_id=input_record.source_secondary_mediation_result_id,
        source_draft_remediation_id=input_record.source_draft_remediation_id,
        source_remediation_authorization_id=input_record.source_remediation_authorization_id,
        source_primary_mediation_result_id=input_record.source_primary_mediation_result_id,
        source_proposed_diff_sha256=input_record.source_proposed_diff_sha256,
        base_snapshot_id=input_record.base_snapshot_id,
        reviewed_context_snapshot_id=input_record.reviewed_context_snapshot_id,
        verification_scope=input_record.verification_scope,
        requested_check_types=input_record.requested_check_types,
        deterministic_stress_runs=input_record.deterministic_stress_runs,
        deterministic_seed=input_record.deterministic_seed,
        user_action=input_record.user_action,
        decision=decision,
        reason_code=reason_code,
        authorization_recorded=True,
        bounded_isolated_verification_plan_authorized=(
            bounded_isolated_verification_plan_authorized
        ),
        requires_separate_execution_contract=True,
        requires_user_hitl_for_any_further_action=True,
        note=note,
    )
    validate_isolated_verification_authorization_result(
        result,
        source_input_record=input_record,
        source_disposition_result=source_disposition_result,
        source_disposition_input=source_disposition_input,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    return result


def validate_isolated_verification_authorization_result(
    result: IsolatedVerificationAuthorizationResult,
    *,
    source_input_record: IsolatedVerificationAuthorizationInput,
    source_disposition_result: HitlDraftDispositionResult,
    source_disposition_input: HitlDraftDispositionInput,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> None:
    """Reject forged or authority-expanding verification-plan results."""
    if not isinstance(result, IsolatedVerificationAuthorizationResult):
        raise ContractViolation(
            "Result must be an ISOLATED_VERIFICATION_AUTHORIZATION_RESULT."
        )

    validate_isolated_verification_authorization_input(
        source_input_record,
        source_disposition_result=source_disposition_result,
        source_disposition_input=source_disposition_input,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )

    for field_name, value in (
        ("authorization_input_id", result.authorization_input_id),
        ("result_id", result.result_id),
        ("source_hitl_disposition_result_id", result.source_hitl_disposition_result_id),
        ("source_secondary_mediation_result_id", result.source_secondary_mediation_result_id),
        ("source_draft_remediation_id", result.source_draft_remediation_id),
        ("source_remediation_authorization_id", result.source_remediation_authorization_id),
        ("source_primary_mediation_result_id", result.source_primary_mediation_result_id),
        ("source_proposed_diff_sha256", result.source_proposed_diff_sha256),
        ("base_snapshot_id", result.base_snapshot_id),
        ("reviewed_context_snapshot_id", result.reviewed_context_snapshot_id),
        ("note", result.note),
    ):
        _require_text(value, f"verification_result.{field_name}")
    if not isinstance(result.verification_scope, Scope):
        raise ContractViolation("verification_result.verification_scope must be a Scope.")
    _require_enum_instance(
        result.user_action,
        IsolatedVerificationAuthorizationAction,
        "verification_result.user_action",
    )
    _require_enum_instance(
        result.decision,
        IsolatedVerificationAuthorizationDecision,
        "verification_result.decision",
    )
    _require_enum_instance(
        result.reason_code,
        IsolatedVerificationAuthorizationReasonCode,
        "verification_result.reason_code",
    )
    if not isinstance(result.requested_check_types, tuple) or not result.requested_check_types:
        raise ContractViolation("verification_result.requested_check_types must be non-empty.")
    for index, check_type in enumerate(result.requested_check_types):
        _require_enum_instance(
            check_type,
            IsolatedVerificationCheckType,
            f"verification_result.requested_check_types[{index}]",
        )

    for field_name, value in (
        ("authorization_recorded", result.authorization_recorded),
        (
            "bounded_isolated_verification_plan_authorized",
            result.bounded_isolated_verification_plan_authorized,
        ),
        ("requires_separate_execution_contract", result.requires_separate_execution_contract),
        (
            "requires_user_hitl_for_any_further_action",
            result.requires_user_hitl_for_any_further_action,
        ),
        (
            "isolated_verification_execution_authorized",
            result.isolated_verification_execution_authorized,
        ),
        ("verification_executed", result.verification_executed),
        ("network_access_allowed", result.network_access_allowed),
        ("external_scan_allowed", result.external_scan_allowed),
        ("repository_write_allowed", result.repository_write_allowed),
        ("source_file_modification_allowed", result.source_file_modification_allowed),
        ("draft_apply_allowed", result.draft_apply_allowed),
        ("application_authorized", result.application_authorized),
        ("change_performed", result.change_performed),
        ("merge_allowed", result.merge_allowed),
        ("auto_merge_allowed", result.auto_merge_allowed),
        ("close_allowed", result.close_allowed),
        ("post_change_audit_started", result.post_change_audit_started),
        ("automatic_progression_allowed", result.automatic_progression_allowed),
    ):
        _require_bool(value, f"verification_result.{field_name}")

    if result.authorization_input_id != source_input_record.authorization_input_id:
        raise ContractViolation("Verification authorization result changed its input reference.")
    for field_name in (
        "source_hitl_disposition_result_id",
        "source_secondary_mediation_result_id",
        "source_draft_remediation_id",
        "source_remediation_authorization_id",
        "source_primary_mediation_result_id",
        "source_proposed_diff_sha256",
        "base_snapshot_id",
        "reviewed_context_snapshot_id",
        "verification_scope",
        "requested_check_types",
        "deterministic_stress_runs",
        "deterministic_seed",
        "user_action",
    ):
        if getattr(result, field_name) != getattr(source_input_record, field_name):
            raise ContractViolation(
                f"Verification authorization result changed bound field: {field_name}."
            )

    (
        expected_decision,
        expected_reason,
        expected_plan_authorized,
        _expected_note,
    ) = _isolated_verification_expected_outcome(source_input_record.user_action)
    if result.decision is not expected_decision or result.reason_code is not expected_reason:
        raise ContractViolation(
            "Verification authorization result does not match the User HITL input."
        )
    if (
        result.bounded_isolated_verification_plan_authorized
        is not expected_plan_authorized
    ):
        raise ContractViolation(
            "Verification authorization result forged plan-authorization status."
        )
    if result.authorization_recorded is not True:
        raise ContractViolation("Verification authorization result must record a User decision.")
    if result.requires_separate_execution_contract is not True:
        raise ContractViolation(
            "An authorized verification plan still requires a separate execution contract."
        )
    if result.requires_user_hitl_for_any_further_action is not True:
        raise ContractViolation(
            "Any further phase after verification-plan authorization requires User HITL."
        )
    if (
        result.isolated_verification_execution_authorized
        or result.verification_executed
        or result.network_access_allowed
        or result.external_scan_allowed
        or result.repository_write_allowed
        or result.source_file_modification_allowed
        or result.draft_apply_allowed
        or result.application_authorized
        or result.change_performed
        or result.merge_allowed
        or result.auto_merge_allowed
        or result.close_allowed
        or result.post_change_audit_started
        or result.automatic_progression_allowed
    ):
        raise ContractViolation(
            "ISOLATED_VERIFICATION_AUTHORIZATION_RESULT cannot execute verification "
            "or authorize external access, modification, apply, merge, close, "
            "post-change audit, or automatic progression."
        )


def authorize_isolated_verification_plan(
    input_record: IsolatedVerificationAuthorizationInput,
    *,
    source_disposition_result: HitlDraftDispositionResult,
    source_disposition_input: HitlDraftDispositionInput,
    source_secondary_result: SecondaryMediationResult,
    source_secondary_input: SecondaryMediationInput,
    draft: DraftRemediation,
    authorization: RemediationAuthorization,
    authorization_request: RemediationAuthorizationRequest,
    primary_input: PrimaryMediationInput,
    primary_result: PrimaryMediationResult,
    current_remediation_snapshot_id: str,
    current_reviewed_context_snapshot_id: str,
) -> IsolatedVerificationAuthorizationResult:
    """
    Record User authorization, hold, or rejection of a bounded plan only.

    This function does not execute tests, accept command text, access a
    network, write files, apply a draft, merge, close, or automatically start
    any subsequent phase.
    """
    validate_isolated_verification_authorization_input(
        input_record,
        source_disposition_result=source_disposition_result,
        source_disposition_input=source_disposition_input,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
    (
        decision,
        reason_code,
        bounded_plan_authorized,
        note,
    ) = _isolated_verification_expected_outcome(input_record.user_action)

    return _isolated_verification_authorization_result(
        input_record,
        decision=decision,
        reason_code=reason_code,
        bounded_isolated_verification_plan_authorized=bounded_plan_authorized,
        note=note,
        source_disposition_result=source_disposition_result,
        source_disposition_input=source_disposition_input,
        source_secondary_result=source_secondary_result,
        source_secondary_input=source_secondary_input,
        draft=draft,
        authorization=authorization,
        authorization_request=authorization_request,
        primary_input=primary_input,
        primary_result=primary_result,
        current_remediation_snapshot_id=current_remediation_snapshot_id,
        current_reviewed_context_snapshot_id=current_reviewed_context_snapshot_id,
    )
