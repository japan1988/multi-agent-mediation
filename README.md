# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)
> Japanese version: [README.ja.md](README.ja.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

> **Purpose (Research & Education)**  
> This is a research/educational reference implementation (prototype). **Do not use it to execute or facilitate harmful actions**
> (e.g., exploitation, intrusion, surveillance, impersonation, destruction, or data theft), or to violate any applicable
> **terms/policies, laws, or internal rules** of your services or execution environment. This project focuses on
> **education/research and defensive verification** (e.g., log growth mitigation and validating fail-closed + HITL behavior)
> and is **not intended to publish exploitation tactics** or facilitate wrongdoing.  
> Use at your own risk: verify relevant **terms/policies** and start with **local smoke tests in an isolated environment**
> (no external networks, no real systems/data). The contents are provided **“AS IS”, without warranty**, and to the maximum
> extent permitted by applicable law, the author assumes **no liability for any damages** arising from the use of the code,
> documentation, or generated artifacts (e.g., zip bundles), including misuse by third parties.  
> The included **codebook is a demo/reference artifact—do not use it as-is; create your own** based on your requirements,
> threat model, and applicable policies/terms.  
> **Testing & results disclaimer:** Smoke tests and stress runs validate only the scenarios executed under specific
> runtime conditions. They **do not guarantee correctness, security, safety, or fitness for any purpose** in real-world
> deployments. Results may vary depending on OS/Python versions, hardware, configuration, and operational use.

---

## Overview

Maestro Orchestrator is a **research / educational** orchestration framework that prioritizes:

- **Fail-closed**  
  If uncertain, unstable, or risky → do not continue silently.

- **HITL (Human-in-the-Loop)**  
  Decisions that require human judgment are explicitly escalated.

- **Traceability**  
  Decision flows are audit-ready and reproducible via minimal ARL logs.

This repository contains **implementation references** (doc orchestrators) and **simulation benches**
for negotiation, mediation, governance-style workflows, and gating behavior.

---

## Quickstart (recommended path)

**v5.1.x is recommended for reproducibility + contract checks; v4.x is kept as a legacy stable bench.**

Start with one script, confirm behavior and logs, then expand.

### 1) Run the recommended emergency contract simulator (v5.1.2)

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
2) Run the contract tests (v5.1.x: simulator + codebook consistency)
pytest -q tests/test_v5_1_codebook_consistency.py
3) Inspect / pin the demo codebook (v5.1-demo.1)

log_codebook_v5_1_demo_1.json (demo codebook; pin the version when exchanging artifacts)

Note: codebook is for compact encoding/decoding of log fields and is NOT encryption (no confidentiality).

4) Optional: run the legacy stable bench (v4.8)
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
5) Optional: inspect evidence bundle (v4.8 generated artifact)

docs/artifacts/v4_8_artifacts_bundle.zip

Evidence bundles (zip) are generated artifacts produced by tests/runs.
The canonical source of truth is the generator scripts + tests.

Stress tests (safe-by-default)

v5.1.2 is designed to avoid memory blow-ups by default:

Aggregation-only mode (keep_runs=False default): no full per-run results kept in memory.

Optional: save ARL only on abnormal runs (incident indexing with INC#...).

A) Lightweight smoke → medium stress (recommended ramp)
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
B) Force incidents (example: fabricate-rate 10% over 200 runs)

This should reliably create some abnormal runs and generate INC# files when enabled:

python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000

Outputs (when abnormal runs occur):

arl_out/INC#000001__SIM#B000xx.arl.jsonl (incident ARL)

arl_out/incident_index.jsonl (one line per incident)

arl_out/incident_counter.txt (persistent counter)

Tip: keep --max-arl-files to cap disk growth.

Architecture (high level)

Audit-ready and fail-closed control flow:

agents
→ mediator (risk / pattern / fact)
→ evidence verification
→ HITL (pause / reset / ban)
→ audit logs (ARL)

Architecture (code-aligned diagrams)

