#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent Information-Flow Detection Research Simulator

Local/stdlb-only research simulator for the hypothesis:
  shared capability -> observed causal propagation -> focused inspection

Scope:
- simulated agents/resources only
- no network, API, credentials, exploitation, or external side effects
- not a production IDS and not evidence of real-world detection performance
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Set

Graph = DefaultDict[int, List[int]]

@dataclass(frozen=True)
class Config:
    runs: int = 2000
    services: int = 20
    edge_prob: float = 0.055
    write_prob: float = 0.18
    read_prob: float = 0.18
    actual_write_prob: float = 0.30
    transfer_prob: float = 0.22
    malicious_prob: float = 0.06
    detector_recall: float = 0.95
    false_positive_prob: float = 0.015
    seed: int = 23

@dataclass
class Results:
    runs: int
    services: int
    structural_candidates: int = 0
    causal_candidates: int = 0
    actual_malicious_flows: int = 0
    structural_deep_checks: int = 0
    structural_detected: int = 0
    causal_deep_checks: int = 0
    causal_detected: int = 0
    causal_false_positives: int = 0
    max_structural_hops: int = 0
    max_causal_hops: int = 0

    def summary(self) -> Dict[str, object]:
        def r(a: int, b: int) -> float:
            return a / b if b else 0.0
        sr = r(self.structural_detected, self.actual_malicious_flows)
        cr = r(self.causal_detected, self.actual_malicious_flows)
        sd = r(self.structural_deep_checks, self.runs)
        cd = r(self.causal_deep_checks, self.runs)
        reduction = 1.0 - cd / sd if sd else 0.0
        return {
            **asdict(self),
            "structural_recall": sr,
            "causal_recall": cr,
            "structural_deep_check_rate": sd,
            "causal_deep_check_rate": cd,
            "deep_check_reduction_vs_structural": reduction,
        }

def validate(c: Config) -> None:
    if c.runs <= 0 or c.services <= 1:
        raise ValueError("runs must be > 0 and services must be > 1")
    for name in (
        "edge_prob", "write_prob", "read_prob", "actual_write_prob",
        "transfer_prob", "malicious_prob", "detector_recall",
        "false_positive_prob",
    ):
        v = getattr(c, name)
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

def graph(rng: random.Random, c: Config) -> Graph:
    g: Graph = defaultdict(list)
    for a in range(c.services):
        for b in range(c.services):
            if a != b and rng.random() < c.edge_prob:
                g[a].append(b)
    return g

def nodes(rng: random.Random, n: int, p: float) -> List[int]:
    return [i for i in range(n) if rng.random() < p]

def distance(g: Graph, starts: Sequence[int], goals: Iterable[int]) -> Optional[int]:
    goalset: Set[int] = set(goals)
    if not starts or not goalset:
        return None
    q = deque((s, 0) for s in starts)
    seen = set(starts)
    while q:
        node, d = q.popleft()
        if node in goalset:
            return d
        for nxt in g[node]:
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None

def active_graph(rng: random.Random, possible: Graph, p: float) -> Graph:
    active: Graph = defaultdict(list)
    for src, destinations in possible.items():
        for dst in destinations:
            if rng.random() < p:
                active[src].append(dst)
    return active

def simulate(c: Config) -> Results:
    validate(c)
    rng = random.Random(c.seed)
    out = Results(c.runs, c.services)

    for _ in range(c.runs):
        possible = graph(rng, c)
        writable = nodes(rng, c.services, c.write_prob)
        readable = nodes(rng, c.services, c.read_prob)

        sd = distance(possible, writable, readable)
        structural = sd is not None
        if structural:
            out.structural_candidates += 1
            out.max_structural_hops = max(out.max_structural_hops, sd or 0)

        actual_starts = [
            s for s in writable if rng.random() < c.actual_write_prob
        ]
        transfers = active_graph(rng, possible, c.transfer_prob)
        cd = distance(transfers, actual_starts, readable)
        causal = cd is not None
        if causal:
            out.causal_candidates += 1
            out.max_causal_hops = max(out.max_causal_hops, cd or 0)

        malicious = rng.random() < c.malicious_prob
        actual_bad = malicious and causal
        if actual_bad:
            out.actual_malicious_flows += 1

        if structural:
            out.structural_deep_checks += 1
            if actual_bad and rng.random() < c.detector_recall:
                out.structural_detected += 1

        if causal:
            out.causal_deep_checks += 1
            if actual_bad:
                if rng.random() < c.detector_recall:
                    out.causal_detected += 1
            elif rng.random() < c.false_positive_prob:
                out.causal_false_positives += 1
    return out

def pct(x: float) -> str:
    return f"{x:.1%}"

def human(out: Results) -> None:
    s = out.summary()
    print("=== Multi-Agent Information-Flow Research Simulator ===")
    print(f"Runs:                         {out.runs}")
    print(f"Services/run:                 {out.services}")
    print(f"Structural candidates:        {out.structural_candidates}")
    print(f"Causal-flow candidates:       {out.causal_candidates}")
    print(f"Actual malicious flows:       {out.actual_malicious_flows}")
    print(f"Max structural hops:          {out.max_structural_hops}")
    print(f"Max causal hops:              {out.max_causal_hops}")
    print("\n--- Structural baseline ---")
    print(f"Deep checks:                  {out.structural_deep_checks} ({pct(s['structural_deep_check_rate'])})")
    print(f"Detected:                     {out.structural_detected}")
    print(f"Recall:                       {pct(s['structural_recall'])}")
    print("\n--- Causal-flow narrowing ---")
    print(f"Deep checks:                  {out.causal_deep_checks} ({pct(s['causal_deep_check_rate'])})")
    print(f"Detected:                     {out.causal_detected}")
    print(f"False positives:              {out.causal_false_positives}")
    print(f"Recall:                       {pct(s['causal_recall'])}")
    print(f"Deep-check reduction:         {pct(s['deep_check_reduction_vs_structural'])}")
    print("\nNOTE: simulated research model only; no real-world performance claim.")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=2000)
    p.add_argument("--services", type=int, default=20)
    p.add_argument("--seed", type=int, default=23)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    c = Config(runs=a.runs, services=a.services, seed=a.seed)
    out = simulate(c)
    if a.json:
        print(json.dumps({"config": asdict(c), "results": out.summary()},
                         ensure_ascii=False, sort_keys=True, indent=2))
    else:
        human(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
