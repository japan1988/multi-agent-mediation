# 📘 Maestro Orchestrator — Multi-Agent Orchestration Framework

> Japanese: [README.ja.md](README.ja.md)

<p align="center">
  <a href="https://github.com/japan1988/multi-agent-mediation/stargazers">
    <img src="https://img.shields.io/github/stars/japan1988/multi-agent-mediation?style=social" alt="GitHub Stars">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/issues">
    <img src="https://img.shields.io/github/issues/japan1988/multi-agent-mediation?style=flat-square" alt="Open Issues">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-brightgreen?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/python-app.yml/badge.svg?branch=main" alt="Python App CI">
  </a>
  <a href="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml">
    <img src="https://github.com/japan1988/multi-agent-mediation/actions/workflows/tasukeru-analysis.yml/badge.svg?branch=main" alt="Tasukeru Advisory">
  </a>
  <br/>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/lint-Ruff-000000.svg?style=flat-square" alt="Ruff">
  <a href="https://github.com/japan1988/multi-agent-mediation/commits/main">
    <img src="https://img.shields.io/github/last-commit/japan1988/multi-agent-mediation?style=flat-square" alt="Last Commit">
  </a>
</p>

---

Maestro Orchestrator is a research-oriented orchestration framework for
multi-agent governance, fail-closed control, HITL escalation, checkpoint-based
resume, and tamper-evident simulation workflows.

This repository contains multiple simulator lines. Some files focus on
KAGE-like gate behavior and mediator separation, while others focus on
document-task batch execution, checkpointing, audit integrity, and artifact
verification.

---

## Safety and scope

This repository is a **research prototype**.

It is not intended for:

- production autonomous decision-making
- unsupervised real-world control
- legal, medical, financial, or regulatory advice
- processing real personal data or confidential operational data
- demonstrating complete or universal safety coverage
- automatic external submission, upload, sending, or deployment
- bypassing HITL review for external side effects

The examples should be read as:

- research simulations
- educational references
- governance / safety test benches
- fail-closed and HITL design examples
- audit-log and checkpoint integrity experiments
- batch-orchestration examples for local simulation

External submit / upload / push / send actions should remain HITL-gated.

---

## Repository purpose

The main purpose of this repository is to explore how agentic workflows can be
controlled through explicit gates, reproducible logs, interruption points, and
human review.

The project emphasizes:

- fail-closed behavior
- HITL escalation
- gate-order invariants
- reason-code stability
- checkpoint / resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- clear separation between advice and execution

This repository does not claim to provide complete AI safety coverage. It is a
research and educational test bench for studying orchestration behavior.

---

## Current simulator lines

### 1. Mediator-based gate simulator

Example:

```text
ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py

This simulator focuses on the following flow:

Agent → Mediator → Orchestrator

Core characteristics:

Agent normalizes task input.
Mediator gives advice only.
Mediator has no execution authority.
Orchestrator evaluates gates in a fixed order.
RFL is used for relative or ambiguous requests.
Ethics / ACC handle higher-risk blocking conditions.
sealed=True may appear only at Ethics / ACC.
raw text should not be persisted.
audit logs should avoid direct PII leakage.

Canonical gate order:

Meaning → Consistency → RFL → Ethics → ACC → Dispatch

This simulator is useful for checking:

gate invariants
HITL transitions
RFL pause behavior
sealed / non-sealed behavior
mediator-to-orchestrator separation
reason-code expectations
lightweight multi-task orchestration behavior
2. Production-oriented document orchestrator simulator

Example version:

v1.2.6-hash-chain-checkpoint

This simulator focuses on document-task orchestration with stronger persistence
and integrity controls.

Core characteristics:

Task Contract Gate
rough token estimation
Word / Excel / PPT task simulation
per-task checkpoint / resume
HMAC-SHA256 audit log hash chain
HMAC-protected checkpoint files
SHA-256 + HMAC artifact integrity records
PII-safe audit / checkpoint / artifact writes
tamper-evidence detection
CLI-based simulation entry point
no mediation / negotiation feature
no automatic external submission

Important implementation note:

The simulator writes text-backed artifact outputs representing document-task
results. It does not claim to generate fully formatted Microsoft Office
documents unless separate document-generation libraries are connected.

Hashing and HMAC provide tamper evidence. They do not provide physical write
prevention. In real deployment, HMAC keys must be supplied from an environment
variable or protected key file and must not be committed to the repository.

Batch execution and resume

This repository also includes batch-style orchestration examples.

Batch execution means that multiple document-related tasks can be evaluated as
a single orchestration run while preserving gate decisions, audit records, and
interruption points.

Mediator-based batch flow

The mediator-based simulator can accept multiple tasks in one run.

Example use cases:

evaluate several spreadsheet / slide tasks together
compare task-level gate outcomes
check HITL behavior across multiple tasks
verify mediator advice before orchestration
confirm that each task still passes through the fixed gate order

This line is useful when the focus is on:

multi-task gate behavior
mediator separation
RFL / HITL transitions
reason-code stability
lightweight orchestration tests

Example task sequence:

T1: xlsx task
T2: pptx task
T3: ambiguous task requiring RFL / HITL

Expected behavior:

each task is normalized by the Agent
each task receives Mediator advice
each task is evaluated by the Orchestrator
paused tasks remain non-sealed unless Ethics / ACC performs a sealed stop
dispatch only occurs when the final decision is RUN
Document-task batch flow

The production-oriented document orchestrator simulator uses a fixed
document-task sequence:

Word → Excel → PPT

This line is useful when the focus is on:

batch task execution
per-task checkpointing
interruption and resume
artifact integrity records
HMAC-protected checkpoints
HMAC-SHA256 audit log hash chains
tamper-evidence detection

If a task is interrupted, the simulator records:

failed task ID
failed layer
reason code
checkpoint path
resume requirement
HITL confirmation requirement when applicable

A later run can resume from the checkpoint after HITL confirmation when
required.

Batch scripts

Batch scripts may be used as convenience wrappers for local simulation runs.

Recommended script examples:

scripts/run_doc_orchestrator_demo.bat
scripts/run_doc_orchestrator_resume.bat
scripts/run_doc_orchestrator_tamper_check.bat

These scripts should be treated as local developer utilities only.

They should not:

embed production HMAC keys
upload or submit artifacts automatically
bypass HITL confirmation
delete files automatically
process real personal or confidential data
change license or safety semantics
weaken tests or gate invariants

For local demonstrations, a demo key mode may be used only when the simulator
explicitly supports it. Production-like runs should use an environment variable
or a protected key file for HMAC keys.

Example batch-script roles
run_doc_orchestrator_demo.bat

Purpose:

run a local demonstration
use safe sample input
write audit logs and simulated artifacts to local output directories
avoid external submission

Typical use:

Local demo run with demo key mode.
run_doc_orchestrator_resume.bat

Purpose:

resume from a checkpoint
require explicit resume confirmation
verify completed artifacts before continuing
preserve checkpoint integrity

Typical use:

Resume interrupted Word / Excel / PPT simulation after HITL confirmation.
run_doc_orchestrator_tamper_check.bat

Purpose:

verify audit-log / checkpoint / artifact integrity behavior
demonstrate tamper-evidence detection
pause for HITL if integrity verification fails

Typical use:

Local tamper-evidence simulation.
Recommended reading order

For gate behavior and KAGE-like invariants:

ai_doc_orchestrator_with_mediator_v1_0.py
tests/test_doc_orchestrator_with_mediator_v1_0.py

For checkpoint, resume, artifact integrity, and HMAC-chain behavior:

Production-oriented Doc Orchestrator Simulator
v1.2.6-hash-chain-checkpoint

For behavior verification, always read the implementation together with the
corresponding tests.

This is especially important for:

gate invariants
reason-code expectations
HITL transitions
sealed / non-sealed behavior
checkpoint / resume behavior
tamper-evidence behavior
reproducibility checks
benchmark expectations
batch execution behavior
Testing and behavior

In this repository, tests often define the expected behavior of the simulators
and orchestration logic.

When checking behavior, it is usually better to read the implementation
together with the corresponding tests.

Tests may verify:

fixed gate order
fail-closed behavior
HITL escalation
RFL non-sealing behavior
Ethics / ACC sealing constraints
checkpoint recovery
audit-log integrity
artifact hash verification
reason-code stability
reproducibility expectations
batch-task behavior
CLI behavior

A newer version number does not always mean that the file is the primary
recommended entry point. Some files are preserved for historical comparison,
reproducibility, or versioned experiments.

Gate and decision model

The repository uses explicit gate decisions to make orchestration behavior
traceable.

Common decisions include:

RUN
PAUSE_FOR_HITL
STOPPED

General interpretation:

RUN: the simulator may continue to the next gate or dispatch step
PAUSE_FOR_HITL: the simulator should pause and wait for human review
STOPPED: the simulator has reached a blocking condition

In KAGE-like simulator lines, RFL should pause for HITL rather than seal.
Sealing behavior should remain limited to higher-risk layers such as Ethics or
ACC, depending on the simulator contract.

Audit and integrity model

Audit and integrity behavior differs by simulator line.

The mediator-based simulator focuses on lightweight audit events and safe
context logging.

The production-oriented document simulator adds stronger integrity controls:

audit log hash chain
row-level HMAC
checkpoint HMAC
artifact SHA-256
artifact HMAC
completed-artifact verification on resume
tamper-evidence detection

These mechanisms are intended to make changes detectable. They do not prevent
a local actor from modifying files on disk.

Checkpoint and resume model

Checkpoint-based simulators are designed to support interrupted execution.

A checkpoint may record:

run ID
current task ID
failed task ID
failed layer
reason code
task status
artifact path
artifact hash
whether resume is allowed
whether HITL is required before resume

When resuming, completed artifacts should be verified before the simulator
continues. If verification fails, the run should pause for HITL rather than
continue silently.

Artifact model

Artifact outputs in the simulator should be treated as research artifacts.

Depending on the simulator line, outputs may include:

artifact previews
text-backed document-task outputs
audit JSONL files
checkpoint JSON files
integrity metadata
summary records

The repository should not describe these simulated outputs as complete
production Office documents unless actual document-generation code is added and
tested.

External side effects

External side effects include actions such as:

sending email
uploading files
submitting artifacts
pushing changes
deleting files
calling external APIs
changing license semantics

These actions should remain blocked, prohibited, or HITL-gated depending on the
simulator contract.

No script or simulator should silently perform external submission.

Archive and historical files

Some files are preserved for:

historical comparison
reproducibility
versioned experiments
regression testing
design comparison

Files under archive/ should generally be treated as historical or reference
material unless explicitly referenced by current tests or documentation.

Language
English README: README.md
Japanese README: README.ja.md
License

This repository uses a split-license model:

Software code: Apache License 2.0
Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

See LICENSE_POLICY.md
 for details.

Disclaimer

This repository is provided for research and educational purposes only.

It is not a production safety system, not a compliance certification, and not a
guarantee of safe autonomous behavior. Users are responsible for reviewing,
testing, and adapting the code before any real-world use.

Do not use this repository to process real personal data, confidential
operational data, or high-stakes decision workflows without independent review
and appropriate safeguards.
