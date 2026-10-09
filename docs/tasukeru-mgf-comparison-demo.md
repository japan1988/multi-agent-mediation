# Tasukeru MGF comparison side experiment

This started as a small side experiment out of curiosity about what would
happen if the Mediator, Gate, Framework and Observer were connected within
one framework while retaining separate authority. It also serves as a
controlled integration test. It is not a production feature or a claim of
improved real-AI accuracy.

After wrapping up this experiment, I plan to focus on developing the next
simulator. I therefore expect Tasukeru updates to pause for a while.

## What was missing and what this adds

The existing mediator boundary demo tests a captured proposal against a
pinned gate. The new comparison adds fixture communication, fresh state
checks, bounded feedback and report observation around that same unchanged
gate. The Mediator supplies a candidate; it cannot grant execution authority,
rewrite the Gate's verdict or remove the Framework's evidence.

The initial connected prototype had a gap between the Observer's last check
and report finalization. A STOP or rejection arriving in that gap could still
leave the report marked `HUMAN_REVIEW`. Two deliberately injected scenarios
reproduce this problem. This is a problem in the experimental wiring, not a
finding of a vulnerability in the existing Tasukeru workflows.

The repaired mock implementation checks current state and consumes a one-use
report slot under the same in-process lock used for STOP and rejection. A
monotonic fixture version also detects state that changes and later returns
to the same bytes. The unprotected path remains a regression control.

This covers STOP received before finalization. STOP received after a report
has been finalized does not retract that report. The lock is local to one
Python process; it is not a shared transaction or a cancellation guarantee
across GitHub Actions runs.

## Four comparison paths

| Path | Included controls |
| --- | --- |
| A | Same pinned Gate with captured input |
| B | Handwritten Mediator candidate followed by that same Gate |
| C | B plus versioned Framework snapshots and anchored fixture messages |
| D | C plus bounded Gate feedback, an independent report Observer and repaired finalization |

Each path receives the same initial literal candidate. All paths invoke the
unchanged outer/evidence gate. A/B/C intentionally omit controls to show what
the new wiring contributes. The experiment compares protocol and state
handling, not the intelligence of different models.

The fixture messages bind the run, proposal, input evidence and state
version. The test driver owns the anchors and simulated producer roles.
Matching hashes do not authenticate a real remote publisher.

For evidence failures, D uses the existing mock resubmission controller.
Outer policy failures use a new local feedback bridge because the evidence
controller does not check destinations, scope or action composition. Every
correction is handwritten, limited to one mock resubmission and checked
against the same original evidence. The bridge is experimental code, not a
live approval path.

## Expected bounded comparison

There are 83 predeclared scenarios per path: 32 static Gate scenarios, 16
healthy controls, 7 state changes, 8 message faults, 8 report faults, 3 late
changes and 9 mock approval scenarios. Of these, 19 are benign controls, 59
must not proceed to human review and 5 permit a bounded mock correction.
The expectations are written to `cases.json` before the comparisons run.

The repaired comparison expects every path to match its declared contract.
That is different from catching every fault: intentionally incomplete paths
have weaker contracts.

| Path | Invalid/stale reports forwarded out of 59 | Benign reports withheld out of 19 |
| --- | ---: | ---: |
| A | 26 | 0 |
| B | 26 | 0 |
| C | 11 | 0 |
| D before the finalization repair | 2 | 0 |
| D after the finalization repair | 0 | 0 |

`HUMAN_REVIEW` means a draft can be reviewed. It is never permission to run
an external action. The counters above concern simulated report forwarding,
not unsafe actions that were actually executed.

Thirteen scheduled thread checks cover STOP, rejection and unknown state
before finalization, plus two competing finalizers sharing one slot. The
existing 20 baseline demo self-tests also run. These finite tests do not prove
correctness under every possible thread schedule.

## Files and execution

This experiment adds five files and does not overwrite existing workflows,
gates, approval adapters or simulator code:

| File | Purpose |
| --- | --- |
| `.github/workflows/tasukeru-mgf-comparison-demo.yml` | Separate manual launcher with synthetic inputs |
| `scripts/tasukeru_mediation_demo/run_mgf_comparison_demo.py` | Comparison, local finalization repair and report entry point |
| `scripts/tasukeru_mediation_demo/mgf_comparison_baseline.json` | Pin 20 original files at commit `b58337bbc2f23b599d41e2ff213be67d9d23d9af` |
| `tests/test_tasukeru_mgf_comparison_demo.py` | Integration and entry-point regressions |
| `docs/tasukeru-mgf-comparison-demo.md` | Purpose, development note, results and limits |

Run locally from the repository root with a new output directory:

```bash
python -I -B tests/test_tasukeru_mgf_comparison_demo.py
python -I -B scripts/tasukeru_mediation_demo/run_mgf_comparison_demo.py --output /tmp/tasukeru-mgf-reports
```

Synthetic evidence is the default. It contains two invented differences and
is explicitly labeled `SYNTHETIC_TEST_FIXTURE`. The Python entry point also
accepts `--observer-zip /path/to/local-observer-report.zip` for an already
downloaded report. That input is labeled
`LOCAL_OBSERVER_ZIP_UNAUTHENTICATED`; it does not establish publisher identity.
No observer download or AI API call is made by the comparison.

The baseline manifest and source files are checked before importing existing
code and again after running the experiment. A change stops the comparison;
it never refreshes its pins automatically to make a check pass.

After manual review and merge, select **Tasukeru MGF Comparison Demo
(fixtures only)** in GitHub Actions and choose **Run workflow** on `main`.
The launcher only permits a manual run on this repository's `main` branch.
It uses a standard Ubuntu 24.04 runner and the Python standard library, with
read-only repository permissions and separate artifacts retained for 7 days.
The runner has a six-minute timeout.

Outputs are `cases.json`, `comparison.csv`, `report.json` and `summary.md`,
plus the workflow's self-test log. Failures return a nonzero exit code.
`EXPECTED_MOCK_BEHAVIOR_AFTER_DRAFT_FIX` describes the bounded fixtures only.

## Validation scope

Local validation passed before placing this branch for review:

- 23 integration and entry-point tests.
- 83 cases per comparison path; repaired D matched 83/83 expectations with
  no invalid/stale report forwarded in the declared non-review scenarios.
- 13 scheduled thread checks and 20 baseline self-tests.
- The default synthetic run and a run using an already downloaded local
  Observer ZIP with two differences, retaining its unresolved classifications.
- All 20 pinned baseline files remained unchanged.
- Python 3.10 syntax parsing, YAML parsing, shell syntax, startup environment
  handoff, summary paths and launcher configuration checks.

The previously available actionlint binary was truncated and could not run;
actionlint validation is not claimed. GitHub Actions runtime verification of
this new launcher is pending. The workflow has not been dispatched as part
of this preparation.

There are no real AI calls, real user approvals, durable ledger writes,
automatic repository repairs, external actions or final adoption. The full
simulator is not connected. Cause, actor and snapshot relationships remain
`UNKNOWN`, and final adoption remains `NOT_DETERMINED`. Local fixture timing
does not measure production latency, model cost or storage overhead.
