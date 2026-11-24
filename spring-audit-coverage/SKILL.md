---
name: spring-audit-coverage
description: Audit a Spring Boot codebase for missing audit logging on regulated operations — money movement, customer data, document handling, deletes. Use when the user asks whether audit logging is complete, needs evidence for a compliance or security review, wants traceability of who changed what, or asks to add audit trails to existing controllers and services.
summary: Scans a Spring Boot repo and lists every controller endpoint with no audit logging, ranked by blast radius - money movement first, then customer identity, then documents - and proposes the lightest fix for the worst one. Use when asked whether audit logging is complete, or to add audit trails.
version: 1.0.0
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
python scripts/scan.py <repo-root>
```

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

If audit happens somewhere central, say so and stop. Do not pad the report with false
gaps — a wrong gap report destroys trust faster than a missing one.

### 3. Rank the gaps

Order by blast radius, not by file name:

1. **Money movement** — transfers, payments, refunds, payouts, balance changes
2. **Customer identity** — KYC, profile, account changes, login and permission changes
3. **Documents** — upload, download, delete, share
4. **Everything else** — reads, lookups, configuration

### 4. Propose before rewriting

For each gap, state the operation, the actor, and what an auditor would want to see.
Then offer the change. Read `references/patterns.md` for the four implementation
patterns and pick the lightest one that fits the codebase.

Never silently refactor a controller. Show the diff, explain the choice, let the user
decide.

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

Then a short "what I would change first" list — three items maximum.
