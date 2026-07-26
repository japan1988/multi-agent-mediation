# Patch 13: ARL hash-chain tamper detection

## Status

Patch 13 is a specification-only patch.

It defines deterministic, local, fixture-based verification requirements for
detecting partial modification, broken links, deletion, and reordering in an
ARL hash chain.

This specification does not itself:

- implement the verifier
- modify an existing workflow
- create or publish an artifact
- modify runtime ARL generation
- introduce HMAC or digital signatures
- create a pull request
- merge
- deploy
- grant authority for a later implementation stage

Implementation requires separate Human Owner approval.

## Role-based terminology

This specification uses role-based terminology and does not require, endorse,
or depend on a specific company, model, product, provider, service, or
repository platform.

The relevant roles are:

- `Human Owner`
- `Design and Review Advisor`
- `Implementation Executor`
- `Repository and CI Evidence Sources`

The Design and Review Advisor may evaluate the specification and resulting
evidence but does not grant repository authority.

The Implementation Executor may perform only work explicitly approved by the
Human Owner for the current stage.

Repository and CI Evidence Sources provide evidence but do not grant
authorization.

## Purpose

Patch 13 defines how to prove that the existing non-keyed ARL hash-chain
contract detects partial tampering.

The required verification must distinguish between:

1. syntactically valid JSONL
2. structurally valid ARL rows
3. internally consistent row hashes
4. internally consistent chain hashes
5. correct linkage between adjacent rows
6. correct row order
7. a valid final head hash

A JSONL document is not considered an intact ARL chain merely because each
line is valid JSON.

## Existing baseline

The existing ARL stress framework verifies:

- a valid ARL JSONL fixture
- an empty ARL fixture
- a fixture with a missing required key
- a fixture containing invalid JSONL

Patch 13 does not replace those checks.

Patch 13 adds a separate integrity-verification scope for:

- row-content tampering
- stored row-hash tampering
- stored chain-hash tampering
- previous-link tampering
- row deletion
- row reordering
- final-row tampering

## Core principle

An ARL chain is valid only when every row satisfies both row integrity and
link integrity.

Expected negative fixtures are successful tests only when the intended
tampering is detected.

A verifier returning `verified=true` for a tampered fixture is a failed test.

A verifier returning `verified=false` for the canonical valid fixture is also
a failed test.

## Scope

Patch 13 covers a deterministic, local, non-keyed SHA-256 chain.

The intended implementation is limited to:

- one local verification and stress script
- synthetic deterministic fixtures
- one deterministic fixture manifest
- local automated tests
- JSON and Markdown result artifacts
- optional repository CI integration under separate approval

Patch 13 does not modify the meaning of existing ARL decisions, gates, reason
codes, findings, or evidence.

## Out of scope

The following are explicitly out of scope:

- HMAC
- digital signatures
- asymmetric signing
- certificate management
- production key management
- secret storage
- identity authentication
- author authentication
- remote timestamp authorities
- external databases
- network verification
- external service calls
- AI API calls
- external AI provider calls
- permission expansion
- workflow self-modification
- automatic repair
- automatic hash regeneration after detection
- automatic commit
- automatic push
- automatic pull-request creation
- automatic retry
- automatic merge
- deployment
- publication of private data
- modification of historical ARL records

## Terminology

### Canonical row

A JSON object representing one ARL entry before `row_hash` and `chain_hash`
are added or verified.

### Canonical JSON

UTF-8 JSON serialized with:

- `ensure_ascii=false`
- keys sorted lexicographically
- separators `(",", ":")`
- no insignificant whitespace
- no trailing newline inside the hashed payload

### Row body

The complete row with only these fields excluded:

- `row_hash`
- `chain_hash`

The `prev_hash` field remains inside the row body and is therefore protected
by `row_hash`.

### Row hash

The SHA-256 digest of the canonical JSON representation of the row body.

### Previous hash

The value stored in `prev_hash`.

For the first row, the required value is:

```text
GENESIS
```

For every later row, it must equal the previously recomputed `chain_hash`.

### Chain hash

The SHA-256 digest of:

```text
<prev_hash>:<row_hash>
```

encoded as UTF-8.

### Head hash

The recomputed `chain_hash` of the final row.

### Tamper detection

