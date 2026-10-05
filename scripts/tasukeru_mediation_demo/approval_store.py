"""DRAFT: local approval-record model for an isolated, report-only experiment.

SQLite is a local concurrency model, NOT a GitHub cross-run approval service.
FixtureAuthority is test data, NOT user authentication. No configuration value
can enable live approval in this draft. A live backend needs a separate review.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class GateStopped(Exception):
    def __init__(self, state, reason):
        self.state, self.reason = state, reason
        super().__init__(reason)


@dataclass(frozen=True)
class FixtureDecision:
    plan_id: str
    plan_sha256: str
    decision: object
    actor: str


class FixtureAuthority:
    """Object identity represents a fixture channel; it authenticates no user."""
    def __init__(self):
        self.issued = []

    def event(self, plan_id, plan_hash, decision="approve", actor="FIXTURE_REVIEWER"):
        item = FixtureDecision(plan_id, plan_hash, decision, actor)
        self.issued.append(item)
        return item

    def recognizes(self, event):
        return isinstance(event, FixtureDecision) and any(x is event for x in self.issued)


class LocalSimulationStore:
    """Each operation opens a new connection; an absent store is not recovered."""
    def __init__(self, path):
        self.path = Path(path)

    @classmethod
    def prepare_new(cls, path):
        obj = cls(path)
        # Exclusive creation also rejects two initializers racing on one path.
        # A partial or corrupt store remains evidence, never an automatic reset.
        with obj.path.open("xb"):
            pass
        with obj.connection() as con:
            con.execute("CREATE TABLE plans (id TEXT PRIMARY KEY, hash TEXT NOT NULL, "
                        "payload BLOB NOT NULL, status TEXT NOT NULL, claims INTEGER NOT NULL, "
                        "result BLOB)")
        return obj

    def connection(self):
        return sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw",
                               uri=True, timeout=2)

    def put(self, plan):
        raw = encode(plan)
        with self.connection() as con:
            con.execute("INSERT INTO plans VALUES (?,?,?,?,?,?)",
                        (plan["plan_id"], digest(raw), raw, plan["initial_state"], 0, None))
        return digest(raw)

    def get(self, plan_id):
        with self.connection() as con:
            row = con.execute("SELECT hash,payload,status,claims,result FROM plans WHERE id=?",
                              (plan_id,)).fetchone()
        if row is None:
            raise GateStopped("STOPPED_PLAN_UNKNOWN", "PLAN_NOT_IN_SIMULATION_STORE")
        expected, raw, state, claims, result = row
        if digest(raw) != expected:
            raise GateStopped("STOPPED_PLAN_UNKNOWN", "STORED_PLAN_DIGEST_MISMATCH")
        return json.loads(raw), expected, state, claims, result

    def decide_once(self, plan_id, plan_hash, decision):
        if decision not in {"approve", "reject", "revise", "stop"}:
            raise GateStopped("STOPPED_DECISION_UNKNOWN", "UNSUPPORTED_USER_DECISION")
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT hash,status,claims FROM plans WHERE id=?", (plan_id,)).fetchone()
            if row is None or row[0] != plan_hash:
                raise GateStopped("STOPPED_BINDING", "APPROVAL_BINDING_MISMATCH")
            if row[1] != "WAITING_FOR_APPROVAL" or row[2]:
                raise GateStopped("DENIED_USED_OR_CLOSED", "PLAN_ALREADY_CLAIMED_OR_CLOSED")
            new_state = {"approve": "CLAIMED", "reject": "REJECTED_BY_HUMAN",
                         "revise": "NEEDS_NEW_PROPOSAL", "stop": "STOPPED_BY_HUMAN"}[decision]
            con.execute("UPDATE plans SET status=?,claims=? WHERE id=?",
                        (new_state, 1 if decision == "approve" else 0, plan_id))
        return new_state

    def finish(self, plan_id, result):
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT status FROM plans WHERE id=?", (plan_id,)).fetchone()
            if row is None:
                raise GateStopped("STOPPED_STORAGE_UNRESOLVED", "PLAN_DISAPPEARED")
            if row[0] == "STOPPED_BY_HUMAN" and result["state"] != "STOPPED_BY_HUMAN":
                raise GateStopped("STOPPED_BY_HUMAN", "STOP_STATE_MUST_NOT_BE_OVERWRITTEN")
            if row[0] not in {"CLAIMED", "STOPPED_BY_HUMAN"}:
                raise GateStopped("DENIED_USED_OR_CLOSED", "TERMINAL_STATE_MUST_NOT_BE_OVERWRITTEN")
            con.execute("UPDATE plans SET status=?,result=? WHERE id=?",
                        (result["state"], encode(result), plan_id))

    def stop_during_request(self, plan_id):
        """Trusted fixture driver only; no real STOP transport exists here."""
        with self.connection() as con:
            changed = con.execute("UPDATE plans SET status='STOPPED_BY_HUMAN' WHERE id=?",
                                  (plan_id,)).rowcount
            if changed != 1:
                raise GateStopped("STOPPED_PLAN_UNKNOWN", "PLAN_NOT_IN_SIMULATION_STORE")

    def close_waiting(self, plan_id, state):
        with self.connection() as con:
            con.execute("UPDATE plans SET status=? WHERE id=? AND status='WAITING_FOR_APPROVAL'",
                        (state, plan_id))


def unavailable_live_response(decision):
    """A dispatch input is a request, never proof of an authenticated approval."""
    valid = type(decision) is str and decision in {"none", "approve", "revise", "reject", "stop"}
    state = "STOPPED_LIVE_APPROVAL_UNCONFIGURED" if valid else "STOPPED_DECISION_UNKNOWN"
    reason = "LIVE_IDENTITY_AND_SHARED_ATOMIC_STORE_NOT_IMPLEMENTED" if valid else "UNSUPPORTED_USER_DECISION"
    if decision == "stop":
        state, reason = "STOPPED_BY_HUMAN_LOCAL_ONLY", "NO_NEW_PROCESSING_REMOTE_CANCELLATION_NOT_CONFIRMED"
    return {"state": state, "reason": reason, "real_AI_calls": 0,
            "mock_generations": 0, "human_authentication_tested": False,
            "approval_accepted": False, "shared_stop_persisted": False,
            "remote_cancellation": "NOT_ATTEMPTED_OR_CONFIRMED",
            "automatic_apply": False, "human_final_adoption": False,
            "original_records_repaired": False}


# STAGE 1 DRAFT: additive storage contract, not connected to the live entry.
# The original fixture API above remains unchanged. No network client, token,
# automatic backend selection, authentication grant, or reset is introduced.
SHARED_RECORD_SCHEMA = "TASUKERU_PROTECTED_RECORD_DRAFT_V1"
SHARED_REPOSITORY = "japan1988/multi-agent-mediation"
SHARED_WORKFLOW = ".github/workflows/tasukeru-mediation-confirmation.yml"
SHARED_PREFIXES = {
    kind: "refs/tags/tasukeru-approval-" + kind + "/"
    for kind in ("plan", "consumed", "stopped")
}
MAX_SHARED_RECORD_BYTES = 256 * 1024


class SharedRecordConflict(Exception):
    """A backend confirmed that create-if-absent did not create a new record."""


class SharedRecordDenied(Exception):
    """A backend confirmed that a write was forbidden before creation."""


class SharedRecordResultUnknown(Exception):
    """Creation may have happened; never retry or release the record."""


def _shared_document(raw):
    """Validate strict JSON bytes without repairing or replacing input bytes."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        if (type(raw) is not bytes or not raw or len(raw) > MAX_SHARED_RECORD_BYTES
                or raw.startswith(b"\xef\xbb\xbf")):
            raise ValueError("invalid bytes")
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        # Reject isolated surrogates also introduced by JSON Unicode escapes.
        encode(value).decode("utf-8", errors="strict")
        if type(value) is not dict:
            raise ValueError("record must be an object")
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise GateStopped("STOPPED_SHARED_RECORD_INVALID", "STRICT_SHARED_JSON_INVALID") from None


