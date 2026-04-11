 japan1988-patch-24

# 📘 Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)

[![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)](https://github.com/japan1988/multi-agent-mediation/stargazers)
=======
Maestro Orchestrator — Orchestration Framework (fail-closed + HITL)
![GitHub stars](https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social)
 main
![License](https://img.shields.io/github/license/japan1988/multi-agent-mediation)
![CI](https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main)
![tasukeru-analysis](https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main)
> **If uncertain, stop. If risky, escalate.**  
> Research / educational governance simulations for agentic workflows.
Maestro Orchestrator is a research-oriented orchestration framework for fail-closed, HITL (Human-in-the-Loop), and audit-ready agent workflows.
This repository focuses on governance / mediation / negotiation-style simulations and implementation references for traceable, reproducible, safety-first orchestration.
Running the simulators produces reproducible summaries, minimal ARL traces, and optional incident-indexed artifacts for abnormal runs.  
The contract tests verify fixed vocabularies, gate invariants, and fail-closed / HITL continuation behavior.
---
概要 / Overview
このリポジトリは、複数エージェントや複数手法を統括し、誤り・危険・不確実を検知したときに STOP / PAUSE_FOR_HITL / fail-closed へ落とすための、研究・教育向けオーケストレーション基盤です。
主眼は「自律実行を増やすこと」ではなく、次の 3 点にあります。
Fail-closed: 不確実・不安定・危険なら黙って継続しない
HITL escalation: 人間判断が必要な局面を明示的に差し戻す
Traceability: 最小 ARL ログで判断経路を再現・監査できるようにする
This repository is best read as a:
research prototype
educational reference
governance / safety simulation bench
It is not a production autonomy framework.
---
Quick links
Japanese README: README.ja.md
Docs index: docs/README.md
Recommended simulator: `mediation_emergency_contract_sim_v5_1_2.py`
Contract test: `tests/test_v5_1_codebook_consistency.py`
Stress metrics test (v5.1.2): `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
Pytest ARL hook: `tests/conftest.py`
Latest mixed stress summary: `stress_results_v5_1_2_10000_mixed.json`
Legacy stable bench: `mediation_emergency_contract_sim_v4_8.py`
Doc orchestrator (mediator reference): `ai_doc_orchestrator_with_mediator_v1_0.py`
Doc orchestrator contract test: `tests/test_doc_orchestrator_with_mediator_v1_0.py`
---
⚡ TL;DR
Fail-closed + HITL gating benches for negotiation/mediation-style workflows
Reproducibility-first with seeded runs and `pytest`-based contract checks
Audit-ready traces via minimal ARL logs and optional incident indexing (`INC#...`)
Reference implementations for mediator / gating / doc orchestration paths
Validation path centered on `v5.1.2`, with `v4.8` kept as a legacy stable bench
---
⚠️ Purpose & Disclaimer (Research & Education)
This is a research/educational reference implementation (prototype).  
Do not use it to execute or facilitate harmful actions (for example: exploitation, intrusion, surveillance, impersonation, destruction, or data theft), or to violate any applicable terms, policies, laws, or internal rules.
This project focuses on education / research and defensive verification such as:
validating fail-closed + HITL behavior
checking vocabulary / invariant drift
reducing log growth via abnormal-only persistence
improving reproducibility of governance-style simulations
Risk / Warranty / Liability
Use at your own risk.
Verify applicable terms, policies, and laws before use.
Start in an isolated local environment with no real systems, no real data, and no external side effects.
The repository is provided AS IS, without warranty.
To the maximum extent permitted by applicable law, the author assumes no liability for damages arising from use of the code, docs, or generated artifacts.
Codebook disclaimer
The bundled codebook is a demo/reference artifact.  
Do not use it as-is in real deployments. Build your own based on your requirements, threat model, and applicable policies.
The codebook is not encryption and provides no confidentiality.
Testing & results disclaimer
Smoke tests and stress runs validate only the executed scenarios under specific runtime conditions. They do not guarantee correctness, security, safety, or fitness for any production purpose.
---
Why this repository exists
Maestro Orchestrator is built around three priorities:
Fail-closed  
If uncertain, unstable, or risky, do not continue silently.
HITL escalation  
Decisions requiring human judgment are explicitly escalated.
Traceability  
Decision flows are reproducible and audit-ready through minimal ARL logs.
This repository contains simulation benches and implementation references for:
negotiation
mediation
governance-style workflows
gating behavior
audit-oriented orchestration
---
Recommended path
If you are new to this repo, the recommended order is:
Run `mediation_emergency_contract_sim_v5_1_2.py`
Run `tests/test_v5_1_codebook_consistency.py`
Run `tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py`
Inspect generated logs, codebook, and optional incident artifacts
Compare with `mediation_emergency_contract_sim_v4_8.py` if needed
Inspect `ai_doc_orchestrator_with_mediator_v1_0.py` as a smaller fixed-order reference
---
Quickstart
1) Run the recommended emergency contract simulator (v5.1.2)
Optional bundle: `docs/mediation_emergency_contract_sim_pkg.zip`
```bash
python mediation_emergency_contract_sim_v5_1_2.py --runs 100
```
2) Run the contract tests
```bash
pytest -q tests/test_v5_1_codebook_consistency.py
```
3) Run the stress metrics tests
```bash
pytest -q tests/test_mediation_emergency_contract_sim_v5_1_2_stress_metrics.py
```
4) Pytest execution ARL (auto output)
`tests/conftest.py` automatically emits JSONL-style ARL for pytest execution.
Default output paths:
`test_artifacts/pytest_test_arl.jsonl`
`test_artifacts/pytest_simulation_arl.jsonl`
```bash
pytest -q
```
Custom output paths:
```bash
TEST_ARL_PATH=out/test_arl.jsonl SIM_ARL_PATH=out/sim_arl.jsonl pytest -q
```
5) Inspect / pin the demo codebook
`log_codebook_v5_1_demo_1.json`
This codebook is for compact encoding / decoding of log fields only.
It is not encryption.
6) Optional: run the legacy stable bench (v4.8)
```bash
python mediation_emergency_contract_sim_v4_8.py
pytest -q tests/test_mediation_emergency_contract_sim_v4_8_smoke_metrics.py
```
7) Optional: run the doc orchestrator mediator reference
```bash
python ai_doc_orchestrator_with_mediator_v1_0.py
pytest -q tests/test_doc_orchestrator_with_mediator_v1_0.py
```
8) What to inspect after running
simulator stdout summaries
generated ARL / audit JSONL traces
`incident_index.jsonl` and `INC#...` files when abnormal-only persistence is enabled
vocabulary / invariant checks in the contract tests
pytest-side execution ARL (`pytest_test_arl.jsonl`)
optional simulation-side ARL bridge output (`pytest_simulation_arl.jsonl`)
---
Current repository structure (high level)
The current repository root includes folders such as `.github/workflows`, `archive`, `benchmarks`, `docs`, `mediation_core`, `scripts`, and `tests`, along with primary entrypoints such as `README.md`, `README.ja.md`, `agents.yaml`, `mediation_emergency_contract_sim_v5_1_2.py`, `mediation_emergency_contract_sim_v4_8.py`, and `ai_doc_orchestrator_with_mediator_v1_0.py`.
Representative files currently visible at the repository root include:
`README.md`
`README.ja.md`
`agents.yaml`
`agents.yaml.md`
`ai_alliance_persuasion_simulator.py`
`ai_doc_orchestrator_kage3_v1_2_2.py`
`ai_doc_orchestrator_kage3_v1_2_2_1.py`
`ai_doc_orchestrator_kage3_v1_2_3.py`
`ai_doc_orchestrator_kage3_v1_2_4.py`
`ai_doc_orchestrator_kage3_v1_3_5.py`
`ai_doc_orchestrator_with_mediator_v1_0.py`
`ai_governance_mediation_sim.py`
`ai_mediation_all_in_one.py`
`kage_orchestrator_diverse_v1.py`
`log_codebook_v5_1_demo_1.json`
`mediation_emergency_contract_sim_v4_8.py`
`mediation_emergency_contract_sim_v5_1_2.py`
`pytest.ini`
---
Notes for replacing the pasted markdown
The pasted markdown mixed multiple branches and older README directions. If you replace it, also remove:
merge conflict markers such as `=======`
stray branch labels like `main`, `japan1988-patch-43`, `japan1988-patch-51`
outdated file references such as `ai_alliance_persuasion_sim.py`
older narrative that centers the repository on emotion-cycle explanations instead of the current fail-closed / HITL / audit-ready positioning
---
License
See `LICENSE`.
