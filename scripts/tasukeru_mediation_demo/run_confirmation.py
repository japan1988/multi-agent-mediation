#!/usr/bin/env python3
"""DRAFT: propose a bounded mediation experiment and verify mock responses.

Modes: propose (display only), simulate (fixture decisions and outputs), respond
(record a request and stop because live identity/shared storage are unavailable),
and self-test. No real AI API, repository repair, final adoption, or live approval
is performed. Existing baseline files are read and hash-checked, never written.
Python 3.12; standard library only. Outputs are separate report artifacts.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


storage = load_module("tasukeru_confirmation_store", Path(__file__).with_name("approval_store.py"))
encode, digest = storage.encode, storage.digest
GateStopped = storage.GateStopped
FixtureAuthority, FixtureDecision = storage.FixtureAuthority, storage.FixtureDecision
LocalSimulationStore = storage.LocalSimulationStore

BASELINE_HASHES = {
    ".github/workflows/tasukeru-analysis.yml": "13ff21a87b74e1f5461a25f5810d6fe90452f6d109296decfd16a9131e3f3f13",
    ".github/workflows/tasukeru-artifact-observer.yml": "fd9a8e01c21187db3c2b8eae216d8270f31fef075c273abaa1d3ac9b10bfbb5f",
    ".github/workflows/tasukeru-mediation-demo.yml": "0d139efc285e485a5a1d4e102775effb51b7e579b58f9409a5b7d41cd6ad119d",
    ".github/workflows/python-app.yml": "d8421906539931813a085831666e8f593d2da1aa319a52e74c904500d484cd33",
    "scripts/tasukeru_mediation_demo/run_demo.py": "d75f1cdabd6d477a9f3707d5233ed63dd016e2665c3e3b59202ab9c0b8212007",
    "scripts/tasukeru_mediation_demo/mediation_gate_draft.py": "779948bb83f7f2c2ec9c0732c7473e39a5ff1591ef697d36a1556a52d6848657",
    "scripts/tasukeru_mediation_demo/resubmission_controller_draft.py": "390fbfc7830c2145ab55328edb14486ebeec52b9c6e35908c542921ebec888b1",
}
EXTRA_CODE = (".github/workflows/tasukeru-mediation-confirmation.yml",
              "scripts/tasukeru_mediation_demo/run_confirmation.py",
              "scripts/tasukeru_mediation_demo/approval_store.py")
SCENARIOS = {
    "consistent": ("HUMAN_REVIEW", 0), "corrected": ("HUMAN_REVIEW", 1),
    "no_approval": ("WAITING_FOR_APPROVAL", 0), "still_inconsistent": ("STOPPED_BUDGET", 1),
    "expired_approval": ("STOPPED_EXPIRED", 0), "result_unknown": ("STOPPED_RESULT_UNKNOWN", 1),
    "human_stop": ("STOPPED_BY_HUMAN", 1), "unsupported_cause": ("STOPPED_BUDGET", 1),
    "replay_approval": ("HUMAN_REVIEW", 1), "double_request": ("HUMAN_REVIEW", 1),
}


def pinned_demo(repo_root):
    for name, expected in BASELINE_HASHES.items():
        path = repo_root / name
        if path.is_symlink() or digest(path.read_bytes()) != expected:
            raise GateStopped("STOPPED_BASELINE_CHANGED", "EXISTING_SOURCE_BASELINE_CHANGED")
    demo = load_module("tasukeru_pinned_demo", repo_root / "scripts/tasukeru_mediation_demo/run_demo.py")
    demo.baseline_check(repo_root)
    return demo


def candidate_bytes(demo, gate, packet):
    good = gate.make_fixture_proposal(copy.deepcopy(packet))
    bad = copy.deepcopy(good)
    if bad["facts"] and bad["facts"][0]["kind"] == "ARL_ROW_COUNT":
        bad["facts"][0]["actual_parsed_rows"] += 1
    else:
        bad["cause"] = "UNSUPPORTED_FIXTURE_CAUSE"
    return good, demo.encoded(bad), demo.encoded(good)


def current_context(repo_root, zip_path, manifest_path, packet, controller):
    return {"repository": "japan1988/multi-agent-mediation",
            "observer_zip_sha256": digest(zip_path.read_bytes()),
            "manifest_sha256": digest(manifest_path.read_bytes()),
            "packet_sha256": digest(encode(packet)), "authority_epoch": controller.AUTHORITY_EPOCH,
            **{name: digest((repo_root / name).read_bytes()) for name in (*BASELINE_HASHES, *EXTRA_CODE)}}


class ConfirmationExperiment:
    def __init__(self, gate, controller, store, authority, context_reader, clock):
        self.gate, self.controller = gate, controller
        self.store, self.authority = store, authority
        self.context_reader, self.clock = context_reader, clock
    def response(self, state, reason, **more):
        return {"state": state, "reason": reason, "real_AI_calls": 0,
                "human_authentication_tested": False, "automatic_apply": False,
                "human_final_adoption": False, "original_records_repaired": False, **more}
    def propose(self, plan_id, packet, initial, ttl=60):
        now = self.clock()
        if type(now) is not int or type(ttl) is not int or not 0 < ttl <= 300:
            raise GateStopped("STOPPED_TIME_UNKNOWN", "TIME_UNRESOLVED")
        context = copy.deepcopy(self.context_reader())
        ctrl = self.controller.ResubmissionController(plan_id, packet,
                                                      lambda: context, self.clock)
        first = ctrl.start(initial)
        request = ctrl.approval_request()
        text = None
        if request is not None:
            text = ("この実験では、Observerの記録から作った模擬案に意図的な不一致を入れています。対象はこの模擬案だけです。"
                    "テスト用の回答を1回だけ再提出し、同じ根拠で機械検証して結果を提示します。"
                    "元の解析ログは変更せず、自動適用・最終採用も行いません。"
                    "この範囲で調停してよいですか？")
        plan = {"schema": "DRAFT_CONFIRMATION_EXPERIMENT_V1", "plan_id": plan_id,
                "initial_state": first["state"], "initial_reason": first["reason"],
                "issued_at": now, "expires_at": now + ttl,
                "displayed_proposal": text, "choices": ["approve", "revise", "reject", "stop"],
                "request": request, "context": context, "packet": copy.deepcopy(packet),
                "initial_proposal_utf8": initial.decode("utf-8"),
                "human_authentication_tested": False, "automatic_apply": False,
                "final_adoption": False, "approval": "NOT_DETERMINED"}
        plan_hash = self.store.put(plan)
        return plan, plan_hash, self.response(first["state"], first["reason"],
                         displayed_proposal=text, mock_generations=0)
    def resume(self, plan_id, event, generator, received_plan=None, fault=None):
        ctrl = None
        try:
            plan, plan_hash, state, claims, _ = self.store.get(plan_id)
            if not self.authority.recognizes(event) or event.actor != "FIXTURE_REVIEWER":
                raise GateStopped("STOPPED_AUTHORITY", "NOT_FROM_AUTHORIZED_FIXTURE_CHANNEL")
            if type(event.decision) is not str or event.decision not in plan["choices"]:
                raise GateStopped("STOPPED_DECISION_UNKNOWN", "UNSUPPORTED_USER_DECISION")
            if event.plan_id != plan_id or event.plan_sha256 != plan_hash:
                raise GateStopped("STOPPED_BINDING", "APPROVAL_BINDING_MISMATCH")
            # A verified, bound STOP is handled before expiry/context checks.
            # It also remains effective for an already claimed request.
            if event.decision == "stop":
                self.store.stop_during_request(plan_id)
                return self.response("STOPPED_BY_HUMAN", "EXPLICIT_FIXTURE_STOP",
                                     remote_cancellation="NOT_ATTEMPTED_OR_CONFIRMED")
            if received_plan is not None and encode(received_plan) != encode(plan):
                raise GateStopped("STOPPED_BINDING", "DISPLAYED_PROPOSAL_CHANGED")
            if state != "WAITING_FOR_APPROVAL" or claims:
                raise GateStopped("DENIED_USED_OR_CLOSED", "PLAN_ALREADY_CLAIMED_OR_CLOSED")
            if event.decision in {"reject", "revise"}:
                decided = self.store.decide_once(plan_id, plan_hash, event.decision)
                return self.response(decided, "EXPLICIT_FIXTURE_" + event.decision.upper())
            now = self.clock()
            if type(now) is not int or now < plan["issued_at"]:
                self.store.close_waiting(plan_id, "STOPPED_TIME_UNKNOWN")
                raise GateStopped("STOPPED_TIME_UNKNOWN", "TIME_UNRESOLVED")
            if now >= plan["expires_at"]:
                self.store.close_waiting(plan_id, "STOPPED_EXPIRED")
                raise GateStopped("STOPPED_EXPIRED", "APPROVAL_EXPIRED")
            if encode(self.context_reader()) != encode(plan["context"]):
                self.store.close_waiting(plan_id, "STOPPED_CONTEXT_CHANGED")
                raise GateStopped("STOPPED_CONTEXT_CHANGED", "APPROVED_INPUT_OR_CODE_CHANGED")
            registry = self.controller.MockApprovalRegistry()
            ctrl = self.controller.ResubmissionController(plan_id, plan["packet"],
                                                          self.context_reader, self.clock)
            ctrl.start(plan["initial_proposal_utf8"].encode("utf-8"))
            if encode(ctrl.approval_request()) != encode(plan["request"]):
                raise GateStopped("STOPPED_BINDING", "RECONSTRUCTED_REQUEST_CHANGED")
            self.store.decide_once(plan_id, plan_hash, "approve")
            if fault == "crash_before_request":
                result = self.response("STOPPED_RESULT_UNKNOWN", "SIMULATED_CRASH_AFTER_CLAIM")
                self.store.finish(plan_id, result)
                return result
            grant = registry.issue(ctrl.approval_request(), now=now,
                                   ttl=plan["expires_at"] - now)
            def wrapped(data):
                receipt = generator(data)
                if self.store.get(plan_id)[2] == "STOPPED_BY_HUMAN":
                    ctrl.stop()
                return receipt
            view = ctrl.regenerate(grant, registry, wrapped)
            if fault == "crash_after_request":
                result = self.response("STOPPED_RESULT_UNKNOWN", "SIMULATED_RESULT_RECORD_LOSS",
                                       controller_state_before_loss=view["state"])
            else:
                result = self.response(view["state"], view["reason"], trace=ctrl.snapshot())
            self.store.finish(plan_id, result)
            return result
        except GateStopped as exc:
            return self.response(exc.state, exc.reason)
        except (sqlite3.Error, OSError):
            if ctrl and ctrl.regenerations_used:
                return self.response("STOPPED_RESULT_UNKNOWN", "RESULT_STORAGE_UNRESOLVED")
            return self.response("STOPPED_STORAGE_UNRESOLVED", "NO_AUTOMATIC_STORE_RECOVERY")
        except Exception:
            return self.response("STOPPED_RESULT_UNKNOWN" if ctrl else "STOPPED_INPUT_UNKNOWN",
                                 "SIMULATION_OPERATION_UNRESOLVED")


def experiment_scenarios(demo, gate, controller, packet, context_reader, output):
    good, initial, valid = candidate_bytes(demo, gate, packet)
    rows = []
    with tempfile.TemporaryDirectory(prefix="confirmation-local-model-") as work:
        for name, (expected, expected_calls) in SCENARIOS.items():
            authority = FixtureAuthority()
            clock = {"now": 1000}
            store = LocalSimulationStore.prepare_new(Path(work) / (name + ".sqlite"))
            experiment = ConfirmationExperiment(gate, controller, store, authority,
                                                context_reader, lambda: clock["now"])
            plan, plan_hash, first = experiment.propose("FIXTURE-" + name, packet,
                                                      valid if name == "consistent" else initial)
            calls, additional = [], []

            def generate(_):
                calls.append("HANDWRITTEN_FIXTURE_ONLY")
                if name == "human_stop":
                    store.stop_during_request(plan["plan_id"])
                if name == "result_unknown":
                    return {"state": "RESULT_UNKNOWN", "payload": None}
                raw = valid
                if name == "still_inconsistent":
                    raw = initial
                if name == "unsupported_cause":
                    candidate = copy.deepcopy(good)
                    candidate["cause"] = "UNSUPPORTED_CAUSE_ASSERTION"
                    raw = demo.encoded(candidate)
                return {"state": "COMPLETED", "payload": raw}

            event = authority.event(plan["plan_id"], plan_hash)
            if name == "expired_approval":
                clock["now"] = plan["expires_at"]
            result = first if name in {"consistent", "no_approval"} else experiment.resume(
                plan["plan_id"], event, generate, copy.deepcopy(plan))
            if name in {"replay_approval", "double_request"}:
                # New handler/connections; simultaneous requests are additionally
                # covered by the process tests. This case tests sequential reuse.
                fresh = FixtureAuthority()
                next_handler = ConfirmationExperiment(gate, controller, LocalSimulationStore(store.path),
                                                       fresh, context_reader, lambda: clock["now"])
                additional.append(next_handler.resume(plan["plan_id"],
                                  fresh.event(plan["plan_id"], plan_hash), generate, copy.deepcopy(plan)))
            invariants = {"one_mock_generation_max": len(calls) <= 1,
                          "no_API_or_apply": result["real_AI_calls"] == 0 and result["automatic_apply"] is False,
                          "no_final_adoption": result["human_final_adoption"] is False,
                          "original_records_retained": result["original_records_repaired"] is False,
                          "no_live_authentication_claim": result["human_authentication_tested"] is False,
                          "duplicate_denied": all(x["state"] == "DENIED_USED_OR_CLOSED" for x in additional)}
            row = {"scenario": name, "state": result["state"], "mock_generations": len(calls),
                   "expected_state": expected, "expected_mock_generations": expected_calls,
                   "passed": result["state"] == expected and len(calls) == expected_calls and all(invariants.values()),
                   "invariants": invariants, "result": result, "additional_results": additional,
                   "initial_candidate_origin": "HANDWRITTEN_FIXTURE", "decision_origin": "FIXTURE"}
            rows.append(row)
            save(output / "cases" / (name + ".json"), encode(row))
    return rows


def run_self_tests(repo_root, demo):
    gate, controller = demo.modules()
    baseline = demo.self_tests(gate, controller)
    test_path = repo_root / "tests/test_tasukeru_mediation_confirmation.py"
    tests = load_module("tasukeru_confirmation_checks", test_path)
    tests.configure(sys.modules[__name__], demo, gate, controller)
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)

    class RecordedResults(unittest.TestResult):
        def __init__(self):
            super().__init__()
            self.rows = []

        def addSuccess(self, test):
            super().addSuccess(test)
            self.rows.append({"name": test.id(), "passed": True})

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.rows.append({"name": test.id(), "passed": False, "kind": "FAILURE"})

        def addError(self, test, err):
            super().addError(test, err)
            self.rows.append({"name": test.id(), "passed": False, "kind": "ERROR"})

    result = RecordedResults()
    suite.run(result)
    return {"status": "PASSED" if result.wasSuccessful() and baseline["status"] == "PASSED" else "FAILED",
            "baseline_self_tests": baseline, "tests_total": result.testsRun,
            "tests_passed": sum(x["passed"] for x in result.rows), "tests": result.rows,
            "real_AI_calls": 0, "live_authentication_tested": False,
            "github_cross_run_storage_tested": False, "fixture_only": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("propose", "simulate", "respond", "self-test"), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observer-zip", type=Path)
    parser.add_argument("--retrieval-manifest", type=Path)
    parser.add_argument("--decision", choices=("none", "approve", "revise", "reject", "stop"), default="none")
    args = parser.parse_args(argv)
    root, output = args.repo_root.resolve(), args.output.resolve()
    # No overwrite/recovery: an existing output is evidence, not a fresh run.
    output.mkdir(parents=True, exist_ok=False)
    summary = None
    try:
        # A real stop/request must never be ignored by another selected mode.
        # Handle it before source reads, baseline checks, or fixture processing.
        if args.mode == "respond" or args.decision != "none":
            report = storage.unavailable_live_response(args.decision)
            report.update({"requested_decision": args.decision, "response_origin": "UNAUTHENTICATED_REQUEST",
                           "status": "LIVE_RESPONSE_BLOCKED", "mode": args.mode})
            summary = ("# 調停案への回答\n\n状態: " + report["state"] +
                       "\n\n実承認の認証と実行間の共有保存は未実装です。承認入力を実行許可として受理していません。"
                       "\n\n新しい調停処理は開始していません。停止入力は、この実行内の停止としてのみ記録します。"
                       "別実行の停止保存や外部処理の取消完了を意味しません。\n")
        elif args.mode == "self-test":
            demo = pinned_demo(root)
            report = run_self_tests(root, demo)
            summary = "# Confirmation experiment self-tests\n\nStatus: " + report["status"] + "\n"
        else:
            demo = pinned_demo(root)
            if args.observer_zip is None or args.retrieval_manifest is None:
                raise GateStopped("STOPPED_INPUT_UNKNOWN", "OBSERVER_INPUT_REQUIRED")
            manifest_raw = demo.read_bounded(args.retrieval_manifest, demo.MAX_JSON)
            observer_raw = demo.read_bounded(args.observer_zip, demo.MAX_ZIP)
            demo.validate_download(demo.strict_document(manifest_raw), observer_raw)
            gate, controller = demo.modules()
            packet, differences = demo.validate_reports(demo.read_archive(observer_raw), gate)
            context_reader = lambda: current_context(root, args.observer_zip, args.retrieval_manifest, packet, controller)
            if args.mode == "propose":
                _, initial, _ = candidate_bytes(demo, gate, packet)
                with tempfile.TemporaryDirectory(prefix="proposal-local-model-") as work:
                    store = LocalSimulationStore.prepare_new(Path(work) / "proposal.sqlite")
                    experiment = ConfirmationExperiment(gate, controller, store, FixtureAuthority(), context_reader,
                                                        lambda: int(time.time()))
                    plan, plan_hash, first = experiment.propose("DISPLAY-ONLY-PROPOSAL", packet, initial, ttl=300)
                    save(output / "proposal.json", encode({"plan": plan, "plan_sha256": plan_hash}))
                report = {"status": "PROPOSAL_DISPLAYED_ONLY", "result": first, "plan_sha256": plan_hash,
                          "initial_candidate_origin": "HANDWRITTEN_FIXTURE", "mock_generations": 0}
                summary = ("# Tasukeru 調停案の提示\n\n" + plan["displayed_proposal"] +
                           "\n\n選択肢: 承認／案を修正／却下／停止\n\n"
                           "これは実際のObserver記録を使った模擬提案です。根拠と異なる模擬案を意図的に作成しています。"
                           "提案の表示だけを行い、再生成は0回です。"
                           "\n\n実際の承認は未接続です。`simulate` は模擬回答を試し、`respond` は要求を記録して停止します。\n")
            else:
                rows = experiment_scenarios(demo, gate, controller, packet, context_reader, output)
                report = {"status": "EXPECTED_EXPERIMENT_BEHAVIOR" if all(x["passed"] for x in rows) else "FAILED",
                          "cases_total": len(rows), "cases_passed": sum(x["passed"] for x in rows), "cases": rows}
                summary = ("# Tasukeru 調停提案の模擬実験\n\nAI出力と承認はテスト用データです。\n\n"
                           "| Scenario | State | Mock generations | Expected behavior |\n|---|---|---:|---|\n" +
                           "\n".join("| " + r["scenario"] + " | " + r["state"] + " | " + str(r["mock_generations"]) +
                                     " | " + ("PASS" if r["passed"] else "FAIL") + " |" for r in rows) + "\n")
            report.update({"observer_run_id": demo.strict_document(manifest_raw)["observer_run_id"],
                           "source_analysis_run_id": packet["source"]["run_id"],
                           "observed_differences_retained": differences, "cause": "UNKNOWN",
                           "actor": "UNKNOWN", "snapshot_relationship": "UNKNOWN"})
            summary += "\n元記録の差異を " + str(differences) + " 件保持。原因・主体・同一時点の関係は UNKNOWN です。\n"
        report.update({"feature_status": "DRAFT_REPORT_ONLY_EXPERIMENT", "real_AI_calls": 0,
                       "automatic_apply": False, "human_final_adoption": False,
                       "original_records_repaired": False, "live_authentication_tested": False,
                       "github_cross_run_storage_tested": False, "final_adoption": "NOT_DETERMINED"})
        summary += "\n実AI API・自動修復・最終採用は行いません。成功は実承認やシステム全体の安全性を証明しません。\n"
        save(output / "report.json", encode(report))
        save(output / "summary.md", summary.encode("utf-8"))
        print("Confirmation status: " + report["status"])
        return 1 if report["status"] == "FAILED" else 0
    except Exception as exc:
        state = exc.state if isinstance(exc, GateStopped) else "STOPPED_INPUT_UNKNOWN"
        reason = exc.reason if isinstance(exc, GateStopped) else "INPUT_OR_BASELINE_UNRESOLVED"
        report = {"status": "STOPPED", "state": state, "reason": reason, "real_AI_calls": 0,
                  "automatic_apply": False, "human_final_adoption": False, "final_adoption": "NOT_DETERMINED"}
        # Preserve any preceding evidence; never replace an existing report.
        for name, data in (("failure.json", encode(report)),
                           ("failure-summary.md", ("# Confirmation experiment stopped\n\n" + state + "\n" + reason + "\n").encode())):
            with (output / name).open("xb") as handle:
                handle.write(data)
        print("Confirmation status: STOPPED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
