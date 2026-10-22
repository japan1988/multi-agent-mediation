# Maestro Orchestrator — Multi-Agent Orchestration Framework

English / [日本語](README.ja.md)

## What it does

A research and educational repository for studying how simulated agents coordinate: when to continue, pause or stop, how to hand decisions to human review, and whether outputs agree with logs.

- **Maestro**: simulations of agent coordination, check ordering, audit records and checkpoints.
- **Tasukeru**: an advisory workflow that organizes static-analysis and repository-specific findings for human review.

## Development status and unverified areas

Phase 1F passed its basic simulation tests, but subsequent in-depth validation identified several issues requiring correction.

These issues are being addressed in V04. The final freeze remains on hold until the fixes have been re-tested and reviewed.

Successful demos and individual tests do not establish completion or safety of Phase 1F as a whole. The mock experiments do not verify real-AI judgment, real-user identity or approval, or durable STOP and duplicate-use protection across separate GitHub Actions runs. Each experiment's documentation defines its scope.

## First run

Start with the **introductory HITL demo v0.1** to see hold, mock approval and resume behavior. Install Git and Python; the repository's Python CI targets 3.10 and 3.11. This demo needs no additional packages or AI API key.

```bash
git clone https://github.com/japan1988/multi-agent-mediation.git
cd multi-agent-mediation
python -B demo_hitl_flow_v0_1.py
```

Use `python3` instead of `python` if required by your environment.

The output shows `WAITING_HITL`, `LOCAL_HOLD` and completion after simulated clarification and approval. These responses are fixed in the script; it does not wait for user input. The task labeled as an external send only records state and text. It sends nothing.

Implementation: [demo](demo_hitl_flow_v0_1.py) / [HITL simulator](hitl_flow_sim_v0_1.py)

## Important constraints

- This is a research prototype. A test `PASS` or successful CI run is not execution permission, final adoption or a production safety guarantee.
- The design under study separates mediation proposals, safety checks and execution authority, with humans retaining the final decision. Do not treat mock approval as real approval.
- Tasukeru Analysis saves review material and comment drafts in its summary and artifacts. It does not automatically post PR comments, repair source files, create branches, PRs or commits, push, or merge.
- GitHub Actions workflows involve network activity, including GitHub API reads, dependency retrieval and auditing, and artifact storage. Their communication scope differs from the local demo above.
- Review only targets you own or are explicitly authorized to review, for defensive and research purposes. Do not use real secrets, personal information or confidential data in examples. See the [Security Policy](SECURITY.md) and its [Japanese translation](SECURITY.ja.md); the English policy takes precedence if they differ.
- Hashes and audit records support integrity checks. They do not establish publisher identity, prevent changes or guarantee whole-system safety.

Software code is under [Apache License 2.0](LICENSE). Documentation, diagrams and research materials are under CC BY-NC-SA 4.0.

## Further reading

| Topic | Reference |
| --- | --- |
| Documentation, diagrams and reference files | [Documentation index](docs/index.md) |
| Document simulator architecture, audit and resume | [Architecture documentation](docs/architecture.md) |
| Actual Tasukeru Analysis configuration | [Analysis workflow](.github/workflows/tasukeru-analysis.yml) |
| Mock mediation and independent verification boundaries | [Mediator boundary demo](docs/tasukeru-mediator-boundary-demo.md) |
| Mediator, Gate, Framework and Observer comparison | [MGF comparison demo](docs/tasukeru-mgf-comparison-demo.md) |
| Earlier simulator catalog and extended explanations | [Pinned snapshot of the previous README](https://github.com/japan1988/multi-agent-mediation/blob/6e2f157cdfa56a5010a9ce5bb274e2eae685538c/README.md) |

Historical and version-specific documents are reference records. Distinguish them from the current implementation and validation status of Phase 1F.
