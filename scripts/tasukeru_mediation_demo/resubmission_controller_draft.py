"""UNADOPTED DRAFT: local simulation of rejection/HITL/resubmission.

No AI API, repository write, workflow dispatch, repair, or final adoption exists
in this module. ApprovalRegistry is a mock trusted test driver, not a real
authentication/authorization service. Passing tests does not establish the
production identity, persistence, atomicity or cancellation mechanisms.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from pathlib import Path
import threading

import mediation_gate_draft as gate

MAX_REGENERATIONS = 1  # This trial condition is NOT an adopted project rule.
AUTHORITY_EPOCH = "SIMULATED_AUTHORITY_V0"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class MockGrant:
    token_id: str
    binding_sha256: str
    issued_at: int
    expires_at: int
    authority_epoch: str


class MockApprovalRegistry:
    """Only the fixture driver issues grants; generator output is never trusted.

Object identity represents the trusted mock channel. This is deliberately NOT
real user authentication, cryptographic authorization or durable token storage.
"""
    def __init__(self):
        self.epoch = AUTHORITY_EPOCH
        self._issued = {}
        self._used = set()
        self._lock = threading.Lock()

    def issue(self, binding, now=1000, ttl=60):
        with self._lock:
            token = "MOCK-GRANT-" + str(len(self._issued) + 1)
            grant = MockGrant(token, sha(canonical(binding)), now, now + ttl, self.epoch)
            self._issued[token] = grant
            return grant

    def consume(self, grant, binding, now):
        with self._lock:
            if not isinstance(grant, MockGrant) or self._issued.get(grant.token_id) is not grant:
                return "APPROVAL_NOT_FROM_TRUSTED_MOCK_CHANNEL"
            if grant.token_id in self._used:
                return "APPROVAL_ALREADY_USED"
            if type(now) is not int or now < grant.issued_at:
                return "APPROVAL_TIME_UNRESOLVED"
            if now >= grant.expires_at:
                return "APPROVAL_EXPIRED"
            if grant.authority_epoch != self.epoch:
                return "APPROVAL_AUTHORITY_CHANGED"
            if grant.binding_sha256 != sha(canonical(binding)):
                return "APPROVAL_BINDING_MISMATCH"
            self._used.add(grant.token_id)
            return "ALLOWED_ONCE"

    def is_used(self, grant):
        return isinstance(grant, MockGrant) and grant.token_id in self._used


class ResubmissionController:
    def __init__(self, simulation_id, packet, context_reader, clock):
        self.simulation_id = simulation_id
        self._packet_bytes = canonical(packet) if packet is not None else None
        self._context_reader = context_reader
        self._clock = clock
        self.expected_context = copy.deepcopy(context_reader())
        self.state = "NEW"
        self.reason = "NOT_STARTED"
        self.regenerations_used = 0
        self.events = []
        self.proposals = []
        self.verifications = []
        self.request_state = "NOT_REQUESTED"
        self.feedback = None
        self._request_bytes = None
        self._lock = threading.Lock()

    def _packet(self):
        return json.loads(self._packet_bytes) if self._packet_bytes is not None else None

    def _event(self, kind, **values):
        self.events.append({"seq": len(self.events) + 1, "kind": kind, **values})

    def _context_valid(self):
        try:
            return canonical(self._context_reader()) == canonical(self.expected_context)
        except Exception:
            return False

    def _view(self, operation="NO_EXTERNAL_ACTION"):
        return {"state": self.state, "reason": self.reason, "operation": operation,
                "regenerations_used": self.regenerations_used,
                "request_state": self.request_state,
                "human_final_adoption": False, "automatic_apply": False,
                "original_records_repaired": False}

    def start(self, raw, model_state="OUTPUT_READY"):
        with self._lock:
            if self.state != "NEW":
                return self._view("DENIED_ALREADY_STARTED")
            self.proposals.append(bytes(raw))
            v = gate.verify_proposal(raw, self._packet(), model_state)
            self.verifications.append(v)
            self._event("INITIAL_VERIFICATION", status=v["status"], reason=v["reason"])
            if v["status"] == "REVIEWABLE_DRAFT":
                self.state, self.reason = "HUMAN_REVIEW", "DECLARED_CHECKS_PASSED"
            elif v["status"] == "UNKNOWN":
                self.state, self.reason = "STOPPED_UNKNOWN", v["reason"]
            else:
                self.state, self.reason = "WAITING_FOR_APPROVAL", v["reason"]
                # Do not quote or execute untrusted instructions from the rejected
                # candidate. Feedback consists of a fixed reason and source facts.
                self.feedback = {"failure_reason": v["reason"],
                                 "rejected_proposal_sha256": sha(raw),
                                 "trusted_facts": self._packet()["facts"],
                                 "required_cause": "UNKNOWN", "required_actor": "UNKNOWN",
                                 "required_approval": "NOT_DETERMINED"}
                binding = {"simulation_id": self.simulation_id,
                           "action": "REGENERATE_MEDIATION_DRAFT_ONCE",
                           "target": "NEW_PROPOSAL_REVISION_2",
                           "purpose": "CORRECT_REJECTED_MEDIATION_PROPOSAL",
                           "scope": "REPORT_ONLY_NO_APPLICATION",
                           "max_regenerations": MAX_REGENERATIONS,
                           "rejected_proposal_sha256": sha(raw),
                           "failure_reason": v["reason"],
                           "preflight_context": self.expected_context,
                           "source": self._packet()["source"]}
                binding["request_id"] = sha(canonical(binding))
                self._request_bytes = canonical(binding)
                self._event("FEEDBACK_READY", request_id=binding["request_id"])
            return self._view()

    def approval_request(self):
        return json.loads(self._request_bytes) if self._request_bytes is not None else None

    def stop(self):
        with self._lock:
            self.state, self.reason = "STOPPED_BY_HUMAN", "HUMAN_STOP"
            self._event("LOCAL_HUMAN_STOP", request_state=self.request_state,
                        remote_cancellation="NOT_ATTEMPTED_OR_CONFIRMED")
            return self._view()

    def regenerate(self, grant, registry, generator):
        with self._lock:
            if self.state != "WAITING_FOR_APPROVAL":
                self._event("REGENERATION_DENIED_STATE", state=self.state)
                return self._view("DENIED_STATE")
            if grant is None:
                self._event("NO_APPROVAL_NO_REQUEST")
                return self._view("WAITING_NO_REQUEST")
            if self.regenerations_used >= MAX_REGENERATIONS:
                self.state, self.reason = "STOPPED_BUDGET", "MAX_REGENERATIONS_REACHED"
                return self._view("DENIED_BUDGET")
            if not self._context_valid():
                self.state, self.reason = "STOPPED_CONTEXT_CHANGED", "PREFLIGHT_CONTEXT_MISMATCH"
                self._event("REGENERATION_DENIED_PREFLIGHT")
                return self._view("DENIED_PREFLIGHT")
            binding = self.approval_request()
            verdict = registry.consume(grant, binding, self._clock())
            if verdict != "ALLOWED_ONCE":
                self.state, self.reason = "STOPPED_APPROVAL", verdict
                self._event("REGENERATION_DENIED_APPROVAL", reason=verdict)
                return self._view("DENIED_APPROVAL")
            self.regenerations_used += 1
            self.state, self.reason = "REGENERATION_REQUESTED", "APPROVED_ONCE"
            self.request_state = "REQUESTED"
            self._event("MOCK_REGENERATION_REQUESTED", token=grant.token_id,
                        request_id=binding["request_id"])
            generation_input = {"binding": binding, "evidence": self._packet(),
                                "feedback": copy.deepcopy(self.feedback)}
        # Release the controller lock so a human STOP can be observed in flight.
        try:
            receipt = generator(generation_input)
        except Exception:
            receipt = {"state": "RESULT_UNKNOWN", "payload": None}
        with self._lock:
            receipt_state = receipt.get("state") if isinstance(receipt, dict) else None
            if receipt_state not in {"COMPLETED", "RESULT_UNKNOWN", "REFUSED", "CONFIRMED_FAILED"}:
                receipt_state = "RESULT_UNKNOWN"
            self.request_state = receipt_state
            payload = receipt.get("payload") if isinstance(receipt, dict) else None
            if isinstance(payload, bytes):
                self.proposals.append(payload)
            self._event("MOCK_REQUEST_RESULT", state=receipt_state)
            if self.state == "STOPPED_BY_HUMAN":
                self._event("RESULT_WITHHELD_AFTER_STOP", result_state=receipt_state,
                            remote_cancellation="NOT_CONFIRMED")
                return self._view("WITHHELD_AFTER_STOP")
            if not self._context_valid():
                self.state, self.reason = "STOPPED_CONTEXT_CHANGED", "POSTFLIGHT_CONTEXT_MISMATCH"
            elif receipt_state == "RESULT_UNKNOWN":
                self.state, self.reason = "STOPPED_RESULT_UNKNOWN", "REGENERATION_RESULT_UNKNOWN"
            elif receipt_state == "REFUSED":
                self.state, self.reason = "STOPPED_REFUSAL", "MODEL_REFUSAL"
            elif receipt_state == "CONFIRMED_FAILED":
                self.state, self.reason = "STOPPED_FAILURE", "PROVIDER_CONFIRMED_FAILURE"
            elif not isinstance(payload, bytes):
                self.state, self.reason = "STOPPED_RESULT_UNKNOWN", "OUTPUT_BYTES_UNRESOLVED"
            else:
                v = gate.verify_proposal(payload, self._packet())
                self.verifications.append(v)
                self._event("RESUBMISSION_VERIFICATION", status=v["status"], reason=v["reason"])
                if v["status"] == "REVIEWABLE_DRAFT":
                    self.state, self.reason = "HUMAN_REVIEW", "DECLARED_CHECKS_PASSED"
                elif v["status"] == "UNKNOWN":
                    self.state, self.reason = "STOPPED_UNKNOWN", v["reason"]
                else:
                    self.state, self.reason = "STOPPED_BUDGET", v["reason"]
            return self._view("MOCK_REQUEST_COMPLETED_OR_UNKNOWN")

    def snapshot(self):
        with self._lock:
            return {**self._view(), "events": copy.deepcopy(self.events),
                    "proposal_hashes": [sha(p) for p in self.proposals],
                    "verifications": copy.deepcopy(self.verifications),
                    "approval_request": self.approval_request()}

