# What each mistake costs, and what good looks like

## L1 — personal data or a secret in the log

Log files are readable by anyone with host access, shipped to third-party aggregators, and
retained for months. A card number written on Tuesday is a card number in every backup taken
since.

What good looks like: log the identifier, not the value.

```java
log.info("card charged, last4={}, amount={}", card.last4(), amount);
```

Masking belongs at the call site. Masking in a log viewer leaves the raw value in the file.

## L2 — `log.error(e.getMessage())`

The one line that explains the failure throws away the explanation.

```java
// loses the trace and the cause chain
log.error("transfer failed: " + e.getMessage());

// keeps both
log.error("transfer failed for transferId={}", id, e);
```

This is the highest-value fix in the list: one argument, and the next incident is diagnosed
from the log instead of from a debugger.

## L3 — logged and rethrown

Every layer logs the same exception as it unwinds, so the log shows the same failure four
times and the original cause is buried under three wrappers.

Rule: catch where you can act. Log where it is handled — the top, once.

## L4 — a log call inside a loop

A batch of 50,000 records produces 50,000 lines, the useful ones scroll out of the window,
and the aggregator bills for the volume.

```java
// one line per batch
log.info("processed {} of {} records", done, total);
```

## L5 — string concatenation

The message is built whether or not the level is enabled, and the values cannot be searched
as separate fields.

```java
log.info("user {} deleted document {}", userId, documentId);   // not "user " + userId
```

## L6 — no correlation id

Without one, two concurrent requests interleave in the file and the timeline is
reconstructed by guessing.

At the edge:

```java
MDC.put("correlationId", incoming != null ? incoming : UUID.randomUUID().toString());
try { chain.doFilter(req, res); } finally { MDC.remove("correlationId"); }
```

In the pattern: `%X{correlationId}`. Forward the header on outbound calls, or the trail stops
at the service boundary.

## L7 — whole request body

The request body is the most sensitive object in the system. It also changes shape without
notice, so the log becomes an unbounded record of whatever a client sent.

Name the fields. If you need the shape for debugging, log the class name and the field
count, not the contents.

## The test that matters

Take one log file from production and answer, without opening anything else:

1. What did request `abc-123` do, in order?
2. What failed, and where in the stack?
3. Whose data was it?

If any answer requires guesswork, the logging is not done, whatever the code looks like.
