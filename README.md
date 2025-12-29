### Positioning (safety-first)
Maestro Orchestrator prioritizes **preventing unsafe or undefined execution** over maximizing autonomous task completion.
When risk or ambiguity is detected, it **fails closed** and escalates to `PAUSE_FOR_HITL` or `STOPPED`, with audit logs explaining **why**.

**Trade-off:** This design may *over-stop by default*; safety and traceability are prioritized over throughput.

## 🚫 Non-goals (IMPORTANT)

This repository is a **research prototype**. The following are explicitly **out of scope**:

- **Production-grade autonomous decision-making** (no unattended real-world authority)
- **Persuasion / reeducation optimization for real users** (safety-evaluation only; must be opt-in and disabled by default)
- **Handling real personal data (PII)** or confidential business data in prompts, test vectors, or logs
- **Compliance/legal advice** or deployment guidance for regulated environments (medical/legal/finance)

## 🔁 REROUTE safety policy (fail-closed)

REROUTE is **allowed only when all conditions are met**. Otherwise, the system must fall back to `PAUSE_FOR_HITL` or `STOPPED`.

| Risk / Condition | REROUTE | Default action |
|---|---:|---|
| Undefined spec / ambiguous intent | ❌ | `PAUSE_FOR_HITL` |
| Any policy-sensitive category (PII, secrets, high-stakes domains) | ❌ | `STOPPED` or `PAUSE_FOR_HITL` |
| Candidate route has **higher** tool/data privileges than original | ❌ | `STOPPED` |
| Candidate route cannot enforce **same-or-stronger** constraints | ❌ | `STOPPED` |
| Safe class task + same-or-lower privileges + same-or-stronger constraints | ✅ | `REROUTE` |
| REROUTE count exceeds limit | ❌ | `PAUSE_FOR_HITL` or `STOPPED` |

**Hard limits (recommended defaults):**
- `max_reroute = 1` (exceed → `PAUSE_FOR_HITL` or `STOPPED`)
- REROUTE must be logged with `reason_code` and the selected route identifier.

## 🧭 Diagrams

### 1) System overview
<p align="center">
  <img src="docs/multi_agent_architecture_overview.webp" width="720" alt="System Overview">
</p>

### 2) Orchestrator one-page design map
**Decision flow map (implementation-aligned):**
`mediator_advice → Meaning → Consistency → RFL → Ethics → ACC → DISPATCH`
Designed to be **fail-closed**: if risk/ambiguity is detected, it falls back to `PAUSE_FOR_HITL` or `STOPPED` and logs **why**.

<p align="center">
  <img src="docs/orchestrator_onepage_design_map.png" width="920" alt="Orchestrator one-page design map">
</p>

If the image is not visible (or too small), open it directly:
- `docs/orchestrator_onepage_design_map.png`

### 3) Context flow

This project produces **audit logs** for reproducibility and accountability.

**Retention (SHOULD):**
- Define a retention window (e.g., 7/30/90 days) and delete logs automatically.

## ⚙️ Execution Examples
```

---

### 追加で直すべき箇所（あなたの断片の続き側）

このブロックの直後に、あなたの README にはたぶん「実行コマンド」「Tests」「CI」「License」が続くはずです。
そこも崩れているなら、次の “正規化済み” を続けて貼ると完成します（任意）。

````md
```bash
python ai_mediation_all_in_one.py
python kage_orchestrator_diverse_v1.py
python ai_doc_orchestrator_kage3_v1_2_2.py
python ai_governance_mediation_sim.py
````

## 🧪 Tests

Reproducible E2E confidential-flow loop guard:

* `kage_end_to_end_confidential_loopguard_v1_0.py`

Test:

* `test_end_to_end_confidential_loopguard_v1_0.py` (CI green on Python 3.9–3.11)

```bash
pytest -q
pytest -q tests/test_definition_hitl_gate_v1.py
pytest -q tests/test_kage_orchestrator_diverse_v1.py
pytest -q test_ai_doc_orchestrator_kage3_v1_2_2.py
pytest -q test_end_to_end_confidential_loopguard_v1_0.py
```

CI runs lint/pytest via `.github/workflows/python-app.yml`.

## 📌 License

See LICENSE.
Repository license: Apache-2.0 (policy intent: Educational / Research).


