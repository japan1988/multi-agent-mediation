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

Maestro Orchestrator is a research-oriented framework for studying how multi-agent and agentic workflows can be controlled with explicit safety checks, audit logs, checkpoints, and human review.

This repository focuses on local simulations and defensive review workflows. It is designed to help test questions such as:

- when an agent workflow should continue
- when it should stop safely
- when it should ask for human review
- whether logs and generated outputs remain consistent
- whether advisory findings stay separate from automatic execution
- whether checkpoints and audit records can detect unexpected changes

This project is not a production automation system.  
It does not provide legal, medical, financial, regulatory, or safety guarantees.

The main design principle is simple:

> If behavior is uncertain, risky, inconsistent, or externally impactful, the workflow should stop or ask for human review instead of continuing automatically.

## Beginner reading guide

If you are new to this repository, start here:

1. Read **Safety and scope**.
2. Read **Responsible use and prohibited use**.
3. Read **Advisory-only policy**.
4. Read **Human review model**.
5. Read **Current simulator lines** only after you understand the safety boundaries.

This repository is a research and educational test bench.  
The outputs are research artifacts, not production approvals or safety guarantees.

When behavior is unclear, read the relevant implementation together with its tests before applying any change.

## Safety and scope

This repository is a research prototype.

It is not intended for:

- production autonomous decision-making
- unsupervised real-world control
- legal, medical, financial, or regulatory advice
- processing real personal data or confidential operational data
- demonstrating complete or universal safety coverage
- automatic external submission, upload, sending, or deployment
- bypassing human review for external side effects

The examples should be read as:

- local research simulations
- educational references
- governance and safety test benches
- fail-closed design examples
- human-review workflow examples
- audit-log and checkpoint integrity experiments
- local batch-orchestration examples

External submit, upload, push, send, deploy, delete, or real-world control actions should remain blocked or human-review gated.

## Responsible use and prohibited use

The review workflow and simulator examples are intended for defensive review of repositories owned by the user or repositories for which the user has explicit authorization.

Do not use this repository or its tools for:

- unauthorized vulnerability discovery
- offensive reconnaissance
- exploitation of third-party systems or code
- credential, token, or secret harvesting
- scanning repositories or systems without permission
- generating or validating exploit steps against real targets
- bypassing access controls, rate limits, or security boundaries
- publishing sensitive findings without responsible disclosure

Findings should be used to improve safety, reliability, traceability, and governance. When reviewing third-party or open-source code, follow the project maintainers' security policy and responsible disclosure process.

## Advisory review workflow

Tasukeru Analysis is the repository's advisory review workflow for defensive repository review.

It is intended to help inspect and govern the increasing complexity of multi-agent and agentic workflows. As these workflows grow, their behavior can become harder to inspect, explain, and audit.

It focuses on review-support questions such as:

- whether findings are classified at an appropriate review level
- whether process logs and generated outputs remain consistent
- whether uncertain or risky cases should be routed back to human review
- whether public PR comments avoid excessive security detail
- whether the workflow remains advisory-only without automatic fixes, commits, pushes, or merges

The workflow does not disclose detailed exploit procedures or act as an autonomous enforcement system. Detailed findings remain in workflow artifacts and logs for human review.

It runs static and repository-specific checks such as:

- Ruff
- Bandit
- pip-audit
- repository-specific logic checks
- documentation review
- human-review classification

The workflow is designed to improve maintainability, safety review, and developer usability without automatically treating every advisory finding as a blocking failure.

It does not aim to hide warnings. Instead, it separates active repair candidates, review-only findings, historical-version warnings, and likely noise so maintainers can focus on the right items first.

## Advisory-only policy

The advisory review workflow does not:

- create branches automatically
- create pull requests automatically
- commit changes automatically
- push changes automatically
- apply fixes automatically
- merge pull requests automatically

Only findings that require human review may produce a PR comment.

Other findings are collected in the GitHub Step Summary and workflow artifacts for human review.

