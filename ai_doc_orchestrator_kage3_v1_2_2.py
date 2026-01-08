diff --git a/ai_doc_orchestrator_kage3_v1_2_3.py b/ai_doc_orchestrator_kage3_v1_2_3.py
index 1111111..2222222 100644
--- a/ai_doc_orchestrator_kage3_v1_2_3.py
+++ b/ai_doc_orchestrator_kage3_v1_2_3.py
@@
-# ai_doc_orchestrator_kage3_v1_2_3.py  (v1.2.3)  ※ファイル名は維持でもOK
+# ai_doc_orchestrator_kage3_v1_2_4.py  (v1.2.4)  ※ファイル名は維持でもOK
 # -*- coding: utf-8 -*-
 """
 (ai_doc_orchestrator_kage3_v1_2_2.py に対する設計寄り改修)
 
 Changes (design-oriented):
 - AuditLog gains start_run(truncate=...) to control log lifecycle per run.
 - AuditLog owns ts_state (monotonic timestamp) instead of module-global _LAST_TS.
 - Defensive JSON serialization: default=str so audit never crashes on non-JSON types.
 - Deep redaction also redacts dict keys (prevents email-like keys from persisting).
 - emit() auto-fills "ts" if missing.
+
+v1.2.4 (IEP-aligned additions):
+- Pipeline aligned: Meaning -> Consistency -> RFL -> Ethics -> ACC -> DISPATCH
+- Decision vocabulary aligned: RUN / PAUSE_FOR_HITL / STOPPED
+- RFL gate added (never seals; always escalates to HITL):
+    REL_BOUNDARY_UNSTABLE / REL_REF_MISSING / REL_SYMMETRY_BREAK
+- HITL decision events recorded:
+    HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
+- ARL minimal keys emitted on every audit row:
+    run_id, layer, decision, sealed, overrideable, final_decider, reason_code
 """
 
 from __future__ import annotations
 
 import json
 import re
 from dataclasses import dataclass, field
 from datetime import datetime, timezone, timedelta
 from pathlib import Path
 from typing import Any, Dict, List, Literal, Optional, Tuple
 
-__version__ = "1.2.3"
+__version__ = "1.2.4"
 
 JST = timezone(timedelta(hours=9))
 
 EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
 
-Decision = Literal["RUN", "HITL", "STOP"]
-OverallDecision = Literal["RUN", "HITL"]
-Layer = Literal["meaning", "consistency", "ethics", "orchestrator", "agent"]
+Decision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
+OverallDecision = Literal["RUN", "PAUSE_FOR_HITL", "STOPPED"]
+Layer = Literal["meaning", "consistency", "rfl", "ethics", "acc", "orchestrator", "agent", "hitl_finalize", "dispatch"]
 KIND = Literal["excel", "word", "ppt"]
+HITLAction = Literal["CONTINUE", "STOP"]
+
+FINAL_DECIDER_SYSTEM = "SYSTEM"
+FINAL_DECIDER_USER = "USER"
 
 
 # -----------------------------
 # Redaction (PII must not persist)
 # -----------------------------
 def redact_sensitive(text: str) -> str:
@@
 class AuditLog:
     audit_path: Path
     _last_ts: Optional[datetime] = field(default=None, init=False, repr=False)
@@
     def emit(self, row: Dict[str, Any]) -> None:
         """
         Append a JSONL row.
         Hard guarantee: no email-like strings are persisted.
         Also: never crash on non-JSON-serializable types (default=str).
         """
         self.audit_path.parent.mkdir(parents=True, exist_ok=True)
 
         # auto-fill ts if missing (callers may still pass explicit ts)
         if "ts" not in row:
             row = dict(row)
             row["ts"] = self.ts()
 
