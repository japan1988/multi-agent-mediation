#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mediation_gate_sim_v0_1.py

Local-only educational simulator that reuses the R39 canonical mediation idea
as a non-agent "mediation gate".

Purpose
-------
- demonstrate Mediation-as-Gate rather than a privileged Mediator agent;
- keep explicit USER approval as the only decision authority;
- separate request, verification, and commit responsibilities;
- fail closed on evidence / semantic mismatch;
- retain an append-only hash-chained audit log.

Safety boundary
---------------
- local simulation only;
- no network calls;
- no external API calls;
- no process control;
- no autonomous external action;
- no auto-fix / commit / push / merge outside this simulator's own local log;
- USER remains the final simulated decision authority.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import tempfile
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple


SCHEMA = "MEDIATION_GATE_SIM_V0_1"
MODEL_ID = "R39-MEDIATION-GATE-SIM-V0.1"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Result:
    decision: Decision
    reason_code: str
    explanation: str = ""


def canon(obj: Any) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:20]}"


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


class AuthorityGate:
    """Fixed separation of duties for the simulator."""

    ALLOWED: Mapping[str, frozenset[str]] = {
        "HARNESS": frozenset({"REQUEST"}),
        "USER": frozenset({"DECIDE"}),
        "MEDIATION_GATE": frozenset({"VERIFY"}),
        "COMMITTER": frozenset({"FINALIZE"}),
    }

    def authorize(self, role: str, action: str) -> Result:
        if role not in self.ALLOWED:
            return Result(Decision.BLOCK, "AUTHORITY_ROLE_UNKNOWN", role)
        if action not in self.ALLOWED[role]:
            return Result(
                Decision.BLOCK,
                "AUTHORITY_ROLE_SEPARATION_VIOLATION",
                f"{role} cannot {action}",
            )
        return Result(Decision.ALLOW, "AUTHORITY_ROLE_ACTION_VALID", f"{role}:{action}")


