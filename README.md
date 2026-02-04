## Architecture (Code-aligned diagrams)

The following diagrams are fully aligned with the current code and terminology.  
They intentionally separate **state transitions** from **gate evaluation order** to preserve
auditability and avoid ambiguity.

These diagrams are **documentation-only** and introduce **no logic changes**.

---

### 1) State Machine (code-aligned)

Minimal lifecycle transitions showing **where execution pauses (HITL)** or
**stops permanently (SEALED)**.

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="State Machine (code-aligned)"
       width="720">
</p>

#### Notes

**Primary execution path**

INIT
→ PAUSE_FOR_HITL_AUTH
→ AUTH_VERIFIED
→ DRAFT_READY
→ PAUSE_FOR_HITL_FINALIZE
→ CONTRACT_EFFECTIVE

markdown
コードをコピーする

- `PAUSE_FOR_HITL_*` represents an explicit **Human-in-the-Loop** decision point  
  (user approval or admin approval).
- `STOPPED (SEALED)` is reached on:
  - invalid or fabricated evidence
  - authorization expiry
  - draft lint failure
- **SEALED stops are fail-closed and non-overrideable by design.**

---

### 2) Gate Pipeline (code-aligned)

Ordered **evaluation gates**, independent from lifecycle state transitions.

<p align="center">
  <img src="docs/architecture_code_aligned.png"
       alt="Gate Pipeline (code-aligned)"
       width="720">
</p>

#### Notes

- This diagram represents **gate order**, not state transitions.
- `PAUSE` indicates **HITL required** (human decision pending).
- `STOPPED (SEALED)` indicates a **non-recoverable safety stop**.

---

## Design intent

- **State Machine** answers:  
  *“Where does execution pause or terminate?”*
- **Gate Pipeline** answers:  
  *“In what order are decisions evaluated?”*

Keeping them separate avoids ambiguity and preserves **audit-ready traceability**.

---

## V1 vs V4: What actually changed (and what did not)

This section explains the **real difference** between V1 and V4, using the diagrams above.

### What did NOT change (important)

- The **core lifecycle states** remain the same:
  - INIT → AUTH → DRAFT → FINALIZE → EFFECTIVE
- The system is **fail-closed by default**.
- `STOPPED (SEALED)` is still:
  - terminal
  - non-overrideable
  - audit-logged

The diagrams therefore remain **structurally valid for both V1 and V4**.

---

### What V1 provided

V1 demonstrated a **minimal, event-driven workflow**:

- USER AUTH (HITL)
- AI draft generation
- ADMIN finalization (HITL)
- Contract becomes effective

Characteristics:

- Minimal gating
- No trust memory
- No evidence validation beyond baseline checks
- Every AUTH required HITL
- Suitable as a **baseline safety proof**

---

### What V4 adds (without breaking V1 semantics)

V4 extends the same structure into a **governance-grade bench**:

#### 1. Evidence gate
- Introduces explicit validation of evidence bundles
- Detects invalid / irrelevant / fabricated evidence
- Fails closed **before** drafting or finalization

#### 2. Draft lint gate
- Enforces “draft-only / non-authoritative” constraints
- Guards scope boundaries before admin finalization
- Hardened against formatting noise

#### 3. Trust & grant system
- Tracks trust score, approval streaks, and cooldowns
- Trust state is **logged in ARL**
- Negative outcomes reduce trust

#### 4. AUTH HITL auto-skip (safe friction reduction)
- When trust ≥ threshold **and** a valid grant exists,
  USER AUTH HITL can be skipped
- This is:
  - scoped
  - reversible
  - fully audit-logged
- Gate order remains unchanged

---

### Why this matters

- **V1** proves *correctness and safety*
- **V4** proves *operability without losing safety*

In other words:

> V1 answers “Can this be done safely?”  
> V4 answers “Can this be done repeatedly in the real world?”

---

## Maintenance note

If an image does not render:

1. Confirm the file exists under `docs/`
2. Confirm the filename matches exactly (case-sensitive)
3. Prefer copy-paste from the file list when updating links
4. If needed, verify via:
https://raw.githubusercontent.com/japan1988/multi-agent-mediation/main/docs/architecture_code_aligned.png

yaml
コードをコピーする