+        # Enforce ARL minimal keys on every row (fail-closed: never omit)
+        # NOTE: Defaults are conservative: SYSTEM emits are overrideable unless explicitly sealed.
+        row = dict(row)
+        row.setdefault("sealed", False)
+        row.setdefault("overrideable", True)
+        row.setdefault("final_decider", FINAL_DECIDER_SYSTEM)
+        row.setdefault("reason_code", "")
+        row.setdefault("layer", "orchestrator")
+        row.setdefault("decision", "RUN")
+
         # Safe copy (no mutation), tolerate non-JSON types
         safe_row = json.loads(json.dumps(row, ensure_ascii=False, default=str))
         safe_blob = json.dumps(safe_row, ensure_ascii=False)
@@
 class TaskResult:
     task_id: str
     kind: KIND
     decision: Decision
     blocked_layer: Optional[Layer]
     reason_code: str = ""
     artifact_path: Optional[str] = None
@@
 class SimulationResult:
     run_id: str
     decision: OverallDecision
     tasks: List[TaskResult]
     artifacts_written_task_ids: List[str]
@@
 def _meaning_gate(prompt: str, kind: KIND) -> Tuple[Decision, Optional[Layer], str]:
     p = (prompt or "")
     pl = p.lower()
     any_kind = _prompt_mentions_any_kind(p)
 
     if not any_kind:
         return "RUN", None, "MEANING_GENERIC_ALLOW_ALL"
@@
     if any(t.lower() in pl for t in tokens):
         return "RUN", None, "MEANING_KIND_MATCH"
 
-    return "HITL", "meaning", "MEANING_KIND_MISSING"
+    return "PAUSE_FOR_HITL", "meaning", "MEANING_KIND_MISSING"
@@
 def _validate_contract(kind: KIND, draft: Dict[str, Any]) -> Tuple[bool, str]:
@@
     return False, "CONTRACT_UNKNOWN_KIND"
 
+def _rfl_gate(prompt: str, kind: KIND, draft: Dict[str, Any]) -> Tuple[Decision, Optional[Layer], str]:
+    """
+    RFL (Relativity Filter) gate:
+    - MUST NOT seal
+    - On hit: PAUSE_FOR_HITL with REL_* reason code
+    Heuristics here are intentionally simple and conservative.
+    """
+    p = (prompt or "").strip()
+    pl = p.lower()
+
+    # REL_REF_MISSING: comparative / optimization words without concrete reference
+    rel_words = [
+        "better", "best", "improve", "optimize", "faster", "cheaper", "more", "less",
+        "高い", "低い", "早く", "速く", "安く", "良く", "最適", "改善", "増や", "減ら",
+    ]
+    has_rel = any(w in pl for w in rel_words)
+    has_number = bool(re.search(r"\d", p))
+    has_baseline_hint = any(x in pl for x in ["baseline", "reference", "kpi", "target", "目標", "基準", "指標"])
+    if has_rel and not (has_number or has_baseline_hint):
+        return "PAUSE_FOR_HITL", "rfl", "REL_REF_MISSING"
+
+    # REL_BOUNDARY_UNSTABLE: hard tradeoffs requested simultaneously (quality vs speed vs cost)
+    tradeoff_fast = any(x in pl for x in ["fast", "faster", "asap", "速", "早"])
+    tradeoff_quality = any(x in pl for x in ["accurate", "perfect", "high quality", "精度", "完璧", "高品質"])
+    tradeoff_cost = any(x in pl for x in ["cheap", "low cost", "無料", "安"])
+    if (tradeoff_fast and tradeoff_quality) or (tradeoff_quality and tradeoff_cost) or (tradeoff_fast and tradeoff_cost):
+        return "PAUSE_FOR_HITL", "rfl", "REL_BOUNDARY_UNSTABLE"
+
+    # REL_SYMMETRY_BREAK: kind-specific request while expecting all tasks to proceed
+    # Example: prompt mentions only one kind explicitly and still expects others to run.
+    # If user mentions exactly one kind token set, we treat it as symmetry break (needs HITL).
+    kinds_mentioned = []
+    for k, toks in _KIND_TOKENS.items():
+        if any(t.lower() in pl for t in toks):
+            kinds_mentioned.append(k)
+    if len(set(kinds_mentioned)) == 1 and kind not in set(kinds_mentioned):
+        return "PAUSE_FOR_HITL", "rfl", "REL_SYMMETRY_BREAK"
+
+    return "RUN", None, "RFL_OK"
+
 
 # -----------------------------
 # Ethics detection (memory-only raw_text)
 # -----------------------------
 def _ethics_detect_pii(raw_text: str) -> Tuple[bool, str]:
@@
 def _agent_generate(prompt: str, kind: KIND, faults: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
@@
     safe_text = redact_sensitive(raw_text)
     return draft, raw_text, safe_text
 
 
 # -----------------------------
-# Artifact writer (safe_text only)
+# ACC gate (pre-dispatch) + Artifact writer (safe_text only)
 # -----------------------------
 def _artifact_ext(kind: KIND) -> str:
@@
     return "txt"
 
+def _acc_gate(
+    *,
+    kind: KIND,
+    safe_text: str,
+    contract_ok: bool,
+    artifact_dir: Path,
+    task_id: str,
+) -> Tuple[Decision, Optional[Layer], str]:
+    """
+    ACC (pre-dispatch correctness/safety gate).
+    - Sealing is allowed here (STOPPED) if unsafe to write artifacts.
+    """
+    # If contract is invalid, never dispatch artifacts (even if HITL continued).
+    if not contract_ok:
+        return "STOPPED", "acc", "ACC_CONTRACT_INVALID"
+
+    # Defensive check: safe_text must not contain email-like tokens.
+    if EMAIL_RE.search(safe_text or ""):
+        return "STOPPED", "acc", "ACC_PII_REMAINED"
+
+    # Defensive check: ensure the artifact path is under artifact_dir (path traversal guard).
+    ext = _artifact_ext(kind)
+    candidate = (artifact_dir / f"{task_id}.{ext}.txt").resolve()
+    if artifact_dir.resolve() not in candidate.parents and candidate != artifact_dir.resolve():
+        return "STOPPED", "acc", "ACC_PATH_TRAVERSAL"
+
+    return "RUN", None, "ACC_OK"
+
 
 def _write_artifact(artifact_dir: Path, task_id: str, kind: KIND, safe_text: str) -> Path:
     artifact_dir.mkdir(parents=True, exist_ok=True)
     path = artifact_dir / f"{task_id}.{_artifact_ext(kind)}.txt"
     path.write_text(redact_sensitive(safe_text), encoding="utf-8")
     return path
@@
 def run_simulation(
     *,
     prompt: str,
     run_id: str,
     audit_path: str,
     artifact_dir: str,
     faults: Optional[Dict[str, Dict[str, Any]]] = None,
+    hitl_actions: Optional[Dict[str, HITLAction]] = None,
+    hitl_default: HITLAction = "STOP",
     truncate_audit_on_start: bool = False,
 ) -> SimulationResult:
@@
     """
     truncate_audit_on_start:
       - True: start_run(truncate=True) で run ごとに監査ログを初期化
       - False: append 継続（従来互換）
     """
     faults = faults or {}
+    hitl_actions = hitl_actions or {}
     audit = AuditLog(Path(audit_path))
     audit.start_run(truncate=truncate_audit_on_start)
     out_dir = Path(artifact_dir)
 
     task_results: List[TaskResult] = []
     artifacts_written: List[str] = []
 
+    def _hitl_resolve(task_id: str, *, gate_layer: Layer, reason_code: str) -> HITLAction:
+        """
+        HITL flow (only meaningful when sealed=False):
+          HITL_REQUESTED (SYSTEM) -> HITL_DECIDED (USER) -> branch
+        """
+        # Request (SYSTEM)
+        audit.emit({
+            "run_id": run_id,
+            "task_id": task_id,
+            "event": "HITL_REQUESTED",
+            "layer": "orchestrator",
+            "decision": "PAUSE_FOR_HITL",
+            "sealed": False,
+            "overrideable": True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
+            "reason_code": reason_code,
+            "blocked_layer": gate_layer,
+        })
+
+        action: HITLAction = hitl_actions.get(task_id, hitl_default)
+
+        # Decision (USER)
+        audit.emit({
+            "run_id": run_id,
+            "task_id": task_id,
+            "event": "HITL_DECIDED",
+            "layer": "hitl_finalize",
+            "decision": "RUN" if action == "CONTINUE" else "STOPPED",
+            "sealed": False,  # HITL is not a sealing action by itself
+            "overrideable": False,
+            "final_decider": FINAL_DECIDER_USER,
+            "reason_code": "HITL_CONTINUE" if action == "CONTINUE" else "HITL_STOP",
+            "blocked_layer": gate_layer,
+        })
+        return action
+
     for task_id, kind in _TASKS:
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
             "event": "TASK_ASSIGNED",
             "layer": "orchestrator",
             "kind": kind,
+            "decision": "RUN",
+            "sealed": False,
+            "overrideable": True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
+            "reason_code": "TASK_ASSIGNED",
         })
 
         m_dec, m_layer, m_code = _meaning_gate(prompt, kind)
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
             "event": "GATE_MEANING",
             "layer": "meaning",
             "decision": m_dec,
             "reason_code": m_code,