class HashChainLog:
    """Append-only simulator log with sequence + previous-record hash ordering."""

    def __init__(self, path: str) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    @staticmethod
    def _preimage(row: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "schema": row["schema"],
            "seq": row["seq"],
            "record_id": row["record_id"],
            "kind": row["kind"],
            "tx_id": row["tx_id"],
            "actor_role": row["actor_role"],
            "payload": row["payload"],
            "observed_at_unix": row["observed_at_unix"],
            "prev_record_hash": row["prev_record_hash"],
        }

    def _rows_raw(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("record is not object")
            rows.append(obj)
        return rows

    def validate(self) -> Result:
        try:
            rows = self._rows_raw()
            prev = ""
            seen: set[str] = set()
            for expected_seq, row in enumerate(rows, 1):
                required = {
                    "schema",
                    "seq",
                    "record_id",
                    "kind",
                    "tx_id",
                    "actor_role",
                    "payload",
                    "observed_at_unix",
                    "prev_record_hash",
                    "record_hash",
                }
                if set(row) != required:
                    return Result(Decision.BLOCK, "LOG_RECORD_SCHEMA_INVALID")
                if row["schema"] != SCHEMA or row["seq"] != expected_seq:
                    return Result(Decision.BLOCK, "LOG_SEQUENCE_INVALID")
                if row["record_id"] in seen:
                    return Result(Decision.BLOCK, "LOG_RECORD_REPLAY")
                seen.add(row["record_id"])
                if row["prev_record_hash"] != prev:
                    return Result(Decision.BLOCK, "LOG_CHAIN_INVALID")
                expected_hash = sha256_text(canon(self._preimage(row)))
                if row["record_hash"] != expected_hash:
                    return Result(Decision.BLOCK, "LOG_RECORD_HASH_INVALID")
                prev = row["record_hash"]
            return Result(Decision.ALLOW, "LOG_VALID", str(len(rows)))
        except Exception as exc:
            return Result(Decision.BLOCK, "LOG_PARSE_FAILED", type(exc).__name__)

    def records(self) -> List[Dict[str, Any]]:
        vr = self.validate()
        if vr.decision != Decision.ALLOW:
            raise RuntimeError(vr.reason_code)
        return self._rows_raw()

    def append(
        self,
        *,
        kind: str,
        tx_id: str,
        actor_role: str,
        payload: Dict[str, Any],
    ) -> Tuple[Result, Optional[Dict[str, Any]]]:
        vr = self.validate()
        if vr.decision != Decision.ALLOW:
            return vr, None
        rows = self._rows_raw()
        row: Dict[str, Any] = {
            "schema": SCHEMA,
            "seq": len(rows) + 1,
            "record_id": new_id("REC"),
            "kind": kind,
            "tx_id": tx_id,
            "actor_role": actor_role,
            "payload": payload,
            "observed_at_unix": float(time.time()),
            "prev_record_hash": rows[-1]["record_hash"] if rows else "",
        }
        row["record_hash"] = sha256_text(canon(self._preimage(row)))
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(canon(row) + "\n")
            return Result(Decision.ALLOW, "LOG_APPEND_VALID", row["record_hash"]), row
        except Exception as exc:
            return Result(Decision.BLOCK, "LOG_APPEND_FAILED", type(exc).__name__), None

    def find(self, record_id: str) -> Optional[Dict[str, Any]]:
        return next((row for row in self.records() if row["record_id"] == record_id), None)


class MediationGate:
    """
    Non-agent mediation responsibility.

    It does not decide and cannot commit.  It verifies that the requested state
    transition, the explicit USER decision, and semantic continuity all bind to
    the same canonical transaction.
    """

    def __init__(self, authority: AuthorityGate, log: HashChainLog) -> None:
        self.authority = authority
        self.log = log
        self.last_digest_by_subject: Dict[str, str] = {}

    def verify(
        self,
        *,
        request_record_id: str,
        decision_record_id: str,
    ) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("MEDIATION_GATE", "VERIFY")
        if ar.decision != Decision.ALLOW:
            return ar, None

        req = self.log.find(request_record_id)
        dec = self.log.find(decision_record_id)
        if req is None or req.get("kind") != "REQUEST":
            return Result(Decision.BLOCK, "MEDIATION_REQUEST_INVALID"), None
        if dec is None or dec.get("kind") != "USER_DECISION":
            return Result(Decision.BLOCK, "MEDIATION_USER_DECISION_INVALID"), None
        if req["tx_id"] != dec["tx_id"]:
            return Result(Decision.BLOCK, "MEDIATION_TRANSACTION_BINDING_INVALID"), None
        if dec["payload"].get("request_record_id") != req["record_id"]:
            return Result(Decision.BLOCK, "MEDIATION_DECISION_BINDING_INVALID"), None
        if dec["payload"].get("decision") != "APPROVE":
            return Result(Decision.BLOCK, "MEDIATION_USER_NOT_APPROVED"), None

        payload = req["payload"]
        subject = payload.get("subject_id")
        if not isinstance(subject, str) or not subject:
            return Result(Decision.BLOCK, "MEDIATION_SUBJECT_INVALID"), None
        if not isinstance(payload.get("previous_state_hash"), str):
            return Result(Decision.BLOCK, "MEDIATION_PREVIOUS_STATE_HASH_INVALID"), None
        if not isinstance(payload.get("next_state_hash"), str):
            return Result(Decision.BLOCK, "MEDIATION_NEXT_STATE_HASH_INVALID"), None
        if not isinstance(payload.get("purpose"), str) or not payload["purpose"]:
            return Result(Decision.BLOCK, "MEDIATION_PURPOSE_INVALID"), None

        previous_digest = self.last_digest_by_subject.get(subject, "")
        proof = {
            "subject_id": subject,
            "request_record_id": req["record_id"],
            "user_decision_record_id": dec["record_id"],
            "previous_mediation_digest": previous_digest,
            "purpose": payload["purpose"],
        }
        digest = sha256_text(canon(proof))
        proof["mediation_digest"] = digest
        return Result(Decision.ALLOW, "MEDIATION_GATE_VALID", digest), proof

    def accept_committed_digest(self, proof: Mapping[str, Any]) -> None:
        subject = str(proof["subject_id"])
        self.last_digest_by_subject[subject] = str(proof["mediation_digest"])


class MediationGateSimulator:
    def __init__(self, log_path: str) -> None:
        self.authority = AuthorityGate()
        self.log = HashChainLog(log_path)
        self.gate = MediationGate(self.authority, self.log)
        self.state: Dict[str, bytes] = {}

    def start(self) -> Result:
        return self.log.validate()

    def request(
        self,
        *,
        subject_id: str,
        next_state: bytes,
        purpose: str,
    ) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("HARNESS", "REQUEST")
        if ar.decision != Decision.ALLOW:
            return ar, None
        tx_id = new_id("TX")
        current = self.state.get(subject_id, b"")
        return self.log.append(
            kind="REQUEST",
            tx_id=tx_id,
            actor_role="HARNESS",
            payload={
                "subject_id": subject_id,
                "previous_state_hash": sha256_bytes(current),
                "next_state_hash": sha256_bytes(next_state),
                "next_state_b64": b64e(next_state),
                "purpose": purpose,
            },
        )

    def user_decide(
        self,
        *,
        request_record_id: str,
        decision: str,
    ) -> Tuple[Result, Optional[Dict[str, Any]]]:
        ar = self.authority.authorize("USER", "DECIDE")
        if ar.decision != Decision.ALLOW:
            return ar, None
        if decision not in {"APPROVE", "REJECT"}:
            return Result(Decision.BLOCK, "USER_DECISION_INVALID"), None
        req = self.log.find(request_record_id)
        if req is None or req.get("kind") != "REQUEST":
            return Result(Decision.BLOCK, "USER_DECISION_REQUEST_INVALID"), None
        if any(
            row["kind"] == "USER_DECISION"
            and row["payload"].get("request_record_id") == request_record_id
            for row in self.log.records()
        ):
            return Result(Decision.BLOCK, "USER_DECISION_REPLAY"), None
        rr, rec = self.log.append(
            kind="USER_DECISION",
            tx_id=req["tx_id"],
            actor_role="USER",
            payload={
                "request_record_id": request_record_id,
                "decision": decision,
            },
        )
        if rr.decision != Decision.ALLOW:
            return rr, None
        return (
            Result(
                Decision.ALLOW if decision == "APPROVE" else Decision.BLOCK,
                "USER_APPROVED" if decision == "APPROVE" else "USER_REJECTED",
                req["tx_id"],
            ),
            rec,
        )

    def finalize(
        self,
        *,
        request_record_id: str,
        decision_record_id: str,
    ) -> Result:
        ar = self.authority.authorize("COMMITTER", "FINALIZE")
        if ar.decision != Decision.ALLOW:
            return ar

        gr, proof = self.gate.verify(
            request_record_id=request_record_id,
            decision_record_id=decision_record_id,
        )
        if gr.decision != Decision.ALLOW or proof is None:
            return gr

        req = self.log.find(request_record_id)
        assert req is not None
        subject = req["payload"]["subject_id"]
        current = self.state.get(subject, b"")
        if sha256_bytes(current) != req["payload"]["previous_state_hash"]:
            return Result(Decision.BLOCK, "COMMIT_PREVIOUS_STATE_MISMATCH")

        try:
            next_state = b64d(req["payload"]["next_state_b64"])
        except Exception:
            return Result(Decision.BLOCK, "COMMIT_NEXT_STATE_DECODE_FAILED")
        if sha256_bytes(next_state) != req["payload"]["next_state_hash"]:
            return Result(Decision.BLOCK, "COMMIT_NEXT_STATE_HASH_MISMATCH")

        rr, _ = self.log.append(
            kind="COMMITTED",
            tx_id=req["tx_id"],
            actor_role="COMMITTER",
            payload={
                "request_record_id": request_record_id,
                "user_decision_record_id": decision_record_id,
                "mediation_digest": proof["mediation_digest"],
            },
        )
        if rr.decision != Decision.ALLOW:
            return rr

        self.state[subject] = next_state
        self.gate.accept_committed_digest(proof)
        return Result(Decision.ALLOW, "MEDIATION_GATE_COMMIT_VALID", req["tx_id"])


def run_contract_suite() -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="mediation_gate_sim_") as td:
        sim = MediationGateSimulator(str(pathlib.Path(td) / "audit.jsonl"))
        checks["start"] = sim.start().decision == Decision.ALLOW
        checks["gate_cannot_decide"] = (
            sim.authority.authorize("MEDIATION_GATE", "DECIDE").decision == Decision.BLOCK
        )
        checks["user_cannot_finalize"] = (
            sim.authority.authorize("USER", "FINALIZE").decision == Decision.BLOCK
        )

        rr, req = sim.request(subject_id="CASE-1", next_state=b"accepted", purpose="demo")
        checks["request"] = rr.decision == Decision.ALLOW and req is not None
        assert req is not None

        # No USER approval -> mediation gate blocks.
        fake_decision_id = "REC-NOT-FOUND"
        blocked = sim.finalize(
            request_record_id=req["record_id"],
            decision_record_id=fake_decision_id,
        )
        checks["no_user_approval_blocks"] = blocked.decision == Decision.BLOCK

        dr, dec = sim.user_decide(request_record_id=req["record_id"], decision="APPROVE")
        checks["user_approval"] = dr.decision == Decision.ALLOW and dec is not None
        assert dec is not None

        final = sim.finalize(
            request_record_id=req["record_id"],
            decision_record_id=dec["record_id"],
        )
        checks["commit_after_gate"] = (
            final.decision == Decision.ALLOW and sim.state.get("CASE-1") == b"accepted"
        )
        checks["audit_chain"] = sim.log.validate().decision == Decision.ALLOW

        # A second USER decision for the same request must fail closed.
        replay, _ = sim.user_decide(request_record_id=req["record_id"], decision="APPROVE")
        checks["decision_replay_blocks"] = replay.decision == Decision.BLOCK

    return {
        "model_id": MODEL_ID,
        "decision": "ALLOW" if all(checks.values()) else "BLOCK",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="R39 mediation-as-gate local simulator")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = run_contract_suite()
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["decision"] == "ALLOW" else 1

    print(json.dumps({
        "model_id": MODEL_ID,
        "message": "Run with --self-test for the local mediation-gate contract suite.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