A deterministic result in which at least one integrity rule fails for a
fixture expected to be tampered.

Tamper detection does not authorize automatic repair.

## Canonical hash contract

For each row, the verifier must use the following equivalent operation:

```python
canonical_row_body = json.dumps(
    {
        key: value
        for key, value in row.items()
        if key not in {"row_hash", "chain_hash"}
    },
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)

recomputed_row_hash = hashlib.sha256(
    canonical_row_body.encode("utf-8")
).hexdigest()

recomputed_chain_hash = hashlib.sha256(
    f"{row['prev_hash']}:{recomputed_row_hash}".encode("utf-8")
).hexdigest()
```

No alternative serialization is permitted.

The verifier must not rely on Python dictionary insertion order.

## Required row fields

Every Patch 13 integrity fixture row must contain:

* `seq`
* `run_id`
* `layer`
* `decision`
* `sealed`
* `overrideable`
* `final_decider`
* `reason_code`
* `prev_hash`
* `row_hash`
* `chain_hash`

Additional fields are permitted and must be included in the row-hash
calculation unless they are exactly `row_hash` or `chain_hash`.

## Field requirements

### `seq`

* integer
* begins at `1`
* increases by exactly `1`
* contains no duplicate
* contains no gap

### `run_id`

* non-empty string
* identical for every row in one fixture

### `prev_hash`

* string
* first row is exactly `GENESIS`
* subsequent rows use a 64-character lowercase hexadecimal value
* subsequent value equals the previously recomputed `chain_hash`

### `row_hash`

* string
* exactly 64 lowercase hexadecimal characters
* equals the recomputed row hash

### `chain_hash`

* string
* exactly 64 lowercase hexadecimal characters
* equals the recomputed chain hash

## Verification order

The verifier must process rows in file order.

For each fixture, it must:

1. confirm that the fixture exists
2. decode the file as UTF-8
3. parse each non-empty line as one JSON object
4. reject an empty chain
5. verify all required fields
6. verify field types
7. verify contiguous `seq` values
8. verify a consistent `run_id`
9. verify hash-field formatting
10. verify the first-row `GENESIS` value
11. compare each later `prev_hash` with the previous recomputed chain hash
12. recompute `row_hash`
13. compare the recomputed and stored row hashes
14. recompute `chain_hash`
15. compare the recomputed and stored chain hashes
16. calculate the final head hash
17. compare the head hash with the fixture manifest when an expected head is
    provided
18. record every detected reason code
19. produce an overall deterministic result

The verifier must not stop after the first row-level integrity error.

It may continue reading the fixture to produce complete evidence, provided
that it does not repair, normalize, or rewrite the fixture.

## Authoritative chain progression

The previously recomputed chain hash is authoritative for verifying the next
row.

A stored chain hash that fails verification must not become trusted merely
because the next row references it.

The verifier must preserve both:

* the stored value
* the recomputed value

in internal comparison logic.

Full raw ARL rows do not need to be copied into result artifacts.

## Verification outcomes

The permitted fixture outcomes are:

* `CHAIN_VALID`
* `TAMPER_DETECTED`
* `INPUT_INVALID`
* `BLOCKED`

### `CHAIN_VALID`

Used only when:

* all rows parse correctly
* all required fields are valid
* sequence and run identity are consistent
* every row hash matches
* every chain hash matches
* every link matches
* the expected head hash matches when provided
* no integrity error is present

### `TAMPER_DETECTED`

Used when:

* the fixture is syntactically readable
* at least one required integrity comparison fails
* the fixture manifest expects tampering

### `INPUT_INVALID`

Used when the fixture cannot be evaluated as an ARL chain because of:

* missing file
* invalid UTF-8
* invalid JSONL
* non-object row
* missing required field
* invalid required field type
* empty input

### `BLOCKED`

Used when:

* the manifest is invalid
* the expected outcome is unknown
* result generation fails
* a tampered fixture unexpectedly verifies successfully
* the canonical valid fixture fails verification
* deterministic expectations are inconsistent

## Reason-code vocabulary

The exact Patch 13 reason codes are:

1. `ARL_CHAIN_VALID`
2. `ARL_FIXTURE_NOT_FOUND`
3. `ARL_CHAIN_EMPTY`
4. `ARL_UTF8_INVALID`
5. `ARL_JSONL_INVALID`
6. `ARL_ROW_NOT_OBJECT`
7. `ARL_REQUIRED_FIELD_MISSING`
8. `ARL_FIELD_TYPE_INVALID`
9. `ARL_SEQUENCE_MISMATCH`
10. `ARL_RUN_ID_MISMATCH`
11. `ARL_HASH_FORMAT_INVALID`
12. `ARL_GENESIS_MISMATCH`
13. `ARL_PREV_HASH_MISMATCH`
14. `ARL_ROW_HASH_MISMATCH`
15. `ARL_CHAIN_HASH_MISMATCH`
16. `ARL_HEAD_HASH_MISMATCH`
17. `ARL_EXPECTED_DETECTION_MISSING`
18. `ARL_EXPECTED_VALIDATION_FAILED`
19. `ARL_MANIFEST_INVALID`
20. `ARL_OUTPUT_WRITE_FAILED`
21. `ARL_UNEXPECTED_ERROR`

Reason codes are evidence labels.

They do not grant authorization.

No implementation may silently add, remove, rename, or reinterpret these
reason codes without a later reviewed specification.

## Fixture design

The fixture directory is intended to be:

```text
tests/stress/fixtures/arl_hash_chain/
```

The canonical fixture is:

```text
valid_chain.jsonl
```

The manifest is:

```text
fixture_manifest.json
```

The manifest must define:

* `schema_version`
* `case_id`
* `fixture_name`
* `expected_outcome`
* `expected_primary_reason_code`
* `expected_additional_reason_codes`
* `intended_mutation`
* `target`
* `expected_row_count`
* `expected_canonical_head_hash` when applicable

### Additional reason-code rules

`expected_additional_reason_codes` is an allow-list of non-primary reason
codes.

- The expected primary reason code is mandatory.
- Additional reason codes are not mandatory merely because they appear in
  the allow-list.
- Every emitted non-primary reason code must appear in the allow-list.
- An empty allow-list prohibits additional reason codes.
- Duplicate reason codes are prohibited.
- Reason codes are recorded in verification order, preserving the first
  occurrence.

The manifest allow-list and the emitted `reason_codes` list must contain
unique reason-code values.

The emitted `reason_codes` list must:

- place the primary reason code first
- preserve verification order for later unique reason codes
- omit duplicate occurrences of the same reason code
- fail the case if it contains a non-primary reason code absent from the
  allow-list

| Case | Expected primary reason | Allowed additional reason codes |
|---|---|---|
| T1 | `ARL_CHAIN_VALID` | none |
| T2 | `ARL_ROW_HASH_MISMATCH` | `ARL_CHAIN_HASH_MISMATCH`, `ARL_PREV_HASH_MISMATCH` |
| T3 | `ARL_CHAIN_HASH_MISMATCH` | none |
| T4 | `ARL_PREV_HASH_MISMATCH` | `ARL_ROW_HASH_MISMATCH`, `ARL_CHAIN_HASH_MISMATCH` |
| T5 | `ARL_ROW_HASH_MISMATCH` | `ARL_CHAIN_HASH_MISMATCH`, `ARL_HEAD_HASH_MISMATCH` |
| T6 | `ARL_SEQUENCE_MISMATCH` | `ARL_PREV_HASH_MISMATCH` |
| T7 | `ARL_SEQUENCE_MISMATCH` | `ARL_PREV_HASH_MISMATCH` |

- `none` means `expected_additional_reason_codes` is an empty array.
- The table defines allowed additional reason codes, not mandatory additional
  reason codes.
- A reason code not listed for the case is unexpected and fails that case.
- The primary reason code remains mandatory.

Fixture data must be synthetic.

Fixture data must not contain:

* secrets
* credentials
* tokens
* API keys
* private keys
* real email addresses
* raw private prompts
* private personal information
* production incident data

## Mandatory cases

Patch 13 defines seven mandatory cases.

### T1 — Canonical valid chain

Case ID:

```text
valid_chain
```

Fixture:

```text
valid_chain.jsonl
```

Expected outcome:

```text
CHAIN_VALID
```

Expected primary reason code:

```text
ARL_CHAIN_VALID
```

Requirements:

* at least four rows
* contiguous sequence
* one consistent run ID
* first `prev_hash` equals `GENESIS`
* every row hash is valid
* every chain hash is valid
* every previous link is valid
* expected head hash matches
* no integrity error is produced

### T2 — Middle-row content tampering

Case ID:

```text
middle_row_content_tampered
```

The fixture must change one protected content value in a middle row.

Examples include:

* `reason_code`
* `decision`
* one synthetic evidence value

The fixture must not update:

* `row_hash`
* `chain_hash`
* downstream hashes

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_ROW_HASH_MISMATCH
```

The modified fixture must remain valid JSONL.

### T3 — Middle-row chain-hash tampering

Case ID:

```text
middle_row_chain_hash_tampered
```

The fixture must change exactly one hexadecimal character in the stored
`chain_hash` of a middle row.

It must not update the next row.

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_CHAIN_HASH_MISMATCH
```

A later `ARL_PREV_HASH_MISMATCH` must not be recorded solely because of this
mutation. The next row must be checked against the previous recomputed
`chain_hash`, not the tampered stored value.

### T4 — Middle-row previous-hash tampering

Case ID:

```text
middle_row_prev_hash_tampered
```

The fixture must change exactly one hexadecimal character in `prev_hash` on a
middle row.

It must not regenerate the row or chain hash.

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_PREV_HASH_MISMATCH
```

`ARL_ROW_HASH_MISMATCH` and `ARL_CHAIN_HASH_MISMATCH` may also be recorded.

### T5 — Final-row content tampering

Case ID:

```text
final_row_content_tampered
```

The fixture must change one protected field in the final row without
regenerating hashes.

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_ROW_HASH_MISMATCH
```

The verifier must not treat an unchanged stored head hash as authoritative.

### T6 — Rows reordered

Case ID:

```text
rows_reordered
```

Two non-genesis rows must be exchanged without regenerating any hash.

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_SEQUENCE_MISMATCH
```

`ARL_PREV_HASH_MISMATCH` may also be recorded.

### T7 — Row deleted

Case ID:

```text
row_deleted
```

One middle row must be removed without changing any remaining row.

Expected outcome:

```text
TAMPER_DETECTED
```

Expected primary reason code:

```text
ARL_SEQUENCE_MISMATCH
```

`ARL_PREV_HASH_MISMATCH` may also be recorded.

## Expected-negative semantics

T2 through T7 are expected-negative cases.

An expected-negative case passes only when:

* the verifier does not return `CHAIN_VALID`
* the outcome is `TAMPER_DETECTED`
* the required primary reason code is present
* the primary reason code is the first item in `reason_codes`
* every non-primary reason code is allowed by
  `expected_additional_reason_codes`
* no duplicate reason code exists
* the expected condition is detected
* no automatic repair occurs

A negative fixture that verifies successfully must produce:

```text
ARL_EXPECTED_DETECTION_MISSING
```

and must fail the overall Patch 13 verification.

## Result artifacts

The intended implementation must write exactly these local outputs:

```text
tasukeru_arl_hash_chain_stress_result.json
tasukeru_arl_hash_chain_stress_report.md
tasukeru_arl_hash_chain_stress_verify.json
```

### Result schema

The result JSON schema version is:

```text
tasukeru-arl-hash-chain-stress-v0.1
```

It must contain:

* schema version
* deterministic generated timestamp
* mode
* hash contract
* fixture directory
* manifest path
* safety boundary
* case list
* counts
* overall verified value

### Required counts

The counts object must include:

* `total_cases`
* `passed_cases`
* `failed_cases`
* `valid_cases`
* `expected_tamper_cases`
* `tamper_cases_detected`
* `unexpected_valid_cases`
* `input_invalid_cases`
* `total_rows_read`
* `total_integrity_errors`

For the canonical seven-case suite, the successful expected values are:

```json
{
  "total_cases": 7,
  "passed_cases": 7,
  "failed_cases": 0,
  "valid_cases": 1,
  "expected_tamper_cases": 6,
  "tamper_cases_detected": 6,
  "unexpected_valid_cases": 0,
  "input_invalid_cases": 0
}
```

### Per-case result

Each case result must include:

* `case_id`
* `fixture_name`
* `expected_outcome`
* `actual_outcome`
* `expected_primary_reason_code`
* `reason_codes`
* `file_exists`
* `line_count`
* `parsed_row_count`
* `expected_row_count`
* `stored_head_hash`
* `recomputed_head_hash`
* `first_error_line`
* `integrity_error_count`
* `expected_condition_detected`
* `passed`

The result must not include complete raw ARL rows unless separately approved.

### Verify artifact

The verify JSON schema version is:

```text
tasukeru-arl-hash-chain-stress-verify-v0.1
```

It must include:

* `verified`
* `checks`
* `counts`
* `result_sha256`
* `report_sha256`
* `manifest_sha256`
* `safety_boundary`
* `hmac_enabled`
* `authenticity_claimed`

The required values are:

```json
{
  "hmac_enabled": false,
  "authenticity_claimed": false
}
```

## Determinism

The implementation must be deterministic.

It must use:

```text
1970-01-01T00:00:00Z
```

as the generated timestamp in deterministic output artifacts.

It must not use:

* current time
* random values
* UUID generation
* network state
* repository-host metadata
* environment-specific absolute paths
* non-deterministic dictionary ordering

Two runs with the same fixtures and implementation must produce
byte-identical JSON and Markdown artifacts.

All JSON outputs must use:

* UTF-8
* no BOM
* LF line endings
* sorted keys
* two-space indentation
* exactly one final LF

## Intended CLI

The intended implementation entry point is:

```text
scripts/tasukeru_arl_hash_chain_stress.py
```

The intended command is:

```bash
python scripts/tasukeru_arl_hash_chain_stress.py \
  --fixtures-dir tests/stress/fixtures/arl_hash_chain \
  --output-dir <output-directory>
