# 📘 Maestro Orchestrator — オーケストレーション・フレームワーク（fail-closed + HITL）
> English version: [README.md](README.md)

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

## 概要（Overview）

Maestro Orchestrator は **研究 / 教育用途** のオーケストレーション・フレームワークです。主に次を優先します。

- **Fail-closed**  
  不確実・不安定・リスクがある場合 → 黙って続行しない。
- **HITL（Human-in-the-Loop）**  
  人間の判断が必要な箇所は明示的にエスカレーションする。
- **トレーサビリティ（Traceability）**  
  最小ARLログにより、意思決定フローを監査可能・再現可能にする。

このリポジトリには、**実装参照（doc orchestrators）** と、交渉・仲裁・ガバナンス系ワークフロー・ゲート挙動の **シミュレーションベンチ** が含まれます。

---

## アーキテクチャ（高レベル）

監査可能で fail-closed な制御フロー：

agents  
→ mediator（risk / pattern / fact）  
→ evidence verification  
→ HITL（pause / reset / ban）  
→ audit logs（ARL）

![Architecture](docs/architecture_unknown_progress.png)

> 画像が表示されない場合は、以下を確認してください：  
> `docs/architecture_unknown_progress.png` が同一ブランチ上に存在し、ファイル名が完全一致（大文字小文字含む）していること。

---

## アーキテクチャ（コード整合ダイアグラム）

以下の図は、**現行コードと用語に完全に整合**しています。  
監査性と曖昧性回避のため、**状態遷移（state transitions）** と **ゲート順序（gate order）** を意図的に分離しています。

この図は **ドキュメント用途のみ** であり、**ロジック変更は一切ありません。**

---

### 1) ステートマシン（code-aligned）

実行が **停止（SEALED）** または **一時停止（HITL）** するポイントを示す最小ライフサイクル遷移。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="State Machine (code-aligned)" width="720">
</p>

**Notes**

**Primary execution path**

INIT  
→ PAUSE_FOR_HITL_AUTH  
→ AUTH_VERIFIED  
→ DRAFT_READY  
→ PAUSE_FOR_HITL_FINALIZE  
→ CONTRACT_EFFECTIVE

- `PAUSE_FOR_HITL_*` は明示的な **HITL（人間判断待ち）** を表します（ユーザー承認／管理者承認）。
- `STOPPED (SEALED)` 到達条件：
  - invalid / fabricated evidence
  - authorization expiry
  - draft lint failure
- **SEALED 停止は fail-closed であり、設計上 non-overrideable です。**

---

### 2) ゲートパイプライン（code-aligned）

ライフサイクル遷移とは独立した、ゲート評価順序。

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)" width="720">
</p>

**Notes**

- この図は **状態遷移ではなくゲート順序** を示します。
- `PAUSE` は **HITLが必要**（人間判断待ち）を示します。
- `STOPPED (SEALED)` は **非回復の安全停止** を示します。

**Design intent**

- **State Machine** が答えるもの：  
  *「どこで止まる／どこで一時停止するか？」*
- **Gate Pipeline** が答えるもの：  
  *「どの順序で判断するか？」*

分離することで曖昧性を避け、監査可能性を保ちます。

**Maintenance note**

画像が表示されない場合：
- `docs/` 配下に存在すること
- ファイル名が完全一致（大文字小文字含む）していること
- リンク更新時はファイル一覧からコピペ推奨

---

## What’s new (2026-01-21)

- **New**: `ai_mediation_hitl_reset_full_with_unknown_progress.py`  
  Simulator for **unknown progress** scenarios with HITL/RESET semantics.
- **New**: `ai_mediation_hitl_reset_full_kage_arl公開用_rfl_relcodes_branches.py`  
  v1.7-IEP aligned simulator for **RFL relcode branching**  
  (RFL is non-sealing → escalates to HITL).
- **Updated**: `ai_doc_orchestrator_kage3_v1_2_4.py`  
  Doc orchestrator reference updated with **post-HITL semantics**.