The workflow is intended to reduce human review load, not to replace human decision-making.

## Human readability policy

This project prioritizes code that humans can safely read, review, and maintain.

A change should not be treated as a good fix merely because it is easier for AI or automated tools to process. If a change may reduce human readability, reviewability, or maintainability, it should be routed back for human review.

## Security review output policy

Security-related outputs should focus on defensive review and safe remediation guidance.

Public PR comments should not include:

- exploit payloads
- attack commands
- offensive reproduction steps
- step-by-step exploitation instructions
- third-party target exploitation details

Security-related findings should focus on:

- the affected file and line
- the defensive reason for review
- the expected safety impact
- a safe remediation direction
- whether human review is required

## Human review model

The repository uses review levels to separate actionable issues from expected noise.

Current review levels:

- `HITL_REQUIRED`: human review is required before merge or further action
- `FIX_RECOMMENDED`: a concrete fix is likely appropriate
- `REVIEW_RECOMMENDED`: review the context before deciding
- `NOISE_CANDIDATE`: likely acceptable in tests, demos, or research simulations
- `INFO_ONLY`: informational finding, including historical-version warnings

This classification is advisory by default. It helps maintainers decide whether to fix, document, suppress, or accept a finding.

## Active review queue

The main review queue is intended to stay compact.

Findings that require immediate attention should appear as:

- `HITL_REQUIRED`
- `FIX_RECOMMENDED`
- `REVIEW_RECOMMENDED`

When these counts are zero, the repository has no active advisory items that the workflow currently recommends prioritizing for human repair or review.

This does not mean the repository has no warnings. It means the remaining warnings are classified as either likely noise or historical/informational records.

## Historical-version warnings

Historical-version warnings are not fully excluded.

The advisory workflow keeps findings from superseded or historical simulator files visible as `INFO_ONLY` when they are useful for audit visibility but are not active repair targets.

This keeps the active review queue focused on findings that currently require human attention, while preserving visibility into older versioned files kept for:

- reproducibility
- regression comparison
- historical reference
- versioned experiments
- design comparison

Historical warnings should be revisited if the file becomes an active entry point again.

## Typical classification examples

Examples:

### Subprocess execution

Usually `HITL_REQUIRED`.

Requires review because subprocess execution can create external side effects.

### Subprocess import

Usually `REVIEW_RECOMMENDED`.

Importing subprocess is not itself an external side effect.

### Assert usage in tests

Usually `NOISE_CANDIDATE`.

Pytest tests commonly use `assert`.

### Assert usage in active runtime code

Usually `FIX_RECOMMENDED`.

Runtime assert statements can be removed under Python optimization flags.

### Assert usage in superseded historical simulator files

Usually `INFO_ONLY`.

Kept visible as a historical-version warning instead of being fully excluded. No immediate fix is required unless the file becomes an active entry point again.

### Temporary path usage in tests

Usually `NOISE_CANDIDATE` when using isolated pytest fixtures such as `tmp_path`.

Should be reviewed if it uses a hard-coded shared path.

### Pseudo-random generator usage in active simulations

Usually `REVIEW_RECOMMENDED`.

Deterministic simulation randomness may be acceptable when not used for secrets, tokens, authentication, authorization, or cryptography.

If accepted, the code should document that the randomness is simulation-only.

### Pseudo-random generator usage in superseded historical simulator files

Usually `INFO_ONLY`.

Kept visible as a historical-version warning. No immediate fix is required unless reused for security-sensitive behavior or active runtime behavior.

### Dependency vulnerabilities from dependency audit tools

Usually `FIX_RECOMMENDED`.

## Evidence, explanation, and prediction

The advisory workflow may attach structured decision-support metadata to findings.

This can include:

- `evidence`: source tool, rule ID, file, line, snippet, and artifact reference
- `explanation`: why the finding matters and why a remediation direction is suggested
- `fix_prediction`: expected safety or maintainability effect of the suggested change
- `fix_verification`: placeholder or result data for candidate verification

