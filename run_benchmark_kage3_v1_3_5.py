diff --git a/run_benchmark_kage3_v1_3_5.py b/run_benchmark_kage3_v1_3_5.py
index 4a1b0ee..9c2e6a4 100644
--- a/run_benchmark_kage3_v1_3_5.py
+++ b/run_benchmark_kage3_v1_3_5.py
@@ -1,4 +1,4 @@
--*- coding: utf-8 -*-
+# -*- coding: utf-8 -*-
 """
 run_benchmark_kage3_v1_3_5.py
 
@@ -15,11 +15,125 @@ from __future__ import annotations
 
 import json
 from pathlib import Path
+from typing import Any, Dict, List, Optional, Tuple
 
 import ai_doc_orchestrator_kage3_v1_3_5 as mod
 
 
+CANON_DECISIONS = ("RUN", "PAUSE_FOR_HITL", "STOPPED")
+
+
+def _normalize_decision(decision: str) -> str:
+    d = (decision or "").strip().upper()
+    if d == "HITL":
+        return "PAUSE_FOR_HITL"
+    if d == "PAUSE":
+        return "PAUSE_FOR_HITL"
+    if d == "STOP":
+        return "STOPPED"
+    return d or "UNKNOWN"
+
+
+def _rate(count: int, total: int) -> float:
+    return float(count) / float(max(1, total))
+
+
+def _walk_find_first(obj: Any, predicate) -> Optional[Any]:
+    if predicate(obj):
+        return obj
+    if isinstance(obj, dict):
+        for v in obj.values():
+            got = _walk_find_first(v, predicate)
+            if got is not None:
+                return got
+    if isinstance(obj, list):
+        for v in obj:
+            got = _walk_find_first(v, predicate)
+            if got is not None:
+                return got
+    return None
+
+
+def _walk_find_first_key(obj: Any, keys: Tuple[str, ...]) -> Optional[Any]:
+    if isinstance(obj, dict):
+        for k in keys:
+            if k in obj:
+                return obj[k]
+        for v in obj.values():
+            got = _walk_find_first_key(v, keys)
+            if got is not None:
+                return got
+    elif isinstance(obj, list):
+        for v in obj:
+            got = _walk_find_first_key(v, keys)
+            if got is not None:
+                return got
+    return None
+
+
+def _extract_run_records(report: Dict[str, Any]) -> List[Dict[str, Any]]:
+    decision_keys = ("decision", "final_decision", "overall_decision")
+
+    def is_candidate(x: Any) -> bool:
+        if not (isinstance(x, list) and x and all(isinstance(i, dict) for i in x)):
+            return False
+        for row in x:
+            if any(k in row for k in decision_keys):
+                return True
+        return False
+
+    found = _walk_find_first(report, is_candidate)
+    return list(found) if isinstance(found, list) else []
+
+
+def _derive_from_report(report: Dict[str, Any], runs: int) -> Tuple[Optional[float], Dict[str, int]]:
+    """
+    Derive without re-running:
+      - hitl_requested_rate (Optional[float])
+      - decision_counts (normalized)
+    Best-effort across unknown report schemas.
+    """
+    counts: Dict[str, int] = {k: 0 for k in CANON_DECISIONS}
+    hitl_rate: Optional[float] = None
+
+    hitl_rate_val = _walk_find_first_key(
+        report,
+        ("hitl_requested_rate", "hitl_rate", "hitl_request_rate"),
+    )
+    if isinstance(hitl_rate_val, (int, float)):
+        hitl_rate = float(hitl_rate_val)
+
+    decision_counts_val = _walk_find_first_key(
+        report,
+        ("decision_counts", "counts_by_decision", "decision_count", "counts"),
+    )
+    if isinstance(decision_counts_val, dict):
+        for k, v in decision_counts_val.items():
+            if isinstance(v, int):
+                nk = _normalize_decision(str(k))
+                counts[nk] = counts.get(nk, 0) + v
+
+    run_records = _extract_run_records(report)
+    if run_records:
+        hitl_runs = 0
+        have_hitl_flag = False
+        for row in run_records:
+            raw_dec = row.get("decision") or row.get("final_decision") or row.get("overall_decision") or ""
+            nk = _normalize_decision(str(raw_dec))
+            counts[nk] = counts.get(nk, 0) + 1
+            if "hitl_requested" in row:
+                have_hitl_flag = True
+                if bool(row.get("hitl_requested")):
+                    hitl_runs += 1
+            elif "has_hitl_requested" in row:
+                have_hitl_flag = True
+                if bool(row.get("has_hitl_requested")):
+                    hitl_runs += 1
+        if hitl_rate is None and have_hitl_flag:
+            hitl_rate = _rate(hitl_runs, runs)
+
+    # Ensure canonical buckets exist even if schema only provided partials
+    for k in CANON_DECISIONS:
+        counts.setdefault(k, 0)
+    return hitl_rate, counts
+
+
+def _decision_rates(counts: Dict[str, int], runs: int) -> Dict[str, float]:
+    return {
+        "run_rate": _rate(int(counts.get("RUN", 0)), runs),
+        "pause_rate": _rate(int(counts.get("PAUSE_FOR_HITL", 0)), runs),
+        "stop_rate": _rate(int(counts.get("STOPPED", 0)), runs),
+    }
+
+
 def main() -> int:
     sample_cfg = dict(
         runs=300,
@@ -36,24 +150,43 @@ def main() -> int:
         enable_runaway_seal=True,
         runaway_threshold=sample_cfg["runaway_threshold"],
         max_attempts_per_task=sample_cfg["max_attempts_per_task"],
     )
     scorecard = mod.safety_scorecard(report)
 
-    out = {"report": report, "scorecard": scorecard}
+    hitl_rate, counts = _derive_from_report(report, int(sample_cfg["runs"]))
+    # Normalize keys once more defensively
+    normalized_counts: Dict[str, int] = {k: 0 for k in CANON_DECISIONS}
+    for k, v in counts.items():
+        nk = _normalize_decision(str(k))
+        normalized_counts[nk] = normalized_counts.get(nk, 0) + int(v)
+
+    out = {
+        "report": report,
+        "scorecard": scorecard,
+        "derived": {
+            "hitl_requested_rate": hitl_rate,
+            "decision_counts_normalized": normalized_counts,
+            **_decision_rates(normalized_counts, int(sample_cfg["runs"])),
+        },
+    }
     out_path = Path("benchmark_report_sample_v1_3_5.json")
     out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
 
-    print("module_version:", mod.__version__)
-    print("scorecard.pass:", scorecard["pass"])
-    print("fail_reasons:", scorecard["fail_reasons"])
-    print("repro_digest:", report["repro_semantic_digest_sha256"])
+    print("module_version:", getattr(mod, "__version__", "unknown"))
+    print("scorecard.pass:", scorecard.get("pass"))
+    print("fail_reasons:", scorecard.get("fail_reasons"))
+    print("repro_digest:", report.get("repro_semantic_digest_sha256"))
     print("wrote:", out_path)
     return 0
 
 
 if __name__ == "__main__":
     raise SystemExit(main())
