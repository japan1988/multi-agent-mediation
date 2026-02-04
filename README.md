## Architecture (Code-aligned diagrams)

The following diagrams are **fully aligned with the current code and terminology**.
They intentionally separate **state transitions** from **gate order** to preserve
auditability and avoid ambiguity.

> These diagrams are documentation-only and introduce **no logic changes**.

---

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing **where execution pauses (HITL)** or
**stops permanently (SEALED)**.

![State Machine](docs/構成図2026年2月4日_17_15_08.png)

**Notes**

- Primary execution path:  
  `INIT → PAUSE_FOR_HITL_AUTH → AUTH_VERIFIED → DRAFT_READY → PAUSE_FOR_HITL_FINALIZE → CONTRACT_EFFECTIVE`
- `PAUSE_FOR_HITL_*` represents an explicit **Human-in-the-Loop decision point**
  (user or admin approval).
- `STOPPED (SEALED)` is reached on:
  - invalid or fabricated evidence,
  - authorization expiry,
  - draft lint failure.
- SEALED stops are **fail-closed and non-overrideable** by design.

---

### 2) Gate Pipeline (code-aligned)

Ordered evaluation gates, **independent from lifecycle states**.

![Gate Pipeline](docs/構成図2026年2月4日_17_15_08.png)

**Notes**

- This diagram represents **gate order**, not state transitions.
- Gates are evaluated sequentially:
  - baseline (Meaning / Consistency / RFL)
  - evidence gate
  - ethics gate
  - authorization (ACC)
  - trust gate
  - draft lint gate
- `PAUSE` indicates **HITL required**.
- `STOPPED (SEALED)` indicates a **non-recoverable safety stop**.

---

### Why two diagrams?

- **State Machine** answers: *“Where does the system pause or stop?”*
- **Gate Pipeline** answers: *“In what order are safety and governance checks applied?”*

Keeping them separate mirrors the code structure and improves traceability
for audits and reviews.

---