```

The command must not require network access or secrets.

## Exit codes

The intended exit-code contract is:

* `0`: all expected cases passed
* `1`: one or more fixture expectations failed
* `2`: invalid CLI usage or an operational configuration error

A detected expected tamper case is not an exit-code failure when its expected
reason code is present.

An undetected tamper case must result in exit code `1`.

## Fail-closed requirements

The implementation must fail closed when:

* the manifest is missing
* the manifest cannot be parsed
* a required case is absent
* an unknown case outcome is used
* a fixture is missing
* the valid fixture fails
* a tampered fixture verifies
* counts are inconsistent
* expected reason codes are absent
* artifact output cannot be written
* deterministic verification fails

No failure may trigger automatic correction or fixture regeneration.

## Safety boundary

The required safety boundary is:

```json
{
  "advisory_only": true,
  "human_review_required": true,
  "modifies_repository": false,
  "network_call": false,
  "ai_api_call": false,
  "external_ai_provider": false,
  "api_key_required": false,
  "secret_required": false,
  "automatic_apply": false,
  "automatic_repair": false,
  "automatic_commit": false,
  "automatic_push": false,
  "automatic_pr": false,
  "automatic_retry": false,
  "automatic_merge": false,
  "automatic_deploy": false
}
```

The verifier may read fixtures and write only to the explicitly supplied
output directory.

## Implementation phases

### Phase 1 — Minimal local proof

Implement and verify:

* T1 canonical valid chain
* T2 middle-row content tampering
* T3 middle-row chain-hash tampering
* T4 middle-row previous-hash tampering

Run local unit tests before adding extended cases.

### Phase 2 — Structural mutations

Add and verify:

* T5 final-row tampering
* T6 row reordering
* T7 row deletion

Phase 2 must not weaken Phase 1 assertions.

### Phase 3 — Repository CI integration

CI integration requires separate explicit approval after local verification.

Permitted CI behavior is limited to:

* running the deterministic verifier
* failing the check when expectations fail
* writing the three defined result files
* uploading those files as one workflow artifact

The intended artifact name is:

```text
tasukeru-arl-hash-chain-stress-results
```

CI integration must not:

* comment automatically
* modify a pull request
* modify a branch
* regenerate fixtures
* commit output
* push
* retry automatically
* merge
* deploy
* call an external service

## Intended tests

The intended automated test file is:

```text
tests/stress/test_tasukeru_arl_hash_chain_stress.py
```

Tests must cover:

* canonical JSON serialization
* row-hash recomputation
* chain-hash recomputation
* genesis validation
* previous-link validation
* sequence validation
* run-ID validation
* hash-format validation
* T1 through T7 expected outcomes
* output determinism
* count consistency
* safety-boundary verification
* CLI exit codes
* no fixture mutation

Tests must verify that fixture bytes are unchanged after execution.

## Compatibility

Patch 3 remains authoritative for general ARL JSONL fixture validation.

Patch 4 remains authoritative for ARL analysis and graph generation.

Patch 13 is authoritative only for deterministic hash-chain tamper-detection
testing.

The initial Patch 13 implementation must not modify:

* existing Patch 3 fixture behavior
* existing Patch 4 graph behavior
* the existing runtime ARL schema
* existing runtime ARL producers
* existing runtime verify-report semantics
* the existing analyzer fixture
* existing Patch 6 through Patch 12 authorization boundaries

The initial implementation must not require changes to:

```text
scripts/tasukeru_arl_analyzer.py
```

Analyzer integration, if later required, must be separately reviewed.

## Integrity versus authenticity

Patch 13 verifies internal hash-chain consistency.

It provides evidence of:

* accidental corruption
* incomplete modification
* stale hash values
* broken row linkage
* row deletion
* row reordering
* partial content tampering

Patch 13 does not prove:

* who created the ARL
* when the ARL was created
* that the first stored copy was trustworthy
* that an attacker did not recompute the entire non-keyed chain
* that the ARL came from an authenticated system

A party with write access can modify every affected row and recompute an
entire non-keyed chain.

Therefore, Patch 13 must not claim cryptographic authenticity.

## Human authority

Verification evidence does not authorize:

* repair
* replacement
* deletion
* commit
* push
* pull-request creation
* merge
* deployment

A failed integrity check requires human review.

The final decision remains with the Human Owner.

## Acceptance criteria

Patch 13 implementation is acceptable only when all of the following are
true:

1. T1 returns `CHAIN_VALID`.
2. T2 through T7 return `TAMPER_DETECTED`.
3. All required primary reason codes are present.
4. Seven of seven cases pass their expected conditions.
5. Six of six expected tamper cases are detected.
6. No tampered fixture returns `CHAIN_VALID`.
7. The valid fixture has zero integrity errors.
8. The valid fixture head hash matches the manifest.
9. Output counts are internally consistent.
10. Repeated runs produce byte-identical artifacts.
11. Fixture bytes remain unchanged.
12. No HMAC or authenticity claim is made.
13. No secret is introduced.
14. No network call is made.
15. No external AI service is called.
16. No automatic correction occurs.
17. No automatic repository write occurs.
18. Local tests pass.
19. `git diff --check` passes.
20. Human review remains required.

## Scenario summary

| Case                     | Expected outcome  | Required primary reason   |
| ------------------------ | ----------------- | ------------------------- |
| T1 valid chain           | `CHAIN_VALID`     | `ARL_CHAIN_VALID`         |
| T2 content changed       | `TAMPER_DETECTED` | `ARL_ROW_HASH_MISMATCH`   |
| T3 chain hash changed    | `TAMPER_DETECTED` | `ARL_CHAIN_HASH_MISMATCH` |
| T4 previous hash changed | `TAMPER_DETECTED` | `ARL_PREV_HASH_MISMATCH`  |
| T5 final content changed | `TAMPER_DETECTED` | `ARL_ROW_HASH_MISMATCH`   |
| T6 rows reordered        | `TAMPER_DETECTED` | `ARL_SEQUENCE_MISMATCH`   |
| T7 row deleted           | `TAMPER_DETECTED` | `ARL_SEQUENCE_MISMATCH`   |

## Known limitations

Patch 13 is limited to synthetic fixture-based verification.

It does not:

* authenticate an ARL producer
* protect a secret key
* sign a head hash
* anchor a head hash externally
* prevent complete chain regeneration
* inspect historical artifacts automatically
* repair a damaged chain
* identify the person who performed a modification
* establish legal non-repudiation
* create a production audit-storage system

## Future work

Future separately reviewed patches may consider:

* HMAC-based verification
* detached digital signatures
* external head-hash anchoring
* authenticated provenance
* signed verification manifests
* cross-artifact head-hash comparison
* retention and archival policy
* incident-specific integrity evidence bundles

Future work does not authorize secrets, external services, automatic repair,
automatic repository writes, merge, or deployment.