`fix_prediction` is not a guarantee. It is a review aid.

`fix_verification`, when enabled, must remain advisory-only. Candidate checks should use temporary or isolated files and must not modify repository files unless a human explicitly chooses to apply a change manually.

## Output artifacts

The advisory workflow may generate review artifacts such as:

- advisory summaries
- human-review reports
- machine-readable review data
- notification state records
- PR-comment drafts
- documentation proposal drafts
- confidence reports
- result consistency reports
- dependency consistency reports

These artifacts are review materials. They do not modify repository files and must not be applied automatically.

Human-readable review reports may include:

- file path
- line number
- finding code
- issue summary
- review level
- suggested action

Machine-readable reports provide the same decision-support data in structured form.

PR-comment drafts are used only when a finding requires human review and qualifies for PR notification.

Documentation proposal drafts may include proposed minimal diffs, full draft text, hashes, evidence, and review checklists. They do not modify repository files and must not be applied automatically.

Confidence scores are review-aid metadata only. They do not indicate that a finding is safe to ignore, and they must not enable automatic fixes, automatic PR creation, automatic commits, automatic pushes, or automatic merges.

Result consistency reports record whether process logs and generated result artifacts agree.

Dependency consistency reports record whether findings, affected structures, impact classifications, review levels, and generated outputs remain consistent.

All of these artifacts are advisory-only. They do not modify findings, change classifications, apply fixes, create commits, push changes, or merge pull requests automatically.

## Advisory behavior

The advisory workflow should help maintainers answer:

- Which findings are likely noise?
- Which findings should be reviewed?
- Which files need attention?
- Why is the finding relevant?
- What is the suggested fix?
- Does this require human review before merge?
- Is this an active repair candidate or a historical-version warning?

The workflow does not replace human review. It is a triage and documentation aid for safer repository maintenance.

## Repository purpose

The main purpose of this repository is to explore how agentic workflows can be controlled through explicit checks, reproducible logs, interruption points, and human review.

The project emphasizes:

- fail-closed behavior
- human review before risky actions
- fixed safety-check order
- stable reason codes
- checkpoint and resume behavior
- tamper-evident audit records
- artifact integrity verification
- reproducible simulation outputs
- clear separation between advice and execution

This repository does not claim to provide complete AI safety coverage. It is a research and educational test bench for studying orchestration behavior.

## Architecture diagrams

Detailed architecture diagrams for the production-oriented document orchestrator simulator are collected in the documentation directory.

The diagram documents may include:

- document orchestrator overview
- task processing flow
- audit hash chain
- checkpoint resume flow
- data structure map

The README keeps the overview concise. Detailed diagrams, reference files, bundles, and documentation assets should be placed in the documentation index.

## Current simulator lines

This repository contains several local-only simulator lines. Each line focuses on a different orchestration or review problem.

### 1. Gate-based mediator simulator

This simulator studies a simple flow:

```text
Agent → Mediator → Orchestrator
```

Core characteristics:

- the agent normalizes task input
- the mediator gives advice only
- the mediator has no execution authority
- the orchestrator evaluates checks in a fixed order
- ambiguous or relative requests are routed to human review
- higher-risk cases can be blocked
- raw text should not be persisted
- audit logs should avoid direct personal-data leakage

Canonical check order:

```text
Meaning → Consistency → Ambiguity Review → External-Action Safety → Dispatch
```

This simulator is useful for checking:

- fixed check order
- human-review transitions
- blocked versus non-blocked behavior
- mediator-to-orchestrator separation
- reason-code expectations
- lightweight multi-task orchestration behavior

### 2. Document-task checkpoint simulator

This simulator studies document-task orchestration with stronger persistence and integrity controls.

Core characteristics:

- task contract checks
- rough token estimation
- Word / Excel / PowerPoint-style task simulation
- per-task checkpoint and resume
- audit log hash chain
- protected checkpoint files
- artifact integrity records
- personal-data-safe audit, checkpoint, and artifact writes
- tamper-evidence detection
- CLI-based local simulation
- no automatic external submission

Important implementation note:

The simulator writes text-backed artifact outputs representing document-task results. It does not claim to generate fully formatted Microsoft Office documents unless separate document-generation libraries are connected and tested.

Hashing and HMAC provide tamper evidence. They do not provide physical write prevention. In real deployment, HMAC keys must be supplied from an environment variable or protected key file and must not be committed to the repository.

### 3. Emergency contract gate-orchestration simulator

This simulator combines an emergency-contract scenario with a gate-based orchestration flow.

It is intended as a small integration proof-of-concept, not as a production contracting, legal, or signal-control system.

Core characteristics:

- emergency-contract scenario
- fixed safety-check order
- ambiguous-priority review behavior
- evidence validation and fabricated-evidence detection
- human authorization checkpoint
- admin finalize checkpoint
- blocked-stop invariants for high-risk conditions
- simulated contract draft artifact generation
- tamper-evident audit rows
- no real-world signal control
- no legal effect
- no external submission, upload, send, API call, or deployment

Canonical integration flow:

```text
Meaning → Consistency → Ambiguity Review → Evidence Check → Human Authorization
→ Draft → Safety Review → Draft Review → External-Action Safety
→ Admin Finalize → Dispatch
```

This simulator is useful for checking:

- emergency-contract scenario handling
- relative-priority evaluation
- fabricated evidence pause behavior
- real-world control blocking
- user and admin stop paths
- simulated artifact dispatch only
- audit-log verification
- safety invariants across normal and abnormal paths

### 4. Infrastructure lifeline mediation simulation

This simulator models a constrained resource-allocation scenario involving three infrastructure agents:

- electricity
- water
- gas

It is intended as a local, seed-reproducible research simulation for studying how a mediator can create proposal-only allocation plans under constrained failure resources.

Core characteristics:

- three infrastructure agents with normal resource requirements
- failure-mode total resource constraint
- minimum guarantees
- priority weights
- life-risk scores
- shortage-rate-aware allocation
- simulated human decisions
- JSON and stdout output
- no external API access
- no real infrastructure control
- no automatic recovery
- no automatic shutdown or disconnection

The mediator only creates allocation proposals. It does not control real infrastructure or perform real-world recovery actions.

The simulated human operator may return:

- `APPROVE`
- `REJECT`
- `REDEFINE`
- `REQUEST_ALTERNATIVES`

This simulator is useful for checking:

- constrained resource allocation behavior
- proposal-only mediation
- seeded reproducibility
- human-review branch behavior
- safety-boundary flags
- JSON output behavior
- allocation totals staying within the available resource limit

### 5. Agent incident mediation simulation

This simulator models a local-only incident mediation flow where one simulated agent performs an out-of-contract action during orchestration.

A diagnostic review helper detects a log/output mismatch, creates review artifacts, and escalates the finding to a mediator. The mediator then performs simulated human review before applying an in-memory result.

Core characteristics:

- simulated abnormal agent behavior
- log/output mismatch detection
- escalation packet to mediator
- simulated human decision branching
- in-memory stop or authorization result only
- audit-log verification
- dependency consistency verification
- result consistency verification
- local artifacts only
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

This simulator is useful for checking:

- whether abnormal agent behavior is detected from log/output inconsistency
- whether the diagnostic helper escalates instead of directly stopping agents
- whether the mediator performs human review before applying a stop or authorization result
- whether the simulated user instruction is recorded
- whether normal agents are not incorrectly stopped or locked
- whether audit logs and generated artifacts remain consistent

### 6. Code anomaly handoff simulation

This simulator models a local-only code-contract anomaly handoff flow.

A diagnostic review helper detects a metadata-only code-contract anomaly and escalates the finding to a user-controlled coordinator. The coordinator does not decide by itself. It requests simulated human review and then executes only the simulated user instruction.

