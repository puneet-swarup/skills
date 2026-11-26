---
name: spring-audit-coverage
description: Audit a Spring Boot codebase for missing audit logging on regulated operations — money movement, customer data, document handling, deletes. Use when the user asks whether audit logging is complete, needs evidence for a compliance or security review, wants traceability of who changed what, or asks to add audit trails to existing controllers and services.
summary: Scans a Spring Boot repo and lists every controller endpoint with no audit logging, ranked by blast radius - money movement first, then customer identity, then documents - with what an auditor asks about each gap. Use when asked whether audit logging is complete, or to find out which endpoints have no audit trail.
version: 1.0.5
tags: spring boot, java, audit logging, audit trail, compliance, soc 2, pci dss, api security, spring security, code review
keywords: audit coverage, audit logging gaps, spring boot audit, endpoint inventory, pii masking, traceability, java, spring mvc
use_cases: audit logging review, compliance evidence, soc 2 readiness, pci dss audit trail, pre-release code review, bfsi and insurance audit
---

# Spring Boot audit coverage

Find the endpoints that change regulated data and have no audit trail, then fix them in
the order that matters.

## When to use this

- "Is our audit logging complete?"
- "We have a security or compliance review next week — what's missing?"
- "Add audit logging to these endpoints."
- Any Spring Boot service handling money, customer records, documents or deletes.

## Workflow

### 1. Scan

Run the scanner against the repository root:

```
python /absolute/path/to/spring-audit-coverage/scripts/scan.py /absolute/path/to/repo
```

Substitute both paths. Your working directory is the user's project, not this skill, so
`scripts/scan.py` on its own will not resolve — and a repo that happens to have its own
`scripts/` directory turns that into a confusing "No such file". Use the absolute path.
The same applies to every `references/...` file below.

It writes a markdown report to stdout. Read it before doing anything else.

### 2. Read the report honestly

The scanner is a heuristic, not a verdict. It reads each controller method and looks for
an audit call or an audit annotation inside that method. An endpoint marked "no" may
still audit through a base class, a servlet filter, a Spring Security event listener or
an aspect defined elsewhere.

The report lists every central candidate it found. If any of them mention auditing, the
gaps are marked **unconfirmed** instead of "no" — that is your cue to resolve them before
reporting anything. Confirm by hand:

- read the `@Aspect` pointcut, and check it matches the package you care about
- read `addPathPatterns` / `excludePathPatterns` on the interceptor or filter
- check for a shared base controller
- check `application.yml` for an audit starter or logging configuration

If audit happens somewhere central, say so and stop. "Stop" means: report where audit
happens, name the endpoints it covers and any it excludes, and do not propose code. A
one-paragraph answer is a complete deliverable when the answer is "already covered".
Do not pad the report with false gaps — a wrong gap report destroys trust faster than a
missing one.

### 3. Rank the gaps

Order by blast radius, not by file name:

1. **Money movement** — transfers, payments, refunds, payouts, balance changes
2. **Customer identity** — KYC, profile, account changes, login and permission changes
3. **Documents** — upload, download, delete, share
4. **Everything else** — reads, lookups, configuration

### 4. State what to fix first, and stop there

For the top gap, state three things: the operation, the actor, and the question an auditor
would ask about it. That is the deliverable — diagnosis, with evidence.

**Do not write the implementation.** Choosing the wiring, getting the transaction boundary
right, masking before the sink and proving it with a test is a separate job, and getting it
half-right is worse than not starting. Name the pattern that applies — an explicit call at
the service state change, an aspect, a filter, or a transactional outbox — and say that the
fix and its verification are a different piece of work. If the user wants the implementation
done, that is where a dedicated skill or a careful hand-written change belongs.

What matters is that they can act on the report: a ranked list, a file and line per row, and
the reason each gap is a problem rather than a number.

### 5. What a record must contain

Read `references/checklist.md`. The minimum is: who, what, when, outcome, correlation
id — and no unmasked personal data.

## Rules

- Never log secrets, tokens, full card numbers or raw document contents. Mask first.
- Never make the audit write block the transaction. Audit asynchronously.
- Never claim coverage you have not verified by reading the code.
- If the codebase already audits centrally, say so plainly — that is a good answer.

## Output format

Report as a table, worst first:

| Endpoint | Method | Operation | Audited? | Risk |
|---|---|---|---|---|

The Risk column carries the scanner's category and score verbatim, for example
`medium (documents, score 35)`. Do not invent a scale.

Then a short "what I would change first" list — three items maximum.

**Non-HTTP gaps get their own section.** The scanner reports scheduled jobs and Feign
clients separately because they are not endpoints. A `@Scheduled` job that creates
money-adjacent records has no caller to audit and no row in the table above; list those
under a "background work" heading, or they get silently dropped.
