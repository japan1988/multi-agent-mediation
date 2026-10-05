"""DRAFT: inspect GitHub review evidence without granting execution authority.

目的: GitHubの承認記録について、本人のID・提案・入力・対象実行・期限を照合する。
範囲: approve/rejectの2択を想定した、未接続の読み取り処理だけ。
一致しても実行許可は返さない。共有台帳の一回限り取得は別途必要。

No HTTP client, token lookup, repository write, AI call, environment configuration
or workflow change is installed. All supplied responses are untrusted data.
A future reviewed caller must fetch them from the fixed GitHub API over verified
TLS, validate the actual environment protections and immutable proposal binding,
and obtain a durable one-use claim before proceeding. This module does not do so.

The review-history response does not itself bind a proposal digest or identify a
run attempt. Its environment created_at/updated_at fields are NOT approval times.
This first draft refuses run attempts other than 1, multiple reviews, multi-
environment reviews, and closed runs instead of inferring which approval applies.
It also requires an explicit processing-start deadline; the relationship between
that deadline and the adopted 48-hour proposal lifetime is not chosen here.

Current proposals lack approval_target and therefore cannot be silently upgraded.
Repeated reads can return the same evidence; no replay-store or authenticated
approval grant is implemented. Stop is local only, not remote cancellation.
Comments in review responses are ignored as data and never executed or exported.

Primary schema reference:
https://docs.github.com/en/rest/actions/workflow-runs#get-the-review-history-for-a-workflow-run
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

REPOSITORY = "japan1988/multi-agent-mediation"
REPOSITORY_ID = 1015944722
REVIEWER_LOGIN = "japan1988"
REVIEWER_ID = 219815083
WORKFLOW_PATH = ".github/workflows/tasukeru-mediation-confirmation.yml"
PROPOSAL_LIFETIME = 48 * 60 * 60
MAX_JSON_BYTES = 1024 * 1024


@dataclass(frozen=True)
class DraftGitHubReply:
    status: int
    body: bytes


@dataclass(frozen=True)
class DraftReviewTarget:
    run_id: int
    head_sha: str
    environment_id: int
    environment_name: str
    plan_sha256: str
    packet_sha256: str
    issued_at: int
    expires_at: int
    start_deadline: int | None = None


class _Stopped(Exception):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value, length):
    return type(value) is str and re.fullmatch("[0-9a-f]{" + str(length) + "}", value) is not None


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    if (type(raw) is not bytes or not raw or len(raw) > MAX_JSON_BYTES
            or raw.startswith(b"\xef\xbb\xbf")):
        raise _Stopped("DRAFT_STOPPED_INVALID_JSON")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _canonical(value)  # Reject unpaired surrogates and nonfinite values.
        return value
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise _Stopped("DRAFT_STOPPED_INVALID_JSON") from None


def _reply(reply):
    if type(reply) is not DraftGitHubReply or type(reply.status) is not int or reply.status != 200:
        raise _Stopped("DRAFT_STOPPED_READ_UNRESOLVED")
    return _json(reply.body)


def _positive(value):
    return type(value) is int and value > 0


def _identity(user):
    return (type(user) is dict and type(user.get("id")) is int
            and user["id"] == REVIEWER_ID
            and user.get("login") == REVIEWER_LOGIN and user.get("type") == "User")


def _target(target, now):
    if (type(target) is not DraftReviewTarget or not _positive(target.run_id)
            or not _positive(target.environment_id) or not _hex(target.head_sha, 40)
            or not _hex(target.plan_sha256, 64) or not _hex(target.packet_sha256, 64)
            or type(target.environment_name) is not str
            or re.fullmatch("[A-Za-z0-9_-]{1,64}", target.environment_name) is None
            or type(target.issued_at) is not int or target.issued_at < 0
            or type(target.expires_at) is not int
            or target.expires_at - target.issued_at != PROPOSAL_LIFETIME
            or type(now) is not int or now < target.issued_at):
        raise _Stopped("DRAFT_STOPPED_TARGET_INVALID")
    if target.start_deadline is None:
        raise _Stopped("DRAFT_STOPPED_START_POLICY_UNRESOLVED")
    if (type(target.start_deadline) is not int
            or not target.issued_at < target.start_deadline <= target.expires_at):
        raise _Stopped("DRAFT_STOPPED_START_POLICY_INVALID")
    if now >= target.expires_at:
        raise _Stopped("DRAFT_STOPPED_PROPOSAL_EXPIRED")
    if now >= target.start_deadline:
        raise _Stopped("DRAFT_STOPPED_START_DEADLINE")


def _plan(target, raw):
    plan = _json(raw)
    if type(plan) is not dict or _canonical(plan) != raw or _sha(raw) != target.plan_sha256:
        raise _Stopped("DRAFT_STOPPED_PLAN_BINDING")
    required_binding = {
        "repository": REPOSITORY, "repository_id": REPOSITORY_ID,
        "run_id": target.run_id, "run_attempt": 1, "head_sha": target.head_sha,
        "environment_id": target.environment_id,
        "environment_name": target.environment_name,
        "packet_sha256": target.packet_sha256,
    }
    binding = plan.get("approval_target")
    if (type(binding) is not dict or set(binding) != set(required_binding)
            or _canonical(binding) != _canonical(required_binding)):
        raise _Stopped("DRAFT_STOPPED_APPROVAL_TARGET_BINDING")
    request = plan.get("request")
    if (plan.get("choices") != ["approve", "reject"]
            or type(plan.get("issued_at")) is not int or plan["issued_at"] != target.issued_at
            or type(plan.get("expires_at")) is not int or plan["expires_at"] != target.expires_at
            or type(plan.get("start_deadline")) is not int
            or plan["start_deadline"] != target.start_deadline
            or plan.get("automatic_apply") is not False or plan.get("final_adoption") is not False
            or type(request) is not dict
            or request.get("action") != "REGENERATE_MEDIATION_DRAFT_ONCE"
            or request.get("scope") != "REPORT_ONLY_NO_APPLICATION"
            or type(request.get("max_regenerations")) is not int
            or request["max_regenerations"] != 1):
        raise _Stopped("DRAFT_STOPPED_PLAN_SCOPE")
    if type(plan.get("packet")) is not dict or _sha(_canonical(plan["packet"])) != target.packet_sha256:
        raise _Stopped("DRAFT_STOPPED_INPUT_BINDING")


def _run(target, value):
    if type(value) is not dict:
        raise _Stopped("DRAFT_STOPPED_RUN_BINDING")
    for field in ("repository", "head_repository"):
        repo = value.get(field)
        if (type(repo) is not dict or type(repo.get("id")) is not int
                or repo["id"] != REPOSITORY_ID or repo.get("full_name") != REPOSITORY
                or repo.get("private") is not False):
            raise _Stopped("DRAFT_STOPPED_REPOSITORY_BINDING")
    if (type(value.get("id")) is not int or value["id"] != target.run_id
            or type(value.get("run_attempt")) is not int or value["run_attempt"] != 1
            or value.get("head_sha") != target.head_sha or value.get("head_branch") != "main"
            or value.get("event") != "workflow_dispatch"
            or value.get("path") != WORKFLOW_PATH):
        raise _Stopped("DRAFT_STOPPED_RUN_BINDING")
    if not _identity(value.get("actor")) or not _identity(value.get("triggering_actor")):
        raise _Stopped("DRAFT_STOPPED_INITIATOR_BINDING")
    if (value.get("status") not in ("waiting", "in_progress")
            or "conclusion" not in value or value["conclusion"] is not None):
        raise _Stopped("DRAFT_STOPPED_RUN_CLOSED")


def _review(target, rows):
    if type(rows) is not list:
        raise _Stopped("DRAFT_STOPPED_REVIEW_SCHEMA")
    if not rows:
        return "DRAFT_WAITING_FOR_REVIEW", "none"
    if len(rows) != 1:
        raise _Stopped("DRAFT_STOPPED_AMBIGUOUS_REVIEWS")
    row = rows[0]
    if (type(row) is not dict or set(row) - {"state", "comment", "environments", "user"}
            or not {"state", "environments", "user"} <= set(row)):
        raise _Stopped("DRAFT_STOPPED_REVIEW_SCHEMA")
    if not _identity(row["user"]):
        raise _Stopped("DRAFT_STOPPED_REVIEWER_BINDING")
    environments = row["environments"]
    if type(environments) is not list or len(environments) != 1:
        raise _Stopped("DRAFT_STOPPED_ENVIRONMENT_SCOPE")
    environment = environments[0]
    if (type(environment) is not dict or type(environment.get("id")) is not int
            or environment["id"] != target.environment_id
            or environment.get("name") != target.environment_name):
        raise _Stopped("DRAFT_STOPPED_ENVIRONMENT_BINDING")
    if row["state"] == "approved":
        return "DRAFT_REVIEW_FIELDS_MATCH_ONLY", "approve"
    if row["state"] == "rejected":
        return "DRAFT_REJECTION_OBSERVED", "reject"
    raise _Stopped("DRAFT_STOPPED_REVIEW_STATE_UNKNOWN")


def inspect_review_evidence(target, plan_raw, run_reply, review_reply, now, *, stopped=False):
    """Read-only field comparison. Never returns an execution grant."""
    status, decision = "DRAFT_STOPPED_INVALID_DATA", "none"
    try:
        if stopped is True:
            raise _Stopped("DRAFT_STOPPED_BY_HUMAN")
        if type(stopped) is not bool:
            raise _Stopped("DRAFT_STOPPED_STOP_STATE_UNKNOWN")
        _target(target, now)
        _plan(target, plan_raw)
        _run(target, _reply(run_reply))
        status, decision = _review(target, _reply(review_reply))
    except _Stopped as error:
        status = str(error)
    except (TypeError, ValueError, KeyError, RecursionError):
        status = "DRAFT_STOPPED_INVALID_DATA"
    return {
        "status": status, "decision": decision,
        "execution_allowed": False, "human_authentication_tested": False,
        "source_authenticity": "NOT_VERIFIED_BY_THIS_MODULE",
        "shared_claim_obtained": False, "real_AI_calls": 0,
        "automatic_apply": False, "final_adoption": "NOT_DETERMINED",
    }