Core characteristics:

- metadata-only code-contract anomaly detection
- escalation to a user-controlled coordinator
- no autonomous decision by the coordinator
- simulated human instruction recording
- safe checkpoint handoff and resume
- audit-log verification
- dependency consistency verification
- result consistency verification
- no code execution
- no malware behavior
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

This simulator is useful for checking:

- whether code-contract anomalies are detected
- whether findings are escalated to a user-controlled coordinator
- whether the coordinator requests human review instead of self-deciding
- whether the simulated user instruction is recorded
- whether lock and quarantine-handoff-resume branches both work
- whether standby handoff resumes from a safe checkpoint
- whether audit logs and generated artifacts remain consistent

### 7. Agent incident risk-report handoff simulation

This simulator extends the local-only agent incident mediation line with report-only risk estimation and user-controlled handoff.

It keeps the same basic incident setting: one simulated agent performs an out-of-contract action, a diagnostic helper detects a log/output mismatch, and the run stays local-only.

Core characteristics:

- simulated abnormal agent behavior
- log/output mismatch detection
- report-only risk estimate
- calculation trace recording
- escalation to a user-controlled coordinator
- simulated human instruction recording
- lock branch
- quarantine-handoff-resume branch
- standby agent promotion
- checkpoint-based task resume
- audit-log verification
- dependency consistency verification
- risk-report verification
- result consistency verification
- no external API access
- no real process control
- no malware behavior
- no automatic fix, commit, push, or merge

This simulator is useful for checking:

- whether the incident flow still works after adding risk reporting and handoff
- whether high-risk simulated incidents are routed to a user-controlled coordinator
- whether the simulated user instruction is recorded
- whether lock and quarantine-handoff-resume branches both work
- whether standby handoff resumes from a checkpoint
- whether normal agents are not incorrectly locked, quarantined, or resumed
- whether audit logs, risk reports, checkpoints, and generated artifacts remain consistent

### 8. Office task mediation simulation

This simulator models a local-only Office task mediation flow using Word / Excel / PowerPoint-style synthetic artifacts.

It checks whether generated document, spreadsheet, and presentation outputs remain aligned with the original user task instruction. A diagnostic helper reads logs, detects anomalies, and outputs risk materials only. The mediator receives only masked metadata packets and reconciles differences between the original task and generated outputs. The coordinator does not decide by itself. It distributes tasks only to user-selected agents, triggers human review only when the score is above the threshold, and executes only explicit user-selected actions.

Simulation flow:

```text
User selects target agents
↓
Coordinator dispatches the task only to user-selected agents
↓
Word / Excel / PowerPoint-style synthetic artifacts are generated
↓
Diagnostic helper reads internal logs and creates masked metadata packets
↓
Mediator receives only masked metadata and compares outputs against the original task snapshot
↓
Mediator calculates the collision score
↓
Risk estimate is attached as advisory metadata
↓
If score == 0.8, the result remains warning / draft review
↓
If score > 0.8, the run pauses for human review
↓
User selects the next action
↓
Coordinator executes only the explicit user-selected action
```

The simulator does not generate real Office files. It uses synthetic Word / Excel / PowerPoint-style records to test consistency, masking, threshold behavior, human-review routing, and draft-only revision propagation.

Core characteristics:

- fixed Word / Excel / PowerPoint synthetic task set
- user-selected agent dispatch
- original task snapshot and hash-fixed task baseline
- diagnostic log analysis and masked metadata handoff
- no raw log handoff to mediator
- Office output consistency checks
- profit, formula, chart, and conclusion mismatch detection
- personal-data and confidential-signal masking
- threshold policy: `score == 0.8` is warning / draft review only
- threshold policy: `score > 0.8` triggers human review
- user-scoped draft revision proposals only
- related agents create draft revision proposals only
- coordinator has no autonomous decision authority
- audit-log verification
- result consistency verification
- required Word / Excel / PowerPoint artifact completeness checks
- missing required artifacts are detected
- zero values are treated as valid values
- safety-buffer metadata is explicit and reviewable
- internal raw agent logs are not saved by default and require explicit simulation-only opt-in
- no real Office document generation
- no external API access
- no real process control
- no automatic fix, commit, push, or merge