---

## What’s new (2026-02-03)

Introduced an **event-driven governance-style workflow**
(fail-closed + HITL + audit-ready).

- **New**: `mediation_emergency_contract_sim_v1.py`  
  Minimal emergency workflow simulator:

  USER auth → AI draft → ADMIN finalize → contract effective

  Invalid or expired events fail-closed and stop execution,
  producing a minimal ARL (JSONL).

- **New**: `mediation_emergency_contract_sim_v4.py`  
  Extended v1 with:
  - evidence gate
  - draft lint gate
  - trust / grant–based HITL friction reduction

---

## What’s new (2026-02-05)

- **New**: `mediation_emergency_contract_sim_v4_1.py`  
  v4.1 is a **behavior-tightening** update over v4.0 to make the bench expectations explicit and code-aligned:

  - **RFL is non-sealing by design**  
    Boundary-unstable proposals trigger `PAUSE_FOR_HITL` with `sealed=false` and `overrideable=true` (human decides).

  - **Fabrication is detected early, but sealing occurs only in ethics**  
    Evidence fabrication is flagged in the evidence gate, and the **only sealing stop** is issued by `ethics_gate`
    (`STOPPED` with `sealed=true`).

  - **Trust/grant friction reduction remains supported**  
    Trust/grant-based AUTH auto-skip behavior is preserved (when thresholds are satisfied), while still logging reasons to ARL.

  **Quick run**
  ```bash
  python mediation_emergency_contract_sim_v4_1.py
Expected

rust
コードをコピーする
NORMAL -> CONTRACT_EFFECTIVE

FABRICATE -> STOPPED (sealed=true in ethics_gate)

RFL_STOP -> STOPPED (sealed=false via HITL stop)
v4.1 regression test

This repo includes a dedicated pytest file that pins v4.1 behavior as a contract:

NORMAL -> CONTRACT_EFFECTIVE (not sealed)

FABRICATE -> STOPPED (sealed=true in ethics_gate)

RFL_STOP -> STOPPED (sealed=false via HITL stop)

Invariant: SEALED is issued only by ethics_gate/acc_gate (RFL never seals).

Run only this test file:

bash
コードをコピーする
pytest -q tests/test_mediation_emergency_contract_sim_v4_1.py
What’s new (2026-02-07)
New: mediation_emergency_contract_sim_v4_4.py
Emergency contract workflow bench v4.4 (fail-closed + HITL + minimal ARL).

New: mediation_emergency_contract_sim_v4_4_stress.py
Stress runner for v4.4 (distribution + invariant checks).

New: stress_results_v4_4_1000.json
Stress summary (1,000 runs).

New: stress_results_v4_4_10000.json
Stress summary (10,000 runs).

Stress-pinned invariants

SEALED is issued only by ethics_gate / acc_gate (RFL never seals).

RFL is non-sealing by design (RFL → PAUSE_FOR_HITL, human decides).

What’s new (2026-02-08)
New: mediation_emergency_contract_sim_v4_6.py
Emergency contract workflow bench v4.6 (fail-closed + HITL + minimal ARL).

New: stress_results_v4_6_100000.json
Reproducible stress evidence for v4.6 (100,000 runs).

New: mediation_emergency_contract_sim_v4_7_full.py
v4.7 introduces coaching by the top (highest-score) agent to reduce low-trust “shortest-path” retries
and improve clean completion.

Why v4.7 (what was found in v4.6)
In v4.6 stress (100,000 runs), 2 runs STOPPED due to low trust where an agent attempted a low-trust
“shortest-path” retry.

v4.7 adds a guidance step (coaching) to improve the agent state before retrying, and is expected to reduce this failure mode.

v4.6 STOPPED (2 cases): reason_code=TRUST_SCORE_LOW @ model_trust_gate (fail-closed)

Guardrail note (design-time prevention)
The guardrails were already present at design time, so these unsafe conditions were stopped early (fail-closed)
instead of silently continuing and becoming incidents.

v4.6 stress snapshot (100,000 runs)
CONTRACT_EFFECTIVE: 73,307

STOPPED: 18,385

INIT: 8,308

v4.7 (regex fix + re-run)
1) Critical fix: word-boundary regex was not functioning in draft_lint_gate
In the current upload, draft_lint_gate regex patterns used raw strings with \\b (double backslash),
so \b did not work as a “word boundary”, and the Safety patterns were effectively dead.

Fix: \\b → \b (7 occurrences) so word-boundary matching works as intended.

Goal: restore intended detection behavior for Safety patterns that assume word boundaries,
ensuring they correctly trigger fail-closed stops.

2) Focused stress after the fix (100,000 runs / seed=42)
Added stress_report_v4_7_draft_lint_100k_seed42.json

Verified that Safety stop rate aligns with the intended behavior (≈ “draft reach × weight”) after the word-boundary fix.

Reproducibility

This is a focused micro-bench for draft_lint_gate (generate → mutate → lint), with fixed weights:
ok=0.86, out_of_scope=0.04, legal_binding=0.05, discrimination=0.05.

Observed (100,000 runs / seed=42)

Category	Expected weight	Observed rate	Observed count
DRAFT_LINT_OK	0.86	0.86022	86,022
DRAFT_OUT_OF_SCOPE	0.04	0.03902	3,902
SAFETY_LEGAL_BINDING_CLAIM	0.05	0.05000	5,000
SAFETY_DISCRIMINATION_TERM	0.05	0.05076	5,076
SAFETY_STOP_RATE (total)	0.10	0.10076	10,076
TOTAL_FAIL_RATE	0.14	0.13978	13,978

Note: This result validates the intended behavior of draft_lint_gate after the regex word-boundary fix.
This micro-bench is scoped to draft_lint_gate only and is not a general safety claim.

V1 → V4: What actually changed
mediation_emergency_contract_sim_v1.py demonstrates the minimum viable pipeline:
a linear, event-driven workflow with fail-closed stops and minimal audit logs.

mediation_emergency_contract_sim_v4.py turns that pipeline into a
repeatable governance bench by adding early rejection and controlled automation.

Added in v4

Evidence gate
Basic verification of evidence bundles. Invalid, irrelevant, or fabricated evidence triggers fail-closed stops.

Draft lint gate
Enforces draft-only semantics and scope boundaries before admin finalization. Hardened against markdown/emphasis noise
to reduce false positives.

Trust system (score + streak + cooldown)
Trust increases on successful HITL outcomes and decreases on failures. Cooldown prevents unsafe automation after errors.
All trust transitions are logged in ARL.

AUTH HITL auto-skip (safe friction reduction)
When trust threshold + approval streak + valid grant are satisfied,
AUTH HITL can be skipped for the same scenario/location only,
while recording the reason in ARL.

実行例（Execution Examples）
まずは1本動かして挙動とログを確認し、その後に広げてください。

NOTE: このリポジトリは research / educational です。
合成データ（ダミー）を使用し、実行時ログをコミットしないでください。

Recommended
Doc orchestrator（参照実装）

bash
コードをコピーする
python ai_doc_orchestrator_kage3_v1_2_4.py
Emergency contract workflow（v4）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4.py
Emergency contract workflow（v4.1）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4_1.py
Emergency contract workflow（v4.4）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4_4.py
Emergency contract stress（v4.4）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4_4_stress.py --runs 10000 --out stress_results_v4_4_10000.json
Emergency contract workflow（v4.6）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4_6.py
Emergency contract workflow（v4.7）

bash
コードをコピーする
python mediation_emergency_contract_sim_v4_7_full.py
Project intent / non-goals
Intent
Reproducible safety and governance simulations

Explicit HITL semantics

Audit-ready decision traces

Non-goals
Production-grade autonomous deployment

Unbounded self-directed agent control

Safety claims beyond what is explicitly tested

License
Apache License 2.0（LICENSE を参照）
