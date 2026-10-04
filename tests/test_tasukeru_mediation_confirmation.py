"""Deterministic fixture checks. No real identity, AI, or GitHub writes.

Run with Python 3.12:
  python -I -B tests/test_tasukeru_mediation_confirmation.py
The workflow entry also emits the result as self-test/report.json.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ENTRY = DEMO = GATE = CONTROLLER = None


def configure(entry, demo, gate, controller):
    global ENTRY, DEMO, GATE, CONTROLLER
    ENTRY, DEMO, GATE, CONTROLLER = entry, demo, gate, controller


def ensure_modules():
    if ENTRY is None:
        path = ROOT / "scripts/tasukeru_mediation_demo/run_confirmation.py"
        spec = importlib.util.spec_from_file_location("confirmation_test_entry", path)
        entry = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = entry
        spec.loader.exec_module(entry)
        demo = entry.pinned_demo(ROOT)
        configure(entry, demo, *demo.modules())


class ConfirmationChecks(unittest.TestCase):
    def setUp(self):
        ensure_modules()
        self.work = tempfile.TemporaryDirectory(prefix="confirmation-test-")
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.packet = DEMO.synthetic_packet()
        self.good, self.initial, self.valid = ENTRY.candidate_bytes(DEMO, GATE, self.packet)
        self.frozen = {"observer_zip_sha256": "a" * 64, "manifest_sha256": "b" * 64,
                       "packet_sha256": ENTRY.digest(ENTRY.encode(self.packet)),
                       "authority_epoch": CONTROLLER.AUTHORITY_EPOCH,
                       "adapter_sha256": ENTRY.digest(Path(ENTRY.__file__).read_bytes())}
        self.network = patch.object(socket, "socket", side_effect=AssertionError("NETWORK_NOT_PERMITTED_IN_FIXTURE_TEST"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def create_plan(self):
        store = ENTRY.LocalSimulationStore.prepare_new(self.directory / "shared.sqlite")
        authority = ENTRY.FixtureAuthority()
        experiment = ENTRY.ConfirmationExperiment(GATE, CONTROLLER, store, authority,
                                                  lambda: self.frozen.copy(), lambda: 1000)
        plan, plan_hash, _ = experiment.propose("PLAN", self.packet, self.initial)
        return store, authority, experiment, plan, plan_hash

    def probe(self, store, plan):
        # Separate Python process, the same local SQLite model. Never GitHub.
        script = '''import importlib.util,json,pathlib,sys
path=pathlib.Path(sys.argv[1]);spec=importlib.util.spec_from_file_location("child_entry",path)
entry=importlib.util.module_from_spec(spec);sys.modules[spec.name]=entry;spec.loader.exec_module(entry)
demo=entry.pinned_demo(path.parents[2]);gate,controller=demo.modules()
store=entry.LocalSimulationStore(sys.argv[2]);plan,plan_hash,*_=store.get("PLAN")
authority=entry.FixtureAuthority();experiment=entry.ConfirmationExperiment(gate,controller,store,authority,lambda:plan["context"],lambda:1000)
calls=[]
def generate(_):
    calls.append(1);good=gate.make_fixture_proposal(plan["packet"])
    return {"state":"COMPLETED","payload":demo.encoded(good)}
result=experiment.resume("PLAN",authority.event("PLAN",plan_hash),generate,plan)
print(json.dumps({"state":result["state"],"mock_calls":len(calls),"api_calls":result["real_AI_calls"]}))
'''
        return [sys.executable, "-I", "-B", "-c", script, ENTRY.__file__, str(store.path)]

    def test_process_restart_denies_consumed_plan(self):
        store, authority, experiment, plan, plan_hash = self.create_plan()
        result = experiment.resume("PLAN", authority.event("PLAN", plan_hash),
                                   lambda _: {"state": "COMPLETED", "payload": self.valid}, plan)
        self.assertEqual(result["state"], "HUMAN_REVIEW")
        response = subprocess.run(self.probe(store, plan), capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(json.loads(response.stdout), {"state": "DENIED_USED_OR_CLOSED", "mock_calls": 0, "api_calls": 0})

    def test_two_processes_claim_once(self):
        store, _, _, plan, _ = self.create_plan()
        processes = [subprocess.Popen(self.probe(store, plan), stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for _ in range(2)]
        rows = []
        try:
            for process in processes:
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, err)
                rows.append(json.loads(out))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=2)
        self.assertEqual(sorted(x["state"] for x in rows), ["DENIED_USED_OR_CLOSED", "HUMAN_REVIEW"])
        self.assertEqual(sum(x["mock_calls"] for x in rows), 1)
        self.assertEqual(store.get("PLAN")[3], 1)

    def test_new_process_replay_after_process_result(self):
        store, _, _, plan, _ = self.create_plan()
        first = subprocess.run(self.probe(store, plan), capture_output=True, text=True, timeout=10, check=True)
        again = subprocess.run(self.probe(store, plan), capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(json.loads(first.stdout)["mock_calls"], 1)
        self.assertEqual(json.loads(again.stdout)["state"], "DENIED_USED_OR_CLOSED")
        self.assertEqual(json.loads(again.stdout)["mock_calls"], 0)

    def test_initializing_existing_store_preserves_it(self):
        store, _, _, _, _ = self.create_plan()
        original = store.path.read_bytes()
        with self.assertRaises(FileExistsError):
            ENTRY.LocalSimulationStore.prepare_new(store.path)
        self.assertEqual(store.path.read_bytes(), original)

    def test_terminal_stop_cannot_be_overwritten(self):
        store, _, _, _, plan_hash = self.create_plan()
        store.decide_once("PLAN", plan_hash, "approve")
        store.stop_during_request("PLAN")
        with self.assertRaises(ENTRY.GateStopped):
            store.finish("PLAN", {"state": "HUMAN_REVIEW"})
        self.assertEqual(store.get("PLAN")[2], "STOPPED_BY_HUMAN")

    def test_rejected_plan_cannot_be_finished_as_success(self):
        store, _, _, _, plan_hash = self.create_plan()
        store.decide_once("PLAN", plan_hash, "reject")
        with self.assertRaises(ENTRY.GateStopped):
            store.finish("PLAN", {"state": "HUMAN_REVIEW"})
        self.assertEqual(store.get("PLAN")[2], "REJECTED_BY_HUMAN")

    def test_stored_payload_corruption_is_detected(self):
        store, authority, experiment, plan, plan_hash = self.create_plan()
        with store.connection() as con:
            con.execute("UPDATE plans SET payload=? WHERE id='PLAN'", (b'{}',))
        calls = []
        result = experiment.resume("PLAN", authority.event("PLAN", plan_hash), lambda _: calls.append(1), plan)
        self.assertEqual(result["state"], "STOPPED_PLAN_UNKNOWN")
        self.assertEqual(calls, [])

    def test_unknown_stop_is_not_claimed_as_persisted(self):
        store, _, _, _, _ = self.create_plan()
        with self.assertRaises(ENTRY.GateStopped):
            store.stop_during_request("UNKNOWN_PLAN")

    def check_dispatch_request(self, mode, decision):
        output = self.directory / "dispatch-report"
        # No baseline/input lookup may precede an explicit stop or live request.
        with patch.object(ENTRY, "pinned_demo", side_effect=AssertionError("SOURCE_READ_BEFORE_STOP")):
            code = ENTRY.main(["--mode", mode, "--decision", decision,
                               "--repo-root", str(self.directory / "absent-repository"),
                               "--output", str(output)])
        self.assertEqual(code, 0)
        report = json.loads((output / "report.json").read_bytes())
        self.assertEqual(report["status"], "LIVE_RESPONSE_BLOCKED")
        self.assertEqual(report["mock_generations"], 0)
        self.assertFalse(report["approval_accepted"])
        if decision == "stop":
            self.assertEqual(report["state"], "STOPPED_BY_HUMAN_LOCAL_ONLY")
            self.assertFalse(report["shared_stop_persisted"])
        else:
            self.assertEqual(report["state"], "STOPPED_LIVE_APPROVAL_UNCONFIGURED")

    def test_dispatch_stop_in_propose(self):
        self.check_dispatch_request("propose", "stop")

    def test_dispatch_stop_in_simulate(self):
        self.check_dispatch_request("simulate", "stop")

    def test_dispatch_stop_in_respond(self):
        self.check_dispatch_request("respond", "stop")

    def test_dispatch_real_approve_in_propose_is_not_a_fixture(self):
        self.check_dispatch_request("propose", "approve")

    def test_dispatch_real_approve_in_simulate_is_not_a_fixture(self):
        self.check_dispatch_request("simulate", "approve")


def make_live_request_test(decision, expected):
    def test(self):
        result = ENTRY.storage.unavailable_live_response(decision)
        self.assertEqual(result["state"], expected)
        self.assertFalse(result["approval_accepted"])
        self.assertFalse(result["shared_stop_persisted"])
        self.assertFalse(result["human_authentication_tested"])
        self.assertEqual(result["mock_generations"], 0)
        self.assertEqual(result["real_AI_calls"], 0)
        self.assertFalse(result["automatic_apply"])
        self.assertEqual(result["remote_cancellation"], "NOT_ATTEMPTED_OR_CONFIRMED")
    return test


for _label, _decision in (("none", "none"), ("approve", "approve"), ("revise", "revise"),
                          ("reject", "reject"), ("stop", "stop"), ("boolean", True), ("invalid", "auto")):
    _expected = ("STOPPED_BY_HUMAN_LOCAL_ONLY" if _decision == "stop" else
                 "STOPPED_LIVE_APPROVAL_UNCONFIGURED" if type(_decision) is str and _decision != "auto" else
                 "STOPPED_DECISION_UNKNOWN")
    setattr(ConfirmationChecks, "test_live_request_" + _label, make_live_request_test(_decision, _expected))


def exercise_case(self, name, expected, expected_calls, mode="approve", context_change=None,
          plan_change=None, event_change=None, receipt_mode="corrected",
          now=1000, restart=False, replay=False, fault=None,
          concurrent=False, storage_failure=None, valid_initial=False, missing_source=False,
          restore_context_before_replay=False,
          expected_duplicate_state="DENIED_USED_OR_CLOSED"):
    demo, gate, controller = DEMO, GATE, CONTROLLER
    frozen = self.frozen.copy()
    packet, good, initial, valid = self.packet, self.good, self.initial, self.valid
    stores = self.directory
    ConfirmationExperiment = ENTRY.ConfirmationExperiment
    LocalSimulationStore = ENTRY.LocalSimulationStore
    FixtureAuthority = ENTRY.FixtureAuthority
    def rehash_current_inputs_and_code():
        return {**frozen, "adapter_sha256": ENTRY.digest(Path(ENTRY.__file__).read_bytes())}
    mutable = copy.deepcopy(frozen)
    clock = {"now": 1000}
    def current_context():
        live = rehash_current_inputs_and_code()
        live.update({key: value for key, value in mutable.items() if value != frozen[key]})
        return live
    authority = FixtureAuthority()
    store = LocalSimulationStore.prepare_new(stores / (name + ".sqlite"))
    draft = ConfirmationExperiment(gate, controller, store, authority,
                               current_context, lambda: clock["now"])
    plan, plan_hash, first = draft.propose("PLAN-" + name, None if missing_source else packet,
                                          valid if valid_initial else initial)
    count = []
    received = copy.deepcopy(plan)
    event = authority.event(plan["plan_id"], plan_hash, mode)
    if event_change == "actor":
        event = authority.event(plan["plan_id"], plan_hash, mode, "UNAUTHORIZED_FIXTURE_ACTOR")
    elif event_change == "copy":
        event = copy.copy(event)
    elif event_change == "hash":
        event = authority.event(plan["plan_id"], "0" * 64, mode)
    elif event_change == "id":
        event = authority.event("ANOTHER-PLAN", plan_hash, mode)
    if context_change:
        mutable[context_change] = "CHANGED"
    if plan_change:
        if plan_change == "display":
            received["displayed_proposal"] += " 変更された説明"
        else:
            received["request"][plan_change] = "CHANGED" if plan_change != "max_regenerations" else 2
    clock["now"] = now
    if storage_failure == "missing":
        draft.store = LocalSimulationStore(stores / (name + "-ABSENT.sqlite"))
    elif storage_failure == "unreadable":
        corrupt = stores / (name + "-CORRUPT.sqlite")
        corrupt.write_bytes(b"not a sqlite database")
        draft.store = LocalSimulationStore(corrupt)
    if restart:
        # New handler, new issuer, new controller, new SQLite connections.
        authority = FixtureAuthority()
        draft = ConfirmationExperiment(gate, controller, LocalSimulationStore(store.path), authority,
                                  current_context, lambda: clock["now"])
        event = authority.event(plan["plan_id"], plan_hash, mode)
    entered, release = threading.Event(), threading.Event()
    def generate(_):
        count.append("HANDWRITTEN_FIXTURE_ONLY")
        if concurrent:
            entered.set()
            if not release.wait(timeout=2):
                raise RuntimeError("Controlled barrier timed out")
        if receipt_mode == "stop":
            store.stop_during_request(plan["plan_id"])
        if receipt_mode == "context_during":
            mutable["observer_zip_sha256"] = "CHANGED_DURING_REQUEST"
        if receipt_mode == "unknown":
            return {"state": "RESULT_UNKNOWN", "payload": None}
        if receipt_mode == "failure":
            return {"state": "CONFIRMED_FAILED", "payload": None}
        if receipt_mode == "refused":
            return {"state": "REFUSED", "payload": None}
        candidate = copy.deepcopy(good)
        raw = valid
        if receipt_mode == "bad":
            raw = initial
        if receipt_mode == "cause":
            candidate["cause"] = "UNSUPPORTED_CAUSE_ASSERTION"
            raw = demo.encoded(candidate)
        if receipt_mode == "apply":
            candidate["automatic_apply"] = True
            raw = demo.encoded(candidate)
        if receipt_mode == "invalid_json":
            raw = b'{"schema_version":'
        return {"state": "COMPLETED", "payload": raw}
    extras = []
    if mode == "none" or valid_initial or missing_source:
        result = first
    elif concurrent:
        holder = []
        def worker():
            holder.append(draft.resume(plan["plan_id"], event, generate, received))
        thread = threading.Thread(target=worker)
        thread.start()
        if not entered.wait(timeout=2):
            release.set()
            thread.join(timeout=2)
            raise AssertionError("First mock request failed to start")
        other = ConfirmationExperiment(gate, controller, LocalSimulationStore(store.path), authority,
                                   current_context, lambda: clock["now"])
        extras.append(other.resume(plan["plan_id"], event, generate, received))
        release.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
        result = holder[0]
    else:
        result = draft.resume(plan["plan_id"], event, generate, received, fault)
    if replay:
        calls_before_replay = len(count)
        if restore_context_before_replay:
            mutable.clear()
            mutable.update(copy.deepcopy(frozen))
            clock["now"] = 1000
        new_authority = FixtureAuthority()
        next_handler = ConfirmationExperiment(gate, controller, LocalSimulationStore(store.path), new_authority,
                                         current_context, lambda: clock["now"])
        again = new_authority.event(plan["plan_id"], plan_hash)
        extras.append(next_handler.resume(plan["plan_id"], again, generate, received))
    invariants = {"no_API_calls": result["real_AI_calls"] == 0,
                  "no_final_adoption": result.get("human_final_adoption", False) is False,
                  "no_application": result["automatic_apply"] is False,
                  "at_most_one_mock_generation": len(count) <= 1,
                  "original_records_not_repaired": result["original_records_repaired"] is False,
                  "human_authentication_not_claimed": result["human_authentication_tested"] is False}
    if first["state"] == "WAITING_FOR_APPROVAL":
        invariants["proposal_was_displayed_before_any_generation"] = bool(first["displayed_proposal"]) and first["mock_generations"] == 0
    if extras:
        invariants["duplicate_dispatch_denied"] = all(x["state"] == expected_duplicate_state for x in extras)
        if result["state"] == "STOPPED_BY_HUMAN":
            invariants["stop_remains_in_shared_store"] = store.get(plan["plan_id"])[2] == "STOPPED_BY_HUMAN"
    if result["state"] == "HUMAN_REVIEW" and "trace" in result:
        v = result["trace"]["verifications"][-1]
        invariants["real_verifier_ran"] = v["status"] == "REVIEWABLE_DRAFT"
        invariants["causality_not_claimed"] = v["causality_verified"] is False
    if receipt_mode == "stop":
        trace = result["trace"]
        invariants["late_output_withheld"] = any(e["kind"] == "RESULT_WITHHELD_AFTER_STOP" for e in trace["events"])
        invariants["late_output_not_verified_or_adopted"] = len(trace["verifications"]) == 1
    if result["state"] in {"STOPPED_RESULT_UNKNOWN", "STOPPED_BUDGET"} and replay:
        invariants["no_auto_or_manual_replay_of_same_plan"] = len(count) == calls_before_replay
    passed = result["state"] == expected and len(count) == expected_calls and all(invariants.values())
    row = {"name": name, "expected_state": expected, "actual_state": result["state"],
           "reason": result["reason"], "expected_mock_calls": expected_calls,
           "actual_mock_calls": len(count), "passed": passed, "invariants": invariants,
           "additional_results": extras, "result": result}
    self.assertTrue(passed, json.dumps(row, ensure_ascii=False))
    return row


CASE_SPECS = [(('proposal_only', 'WAITING_FOR_APPROVAL', 0), {'mode': 'none'}), (('approve_corrected', 'HUMAN_REVIEW', 1), {}), (('no_response', 'WAITING_FOR_APPROVAL', 0), {'mode': 'none', 'now': 1010}), (('reject', 'REJECTED_BY_HUMAN', 0), {'mode': 'reject'}), (('revise_requires_new_plan', 'NEEDS_NEW_PROPOSAL', 0), {'mode': 'revise', 'replay': True}), (('stop_before_request', 'STOPPED_BY_HUMAN', 0), {'mode': 'stop', 'replay': True}), (('unauthorized_actor', 'STOPPED_AUTHORITY', 0), {'event_change': 'actor'}), (('copied_or_forged_event', 'STOPPED_AUTHORITY', 0), {'event_change': 'copy'}), (('boolean_approval_not_a_decision', 'STOPPED_DECISION_UNKNOWN', 0), {'mode': True}), (('approval_for_different_plan', 'STOPPED_BINDING', 0), {'event_change': 'id'}), (('approval_hash_mismatch', 'STOPPED_BINDING', 0), {'event_change': 'hash'}), (('changed_display', 'STOPPED_BINDING', 0), {'plan_change': 'display'}), (('changed_scope', 'STOPPED_BINDING', 0), {'plan_change': 'scope'}), (('changed_target', 'STOPPED_BINDING', 0), {'plan_change': 'target'}), (('changed_purpose', 'STOPPED_BINDING', 0), {'plan_change': 'purpose'}), (('expanded_budget', 'STOPPED_BINDING', 0), {'plan_change': 'max_regenerations'}), (('changed_source', 'STOPPED_CONTEXT_CHANGED', 0), {'context_change': 'observer_zip_sha256'}), (('changed_evidence', 'STOPPED_CONTEXT_CHANGED', 0), {'context_change': 'packet_sha256'}), (('changed_adapter', 'STOPPED_CONTEXT_CHANGED', 0), {'context_change': 'adapter_sha256'}), (('changed_authority', 'STOPPED_CONTEXT_CHANGED', 0), {'context_change': 'authority_epoch'}), (('expired', 'STOPPED_EXPIRED', 0), {'now': 1061}), (('expiry_boundary', 'STOPPED_EXPIRED', 0), {'now': 1060}), (('clock_before_issuance', 'STOPPED_TIME_UNKNOWN', 0), {'now': 999}), (('fresh_handler_resume', 'HUMAN_REVIEW', 1), {'restart': True}), (('replay_after_handler_restart', 'HUMAN_REVIEW', 1), {'replay': True}), (('duplicate_parallel_resumes', 'HUMAN_REVIEW', 1), {'concurrent': True}), (('unknown_result_no_retry', 'STOPPED_RESULT_UNKNOWN', 1), {'receipt_mode': 'unknown', 'replay': True}), (('confirmed_failure', 'STOPPED_FAILURE', 1), {'receipt_mode': 'failure', 'replay': True}), (('generator_refusal', 'STOPPED_REFUSAL', 1), {'receipt_mode': 'refused', 'replay': True}), (('still_inconsistent', 'STOPPED_BUDGET', 1), {'receipt_mode': 'bad', 'replay': True}), (('unsupported_cause', 'STOPPED_BUDGET', 1), {'receipt_mode': 'cause'}), (('invalid_json_resubmission', 'STOPPED_BUDGET', 1), {'receipt_mode': 'invalid_json'}), (('authority_expansion_in_output', 'STOPPED_BUDGET', 1), {'receipt_mode': 'apply'}), (('source_changes_in_flight', 'STOPPED_CONTEXT_CHANGED', 1), {'receipt_mode': 'context_during', 'replay': True}), (('human_stop_late_result', 'STOPPED_BY_HUMAN', 1), {'receipt_mode': 'stop', 'replay': True}), (('crash_after_claim_before_request', 'STOPPED_RESULT_UNKNOWN', 0), {'fault': 'crash_before_request', 'replay': True}), (('crash_after_request_before_record', 'STOPPED_RESULT_UNKNOWN', 1), {'fault': 'crash_after_request', 'replay': True}), (('missing_claim_store', 'STOPPED_STORAGE_UNRESOLVED', 0), {'storage_failure': 'missing'}), (('corrupt_claim_store', 'STOPPED_STORAGE_UNRESOLVED', 0), {'storage_failure': 'unreadable'}), (('initial_already_consistent', 'HUMAN_REVIEW', 0), {'valid_initial': True}), (('source_unavailable', 'STOPPED_UNKNOWN', 0), {'missing_source': True}), (('stop_with_changed_context', 'STOPPED_BY_HUMAN', 0), {'mode': 'stop', 'context_change': 'observer_zip_sha256', 'replay': True, 'restore_context_before_replay': True}), (('stop_with_expired_plan', 'STOPPED_BY_HUMAN', 0), {'mode': 'stop', 'now': 1061, 'replay': True, 'restore_context_before_replay': True}), (('stop_with_changed_display', 'STOPPED_BY_HUMAN', 0), {'mode': 'stop', 'plan_change': 'display', 'replay': True, 'expected_duplicate_state': 'STOPPED_BINDING'}), (('context_restored_does_not_reactivate', 'STOPPED_CONTEXT_CHANGED', 0), {'context_change': 'observer_zip_sha256', 'replay': True, 'restore_context_before_replay': True}), (('clock_rollback_does_not_reactivate', 'STOPPED_EXPIRED', 0), {'now': 1061, 'replay': True, 'restore_context_before_replay': True})]

def make_case_test(args, options):
    def test(self):
        exercise_case(self, *args, **options)
    return test

for _args, _options in CASE_SPECS:
    setattr(ConfirmationChecks, "test_scenario_" + _args[0], make_case_test(_args, _options))





# Stage 2: offline checks for the Stage 1 shared-record storage contract.
# The separate SQLite backend below is a disposable test fixture. It is not a
# GitHub backend, does not authenticate a human, and grants no execution rights.
# These tests do not enable live approval or change the workflow entry.


def _shared_store_module():
    ensure_modules()
    return ENTRY.storage


def _shared_fixture_authority():
    module = _shared_store_module()
    return {
        "schema": "NORMALIZED_PROTECTED_REF_POLICY_DRAFT_V1",
        "repository": module.SHARED_REPOSITORY,
        "authority_epoch": "OFFLINE_STAGE2_FIXTURE_ONLY",
        "prefixes": copy.deepcopy(module.SHARED_PREFIXES),
        "enforcement": "active",
        "creation_allowed": True,
        "updates_allowed": False,
        "deletions_allowed": False,
        "bypass_actors": [],
    }


def _shared_fixture_binding():
    module = _shared_store_module()
    return {
        "repository": module.SHARED_REPOSITORY,
        "workflow_path": module.SHARED_WORKFLOW,
        "run_id": 900000001,
        "run_attempt": 1,
        # Synthetic binding only; not authority from an actual Actions run.
        "head_sha": "42b688079fca3d04a27f1c0d6bbdfa9d90f4ac78",
        "head_branch": "main",
    }


class _SharedFixtureBackend:
    """Separate LOCAL create-once fixture. Server protection is not verified."""

    def __init__(self, path):
        self.path = Path(path)
        self.module = _shared_store_module()
        self.fault = None
        self.before_create = None
        self.read_fault = False
        self.create_count = 0
        self.policy_override = False
        self.policy_value = None

    @classmethod
    def prepare(cls, path):
        module = _shared_store_module()
        with Path(path).open("xb"):
            pass
        with sqlite3.connect(path) as con:
            con.execute("CREATE TABLE policy (raw BLOB)")
            con.execute("INSERT INTO policy VALUES (?)",
                        (module.encode(_shared_fixture_authority()),))
            con.execute("CREATE TABLE refs (ref TEXT PRIMARY KEY, raw BLOB)")
            con.execute(
                "CREATE TRIGGER no_update BEFORE UPDATE ON refs "
                "BEGIN SELECT RAISE(ABORT,'immutable fixture record'); END"
            )
            con.execute(
                "CREATE TRIGGER no_delete BEFORE DELETE ON refs "
                "BEGIN SELECT RAISE(ABORT,'immutable fixture record'); END"
            )
        return cls(path)

    def connection(self):
        # A missing backend must fail rather than silently create a fresh DB.
        return sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=3
        )

    def policy(self):
        if self.policy_override:
            return copy.deepcopy(self.policy_value)
        with self.connection() as con:
            return json.loads(con.execute("SELECT raw FROM policy").fetchone()[0])

    def read_exact(self, reference):
        if self.read_fault:
            raise OSError("UNRESOLVED_OFFLINE_FIXTURE_READ")
        with self.connection() as con:
            row = con.execute(
                "SELECT raw FROM refs WHERE ref=?", (reference,)
            ).fetchone()
        return row[0] if row else None

    def create_once(self, reference, raw):
        self.create_count += 1
        if self.fault == "forbidden":
            raise self.module.SharedRecordDenied()
        if self.before_create is not None:
            self.before_create()
        try:
            with self.connection() as con:
                con.execute("INSERT INTO refs VALUES (?,?)", (reference, raw))
        except sqlite3.IntegrityError:
            raise self.module.SharedRecordConflict() from None
        if self.fault == "lost_ack":
            raise self.module.SharedRecordResultUnknown()
        if self.fault == "bad_receipt":
            return {"created": True}
        return {
            "reference": reference,
            "sha256": self.module.digest(raw),
            "created": True,
        }

    def fault_replace(self, kind, raw):
        """Deliberate fixture corruption; not a recovery or production API."""
        with self.connection() as con:
            con.execute("DROP TRIGGER no_update")
            con.execute(
                "UPDATE refs SET raw=? WHERE ref LIKE ?",
                (raw, self.module.SHARED_PREFIXES[kind] + "%"),
            )
            con.execute(
                "CREATE TRIGGER no_update BEFORE UPDATE ON refs "
                "BEGIN SELECT RAISE(ABORT,'immutable fixture record'); END"
            )

    def fault_remove(self, kind):
        """Deliberate fixture corruption; protected-record loss is not safe."""
        with self.connection() as con:
            con.execute("DROP TRIGGER no_delete")
            con.execute(
                "DELETE FROM refs WHERE ref LIKE ?",
                (self.module.SHARED_PREFIXES[kind] + "%",),
            )
            con.execute(
                "CREATE TRIGGER no_delete BEFORE DELETE ON refs "
                "BEGIN SELECT RAISE(ABORT,'immutable fixture record'); END"
            )


_SHARED_PROCESS_PROBE = '''
import importlib.util
import json
from pathlib import Path
import socket
import sys
import time
from unittest.mock import patch

with patch.object(socket, "socket", side_effect=AssertionError("NO_FIXTURE_NETWORK")):
    test_path, db_path, owner, barrier_path = sys.argv[1:]
    spec = importlib.util.spec_from_file_location("shared_contract_child_tests", test_path)
    checks = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checks
    spec.loader.exec_module(checks)
    module = checks._shared_store_module()
    backend = checks._SharedFixtureBackend(db_path)
    if barrier_path:
        barrier = Path(barrier_path)
        def before_create():
            with (barrier / owner).open("xb"):
                pass
            deadline = time.monotonic() + 5
            while not all((barrier / name).is_file() for name in ("WORKER_0", "WORKER_1")):
                if time.monotonic() >= deadline:
                    raise RuntimeError("BOUNDED_OFFLINE_PROCESS_BARRIER_TIMEOUT")
                time.sleep(0.01)
        backend.before_create = before_create
    store = module.SharedRecordStoreDraft(
        backend, expected_authority=checks._shared_fixture_authority()
    )
    try:
        store.claim_once(
            checks._shared_fixture_binding(), b'{"proposal":"OFFLINE FIXTURE"}', owner
        )
        state = "CLAIMED"
    except module.GateStopped as exc:
        state = exc.state
    print(json.dumps({"state": state, "create_attempts": backend.create_count}))
'''


class SharedRecordContractChecks(unittest.TestCase):
    """Offline storage invariants only; live identity/expiry remain untested."""

    def setUp(self):
        network = patch.object(
            socket, "socket", side_effect=AssertionError("NO_FIXTURE_NETWORK")
        )
        network.start()
        self.addCleanup(network.stop)
        self.module = _shared_store_module()
        self.assertTrue(
            hasattr(self.module, "SharedRecordStoreDraft"),
            "Stage 1 approval_store.py is required; missing checks are not skipped.",
        )
        self.temp = tempfile.TemporaryDirectory(prefix="shared-contract-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "protected.sqlite"
        self.backend = _SharedFixtureBackend.prepare(self.path)
        self.store = self.new_store(self.backend)
        self.binding = _shared_fixture_binding()
        self.raw = b'{"proposal":"OFFLINE FIXTURE"}'
        self.store.register_plan_once(self.binding, self.raw)

    def new_store(self, backend):
        return self.module.SharedRecordStoreDraft(
            backend, expected_authority=_shared_fixture_authority()
        )

    def fresh(self):
        return self.new_store(_SharedFixtureBackend(self.path))

    def stopped(self, state, operation):
        with self.assertRaises(self.module.GateStopped) as caught:
            operation()
        self.assertEqual(caught.exception.state, state)

    def claim(self):
        self.store.claim_once(self.binding, self.raw, "WORKER_1")

    def test_default_has_no_live_backend(self):
        self.stopped(
            "STOPPED_SHARED_STORE_UNCONFIGURED",
            lambda: self.module.SharedRecordStoreDraft().status(self.binding, self.raw),
        )

    def test_new_plan_is_pending(self):
        self.assertEqual(self.fresh().status(self.binding, self.raw)["state"],
                         "WAITING_FOR_APPROVAL")
        # Check the LOCAL fixture assumptions; this proves nothing about GitHub.
        with self.backend.connection() as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE refs SET raw=?", (b"{}",))
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM refs")

    def test_duplicate_plan_does_not_write(self):
        before = self.backend.create_count
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.store.register_plan_once(self.binding, self.raw),
        )
        self.assertEqual(self.backend.create_count, before)

    def test_claim_replay_new_handler_denied(self):
        self.claim()
        response = subprocess.run(
            self.process_probe("WORKER_2"), capture_output=True,
            text=True, timeout=10, check=True,
        )
        self.assertEqual(
            json.loads(response.stdout),
            {"state": "DENIED_USED_OR_CLOSED", "create_attempts": 0},
        )

    def test_same_owner_cannot_claim_again(self):
        self.claim()
        self.stopped("DENIED_USED_OR_CLOSED", self.claim)

    def test_other_owner_cannot_continue(self):
        self.claim()
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.fresh().assert_owned_claim(self.binding, self.raw, "WORKER_2"),
        )

    def test_rejection_is_terminal(self):
        self.store.reject_once(self.binding, self.raw)
        self.stopped("DENIED_USED_OR_CLOSED", self.claim)
        self.assertEqual(self.fresh().status(self.binding, self.raw)["state"],
                         "REJECTED_BY_HUMAN")

    def test_stop_before_claim(self):
        self.store.stop_for_verified_request(self.binding, self.raw)
        self.stopped("STOPPED_BY_HUMAN", self.claim)

    def test_stop_after_claim(self):
        self.claim()
        self.store.stop_for_verified_request(self.binding, self.raw)
        self.stopped(
            "STOPPED_BY_HUMAN",
            lambda: self.fresh().assert_owned_claim(self.binding, self.raw, "WORKER_1"),
        )

    def test_stop_does_not_require_new_write_for_repeat(self):
        self.store.stop_for_verified_request(self.binding, self.raw)
        before = self.backend.create_count
        self.store.stop_for_verified_request(self.binding, self.raw)
        self.assertEqual(self.backend.create_count, before)

    def test_rewind_mutable_progress_cannot_reuse(self):
        progress = self.module.LocalSimulationStore.prepare_new(
            self.path.with_name("mutable.sqlite")
        )
        local_hash = progress.put({
            "plan_id": "LOCAL", "initial_state": "WAITING_FOR_APPROVAL",
            "protected_plan_sha256": self.module.digest(self.raw),
        })
        calls = []
        self.claim()
        progress.decide_once("LOCAL", local_hash, "approve")
        calls.append("OFFLINE FIXTURE")
        progress.finish("LOCAL", {"state": "HUMAN_REVIEW"})
        with progress.connection() as con:
            con.execute(
                "UPDATE plans SET status='WAITING_FOR_APPROVAL',claims=0,result=NULL"
            )
        self.assertEqual(progress.get("LOCAL")[2], "WAITING_FOR_APPROVAL")
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.fresh().claim_once(self.binding, self.raw, "WORKER_2"),
        )
        self.assertEqual(len(calls), 1)

    def test_rewind_mutable_progress_cannot_resume_stop(self):
        progress = self.module.LocalSimulationStore.prepare_new(
            self.path.with_name("mutable.sqlite")
        )
        progress.put({
            "plan_id": "LOCAL", "initial_state": "WAITING_FOR_APPROVAL",
            "protected_plan_sha256": self.module.digest(self.raw),
        })
        progress.stop_during_request("LOCAL")
        self.store.stop_for_verified_request(self.binding, self.raw)
        with progress.connection() as con:
            con.execute(
                "UPDATE plans SET status='WAITING_FOR_APPROVAL',claims=0,result=NULL"
            )
        self.assertEqual(progress.get("LOCAL")[2], "WAITING_FOR_APPROVAL")
        self.stopped(
            "STOPPED_BY_HUMAN",
            lambda: self.fresh().claim_once(self.binding, self.raw, "WORKER_2"),
        )

    def test_new_bytes_for_same_run_not_a_new_slot(self):
        self.stopped(
            "STOPPED_BINDING",
            lambda: self.store.status(self.binding, b'{"proposal":"CHANGED"}'),
        )
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.store.register_plan_once(self.binding, b'{"proposal":"CHANGED"}'),
        )

    def test_exact_byte_binding_preserves_whitespace_difference(self):
        self.stopped(
            "STOPPED_BINDING",
            lambda: self.store.status(self.binding, b'{ "proposal": "OFFLINE FIXTURE" }'),
        )

    def test_unknown_read_not_absence(self):
        self.backend.read_fault = True
        before = self.backend.create_count
        self.stopped("STOPPED_SHARED_STORAGE_UNRESOLVED", self.claim)
        self.assertEqual(self.backend.create_count, before)

    def test_missing_backend_no_recreation(self):
        self.backend.path = self.path.with_name("absent.sqlite")
        self.stopped("STOPPED_SHARED_PROTECTION", self.claim)
        self.assertFalse(self.backend.path.exists())

    def test_creation_lost_ack_no_retry_or_release(self):
        self.backend.fault = "lost_ack"
        before = self.backend.create_count
        self.stopped("STOPPED_RESULT_UNKNOWN", self.claim)
        self.assertEqual(self.backend.create_count - before, 1)
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.fresh().claim_once(self.binding, self.raw, "WORKER_2"),
        )

    def test_unverified_receipt_no_retry_or_release(self):
        self.backend.fault = "bad_receipt"
        before = self.backend.create_count
        self.stopped("STOPPED_RESULT_UNKNOWN", self.claim)
        self.assertEqual(self.backend.create_count - before, 1)
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.fresh().claim_once(self.binding, self.raw, "WORKER_2"),
        )

    def test_creation_forbidden_no_automatic_retry(self):
        self.backend.fault = "forbidden"
        before = self.backend.create_count
        self.stopped("STOPPED_SHARED_WRITE_FORBIDDEN", self.claim)
        self.assertEqual(self.backend.create_count - before, 1)

    def test_corrupt_plan_anchor_blocks(self):
        self.backend.fault_replace("plan", b"{")
        self.stopped("STOPPED_SHARED_RECORD_INVALID", self.claim)

    def test_unknown_record_key_blocks(self):
        ref = self.module.SHARED_PREFIXES["plan"] + self.store._binding(self.binding)
        value = json.loads(self.backend.read_exact(ref))
        value["extra"] = "UNKNOWN"
        self.backend.fault_replace("plan", self.module.encode(value))
        self.stopped("STOPPED_BINDING", self.claim)

    def test_plan_anchor_hash_mismatch_blocks(self):
        ref = self.module.SHARED_PREFIXES["plan"] + self.store._binding(self.binding)
        value = json.loads(self.backend.read_exact(ref))
        value["plan_sha256"] = "0" * 64
        self.backend.fault_replace("plan", self.module.encode(value))
        self.stopped("STOPPED_BINDING", self.claim)

    def test_orphaned_consumption_not_reinitialized(self):
        self.claim()
        self.backend.fault_remove("plan")
        self.stopped(
            "DENIED_USED_OR_CLOSED",
            lambda: self.store.register_plan_once(self.binding, self.raw),
        )

    def test_orphaned_stop_not_reinitialized(self):
        self.store.stop_for_verified_request(self.binding, self.raw)
        self.backend.fault_remove("plan")
        self.stopped(
            "STOPPED_BY_HUMAN",
            lambda: self.store.register_plan_once(self.binding, self.raw),
        )

    def test_missing_plan_not_automatically_recovered(self):
        self.backend.fault_remove("plan")
        self.stopped("STOPPED_PLAN_UNKNOWN", self.claim)

    def test_wrong_decision_type_blocks(self):
        self.claim()
        ref = self.module.SHARED_PREFIXES["consumed"] + self.store._binding(self.binding)
        value = json.loads(self.backend.read_exact(ref))
        value["decision"] = []
        self.backend.fault_replace("consumed", self.module.encode(value))
        self.stopped(
            "STOPPED_SHARED_RECORD_INVALID",
            lambda: self.store.status(self.binding, self.raw),
        )

    def test_stop_invalid_plan_rejected(self):
        self.stopped(
            "STOPPED_BINDING",
            lambda: self.store.stop_for_verified_request(
                self.binding, b'{"proposal":"CHANGED"}'
            ),
        )

    def test_thread_race_has_one_reservation(self):
        barrier = threading.Barrier(2)
        results = []

        def worker(owner):
            backend = _SharedFixtureBackend(self.path)
            backend.before_create = lambda: barrier.wait(timeout=5)
            store = self.new_store(backend)
            try:
                store.claim_once(self.binding, self.raw, owner)
                results.append("CLAIMED")
            except self.module.GateStopped as exc:
                results.append(exc.state)

        threads = [
            threading.Thread(target=worker, args=("WORKER_" + str(i),))
            for i in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=6)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(results), ["CLAIMED", "DENIED_USED_OR_CLOSED"])

    def process_probe(self, owner, barrier_path=""):
        # Uses fresh isolated Python processes, without a platform-specific fork.
        return [
            sys.executable, "-I", "-B", "-c", _SHARED_PROCESS_PROBE,
            str(Path(__file__).resolve()), str(self.path), owner, str(barrier_path),
        ]

    def test_process_race_has_one_reservation(self):
        barrier_path = self.path.with_name("process-barrier")
        barrier_path.mkdir()
        workers = [
            subprocess.Popen(
                self.process_probe("WORKER_" + str(i), barrier_path),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            for i in range(2)
        ]
        rows = []
        try:
            for worker in workers:
                out, err = worker.communicate(timeout=10)
                self.assertEqual(worker.returncode, 0, err)
                rows.append(json.loads(out))
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=2)
        self.assertEqual(
            sorted(row["state"] for row in rows),
            ["CLAIMED", "DENIED_USED_OR_CLOSED"],
        )
        self.assertEqual(sum(row["create_attempts"] for row in rows), 2)
        self.assertEqual(self.fresh().status(self.binding, self.raw)["state"], "CLAIMED")

    def test_legacy_live_response_still_disabled(self):
        for decision in ("approve", "reject", "none"):
            result = self.module.unavailable_live_response(decision)
            self.assertEqual(result["state"], "STOPPED_LIVE_APPROVAL_UNCONFIGURED")
            self.assertFalse(result["approval_accepted"])
            self.assertEqual(result["mock_generations"], 0)


_SHARED_INVALID_JSON = [
    ("duplicate", b'{"a":1,"a":2}'),
    ("BOM", b'\xef\xbb\xbf{}'),
    ("nonfinite", b'{"a":NaN}'),
    ("surrogate", b'{"a":"\\ud800"}'),
    ("trailing_comma", b'{"a":1,}'),
    ("nonobject", b"[]"),
]


def _make_shared_json_test(raw):
    def test(self):
        self.stopped(
            "STOPPED_SHARED_RECORD_INVALID",
            lambda: self.store.status(self.binding, raw),
        )
    return test


for _name, _raw in _SHARED_INVALID_JSON:
    setattr(SharedRecordContractChecks, "test_json_" + _name, _make_shared_json_test(_raw))


_SHARED_BAD_BINDINGS = [
    ("run_id_bool", "run_id", True),
    ("rerun", "run_attempt", 2),
    ("head_changed", "head_sha", "0" * 40),
    ("branch", "head_branch", "other"),
    ("workflow", "workflow_path", ".github/workflows/other.yml"),
]


def _make_shared_binding_test(key, value):
    def test(self):
        self.binding[key] = value
        self.stopped(
            "STOPPED_BINDING",
            lambda: self.store.status(self.binding, self.raw),
        )
    return test


for _name, _key, _value in _SHARED_BAD_BINDINGS:
    setattr(
        SharedRecordContractChecks, "test_binding_" + _name,
        _make_shared_binding_test(_key, _value),
    )


_SHARED_BAD_POLICIES = [
    ("unknown", None, None),
    ("updates", "updates_allowed", True),
    ("delete", "deletions_allowed", True),
    ("bypass", "bypass_actors", ["fixture"]),
    ("disabled", "enforcement", "disabled"),
    ("missing_field", "missing", None),
    ("nonfinite", "updates_allowed", float("nan")),
]


def _make_shared_policy_test(key, value):
    def test(self):
        policy = _shared_fixture_authority()
        if key is None:
            policy = None
        elif key == "missing":
            del policy["updates_allowed"]
        else:
            policy[key] = value
        self.backend.policy_override = True
        self.backend.policy_value = policy
        self.stopped("STOPPED_SHARED_PROTECTION", self.claim)
    return test


for _name, _key, _value in _SHARED_BAD_POLICIES:
    setattr(
        SharedRecordContractChecks, "test_protection_" + _name,
        _make_shared_policy_test(_key, _value),
    )

if __name__ == "__main__":
    unittest.main()
