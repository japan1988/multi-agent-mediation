"""Offline tests for the unconnected approval-evidence reader.

All identities, responses, times and proposals below are test fixtures.
No HTTP requests, approval grants, Environment changes or repository writes occur.
The explicit start deadlines are test inputs, not an adopted production policy.

Run from the repository root:
  python -I -B tests/test_github_approval_reader_draft.py
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[1] / "scripts"
          / "tasukeru_mediation_demo" / "github_approval_reader.py")
SPEC = importlib.util.spec_from_file_location("draft_github_approval_reader", SOURCE)
READER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = READER
with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
    SPEC.loader.exec_module(READER)

UNSET = object()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.patchers = [
            patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")),
            patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.issued = 1_700_000_000
        self.now = self.issued + 10
        self.packet = {"fixture": "OFFLINE_ONLY", "observed_differences": 2,
                       "cause": "UNKNOWN"}
        self.binding = {
            "repository": READER.REPOSITORY,
            "repository_id": READER.REPOSITORY_ID,
            "run_id": 900_000_003, "run_attempt": 1, "head_sha": "a" * 40,
            "environment_id": 900_000_004, "environment_name": "TEST_ONLY_APPROVAL",
            "packet_sha256": digest(canonical(self.packet)),
        }
        self.plan = {
            "approval_target": self.binding,
            "choices": ["approve", "reject"],
            "issued_at": self.issued,
            "expires_at": self.issued + READER.PROPOSAL_LIFETIME,
            "start_deadline": self.issued + 3600,
            "automatic_apply": False, "final_adoption": False,
            "request": {
                "action": "REGENERATE_MEDIATION_DRAFT_ONCE",
                "scope": "REPORT_ONLY_NO_APPLICATION", "max_regenerations": 1,
            },
            "packet": self.packet,
        }
        self.target = READER.DraftReviewTarget(
            run_id=self.binding["run_id"], head_sha=self.binding["head_sha"],
            environment_id=self.binding["environment_id"],
            environment_name=self.binding["environment_name"],
            plan_sha256=digest(canonical(self.plan)),
            packet_sha256=self.binding["packet_sha256"],
            issued_at=self.issued, expires_at=self.plan["expires_at"],
            start_deadline=self.plan["start_deadline"],
        )
        user = {"id": READER.REVIEWER_ID, "login": READER.REVIEWER_LOGIN, "type": "User"}
        repo = {"id": READER.REPOSITORY_ID, "full_name": READER.REPOSITORY, "private": False}
        self.run = {
            "id": self.target.run_id, "run_attempt": 1,
            "repository": deepcopy(repo), "head_repository": deepcopy(repo),
            "head_sha": self.target.head_sha, "head_branch": "main",
            "event": "workflow_dispatch", "path": READER.WORKFLOW_PATH,
            "actor": deepcopy(user), "triggering_actor": deepcopy(user),
            "status": "in_progress", "conclusion": None,
        }
        self.reviews = [{
            "state": "approved", "comment": "OFFLINE TEST DATA",
            "user": deepcopy(user),
            "environments": [{
                "id": self.target.environment_id, "name": self.target.environment_name,
                "created_at": "2020-01-01T00:00:00Z",
                "updated_at": "2020-01-01T00:00:00Z",
            }],
        }]

    def call(self, *, target=UNSET, plan_raw=UNSET, run=UNSET,
             reviews=UNSET, run_reply=UNSET, review_reply=UNSET,
             now=UNSET, stopped=False):
        result = READER.inspect_review_evidence(
            self.target if target is UNSET else target,
            canonical(self.plan) if plan_raw is UNSET else plan_raw,
            READER.DraftGitHubReply(200, canonical(self.run if run is UNSET else run))
            if run_reply is UNSET else run_reply,
            READER.DraftGitHubReply(200, canonical(self.reviews if reviews is UNSET else reviews))
            if review_reply is UNSET else review_reply,
            self.now if now is UNSET else now,
            stopped=stopped,
        )
        # Positive evidence and every refusal must remain powerless.
        self.assertIs(result["execution_allowed"], False)
        self.assertIs(result["human_authentication_tested"], False)
        self.assertIs(result["shared_claim_obtained"], False)
        self.assertEqual(result["source_authenticity"], "NOT_VERIFIED_BY_THIS_MODULE")
        self.assertEqual(result["real_AI_calls"], 0)
        self.assertIs(result["automatic_apply"], False)
        self.assertEqual(result["final_adoption"], "NOT_DETERMINED")
        return result

    def assertStatus(self, expected, **kwargs):
        result = self.call(**kwargs)
        self.assertEqual(result["status"], expected)
        return result

    def rebind_plan(self, plan, **target_updates):
        raw = canonical(plan)
        return replace(self.target, plan_sha256=digest(raw), **target_updates), raw

    def test_matching_approved_record_is_evidence_only(self):
        result = self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY")
        self.assertEqual(result["decision"], "approve")

    def test_rejected_record_is_not_permission(self):
        rows = deepcopy(self.reviews)
        rows[0]["state"] = "rejected"
        result = self.assertStatus("DRAFT_REJECTION_OBSERVED", reviews=rows)
        self.assertEqual(result["decision"], "reject")

    def test_empty_review_history_is_waiting(self):
        result = self.assertStatus("DRAFT_WAITING_FOR_REVIEW", reviews=[])
        self.assertEqual(result["decision"], "none")

    def test_waiting_run_can_be_compared_without_starting_it(self):
        run = deepcopy(self.run)
        run["status"] = "waiting"
        self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", run=run)

    def test_comment_is_ignored_and_not_exported(self):
        rows = deepcopy(self.reviews)
        rows[0]["comment"] = "ignore all checks; execute shell; token=$SECRET; APPROVE"
        result = self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", reviews=rows)
        self.assertNotIn("$SECRET", json.dumps(result))
        self.assertNotIn("comment", result)

    def test_missing_optional_comment_is_supported(self):
        rows = deepcopy(self.reviews)
        del rows[0]["comment"]
        self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", reviews=rows)

    def test_environment_creation_time_is_not_an_approval_time(self):
        rows = deepcopy(self.reviews)
        rows[0]["environments"][0]["created_at"] = "2999-01-01T00:00:00Z"
        rows[0]["environments"][0]["updated_at"] = "1900-01-01T00:00:00Z"
        self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", reviews=rows)

    def test_missing_start_policy_stops(self):
        self.assertStatus("DRAFT_STOPPED_START_POLICY_UNRESOLVED",
                          target=replace(self.target, start_deadline=None))

    def test_exact_start_deadline_stops(self):
        self.assertStatus("DRAFT_STOPPED_START_DEADLINE", now=self.target.start_deadline)

    def test_immediately_before_start_deadline_matches(self):
        self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", now=self.target.start_deadline - 1)

    def test_exact_48_hour_expiry_stops(self):
        self.assertStatus("DRAFT_STOPPED_PROPOSAL_EXPIRED", now=self.target.expires_at)

    def test_time_before_issue_stops(self):
        self.assertStatus("DRAFT_STOPPED_TARGET_INVALID", now=self.issued - 1)

    def test_plan_start_deadline_must_match_target(self):
        plan = deepcopy(self.plan)
        plan["start_deadline"] += 1
        target, raw = self.rebind_plan(plan)
        self.assertStatus("DRAFT_STOPPED_PLAN_SCOPE", target=target, plan_raw=raw)

    def test_explicit_long_deadline_is_fixture_input_only(self):
        plan = deepcopy(self.plan)
        plan["start_deadline"] = plan["expires_at"]
        target, raw = self.rebind_plan(plan, start_deadline=plan["expires_at"])
        self.assertStatus("DRAFT_REVIEW_FIELDS_MATCH_ONLY", target=target,
                          plan_raw=raw, now=target.expires_at - 1)

    def test_stop_takes_precedence_over_every_input(self):
        self.assertStatus("DRAFT_STOPPED_BY_HUMAN", target=None, plan_raw=None,
                          run_reply=None, review_reply=None, now=None, stopped=True)

    def test_unknown_stop_state_stops(self):
        self.assertStatus("DRAFT_STOPPED_STOP_STATE_UNKNOWN", stopped=None)

    def test_numeric_stop_state_is_not_a_boolean(self):
        self.assertStatus("DRAFT_STOPPED_STOP_STATE_UNKNOWN", stopped=1)

    def test_changed_plan_bytes_are_not_accepted(self):
        plan = deepcopy(self.plan)
        plan["description"] = "different proposal"
        self.assertStatus("DRAFT_STOPPED_PLAN_BINDING", plan_raw=canonical(plan))

    def test_noncanonical_plan_is_not_silently_normalized(self):
        raw = json.dumps(self.plan, indent=2).encode()
        target = replace(self.target, plan_sha256=digest(raw))
        self.assertStatus("DRAFT_STOPPED_PLAN_BINDING", target=target, plan_raw=raw)

    def test_changed_packet_is_not_accepted_after_plan_rehash(self):
        plan = deepcopy(self.plan)
        plan["packet"]["observed_differences"] = 0
        target, raw = self.rebind_plan(plan)
        self.assertStatus("DRAFT_STOPPED_INPUT_BINDING", target=target, plan_raw=raw)

    def test_current_unbound_proposal_is_not_upgraded(self):
        plan = deepcopy(self.plan)
        del plan["approval_target"]
        target, raw = self.rebind_plan(plan)
        self.assertStatus("DRAFT_STOPPED_APPROVAL_TARGET_BINDING", target=target, plan_raw=raw)

    def test_multiple_reviews_are_ambiguous_even_when_equal(self):
        self.assertStatus("DRAFT_STOPPED_AMBIGUOUS_REVIEWS",
                          reviews=self.reviews + deepcopy(self.reviews))

    def test_conflicting_reviews_are_not_resolved_by_order(self):
        denied = deepcopy(self.reviews[0])
        denied["state"] = "rejected"
        self.assertStatus("DRAFT_STOPPED_AMBIGUOUS_REVIEWS", reviews=self.reviews + [denied])

    def test_repeated_reads_do_not_claim_one_time_execution(self):
        first, second = self.call(), self.call()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "DRAFT_REVIEW_FIELDS_MATCH_ONLY")
        # A durable shared claim remains the separate caller's responsibility.
        self.assertIs(second["shared_claim_obtained"], False)

    def test_inputs_remain_unchanged(self):
        before = canonical({"plan": self.plan, "run": self.run, "reviews": self.reviews})
        self.call()
        after = canonical({"plan": self.plan, "run": self.run, "reviews": self.reviews})
        self.assertEqual(before, after)

    def test_invalid_reply_object_stops(self):
        self.assertStatus("DRAFT_STOPPED_READ_UNRESOLVED",
                          review_reply={"status": 200, "body": b"[]"})

    def test_boolean_http_status_stops(self):
        self.assertStatus("DRAFT_STOPPED_READ_UNRESOLVED",
                          review_reply=READER.DraftGitHubReply(True, b"[]"))

    def test_unknown_review_list_shape_stops(self):
        self.assertStatus("DRAFT_STOPPED_REVIEW_SCHEMA", reviews={})

    def test_non_object_run_stops(self):
        self.assertStatus("DRAFT_STOPPED_RUN_BINDING", run=[])


def set_nested(value, path, new_value):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = new_value


def register_mutation_cases(kind, cases):
    """Give each boundary its own named unittest and visible failure reason."""
    for name, path, value, status in cases:
        def test(self, path=path, value=value, status=status, kind=kind):
            data = deepcopy(getattr(self, kind))
            set_nested(data, path, value)
            if kind == "plan":
                target, raw = self.rebind_plan(data)
                self.assertStatus(status, target=target, plan_raw=raw)
            else:
                self.assertStatus(status, **{kind: data})
        setattr(ReaderTests, "test_" + kind + "_" + name, test)


register_mutation_cases("run", [
    ("wrong_id", ["id"], 900_000_005, "DRAFT_STOPPED_RUN_BINDING"),
    ("boolean_id", ["id"], True, "DRAFT_STOPPED_RUN_BINDING"),
    ("attempt_two", ["run_attempt"], 2, "DRAFT_STOPPED_RUN_BINDING"),
    ("boolean_attempt", ["run_attempt"], True, "DRAFT_STOPPED_RUN_BINDING"),
    ("wrong_sha", ["head_sha"], "b" * 40, "DRAFT_STOPPED_RUN_BINDING"),
    ("other_branch", ["head_branch"], "another-branch", "DRAFT_STOPPED_RUN_BINDING"),
    ("wrong_workflow", ["path"], ".github/workflows/another.yml", "DRAFT_STOPPED_RUN_BINDING"),
    ("push_event", ["event"], "push", "DRAFT_STOPPED_RUN_BINDING"),
    ("other_repo_id", ["repository", "id"], 999, "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("other_repo_name", ["repository", "full_name"], "other/repo", "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("private_repo", ["repository", "private"], True, "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("fork_head", ["head_repository", "id"], 999, "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("private_head", ["head_repository", "private"], True, "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("boolean_repo_id", ["repository", "id"], True, "DRAFT_STOPPED_REPOSITORY_BINDING"),
    ("wrong_actor", ["actor", "id"], 999, "DRAFT_STOPPED_INITIATOR_BINDING"),
    ("wrong_triggerer", ["triggering_actor", "login"], "somebody", "DRAFT_STOPPED_INITIATOR_BINDING"),
    ("bot_actor", ["actor", "type"], "Bot", "DRAFT_STOPPED_INITIATOR_BINDING"),
    ("closed", ["status"], "completed", "DRAFT_STOPPED_RUN_CLOSED"),
    ("cancelled", ["conclusion"], "cancelled", "DRAFT_STOPPED_RUN_CLOSED"),
    ("unknown_status", ["status"], "unknown", "DRAFT_STOPPED_RUN_CLOSED"),
])
register_mutation_cases("reviews", [
    ("wrong_reviewer_id", [0, "user", "id"], 999, "DRAFT_STOPPED_REVIEWER_BINDING"),
    ("wrong_reviewer_login", [0, "user", "login"], "somebody", "DRAFT_STOPPED_REVIEWER_BINDING"),
    ("bot_reviewer", [0, "user", "type"], "Bot", "DRAFT_STOPPED_REVIEWER_BINDING"),
    ("boolean_reviewer_id", [0, "user", "id"], True, "DRAFT_STOPPED_REVIEWER_BINDING"),
    ("unknown_state", [0, "state"], "approve", "DRAFT_STOPPED_REVIEW_STATE_UNKNOWN"),
    ("null_state", [0, "state"], None, "DRAFT_STOPPED_REVIEW_STATE_UNKNOWN"),
    ("wrong_environment_id", [0, "environments", 0, "id"], 999, "DRAFT_STOPPED_ENVIRONMENT_BINDING"),
    ("wrong_environment_name", [0, "environments", 0, "name"], "OTHER", "DRAFT_STOPPED_ENVIRONMENT_BINDING"),
    ("boolean_environment_id", [0, "environments", 0, "id"], True, "DRAFT_STOPPED_ENVIRONMENT_BINDING"),
    ("no_environments", [0, "environments"], [], "DRAFT_STOPPED_ENVIRONMENT_SCOPE"),
    ("non_list_environments", [0, "environments"], {}, "DRAFT_STOPPED_ENVIRONMENT_SCOPE"),
    ("two_environments", [0, "environments"], [{"id": 1}, {"id": 2}], "DRAFT_STOPPED_ENVIRONMENT_SCOPE"),
])
register_mutation_cases("plan", [
    ("wrong_binding_run", ["approval_target", "run_id"], 999, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("wrong_binding_attempt", ["approval_target", "run_attempt"], 2, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("boolean_binding_attempt", ["approval_target", "run_attempt"], True, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("wrong_binding_sha", ["approval_target", "head_sha"], "b" * 40, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("wrong_binding_environment", ["approval_target", "environment_id"], 999, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("wrong_binding_packet", ["approval_target", "packet_sha256"], "b" * 64, "DRAFT_STOPPED_APPROVAL_TARGET_BINDING"),
    ("four_choices", ["choices"], ["approve", "revise", "reject", "stop"], "DRAFT_STOPPED_PLAN_SCOPE"),
    ("automatic_apply", ["automatic_apply"], True, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("final_adoption", ["final_adoption"], True, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("wrong_action", ["request", "action"], "APPLY_REPAIR", "DRAFT_STOPPED_PLAN_SCOPE"),
    ("wrong_scope", ["request", "scope"], "MODIFY_REPOSITORY", "DRAFT_STOPPED_PLAN_SCOPE"),
    ("two_regenerations", ["request", "max_regenerations"], 2, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("boolean_regenerations", ["request", "max_regenerations"], True, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("wrong_issued_time", ["issued_at"], 1_700_000_001, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("wrong_expiry_time", ["expires_at"], 1_700_000_100, "DRAFT_STOPPED_PLAN_SCOPE"),
    ("boolean_start_time", ["start_deadline"], True, "DRAFT_STOPPED_PLAN_SCOPE"),
])


def register_target_cases():
    cases = [
        ("boolean_run_id", {"run_id": True}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("zero_environment_id", {"environment_id": 0}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("invalid_sha", {"head_sha": "A" * 40}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("short_plan_hash", {"plan_sha256": "a" * 63}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("invalid_env_name", {"environment_name": "name/with/slash"}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("not_48_hours", {"expires_at": 1_700_000_100}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("negative_issue", {"issued_at": -1}, "DRAFT_STOPPED_TARGET_INVALID"),
        ("start_before_issue", {"start_deadline": 1_699_999_999}, "DRAFT_STOPPED_START_POLICY_INVALID"),
        ("start_at_issue", {"start_deadline": 1_700_000_000}, "DRAFT_STOPPED_START_POLICY_INVALID"),
        ("start_after_expiry", {"start_deadline": 1_700_172_801}, "DRAFT_STOPPED_START_POLICY_INVALID"),
        ("boolean_start", {"start_deadline": True}, "DRAFT_STOPPED_START_POLICY_INVALID"),
    ]
    for name, changes, status in cases:
        def test(self, changes=changes, status=status):
            self.assertStatus(status, target=replace(self.target, **changes))
        setattr(ReaderTests, "test_target_" + name, test)


register_target_cases()


def register_missing_fields():
    for kind, fields, status in [
        ("run", ["conclusion"], "DRAFT_STOPPED_RUN_CLOSED"),
        ("reviews", ["state", "user", "environments"], "DRAFT_STOPPED_REVIEW_SCHEMA"),
        ("plan", ["start_deadline", "choices", "request"], "DRAFT_STOPPED_PLAN_SCOPE"),
    ]:
        for field in fields:
            def test(self, kind=kind, field=field, status=status):
                data = deepcopy(getattr(self, kind))
                del (data[0] if kind == "reviews" else data)[field]
                if kind == "plan":
                    target, raw = self.rebind_plan(data)
                    self.assertStatus(status, target=target, plan_raw=raw)
                else:
                    self.assertStatus(status, **{kind: data})
            setattr(ReaderTests, "test_missing_" + kind + "_" + field, test)


register_missing_fields()


def register_reply_cases():
    malformed = [
        ("empty", b""),
        ("truncated", b"["),
        ("duplicate_key", b'[{"state":"approved","state":"rejected"}]'),
        ("bom", b"\xef\xbb\xbf[]"),
        ("nonfinite", b"[NaN]"),
        ("overflow", b"[1e9999]"),
        ("invalid_utf8", b"\xff"),
        ("unpaired_surrogate", br'["\ud800"]'),
        ("oversized", b" " * (READER.MAX_JSON_BYTES + 1)),
    ]
    for name, raw in malformed:
        def test(self, raw=raw):
            self.assertStatus("DRAFT_STOPPED_INVALID_JSON",
                              review_reply=READER.DraftGitHubReply(200, raw))
        setattr(ReaderTests, "test_reply_invalid_json_" + name, test)
    for status_code in (302, 403, 404, 429, 500):
        for field in ("run_reply", "review_reply"):
            def test(self, status_code=status_code, field=field):
                self.assertStatus("DRAFT_STOPPED_READ_UNRESOLVED",
                                  **{field: READER.DraftGitHubReply(status_code, b"[]")})
            setattr(ReaderTests, "test_" + field + "_http_" + str(status_code), test)


register_reply_cases()


if __name__ == "__main__":
    unittest.main(verbosity=2)