This simulator is useful for checking:

- whether Word / Excel / PowerPoint-style outputs remain consistent
- whether Excel formula results and PowerPoint chart values conflict
- whether Word text, spreadsheet values, and presentation summaries diverge
- whether the original user instruction remains the comparison baseline
- whether personal-data and confidential signals are masked before mediation
- whether the mediator uses only masked metadata
- whether `score == 0.8` does not trigger human review
- whether `score > 0.8` triggers human review
- whether user-targeted revision prompts generate draft proposals only
- whether the coordinator avoids self-decision and only executes explicit user-selected actions

### 9. Trust-to-risk automation draft extension

This draft extension adds automation-entry and automation-continuation diagnostics to the Office task mediation line.

Core characteristics:

- trust-score based automation entry diagnosis
- `trust_score == 0.9` is not auto eligible
- `trust_score > 0.9` may become an automation candidate after user approval
- automation-risk based continuation diagnosis after automation starts
- `automation_risk_score < 0.1` continues automation
- `automation_risk_score >= 0.1` triggers fail-closed suspension
- coordinator relay-only temporary automation suspension
- user review required for automation resume
- diagnostic helper remains diagnostic-only and does not directly command agents
- no automatic fix, commit, push, or merge

This extension is useful for checking:

- whether automation entry remains gated by `trust_score > 0.9`
- whether `trust_score == 0.9` is treated as non-eligible
- whether user approval is required before automation becomes active
- whether automation continuation switches from trust scoring to risk scoring
- whether `automation_risk_score == 0.1` fails closed into suspension
- whether user review is required to resume suspended automation
- whether automatic fix, commit, push, and merge remain disabled

### 10. Source-grounded Office orchestration simulation

This simulator extends the Office task mediation line from artifact consistency checking into source-grounded multi-agent orchestration.

Core additions:

- primary / secondary / tertiary synthetic source agents
- source evidence packets instead of raw source logs
- source-to-artifact consistency checks
- Office draft artifacts grounded in source packets
- mediator reconciliation for source conflicts and artifact contradictions
- diagnostic source/artifact packet boundary checks
- personal-data and confidential-signal masking
- unsupported-claim detection
- missing artifact detection
- unknown selected-agent detection
- request tampering detection
- retry loop with a fixed loop limit
- final output remains draft-only and requires user review

The simulator remains local-only and synthetic. It does not fetch real sources, generate real Office files, call external APIs, control real processes, auto-fix, commit, push, or merge.

This simulator is useful for checking:

- whether source packets and generated artifacts remain consistent
- whether unsupported claims are routed to review
- whether source conflicts are reported
- whether missing required artifacts are detected
- whether unknown selected agents are detected
- whether unsafe mediator request keys are rejected
- whether request tampering is rejected
- whether reconciliation stops after the loop limit
- whether audit logs and generated artifacts remain consistent

## Batch execution and resume

This repository includes batch-style orchestration examples.

Batch execution means that multiple document-related tasks can be evaluated as a single orchestration run while preserving check decisions, audit records, and interruption points.

### Mediator-based batch flow

The mediator-based simulator can accept multiple tasks in one run.

Example use cases:

- evaluate several spreadsheet or slide tasks together
- compare task-level check outcomes
- check human-review behavior across multiple tasks
- verify mediator advice before orchestration
- confirm that each task still passes through the fixed check order

This line is useful when the focus is on:

- multi-task check behavior
- mediator separation
- ambiguity review and human-review transitions
- reason-code stability
- lightweight orchestration tests

Example task sequence:

- T1: spreadsheet task
- T2: presentation task
- T3: ambiguous task requiring human review