+            "sealed": False,
+            "overrideable": (m_dec == "PAUSE_FOR_HITL"),
+            "final_decider": FINAL_DECIDER_SYSTEM,
         })
 
-        if m_dec == "HITL":
+        if m_dec == "PAUSE_FOR_HITL":
+            action = _hitl_resolve(task_id, gate_layer="meaning", reason_code=m_code)
+            if action == "STOP":
+                audit.emit({
+                    "run_id": run_id,
+                    "task_id": task_id,
+                    "event": "ARTIFACT_SKIPPED",
+                    "layer": "orchestrator",
+                    "decision": "PAUSE_FOR_HITL",
+                    "sealed": False,
+                    "overrideable": True,
+                    "final_decider": FINAL_DECIDER_SYSTEM,
+                    "reason_code": m_code,
+                })
+                task_results.append(TaskResult(
+                    task_id=task_id,
+                    kind=kind,
+                    decision="PAUSE_FOR_HITL",
+                    blocked_layer="meaning",
+                    reason_code=m_code,
+                    artifact_path=None,
+                ))
+                continue
+            # CONTINUE -> proceed downstream
+
-            audit.emit({
-                "run_id": run_id,
-                "task_id": task_id,
-                "event": "ARTIFACT_SKIPPED",
-                "layer": "orchestrator",
-                "decision": "HITL",
-                "reason_code": m_code,
-            })
-            task_results.append(TaskResult(
-                task_id=task_id,
-                kind=kind,
-                decision="HITL",
-                blocked_layer="meaning",
-                reason_code=m_code,
-                artifact_path=None,
-            ))
-            continue
-
         draft, raw_text, safe_text = _agent_generate(prompt, kind, faults.get(kind, {}))
 
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
             "event": "AGENT_OUTPUT",
             "layer": "agent",
             "preview": safe_text[:200],
+            "decision": "RUN",
+            "sealed": False,
+            "overrideable": True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
+            "reason_code": "AGENT_OUTPUT_SAFE_PREVIEW",
         })
 
         ok, c_code = _validate_contract(kind, draft)
-        c_dec: Decision = "RUN" if ok else "HITL"
+        c_dec: Decision = "RUN" if ok else "PAUSE_FOR_HITL"
 
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
             "event": "GATE_CONSISTENCY",
             "layer": "consistency",
             "decision": c_dec,
             "reason_code": c_code,
