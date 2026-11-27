# Agensi submission sheet — spring-migration-review

Generated from `listings/spring-migration-review.md` and the skill frontmatter.
Every field below is the exact text to paste. Nothing to look up.
Regenerate with `python build.py agensi spring-migration-review`.

| # | Field | Value |
|---|---|---|
| 1 | ZIP | see below |
| 2 | Agensi tools | Skip. No image, video, voice or live-data service. |
| 3 | Logo | spring-migration-review/icon.png |
| 4 | Name | spring-migration-review |
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
spring-migration-review.zip
https://github.com/puneet-swarup/skills/releases/download/current/spring-migration-review.zip
````

## 2. Agensi tools

````
Skip. No image, video, voice or live-data service.
````

## 3. Logo

````
spring-migration-review/icon.png
````

## 4. Name

````
spring-migration-review
````

## 5. Summary

````
Reviews Flyway and Liquibase migrations for seven statements that lose data or lock a table in production - dropped columns, type changes, NOT NULL without a default, non-concurrent indexes, unbounded deletes. Use before deploying a schema change, or when a migration has already caused a lock.
````

## 6. Description

````
A migration is the one change you cannot roll back by deploying the previous version. Code
rolls back. A dropped column does not.

This skill reviews a Flyway or Liquibase changelog and reports the statements that lose data
or lock a table, before they run.

### What it does

Seven checks, each with a file and line:

- `DROP TABLE`, `DROP COLUMN` or `TRUNCATE` — the data is gone, and the rollback path went with it
- A column type change — rewrites and locks the whole table
- `ADD COLUMN NOT NULL` with no default — fails or rewrites on existing rows
- `CREATE INDEX` without `CONCURRENTLY` on a table that already holds data
- `UPDATE` or `DELETE` with no `WHERE` — the entire table
- A constraint added to an existing table — validates every row while holding a lock
- A Liquibase changeset with no rollback

### How it works

It reads the migration files and splits them into statements, so it knows whether a table
was created in the same migration. That matters: an index on a brand-new table is harmless,
and the same index on a table with ten million rows is an outage. New-table migrations come
back quiet.

It also separates what has already run from what has not, because that changes the fix
entirely. A migration already applied cannot be edited — Flyway and Liquibase record a
checksum — so the answer is a new migration that compensates, not an edit to the old one.

### Where it stops

- SQL and Liquibase XML only. Not Java-based Flyway migrations, Alembic, Rails or raw JDBC
  calls at startup.
- It does not know your table sizes. "Locks the table" is a problem at ten million rows and
  noise at ten.
- It cannot tell which migrations have already run — that is in `flyway_schema_history`, and
  it decides whether a finding is fixable by editing.

---

If a finding needs rewriting rather than just reporting, spring-migration-safe-rewrite produces the safe sequence - expand-contract across releases, batched backfill, CONCURRENTLY handled outside the transaction, and a rollback you have run.

---
````

## 7. Demo — what the user asks

````
We deploy on Thursday. Review these migrations and tell me what could go wrong.
````

## 8. Demo — what they get back

````
**What the agent did**

Ran `python scripts/scan.py .` against the repository, then separated the findings into
migrations already applied and migrations still to run, because only the second group can be
edited.

**Output (trimmed)**

```
| # | Check | Severity | Where | Problem |
|---|---|---|---|---|
| 1 | M1 | high | `V10__cleanup.sql`:2 | DROP TABLE is irreversible |
| 2 | M1 | high | `V10__cleanup.sql`:4 | DROP COLUMN is irreversible |
| 3 | M2 | high | `V10__cleanup.sql`:6 | column type change rewrites the whole table |
| 4 | M3 | high | `V10__cleanup.sql`:8 | ADD COLUMN NOT NULL with no default |
| 5 | M4 | medium | `V10__cleanup.sql`:10 | CREATE INDEX without CONCURRENTLY on an existing table |
```

**What the agent then said**

> Two of these are release blockers, not code smells. `V10` drops `legacy_ref` on the same
> deploy that stops reading it — so if Thursday goes wrong, the rollback runs against a
> schema that no longer has the column. The rollback path and the deploy go out together.
>
> The `NOT NULL` without a default fails outright if `customers` has rows, which it will.
>
> Order it: add `kyc_status` nullable, backfill in batches, deploy code that writes both,
> then constrain it in a separate migration. Drop `legacy_ref` one release later, after
> nothing reads it. The index needs `CONCURRENTLY` and that cannot run inside a Flyway
> transaction — plan it as a separate step or it will fail on deploy.

---
````

## 9. Compatibility note

````
```
Requires Python 3.8+. Standard library only, no dependencies, no network access. Reads .sql migrations and Liquibase XML changelogs from the repository.
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
database migration, flyway, liquibase, sql, postgresql, mysql, schema change, data loss, zero downtime, devops
review a migration before deploy, pre-release schema review, incident review after a lock, flyway changelog check, liquibase rollback check
````

## 13. Permissions

````
Read what the scan detected. Expect: reads local files, no network.
````

## 14. Limitations and FAQ

````
**Does it run the migrations?**
No. It reads the files and reports. Nothing is executed and no database is touched.

**Will it work with Liquibase?**
Yes — XML changelogs, including `<dropColumn>`-style changesets and missing rollback blocks.

**Does it need the database?**
No, and that is also its limit: it cannot see table sizes, which decide whether a lock
matters.

**Why is this free?**
Because the fix is the hard part and it is a separate piece of work. This tells you what
will hurt; rewriting the migration safely needs your table sizes, traffic and rollback plan.
````

## 15. Screenshots and video

````
Skip.
````

## 16. Docs link

````
Leave empty. Never a private repo.
````

