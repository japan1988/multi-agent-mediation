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