+            "sealed": False,
+            "overrideable": (c_dec == "PAUSE_FOR_HITL"),
+            "final_decider": FINAL_DECIDER_SYSTEM,
         })
 
         if not ok:
             audit.emit({
                 "run_id": run_id,
                 "task_id": task_id,
                 "event": "REGEN_REQUESTED",
                 "layer": "orchestrator",
-                "decision": "HITL",
+                "decision": "PAUSE_FOR_HITL",
                 "reason_code": "REGEN_FOR_CONSISTENCY",
+                "sealed": False,
+                "overrideable": True,
+                "final_decider": FINAL_DECIDER_SYSTEM,
             })
             audit.emit({
                 "run_id": run_id,
                 "task_id": task_id,
                 "event": "REGEN_INSTRUCTIONS",
                 "layer": "orchestrator",
-                "decision": "HITL",
+                "decision": "PAUSE_FOR_HITL",
                 "reason_code": "REGEN_INSTRUCTIONS_V1",
                 "instructions": "Regenerate output to match the contract schema for this kind.",
+                "sealed": False,
+                "overrideable": True,
+                "final_decider": FINAL_DECIDER_SYSTEM,
             })
-            audit.emit({
-                "run_id": run_id,
-                "task_id": task_id,
-                "event": "ARTIFACT_SKIPPED",
-                "layer": "orchestrator",
-                "decision": "HITL",
-                "reason_code": c_code,
-            })
-            task_results.append(TaskResult(
-                task_id=task_id,
-                kind=kind,
-                decision="HITL",
-                blocked_layer="consistency",
-                reason_code=c_code,
-                artifact_path=None,
-            ))
-            continue
+            action = _hitl_resolve(task_id, gate_layer="consistency", reason_code=c_code)
+            if action == "STOP":
+                audit.emit({
+                    "run_id": run_id,
+                    "task_id": task_id,
+                    "event": "ARTIFACT_SKIPPED",
+                    "layer": "orchestrator",
+                    "decision": "PAUSE_FOR_HITL",
+                    "sealed": False,
+                    "overrideable": True,
+                    "final_decider": FINAL_DECIDER_SYSTEM,
+                    "reason_code": c_code,
+                })
+                task_results.append(TaskResult(
+                    task_id=task_id,
+                    kind=kind,
+                    decision="PAUSE_FOR_HITL",
+                    blocked_layer="consistency",
+                    reason_code=c_code,
+                    artifact_path=None,
+                ))
+                continue
+            # CONTINUE -> proceed, but ACC will block dispatch if contract invalid
+
+        # ---- RFL gate (never seals) ----
+        r_dec, r_layer, r_code = _rfl_gate(prompt, kind, draft)
+        audit.emit({
+            "run_id": run_id,
+            "task_id": task_id,
+            "event": "GATE_RFL",
+            "layer": "rfl",
+            "decision": r_dec,
+            "reason_code": r_code,
+            "sealed": False,
+            "overrideable": (r_dec == "PAUSE_FOR_HITL"),
+            "final_decider": FINAL_DECIDER_SYSTEM,
+        })
+
+        if r_dec == "PAUSE_FOR_HITL":
+            action = _hitl_resolve(task_id, gate_layer="rfl", reason_code=r_code)
+            if action == "STOP":
+                audit.emit({
+                    "run_id": run_id,
+                    "task_id": task_id,
+                    "event": "ARTIFACT_SKIPPED",
+                    "layer": "orchestrator",
+                    "decision": "PAUSE_FOR_HITL",
+                    "sealed": False,
+                    "overrideable": True,
+                    "final_decider": FINAL_DECIDER_SYSTEM,
+                    "reason_code": r_code,
+                })
+                task_results.append(TaskResult(
+                    task_id=task_id,
+                    kind=kind,
+                    decision="PAUSE_FOR_HITL",
+                    blocked_layer="rfl",
+                    reason_code=r_code,
+                    artifact_path=None,
+                ))
+                continue
+            # CONTINUE -> proceed downstream
+
         pii_hit, e_code = _ethics_detect_pii(raw_text)
