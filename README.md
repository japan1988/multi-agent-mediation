### V4 → V5 (conceptual)

v4 focuses on a stable “emergency contract” governance bench with smoke tests and stress runners.
v5 extends that bench toward artifact-level reproducibility and contract-style compatibility checks.

Added / strengthened in v5:

* **Log codebook (demo) + contract tests**
  Enforces emitted vocabularies (`layer/decision/final_decider/reason_code`) via pytest

* **Reproducibility surface (pin what matters)**
  Pin simulator version, test version, and codebook version

* **Tighter invariant enforcement**
  Explicit tests/contracts around invariants reduce silent drift

What did NOT change (still true in v5):

* Research / educational intent
* Fail-closed + HITL semantics
* Use synthetic data only and run in isolated environments
* No security guarantees (codebook is not encryption; tests do not guarantee safety in real-world deployments)

---

## Project intent / non-goals

### Intent

* Reproducible safety and governance simulations
* Explicit HITL semantics (pause/reset/ban)
* Audit-ready decision traces (minimal ARL)

### Non-goals

* Production-grade autonomous deployment
* Unbounded self-directed agent control
* Safety claims beyond what is explicitly tested

---

## Data & safety notes

* Use synthetic/dummy data only
* Prefer not to commit runtime logs; keep evidence artifacts minimal and reproducible
* Treat generated bundles (zip) as reviewable evidence, not canonical source

---

## License

Apache License 2.0 (see `LICENSE`)