#!/usr/bin/env python3
"""Strict Phase 5A -> Phase 5B one-time handoff gate (local DRAFT_FIX).

The gate is simulation-only.  A successful claim does not start Phase 5B and
does not grant authority.  Failed claims are irreversible and require review.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


HANDOFF_SCHEMA = "tasukeru.phase5a-to-phase5b.handoff.v0.1"
STOP_RESULT_SCHEMA = "tasukeru.phase5a-to-phase5b.stop-result.v0.1"
MANIFEST_SCHEMA = "tasukeru.phase5a-completion-manifest.v0.1"
MANIFEST_FILENAME = "phase5a_completion_manifest.json"
CONSUMPTION_POLICY = "single_attempt_irreversible"
ARTIFACT_NAMES = (
    "phase5a_result.json",
    "phase5a_source_binding.json",
    "phase5a_report.md",
    "phase5a_verify.json",
)
HANDOFF_KEYS = (
    "schema_version", "handoff_id", "manifest_filename", "manifest_sha256",
    "issued_at_utc", "expires_at_utc", "consumption_policy",
    "simulation_boundary",
)
BOUNDARY_KEYS = (
    "ai_mode", "api_call_performed", "api_key_required",
    "external_ai_provider", "external_network_call", "billable_action",
    "fixture_response_used", "human_review_required",
)
BOUNDARY_VALUE = {
    "ai_mode": "simulated",
    "api_call_performed": False,
    "api_key_required": False,
    "external_ai_provider": None,
    "external_network_call": False,
    "billable_action": False,
    "fixture_response_used": True,
    "human_review_required": True,
}

HANDOFF_MISSING = "STOPPED_PHASE5A_HANDOFF_MISSING"
HANDOFF_INVALID = "STOPPED_PHASE5A_HANDOFF_INVALID"
HANDOFF_EXPIRED = "STOPPED_PHASE5A_HANDOFF_EXPIRED"
HANDOFF_NOT_ISSUED = "STOPPED_PHASE5A_HANDOFF_NOT_ISSUED"
ATTEMPT_ALREADY_USED = "STOPPED_PHASE5A_HANDOFF_ATTEMPT_ALREADY_USED"
CONCURRENT_CLAIM_LOST = "STOPPED_PHASE5A_HANDOFF_CONCURRENT_CLAIM_LOST"
MANIFEST_HASH_MISMATCH = "STOPPED_PHASE5A_MANIFEST_HASH_MISMATCH"
MANIFEST_INVALID = "STOPPED_PHASE5A_MANIFEST_INVALID"
ARTIFACT_INVALID = "STOPPED_PHASE5A_ARTIFACT_INVALID"
CLAIMED = "PHASE5A_HANDOFF_CLAIMED"

REASON_PRECEDENCE = (
    HANDOFF_MISSING, HANDOFF_INVALID, HANDOFF_EXPIRED, HANDOFF_NOT_ISSUED,
    ATTEMPT_ALREADY_USED, CONCURRENT_CLAIM_LOST, MANIFEST_HASH_MISMATCH,
    MANIFEST_INVALID, ARTIFACT_INVALID,
)


class DuplicateKeyError(ValueError):
    pass


@dataclass(frozen=True)
class StopResult:
    schema_version: str
    decision: str
    primary_stop_reason: str
    additional_findings_detected: bool
    additional_finding_count: int
    additional_findings: tuple[str, ...]
    diagnostic_coverage: str
    unexamined_conditions_may_exist: bool
    automatic_retry: bool
    external_side_effect_allowed: bool
    human_review_required: bool

    def to_dict(self) -> dict:
        result = asdict(self)
        result["additional_findings"] = list(self.additional_findings)
        return result


@dataclass(frozen=True)
class ClaimResult:
    decision: str = "CLAIMED"
    reason_code: str = CLAIMED
    phase5b_started: bool = False
    trust_state: str = "UNTRUSTED"
    execution_mode: str = "SIMULATION_ONLY"
    authority_granted: bool = False
    external_side_effect_allowed: bool = False
    automatic_retry: bool = False
    human_review_required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _strict_json(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("BOM prohibited")
    text = raw.decode("utf-8")
    decoder = json.JSONDecoder(object_pairs_hook=_pairs_no_duplicates)
    value, end = decoder.raw_decode(text)
    if text[end:].strip():
        raise ValueError("trailing data")
    if type(value) is not dict:
        raise ValueError("top-level object required")
    return value, raw


def _exact_keys(value: dict, keys: tuple[str, ...]) -> bool:
    return type(value) is dict and set(value) == set(keys)


def _lower_sha256(value) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _parse_utc(value) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("canonical UTC timestamp required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("UTC required")
    return parsed


def _validate_handoff(value: dict) -> dict:
    if not _exact_keys(value, HANDOFF_KEYS):
        raise ValueError("handoff keys")
    if value["schema_version"] != HANDOFF_SCHEMA:
        raise ValueError("schema")
    parsed_uuid = uuid.UUID(value["handoff_id"], version=4)
    if str(parsed_uuid) != value["handoff_id"]:
        raise ValueError("canonical UUID v4")
    if value["manifest_filename"] != MANIFEST_FILENAME:
        raise ValueError("manifest filename")
    if not _lower_sha256(value["manifest_sha256"]):
        raise ValueError("manifest hash")
    issued = _parse_utc(value["issued_at_utc"])
    expires = _parse_utc(value["expires_at_utc"])
    if expires <= issued or (expires - issued).total_seconds() != 900:
        raise ValueError("exact 15 minute lifetime")
    if value["consumption_policy"] != CONSUMPTION_POLICY:
        raise ValueError("consumption policy")
    boundary = value["simulation_boundary"]
    if not _exact_keys(boundary, BOUNDARY_KEYS) or boundary != BOUNDARY_VALUE:
        raise ValueError("simulation boundary")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def initialize_state_db(path: Path | str) -> None:
    """Provision schema. Intended for the Phase 5A emitter/setup path."""
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            "CREATE TABLE IF NOT EXISTS phase5a_handoff_issuances ("
            "handoff_id TEXT PRIMARY KEY, manifest_sha256 TEXT NOT NULL, "
            "issued_at_utc TEXT NOT NULL, expires_at_utc TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS phase5b_handoff_attempts ("
            "handoff_id TEXT PRIMARY KEY, state TEXT NOT NULL, "
            "claimed_at_utc TEXT NOT NULL, primary_stop_reason TEXT);"
        )
        connection.commit()
    finally:
        connection.close()


def record_issuance(path: Path | str, handoff: dict) -> None:
    """Persist Phase 5A issuance before publishing its handoff file."""
    _validate_handoff(handoff)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "INSERT INTO phase5a_handoff_issuances VALUES (?, ?, ?, ?)",
            (handoff["handoff_id"], handoff["manifest_sha256"],
             handoff["issued_at_utc"], handoff["expires_at_utc"]),
        )
        connection.commit()
    finally:
        connection.close()


def _read_only_db(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)


def _issued_exactly(path: Path, handoff: dict) -> bool:
    try:
        connection = _read_only_db(path)
        try:
            row = connection.execute(
                "SELECT manifest_sha256, issued_at_utc, expires_at_utc "
                "FROM phase5a_handoff_issuances WHERE handoff_id = ?",
                (handoff["handoff_id"],),
            ).fetchone()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return False
    return row == (handoff["manifest_sha256"], handoff["issued_at_utc"],
                   handoff["expires_at_utc"])


def _already_used(path: Path, handoff_id: str) -> bool:
    try:
        connection = _read_only_db(path)
        try:
            return connection.execute(
                "SELECT 1 FROM phase5b_handoff_attempts WHERE handoff_id = ?",
                (handoff_id,),
            ).fetchone() is not None
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return False


def _manifest_findings(root: Path, handoff: dict) -> tuple[list[str], bool]:
    findings = []
    path = root / MANIFEST_FILENAME
    try:
        manifest, raw = _strict_json(path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return [MANIFEST_INVALID], False
    if not hmac.compare_digest(_sha256(raw), handoff["manifest_sha256"]):
        findings.append(MANIFEST_HASH_MISMATCH)
    if not _exact_keys(manifest, ("schema_version", "artifacts")):
        findings.append(MANIFEST_INVALID)
        return findings, False
    artifacts = manifest["artifacts"]
    if manifest["schema_version"] != MANIFEST_SCHEMA or not _exact_keys(artifacts, ARTIFACT_NAMES):
        findings.append(MANIFEST_INVALID)
        return findings, False
    all_checked = True
    for name in ARTIFACT_NAMES:
        expected = artifacts[name]
        path = root / name
        if not _lower_sha256(expected) or not path.is_file() or path.is_symlink():
            findings.append(ARTIFACT_INVALID)
            all_checked = False
            continue
        try:
            if not hmac.compare_digest(_sha256(path.read_bytes()), expected):
                findings.append(ARTIFACT_INVALID)
        except OSError:
            findings.append(ARTIFACT_INVALID)
            all_checked = False
    return findings, all_checked


def _stop(primary: str, findings=(), coverage="NONE") -> StopResult:
    unique = sorted(
        {item for item in findings if item != primary},
        key=lambda item: REASON_PRECEDENCE.index(item),
    )
    return StopResult(
        schema_version=STOP_RESULT_SCHEMA,
        decision="STOPPED",
        primary_stop_reason=primary,
        additional_findings_detected=bool(unique),
        additional_finding_count=len(unique),
        additional_findings=tuple(unique),
        diagnostic_coverage=coverage,
        unexamined_conditions_may_exist=True,
        automatic_retry=False,
        external_side_effect_allowed=False,
        human_review_required=True,
    )


def _post_stop_diagnostic(primary: str, root: Path, state: Path,
                          handoff: Optional[dict]) -> StopResult:
    if handoff is None:
        return _stop(primary)
    findings = []
    if not _issued_exactly(state, handoff):
        findings.append(HANDOFF_NOT_ISSUED)
    if _already_used(state, handoff["handoff_id"]):
        findings.append(ATTEMPT_ALREADY_USED)
    manifest_findings, complete = _manifest_findings(root, handoff)
    findings.extend(manifest_findings)
    coverage = "FULL_READ_ONLY_SCOPE" if complete else "PARTIAL_READ_ONLY"
    return _stop(primary, findings, coverage)


def acquire_handoff(
    artifact_root: Path | str,
    handoff_path: Path | str,
    state_db_path: Path | str,
    *,
    now: Optional[datetime] = None,
    _after_begin: Optional[Callable[[], None]] = None,
):
    """Validate, irreversibly claim, then verify one Phase 5A handoff."""
    root, handoff_path, state = map(Path, (artifact_root, handoff_path, state_db_path))
    if not handoff_path.is_file() or handoff_path.is_symlink():
        return _stop(HANDOFF_MISSING)
    try:
        handoff, _ = _strict_json(handoff_path)
        handoff = _validate_handoff(handoff)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return _stop(HANDOFF_INVALID)

    evaluation_time = now or datetime.now(timezone.utc)
    if evaluation_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if evaluation_time.astimezone(timezone.utc) >= _parse_utc(handoff["expires_at_utc"]):
        return _post_stop_diagnostic(HANDOFF_EXPIRED, root, state, handoff)
    if not _issued_exactly(state, handoff):
        return _post_stop_diagnostic(HANDOFF_NOT_ISSUED, root, state, handoff)
    if _already_used(state, handoff["handoff_id"]):
        return _post_stop_diagnostic(ATTEMPT_ALREADY_USED, root, state, handoff)

    connection = sqlite3.connect(state, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA busy_timeout = 0")
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                return _post_stop_diagnostic(CONCURRENT_CLAIM_LOST, root, state, handoff)
            raise
        if _after_begin:
            _after_begin()
        claimed_at = evaluation_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            connection.execute(
                "INSERT INTO phase5b_handoff_attempts VALUES (?, ?, ?, NULL)",
                (handoff["handoff_id"], "ATTEMPT_CLAIMED", claimed_at),
            )
            connection.execute("COMMIT")
        except sqlite3.IntegrityError:
            connection.execute("ROLLBACK")
            return _post_stop_diagnostic(CONCURRENT_CLAIM_LOST, root, state, handoff)
    finally:
        connection.close()

    findings, _ = _manifest_findings(root, handoff)
    if findings:
        primary = next(reason for reason in REASON_PRECEDENCE if reason in findings)
        connection = sqlite3.connect(state)
        try:
            connection.execute(
                "UPDATE phase5b_handoff_attempts SET state = 'CONSUMED_REJECTED', "
                "primary_stop_reason = ? WHERE handoff_id = ? AND state = 'ATTEMPT_CLAIMED'",
                (primary, handoff["handoff_id"]),
            )
            connection.commit()
        finally:
            connection.close()
        return _stop(primary, findings, "FULL_READ_ONLY_SCOPE")

    connection = sqlite3.connect(state)
    try:
        connection.execute(
            "UPDATE phase5b_handoff_attempts SET state = 'CONSUMED_SUCCESS' "
            "WHERE handoff_id = ? AND state = 'ATTEMPT_CLAIMED'",
            (handoff["handoff_id"],),
        )
        connection.commit()
    finally:
        connection.close()
    return ClaimResult()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--state-db", required=True, type=Path)
    args = parser.parse_args()
    result = acquire_handoff(args.artifact_root, args.handoff, args.state_db)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", end="")
    return 0 if isinstance(result, ClaimResult) else 2


if __name__ == "__main__":
    raise SystemExit(main())
