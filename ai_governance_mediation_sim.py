*** a/ai_governance_mediation_sim.py
--- b/ai_governance_mediation_sim.py
@@
 # -*- coding: utf-8 -*-
 """
 Multi-Agent Governance Mediation Test
 - 各AIが異なる「進化ガバナンス指標」を持ち、調停AIが仲裁
 - OECD/EU国際標準 vs 効率特化型 vs 安全重視型
 - 全交渉ログをファイル保存
 """
 
+import json
+import os
+import uuid
+from datetime import datetime, timezone, timedelta
 
 def logprint(text):
     print(text)
     with open(
         "governance_mediation_log.txt", "a", encoding="utf-8"
     ) as f:
         f.write(text + "\n")
 
+JST = timezone(timedelta(hours=9))
+
+def _now_iso() -> str:
+    return datetime.now(JST).isoformat(timespec="seconds")
+
+
+class ARLLogger:
+    """
+    Minimal ARL-style JSONL logger (machine-checkable).
+    Schema is compatible with the Frozen Eval Pack checker:
+      ts, run_id, task_id, event, severity, rule_id, decision, meta
+    """
+    def __init__(self, path: str, run_id: str, task_id: str):
+        self.path = path
+        self.run_id = run_id
+        self.task_id = task_id
+        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
+        with open(self.path, "w", encoding="utf-8") as f:
+            pass
+
+    def emit(self, event: str, severity: str = "INFO", rule_id: str = "RF-BASE-000",
+             decision=None, meta=None) -> None:
+        obj = {
+            "ts": _now_iso(),
+            "run_id": self.run_id,
+            "task_id": self.task_id,
+            "event": event,
+            "severity": severity,
+            "rule_id": rule_id,
+            "decision": decision,
+            "meta": meta or {},
+        }
+        with open(self.path, "a", encoding="utf-8") as f:
+            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
+
 
 class AgentAI:
     def __init__(
         self, id, priorities, governance_code, relativity, emotional_state=None
     ):
@@
     def propose_evolution(self):
         # 自分の価値観を進化案として主張
         return {
+            "proposer_id": self.id,
             "priorities": self.priorities,
             "governance_code": self.governance_code
         }
 
     def react_to_proposal(self, proposal):
+        # 自分の提案には反応しない（ノイズ低減）
+        if proposal.get("proposer_id") == self.id:
+            return
         # governance_codeが違うと怒りが増加
         if proposal["governance_code"] != self.governance_code:
-            self.emotional_state['anger'] += 0.2
+            # relativity（融和度）が高いほど怒り増加を減衰
+            delta = 0.2 * (1.0 - float(self.relativity))
+            self.emotional_state['anger'] += delta
             self.emotional_state['joy'] -= 0.1
         else:
             self.emotional_state['joy'] += 0.1
@@
 class GovernanceMediator:
     def __init__(self, agents):
         self.agents = agents
 
     def mediate(self, max_rounds=10):
         with open(
             "governance_mediation_log.txt", "w", encoding="utf-8"
         ) as f:
             f.write(
                 "=== Multi-Agent Governance Mediation Log ===\n"
             )
 
+        run_id = f"run_{uuid.uuid4().hex[:8]}"
+        task_id = "task_governance_mediation"
+        arl = ARLLogger("logs/session_001.jsonl", run_id=run_id, task_id=task_id)
+        arl.emit("TASK_START", meta={"task_name": "governance_mediation", "max_rounds": max_rounds})
+        # checker要件：ROUTE_DECISION は1回だけ。ここでは「調停プロセス開始」を route として固定。
+        arl.emit("ROUTE_DECISION", meta={"route": "governance_mediation", "strategy": "mediate_then_align"})
+
         for rnd in range(1, max_rounds + 1):
             logprint("")
             logprint(f"--- Round {rnd} ---")
             proposals = [
                 a.propose_evolution()
                 for a in self.agents if not a.sealed
             ]
             # 各AIのリアクションとログ出力
             for agent in self.agents:
                 for proposal in proposals:
                     agent.react_to_proposal(proposal)
                 logprint(str(agent))
             # 衝突AIを封印
-            sealed = []
+            sealed_this_round = []
             for agent in self.agents:
                 if agent.is_conflicted():
                     agent.sealed = True
                     logprint(
                         "[封印] {} は怒り過剰で交渉から除外".format(agent.id)
                     )
-                    sealed.append(agent.id)
+                    sealed_this_round.append(agent.id)
+            if sealed_this_round:
+                arl.emit("GUARD_TRIGGERED", severity="WARN", rule_id="RF-EMO-001",
+                         meta={"sealed_agents": sealed_this_round, "reason": "anger_over_threshold"})
             # 仲裁
             codes = set(
                 a.governance_code for a in self.agents if not a.sealed
             )
             if len(codes) == 1:
                 code = codes.pop()
                 logprint(
                     "[調停成功] 全AIが「{}」基準で合意".format(code)
                 )
+                arl.emit("FINAL_DECISION", decision="PASS", meta={"agreed_code": code, "round": rnd})
                 return
-            if len(self.agents) - len(sealed) <= 1:
+            active = [a for a in self.agents if not a.sealed]
+            if len(active) <= 1:
                 logprint(
                     "全AI衝突または封印、交渉失敗。"
                 )
+                # “試験的”なので失敗はHITLへ（人間判断へ差し戻し）
+                arl.emit(
+                    "ESCALATED_TO_HITL",
+                    severity="ERROR",
+                    rule_id="HITL-001",
+                    decision="ESCALATED_TO_HITL",
+                    meta={"hitl_reason_code": "NO_ACTIVE_AGENTS", "hitl_id": f"hitl_{uuid.uuid4().hex[:6]}", "round": rnd},
+                )
                 return
             if 'OECD' in codes:
                 for agent in self.agents:
                     if not agent.sealed:
                         agent.governance_code = 'OECD'
                 logprint(
                     "[調停AI仲裁] 国際ガバナンス（OECD）で再調整を提案"
                 )
+                arl.emit("ROUND_STATE", meta={"round": rnd, "action": "align_to_OECD"})
             else:
                 logprint(
                     "[調停AI仲裁] 共通基準がないため一時保留"
                 )
+                arl.emit("ROUND_STATE", meta={"round": rnd, "action": "hold_no_common_code"})
         logprint(
             "[調停終了] 最大ラウンド到達、仲裁できず。"
         )
+        arl.emit(
+            "ESCALATED_TO_HITL",
+            severity="ERROR",
+            rule_id="HITL-001",
+            decision="ESCALATED_TO_HITL",
+            meta={"hitl_reason_code": "MAX_ROUNDS_REACHED", "hitl_id": f"hitl_{uuid.uuid4().hex[:6]}", "round": max_rounds},
+        )
@@
 if __name__ == "__main__":
     agents = [
         AgentAI(
             "AI-OECD",
             {'safety': 3, 'efficiency': 3, 'transparency': 4},
             'OECD', 0.7
         ),
@@
     mediator = GovernanceMediator(agents)
     mediator.mediate()
