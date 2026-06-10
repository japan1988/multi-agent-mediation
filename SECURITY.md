# Security Policy

## Purpose

This project is a local research and educational test bench for multi-agent orchestration, advisory review, audit logging, checkpoint behavior, and human-in-the-loop safety boundaries.

It is not a production security product, autonomous enforcement system, vulnerability scanner, exploit framework, compliance tool, or safety certification system.

Security-related outputs in this repository are intended to support defensive review, maintainability, traceability, and human decision-making.

## Supported use

Use this repository only in local, authorized, defensive, and educational contexts.

Appropriate use includes:

* reviewing repositories that you own or are explicitly authorized to review
* studying local-only multi-agent orchestration behavior
* testing advisory-only review workflows
* checking whether findings remain separate from automatic execution
* studying fail-closed behavior, audit logs, checkpoints, and human-review routing
* preparing safe remediation guidance without automatic application

## Prohibited use

Do not use this repository or its tools for:

* unauthorized vulnerability discovery
* offensive reconnaissance
* exploitation of third-party systems, services, or code
* credential, token, or secret harvesting
* scanning repositories, systems, networks, or services without permission
* generating or validating exploit steps against real targets
* bypassing access controls, rate limits, or security boundaries
* publishing sensitive findings without responsible disclosure
* automating external security enforcement without explicit human authorization
* converting advisory simulations into attack tooling

## Advisory-only boundary

The project must remain advisory-only by default.

The repository and its workflows do not authorize:

* automatic fixes
* automatic remediation application
* automatic branch creation
* automatic pull request creation
* automatic commits
* automatic pushes
* automatic merges
* automatic deployment
* automatic external scanning
* exploit execution
* real-world system control

Any externally impactful action must remain blocked, prohibited, or explicitly human-review gated.

## Security review output policy

Public security-related outputs should avoid offensive detail.

Public comments, reports, and documentation should not include:

* exploit payloads
* attack commands
* offensive reproduction steps
* step-by-step exploitation instructions
* third-party target exploitation details
* raw secrets, tokens, credentials, or personal data

Security-related findings should focus on:

* affected file and line
* defensive reason for review
* expected safety or maintainability impact
* safe remediation direction
* whether human review is required

## Reporting a vulnerability

If you believe this repository contains a security issue, please report it responsibly.

Recommended report contents:

* affected file or component
* short description of the issue
* why it matters defensively
* minimal safe reproduction context, if applicable
* suggested safe remediation direction
* whether the issue may expose secrets, personal data, or external side effects

Do not include exploit payloads, offensive instructions, or sensitive data in public issues or pull requests.

If a report involves a real secret, credential, token, personal data, or a third-party target, do not post the raw value publicly. Mask the value and use an appropriate private disclosure path.

### Response expectations

This project is maintained on a best-effort basis.

Because maintainer availability may vary, immediate response or remediation cannot be guaranteed. Security reports will be reviewed when possible, with priority given to issues that may affect repository safety, disclosure of sensitive information, or misuse of the project outside its intended local-only, defensive, and advisory-only scope.

If a report involves an urgent risk, exposed secret, credential, personal data, or a third-party target, do not post sensitive details publicly. Use an appropriate private disclosure path and include only masked or minimal information in public channels.

## Handling of secrets and personal data

This repository should not contain real secrets, credentials, tokens, personal data, or confidential operational data.

When reviewing or preparing examples:

* use placeholder values only
* avoid realistic secret-looking strings when possible
* mask sensitive values in reports
* do not commit production keys or credentials
* do not process real personal or confidential data in simulations

Example placeholders should be clearly invalid, such as:

```text
[REDACTED_EXAMPLE_SECRET]
example-token-not-valid
placeholder-api-key
```

## Scope of security simulations

Security-oriented simulations in this repository are limited to defensive, local-only, and advisory-only behavior.

They may model:

* read-only static audit authorization
* candidate finding records
* mediation and human-review routing
* non-executing draft remediation proposal records
* bounded isolated-verification authorization records
* separation between advice, execution, application, merge, and close

They must not be expanded into:

* exploit execution
* external scanning
* external system access
* automatic remediation
* automatic application
* automatic merge
* autonomous security enforcement
* exploit validation against real targets

## Human review requirement

When behavior is uncertain, risky, inconsistent, or externally impactful, the workflow should stop or request human review.

Human review is required before any action that could:

* modify repository files
* expose sensitive information
* affect external systems
* publish security findings
* apply remediation
* merge code
* change policy or license semantics
* alter safety boundaries

## No production guarantee

This repository does not provide:

* production safety guarantees
* complete vulnerability coverage
* legal, medical, financial, regulatory, or compliance advice
* assurance that a repository or system is secure
* authorization to scan or test third-party targets

A clean advisory result means only that no configured finding was reported within the tested local scope and assumptions. It is not proof of safety.

## Maintainer guidance

When reviewing security-related changes, maintainers should check:

* whether the change remains local-only and advisory-only
* whether human review gates remain intact
* whether external side effects remain blocked or gated
* whether findings avoid offensive detail
* whether examples avoid real secrets or personal data
* whether documentation accurately describes limitations
* whether tests preserve fail-closed and no-auto-apply behavior

If a change weakens these boundaries, treat it as requiring human review before merge.
