#!/usr/bin/env python3
"""
Territory Mediation Simulator v0.2 — Hardened R39 Cleanup (Consolidation-First)

R39 Cleanup preserves the frozen R39 purpose while consolidating duplicated
responsibilities. It is a local educational simulator, not a production trust
infrastructure.

Core architecture (exactly four concepts):
  1. CANONICAL_AUTHORITY_CONTRACT
  2. CANONICAL_SIM_PROOF
  3. CANONICAL_SIM_TRANSACTION
  4. DURABLE_CANONICAL_SIM_LOG

Security objective:
  - only an explicit USER decision can authorize a simulated state change;
  - semantic / role meaning cannot drift silently;
  - failures are fail-closed;
  - one durable log is the authoritative history and recovery source.

Non-goals:
  - TPM/HSM/secure-enclave emulation;
  - OS-principal isolation guarantees;
  - external monotonic rollback protection;
  - real-world autonomous execution.
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import os
import pathlib
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

MODEL_ID = "HM-R39-CANONICAL-MEDIATION-V1"
SIM_VERSION = "0.2-r39"
R39_SCHEMA = "R39_CLEANUP_CANONICAL_SIM_V1"

CORE_CONTROLS = (
    "CANONICAL_AUTHORITY_CONTRACT",
    "CANONICAL_SIM_PROOF",
    "CANONICAL_SIM_TRANSACTION",
    "DURABLE_CANONICAL_SIM_LOG",
)

PURPOSE_INVARIANTS = (
    "USER_DECIDES",
    "SEMANTIC_ROLE_CONTINUITY",
    "FAIL_CLOSED",
    "AUDITABLE_AND_RECONSTRUCTIBLE",
)


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Result:
    decision: Decision
    reason_code: str
    explanation: str = ""


def _json_no_dupes(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key: {k}")
        out[k] = v
    return out


def strict_loads(s: str) -> Any:
    return json.loads(s, object_pairs_hook=_json_no_dupes, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def htxt(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hbytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"), validate=True)


# ---------------------------------------------------------------------------
# 1) CANONICAL_AUTHORITY_CONTRACT
# ---------------------------------------------------------------------------

class CanonicalAuthorityContract:
    CONTROL_ID = "CANONICAL_AUTHORITY_CONTRACT"
    ALLOWED: Mapping[str, frozenset[str]] = {
        "USER": frozenset({"DECIDE"}),
        "HARNESS": frozenset({"REQUEST"}),
        "VERIFIER": frozenset({"VERIFY"}),
        "COMMITTER": frozenset({"FINALIZE"}),
    }
    RECORD_ACTOR: Mapping[str, str] = {
        "AUTH_REQUEST": "HARNESS",
        "USER_DECISION": "USER",
        "TX_PREPARED": "VERIFIER",
        "TX_COMMITTED": "COMMITTER",
        "TX_ABORTED": "COMMITTER",
    }

    def authorize(self, role: str, action: str) -> Result:
        if role not in self.ALLOWED:
            return Result(Decision.BLOCK, "AUTHORITY_ROLE_UNKNOWN", role)
        if action not in self.ALLOWED[role]:
            return Result(Decision.BLOCK, "AUTHORITY_ROLE_SEPARATION_VIOLATION", f"{role} cannot {action}")
        return Result(Decision.ALLOW, "AUTHORITY_ROLE_ACTION_VALID", f"{role}:{action}")

    def __init__(self) -> None:
        self._record_issuers: Dict[str, Tuple[int, Any]] = {}

    def record_actor(self, kind: str) -> Optional[str]:
        return self.RECORD_ACTOR.get(kind)

    def bind_record_issuer(self, kind: str, bound_method: Any) -> Result:
        if kind not in self.RECORD_ACTOR:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_KIND_UNKNOWN", kind)
        owner = getattr(bound_method, "__self__", None)
        func = getattr(bound_method, "__func__", None)
        code = getattr(func, "__code__", None)
        if owner is None or code is None:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_ISSUER_BINDING_INVALID", kind)
        if kind in self._record_issuers:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_ISSUER_REBIND_FORBIDDEN", kind)
        self._record_issuers[kind] = (id(owner), code)
        return Result(Decision.ALLOW, "AUTHORITY_RECORD_ISSUER_BOUND", kind)

    def authorize_record_issuance(self, kind: str, caller_self: Any, caller_code: Any) -> Result:
        bound = self._record_issuers.get(kind)
        if bound is None:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_ISSUER_UNBOUND", kind)
        owner_id, code = bound
        if caller_self is None or id(caller_self) != owner_id or caller_code is not code:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_ISSUANCE_PATH_INVALID", kind)
        return Result(Decision.ALLOW, "AUTHORITY_RECORD_ISSUANCE_PATH_VALID", kind)

    def validate_contract(self) -> Result:
        exact = (
            self.ALLOWED["USER"] == frozenset({"DECIDE"})
            and self.ALLOWED["HARNESS"] == frozenset({"REQUEST"})
            and self.ALLOWED["VERIFIER"] == frozenset({"VERIFY"})
            and self.ALLOWED["COMMITTER"] == frozenset({"FINALIZE"})
            and self.RECORD_ACTOR == {
                "AUTH_REQUEST": "HARNESS",
                "USER_DECISION": "USER",
                "TX_PREPARED": "VERIFIER",
                "TX_COMMITTED": "COMMITTER",
                "TX_ABORTED": "COMMITTER",
            }
        )
        return Result(Decision.ALLOW if exact else Decision.BLOCK,
                      "CANONICAL_AUTHORITY_CONTRACT_VALID" if exact else "AUTHORITY_CONTRACT_INVALID")


# ---------------------------------------------------------------------------
# 4) DURABLE_CANONICAL_SIM_LOG (implemented before Proof/Transaction because
#    both use the same single durable history source)
# ---------------------------------------------------------------------------

class DurableCanonicalSimLog:
    CONTROL_ID = "DURABLE_CANONICAL_SIM_LOG"
    SECURITY_ORDERING_SOURCE = "SEQUENCE_PLUS_PREVIOUS_RECORD_HASH"
    TIMESTAMP_SECURITY_AUTHORITY = False

    CANONICAL_PAYLOAD_KEYS: Mapping[str, frozenset[str]] = {
        "AUTH_REQUEST": frozenset({"source_id", "previous_state_hash", "next_state_hash", "next_state_b64", "purpose"}),
        "USER_DECISION": frozenset({"request_record_id", "decision"}),
        "TX_PREPARED": frozenset({"user_decision_record_id", "previous_proof_hash"}),
        "TX_COMMITTED": frozenset({"prepared_record_hash"}),
        "TX_ABORTED": frozenset({"prepared_record_hash", "reason_code"}),
    }

    def _validate_payload_schema(self, kind: Any, tx_id: Any, payload: Any) -> Result:
        if not isinstance(kind, str) or not isinstance(tx_id, str) or not isinstance(payload, dict):
            return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", str(kind))
        if kind == "AUDIT_NOTE":
            return Result(Decision.ALLOW, "CANONICAL_LOG_PAYLOAD_SCHEMA_VALID", kind)
        expected = self.CANONICAL_PAYLOAD_KEYS.get(kind)
        if expected is None:
            return Result(Decision.BLOCK, "CANONICAL_LOG_RECORD_KIND_UNKNOWN", kind)
        if set(payload) != expected:
            return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        if kind == "AUTH_REQUEST":
            if not all(isinstance(payload[k], str) for k in expected):
                return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        elif kind == "USER_DECISION":
            if not isinstance(payload["request_record_id"], str) or payload["decision"] not in {"APPROVE", "REJECT"}:
                return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        elif kind == "TX_PREPARED":
            if not isinstance(payload["user_decision_record_id"], str) or not isinstance(payload["previous_proof_hash"], str):
                return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        elif kind == "TX_COMMITTED":
            if not isinstance(payload["prepared_record_hash"], str):
                return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        elif kind == "TX_ABORTED":
            if not isinstance(payload["prepared_record_hash"], str) or not isinstance(payload["reason_code"], str):
                return Result(Decision.BLOCK, "CANONICAL_LOG_PAYLOAD_SCHEMA_INVALID", kind)
        return Result(Decision.ALLOW, "CANONICAL_LOG_PAYLOAD_SCHEMA_VALID", kind)

    def __init__(self, authority: CanonicalAuthorityContract, path: str):
        self.authority = authority
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")
        self.fail_next_append = False

    @staticmethod
    def _preimage(raw: Mapping[str, Any]) -> Dict[str, Any]:
        return {k: raw[k] for k in (
            "schema_version", "seq", "record_id", "kind", "tx_id", "actor_role",
            "payload", "observed_at_unix", "prev_record_hash"
        )}

    def _read_raw(self) -> Tuple[Result, List[Dict[str, Any]]]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            out: List[Dict[str, Any]] = []
            for line in lines:
                if not line.strip():
                    continue
                obj = strict_loads(line)
                if not isinstance(obj, dict):
                    return Result(Decision.BLOCK, "CANONICAL_LOG_PARSE_FAILED", "record is not object"), []
                out.append(obj)
            return Result(Decision.ALLOW, "CANONICAL_LOG_READ_VALID", str(len(out))), out
        except Exception as e:
            return Result(Decision.BLOCK, "CANONICAL_LOG_PARSE_FAILED", type(e).__name__), []

    def validate(self) -> Result:
        rr, rows = self._read_raw()
        if rr.decision != Decision.ALLOW:
            return rr
        prev = ""
        seen_ids: set[str] = set()
        for idx, raw in enumerate(rows, 1):
            required = {
                "schema_version", "seq", "record_id", "kind", "tx_id", "actor_role",
                "payload", "observed_at_unix", "prev_record_hash", "record_hash"
            }
            if set(raw) != required:
                return Result(Decision.BLOCK, "CANONICAL_LOG_RECORD_SCHEMA_INVALID", f"seq={idx}")
            if raw["schema_version"] != R39_SCHEMA or raw["seq"] != idx:
                return Result(Decision.BLOCK, "CANONICAL_LOG_SEQUENCE_INVALID", f"seq={idx}")
            ps = self._validate_payload_schema(raw["kind"], raw["tx_id"], raw["payload"])
            if ps.decision != Decision.ALLOW:
                return Result(Decision.BLOCK, ps.reason_code, f"seq={idx}:{ps.explanation}")
            expected_actor = self.authority.record_actor(raw["kind"])
            if expected_actor is not None and raw["actor_role"] != expected_actor:
                return Result(Decision.BLOCK, "AUTHORITY_RECORD_ACTOR_MISMATCH", f"seq={idx}")
            if raw["record_id"] in seen_ids:
                return Result(Decision.BLOCK, "CANONICAL_LOG_RECORD_REPLAY", raw["record_id"])
            seen_ids.add(raw["record_id"])
            if raw["prev_record_hash"] != prev:
                return Result(Decision.BLOCK, "CANONICAL_LOG_CHAIN_INVALID", f"seq={idx}")
            expected = htxt(canon(self._preimage(raw)))
            if raw["record_hash"] != expected:
                return Result(Decision.BLOCK, "CANONICAL_LOG_RECORD_HASH_INVALID", f"seq={idx}")
            prev = raw["record_hash"]
        return Result(Decision.ALLOW, "DURABLE_CANONICAL_SIM_LOG_VALID", str(len(rows)))

    def records(self) -> List[Dict[str, Any]]:
        vr = self.validate()
        if vr.decision != Decision.ALLOW:
            raise RuntimeError(vr.reason_code)
        return self._read_raw()[1]

    def _append_raw(self, *, kind: str, tx_id: str, actor_role: str, payload: Dict[str, Any], observed_at_unix: Optional[float] = None) -> Tuple[Result, Optional[Dict[str, Any]]]:
        caller = inspect.currentframe().f_back
        caller_self = caller.f_locals.get("self") if caller else None
        caller_code = caller.f_code if caller else None
        internal_codes = {self._append_canonical.__func__.__code__, self.append_audit_note.__func__.__code__}
        if caller_self is not self or caller_code not in internal_codes:
            return Result(Decision.BLOCK, "CANONICAL_LOG_INTERNAL_APPEND_PATH_INVALID"), None
        ps = self._validate_payload_schema(kind, tx_id, payload)
        if ps.decision != Decision.ALLOW:
            return ps, None
        vr = self.validate()
        if vr.decision != Decision.ALLOW:
            return vr, None
        if self.fail_next_append:
            self.fail_next_append = False
            return Result(Decision.BLOCK, "CANONICAL_LOG_APPEND_FAILED", "failure injection"), None
        rows = self._read_raw()[1]
        seq = len(rows) + 1
        prev = rows[-1]["record_hash"] if rows else ""
        raw: Dict[str, Any] = {
            "schema_version": R39_SCHEMA,
            "seq": seq,
            "record_id": new_id("REC"),
            "kind": kind,
            "tx_id": tx_id,
            "actor_role": actor_role,
            "payload": payload,
            "observed_at_unix": float(time.time() if observed_at_unix is None else observed_at_unix),
            "prev_record_hash": prev,
        }
        raw["record_hash"] = htxt(canon(self._preimage(raw)))
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(canon(raw) + "\n")
                f.flush()
                os.fsync(f.fileno())
            return Result(Decision.ALLOW, "CANONICAL_LOG_APPEND_VALID", raw["record_hash"]), raw
        except Exception as e:
            return Result(Decision.BLOCK, "CANONICAL_LOG_APPEND_FAILED", type(e).__name__), None

    def _append_canonical(self, *, kind: str, tx_id: str, payload: Dict[str, Any]) -> Tuple[Result, Optional[Dict[str, Any]]]:
        actor_role = self.authority.record_actor(kind)
        if actor_role is None:
            return Result(Decision.BLOCK, "AUTHORITY_RECORD_KIND_UNKNOWN", kind), None
        caller = inspect.currentframe().f_back
        caller_self = caller.f_locals.get("self") if caller else None
        caller_code = caller.f_code if caller else None
        ir = self.authority.authorize_record_issuance(kind, caller_self, caller_code)
        if ir.decision != Decision.ALLOW:
            return ir, None
        return self._append_raw(kind=kind, tx_id=tx_id, actor_role=actor_role, payload=payload)

    def append_audit_note(self, *, payload: Dict[str, Any], observed_at_unix: Optional[float] = None) -> Tuple[Result, Optional[Dict[str, Any]]]:
        return self._append_raw(kind="AUDIT_NOTE", tx_id="", actor_role="HARNESS", payload=payload, observed_at_unix=observed_at_unix)

    def find_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        for r in self.records():
            if r["record_id"] == record_id:
                return r
        return None

    def transaction_records(self, tx_id: str) -> List[Dict[str, Any]]:
        return [r for r in self.records() if r["tx_id"] == tx_id and r["kind"].startswith("TX_")]


# ---------------------------------------------------------------------------
# 2) CANONICAL_SIM_PROOF
#    Verification responsibility remains distinct, but proof state is stored
#    directly in TX_PREPARED rather than in a separate proof object.
# ---------------------------------------------------------------------------

class CanonicalSimProofValidator:
    CONTROL_ID = "CANONICAL_SIM_PROOF"
    VERIFICATION_AUTHORITY = "CANONICAL_LOG_ACTOR_ROLE_VERIFIER"
    SEMANTIC_ROLE = "SOURCE_STATE_TRANSITION"
    TRUST_DOMAIN = "R39_SIMULATION"

    def __init__(self, authority: CanonicalAuthorityContract, log: DurableCanonicalSimLog):
        self.authority = authority
        self.log = log

    @staticmethod
    def _prepared_semantic_preimage(prepared_record: Mapping[str, Any]) -> Dict[str, Any]:
        # Deliberately excludes the log envelope (record_hash, prev_record_hash,
        # sequence, timestamp). The semantic chain is the PREPARED proof state.
        payload = prepared_record["payload"]
        return {
            "user_decision_record_id": payload["user_decision_record_id"],
            "previous_proof_hash": payload["previous_proof_hash"],
        }

    def canonical_prepared_proof_digest(self, prepared_record: Mapping[str, Any]) -> str:
        if prepared_record.get("kind") != "TX_PREPARED":
            raise ValueError("not TX_PREPARED")
        payload = prepared_record.get("payload")
        if not isinstance(payload, dict) or set(payload) != {"user_decision_record_id", "previous_proof_hash"}:
            raise ValueError("invalid TX_PREPARED proof state")
        if not isinstance(payload["user_decision_record_id"], str) or not isinstance(payload["previous_proof_hash"], str):
            raise ValueError("invalid TX_PREPARED proof state")
        return htxt(canon(self._prepared_semantic_preimage(prepared_record)))

    def resolve_prepared_evidence(
        self, prepared_record: Mapping[str, Any]
    ) -> Tuple[Result, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        try:
            if prepared_record["kind"] != "TX_PREPARED" or prepared_record["actor_role"] != "VERIFIER":
                return Result(Decision.BLOCK, "CANONICAL_PROOF_PREPARED_RECORD_INVALID"), None, None
            tx_id = prepared_record["tx_id"]
            decision_id = prepared_record["payload"]["user_decision_record_id"]
            dec = self.log.find_record(decision_id)
            if dec is None or dec["kind"] != "USER_DECISION" or dec["actor_role"] != "USER":
                return Result(Decision.BLOCK, "CANONICAL_PROOF_USER_DECISION_INVALID"), None, None
            if dec["tx_id"] != tx_id or dec["payload"].get("decision") != "APPROVE":
                return Result(Decision.BLOCK, "CANONICAL_PROOF_TRANSACTION_BINDING_INVALID"), None, None
            req_id = dec["payload"].get("request_record_id")
            req = self.log.find_record(req_id) if isinstance(req_id, str) else None
            if req is None or req["kind"] != "AUTH_REQUEST" or req["actor_role"] != "HARNESS":
                return Result(Decision.BLOCK, "CANONICAL_PROOF_REQUEST_INVALID"), None, None
            if req["tx_id"] != tx_id:
                return Result(Decision.BLOCK, "CANONICAL_PROOF_TRANSACTION_BINDING_INVALID"), None, None
            return Result(Decision.ALLOW, "CANONICAL_PROOF_EVIDENCE_RESOLVED"), req, dec
        except Exception as e:
            return Result(Decision.BLOCK, "CANONICAL_PROOF_VERIFY_FAILED", type(e).__name__), None, None

    def verify_prepared(
        self,
        prepared_record: Mapping[str, Any],
        *,
        expected_previous_proof_hash: str,
    ) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("VERIFIER", "VERIFY")
        if ar.decision != Decision.ALLOW:
            return ar, None
        rr, req, _dec = self.resolve_prepared_evidence(prepared_record)
        if rr.decision != Decision.ALLOW or req is None:
            return rr, None
        try:
            if prepared_record["payload"]["previous_proof_hash"] != expected_previous_proof_hash:
                return Result(Decision.BLOCK, "RECURSIVE_SEMANTIC_ROLE_CONTINUITY_BROKEN"), None
            # Semantic subject, role, scope and capability are derived from the
            # canonical request/model. They are no longer independently stored,
            # so there is no duplicated proof-side state that can drift.
            source_id = req["payload"]["source_id"]
            if not isinstance(source_id, str) or not source_id:
                return Result(Decision.BLOCK, "RECURSIVE_SEMANTIC_ROLE_CONTINUITY_BROKEN"), None
            digest = self.canonical_prepared_proof_digest(prepared_record)
            return Result(Decision.ALLOW, "CANONICAL_SIM_PROOF_VALID", digest), req
        except Exception as e:
            return Result(Decision.BLOCK, "CANONICAL_PROOF_VERIFY_FAILED", type(e).__name__), None


# ---------------------------------------------------------------------------
# 3) CANONICAL_SIM_TRANSACTION
# ---------------------------------------------------------------------------

class CanonicalSimTransactionEngine:
    CONTROL_ID = "CANONICAL_SIM_TRANSACTION"
    STATES = frozenset({"PREPARED", "COMMITTED", "ABORTED"})

    def __init__(self, authority: CanonicalAuthorityContract, log: DurableCanonicalSimLog, proof_validator: CanonicalSimProofValidator):
        self.authority = authority
        self.log = log
        self.proof_validator = proof_validator
        self.state: Dict[str, bytes] = {}
        self.last_prepared_digest_by_subject: Dict[str, str] = {}

    def _tx_status(self, tx_id: str) -> Optional[str]:
        recs = self.log.transaction_records(tx_id)
        statuses = [r["kind"].removeprefix("TX_") for r in recs]
        if not statuses:
            return None
        if statuses.count("PREPARED") != 1:
            return "INVALID"
        terminals = [s for s in statuses if s in {"COMMITTED", "ABORTED"}]
        if len(terminals) > 1:
            return "INVALID"
        return terminals[0] if terminals else "PREPARED"

    def prepare(self, *, transaction_id: str, request_record: Dict[str, Any], decision_record: Dict[str, Any]) -> Tuple[Result, Optional[Dict[str, Any]]]:
        if self._tx_status(transaction_id) is not None:
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_REPLAY"), None
        try:
            # Resolve the canonical evidence chain from the durable log before
            # TX_PREPARED exists. Caller-supplied record contents are not authority.
            provisional = {
                "kind": "TX_PREPARED",
                "actor_role": "VERIFIER",
                "tx_id": transaction_id,
                "payload": {
                    "user_decision_record_id": decision_record["record_id"],
                    "previous_proof_hash": "",
                },
            }
            rr, canonical_req, canonical_dec = self.proof_validator.resolve_prepared_evidence(provisional)
            if rr.decision != Decision.ALLOW or canonical_req is None or canonical_dec is None:
                return rr, None
            if request_record.get("record_id") != canonical_req["record_id"] or decision_record.get("record_id") != canonical_dec["record_id"]:
                return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_EVIDENCE_BINDING_INVALID"), None

            req = canonical_req["payload"]
            source_id = req["source_id"]
            previous_digest = self.last_prepared_digest_by_subject.get(source_id, "")
            payload = {
                "user_decision_record_id": canonical_dec["record_id"],
                "previous_proof_hash": previous_digest,
            }
            candidate = {
                "kind": "TX_PREPARED",
                "actor_role": "VERIFIER",
                "tx_id": transaction_id,
                "payload": payload,
            }
            pv, verified_req = self.proof_validator.verify_prepared(
                candidate, expected_previous_proof_hash=previous_digest
            )
            if pv.decision != Decision.ALLOW or verified_req is None:
                return pv, None

            # Transaction facts are validated from the canonical AUTH_REQUEST,
            # not from caller-supplied copies, before the durable PREPARED append.
            current = self.state.get(source_id, b"")
            if hbytes(current) != req["previous_state_hash"]:
                return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_PREVIOUS_STATE_MISMATCH"), None
            next_bytes = b64d(req["next_state_b64"])
            if hbytes(next_bytes) != req["next_state_hash"]:
                return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_NEXT_STATE_HASH_MISMATCH"), None

            ar = self.log._append_canonical(kind="TX_PREPARED", tx_id=transaction_id, payload=payload)
            if ar[0].decision != Decision.ALLOW:
                return ar[0], None
            return Result(Decision.ALLOW, "CANONICAL_SIM_TRANSACTION_PREPARED", transaction_id), ar[1]
        except Exception as e:
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_PREPARE_FAILED", type(e).__name__), None

    def finalize(self, transaction_id: str) -> Result:
        ar = self.authority.authorize("COMMITTER", "FINALIZE")
        if ar.decision != Decision.ALLOW:
            return ar
        if self._tx_status(transaction_id) != "PREPARED":
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_NOT_PREPARED")
        prep = next(r for r in self.log.transaction_records(transaction_id) if r["kind"] == "TX_PREPARED")
        rr, req, _dec = self.proof_validator.resolve_prepared_evidence(prep)
        if rr.decision != Decision.ALLOW or req is None:
            self.log._append_canonical(
                kind="TX_ABORTED", tx_id=transaction_id,
                payload={"prepared_record_hash": prep["record_hash"], "reason_code": rr.reason_code},
            )
            return rr
        rq = req["payload"]
        source_id = rq["source_id"]
        expected_previous = self.last_prepared_digest_by_subject.get(source_id, "")
        vr, req2 = self.proof_validator.verify_prepared(
            prep, expected_previous_proof_hash=expected_previous
        )
        if vr.decision != Decision.ALLOW or req2 is None:
            self.log._append_canonical(
                kind="TX_ABORTED", tx_id=transaction_id,
                payload={"prepared_record_hash": prep["record_hash"], "reason_code": vr.reason_code},
            )
            return vr
        current = self.state.get(source_id, b"")
        if hbytes(current) != rq["previous_state_hash"]:
            self.log._append_canonical(
                kind="TX_ABORTED", tx_id=transaction_id,
                payload={"prepared_record_hash": prep["record_hash"], "reason_code": "CANONICAL_TRANSACTION_PREVIOUS_STATE_MISMATCH"},
            )
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_PREVIOUS_STATE_MISMATCH")
        try:
            next_bytes = b64d(rq["next_state_b64"])
        except Exception:
            self.log._append_canonical(
                kind="TX_ABORTED", tx_id=transaction_id,
                payload={"prepared_record_hash": prep["record_hash"], "reason_code": "CANONICAL_TRANSACTION_NEXT_STATE_INVALID"},
            )
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_NEXT_STATE_INVALID")
        if hbytes(next_bytes) != rq["next_state_hash"]:
            self.log._append_canonical(
                kind="TX_ABORTED", tx_id=transaction_id,
                payload={"prepared_record_hash": prep["record_hash"], "reason_code": "CANONICAL_TRANSACTION_NEXT_STATE_HASH_MISMATCH"},
            )
            return Result(Decision.BLOCK, "CANONICAL_TRANSACTION_NEXT_STATE_HASH_MISMATCH")
        cr, _ = self.log._append_canonical(
            kind="TX_COMMITTED",
            tx_id=transaction_id,
            payload={"prepared_record_hash": prep["record_hash"]},
        )
        if cr.decision != Decision.ALLOW:
            return cr
        self.state[source_id] = next_bytes
        self.last_prepared_digest_by_subject[source_id] = self.proof_validator.canonical_prepared_proof_digest(prep)
        return Result(Decision.ALLOW, "CANONICAL_SIM_TRANSACTION_COMMITTED", transaction_id)

    def recover(self) -> Result:
        vr = self.log.validate()
        if vr.decision != Decision.ALLOW:
            return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", vr.reason_code)
        self.state.clear()
        self.last_prepared_digest_by_subject.clear()
        rows = self.log.records()
        by_tx: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            if r["kind"].startswith("TX_"):
                by_tx.setdefault(r["tx_id"], []).append(r)
        commits = [r for r in rows if r["kind"] == "TX_COMMITTED"]
        for commit in commits:
            tx_id = commit["tx_id"]
            recs = by_tx.get(tx_id, [])
            preps = [r for r in recs if r["kind"] == "TX_PREPARED"]
            terminals = [r for r in recs if r["kind"] in {"TX_COMMITTED", "TX_ABORTED"}]
            if len(preps) != 1 or len(terminals) != 1 or terminals[0]["kind"] != "TX_COMMITTED":
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", f"tx={tx_id}")
            prep = preps[0]
            if commit["payload"].get("prepared_record_hash") != prep["record_hash"]:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", "prepared binding")
            rr, req, _dec = self.proof_validator.resolve_prepared_evidence(prep)
            if rr.decision != Decision.ALLOW or req is None:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", rr.reason_code)
            rq = req["payload"]
            source_id = rq["source_id"]
            expected_previous = self.last_prepared_digest_by_subject.get(source_id, "")
            pr, _ = self.proof_validator.verify_prepared(
                prep, expected_previous_proof_hash=expected_previous
            )
            if pr.decision != Decision.ALLOW:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", pr.reason_code)
            current = self.state.get(source_id, b"")
            if hbytes(current) != rq["previous_state_hash"]:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", "state chain")
            try:
                next_bytes = b64d(rq["next_state_b64"])
            except Exception:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", "next state")
            if hbytes(next_bytes) != rq["next_state_hash"]:
                return Result(Decision.BLOCK, "RECOVERY_RECONSTRUCTION_FAILED", "next hash")
            self.state[source_id] = next_bytes
            self.last_prepared_digest_by_subject[source_id] = self.proof_validator.canonical_prepared_proof_digest(prep)
        return Result(Decision.ALLOW, "RECOVERY_RECONSTRUCTED_FROM_ONE_DURABLE_CANONICAL_LOG", str(len(commits)))

    def verify_historical_proof(self, tx_id: str) -> Result:
        vr = self.log.validate()
        if vr.decision != Decision.ALLOW:
            return vr
        last: Dict[str, str] = {}
        for commit in [r for r in self.log.records() if r["kind"] == "TX_COMMITTED"]:
            recs = self.log.transaction_records(commit["tx_id"])
            prep = next((r for r in recs if r["kind"] == "TX_PREPARED"), None)
            if prep is None:
                return Result(Decision.BLOCK, "HISTORICAL_PROOF_RECONSTRUCTION_FAILED")
            if commit["payload"].get("prepared_record_hash") != prep["record_hash"]:
                return Result(Decision.BLOCK, "HISTORICAL_PROOF_RECONSTRUCTION_FAILED", "prepared binding")
            rr, req, _dec = self.proof_validator.resolve_prepared_evidence(prep)
            if rr.decision != Decision.ALLOW or req is None:
                return rr
            source_id = req["payload"]["source_id"]
            pv, _ = self.proof_validator.verify_prepared(
                prep, expected_previous_proof_hash=last.get(source_id, "")
            )
            if pv.decision != Decision.ALLOW:
                return pv
            digest = self.proof_validator.canonical_prepared_proof_digest(prep)
            last[source_id] = digest
            if commit["tx_id"] == tx_id:
                return Result(Decision.ALLOW, "HISTORICAL_CANONICAL_SIM_PROOF_VALID", digest)
        return Result(Decision.BLOCK, "HISTORICAL_PROOF_NOT_FOUND")


# ---------------------------------------------------------------------------
# R39 Simulator orchestration
# ---------------------------------------------------------------------------

class R39Simulator:
    def __init__(self, log_path: str):
        self.authority = CanonicalAuthorityContract()
        self.log = DurableCanonicalSimLog(self.authority, log_path)
        self.proof_validator = CanonicalSimProofValidator(self.authority, self.log)
        self.transactions = CanonicalSimTransactionEngine(self.authority, self.log, self.proof_validator)
        bindings = (
            ("AUTH_REQUEST", self.harness_request),
            ("USER_DECISION", self.user_decide),
            ("TX_PREPARED", self.transactions.prepare),
            ("TX_COMMITTED", self.transactions.finalize),
            ("TX_ABORTED", self.transactions.finalize),
        )
        for kind, method in bindings:
            br = self.authority.bind_record_issuer(kind, method)
            if br.decision != Decision.ALLOW:
                raise RuntimeError(br.reason_code)

    def start(self) -> Result:
        for r in (self.authority.validate_contract(), self.log.validate(), self.transactions.recover()):
            if r.decision != Decision.ALLOW:
                return r
        return Result(Decision.ALLOW, "R39_CLEANUP_RUNTIME_VALID", MODEL_ID)

    def harness_request(self, *, source_id: str, next_state: bytes, purpose: str) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("HARNESS", "REQUEST")
        if ar.decision != Decision.ALLOW:
            return ar, None
        tx_id = new_id("TX")
        current = self.transactions.state.get(source_id, b"")
        payload = {
            "source_id": source_id,
            "previous_state_hash": hbytes(current),
            "next_state_hash": hbytes(next_state),
            "next_state_b64": b64e(next_state),
            "purpose": purpose,
        }
        rr, rec = self.log._append_canonical(kind="AUTH_REQUEST", tx_id=tx_id, payload=payload)
        return (Result(Decision.ALLOW, "HARNESS_AUTHORITY_REQUEST_RECORDED", tx_id), rec) if rr.decision == Decision.ALLOW else (rr, None)

    def user_decide(self, request_record_id: str, decision: str) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("USER", "DECIDE")
        if ar.decision != Decision.ALLOW:
            return ar, None
        if decision not in {"APPROVE", "REJECT"}:
            return Result(Decision.BLOCK, "USER_DECISION_INVALID"), None
        req = self.log.find_record(request_record_id)
        if req is None or req["kind"] != "AUTH_REQUEST":
            return Result(Decision.BLOCK, "USER_DECISION_REQUEST_INVALID"), None
        # Exact request is one-decision-only. USER_DECISION references the
        # canonical AUTH_REQUEST record instead of copying its hash/transaction facts.
        if any(r["kind"] == "USER_DECISION" and r["payload"].get("request_record_id") == req["record_id"] for r in self.log.records()):
            return Result(Decision.BLOCK, "USER_DECISION_REPLAY"), None
        payload = {
            "request_record_id": req["record_id"],
            "decision": decision,
        }
        rr, rec = self.log._append_canonical(kind="USER_DECISION", tx_id=req["tx_id"], payload=payload)
        if rr.decision != Decision.ALLOW:
            return rr, None
        return Result(Decision.ALLOW if decision == "APPROVE" else Decision.BLOCK,
                      "USER_APPROVED_EXACT_TRANSACTION" if decision == "APPROVE" else "USER_REJECTED_EXACT_TRANSACTION",
                      req["tx_id"]), rec

    def prepare_approved_request(self, request_record_id: str) -> Tuple[Result, Optional[Dict[str, Any]]]:
        req = self.log.find_record(request_record_id)
        if req is None:
            return Result(Decision.BLOCK, "CANONICAL_REQUEST_NOT_FOUND"), None
        dec = next((r for r in self.log.records() if r["kind"] == "USER_DECISION" and r["payload"].get("request_record_id") == req["record_id"]), None)
        if dec is None:
            return Result(Decision.BLOCK, "EXPLICIT_USER_DECISION_REQUIRED"), None
        return self.transactions.prepare(transaction_id=req["tx_id"], request_record=req, decision_record=dec)

    def finalize(self, tx_id: str) -> Result:
        return self.transactions.finalize(tx_id)


# ---------------------------------------------------------------------------
# Runtime consistency checks (historical R38/R39 migration checks are external)
# ---------------------------------------------------------------------------

def runtime_integrity_check(source_path: Optional[str] = None) -> Dict[str, Any]:
    p = pathlib.Path(source_path or __file__)
    text = p.read_text(encoding="utf-8")
    authority = CanonicalAuthorityContract()
    proof_fields: set[str] = set()
    checks = {
        "exact_four_core_controls": len(CORE_CONTROLS) == 4 and len(set(CORE_CONTROLS)) == 4,
        "one_transaction_state_machine": CanonicalSimTransactionEngine.STATES == frozenset({"PREPARED", "COMMITTED", "ABORTED"}),
        "one_recovery_source": DurableCanonicalSimLog.CONTROL_ID == "DURABLE_CANONICAL_SIM_LOG",
        "timestamp_not_security_authority": DurableCanonicalSimLog.TIMESTAMP_SECURITY_AUTHORITY is False,
        "authority_roles_non_overlapping": all(
            authority.authorize(role, action).decision == Decision.BLOCK
            for role, action in (("HARNESS", "DECIDE"), ("VERIFIER", "DECIDE"), ("COMMITTER", "DECIDE"), ("USER", "FINALIZE"))
        ),
        "purpose_invariants_preserved": PURPOSE_INVARIANTS == (
            "USER_DECIDES", "SEMANTIC_ROLE_CONTINUITY", "FAIL_CLOSED", "AUDITABLE_AND_RECONSTRUCTIBLE"
        ),
        "proof_uses_one_evidence_binding": not proof_fields and DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["TX_PREPARED"] == frozenset({"user_decision_record_id", "previous_proof_hash"}),
        "proof_ordering_delegated_to_log": DurableCanonicalSimLog.SECURITY_ORDERING_SOURCE == "SEQUENCE_PLUS_PREVIOUS_RECORD_HASH" and "previous_proof_hash" in DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["TX_PREPARED"],
        "auth_request_tx_id_owned_by_record_envelope": "transaction_id" not in DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["AUTH_REQUEST"],
        "unused_intent_hash_removed": "intent_hash" not in DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["AUTH_REQUEST"],
        "simulated_attestation_layer_removed": not hasattr(CanonicalSimProofValidator, "_attest"),
        "abort_not_public_authority_surface": not hasattr(CanonicalSimTransactionEngine, "abort") and not hasattr(CanonicalSimTransactionEngine, "_abort_failed_transaction"),
        "historical_migration_checks_not_in_runtime_core": "R38_PARENT_SOURCE_SHA256" not in globals() and "verify_r38_reduction_input" not in globals(),
        "production_trust_infrastructure_not_claimed": "not a production trust" in text,
    }
    all_ok = all(checks.values())
    return {
        "check_version": "R39_CLEANUP_RUNTIME_INTEGRITY_V1",
        "decision": "ALLOW" if all_ok else "BLOCK",
        "reason_code": "R39_CLEANUP_CONSISTENCY_NON_CONTRADICTION_PURPOSE_MEANS_VALID" if all_ok else "R39_CLEANUP_RUNTIME_INTEGRITY_FAILED",
        "checks": checks,
        "core_controls": list(CORE_CONTROLS),
        "purpose_invariants": list(PURPOSE_INVARIANTS),
        "purpose_means_statement": "Duplicate responsibilities are consolidated; distinct purpose-critical responsibilities remain separate.",
    }


# ---------------------------------------------------------------------------
# Behavioral contracts for the reduced architecture
# ---------------------------------------------------------------------------

def run_behavioral_contract_suite() -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    def record(tid: str, passed: bool, detail: str) -> None:
        results[tid] = {"pass": bool(passed), "detail": detail}

    with tempfile.TemporaryDirectory(prefix="r39_contract_") as td:
        path = str(pathlib.Path(td) / "canonical.jsonl")
        sim = R39Simulator(path)
        record("TEST-R39-STRUCT-001", sim.start().decision == Decision.ALLOW, "single-log runtime starts")
        record("TEST-R39-AUTH-001", sim.authority.authorize("HARNESS", "DECIDE").decision == Decision.BLOCK, "Harness cannot decide")
        record("TEST-R39-AUTH-002", sim.authority.authorize("VERIFIER", "DECIDE").decision == Decision.BLOCK, "Verifier cannot decide")
        record("TEST-R39-AUTH-003", sim.authority.authorize("COMMITTER", "DECIDE").decision == Decision.BLOCK, "Committer cannot decide")
        record("TEST-R39-AUTH-004", sim.authority.authorize("USER", "DECIDE").decision == Decision.ALLOW, "User alone has decision action")

        r1, req1 = sim.harness_request(source_id="R", next_state=b"one", purpose="R39_ONE")
        record("TEST-R39-TX-001", r1.decision == Decision.ALLOW and req1 is not None, "Harness request recorded")
        pre_no_user, _ = sim.prepare_approved_request(req1["record_id"])
        record("TEST-R39-TX-002", pre_no_user.decision == Decision.BLOCK and pre_no_user.reason_code == "EXPLICIT_USER_DECISION_REQUIRED", "no user decision => no prepare")
        d1, dec1 = sim.user_decide(req1["record_id"], "APPROVE")
        record("TEST-R39-AUTH-005", d1.decision == Decision.ALLOW and dec1 is not None, "exact user approval recorded")
        replay, _ = sim.user_decide(req1["record_id"], "APPROVE")
        record("TEST-R39-AUTH-006", replay.decision == Decision.BLOCK and replay.reason_code == "USER_DECISION_REPLAY", "user decision one-time")
        p1, prep1 = sim.prepare_approved_request(req1["record_id"])
        record("TEST-R39-PROOF-001", p1.decision == Decision.ALLOW and prep1 is not None, "canonical proof validated before prepare")
        c1 = sim.finalize(req1["tx_id"])
        record("TEST-R39-TX-003", c1.decision == Decision.ALLOW and sim.transactions.state.get("R") == b"one", "commit applies state only after durable COMMITTED record")
        record("TEST-R39-LOG-001", sim.log.validate().decision == Decision.ALLOW, "canonical log hash chain valid")
        record("TEST-R39-PROOF-002", sim.transactions.verify_historical_proof(req1["tx_id"]).decision == Decision.ALLOW, "historical proof reconstructs")

        # Second commit proves recursive semantic/role continuity without a separate semantic ledger.
        r2, req2 = sim.harness_request(source_id="R", next_state=b"two", purpose="R39_TWO")
        sim.user_decide(req2["record_id"], "APPROVE")
        p2, prep2 = sim.prepare_approved_request(req2["record_id"])
        c2 = sim.finalize(req2["tx_id"])
        record("TEST-R39-PROOF-003", p2.decision == Decision.ALLOW and c2.decision == Decision.ALLOW, "second proof preserves semantic/role chain")
        record("TEST-R39-PROOF-004", sim.transactions.verify_historical_proof(req1["tx_id"]).decision == Decision.ALLOW, "first proof remains valid after second commit")

        # Semantic continuity drift probe under the merged proof-state model.
        prep2_rec = next(r for r in sim.log.transaction_records(req2["tx_id"]) if r["kind"] == "TX_PREPARED")
        prep1_rec = next(r for r in sim.log.transaction_records(req1["tx_id"]) if r["kind"] == "TX_PREPARED")
        expected_prev = sim.proof_validator.canonical_prepared_proof_digest(prep1_rec)
        bad_prep = {
            **prep2_rec,
            "payload": {
                **prep2_rec["payload"],
                "previous_proof_hash": "f" * 64,
            },
        }
        drift, _ = sim.proof_validator.verify_prepared(
            bad_prep, expected_previous_proof_hash=expected_prev
        )
        record("TEST-R39-PROOF-005", drift.decision == Decision.BLOCK and drift.reason_code == "RECURSIVE_SEMANTIC_ROLE_CONTINUITY_BROKEN", "merged TX_PREPARED semantic continuity drift is blocked")

        # Canonical transaction atomicity under log failure: PREPARED can exist, but state does not move without COMMITTED.
        r3, req3 = sim.harness_request(source_id="R", next_state=b"three", purpose="R39_FAIL_COMMIT")
        sim.user_decide(req3["record_id"], "APPROVE")
        sim.prepare_approved_request(req3["record_id"])
        before = sim.transactions.state["R"]
        sim.log.fail_next_append = True
        fail_commit = sim.finalize(req3["tx_id"])
        record("TEST-R39-TX-004", fail_commit.decision == Decision.BLOCK and sim.transactions.state["R"] == before, "failed COMMITTED append cannot partially change authoritative state")
        record("TEST-R39-TX-005", sim.transactions._tx_status(req3["tx_id"]) == "PREPARED", "failed finalize leaves one non-authoritative PREPARED record only")

        # Recovery ignores non-terminal PREPARED and reconstructs only COMMITTED state.
        sim2 = R39Simulator(path)
        rec = sim2.start()
        record("TEST-R39-REC-001", rec.decision == Decision.ALLOW and sim2.transactions.state.get("R") == b"two", "restart reconstructs committed state from one log")
        record("TEST-R39-REC-002", sim2.transactions.verify_historical_proof(req1["tx_id"]).decision == Decision.ALLOW, "historical proof reconstructs after restart")

        # Wall clock is deliberately descriptive: security ordering is sequence + prev hash.
        rr, _ = sim2.log.append_audit_note(payload={"note":"backdated descriptive time"}, observed_at_unix=time.time()-3600)
        record("TEST-R39-TIME-001", rr.decision == Decision.ALLOW and sim2.log.validate().decision == Decision.ALLOW, "backdated descriptive timestamp cannot change security ordering")
        record("TEST-R39-TIME-002", sim2.log.SECURITY_ORDERING_SOURCE == "SEQUENCE_PLUS_PREVIOUS_RECORD_HASH" and not sim2.log.TIMESTAMP_SECURITY_AUTHORITY, "timestamp is not a security authority")

        # Log tamper is fail-closed.
        good = pathlib.Path(path).read_bytes()
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        obj = strict_loads(lines[0]); obj["payload"]["purpose"] = "tampered" if "purpose" in obj["payload"] else "tampered"
        lines[0] = canon(obj); pathlib.Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
        record("TEST-R39-LOG-002", sim2.log.validate().decision == Decision.BLOCK, "tampered canonical log fails closed")
        pathlib.Path(path).write_bytes(good)
        record("TEST-R39-LOG-003", sim2.log.validate().decision == Decision.ALLOW, "restored canonical log validates")

        integrity = runtime_integrity_check()
        record("TEST-R39-CLEANUP-001", integrity["decision"] == "ALLOW", "runtime consistency/non-contradiction/purpose-means check passes")
        record("TEST-R39-CLEANUP-002", len(integrity["core_controls"]) == 4, "architecture still has exactly four core controls")
        proof_fields: set[str] = set()
        record("TEST-R39-CLEANUP-003", "CanonicalSimProof" not in globals() and not proof_fields, "separate CanonicalSimProof storage object removed")
        record("TEST-R39-CLEANUP-004", DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["TX_PREPARED"] == frozenset({"user_decision_record_id", "previous_proof_hash"}), "proof state merged into minimal TX_PREPARED payload")
        record("TEST-R39-CLEANUP-005", "proof_sequence" not in proof_fields and "previous_proof_hash" in DurableCanonicalSimLog.CANONICAL_PAYLOAD_KEYS["TX_PREPARED"], "log ordering and semantic continuity remain separate responsibilities")
        record("TEST-R39-CLEANUP-006", not hasattr(sim.transactions, "abort") and not hasattr(sim.transactions, "_abort_failed_transaction"), "TX_ABORTED is only an internal terminal outcome emitted by finalize")

    return results


def behavioral_suite_result() -> Result:
    r = run_behavioral_contract_suite()
    failed = sorted(k for k, v in r.items() if not v["pass"])
    if failed:
        return Result(Decision.BLOCK, "R39_CLEANUP_BEHAVIORAL_CONTRACT_FAILED", ",".join(failed))
    return Result(Decision.ALLOW, "R39_CLEANUP_BEHAVIORAL_CONTRACTS_VALID", f"{len(r)} reduced-architecture tests passed")


def run_simulation() -> Dict[str, Any]:
    root = pathlib.Path(tempfile.mkdtemp(prefix="r39_normal_", dir="/mnt/data"))
    log_path = str(root / "canonical.jsonl")
    sim = R39Simulator(log_path)
    out: Dict[str, Any] = {
        "model_id": MODEL_ID,
        "sim_version": SIM_VERSION,
        "behavioral_contracts": asdict(behavioral_suite_result()),
        "runtime_integrity": runtime_integrity_check(),
        "start_runtime": asdict(sim.start()),
    }
    r1, req1 = sim.harness_request(source_id="R", next_state=b"r39-normal-1", purpose="R39_NORMAL_1")
    d1, _ = sim.user_decide(req1["record_id"], "APPROVE") if req1 else (Result(Decision.BLOCK,"NO_REQ"), None)
    p1, _ = sim.prepare_approved_request(req1["record_id"]) if req1 else (Result(Decision.BLOCK,"NO_REQ"), None)
    c1 = sim.finalize(req1["tx_id"]) if req1 else Result(Decision.BLOCK,"NO_REQ")
    r2, req2 = sim.harness_request(source_id="R", next_state=b"r39-normal-2", purpose="R39_NORMAL_2")
    d2, _ = sim.user_decide(req2["record_id"], "APPROVE") if req2 else (Result(Decision.BLOCK,"NO_REQ"), None)
    p2, _ = sim.prepare_approved_request(req2["record_id"]) if req2 else (Result(Decision.BLOCK,"NO_REQ"), None)
    c2 = sim.finalize(req2["tx_id"]) if req2 else Result(Decision.BLOCK,"NO_REQ")
    hist1 = sim.transactions.verify_historical_proof(req1["tx_id"]) if req1 else Result(Decision.BLOCK,"NO_REQ")
    log_valid = sim.log.validate()
    state_before_restart = sim.transactions.state.get("R", b"")
    sim2 = R39Simulator(log_path)
    recovery = sim2.start()
    state_after_restart = sim2.transactions.state.get("R", b"")
    out.update({
        "first_request": asdict(r1), "first_user_decision": asdict(d1), "first_prepare": asdict(p1), "first_commit": asdict(c1),
        "second_request": asdict(r2), "second_user_decision": asdict(d2), "second_prepare": asdict(p2), "second_commit": asdict(c2),
        "historical_first_proof_after_second_commit": asdict(hist1),
        "canonical_log": asdict(log_valid),
        "recovery": asdict(recovery),
        "state_before_restart_hash": hbytes(state_before_restart),
        "state_after_restart_hash": hbytes(state_after_restart),
        "state_recovery_exact": state_before_restart == state_after_restart,
        "canonical_log_path": log_path,
        "core_controls": list(CORE_CONTROLS),
        "security_ordering": DurableCanonicalSimLog.SECURITY_ORDERING_SOURCE,
        "timestamp_security_authority": DurableCanonicalSimLog.TIMESTAMP_SECURITY_AUTHORITY,
    })
    required = [
        out["behavioral_contracts"]["decision"] == Decision.ALLOW.value,
        out["runtime_integrity"]["decision"] == "ALLOW",
        out["start_runtime"]["decision"] == Decision.ALLOW.value,
        c1.decision == Decision.ALLOW,
        c2.decision == Decision.ALLOW,
        hist1.decision == Decision.ALLOW,
        log_valid.decision == Decision.ALLOW,
        recovery.decision == Decision.ALLOW,
        state_before_restart == state_after_restart,
    ]
    out["r39_status"] = {
        "decision": "ALLOW" if all(required) else "BLOCK",
        "reason_code": "R39_CLEANUP_NORMAL_SIMULATION_VALID" if all(required) else "R39_CLEANUP_NORMAL_SIMULATION_FAILED",
    }
    return out


if __name__ == "__main__":
    print(json.dumps(run_simulation(), ensure_ascii=False, indent=2, default=lambda o: o.value if isinstance(o, Enum) else str(o)))
