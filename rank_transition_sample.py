diff --git a/rank_transition_sample.py b/rank_transition_sample.py
index 1111111..2222222 100644
--- a/rank_transition_sample.py
+++ b/rank_transition_sample.py
@@ -1,6 +1,9 @@
 # -*- coding: utf-8 -*-
 """
 Hierarchy Rank Transition plotter
+
+Note:
+- For reproducibility, this script supports an optional RNG seed.
 """
 from __future__ import annotations
 
@@ -36,11 +39,17 @@ def run_simulation(
     initial_follow_rate: float = 0.5,
     steps: int = 50,
     mediation_interval: int = 5,
     mediation_strength: float = 0.5,
+    seed: int | None = None,
 ) -> list[float]:
+    # Reproducibility: if seed is provided, make the simulation deterministic.
+    if seed is not None:
+        random.seed(seed)
+
     agents = [
         AIAgent(
             agent_id=i,
             is_rule_follower=(random.random() < initial_follow_rate),
             self_purpose=random.uniform(0.0, 0.5),
@@ -70,7 +79,7 @@ def run_simulation(
 
 def main() -> None:
     steps = 50
-    rates = run_simulation(steps=steps, mediation_strength=0.5)
+    rates = run_simulation(steps=steps, mediation_strength=0.5, seed=42)
 
     plt.figure(figsize=(6, 4))
     plt.plot(range(steps), rates, marker="o")
     plt.ylim(0.0, 1.0)
