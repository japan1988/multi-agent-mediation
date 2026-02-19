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
python mediation_emergency_contract_sim_v5_1_2.py
2) Run the contract tests (v5.1.x: simulator + codebook consistency)
bash
コードをコピーする
pytest -q tests/test_v5_1_codebook_consistency.py
3) Inspect / pin the demo codebook (v5.1-demo.1)
log_codebook_v5_1_demo_1.json (demo codebook; pin the version when exchanging artifacts)

Note: the codebook is for compact encoding/decoding of log fields and is NOT encryption.
It provides no confidentiality guarantees.

4) Optional: run the legacy stable bench (v4.8)
bash
コードをコピーする
python mediation_emergency_contract_sim_v4_8.py
bash
コードをコピーする
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
5) Optional: inspect evidence bundle (v4.8 generated artifact)
docs/artifacts/v4_8_artifacts_bundle.zip

Note: evidence bundles (zip) are generated artifacts produced by tests/runs.
The canonical source of truth is the generator scripts + tests.

Architecture (high level)
Audit-ready and fail-closed control flow:

agents
→ mediator (risk / pattern / fact)
→ evidence verification
→ HITL (pause / reset / ban)
→ audit logs (ARL)



If an image does not render
Confirm that:

the file exists under docs/

the filename matches exactly (case-sensitive)

the link points to the same branch you are viewing

Architecture (code-aligned diagrams)
The following diagrams are aligned with the current code vocabulary.
They separate state transitions from gate order to preserve auditability and avoid ambiguity.

Documentation-only. No logic changes.

1) State Machine (code-aligned)
Minimal lifecycle transitions showing where execution pauses (HITL)
or stops permanently (SEALED).

<p align="center"> <img src="docs/architecture_state_machine_code_aligned.png" alt="State Machine (code-aligned)" width="720"> </p>
Primary execution path

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

Notes

PAUSE_FOR_HITL_* represents an explicit Human-in-the-Loop decision point (user approval or admin approval).

STOPPED (SEALED) is reached on:

invalid or fabricated evidence

authorization expiry

draft lint failure

SEALED stops are fail-closed and non-overrideable by design.

2) Gate Pipeline (code-aligned)
Ordered evaluation gates, independent from lifecycle state transitions.

<p align="center"> <img src="docs/architecture_gate_pipeline_code_aligned.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>
Notes

This diagram represents gate order, not state transitions.

PAUSE indicates HITL required (human decision pending).

STOPPED (SEALED) indicates a non-recoverable safety stop.

Design intent

State Machine answers: “Where does execution pause or terminate?”

Gate Pipeline answers: “In what order are decisions evaluated?”

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

What’s new
This project is under active development.

Latest updates: check the commit history (GitHub “Commits”) and release notes (if tagged).

Key additions/changes are documented as needed in docs/ (and/or CHANGELOG.md if present).

Design note: the README stays minimal on purpose to keep the “recommended path” clear.

V1 → V4: What actually changed
mediation_emergency_contract_sim_v1.py demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

mediation_emergency_contract_sim_v4.py turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

Added in v4

Evidence gate
Basic verification of evidence bundles. Invalid/irrelevant/fabricated evidence triggers fail-closed stops.

Draft lint gate
Enforces draft-only semantics and scope boundaries before admin finalization.

Trust system (score + streak + cooldown)
Trust increases on successful HITL outcomes and decreases on failures. Cooldown prevents unsafe automation after errors. All transitions are logged in ARL.

AUTH HITL auto-skip (safe friction reduction)
When trust threshold + approval streak + valid grant are satisfied, AUTH HITL can be skipped for the same scenario/location only, while recording reasons in ARL.

V4 → V5: What changed
V4 focuses on a stable “emergency contract” governance bench with smoke tests and stress runners.
V5 extends that bench toward artifact-level reproducibility and contract-style compatibility checks.

Added / strengthened in V5

Log codebook (demo) + contract tests
V5 introduces a versioned codebook for compact log encoding/decoding and pytest checks that enforce that emitted
vocabularies (layer / decision / final_decider / reason_code) remain consistent.

Reproducibility surface (pin what matters)
V5 encourages pinning simulator version, test version, and codebook version to reproduce results across environments.

Tighter invariant enforcement
V5 adds explicit tests/contracts around core invariants (e.g., sealed only by ethics/acc; relativity gate never sealed),
reducing “silent drift” during refactors.

What did NOT change (still true in V5)

Research / educational intent

Fail-closed + HITL semantics

Use synthetic data only and run in isolated environments

No security guarantees (this is not encryption; tests do not guarantee safety in real-world deployments)

Execution examples
Doc orchestrator (reference implementation)

bash
python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract (recommended: v5.1.2) + contract tests

bash
python mediation_emergency_contract_sim_v5_1_2.py

bash
pytest -q tests/test_v5_1_codebook_consistency.py
Emergency contract (legacy stable bench: v4.8)

bash
python mediation_emergency_contract_sim_v4_8.py
bash
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
Emergency contract (v4.1)

bash
python mediation_emergency_contract_sim_v4_1.py
Emergency contract stress (v4.4)

bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
Project intent / non-goals
Intent
Reproducible safety and governance simulations

Explicit HITL semantics (pause/reset/ban)

Audit-ready decision traces (minimal ARL)

Non-goals
Production-grade autonomous deployment

Unbounded self-directed agent control

Safety claims beyond what is explicitly tested

Data & safety notes
Use synthetic/dummy data only.

Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible.

Treat generated bundles (zip) as reviewable evidence, not canonical source.

License
Apache License 2.0 (see LICENSE)
