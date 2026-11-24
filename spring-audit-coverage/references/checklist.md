# What an audit record must contain

Use this as the review checklist. If a record is missing any of the first five fields,
it will not survive an audit.

## Required fields

| Field | Why an auditor asks for it |
|---|---|
| **Who** | Principal, user id, service account. "Someone" is not an answer. |
| **What** | The business operation, not the URL. "Policy issued", not "POST /v1/policies". |
| **When** | Timestamp with timezone, from a single clock source. |
| **Outcome** | Success or failure, with the failure reason. Failed attempts matter most. |
| **Correlation id** | Ties one user action across every service it touched. |

## Strongly recommended

| Field | Why |
|---|---|
| **Before / after values** | For changed records — proves what actually changed. |
| **Source** | Channel: mobile, web, batch, API client. |
| **Actor IP and user agent** | Inbound only. Useful in dispute investigations. |
| **Trace id** | OpenTelemetry or equivalent, so audit and logs line up. |

## Never record

- Passwords, tokens, API keys, session ids
- Full card numbers, CVV, bank account numbers
- Raw document contents, uploaded files, email bodies
- Anything you would not want printed in a regulator's office

Mask before the record is built, not before it is displayed. A record that is stored
with the card number and masked in the UI has still stored the card number.

## Retention

Audit records are usually kept longer than operational logs — commonly five to seven
years in financial services, and often write-once. Decide the retention period before
building the sink, because append-only storage and a "delete after 30 days" policy are
not compatible.

## Failure handling

An audit write that fails must not silently vanish:

- publish to a durable queue or a local spool file
- alert on sustained publish failure
- never swallow the exception with an empty catch

An audit trail with invisible gaps is worse than no audit trail, because it creates
false confidence.

## The question to ask

For every audited operation, ask: *"If a regulator asked who did this and when, could I
answer from the audit table alone, without reading application logs?"*

If the answer is no, the record is incomplete.
