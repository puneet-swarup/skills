# Agensi submission copy — spring-audit-coverage

Copy-paste source for the listing form at `agensi.io/dashboard/submit`. The summary, tags,
keywords and use cases also live in `SKILL.md` frontmatter, which the form reads
automatically — this file is for the fields it does not read, and for keeping the wording
under version control.

---

## Name

```
spring-audit-coverage
```

## Summary (max 300 chars — 294)

```
Scans a Spring Boot repo and lists every controller endpoint with no audit logging, ranked by blast radius - money movement first, then customer identity, then documents - with the question an auditor asks about each gap. Use when asked whether audit logging is complete, or which endpoints have no audit trail.
```

## Price

Free. No payout method needed for a free listing.

## Categories

The form offers 32 fixed categories and takes up to 3; the first decides the category page.
Pick the closest matches — do not invent names. Likely fits: a developer-tools or code-review
category first, then security or compliance if offered.

## Tags and use cases

```
spring boot, java, audit logging, audit trail, compliance, soc 2, pci dss, api security, spring security, code review
audit logging review, compliance evidence, soc 2 readiness, pci dss audit trail, pre-release code review, bfsi and insurance audit
```

## Compatibility note

```
Requires Python 3.8+. Standard library only, no dependencies, no network access. Reads local Java sources; works on any Spring Boot or Spring MVC repository. Nothing is installed and nothing leaves the machine.
```

---

## Description (markdown)

Most Spring Boot services log some calls and not others, and nobody knows which. The gap
is usually the endpoint that deletes a document or moves money.

This skill finds those endpoints and ranks them, so you fix the one that matters first
rather than rewriting twelve controllers.

### What it does

It scans a Spring Boot repository and reports every controller endpoint with no audit
logging, worst first:

- **Money movement** — payments, transfers, refunds, invoices, claims, renewals
- **Customer identity** — authentication, profiles, consent, KYC, roles
- **Documents** — upload, download, delete, export
- **Everything else** — reads, lookups, configuration

Every row carries the file and line, so "not audited" is a claim you can check instead of
one you have to trust.

### How it works

The scanner reads each controller method, not each file. A file that mentions
`AuditService` in a comment is not an audited file, and reporting it as one is how a
service ends up with a money-movement endpoint nobody records.

It strips comments and masks string literals before parsing, so a commented-out audit call
does not count and a path like `"/{id}"` is not mistaken for a code block. It also looks
for audit infrastructure in one place — aspects, filters, interceptors, controller advice,
audited base classes — and if any of it mentions auditing, it marks the gaps `unconfirmed`
rather than reporting them as fact.

Each gap is stated in the terms an auditor uses — who moved the money, who changed access,
who destroyed the record — with an indicative control mapping (SOC 2, PCI DSS, ISO 27001).
That is what turns a list of endpoints into a reason to act.

It diagnoses. It does not write the implementation, because a half-correct audit trail is
worse than none.

### Where it stops

- Regex-based Java parsing, not a compiler. It does not see endpoints defined in Kotlin,
  XML, GraphQL resolvers or a `RouterFunction` bean.
- Audit done in a gateway, proxy or database trigger is invisible to it.
- "Audited" means the method calls an audit sink or carries an audit annotation. It does
  not mean the record is complete — the bundled checklist covers that.
- It does not read `application.yml`, so it cannot tell you whether audit is switched off
  in production.

If your audit logging is already centralised, it will tell you so and stop. That is a
correct answer, not a failure to find work.

---

If the scan finds gaps you need to close, spring-audit-implementation covers the fix: aspect or filter wiring, masking before the sink, and an audit write that survives a rollback.

---

## See it in action

**Request**

```
Is our audit logging complete? Point the scanner at the repo in the current directory
and tell me what to fix first.
```

**What the agent did**

Ran `python scripts/scan.py .` against a Spring Boot service, then read the report and
checked whether the central infrastructure covered the gaps.

**Output (trimmed)**

```
- Java files read: **35**
- Controllers: **5**
- Endpoints found: **8**
- With audit logging in the method: **0**
- **Without audit logging: 8**
| Kind | Where | Audit-aware |

|---|---|---|
| advice | `src/main/java/com/personavault/config/GlobalExceptionHandler.java`:27 | no |
| Endpoint | Method | Operation | Audited? | Risk | What an auditor asks |
|---|---|---|---|---|---|
| `/api/documents/{id}` | DELETE | `deleteDocument()` | no | medium (documents, score 35) | who accessed or destroyed this record - SOC 2 CC7.2, ISO 27001 A.8.15 |
| `/api/documents/upload` | POST | `upload()` | no | medium (documents, score 30) | who accessed or destroyed this record - SOC 2 CC7.2, ISO 27001 A.8.15 |
| `/api/chat/stream` | POST | `stream()` | no | low (other, score 20) | every access to this component is logged - PCI DSS 10.2 |
| `/api/documents` | GET | `listDocuments()` | no | low (documents, score 20) | who accessed or destroyed this record - SOC 2 CC7.2, ISO 27001 A.8.15 |
```

**What the agent then said**

> Eight endpoints, none audited, and the only central component is an exception handler,
> which is not an audit trail — so these are real gaps. Fix `deleteDocument` first: it is
> the only endpoint that destroys a record, and the checklist needs the actor, the document
> id and the outcome. A soft delete that leaves no audit row is indistinguishable from an
> accident.

---

## Limitations and FAQ

**Does it need network access?**
No. It reads local files and prints a report. Nothing is uploaded and no API keys are used.

**Will it work on a multi-module project?**
Yes. Point it at the repository root or at the module containing your controllers.

**Does it change my code?**
No. The scanner only reads. Any code change is proposed for you to review, not applied.

**What if we audit centrally already?**
It reports the central component and marks the gaps `unconfirmed`, then tells you to check
the pointcut or path pattern before treating anything as a gap.

**Which agents can use it?**
Any agent that loads `SKILL.md` skills — Claude Code, Codex, Cursor and similar. It is
plain markdown and standard-library Python.
