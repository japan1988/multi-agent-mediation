import hashlib
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tasukeru_phase5b_handoff_gate import (  # noqa: E402
    ARTIFACT_INVALID,
    ARTIFACT_NAMES,
    ATTEMPT_ALREADY_USED,
    BOUNDARY_VALUE,
    CLAIMED,
    CONCURRENT_CLAIM_LOST,
    HANDOFF_EXPIRED,
    HANDOFF_INVALID,
    HANDOFF_MISSING,
    HANDOFF_NOT_ISSUED,
    HANDOFF_SCHEMA,
    MANIFEST_FILENAME,
    MANIFEST_HASH_MISMATCH,
    MANIFEST_SCHEMA,
    STOP_RESULT_SCHEMA,
    ClaimResult,
    acquire_handoff,
    initialize_state_db,
    record_issuance,
)


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


class Phase5BHandoffGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state.sqlite3"
        initialize_state_db(self.state)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def utc(value):
        return value.isoformat().replace("+00:00", "Z")

    def make_case(self, *, issued=True, expires=None, manifest_hash=None):
        hashes = {}
        for index, name in enumerate(ARTIFACT_NAMES):
            raw = f"fixture-{index}\n".encode()
            (self.root / name).write_bytes(raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
        manifest = {"schema_version": MANIFEST_SCHEMA, "artifacts": hashes}
        manifest_raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
        (self.root / MANIFEST_FILENAME).write_bytes(manifest_raw)
        issued_at = ((expires - timedelta(minutes=15)) if expires
                     else NOW - timedelta(minutes=5))
        handoff = {
            "schema_version": HANDOFF_SCHEMA,
            "handoff_id": str(uuid.uuid4()),
            "manifest_filename": MANIFEST_FILENAME,
            "manifest_sha256": manifest_hash or hashlib.sha256(manifest_raw).hexdigest(),
            "issued_at_utc": self.utc(issued_at),
            "expires_at_utc": self.utc(expires or issued_at + timedelta(minutes=15)),
            "consumption_policy": "single_attempt_irreversible",
            "simulation_boundary": dict(BOUNDARY_VALUE),
        }
        if issued:
            record_issuance(self.state, handoff)
        handoff_path = self.root / "handoff.json"
        handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
        return handoff_path, handoff

    def assert_stop_shape(self, result, primary):
        data = result.to_dict()
        self.assertEqual(list(data), [
            "schema_version", "decision", "primary_stop_reason",
            "additional_findings_detected", "additional_finding_count",
            "additional_findings", "diagnostic_coverage",
            "unexamined_conditions_may_exist", "automatic_retry",
            "external_side_effect_allowed", "human_review_required",
        ])
        self.assertEqual(data["schema_version"], STOP_RESULT_SCHEMA)
        self.assertEqual((data["decision"], data["primary_stop_reason"]),
                         ("STOPPED", primary))
        self.assertEqual(data["additional_finding_count"],
                         len(data["additional_findings"]))
        self.assertEqual(data["additional_findings_detected"],
                         bool(data["additional_findings"]))
        self.assertTrue(data["unexamined_conditions_may_exist"])
        self.assertFalse(data["automatic_retry"])
        self.assertFalse(data["external_side_effect_allowed"])
        self.assertTrue(data["human_review_required"])

    def test_valid_handoff_is_claimed_once_without_start_or_authority(self):
        handoff, _ = self.make_case()
        first = acquire_handoff(self.root, handoff, self.state, now=NOW)
        self.assertIsInstance(first, ClaimResult)
        self.assertEqual(first.reason_code, CLAIMED)
        self.assertFalse(first.phase5b_started)
        self.assertFalse(first.authority_granted)
        second = acquire_handoff(self.root, handoff, self.state, now=NOW)
        self.assert_stop_shape(second, ATTEMPT_ALREADY_USED)

    def test_missing_precedes_all_and_does_not_mutate_state(self):
        before = self.state.read_bytes()
        result = acquire_handoff(self.root, self.root / "missing.json", self.state, now=NOW)
        self.assert_stop_shape(result, HANDOFF_MISSING)
        self.assertEqual(before, self.state.read_bytes())

    def test_strict_json_rejects_duplicate_bom_extra_and_bad_uuid(self):
        cases = []
        handoff_path, handoff = self.make_case()
        cases.append(b'{"schema_version":"x","schema_version":"y"}\n')
        cases.append(b"\xef\xbb\xbf" + handoff_path.read_bytes())
        extra = dict(handoff); extra["extra"] = True
        cases.append(json.dumps(extra).encode())
        bad_uuid = dict(handoff); bad_uuid["handoff_id"] = "h-001"
        cases.append(json.dumps(bad_uuid).encode())
        for index, raw in enumerate(cases):
            with self.subTest(index=index):
                path = self.root / f"bad-{index}.json"
                path.write_bytes(raw)
                self.assert_stop_shape(
                    acquire_handoff(self.root, path, self.state, now=NOW),
                    HANDOFF_INVALID,
                )

    def test_expired_is_primary_and_additional_findings_are_reported(self):
        handoff_path, _ = self.make_case(
            issued=False, expires=NOW - timedelta(minutes=5),
            manifest_hash="0" * 64,
        )
        result = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assert_stop_shape(result, HANDOFF_EXPIRED)
        self.assertEqual(result.additional_findings,
                         (HANDOFF_NOT_ISSUED, MANIFEST_HASH_MISMATCH))
        self.assertEqual(result.diagnostic_coverage, "FULL_READ_ONLY_SCOPE")

    def test_not_issued_stops_before_claim(self):
        handoff_path, _ = self.make_case(issued=False)
        result = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assert_stop_shape(result, HANDOFF_NOT_ISSUED)
        with sqlite3.connect(self.state) as connection:
            count = connection.execute("SELECT count(*) FROM phase5b_handoff_attempts").fetchone()[0]
        self.assertEqual(count, 0)

    def test_post_claim_manifest_failure_is_consumed_rejected(self):
        handoff_path, handoff = self.make_case(manifest_hash="0" * 64)
        result = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assert_stop_shape(result, MANIFEST_HASH_MISMATCH)
        with sqlite3.connect(self.state) as connection:
            row = connection.execute(
                "SELECT state, primary_stop_reason FROM phase5b_handoff_attempts "
                "WHERE handoff_id = ?", (handoff["handoff_id"],)
            ).fetchone()
        self.assertEqual(row, ("CONSUMED_REJECTED", MANIFEST_HASH_MISMATCH))
        replay = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assert_stop_shape(replay, ATTEMPT_ALREADY_USED)

    def test_artifact_tamper_after_issuance_is_consumed_rejected(self):
        handoff_path, handoff = self.make_case()
        (self.root / ARTIFACT_NAMES[0]).write_text("tampered\n", encoding="utf-8")
        result = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assert_stop_shape(result, ARTIFACT_INVALID)
        with sqlite3.connect(self.state) as connection:
            state = connection.execute(
                "SELECT state FROM phase5b_handoff_attempts WHERE handoff_id = ?",
                (handoff["handoff_id"],),
            ).fetchone()[0]
        self.assertEqual(state, "CONSUMED_REJECTED")

    def test_concurrent_claim_has_one_winner_and_one_loser(self):
        handoff_path, _ = self.make_case()
        opened = threading.Event(); release = threading.Event(); results = {}

        def after_begin():
            opened.set(); self.assertTrue(release.wait(5))

        def winner():
            results["winner"] = acquire_handoff(
                self.root, handoff_path, self.state, now=NOW, _after_begin=after_begin)

        thread = threading.Thread(target=winner)
        thread.start(); self.assertTrue(opened.wait(5))
        results["loser"] = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        release.set(); thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(results["winner"], ClaimResult)
        self.assert_stop_shape(results["loser"], CONCURRENT_CLAIM_LOST)

    def test_primary_is_not_duplicated_and_additional_order_is_fixed(self):
        handoff_path, _ = self.make_case(
            issued=False, expires=NOW - timedelta(minutes=5), manifest_hash="0" * 64)
        (self.root / ARTIFACT_NAMES[0]).unlink()
        result = acquire_handoff(self.root, handoff_path, self.state, now=NOW)
        self.assertEqual(result.primary_stop_reason, HANDOFF_EXPIRED)
        self.assertEqual(result.additional_findings,
                         (HANDOFF_NOT_ISSUED, MANIFEST_HASH_MISMATCH, ARTIFACT_INVALID))
        self.assertNotIn(result.primary_stop_reason, result.additional_findings)


if __name__ == "__main__":
    unittest.main()