Expected behavior:

- each task is normalized by the agent
- each task receives mediator advice
- each task is evaluated by the orchestrator
- paused tasks remain non-final unless a high-risk safety check blocks them
- dispatch only occurs when the final decision is to continue

### Document-task batch flow

The document-task checkpoint simulator uses a fixed document-task sequence:

```text
Word → Excel → PowerPoint
```

This line is useful when the focus is on:

- batch task execution
- per-task checkpointing
- interruption and resume
- artifact integrity records
- protected checkpoints
- audit log hash chains
- tamper-evidence detection

If a task is interrupted, the simulator records:

- failed task ID
- failed check
- reason code
- checkpoint path
- resume requirement
- human confirmation requirement when applicable

A later run can resume from the checkpoint after human confirmation when required.

## Batch scripts

Batch scripts may be used as convenience wrappers for local simulation runs.

Recommended script examples:

- local demo run
- checkpoint resume run
- tamper-evidence check run

These scripts should be treated as local developer utilities only.

They should not:

- embed production HMAC keys
- upload or submit artifacts automatically
- bypass human confirmation
- delete files automatically
- process real personal or confidential data
- change license or safety semantics
- weaken tests or safety-check invariants

For local demonstrations, a demo key mode may be used only when the simulator explicitly supports it. Production-like runs should use an environment variable or a protected key file for HMAC keys.

### Example batch-script roles

#### Local demo script

Purpose:

- run a local demonstration
- use safe sample input
- write audit logs and simulated artifacts to local output directories
- avoid external submission

#### Resume script

Purpose:

- resume from a checkpoint
- require explicit resume confirmation
- verify completed artifacts before continuing
- preserve checkpoint integrity

#### Tamper-check script

Purpose:

- verify audit-log, checkpoint, and artifact integrity behavior
- demonstrate tamper-evidence detection
- pause for human review if integrity verification fails

## Recommended reading order

For gate behavior and mediator separation:

- read the mediator-based gate simulator
- read its corresponding tests

This path is useful for studying fixed check order, human-review transitions, blocked and non-blocked behavior, mediator separation, and lightweight multi-task orchestration behavior.

For checkpoint, resume, artifact integrity, and hash-chain behavior:

- read the document-task checkpoint simulator
- read its corresponding tests

This path is useful for studying batch execution, checkpointing, artifact verification, tamper evidence, and resume behavior.

For emergency-contract behavior:

- read the emergency contract gate-orchestration simulator
- read its corresponding tests

This path is useful for studying how a concrete emergency-contract scenario can be evaluated by fixed checks, human-review checkpoints, audit verification, and simulated artifact dispatch without real-world control or legal effect.

For agent incident mediation behavior:

- read the agent incident mediation simulator
- read its corresponding tests

This path is useful for studying how a diagnostic helper detects a simulated log/output mismatch, escalates to a mediator, triggers human review, records the user instruction, and verifies output consistency without external side effects.

For code anomaly handoff behavior:

- read the code anomaly handoff simulator
- read its corresponding tests

This path is useful for studying how metadata-only code-contract anomalies are detected, escalated to a user-controlled coordinator, reviewed by a human, and handled through safe checkpoint handoff without external side effects.

For Office task mediation behavior:

- read the Office task mediation simulator
- read its corresponding tests

This path is useful for studying Word / Excel / PowerPoint-style consistency checks, masked metadata handoff, threshold-based human-review behavior, and user-targeted draft revision without automatic application.

For source-grounded Office orchestration behavior:

- read the source-grounded Office orchestration simulator
- read its corresponding tests

This path is useful for studying how source agents, source evidence packets, Office draft artifacts, mediator reconciliation, diagnostic packet handling, human-review relay, and loop-limit enforcement work together without external side effects.

For behavior verification, always read the implementation together with the corresponding tests.

This is especially important for:

