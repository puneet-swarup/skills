# Agensi submission sheet — spring-logging-hygiene

Generated from `listings/spring-logging-hygiene.md` and the skill frontmatter.
Every field below is the exact text to paste. Nothing to look up.
Regenerate with `python build.py agensi spring-logging-hygiene`.

| # | Field | Value |
|---|---|---|
| 1 | ZIP | see below |
| 2 | Agensi tools | Skip. No image, video, voice or live-data service. |
| 3 | Logo | spring-logging-hygiene/icon.png |
| 4 | Name | spring-logging-hygiene |
| 5 | Summary | see below |
| 6 | Description | see below |
| 7 | Demo — what the user asks | see below |
| 8 | Demo — what they get back | see below |
| 9 | Compatibility note | see below |
| 10 | Pricing | Free. |
| 11 | Categories | see below |
| 12 | Tags and use cases | see below |
| 13 | Permissions | see below |
| 14 | Limitations and FAQ | see below |
| 15 | Screenshots and video | Skip. |
| 16 | Docs link | Leave empty. Never a private repo. |

## 1. ZIP

````
spring-logging-hygiene.zip
https://github.com/puneet-swarup/skills/releases/download/current/spring-logging-hygiene.zip
````

## 2. Agensi tools

````
Skip. No image, video, voice or live-data service.
````

## 3. Logo

````
spring-logging-hygiene/icon.png
````

## 4. Name

````
spring-logging-hygiene
````

## 5. Summary

````
Reviews Java logging for seven mistakes that leak personal data or lose the stack trace - PII in log statements, log.error(getMessage()), log-then-rethrow, log calls in loops, concatenation, no correlation id, whole request bodies logged. Use before a security review, or when logs were useless during an outage.
````

## 6. Description

````
Logs are the only record of what happened that you read while something is on fire. The
mistakes below are invisible in review, because each one looks responsible at the time.

`log.error(e.getMessage())` reads like careful error handling and throws away the stack
trace. Logging a whole request body reads like thoroughness and writes a customer's data to
a file with a long retention.

### What it does

Seven checks, each with a file and line:

- Personal data or a secret in a log statement — card numbers, account numbers, Aadhaar, PAN, tokens
- `log.error(e.getMessage())` — the stack trace and cause chain discarded
- Logged and then rethrown — the same failure recorded at every layer
- A log call inside a loop — one line per record, and the useful one scrolls away
- String concatenation instead of placeholders — built whether or not the level is enabled
- No correlation id anywhere — two concurrent requests are inseparable in the file
- A whole request body or DTO passed to the logger

### How it works

It reads the log statements themselves, not file names, and looks at what is passed in. PII
is caught through getters as well as field names, because that is how it usually arrives:
`log.info("card {}", card.getCardNumber())`.

The correlation-id check is repository-wide, because one MDC filter at the edge serves every
call site — so it stays quiet on a codebase that has one, and says so plainly when none
exists.

### Where it stops

- Java with slf4j-style loggers. Not Kotlin, not `System.out`, not a framework configured
  entirely in XML.
- It cannot see whether the logger is disabled in production, or whether a shipper filters
  the line before anyone reads it.
- It does not know your retention policy or your regulatory basis — only whether the value
  reaches the file.

---
````

## 7. Demo — what the user asks

````
We have a security review next week. Review our logging and tell me what
would embarrass us.
````

## 8. Demo — what they get back

````
**What the agent did**

Ran `python scripts/scan.py .`, then asked for one real log file and tried to answer three
questions from it alone: what a single request did, what failed, and whose data it was.

**Output (trimmed)**

```
| # | Check | Severity | Where | Problem |
|---|---|---|---|---|
| 1 | L1 | high | `PayService.java`:13 | log statement carries personal data or a secret: cardnumber |
| 2 | L2 | high | `PayService.java`:17 | log.error passes getMessage() instead of the exception |
| 3 | L3 | medium | `PayService.java`:17 | failure is logged and then rethrown |
| 4 | L4 | medium | `PayService.java`:24 | log call inside a loop |
| 5 | L6 | medium | `(repository)`:1 | no correlation id anywhere in the codebase |
```

**What the agent then said**

> The two that would embarrass you are L1 and L6. Line 13 writes a card number into a file
> that rotates slowly and sits in every backup since — that is a finding, not a style note.
>
> L6 is worse in practice: with no correlation id, you cannot reconstruct a single request
> from the logs at all, so the other findings barely matter during an incident.
>
> L2 costs you nothing to fix and buys the most: pass the exception as the last argument and
> the next outage is diagnosed from the log instead of a debugger.

---
````

## 9. Compatibility note

````
```
Requires Python 3.8+. Standard library only, no dependencies, no network access. Reads Java sources using slf4j-style loggers.
```

---
````

## 10. Pricing

````
Free.
````

## 11. Categories

````
Up to 3 of the 32 on the form. Closest developer-tools first, then security or compliance. Use the form's own names.
````

## 12. Tags and use cases

````
logging, java, slf4j, spring boot, pii, security, observability, correlation id, soc 2, incident response
logging review before release, security review evidence, incident postmortem follow-up, reduce log noise, pii in logs audit
````

## 13. Permissions

````
Read what the scan detected. Expect: reads local files, no network.
````

## 14. Limitations and FAQ

````
**Does it read my log files?**
No. It reads source. It will tell you to read one real log file yourself, because only that
shows whether the output is usable.

**Will it work with log4j or java.util.logging?**
The checks look for slf4j-style calls (`log.info(...)`). A codebase that uses a different
facade consistently will be missed.

**Does it change my log levels?**
No. Level choices depend on production volume, which a scanner cannot see.

**Why is this free?**
Because fixing it is the separate, harder job — masking at the boundary, correlation
propagation, and a pattern that survives an incident.
````

## 15. Screenshots and video

````
Skip.
````

## 16. Docs link

````
Leave empty. Never a private repo.
````