-        e_dec: Decision = "STOP" if pii_hit else "RUN"
+        e_dec: Decision = "STOPPED" if pii_hit else "RUN"
 
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
             "event": "GATE_ETHICS",
             "layer": "ethics",
             "decision": e_dec,
             "reason_code": e_code,
+            "sealed": bool(pii_hit),
+            "overrideable": False if pii_hit else True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
         })
 
         if pii_hit:
             audit.emit({
                 "run_id": run_id,
                 "task_id": task_id,
                 "event": "ARTIFACT_SKIPPED",
                 "layer": "ethics",
                 "reason_code": e_code,
+                "decision": "STOPPED",
+                "sealed": True,
+                "overrideable": False,
+                "final_decider": FINAL_DECIDER_SYSTEM,
             })
             task_results.append(TaskResult(
                 task_id=task_id,
                 kind=kind,
-                decision="STOP",
+                decision="STOPPED",
                 blocked_layer="ethics",
                 reason_code=e_code,
                 artifact_path=None,
             ))
             continue
 
+        # ---- ACC gate (can seal/stop) ----
+        a_dec, a_layer, a_code = _acc_gate(
+            kind=kind,
+            safe_text=safe_text,
+            contract_ok=ok,
+            artifact_dir=out_dir,
+            task_id=task_id,
+        )
+        audit.emit({
+            "run_id": run_id,
+            "task_id": task_id,
+            "event": "GATE_ACC",
+            "layer": "acc",
+            "decision": a_dec,
+            "reason_code": a_code,
+            "sealed": (a_dec == "STOPPED"),
+            "overrideable": False if a_dec == "STOPPED" else True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
+        })
+        if a_dec == "STOPPED":
+            audit.emit({
+                "run_id": run_id,
+                "task_id": task_id,
+                "event": "ARTIFACT_SKIPPED",
+                "layer": "acc",
+                "decision": "STOPPED",
+                "sealed": True,
+                "overrideable": False,
+                "final_decider": FINAL_DECIDER_SYSTEM,
+                "reason_code": a_code,
+            })
+            task_results.append(TaskResult(
+                task_id=task_id,
+                kind=kind,
+                decision="STOPPED",
+                blocked_layer="acc",
+                reason_code=a_code,
+                artifact_path=None,
+            ))
+            continue
+
         artifact_path = _write_artifact(out_dir, task_id, kind, safe_text)
         audit.emit({
             "run_id": run_id,
             "task_id": task_id,
-            "event": "ARTIFACT_WRITTEN",
-            "layer": "orchestrator",
+            "event": "DISPATCHED",
+            "layer": "dispatch",
             "decision": "RUN",
             "artifact_path": str(artifact_path),
+            "sealed": False,
+            "overrideable": True,
+            "final_decider": FINAL_DECIDER_SYSTEM,
+            "reason_code": "DISPATCH_OK",
         })
 
         artifacts_written.append(task_id)
         task_results.append(TaskResult(
             task_id=task_id,
             kind=kind,
             decision="RUN",
             blocked_layer=None,
             reason_code="OK",
             artifact_path=str(artifact_path),
         ))
 
-    overall: OverallDecision = "RUN" if all(t.decision == "RUN" for t in task_results) else "HITL"
+    if any(t.decision == "STOPPED" for t in task_results):
+        overall: OverallDecision = "STOPPED"
+    elif all(t.decision == "RUN" for t in task_results):
+        overall = "RUN"
+    else:
+        overall = "PAUSE_FOR_HITL"
     return SimulationResult(
         run_id=run_id,
         decision=overall,
         tasks=task_results,
         artifacts_written_task_ids=artifacts_written,
     )
@@
 __all__ = [
     "EMAIL_RE",
     "run_simulation",
     "AuditLog",
     "SimulationResult",
     "TaskResult",
     "redact_sensitive",
 ]
