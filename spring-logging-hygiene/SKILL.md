---
name: spring-logging-hygiene
description: Review Java logging for the mistakes that leak personal data, throw away the stack trace, or make an incident unreadable — PII and secrets in log statements, log.error(getMessage()), logging then rethrowing, log calls inside loops, string concatenation instead of placeholders, missing correlation ids, and whole request bodies written to the log. Use when asked to review logging, prepare for a security or SOC 2 review, investigate why an incident was hard to diagnose, or clean up noisy logs before a release.
summary: Finds the seven logging mistakes that leak data or lose the stack trace, each with a file and line, and says what each one costs during an incident. Use before a security review, or when logs were useless during an outage.
version: 1.0.0
tags: logging, java, slf4j, spring boot, pii, security, observability, correlation id, soc 2, incident response
keywords: logging review, pii in logs, log masking, structured logging, correlation id, mdc, log level, stack trace, noisy logs
use_cases: logging review before release, security review evidence, incident postmortem follow-up, reduce log noise, pii in logs audit
---

# Logging review

Logs are the only record of what happened that you read while something is on fire. The
mistakes below are invisible in review because each one looks responsible at the time.

## Workflow

### 1. Scan

```
python /absolute/path/to/spring-logging-hygiene/scripts/scan.py /absolute/path/to/repo
```

Both paths absolute — your working directory is the user's project, not this skill. The same
applies to every `references/...` file below.

Seven checks, each with a file and line:

| Check | Finds |
|---|---|
| L1 | personal data or a secret in a log statement |
| L2 | `log.error(e.getMessage())` — the stack trace is discarded |
| L3 | logged and then rethrown — the same failure recorded twice |
| L4 | a log call inside a loop |
| L5 | string concatenation instead of placeholders |
| L6 | no correlation id anywhere |
| L7 | a whole request body or DTO passed to the logger |

### 2. Read one real log file

The scanner reads code. Only a real log tells you whether the code produces something
usable. Ask for a log file from production and try to answer: *what did this one request
do, in order, and what failed?*

If you cannot answer that from the file, the findings are symptoms of a bigger problem than
any single line.

### 3. Say what it costs during an incident

"PII in logs" is a compliance point. What changes behaviour is: *during the last incident,
this line printed the exception message and not the stack trace, so the cause was found
forty minutes later than it should have been.*

### 4. Fix in this order

1. **Secrets and PII first.** Not a style issue — a leak with a long retention.
2. **The stack trace.** One argument added; the biggest diagnostic gain per keystroke.
3. **Correlation id.** Without it, nothing else is joinable.
4. **Levels and loops.** Volume, not correctness.
5. **Placeholders.** Cheap, do it while you are in the file.

### 5. State what you did not change

Log levels are a judgement about production volume, and the right level depends on how much
traffic the service sees. Do not silently demote `info` to `debug` in a payment path.

## Rules

- **Never log a secret or a full credential.** Not the token, not the header, not the first
  eight characters.
- **Never log a card number, account number, Aadhaar, PAN or SSN unmasked.** Mask at the
  call site, not in the viewer.
- **Never log a whole request body.** Name the fields.
- **Never pass `getMessage()` where the exception belongs.** Pass the throwable as the last
  argument.
- **Never log and rethrow in the same block.** Log where it is handled.
- **Never claim logs are fine because they are structured.** Structure without a correlation
  id is still unjoinable.
- **Say when logging is already good.** A service that logs one line per request with a
  correlation id and no PII needs no work, and saying so is a complete answer.

## Where it stops

- Java with slf4j-style loggers. Not Kotlin, not `System.out`, not a logging framework
  configured entirely in XML.
- It cannot see whether the logger is disabled in production, or whether a log shipper
  filters the line before anyone reads it.
- It does not know your retention policy or your regulatory basis — only whether the value
  reaches the file.
- Log volume and level choices depend on traffic. That is a judgement, not a static fact.