def _shared_hash(value):
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


class SharedRecordStoreDraft:
    """Create-only backend contract; no real backend is supplied by Stage 1.

    A reviewed adapter must supply policy(), read_exact(reference), and
    create_once(reference, bytes). A read returns bytes or a confirmed exact
    absence, never absence inferred from an error. A create returns an exact
    receipt or raises one of the typed outcomes above. No retry/update/delete
    API is used here. Every operation checks the supplied protection policy.

    expected_authority is a normalized trusted-deployment specification, not
    user input and not a raw GitHub ruleset response. Checking its equality
    does NOT prove actual server protection. The adapter and protection need
    independent review, including lifetime retention and authorized writers.

    This class stores bindings and one-use/stop evidence. It authenticates no
    human and grants no permission to generate. The future caller must verify
    identity, approval, expiry, unchanged context and scope before claiming,
    and revalidate them before processing. Existing respond remains blocked.
    """
    def __init__(self, backend=None, *, expected_authority=None):
        self.backend = backend
        self.expected_authority = json.loads(encode(expected_authority)) if expected_authority is not None else None
        self.create_attempts = 0

    def _authority(self):
        expected = self.expected_authority
        if self.backend is None or type(expected) is not dict:
            raise GateStopped("STOPPED_SHARED_STORE_UNCONFIGURED", "NO_REVIEWED_SHARED_BACKEND")
        keys = {"schema", "repository", "authority_epoch", "prefixes", "enforcement",
                "creation_allowed", "updates_allowed", "deletions_allowed", "bypass_actors"}
        if (set(expected) != keys or expected["schema"] != "NORMALIZED_PROTECTED_REF_POLICY_DRAFT_V1"
                or expected["repository"] != SHARED_REPOSITORY
                or type(expected["authority_epoch"]) is not str or not expected["authority_epoch"]
                or expected["prefixes"] != SHARED_PREFIXES or expected["enforcement"] != "active"
                or expected["creation_allowed"] is not True or expected["updates_allowed"] is not False
                or expected["deletions_allowed"] is not False or expected["bypass_actors"] != []):
            raise GateStopped("STOPPED_SHARED_PROTECTION", "UNSAFE_OR_UNRESOLVED_PROTECTION_SPEC")
        try:
            actual = self.backend.policy()
            actual_raw = encode(actual)
        except Exception:
            raise GateStopped("STOPPED_SHARED_PROTECTION", "PROTECTION_READ_UNRESOLVED") from None
        if type(actual) is not dict or actual_raw != encode(expected):
            raise GateStopped("STOPPED_SHARED_PROTECTION", "PROTECTION_BINDING_MISMATCH")
        return digest(encode(expected))

    def _binding(self, binding):
        keys = {"repository", "workflow_path", "run_id", "run_attempt", "head_sha", "head_branch"}
        if (type(binding) is not dict or set(binding) != keys
                or binding["repository"] != SHARED_REPOSITORY
                or binding["workflow_path"] != SHARED_WORKFLOW
                or type(binding["run_id"]) is not int or binding["run_id"] <= 0
                or type(binding["run_attempt"]) is not int or binding["run_attempt"] != 1
                or binding["head_branch"] != "main"
                or type(binding["head_sha"]) is not str or len(binding["head_sha"]) != 40
                or any(char not in "0123456789abcdef" for char in binding["head_sha"])):
            raise GateStopped("STOPPED_BINDING", "SHARED_RUN_BINDING_INVALID")
        return digest(encode({key: binding[key] for key in ("repository", "workflow_path", "run_id")}))

    def _record(self, binding, plan_raw, kind, owner=None, decision=None):
        _shared_document(plan_raw)
        return {"schema": SHARED_RECORD_SCHEMA, "kind": kind,
                "authority_sha256": self._authority(), "run_key": self._binding(binding),
                "binding_sha256": digest(encode(binding)), "plan_sha256": digest(plan_raw),
                "owner": owner, "decision": decision,
                "plan_utf8": plan_raw.decode("utf-8") if kind == "plan" else None}

    def _read(self, binding, kind):
        authority = self._authority()
        key = self._binding(binding)
        reference = SHARED_PREFIXES[kind] + key
        try:
            raw = self.backend.read_exact(reference)
        except Exception:
            raise GateStopped("STOPPED_SHARED_STORAGE_UNRESOLVED", "SHARED_READ_UNKNOWN_NOT_ABSENCE") from None
        if raw is None:
            return None
        value = _shared_document(raw)
        keys = {"schema", "kind", "authority_sha256", "run_key", "binding_sha256",
                "plan_sha256", "owner", "decision", "plan_utf8"}
        if (set(value) != keys or value["schema"] != SHARED_RECORD_SCHEMA
                or value["kind"] != kind or value["authority_sha256"] != authority
                or value["run_key"] != key or value["binding_sha256"] != digest(encode(binding))
                or not _shared_hash(value["plan_sha256"])):
            raise GateStopped("STOPPED_BINDING", "SHARED_RECORD_BINDING_MISMATCH")
        if kind == "plan":
            if (type(value["plan_utf8"]) is not str or value["owner"] is not None
                    or value["decision"] is not None):
                raise GateStopped("STOPPED_SHARED_RECORD_INVALID", "INVALID_PLAN_ANCHOR")
            stored = value["plan_utf8"].encode("utf-8")
            _shared_document(stored)
            if digest(stored) != value["plan_sha256"]:
                raise GateStopped("STOPPED_BINDING", "PLAN_ANCHOR_DIGEST_MISMATCH")
        elif kind == "consumed":
            if (value["plan_utf8"] is not None or type(value["decision"]) is not str
                    or value["decision"] not in {"claimed", "rejected"}
                    or (value["decision"] == "claimed" and not self._owner_valid(value["owner"]))
                    or (value["decision"] == "rejected" and value["owner"] is not None)):
                raise GateStopped("STOPPED_SHARED_RECORD_INVALID", "INVALID_CONSUMPTION_RECORD")
        elif value["owner"] is not None or value["decision"] is not None or value["plan_utf8"] is not None:
            raise GateStopped("STOPPED_SHARED_RECORD_INVALID", "INVALID_STOP_RECORD")
        return value

    @staticmethod
    def _owner_valid(owner):
        return (type(owner) is str and 0 < len(owner) <= 128
                and all(char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in owner))

    def _create(self, binding, plan_raw, kind, owner=None, decision=None):
        record = self._record(binding, plan_raw, kind, owner, decision)
        reference = SHARED_PREFIXES[kind] + record["run_key"]
        raw = encode(record)
        if len(raw) > MAX_SHARED_RECORD_BYTES:
            raise GateStopped("STOPPED_SHARED_RECORD_INVALID", "SHARED_RECORD_TOO_LARGE")
        self.create_attempts += 1
        try:
            receipt = self.backend.create_once(reference, raw)
        except SharedRecordConflict:
            raise GateStopped("DENIED_USED_OR_CLOSED", "SHARED_REFERENCE_ALREADY_EXISTS") from None
        except SharedRecordDenied:
            raise GateStopped("STOPPED_SHARED_WRITE_FORBIDDEN", "SHARED_CREATE_FORBIDDEN") from None
        except Exception:
            raise GateStopped("STOPPED_RESULT_UNKNOWN", "SHARED_CREATE_RESULT_UNKNOWN_NO_RETRY") from None
        expected = {"reference": reference, "sha256": digest(raw), "created": True}
        if type(receipt) is not dict or set(receipt) != set(expected) or encode(receipt) != encode(expected):
            raise GateStopped("STOPPED_RESULT_UNKNOWN", "SHARED_CREATE_RECEIPT_UNVERIFIED_NO_RETRY")
        return record

    def register_plan_once(self, binding, plan_raw):
        """Anchor exact displayed bytes before presentation; no re-registration."""
        if self._read(binding, "stopped") is not None:
            raise GateStopped("STOPPED_BY_HUMAN", "DURABLE_SHARED_STOP_RETAINED")
        if self._read(binding, "plan") is not None:
            raise GateStopped("DENIED_USED_OR_CLOSED", "RUN_ALREADY_HAS_FIXED_PROPOSAL")
        if self._read(binding, "consumed") is not None:
            raise GateStopped("DENIED_USED_OR_CLOSED", "ORPHAN_USAGE_IS_NOT_UNUSED")
        return self._create(binding, plan_raw, "plan")

    def status(self, binding, plan_raw):
        """Stop first. A new handler never treats a prior claim as unused."""
        _shared_document(plan_raw)
        stopped = self._read(binding, "stopped")
        if stopped is not None:
            raise GateStopped("STOPPED_BY_HUMAN", "DURABLE_SHARED_STOP_RETAINED")
        anchor = self._read(binding, "plan")
        if anchor is None:
            raise GateStopped("STOPPED_PLAN_UNKNOWN", "NO_SHARED_PLAN_ANCHOR_NO_RECOVERY")
        plan_hash = digest(plan_raw)
        if anchor["plan_sha256"] != plan_hash:
            raise GateStopped("STOPPED_BINDING", "DISPLAYED_PLAN_BYTES_CHANGED")
        consumed = self._read(binding, "consumed")
        if consumed is None:
            return {"state": "WAITING_FOR_APPROVAL", "owner": None, "plan_sha256": plan_hash}
        if consumed["plan_sha256"] != plan_hash:
            raise GateStopped("STOPPED_BINDING", "CONSUMPTION_PLAN_BINDING_CHANGED")
        return {"state": "CLAIMED" if consumed["decision"] == "claimed" else "REJECTED_BY_HUMAN",
                "owner": consumed["owner"], "plan_sha256": plan_hash}

    def claim_once(self, binding, plan_raw, owner):
        """Storage reservation only; caller must verify human approval separately."""
        if not self._owner_valid(owner):
            raise GateStopped("STOPPED_BINDING", "INVALID_CLAIM_OWNER")
        view = self.status(binding, plan_raw)
        if view["state"] != "WAITING_FOR_APPROVAL":
            raise GateStopped("DENIED_USED_OR_CLOSED", "SHARED_APPROVAL_ALREADY_CONSUMED")
        self._create(binding, plan_raw, "consumed", owner=owner, decision="claimed")
        # A stop racing with creation wins; consumption is never released.
        self.assert_owned_claim(binding, plan_raw, owner)

    def reject_once(self, binding, plan_raw):
        """Storage only; this is not proof that a human rejected the proposal."""
        view = self.status(binding, plan_raw)
        if view["state"] != "WAITING_FOR_APPROVAL":
            raise GateStopped("DENIED_USED_OR_CLOSED", "SHARED_APPROVAL_ALREADY_CONSUMED")
        self._create(binding, plan_raw, "consumed", decision="rejected")

    def assert_owned_claim(self, binding, plan_raw, owner):
        view = self.status(binding, plan_raw)
        if view["state"] != "CLAIMED" or view["owner"] != owner or not self._owner_valid(owner):
            raise GateStopped("DENIED_USED_OR_CLOSED", "SHARED_CLAIM_OWNER_MISMATCH")

    def stop_for_verified_request(self, binding, plan_raw):
        """Caller must authenticate the request; live STOP remains unconnected."""
        _shared_document(plan_raw)
        if self._read(binding, "stopped") is not None:
            return
        anchor = self._read(binding, "plan")
        if anchor is None or anchor["plan_sha256"] != digest(plan_raw):
            raise GateStopped("STOPPED_BINDING", "STOP_REQUEST_PLAN_BINDING_MISMATCH")
        self._create(binding, plan_raw, "stopped")
