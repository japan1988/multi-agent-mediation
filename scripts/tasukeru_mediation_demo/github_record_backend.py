"""DRAFT: GitHub record-storage protocol adapter; live entry is unconnected.

目的:
  別のActions実行でも、提案・承認の使用・却下・停止を同じ保存先で照合し、
  同じ承認の二重使用や停止後の再開を拒否する保存処理の接続を準備する。
処理:
  明示指定されたタグ保護ルールを照合し、固定名前空間の記録を読み取る。
  新しい記録はGit blob、annotated tag、参照の順に作り、参照を一度だけ作成する。
  更新・削除・自動再試行は行わず、不一致・取得失敗・結果不明を停止へ渡す。
範囲:
  保存だけを担当する。本人確認、承認期限、実行許可の確認は呼出側の責任。
  ファイルを追加するだけでは、実承認や既存ワークフローは有効・変更にならない。

No HTTP client, token lookup, automatic configuration, or workflow is installed.
A future separately reviewed caller must supply a bounded, authenticated transport
restricted to https://api.github.com and the fixed repository below, without
redirects or retries. Its callable contract is transport(method, path, payload),
returning GitHubReply(status, raw_json_bytes). Supplying transport is not approval.

The current ruleset snapshot is checked, not its uninterrupted lifetime. Protection
retention, authorized writers and approval binding still need separate review.
An administrator who removes protection and records is outside this guarantee.
Any uncertain POST blocks this instance; a new instance must not be used to retry
the old grant. Caller-side run closure is required before any live connection.
Intermediate Git objects may exist after failure; no cleanup or rollback is done.

Protocol references (primary documentation):
https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset
https://docs.github.com/en/rest/git/refs#list-matching-references
https://docs.github.com/en/rest/git/refs#create-a-reference
https://docs.github.com/en/rest/git/tags#create-a-tag-object
https://docs.github.com/en/rest/git/blobs#create-a-blob
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json


REPOSITORY = "japan1988/multi-agent-mediation"
API_ROOT = "/repos/" + REPOSITORY
MAX_RESPONSE_BYTES = 1024 * 1024
TAG_MESSAGE = "TASUKERU_SHARED_RECORD_DRAFT_V1"


class BackendReadUnresolved(Exception):
    """A read failure is not proof that a record is absent."""


@dataclass(frozen=True)
class GitHubReply:
    status: int
    body: bytes


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _strict_response(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_RESPONSE_KEY")
            result[key] = value
        return result
    if (type(raw) is not bytes or not raw or len(raw) > MAX_RESPONSE_BYTES
            or raw.startswith(b"\xef\xbb\xbf")):
        raise BackendReadUnresolved("INVALID_RESPONSE_BYTES")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _json_bytes(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise BackendReadUnresolved("INVALID_RESPONSE_JSON") from None


def _hex(value, length):
    return (type(value) is str and len(value) == length
            and all(char in "0123456789abcdef" for char in value))


def _blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class GitHubRecordBackendDraft:
    """Create-only adapter. Defaults are disabled; no human authority is inferred."""

    def __init__(self, store_module, transport=None, *, expected_policy=None,
                 ruleset_id=None, ruleset_sha256=None):
        self.module = store_module
        self.transport = transport
        self.expected_policy = (_strict_response(_json_bytes(expected_policy))
                                if expected_policy is not None else None)
        self.ruleset_id = ruleset_id
        self.ruleset_sha256 = ruleset_sha256
        self._attempted = set()
        self._write_unresolved = False

    def _allowed_route(self, method, path):
        if type(path) is not str:
            return False
        if method == "POST":
            return path in {API_ROOT + "/git/blobs", API_ROOT + "/git/tags",
                            API_ROOT + "/git/refs"}
        if method != "GET":
            return False
        if (type(self.ruleset_id) is int and self.ruleset_id > 0
                and path == API_ROOT + "/rulesets/" + str(self.ruleset_id)):
            return True
        for kind in ("tags", "blobs"):
            prefix = API_ROOT + "/git/" + kind + "/"
            if path.startswith(prefix) and _hex(path[len(prefix):], 40):
                return True
        prefix = API_ROOT + "/git/matching-refs/"
        if path.startswith(prefix):
            try:
                self._reference("refs/" + path[len(prefix):])
                return True
            except BackendReadUnresolved:
                pass
        return False

    def _request(self, method, path, payload=None):
        if (self.transport is None or not callable(self.transport)
                or not self._allowed_route(method, path)
                or ".." in path or "%" in path):
            raise BackendReadUnresolved("TRANSPORT_UNCONFIGURED_OR_SCOPE_INVALID")
        try:
            reply = self.transport(method, path, payload)
        except Exception:
            raise BackendReadUnresolved("TRANSPORT_RESULT_UNRESOLVED") from None
        if (type(reply) is not GitHubReply or type(reply.status) is not int
                or not 100 <= reply.status <= 599 or type(reply.body) is not bytes
                or len(reply.body) > MAX_RESPONSE_BYTES):
            raise BackendReadUnresolved("REPLY_UNVERIFIED")
        # Never follow redirects or retry a request.
        return reply

    def _get(self, path):
        reply = self._request("GET", path)
        if reply.status != 200:
            raise BackendReadUnresolved("GET_NOT_CONFIRMED_SUCCESS")
        return _strict_response(reply.body)

    def policy(self):
        expected = self.expected_policy
        if (type(expected) is not dict or type(self.ruleset_id) is not int
                or self.ruleset_id <= 0 or not _hex(self.ruleset_sha256, 64)):
            raise BackendReadUnresolved("REVIEWED_PROTECTION_PIN_UNCONFIGURED")
        # Reuse Stage 1's strict normalized-policy validation. The fake reader
        # below validates the specification only; it is not server evidence.
        class SpecificationOnly:
            def policy(inner):
                return expected
        self.module.SharedRecordStoreDraft(
            SpecificationOnly(), expected_authority=expected
        )._authority()
        value = self._get(API_ROOT + "/rulesets/" + str(self.ruleset_id))
        if (type(value) is not dict
                or hashlib.sha256(_json_bytes(value)).hexdigest() != self.ruleset_sha256
                or type(value.get("id")) is not int or value["id"] != self.ruleset_id
                or value.get("source_type") != "Repository"
                or value.get("source") != REPOSITORY or value.get("target") != "tag"
                or value.get("enforcement") != "active"
                or "bypass_actors" not in value or value["bypass_actors"] != []):
            raise BackendReadUnresolved("PROTECTION_SNAPSHOT_CHANGED_OR_UNSUPPORTED")
        include = sorted(prefix + "*" for prefix in self.module.SHARED_PREFIXES.values())
        conditions = value.get("conditions")
        if conditions != {"ref_name": {"include": include, "exclude": []}}:
            raise BackendReadUnresolved("PROTECTION_SCOPE_UNRESOLVED")
        rules = value.get("rules")
        supported = [
            [{"type": "update"}, {"type": "deletion"}],
            [{"type": "update", "parameters": {"update_allows_fetch_and_merge": False}},
             {"type": "deletion"}],
        ]
        if (type(rules) is not list or len(rules) != 2
                or not any(sorted(rules, key=lambda x: _json_bytes(x)) ==
                           sorted(choice, key=lambda x: _json_bytes(x))
                           for choice in supported)):
            raise BackendReadUnresolved("PROTECTION_RULES_UNSUPPORTED")
        return _strict_response(_json_bytes(expected))

    def _reference(self, reference):
        if type(reference) is str:
            for kind, prefix in self.module.SHARED_PREFIXES.items():
                if reference.startswith(prefix) and _hex(reference[len(prefix):], 64):
                    return kind, reference[len(prefix):]
        raise BackendReadUnresolved("REFERENCE_OUTSIDE_FIXED_SCOPE")

    def _read_after_policy(self, reference):
        self._reference(reference)
        # Only a successful collection response [] means confirmed absence.
        # In particular, 404/403/timeout are never converted into absence.
        values = self._get(API_ROOT + "/git/matching-refs/" + reference[5:])
        if values == []:
            return None
        if (type(values) is not list or len(values) != 1
                or type(values[0]) is not dict or values[0].get("ref") != reference):
            raise BackendReadUnresolved("EXACT_REFERENCE_UNRESOLVED")
        obj = values[0].get("object")
        if type(obj) is not dict or obj.get("type") != "tag" or not _hex(obj.get("sha"), 40):
            raise BackendReadUnresolved("REFERENCE_OBJECT_UNSUPPORTED")
        tag = self._get(API_ROOT + "/git/tags/" + obj["sha"])
        if (type(tag) is not dict or tag.get("sha") != obj["sha"]
                or tag.get("tag") != reference[10:] or tag.get("message") != TAG_MESSAGE):
            raise BackendReadUnresolved("TAG_BINDING_UNVERIFIED")
        target = tag.get("object")
        if type(target) is not dict or target.get("type") != "blob" or not _hex(target.get("sha"), 40):
            raise BackendReadUnresolved("TAG_TARGET_UNSUPPORTED")
        blob = self._get(API_ROOT + "/git/blobs/" + target["sha"])
        if (type(blob) is not dict or blob.get("sha") != target["sha"]
                or blob.get("encoding") != "base64" or type(blob.get("content")) is not str
                or type(blob.get("size")) is not int
                or not 0 < blob["size"] <= self.module.MAX_SHARED_RECORD_BYTES):
            raise BackendReadUnresolved("BLOB_METADATA_UNVERIFIED")
        try:
            raw = base64.b64decode(blob["content"].replace("\n", ""), validate=True)
        except (ValueError, UnicodeError):
            raise BackendReadUnresolved("BLOB_ENCODING_INVALID") from None
        if len(raw) != blob["size"] or _blob_sha(raw) != target["sha"]:
            raise BackendReadUnresolved("BLOB_BYTES_UNVERIFIED")
        value = self.module._shared_document(raw)
        kind, key = self._reference(reference)
        if value.get("kind") != kind or value.get("run_key") != key:
            raise BackendReadUnresolved("RECORD_REFERENCE_BINDING_MISMATCH")
        return raw

    def read_exact(self, reference):
        self._reference(reference)
        self.policy()
        return self._read_after_policy(reference)

    def create_once(self, reference, raw):
        kind, key = self._reference(reference)
        value = self.module._shared_document(raw)
        if value.get("kind") != kind or value.get("run_key") != key:
            raise BackendReadUnresolved("RECORD_REFERENCE_BINDING_MISMATCH")
        if self._write_unresolved:
            raise self.module.SharedRecordResultUnknown("INSTANCE_CLOSED_AFTER_UNKNOWN_WRITE")
        if reference in self._attempted:
            raise self.module.SharedRecordConflict("INSTANCE_ALREADY_ATTEMPTED_REFERENCE")
        self.policy()
        if self._read_after_policy(reference) is not None:
            raise self.module.SharedRecordConflict("REFERENCE_ALREADY_EXISTS")
        self._attempted.add(reference)
        # Fail closed before the first POST, including failures between objects.
        self._write_unresolved = True
        try:
            blob_reply = self._request("POST", API_ROOT + "/git/blobs", {
                "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"
            })
            if blob_reply.status in {401, 403}:
                raise self.module.SharedRecordDenied("FIRST_WRITE_CONFIRMED_FORBIDDEN")
            if blob_reply.status != 201:
                raise BackendReadUnresolved("BLOB_CREATION_UNRESOLVED")
            blob = _strict_response(blob_reply.body)
            if type(blob) is not dict or blob.get("sha") != _blob_sha(raw):
                raise BackendReadUnresolved("CREATED_BLOB_DIGEST_UNVERIFIED")
            self.policy()
            tag_reply = self._request("POST", API_ROOT + "/git/tags", {
                "tag": reference[10:], "message": TAG_MESSAGE,
                "object": blob["sha"], "type": "blob",
                # Synthetic technical metadata; it is not a human approval.
                "tagger": {"name": "Tasukeru Record Adapter",
                           "email": "tasukeru-record@example.invalid",
                           "date": "2000-01-01T00:00:00Z"},
            })
            if tag_reply.status != 201:
                raise BackendReadUnresolved("TAG_CREATION_UNRESOLVED")
            tag = _strict_response(tag_reply.body)
            if (type(tag) is not dict or not _hex(tag.get("sha"), 40)
                    or tag.get("tag") != reference[10:] or tag.get("message") != TAG_MESSAGE
                    or tag.get("object", {}).get("type") != "blob"
                    or tag["object"].get("sha") != blob["sha"]):
                raise BackendReadUnresolved("CREATED_TAG_BINDING_UNVERIFIED")
            self.policy()
            ref_reply = self._request("POST", API_ROOT + "/git/refs", {
                "ref": reference, "sha": tag["sha"]
            })
            if ref_reply.status in {409, 422}:
                # Read-only disambiguation. A status code alone is not proof.
                if self._read_after_policy(reference) is not None:
                    raise self.module.SharedRecordConflict("REFERENCE_EXISTS_AFTER_CONFLICT")
                raise BackendReadUnresolved("REF_REJECTION_UNRESOLVED")
            if ref_reply.status != 201:
                raise BackendReadUnresolved("REF_CREATION_UNRESOLVED")
            ref = _strict_response(ref_reply.body)
            if (type(ref) is not dict or ref.get("ref") != reference
                    or ref.get("object", {}).get("type") != "tag"
                    or ref["object"].get("sha") != tag["sha"]):
                raise BackendReadUnresolved("CREATED_REFERENCE_UNVERIFIED")
            self.policy()
            if self._read_after_policy(reference) != raw:
                raise BackendReadUnresolved("POST_WRITE_BYTES_UNVERIFIED")
            self._write_unresolved = False
            return {"reference": reference, "sha256": hashlib.sha256(raw).hexdigest(),
                    "created": True}
        except (self.module.SharedRecordDenied, self.module.SharedRecordConflict):
            raise
        except Exception:
            raise self.module.SharedRecordResultUnknown("WRITE_RESULT_UNKNOWN_NO_RETRY") from None
