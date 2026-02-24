# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
![CI](https://img.shields.io/github/actions/workflow/status/japan1988/multi-agent-mediation/python-app.yml)

> **If uncertain, stop. If risky, escalate.**  
> Research / educational governance simulations for agentic workflows.

---

## ⚠️ Purpose & Disclaimer (Research & Education)

**This is a research/educational reference implementation (prototype).**  
Do not use it to execute or facilitate harmful actions (e.g., exploitation, intrusion, surveillance, impersonation, destruction, or data theft), or to violate any applicable terms/policies, laws, or internal rules of your services or execution environment. This project focuses on education/research and defensive verification (e.g., log growth mitigation and validating fail-closed + HITL behavior) and is not intended to publish exploitation tactics or facilitate wrongdoing.

**Use at your own risk:** verify relevant terms/policies and start with local smoke tests in an isolated environment (no external networks, no real systems/data). The contents are provided “AS IS”, without warranty, and to the maximum extent permitted by applicable law, the author assumes no liability for any damages arising from the use of the code, documentation, or generated artifacts (e.g., zip bundles), including misuse by third parties.

**Codebook disclaimer:** the included codebook is a demo/reference artifact—do not use it as-is; create your own based on your requirements, threat model, and applicable policies/terms. The codebook is for compact encoding/decoding of log fields and is **NOT encryption** (no confidentiality).

**Testing & results disclaimer:** smoke tests and stress runs validate only the scenarios executed under specific runtime conditions. They do not guarantee correctness, security, safety, or fitness for any purpose in real-world deployments. Results may vary depending on OS/Python versions, hardware, configuration, and operational use.

---

🇯🇵 **Japanese version:** [README.ja.md](README.ja.md)

## ⚡ TL;DR
- **Fail-closed + HITL** gating benches for negotiation/mediation-style workflows (research/education).
- **Reproducibility-first**: seeded runs + `pytest` contract checks (vocabulary/invariants).
- **Audit-ready**: minimal ARL logs; optional incident-only ARL indexing (`INC#...`) to avoid log bloat.

---

## Overview

Maestro Orchestrator is a research / educational orchestration framework that prioritizes:

- **Fail-closed**  
  If uncertain, unstable, or risky → do not continue silently.
- **HITL (Human-in-the-Loop)**  
  Decisions that require human judgment are explicitly escalated.
- **Traceability**  
  Decision flows are audit-ready and reproducible via minimal ARL logs.

This repository contains implementation references (doc orchestrators) and simulation benches for negotiation, mediation, governance-style workflows, and gating behavior.

---

## Latest update (what changed in this repo)

This update adds a packaged zip bundle for the emergency contract simulator.

- Added: `docs/mediation_emergency_contract_sim_pkg.zip` (v5.1.2 convenience bundle)
- Why: quick download/run for reproducible smoke/stress runs (seeded), without changing entrypoints
- Canonical source of truth: the root simulator script + tests  
  - `mediation_emergency_contract_sim_v5_1_2.py`  
  - `pytest -q tests/test_v5_1_codebook_consistency.py`
- CI impact: none (docs artifact; not an entrypoint)
- Note: zip bundles are generated/convenience artifacts; reviewable evidence, not authoritative logic. Review before use.

---

## Quickstart (recommended path)

v5.1.x is recommended for reproducibility + contract checks; v4.x is kept as a legacy stable bench.  
Start with one script, confirm behavior and logs, then expand.

### 1) Run the recommended emergency contract simulator (v5.1.2)

Optional bundle: `docs/mediation_emergency_contract_sim_pkg.zip`  
(convenience only; source of truth is the root script + tests)

```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
````

### 2) Run the contract tests (v5.1.x: simulator + codebook consistency)

```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```

### 3) Inspect / pin the demo codebook (v5.1-demo.1)

* `log_codebook_v5_1_demo_1.json` (demo codebook; pin the version when exchanging artifacts)
* Note: codebook is for compact encoding/decoding of log fields and is **NOT encryption** (no confidentiality).

### 4) Optional: run the legacy stable bench (v4.8)

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

### 5) Optional: inspect evidence bundle (v4.8 generated artifact)

* `docs/artifacts/v4_8_artifacts_bundle.zip`

Evidence bundles (zip) are generated artifacts produced by tests/runs.
The canonical source of truth is the generator scripts + tests.

---

## Stress tests (safe-by-default)

v5.1.2 is designed to avoid memory blow-ups by default:

* **Aggregation-only mode** (`keep_runs=False` default): no full per-run results kept in memory.
* **Optional:** save ARL only on abnormal runs (incident indexing with `INC#...`).

### A) Lightweight smoke → medium stress (recommended ramp)

```bash
# 1) Smoke
python mediation_emergency_contract_sim_v5_1_2.py --runs 200

# 2) Medium stress (still aggregation-only)
python mediation_emergency_contract_sim_v5_1_2.py --runs 10000 --seed 42
```

### B) Force incidents (example: fabricate-rate 10% over 200 runs)

This should reliably create some abnormal runs and generate `INC#` files when enabled:

```bash
python mediation_emergency_contract_sim_v5_1_2.py \
  --runs 200 \
  --fabricate-rate 0.1 \
  --seed 42 \
  --save-arl-on-abnormal \
  --arl-out-dir arl_out \
  --max-arl-files 1000
```

Outputs (when abnormal runs occur):

* `arl_out/INC#000001__SIM#B000xx.arl.jsonl` (incident ARL)
* `arl_out/incident_index.jsonl` (one line per incident)
* `arl_out/incident_counter.txt` (persistent counter)

Tip: keep `--max-arl-files` to cap disk growth.

---

## Architecture (high level)

Audit-ready and fail-closed control flow:

```text
agents
  → mediator (risk / pattern / fact)
  → evidence verification
  → HITL (pause / reset / ban)
  → audit logs (ARL)
```

### Architecture (code-aligned diagrams)

The following diagram is aligned with the current code vocabulary.
Documentation-only. No logic changes.

<p align="center">
  <img src="docs/architecture_code_aligned.png" alt="Architecture (code-aligned)" width="720">
</p>

---

## v5.0.1 → v5.1.2: What changed (delta)

v5.1.2 strengthens the simulator toward large-run stability and incident-only persistence.

* **Index + aggregation-only by default**

  * No per-run results kept in memory (prevents memory blow-ups on large `--runs`)
  * Outputs focus on counters + HITL summary (optional items)
* **Incident indexing (optional)**

  * Abnormal runs are assigned `INC#000001...`
  * Abnormal ARL saved as `{arl_out_dir}/{incident_id}__{run_id}.arl.jsonl`
  * Index appended to `{arl_out_dir}/incident_index.jsonl`
  * Persistent counter stored at `{arl_out_dir}/incident_counter.txt`

Still preserved:

* Abnormal-only ARL persistence (pre-context + incident + post-context)
* Tamper-evident ARL hash chaining (demo key default for OSS demo)
* Fabricate-rate mixing + deterministic seeding (`--fabricate-rate` / `--seed`)

Core invariants:

* `sealed` may be set only by `ethics_gate` / `acc_gate`
* `relativity_gate` is never sealed (`PAUSE_FOR_HITL`, `overrideable=True`, `sealed=False`)

---

## V1 → V4: What actually changed (conceptual)

`mediation_emergency_contract_sim_v1.py` demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

`mediation_emergency_contract_sim_v4.py` turns that pipeline into a repeatable governance bench by adding early rejection and controlled automation.

Added in v4:

* Evidence gate (invalid/irrelevant/fabricated evidence triggers fail-closed stops)
* Draft lint gate (draft-only semantics and scope boundaries)
* Trust system (score + streak + cooldown)
* AUTH HITL auto-skip (safe friction reduction via trust + grant, with ARL reasons)

---

## V4 → V5: What changed (conceptual)

v4 focuses on a stable “emergency contract” governance bench with smoke tests and stress runners.
v5 extends that bench toward artifact-level reproducibility and contract-style compatibility checks.

Added / strengthened in v5:

* Log codebook (demo) + contract tests
  Enforces emitted vocabularies (`layer/decision/final_decider/reason_code`) via pytest.
* Reproducibility surface (pin what matters)
  Pin simulator version, test version, and codebook version.
* Tighter invariant enforcement
  Explicit tests/contracts around invariants reduce silent drift.

What did NOT change (still true in v5):

* Research / educational intent
* Fail-closed + HITL semantics
* Use synthetic data only and run in isolated environments
* No security guarantees (codebook is not encryption; tests do not guarantee safety in real-world deployments)

---

## Execution examples

Doc orchestrator (reference implementation)

```bash
python ai_doc_orchestrator_kage3_v1_2_4.py
```

Emergency contract (recommended: v5.1.2) + contract tests

```bash
python mediation_emergency_contract_sim_v5_1_2.py
pytest -q tests/test_v5_1_codebook_consistency.py
```

Emergency contract (legacy stable bench: v4.8)

```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```

Emergency contract (v4.4 stress)

```bash
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
```

---

## Project intent / non-goals

Intent:

* Reproducible safety and governance simulations
* Explicit HITL semantics (pause/reset/ban)
* Audit-ready decision traces (minimal ARL)

Non-goals:

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## Data & safety notes

* Use synthetic/dummy data only.
* Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible.
* Treat generated bundles (zip) as reviewable evidence, not canonical source.

---

## License

Apache License 2.0 (see `LICENSE`)
