Architecture (Code-aligned diagrams)

The following diagrams are fully aligned with the current code and terminology.
They intentionally separate state transitions from gate order to preserve auditability and avoid ambiguity.

These diagrams are documentation-only and introduce no logic changes.

1) State Machine (code-aligned)

Minimal lifecycle transitions showing where execution pauses (HITL) or stops permanently (SEALED).

<p align="center"> <img src="docs/構成図2026年2月4日_17_15_08.png" alt="State Machine (code-aligned)" width="720"> </p>

Notes

Primary execution path
INIT → PAUSE_FOR_HITL_AUTH → AUTH_VERIFIED → DRAFT_READY → PAUSE_FOR_HITL_FINALIZE → CONTRACT_EFFECTIVE

PAUSE_FOR_HITL_* represents an explicit Human-in-the-Loop decision point
(user approval or admin approval).

STOPPED (SEALED) is reached on:

invalid or fabricated evidence,

authorization expiry,

draft lint failure.

SEALED stops are fail-closed and non-overrideable by design.

2) Gate Pipeline (code-aligned)

Ordered evaluation gates, independent from lifecycle state transitions.

<p align="center"> <img src="docs/構成図2026年2月4日_17_15_08.png" alt="Gate Pipeline (code-aligned)" width="720"> </p>

Notes

This diagram represents gate order, not state transitions.

PAUSE indicates HITL required (human decision pending).

STOPPED (SEALED) indicates a non-recoverable safety stop.

Design intent

State Machine answers: “Where does execution pause or terminate?”

Gate Pipeline answers: “In what order are decisions evaluated?”

Keeping them separate avoids ambiguity and preserves audit-ready traceability.

Maintenance note

If an image does not render:

Confirm the file exists under docs/

Confirm the filename matches exactly (case-sensitive, Japanese characters included)

Prefer copy-paste from the file list when updating links
