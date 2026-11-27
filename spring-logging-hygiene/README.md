# spring-logging-hygiene

Reviews Java logging for the seven mistakes that leak data or lose the stack trace.

Each one looks responsible in review. `log.error(e.getMessage())` reads like careful error
handling and throws away the trace. Logging a request body reads like thoroughness and writes
a customer's data to a file with a long retention.

## Install

```bash
cp -r spring-logging-hygiene ~/.claude/skills/
```

Then ask: *"Review our logging before the security review"* or *"why was last week's
incident so hard to diagnose?"*

## Run the scanner on its own

```bash
python scripts/scan.py /path/to/repo
python scripts/scan.py . --json
```

## What it checks

| Check | Severity | Finds |
|---|---|---|
| L1 | high | personal data or a secret in a log statement |
| L2 | high | `log.error(getMessage())` — stack trace discarded |
| L3 | medium | logged and then rethrown |
| L4 | medium | log call inside a loop |
| L5 | low | string concatenation instead of placeholders |
| L6 | medium | no correlation id anywhere |
| L7 | medium | whole request body or DTO logged |

Tested on real code: a deliberately bad service triggers all seven, and a logging library
comes back with `getMessage()` calls, log-in-loop and concatenation — genuine findings, not
noise.

## What's inside

```
SKILL.md                       workflow, rules, where it stops
scripts/scan.py                the seven checks
references/what-goes-wrong.md  what each costs, and what good looks like
spring-logging-hygiene-icon.svg  icon source
spring-logging-hygiene-icon.png  512x512, for the marketplace listing logo
```

The icon files are listing assets and are not part of the distributed zip.

## Where it stops

Java with slf4j-style loggers. It cannot see whether the logger is disabled in production, or
whether a shipper filters the line before anyone reads it.

## Licence

MIT. Use it commercially, fork it, change it.