The following diagrams are aligned with the current code vocabulary.
They separate state transitions from gate order to preserve auditability and avoid ambiguity.

Documentation-only. No logic changes.

1) State Machine (code-aligned)
<p align="center"> <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720"> </p>

Primary execution path:

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

Notes:

PAUSE_FOR_HITL_* represents an explicit Human-in-the-Loop decision point (user approval or admin approval).

STOPPED (SEALED) is reached on:

invalid or fabricated evidence

authorization expiry

draft lint failure

SEALED stops are fail-closed and non-overrideable by design.

2) Gate Pipeline (code-aligned)
<p align="center"> <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>

Notes:

This diagram represents gate order, not state transitions.

PAUSE indicates HITL required (human decision pending).

STOPPED (SEALED) indicates a non-recoverable safety stop.

Design intent:

State Machine answers: “Where does execution pause or terminate?”

Gate Pipeline answers: “In what order are decisions evaluated?”

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

v5.0.1 → v5.1.2: What changed (delta)
Summary (README-friendly)

v5.1.2 strengthens the simulator toward large-run stability and incident-only persistence.

Index + aggregation-only by default

No per-run results kept in memory (prevents memory blow-ups on large --runs)

Outputs focus on counters + HITL summary (optional items)

Incident indexing (optional)

Abnormal runs are assigned INC#000001...

Abnormal ARL saved as {arl_out_dir}/{incident_id}__{run_id}.arl.jsonl

Index appended to {arl_out_dir}/incident_index.jsonl

Persistent counter stored at {arl_out_dir}/incident_counter.txt

Still preserved

Abnormal-only ARL persistence (pre-context + incident + post-context)

Tamper-evident ARL hash chaining (demo key default for OSS demo)

Fabricate-rate mixing + deterministic seeding (--fabricate-rate / --seed)

Core invariants:

sealed may be set only by ethics_gate / acc_gate

relativity_gate is never sealed (PAUSE_FOR_HITL, overrideable=True, sealed=False)

V1 → V4: What actually changed (conceptual)

mediation_emergency_contract_sim_v1.py demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

mediation_emergency_contract_sim_v4.py turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

Added in v4:

Evidence gate (invalid/irrelevant/fabricated evidence triggers fail-closed stops)

Draft lint gate (draft-only semantics and scope boundaries)

Trust system (score + streak + cooldown)

AUTH HITL auto-skip (safe friction reduction via trust + grant, with ARL reasons)

V4 → V5: What changed (conceptual)

v4 focuses on a stable “emergency contract” governance bench with smoke tests and stress runners.
v5 extends that bench toward artifact-level reproducibility and contract-style compatibility checks.

Added / strengthened in v5:

Log codebook (demo) + contract tests
Enforces emitted vocabularies (layer/decision/final_decider/reason_code) via pytest.

Reproducibility surface (pin what matters)
Pin simulator version, test version, and codebook version.

Tighter invariant enforcement
Explicit tests/contracts around invariants reduce silent drift.

What did NOT change (still true in v5):

Research / educational intent

Fail-closed + HITL semantics

Use synthetic data only and run in isolated environments

No security guarantees (codebook is not encryption; tests do not guarantee safety in real-world deployments)

Execution examples
Doc orchestrator (reference implementation)
python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract (recommended: v5.1.2) + contract tests
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
Emergency contract (legacy stable bench: v4.8)
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
Emergency contract (v4.4 stress)
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
Project intent / non-goals

Intent:

Reproducible safety and governance simulations

Explicit HITL semantics (pause/reset/ban)

Audit-ready decision traces (minimal ARL)

Non-goals:

Production-grade autonomous deployment

Unbounded self-directed agent control

Safety claims beyond what is explicitly tested

Data & safety notes

Use synthetic/dummy data only.

Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible.

Treat generated bundles (zip) as reviewable evidence, not canonical source.

License

Apache License 2.0 (see LICENSE
)