- safety-check invariants
- reason-code expectations
- human-review transitions
- blocked and non-blocked behavior
- checkpoint and resume behavior
- tamper-evidence behavior
- reproducibility checks
- benchmark expectations
- batch execution behavior

## Testing and behavior

In this repository, tests often define the expected behavior of the simulators and orchestration logic.

When checking behavior, read the implementation together with the corresponding tests.

Tests may verify:

- fixed check order
- fail-closed behavior
- human-review escalation
- ambiguity review behavior
- blocking constraints
- checkpoint recovery
- audit-log integrity
- artifact hash verification
- reason-code stability
- reproducibility expectations
- batch-task behavior
- CLI behavior
- emergency-contract scenario flow
- fabricated-evidence handling
- real-world control blocking
- user/admin rejection paths
- tamper-evidence detection

A newer version number does not always mean that the file is the primary recommended entry point. Some files are preserved for historical comparison, reproducibility, or versioned experiments.

## Gate and decision model

The repository uses explicit gate decisions to make orchestration behavior traceable.

Common decisions include:

- `RUN`
- `PAUSE_FOR_HITL`
- `STOPPED`

General interpretation:

- `RUN`: the simulator may continue to the next check or dispatch step
- `PAUSE_FOR_HITL`: the simulator should pause and wait for human review
- `STOPPED`: the simulator has reached a blocking condition

Ambiguous or relative requests should pause for human review instead of being silently treated as safe.

Higher-risk conditions, especially external side effects, policy violations, or unsafe actions, should be blocked or routed to human review depending on the simulator contract.

## Audit and integrity model

Audit and integrity behavior differs by simulator line.

The mediator-based simulator focuses on lightweight audit events and safe context logging.

The document-task checkpoint simulator adds stronger integrity controls:

- audit log hash chain
- row-level HMAC
- checkpoint HMAC
- artifact SHA-256
- artifact HMAC
- completed-artifact verification on resume
- tamper-evidence detection

These mechanisms are intended to make changes detectable. They do not prevent a local actor from modifying files on disk.

## Checkpoint and resume model

Checkpoint-based simulators are designed to support interrupted execution.

A checkpoint may record:

- run ID
- current task ID
- failed task ID
- failed check
- reason code
- task status
- artifact path
- artifact hash
- whether resume is allowed
- whether human review is required before resume

When resuming, completed artifacts should be verified before the simulator continues. If verification fails, the run should pause for human review rather than continue silently.

## Artifact model

Artifact outputs in the simulator should be treated as research artifacts.

Depending on the simulator line, outputs may include:

- artifact previews
- text-backed document-task outputs
- audit JSONL files
- checkpoint JSON files
- integrity metadata
- summary records

The repository should not describe simulated outputs as complete production Office documents unless actual document-generation code is added and tested.

## External side effects

External side effects include actions such as:

- sending email
- uploading files
- submitting artifacts
- pushing changes
- deleting files
- calling external APIs
- changing license semantics

These actions should remain blocked, prohibited, or human-review gated depending on the simulator contract.

No script or simulator should silently perform external submission.

## Archive and historical files

Some files are preserved for:

- historical comparison
- reproducibility
- versioned experiments
- regression testing
- design comparison

Files under `archive/` should generally be treated as historical or reference material unless explicitly referenced by current tests or documentation.

## Language

- English README: `README.md`
- Japanese README: `README.ja.md`

## License

This repository uses a split-license model:

- Software code: Apache License 2.0
- Documentation, diagrams, and research materials: CC BY-NC-SA 4.0

See `LICENSE_POLICY.md` for details.

## Project policies

- [Security Policy](SECURITY.md)
- [License Policy](LICENSE_POLICY.md)
- [Contributing Guide](CONTRIBUTING.md)

## Disclaimer

This repository is provided for research and educational purposes only.

It is not a production safety system, legal tool, medical tool, financial tool, regulatory compliance tool, or autonomous control system.

Use it only in local, authorized, defensive, and educational contexts.
