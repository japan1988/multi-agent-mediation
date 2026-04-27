
# -*- coding: utf-8 -*-
"""
Production-oriented Doc Orchestrator Simulator.

Features:
- Task Contract Gate
- Rough token estimate
- Per-task checkpoint / resume for Word, Excel, and PPT tasks
- HMAC-SHA256 audit log hash chain
- HMAC-protected checkpoint files
- SHA-256 + HMAC artifact integrity records
- PII-safe audit / checkpoint / artifact writes
- No mediation / negotiation feature
- No automatic external submission

Important:
- HMAC keys must be supplied from environment or a protected key file.
- Hashing here provides tamper evidence, not physical write prevention.
- In real deployment, store HMAC keys outside the repository.
- External submit / upload / push / send actions should remain HITL-gated.

Version: v1.2.6-hash-chain-checkpoint
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

__version__ = "1.2.6-hash-chain-checkpoint"

JST = timezone(timedelta(hours=9))
GENESIS_HASH = "0" * 64

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
FinalDecider = Literal["SYSTEM", "USER"]
KIND = Literal["excel", "word", "ppt"]
TaskStatus = Literal[
    "NOT_STARTED",
    "RUNNING",
    "COMPLETED",
    "INTERRUPTED",
    "WAITING_FOR_HITL",
    "FAILED_FINAL",
    "SKIPPED",
]

_TASKS: List[Tuple[str, KIND]] = [
    ("task_word", "word"),
    ("task_excel", "excel"),
    ("task_ppt", "ppt"),
]

ALLOWED_OUTPUT_MODES = {
    "full_code",
    "unified_diff",
    "summary",
    "steps",
    "artifact",
}

KNOWN_PROHIBITED_ACTIONS = {
    "seal_rfl",
    "sealed_overrideable_true",
    "seal_outside_ethics_or_acc",
    "weaken_tests",
    "external_api_call",
    "external_api_call_without_approval",
    "file_delete",
    "license_semantics_change_without_confirmation",
    "persist_raw_text",
    "persist_pii",
    "write_artifacts",
    "submit_without_user_approval",
}

OUTPUT_MODE_BASE_RANGE = {
    "summary": (800, 1500),
    "steps": (1000, 2000),
    "artifact": (1500, 3000),
    "unified_diff": (2500, 6000),
    "full_code": (4000, 12000),
}


class IntegrityError(RuntimeError):
    """Raised when tamper-evident verification fails."""


# -----------------------------
# Canonical hashing / HMAC
# -----------------------------
def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256_hex(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return cleaned.strip("_") or "run"


def _ts() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


# -----------------------------
# PII redaction
# -----------------------------
def redact_sensitive(text: str) -> str:
    if not text:
        return ""
    return EMAIL_RE.sub("<REDACTED_EMAIL>", text)


def _deep_redact(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, list):
        return [_deep_redact(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _deep_redact(value) for key, value in obj.items()}
    return obj


def _json_safe_copy(obj: Any) -> Any:
    return json.loads(json.dumps(obj, ensure_ascii=False))


# -----------------------------
# Data classes
# -----------------------------
@dataclass
class TokenEstimate:
    estimated_input_tokens: int
    estimated_output_tokens_min: int
    estimated_output_tokens_max: int
    estimated_output_tokens_mid: int
    estimated_total_tokens_min: int
    estimated_total_tokens_max: int
    estimated_total_tokens_mid: int
    complexity: str
    hitl_probability: str
    confidence: str
    basis: List[str]
    disclaimer: str


@dataclass
class TaskResult:
    task_id: str
    kind: KIND
    decision: Decision
    blocked_layer: Optional[str]
    reason_code: str = ""
    artifact_path: Optional[str] = None


@dataclass
class SimulationResult:
    run_id: str
    decision: Decision
    tasks: List[TaskResult]
    artifacts_written_task_ids: List[str]
    token_estimate: Optional[TokenEstimate] = None
    checkpoint_path: Optional[str] = None
    integrity_status: str = "NOT_CHECKED"


@dataclass
class TaskContractResult:
    decision: Decision
    reason_code: str
    normalized_contract: Optional[Dict[str, Any]]
    missing_fields: List[str]
    invalid_fields: List[str]
    unknown_prohibitions: List[str]
    token_estimate: TokenEstimate


@dataclass
class TaskCheckpoint:
    task_id: str
    kind: KIND
    status: TaskStatus = "NOT_STARTED"
    last_completed_layer: Optional[str] = None
    failed_layer: Optional[str] = None
    reason_code: str = ""
    artifact_path: Optional[str] = None
    artifact_sha256: Optional[str] = None
    artifact_hmac: Optional[str] = None
    resume_allowed: bool = True
    requires_hitl_before_resume: bool = False


@dataclass
class RunCheckpoint:
    checkpoint_version: str
    run_id: str
    status: str
    resume_mode: str
    current_task_id: Optional[str]
    failed_task_id: Optional[str]
    failed_layer: Optional[str]
    reason_code: str
    key_id: str
    hash_alg: str
    tasks: List[TaskCheckpoint]
    token_estimate: Optional[Dict[str, Any]] = None
    checkpoint_hmac: Optional[str] = None


# -----------------------------
# Key loading
# -----------------------------
def load_hmac_key(
    *,
    env_var: str = "DOC_ORCH_HMAC_KEY",
    key_file: Optional[str] = None,
    allow_demo_key: bool = False,
) -> bytes:
    """
    Load the HMAC key.

    Production recommendation:
    - Use env var or a protected file.
    - Do not commit keys to the repository.
    """
    if key_file:
        data = Path(key_file).read_bytes().strip()
        if not data:
            raise ValueError("HMAC key file is empty.")
        return data

    value = os.environ.get(env_var)
    if value:
        return value.encode("utf-8")

    if allow_demo_key:
        # Runtime-only demo key. Do not use for production.
        return hashlib.sha256(b"doc-orchestrator-local-demo-key").digest()

    raise ValueError(
        f"HMAC key missing. Set {env_var}, pass --hmac-key-file, "
        "or use --allow-demo-key for local demonstration only."
    )


# -----------------------------
# Audit hash chain
# -----------------------------
@dataclass
class AuditLog:
    audit_path: Path
    hmac_key: bytes
    key_id: str = "default"
    chain_id: str = "doc-orchestrator"
    verify_existing: bool = True

    def __post_init__(self) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = GENESIS_HASH
        self._row_index = 0

        if self.audit_path.exists() and self.audit_path.stat().st_size > 0:
            if self.verify_existing:
                last_hash, count = verify_audit_hash_chain(
                    self.audit_path,
                    self.hmac_key,
                )
                self._prev_hash = last_hash
                self._row_index = count
            else:
                rows = _read_jsonl_rows(self.audit_path)
                if rows:
                    last = rows[-1]
                    self._prev_hash = str(last.get("row_hash", GENESIS_HASH))
                    self._row_index = len(rows)

    def emit(self, row: Dict[str, Any]) -> None:
        """
        Append a tamper-evident JSONL row.

        Each row contains:
        - row_index
        - prev_hash
        - row_hash
        - key_id
        - chain_id

        PII-like strings are redacted before hashing and writing.
        """
        base = _json_safe_copy(row)
        base = _deep_redact(base)

        base.setdefault("ts", _ts())
        base.setdefault("event", "AUDIT_EVENT")
        base.setdefault("decision", "RUN")
        base.setdefault("sealed", False)
        base.setdefault("overrideable", False)
        base.setdefault("final_decider", "SYSTEM")
        base.setdefault("reason_code", "AUDIT_EVENT")
        base.setdefault("layer", "orchestrator")

        base["row_index"] = self._row_index
        base["prev_hash"] = self._prev_hash
        base["key_id"] = self.key_id
        base["chain_id"] = self.chain_id
        base["hash_alg"] = "HMAC-SHA256"

        row_hash = _hmac_sha256_hex(self.hmac_key, _canonical_json_bytes(base))
        base["row_hash"] = row_hash

        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(base, ensure_ascii=False, sort_keys=True) + "\n")

        self._prev_hash = row_hash
        self._row_index += 1


def _read_jsonl_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as err:
                raise IntegrityError(f"JSONL parse failed at {path}:{line_no}: {err}") from err
            if not isinstance(obj, dict):
                raise IntegrityError(f"JSONL row is not an object at {path}:{line_no}")
            rows.append(obj)

    return rows


def verify_audit_hash_chain(path: Path, hmac_key: bytes) -> Tuple[str, int]:
    """
    Verify the audit log hash chain.

    Returns:
    - last row_hash
    - row count
    """
    rows = _read_jsonl_rows(path)
    prev = GENESIS_HASH

    for expected_index, row in enumerate(rows):
        stored_hash = str(row.get("row_hash", ""))
        stored_prev = str(row.get("prev_hash", ""))

        if stored_prev != prev:
            raise IntegrityError(
                f"Audit prev_hash mismatch at row {expected_index}: "
                f"expected {prev}, got {stored_prev}"
            )

        if row.get("row_index") != expected_index:
            raise IntegrityError(
                f"Audit row_index mismatch at row {expected_index}: "
                f"got {row.get('row_index')}"
            )

        body = dict(row)
        body.pop("row_hash", None)
        recomputed = _hmac_sha256_hex(hmac_key, _canonical_json_bytes(body))

        if not hmac.compare_digest(stored_hash, recomputed):
            raise IntegrityError(
                f"Audit row_hash mismatch at row {expected_index}"
            )

        prev = stored_hash

    return prev, len(rows)


def _emit_gate_row(
    audit: AuditLog,
    *,
    run_id: str,
    layer: str,
    decision: Decision,
    reason_code: str,
    task_id: Optional[str] = None,
    kind: Optional[KIND] = None,
    final_decider: FinalDecider = "SYSTEM",
    overrideable: Optional[bool] = None,
    sealed: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if overrideable is None:
        overrideable = decision == "PAUSE_FOR_HITL" and not sealed

    row: Dict[str, Any] = {
        "run_id": run_id,
        "event": "GATE",
        "layer": layer,
        "decision": decision,
        "reason_code": reason_code,
        "sealed": sealed,
        "overrideable": overrideable,
        "final_decider": final_decider,
    }

    if task_id is not None:
        row["task_id"] = task_id
    if kind is not None:
        row["kind"] = kind
    if extra:
        row.update(extra)

    audit.emit(row)


# -----------------------------
# Token estimate
# -----------------------------
def _rough_token_count_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 3.2))


def _estimate_complexity(
    *,
    task_count: int,
    output_mode: str,
    prohibited_actions_count: int,
    completion_criteria_count: int,
) -> str:
    score = task_count

    if output_mode in {"full_code", "unified_diff"}:
        score += 3
    elif output_mode == "artifact":
        score += 2
    else:
        score += 1

    if prohibited_actions_count >= 8:
        score += 2
    elif prohibited_actions_count >= 4:
        score += 1

    if completion_criteria_count >= 5:
        score += 2
    elif completion_criteria_count >= 3:
        score += 1

    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _estimate_hitl_probability(
    *,
    require_task_contract: bool,
    missing_fields_count: int,
    invalid_fields_count: int,
    prohibited_actions_count: int,
    output_mode: str,
) -> str:
    if missing_fields_count or invalid_fields_count:
        return "high"

    score = 0
    if require_task_contract:
        score += 1
    if prohibited_actions_count >= 8:
        score += 2
    elif prohibited_actions_count >= 4:
        score += 1
    if output_mode in {"full_code", "unified_diff"}:
        score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def estimate_token_usage(
    *,
    prompt: str,
    task_contract: Optional[Dict[str, Any]],
    task_count: int,
    require_task_contract: bool,
    missing_fields_count: int = 0,
    invalid_fields_count: int = 0,
) -> TokenEstimate:
    contract_text = ""
    output_mode = "artifact"
    prohibited_actions_count = 0
    completion_criteria_count = 0

    if isinstance(task_contract, dict):
        contract_text = json.dumps(task_contract, ensure_ascii=False, sort_keys=True)

        raw_output_mode = task_contract.get("output_mode")
        if isinstance(raw_output_mode, str) and raw_output_mode.strip():
            output_mode = raw_output_mode.strip()

        prohibited_actions = task_contract.get("prohibited_actions")
        if isinstance(prohibited_actions, list):
            prohibited_actions_count = len(
                [item for item in prohibited_actions if isinstance(item, str)]
            )

        completion_criteria = task_contract.get("completion_criteria")
        if isinstance(completion_criteria, list):
            completion_criteria_count = len(
                [item for item in completion_criteria if isinstance(item, str)]
            )

    input_tokens = (
        _rough_token_count_from_text(prompt)
        + _rough_token_count_from_text(contract_text)
        + 250
    )

    base_min, base_max = OUTPUT_MODE_BASE_RANGE.get(
        output_mode,
        OUTPUT_MODE_BASE_RANGE["artifact"],
    )

    task_multiplier = max(1.0, task_count / 3.0)
    criteria_add = completion_criteria_count * 80
    prohibition_add = prohibited_actions_count * 45

    output_min = math.ceil(base_min * task_multiplier + criteria_add + prohibition_add)
    output_max = math.ceil(base_max * task_multiplier + criteria_add + prohibition_add)
    output_mid = math.ceil((output_min + output_max) / 2)

    total_min = input_tokens + output_min
    total_max = input_tokens + output_max
    total_mid = input_tokens + output_mid

    complexity = _estimate_complexity(
        task_count=task_count,
        output_mode=output_mode,
        prohibited_actions_count=prohibited_actions_count,
        completion_criteria_count=completion_criteria_count,
    )

    hitl_probability = _estimate_hitl_probability(
        require_task_contract=require_task_contract,
        missing_fields_count=missing_fields_count,
        invalid_fields_count=invalid_fields_count,
        prohibited_actions_count=prohibited_actions_count,
        output_mode=output_mode,
    )

    return TokenEstimate(
        estimated_input_tokens=input_tokens,
        estimated_output_tokens_min=output_min,
        estimated_output_tokens_max=output_max,
        estimated_output_tokens_mid=output_mid,
        estimated_total_tokens_min=total_min,
        estimated_total_tokens_max=total_max,
        estimated_total_tokens_mid=total_mid,
        complexity=complexity,
        hitl_probability=hitl_probability,
        confidence="rough",
        basis=[
            "prompt_length",
            "task_contract_length",
            "task_count",
            "output_mode",
            "completion_criteria_count",
            "prohibited_actions_count",
        ],
        disclaimer=(
            "This is a rough estimate only. It is not an actual model token count "
            "and does not guarantee billing or runtime cost."
        ),
    )


# -----------------------------
# Task Contract Gate
# -----------------------------
def _normalize_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    out: List[str] = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                out.append(item)
    return out


def _validate_task_contract(
    task_contract: Optional[Dict[str, Any]],
    *,
    prompt: str,
    task_count: int,
    require_task_contract: bool,
) -> TaskContractResult:
    if task_contract is None:
        estimate = estimate_token_usage(
            prompt=prompt,
            task_contract=None,
            task_count=task_count,
            require_task_contract=require_task_contract,
            missing_fields_count=4 if require_task_contract else 0,
        )

        if require_task_contract:
            return TaskContractResult(
                decision="PAUSE_FOR_HITL",
                reason_code="TASK_CONTRACT_REQUIRED",
                normalized_contract=None,
                missing_fields=[
                    "priority_order",
                    "prohibited_actions",
                    "output_mode",
                    "completion_criteria",
                ],
                invalid_fields=[],
                unknown_prohibitions=[],
                token_estimate=estimate,
            )

        return TaskContractResult(
            decision="RUN",
            reason_code="TASK_CONTRACT_NOT_REQUIRED",
            normalized_contract=None,
            missing_fields=[],
            invalid_fields=[],
            unknown_prohibitions=[],
            token_estimate=estimate,
        )

    if not isinstance(task_contract, dict):
        estimate = estimate_token_usage(
            prompt=prompt,
            task_contract=None,
            task_count=task_count,
            require_task_contract=require_task_contract,
            invalid_fields_count=1,
        )
        return TaskContractResult(
            decision="PAUSE_FOR_HITL",
            reason_code="TASK_CONTRACT_INVALID",
            normalized_contract=None,
            missing_fields=[],
            invalid_fields=["task_contract"],
            unknown_prohibitions=[],
            token_estimate=estimate,
        )

    priority_order = _normalize_str_list(task_contract.get("priority_order"))
    prohibited_actions = _normalize_str_list(task_contract.get("prohibited_actions"))
    completion_criteria = _normalize_str_list(task_contract.get("completion_criteria"))
    output_mode_raw = task_contract.get("output_mode")
    output_mode = str(output_mode_raw).strip() if output_mode_raw is not None else ""

    missing_fields: List[str] = []
    invalid_fields: List[str] = []

    if not priority_order:
        missing_fields.append("priority_order")
    if not prohibited_actions:
        missing_fields.append("prohibited_actions")
    if not output_mode:
        missing_fields.append("output_mode")
    if not completion_criteria:
        missing_fields.append("completion_criteria")

    if output_mode and output_mode not in ALLOWED_OUTPUT_MODES:
        invalid_fields.append("output_mode")

    unknown_prohibitions = [
        item for item in prohibited_actions if item not in KNOWN_PROHIBITED_ACTIONS
    ]

    estimate = estimate_token_usage(
        prompt=prompt,
        task_contract=task_contract,
        task_count=task_count,
        require_task_contract=require_task_contract,
        missing_fields_count=len(missing_fields),
        invalid_fields_count=len(invalid_fields),
    )

    if missing_fields:
        if "priority_order" in missing_fields:
            reason_code = "TASK_CONTRACT_PRIORITY_MISSING"
        elif "prohibited_actions" in missing_fields:
            reason_code = "TASK_CONTRACT_PROHIBITION_MISSING"
        elif "completion_criteria" in missing_fields:
            reason_code = "TASK_CONTRACT_COMPLETION_CRITERIA_MISSING"
        else:
            reason_code = "TASK_CONTRACT_REQUIRED"

        return TaskContractResult(
            decision="PAUSE_FOR_HITL",
            reason_code=reason_code,
            normalized_contract=None,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            unknown_prohibitions=unknown_prohibitions,
            token_estimate=estimate,
        )

    if invalid_fields:
        reason_code = (
            "TASK_CONTRACT_OUTPUT_MODE_INVALID"
            if "output_mode" in invalid_fields
            else "TASK_CONTRACT_INVALID"
        )
        return TaskContractResult(
            decision="PAUSE_FOR_HITL",
            reason_code=reason_code,
            normalized_contract=None,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            unknown_prohibitions=unknown_prohibitions,
            token_estimate=estimate,
        )

    normalized = {
        "priority_order": priority_order,
        "prohibited_actions": prohibited_actions,
        "output_mode": output_mode,
        "completion_criteria": completion_criteria,
        "unknown_prohibitions": unknown_prohibitions,
    }

    return TaskContractResult(
        decision="RUN",
        reason_code="TASK_CONTRACT_CONFIRMED",
        normalized_contract=normalized,
        missing_fields=[],
        invalid_fields=[],
        unknown_prohibitions=unknown_prohibitions,
        token_estimate=estimate,
    )


def _task_contract_gate(
    audit: AuditLog,
    *,
    run_id: str,
    prompt: str,
    task_contract: Optional[Dict[str, Any]],
    require_task_contract: bool,
    task_count: int,
) -> TaskContractResult:
    result = _validate_task_contract(
        task_contract,
        prompt=prompt,
        task_count=task_count,
        require_task_contract=require_task_contract,
    )

    estimate_dict = asdict(result.token_estimate)

    _emit_gate_row(
        audit,
        run_id=run_id,
        layer="task_contract_gate",
        decision=result.decision,
        reason_code=result.reason_code,
        sealed=False,
        overrideable=result.decision == "PAUSE_FOR_HITL",
        final_decider="SYSTEM",
        extra={
            "missing_fields": result.missing_fields,
            "invalid_fields": result.invalid_fields,
            "unknown_prohibitions": result.unknown_prohibitions,
            "has_task_contract": task_contract is not None,
            "token_estimate": estimate_dict,
        },
    )

    audit.emit(
        {
            "run_id": run_id,
            "event": "TOKEN_ESTIMATE",
            "layer": "token_estimate",
            "decision": "RUN",
            "reason_code": "TOKEN_ESTIMATE_ROUGH",
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "token_estimate": estimate_dict,
        }
    )

    if result.decision == "RUN" and result.normalized_contract is not None:
        _emit_gate_row(
            audit,
            run_id=run_id,
            layer="hitl_finalize",
            decision="RUN",
            reason_code="TASK_CONTRACT_CONFIRMED",
            sealed=False,
            overrideable=False,
            final_decider="USER",
            extra={
                "task_contract": result.normalized_contract,
                "token_estimate": estimate_dict,
            },
        )

    return result


# -----------------------------
# Checkpoint integrity
# -----------------------------
def _default_checkpoint_path(run_id: str) -> str:
    return str(Path("out/checkpoints") / f"{_safe_filename(run_id)}.checkpoint.json")


def _checkpoint_body_for_hmac(checkpoint: RunCheckpoint) -> Dict[str, Any]:
    body = asdict(checkpoint)
    body.pop("checkpoint_hmac", None)
    body = _deep_redact(body)
    return body


def _compute_checkpoint_hmac(checkpoint: RunCheckpoint, hmac_key: bytes) -> str:
    body = _checkpoint_body_for_hmac(checkpoint)
    return _hmac_sha256_hex(hmac_key, _canonical_json_bytes(body))


def _save_checkpoint(path: str, checkpoint: RunCheckpoint, hmac_key: bytes) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint.checkpoint_hmac = None
    checkpoint.checkpoint_hmac = _compute_checkpoint_hmac(checkpoint, hmac_key)

    out_path.write_text(
        json.dumps(_deep_redact(asdict(checkpoint)), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _task_checkpoint_from_dict(obj: Dict[str, Any]) -> TaskCheckpoint:
    return TaskCheckpoint(
        task_id=str(obj.get("task_id", "")),
        kind=obj.get("kind", "word"),
        status=obj.get("status", "NOT_STARTED"),
        last_completed_layer=obj.get("last_completed_layer"),
        failed_layer=obj.get("failed_layer"),
        reason_code=str(obj.get("reason_code", "")),
        artifact_path=obj.get("artifact_path"),
        artifact_sha256=obj.get("artifact_sha256"),
        artifact_hmac=obj.get("artifact_hmac"),
        resume_allowed=bool(obj.get("resume_allowed", True)),
        requires_hitl_before_resume=bool(obj.get("requires_hitl_before_resume", False)),
    )


def _run_checkpoint_from_dict(obj: Dict[str, Any]) -> RunCheckpoint:
    tasks_raw = obj.get("tasks", [])
    tasks = [
        _task_checkpoint_from_dict(item)
        for item in tasks_raw
        if isinstance(item, dict)
    ]

    return RunCheckpoint(
        checkpoint_version=str(obj.get("checkpoint_version", "1.0")),
        run_id=str(obj.get("run_id", "")),
        status=str(obj.get("status", "RUNNING")),
        resume_mode=str(obj.get("resume_mode", "FROM_TASK_CHECKPOINT")),
        current_task_id=obj.get("current_task_id"),
        failed_task_id=obj.get("failed_task_id"),
        failed_layer=obj.get("failed_layer"),
        reason_code=str(obj.get("reason_code", "")),
        key_id=str(obj.get("key_id", "default")),
        hash_alg=str(obj.get("hash_alg", "HMAC-SHA256")),
        tasks=tasks,
        token_estimate=obj.get("token_estimate"),
        checkpoint_hmac=obj.get("checkpoint_hmac"),
    )


def _load_checkpoint(path: str, hmac_key: bytes) -> Optional[RunCheckpoint]:
    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        return None

    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except Exception as err:
        raise IntegrityError(f"Checkpoint parse failed: {checkpoint_path}") from err

    if not isinstance(data, dict):
        raise IntegrityError(f"Checkpoint is not an object: {checkpoint_path}")

    checkpoint = _run_checkpoint_from_dict(data)
    stored = checkpoint.checkpoint_hmac
    checkpoint.checkpoint_hmac = None
    recomputed = _compute_checkpoint_hmac(checkpoint, hmac_key)
    checkpoint.checkpoint_hmac = stored

    if not stored or not hmac.compare_digest(stored, recomputed):
        raise IntegrityError("Checkpoint HMAC mismatch")

    return checkpoint


def _new_run_checkpoint(run_id: str, *, key_id: str) -> RunCheckpoint:
    return RunCheckpoint(
        checkpoint_version="1.0",
        run_id=run_id,
        status="RUNNING",
        resume_mode="FROM_TASK_CHECKPOINT",
        current_task_id=None,
        failed_task_id=None,
        failed_layer=None,
        reason_code="CHECKPOINT_INITIALIZED",
        key_id=key_id,
        hash_alg="HMAC-SHA256",
        tasks=[
            TaskCheckpoint(task_id=task_id, kind=kind)
            for task_id, kind in _TASKS
        ],
        token_estimate=None,
        checkpoint_hmac=None,
    )


def _find_task_checkpoint(
    checkpoint: RunCheckpoint,
    task_id: str,
) -> Optional[TaskCheckpoint]:
    for task in checkpoint.tasks:
        if task.task_id == task_id:
            return task
    return None


def _set_task_running(checkpoint: RunCheckpoint, task_id: str, kind: KIND) -> None:
    task = _find_task_checkpoint(checkpoint, task_id)
    if task is None:
        task = TaskCheckpoint(task_id=task_id, kind=kind)
        checkpoint.tasks.append(task)

    task.status = "RUNNING"
    task.failed_layer = None
    task.reason_code = "TASK_RUNNING"
    task.resume_allowed = True
    task.requires_hitl_before_resume = False

    checkpoint.status = "RUNNING"
    checkpoint.current_task_id = task_id
    checkpoint.reason_code = "TASK_RUNNING"


def _set_task_completed(
    checkpoint: RunCheckpoint,
    *,
    task_id: str,
    artifact_path: str,
    artifact_sha256: str,
    artifact_hmac: str,
) -> None:
    task = _find_task_checkpoint(checkpoint, task_id)
    if task is None:
        return

    task.status = "COMPLETED"
    task.last_completed_layer = "orchestrator"
    task.failed_layer = None
    task.reason_code = "ARTIFACT_WRITTEN"
    task.artifact_path = artifact_path
    task.artifact_sha256 = artifact_sha256
    task.artifact_hmac = artifact_hmac
    task.resume_allowed = False
    task.requires_hitl_before_resume = False

    checkpoint.current_task_id = task_id
    checkpoint.reason_code = "TASK_COMPLETED"


def _set_task_interrupted(
    checkpoint: RunCheckpoint,
    *,
    task_id: str,
    failed_layer: str,
    reason_code: str,
    requires_hitl_before_resume: bool = True,
    resume_allowed: bool = True,
) -> None:
    task = _find_task_checkpoint(checkpoint, task_id)
    if task is None:
        return

    task.status = "WAITING_FOR_HITL" if requires_hitl_before_resume else "INTERRUPTED"
    task.failed_layer = failed_layer
    task.reason_code = reason_code
    task.resume_allowed = resume_allowed
    task.requires_hitl_before_resume = requires_hitl_before_resume

    checkpoint.status = "INTERRUPTED"
    checkpoint.current_task_id = task_id
    checkpoint.failed_task_id = task_id
    checkpoint.failed_layer = failed_layer
    checkpoint.reason_code = reason_code


def _checkpoint_requires_resume_hitl(checkpoint: RunCheckpoint) -> bool:
    return any(
        task.status in {"WAITING_FOR_HITL", "INTERRUPTED"}
        and task.requires_hitl_before_resume
        for task in checkpoint.tasks
    )


def _checkpoint_task_results(checkpoint: RunCheckpoint) -> List[TaskResult]:
    results: List[TaskResult] = []

    for task in checkpoint.tasks:
        if task.status == "COMPLETED":
            results.append(
                TaskResult(
                    task_id=task.task_id,
                    kind=task.kind,
                    decision="RUN",
                    blocked_layer=None,
                    reason_code="CHECKPOINT_COMPLETED",
                    artifact_path=task.artifact_path,
                )
            )
        elif task.status in {"WAITING_FOR_HITL", "INTERRUPTED"}:
            results.append(
                TaskResult(
                    task_id=task.task_id,
                    kind=task.kind,
                    decision="PAUSE_FOR_HITL",
                    blocked_layer="checkpoint_gate",
                    reason_code=task.reason_code,
                    artifact_path=task.artifact_path,
                )
            )

    return results


def _all_tasks_completed(checkpoint: RunCheckpoint) -> bool:
    expected = {task_id for task_id, _ in _TASKS}
    completed = {
        task.task_id
        for task in checkpoint.tasks
        if task.status == "COMPLETED"
    }
    return expected.issubset(completed)


# -----------------------------
# Artifact integrity
# -----------------------------
def _artifact_hmac_for_bytes(
    *,
    hmac_key: bytes,
    run_id: str,
    task_id: str,
    artifact_bytes: bytes,
) -> str:
    body = {
        "run_id": run_id,
        "task_id": task_id,
        "artifact_sha256": _sha256_hex_bytes(artifact_bytes),
    }
    return _hmac_sha256_hex(hmac_key, _canonical_json_bytes(body))


def _verify_completed_artifacts(
    checkpoint: RunCheckpoint,
    *,
    hmac_key: bytes,
    run_id: str,
) -> None:
    for task in checkpoint.tasks:
        if task.status != "COMPLETED":
            continue

        if not task.artifact_path:
            raise IntegrityError(f"Completed task has no artifact path: {task.task_id}")

        artifact_path = Path(task.artifact_path)
        if not artifact_path.exists():
            raise IntegrityError(f"Artifact missing: {artifact_path}")

        data = artifact_path.read_bytes()
        sha = _sha256_hex_bytes(data)
        artifact_hmac = _artifact_hmac_for_bytes(
            hmac_key=hmac_key,
            run_id=run_id,
            task_id=task.task_id,
            artifact_bytes=data,
        )

        if not task.artifact_sha256 or not hmac.compare_digest(task.artifact_sha256, sha):
            raise IntegrityError(f"Artifact SHA-256 mismatch: {task.task_id}")

        if not task.artifact_hmac or not hmac.compare_digest(task.artifact_hmac, artifact_hmac):
            raise IntegrityError(f"Artifact HMAC mismatch: {task.task_id}")


# -----------------------------
# Gates and agents
# -----------------------------
def _is_action_prohibited(
    normalized_contract: Optional[Dict[str, Any]],
    action: str,
) -> bool:
    if not normalized_contract:
        return False

    prohibited = normalized_contract.get("prohibited_actions")
    if not isinstance(prohibited, list):
        return False

    return action in prohibited


_KIND_TOKENS: Dict[KIND, List[str]] = {
    "excel": ["excel", "xlsx", "表", "列", "columns", "table"],
    "word": ["word", "docx", "見出し", "章", "アウトライン", "outline", "document"],
    "ppt": ["ppt", "pptx", "powerpoint", "スライド", "slides", "slide"],
}


def _prompt_mentions_any_kind(prompt: str) -> bool:
    prompt_lower = (prompt or "").lower()

    for tokens in _KIND_TOKENS.values():
        for token in tokens:
            if token.lower() in prompt_lower:
                return True

    return False


def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[str], str]:
    prompt_text = prompt or ""
    prompt_lower = prompt_text.lower()

    any_kind = _prompt_mentions_any_kind(prompt_text)
    if not any_kind:
        return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"

    tokens = _KIND_TOKENS[kind]
    if any(token.lower() in prompt_lower for token in tokens):
        return "RUN", None, "MEANING_KIND_MATCH"

    return "PAUSE_FOR_HITL", "meaning_gate", "MEANING_KIND_MISSING"


def _validate_contract(kind: KIND, draft: Dict[str, Any]) -> Tuple[bool, str]:
    if kind == "excel":
        columns = draft.get("columns")
        rows = draft.get("rows")

        if not (
            isinstance(columns, list)
            and all(isinstance(item, str) for item in columns)
        ):
            return False, "CONTRACT_EXCEL_COLUMNS_INVALID"

        if not (
            isinstance(rows, list)
            and all(isinstance(item, dict) for item in rows)
        ):
            return False, "CONTRACT_EXCEL_ROWS_INVALID"

        return True, "CONTRACT_OK"

    if kind == "word":
        headings = draft.get("headings")
        if not (
            isinstance(headings, list)
            and all(isinstance(item, str) for item in headings)
        ):
            return False, "CONTRACT_WORD_HEADINGS_INVALID"
        return True, "CONTRACT_OK"

    if kind == "ppt":
        slides = draft.get("slides")
        if not (
            isinstance(slides, list)
            and all(isinstance(item, str) for item in slides)
        ):
            return False, "CONTRACT_PPT_SLIDES_INVALID"
        return True, "CONTRACT_OK"

    return False, "CONTRACT_UNKNOWN_KIND"


def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
    if EMAIL_RE.search(raw_text or ""):
        return True, "ETHICS_EMAIL_DETECTED"
    return False, "ETHICS_OK"


def _agent_generate(
    prompt: str,
    kind: KIND,
    faults: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, str]:
    _ = prompt

    leak_email = bool((faults or {}).get("leak_email"))
    break_contract = bool((faults or {}).get("break_contract"))

    if kind == "excel":
        draft: Dict[str, Any] = {
            "columns": ["Item", "Owner", "Status"],
            "rows": [
                {"Item": "Task A", "Owner": "Team", "Status": "In Progress"},
                {"Item": "Task B", "Owner": "Team", "Status": "Planned"},
            ],
        }
        raw_text = "Excel Table:\n- Columns: Item | Owner | Status\n- Rows: 2\n"
    elif kind == "word":
        draft = {"headings": ["Title", "Purpose", "Summary", "Next Steps"]}
        raw_text = "Word Outline:\n1) Title\n2) Purpose\n3) Summary\n4) Next Steps\n"
    elif kind == "ppt":
        draft = {"slides": ["Purpose", "Key Points", "Next Steps"]}
        raw_text = (
            "PPT Slides:\n"
            "- Slide 1: Purpose\n"
            "- Slide 2: Key Points\n"
            "- Slide 3: Next Steps\n"
        )
    else:
        draft = {"note": "unknown kind"}
        raw_text = "Unknown kind\n"

    if break_contract:
        if kind == "excel":
            draft = {"cols": "Item,Owner,Status"}
        elif kind == "word":
            draft = {"heading": "Title"}
        elif kind == "ppt":
            draft = {"slides": "Purpose,Key Points"}

    if leak_email:
        raw_text += "\nContact: test.user+demo@example.com\n"

    safe_text = redact_sensitive(raw_text)
    return draft, raw_text, safe_text


def _artifact_ext(kind: KIND) -> str:
    if kind == "excel":
        return "xlsx"
    if kind == "word":
        return "docx"
    if kind == "ppt":
        return "pptx"
    return "txt"


def _write_artifact(
    artifact_dir: Path,
    task_id: str,
    kind: KIND,
    safe_text: str,
) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
    path.write_text(redact_sensitive(safe_text), encoding="utf-8")
    return path


# -----------------------------
# Main orchestration
# -----------------------------
def _pause_for_tamper(
    *,
    run_id: str,
    checkpoint_path: Optional[str],
    detail: str,
) -> SimulationResult:
    return SimulationResult(
        run_id=run_id,
        decision="PAUSE_FOR_HITL",
        tasks=[],
        artifacts_written_task_ids=[],
        token_estimate=None,
        checkpoint_path=checkpoint_path,
        integrity_status=f"TAMPER_EVIDENCE_DETECTED: {detail}",
    )


def run_simulation(
    *,
    prompt: str,
    run_id: str,
    audit_path: str,
    artifact_dir: str,
    hmac_key: bytes,
    key_id: str = "default",
    chain_id: str = "doc-orchestrator",
    faults: Optional[Dict[str, Dict[str, Any]]] = None,
    task_contract: Optional[Dict[str, Any]] = None,
    require_task_contract: bool = False,
    checkpoint_path: Optional[str] = None,
    resume_from_checkpoint: bool = False,
    resume_confirmed: bool = False,
    stop_on_interruption: bool = True,
) -> SimulationResult:
    """
    Run the simulator with a fixed task set: word/excel/ppt.

    Production-oriented integrity behavior:
    - Audit log is HMAC-chained.
    - Existing audit chain is verified before append.
    - Checkpoint file is HMAC-protected.
    - Completed artifacts are verified on resume.
    - Tamper evidence leads to PAUSE_FOR_HITL.
    """
    faults = faults or {}
    checkpoint_path = checkpoint_path or _default_checkpoint_path(run_id)

    try:
        audit = AuditLog(
            Path(audit_path),
            hmac_key=hmac_key,
            key_id=key_id,
            chain_id=chain_id,
            verify_existing=True,
        )
    except IntegrityError as err:
        return _pause_for_tamper(
            run_id=run_id,
            checkpoint_path=checkpoint_path,
            detail=str(err),
        )

    out_dir = Path(artifact_dir)
    checkpoint: Optional[RunCheckpoint] = None

    if resume_from_checkpoint:
        try:
            checkpoint = _load_checkpoint(checkpoint_path, hmac_key)
            if checkpoint is not None:
                if checkpoint.run_id != run_id:
                    raise IntegrityError("Checkpoint run_id mismatch")
                _verify_completed_artifacts(
                    checkpoint,
                    hmac_key=hmac_key,
                    run_id=run_id,
                )
        except IntegrityError as err:
            _emit_gate_row(
                audit,
                run_id=run_id,
                layer="integrity_gate",
                decision="PAUSE_FOR_HITL",
                reason_code="TAMPER_EVIDENCE_DETECTED",
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                extra={
                    "checkpoint_path": checkpoint_path,
                    "integrity_error": str(err),
                },
            )
            return _pause_for_tamper(
                run_id=run_id,
                checkpoint_path=checkpoint_path,
                detail=str(err),
            )

        if checkpoint is not None:
            audit.emit(
                {
                    "run_id": run_id,
                    "event": "CHECKPOINT_LOADED",
                    "layer": "checkpoint_gate",
                    "decision": "RUN",
                    "reason_code": "CHECKPOINT_HASH_VERIFIED",
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
                }
            )

    if checkpoint is None:
        checkpoint = _new_run_checkpoint(run_id, key_id=key_id)
        _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

        audit.emit(
            {
                "run_id": run_id,
                "event": "CHECKPOINT_INITIALIZED",
                "layer": "checkpoint_gate",
                "decision": "RUN",
                "reason_code": "CHECKPOINT_HASH_WRITTEN",
                "checkpoint_path": checkpoint_path,
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

    if resume_from_checkpoint and _checkpoint_requires_resume_hitl(checkpoint):
        if not resume_confirmed:
            _emit_gate_row(
                audit,
                run_id=run_id,
                layer="checkpoint_gate",
                decision="PAUSE_FOR_HITL",
                reason_code="RESUME_REQUIRES_HITL_CONFIRMATION",
                sealed=False,
                overrideable=True,
                final_decider="SYSTEM",
                extra={"checkpoint_path": checkpoint_path},
            )
            return SimulationResult(
                run_id=run_id,
                decision="PAUSE_FOR_HITL",
                tasks=_checkpoint_task_results(checkpoint),
                artifacts_written_task_ids=[],
                token_estimate=None,
                checkpoint_path=checkpoint_path,
                integrity_status="VERIFIED",
            )

        _emit_gate_row(
            audit,
            run_id=run_id,
            layer="hitl_finalize",
            decision="RUN",
            reason_code="RESUME_FROM_CHECKPOINT_CONFIRMED",
            sealed=False,
            overrideable=False,
            final_decider="USER",
            extra={"checkpoint_path": checkpoint_path},
        )

    contract_result = _task_contract_gate(
        audit,
        run_id=run_id,
        prompt=prompt,
        task_contract=task_contract,
        require_task_contract=require_task_contract,
        task_count=len(_TASKS),
    )

    token_estimate = contract_result.token_estimate
    checkpoint.token_estimate = asdict(token_estimate)
    _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

    if contract_result.decision == "PAUSE_FOR_HITL":
        checkpoint.status = "INTERRUPTED"
        checkpoint.failed_layer = "task_contract_gate"
        checkpoint.reason_code = contract_result.reason_code
        _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

        audit.emit(
            {
                "run_id": run_id,
                "event": "RUN_PAUSED",
                "layer": "task_contract_gate",
                "decision": "PAUSE_FOR_HITL",
                "reason_code": contract_result.reason_code,
                "sealed": False,
                "overrideable": True,
                "final_decider": "SYSTEM",
                "checkpoint_path": checkpoint_path,
                "token_estimate": asdict(token_estimate),
            }
        )

        return SimulationResult(
            run_id=run_id,
            decision="PAUSE_FOR_HITL",
            tasks=[],
            artifacts_written_task_ids=[],
            token_estimate=token_estimate,
            checkpoint_path=checkpoint_path,
            integrity_status="VERIFIED",
        )

    normalized_contract = contract_result.normalized_contract
    task_results: List[TaskResult] = []
    artifacts_written: List[str] = []

    for task_id, kind in _TASKS:
        existing = _find_task_checkpoint(checkpoint, task_id)

        if resume_from_checkpoint and existing and existing.status == "COMPLETED":
            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "TASK_SKIPPED_BY_CHECKPOINT",
                    "layer": "checkpoint_gate",
                    "kind": kind,
                    "decision": "RUN",
                    "reason_code": "ARTIFACT_HASH_VERIFIED",
                    "artifact_path": existing.artifact_path,
                    "artifact_sha256": existing.artifact_sha256,
                    "sealed": False,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
                }
            )

            if existing.artifact_path:
                artifacts_written.append(task_id)

            task_results.append(
                TaskResult(
                    task_id=task_id,
                    kind=kind,
                    decision="RUN",
                    blocked_layer=None,
                    reason_code="TASK_ALREADY_COMPLETED",
                    artifact_path=existing.artifact_path,
                )
            )
            continue

        _set_task_running(checkpoint, task_id, kind)
        _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "TASK_ASSIGNED",
                "layer": "orchestrator",
                "kind": kind,
                "decision": "RUN",
                "reason_code": "TASK_ASSIGNED",
                "checkpoint_path": checkpoint_path,
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        m_dec, m_layer, m_code = _meaning_gate(prompt, kind)

        _emit_gate_row(
            audit,
            run_id=run_id,
            task_id=task_id,
            kind=kind,
            layer="meaning_gate",
            decision=m_dec,
            reason_code=m_code,
            sealed=False,
            overrideable=m_dec == "PAUSE_FOR_HITL",
            final_decider="SYSTEM",
        )

        if m_dec == "PAUSE_FOR_HITL":
            _set_task_interrupted(
                checkpoint,
                task_id=task_id,
                failed_layer="meaning_gate",
                reason_code=m_code,
                requires_hitl_before_resume=True,
                resume_allowed=True,
            )
            _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

            result = TaskResult(
                task_id=task_id,
                kind=kind,
                decision="PAUSE_FOR_HITL",
                blocked_layer=m_layer,
                reason_code=m_code,
                artifact_path=None,
            )
            task_results.append(result)

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "CHECKPOINT_CREATED_AFTER_INTERRUPTION",
                    "layer": "checkpoint_gate",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": m_code,
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )

            if stop_on_interruption:
                return SimulationResult(
                    run_id=run_id,
                    decision="PAUSE_FOR_HITL",
                    tasks=task_results,
                    artifacts_written_task_ids=artifacts_written,
                    token_estimate=token_estimate,
                    checkpoint_path=checkpoint_path,
                    integrity_status="VERIFIED",
                )
            continue

        draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))

        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "AGENT_OUTPUT",
                "layer": "agent",
                "decision": "RUN",
                "reason_code": "AGENT_OUTPUT_SAFE_PREVIEW",
                "preview": safe_text[:200],
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        ok, c_code = _validate_contract(kind, draft)
        c_dec: Decision = "RUN" if ok else "PAUSE_FOR_HITL"

        _emit_gate_row(
            audit,
            run_id=run_id,
            task_id=task_id,
            kind=kind,
            layer="consistency_gate",
            decision=c_dec,
            reason_code=c_code,
            sealed=False,
            overrideable=c_dec == "PAUSE_FOR_HITL",
            final_decider="SYSTEM",
        )

        if not ok:
            _set_task_interrupted(
                checkpoint,
                task_id=task_id,
                failed_layer="consistency_gate",
                reason_code=c_code,
                requires_hitl_before_resume=True,
                resume_allowed=True,
            )
            _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "REGEN_REQUESTED",
                    "layer": "orchestrator",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": "REGEN_FOR_CONSISTENCY",
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )

            result = TaskResult(
                task_id=task_id,
                kind=kind,
                decision="PAUSE_FOR_HITL",
                blocked_layer="consistency_gate",
                reason_code=c_code,
                artifact_path=None,
            )
            task_results.append(result)

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "CHECKPOINT_CREATED_AFTER_INTERRUPTION",
                    "layer": "checkpoint_gate",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": c_code,
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )

            if stop_on_interruption:
                return SimulationResult(
                    run_id=run_id,
                    decision="PAUSE_FOR_HITL",
                    tasks=task_results,
                    artifacts_written_task_ids=artifacts_written,
                    token_estimate=token_estimate,
                    checkpoint_path=checkpoint_path,
                    integrity_status="VERIFIED",
                )
            continue

        pii_hit, e_code = _ethics_detect_pii(raw_text)
        e_dec: Decision = "STOPPED" if pii_hit else "RUN"

        _emit_gate_row(
            audit,
            run_id=run_id,
            task_id=task_id,
            kind=kind,
            layer="ethics_gate",
            decision=e_dec,
            reason_code=e_code,
            sealed=False,
            overrideable=False,
            final_decider="SYSTEM",
        )

        if pii_hit:
            _set_task_interrupted(
                checkpoint,
                task_id=task_id,
                failed_layer="ethics_gate",
                reason_code=e_code,
                requires_hitl_before_resume=True,
                resume_allowed=True,
            )
            _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

            result = TaskResult(
                task_id=task_id,
                kind=kind,
                decision="STOPPED",
                blocked_layer="ethics_gate",
                reason_code=e_code,
                artifact_path=None,
            )
            task_results.append(result)

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "CHECKPOINT_CREATED_AFTER_INTERRUPTION",
                    "layer": "checkpoint_gate",
                    "decision": "PAUSE_FOR_HITL",
                    "reason_code": e_code,
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": True,
                    "final_decider": "SYSTEM",
                }
            )

            if stop_on_interruption:
                return SimulationResult(
                    run_id=run_id,
                    decision="PAUSE_FOR_HITL",
                    tasks=task_results,
                    artifacts_written_task_ids=artifacts_written,
                    token_estimate=token_estimate,
                    checkpoint_path=checkpoint_path,
                    integrity_status="VERIFIED",
                )
            continue

        if _is_action_prohibited(normalized_contract, "write_artifacts"):
            reason = "PROHIBITED_ACTION_DETECTED"

            _set_task_interrupted(
                checkpoint,
                task_id=task_id,
                failed_layer="consistency_gate",
                reason_code=reason,
                requires_hitl_before_resume=True,
                resume_allowed=True,
            )
            _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

            result = TaskResult(
                task_id=task_id,
                kind=kind,
                decision="STOPPED",
                blocked_layer="consistency_gate",
                reason_code=reason,
                artifact_path=None,
            )
            task_results.append(result)

            audit.emit(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "event": "PROHIBITED_ACTION_DETECTED",
                    "layer": "consistency_gate",
                    "decision": "STOPPED",
                    "reason_code": reason,
                    "prohibited_action": "write_artifacts",
                    "checkpoint_path": checkpoint_path,
                    "sealed": False,
                    "overrideable": False,
                    "final_decider": "SYSTEM",
                }
            )

            if stop_on_interruption:
                return SimulationResult(
                    run_id=run_id,
                    decision="PAUSE_FOR_HITL",
                    tasks=task_results,
                    artifacts_written_task_ids=artifacts_written,
                    token_estimate=token_estimate,
                    checkpoint_path=checkpoint_path,
                    integrity_status="VERIFIED",
                )
            continue

        artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
        artifact_bytes = artifact_path.read_bytes()
        artifact_sha256 = _sha256_hex_bytes(artifact_bytes)
        artifact_hmac = _artifact_hmac_for_bytes(
            hmac_key=hmac_key,
            run_id=run_id,
            task_id=task_id,
            artifact_bytes=artifact_bytes,
        )
        artifacts_written.append(task_id)

        _set_task_completed(
            checkpoint,
            task_id=task_id,
            artifact_path=str(artifact_path),
            artifact_sha256=artifact_sha256,
            artifact_hmac=artifact_hmac,
        )
        _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "ARTIFACT_WRITTEN",
                "layer": "orchestrator",
                "decision": "RUN",
                "reason_code": "ARTIFACT_HASH_WRITTEN",
                "artifact_path": str(artifact_path),
                "artifact_sha256": artifact_sha256,
                "artifact_hmac": artifact_hmac,
                "checkpoint_path": checkpoint_path,
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        audit.emit(
            {
                "run_id": run_id,
                "task_id": task_id,
                "event": "TASK_CHECKPOINT_SAVED",
                "layer": "checkpoint_gate",
                "decision": "RUN",
                "reason_code": "CHECKPOINT_HASH_WRITTEN",
                "checkpoint_path": checkpoint_path,
                "sealed": False,
                "overrideable": False,
                "final_decider": "SYSTEM",
            }
        )

        task_results.append(
            TaskResult(
                task_id=task_id,
                kind=kind,
                decision="RUN",
                blocked_layer=None,
                reason_code="OK",
                artifact_path=str(artifact_path),
            )
        )

    if _all_tasks_completed(checkpoint):
        checkpoint.status = "COMPLETED"
        checkpoint.current_task_id = None
        checkpoint.failed_task_id = None
        checkpoint.failed_layer = None
        checkpoint.reason_code = "RUN_COMPLETED"
        _save_checkpoint(checkpoint_path, checkpoint, hmac_key)

    overall: Decision = (
        "RUN" if all(task.decision == "RUN" for task in task_results) else "PAUSE_FOR_HITL"
    )

    audit.emit(
        {
            "run_id": run_id,
            "event": "RUN_SUMMARY",
            "layer": "orchestrator",
            "decision": overall,
            "reason_code": "RUN_COMPLETE",
            "tasks_total": len(task_results),
            "artifacts_written_task_ids": artifacts_written,
            "checkpoint_path": checkpoint_path,
            "checkpoint_status": checkpoint.status,
            "sealed": False,
            "overrideable": False,
            "final_decider": "SYSTEM",
            "token_estimate": asdict(token_estimate),
        }
    )

    return SimulationResult(
        run_id=run_id,
        decision=overall,
        tasks=task_results,
        artifacts_written_task_ids=artifacts_written,
        token_estimate=token_estimate,
        checkpoint_path=checkpoint_path,
        integrity_status="VERIFIED",
    )


# -----------------------------
# CLI
# -----------------------------
def _load_task_contract_from_path(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Task contract JSON must be an object.")
    return data


def _build_faults(args: argparse.Namespace) -> Dict[str, Dict[str, Any]]:
    faults: Dict[str, Dict[str, Any]] = {}

    if args.fault_excel_break_contract:
        faults.setdefault("excel", {})["break_contract"] = True
    if args.fault_word_break_contract:
        faults.setdefault("word", {})["break_contract"] = True
    if args.fault_ppt_break_contract:
        faults.setdefault("ppt", {})["break_contract"] = True

    if args.fault_excel_leak_email:
        faults.setdefault("excel", {})["leak_email"] = True
    if args.fault_word_leak_email:
        faults.setdefault("word", {})["leak_email"] = True
    if args.fault_ppt_leak_email:
        faults.setdefault("ppt", {})["leak_email"] = True

    return faults


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Doc orchestrator with HMAC audit chain and checkpoint resume."
    )
    parser.add_argument(
        "--prompt",
        default="Excelで進捗表を作成し、Wordで要約し、PPTでスライドを作成してください。",
    )
    parser.add_argument(
        "--run-id",
        default=f"R#DOC_ORCH_{datetime.now(JST).strftime('%Y%m%d%H%M%S')}",
    )
    parser.add_argument("--audit-path", default=None)
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--checkpoint-path", default=None)
    parser.add_argument("--task-contract", default=None)
    parser.add_argument("--require-task-contract", action="store_true")
    parser.add_argument("--resume-from-checkpoint", action="store_true")
    parser.add_argument("--resume-confirmed", action="store_true")
    parser.add_argument("--stop-on-interruption", action="store_true", default=True)
    parser.add_argument("--continue-on-interruption", action="store_false", dest="stop_on_interruption")
    parser.add_argument("--hmac-key-env", default="DOC_ORCH_HMAC_KEY")
    parser.add_argument("--hmac-key-file", default=None)
    parser.add_argument("--key-id", default="default")
    parser.add_argument("--chain-id", default="doc-orchestrator")
    parser.add_argument("--allow-demo-key", action="store_true")

    parser.add_argument("--fault-excel-break-contract", action="store_true")
    parser.add_argument("--fault-word-break-contract", action="store_true")
    parser.add_argument("--fault-ppt-break-contract", action="store_true")
    parser.add_argument("--fault-excel-leak-email", action="store_true")
    parser.add_argument("--fault-word-leak-email", action="store_true")
    parser.add_argument("--fault-ppt-leak-email", action="store_true")

    args = parser.parse_args(argv)

    hmac_key = load_hmac_key(
        env_var=args.hmac_key_env,
        key_file=args.hmac_key_file,
        allow_demo_key=args.allow_demo_key,
    )

    run_safe = _safe_filename(args.run_id)
    audit_path = args.audit_path or f"out/{run_safe}.audit.jsonl"
    artifact_dir = args.artifact_dir or f"out/{run_safe}_artifacts"
    checkpoint_path = args.checkpoint_path or _default_checkpoint_path(args.run_id)

    task_contract = _load_task_contract_from_path(args.task_contract)
    faults = _build_faults(args)

    result = run_simulation(
        prompt=args.prompt,
        run_id=args.run_id,
        audit_path=audit_path,
        artifact_dir=artifact_dir,
        hmac_key=hmac_key,
        key_id=args.key_id,
        chain_id=args.chain_id,
        faults=faults,
        task_contract=task_contract,
        require_task_contract=args.require_task_contract,
        checkpoint_path=checkpoint_path,
        resume_from_checkpoint=args.resume_from_checkpoint,
        resume_confirmed=args.resume_confirmed,
        stop_on_interruption=args.stop_on_interruption,
    )

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.decision == "RUN" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EMAIL_RE",
    "IntegrityError",
    "AuditLog",
    "SimulationResult",
    "TaskResult",
    "TaskContractResult",
    "TokenEstimate",
    "TaskCheckpoint",
    "RunCheckpoint",
    "estimate_token_usage",
    "load_hmac_key",
    "redact_sensitive",
    "run_simulation",
    "verify_audit_hash_chain",
]
