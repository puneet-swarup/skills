---
name: spring-migration-review
description: Review database migrations before they run in production and find the statements that lose data or lock a table — DROP TABLE and DROP COLUMN, TRUNCATE, column type changes, NOT NULL added without a default, CREATE INDEX without CONCURRENTLY, UPDATE or DELETE with no WHERE, constraints added to a large table, and Liquibase changesets with no rollback. Use when asked to review a migration, check a Flyway or Liquibase changelog before deploying, explain why a deploy locked the database, or prepare a schema change for a release. Covers Flyway, Liquibase, PostgreSQL and MySQL.
summary: Reviews Flyway and Liquibase migrations for the seven statements that lose data or lock a table in production, each with the cost and the safe direction. Use before deploying a schema change, or when a migration has already caused a lock or a lost column.
version: 1.0.1
tags: database migration, flyway, liquibase, sql, postgresql, mysql, schema change, data loss, zero downtime, devops
keywords: migration review, destructive ddl, drop column, table lock, create index concurrently, expand contract, rollback, changelog
use_cases: review a migration before deploy, pre-release schema review, incident review after a lock, flyway changelog check, liquibase rollback check
---

# Migration review

A migration is the one change that can destroy data and cannot be undone by deploying the
previous version. Code you can roll back. A dropped column you cannot.

## Workflow

### 1. Scan

```
python /absolute/path/to/spring-migration-review/scripts/scan.py /absolute/path/to/repo
```

Both paths absolute — your working directory is the user's project, not this skill. The same
applies to every `references/...` file below.

Seven checks, each with a file and line:

| Check | Finds |
|---|---|
| M1 | DROP TABLE, DROP COLUMN, TRUNCATE — irreversible |
| M2 | column type change — rewrites and locks the table |
| M3 | ADD COLUMN NOT NULL with no default |
| M4 | CREATE INDEX without CONCURRENTLY on an existing table |
| M5 | UPDATE or DELETE with no WHERE |
| M6 | constraint added to an existing table — validates every row under a lock |
| M7 | Liquibase changeset with no rollback |

### 2. Separate what has already run from what has not

This is the first question and it changes everything.

A migration already applied in production **cannot be edited**. Flyway and Liquibase record a
checksum; editing the file makes the next startup fail. The fix is a new migration that
compensates, not an edit to the old one.

So sort the findings into two piles before saying anything: not yet applied (the file can be
changed), and already applied (only a forward migration can help).

### 3. Say what it costs, not what the rule is

"DROP COLUMN is destructive" tells them nothing they didn't know. What they need is: this
column is dropped on Thursday, the deploy takes an exclusive lock, and the previous release
still reads that column — so the rollback path is a restore.

### 4. Name the direction, not the code

`references/what-goes-wrong.md` covers what each statement does to a live table and the
direction that avoids it. That is enough for the team to act. Writing the replacement
migration is a separate job: it needs the table sizes, the traffic window, and a rollback
plan, none of which a scanner has.

### 5. Check the release order

A migration is one step of a deploy, and the order is where most damage happens:

- add the new column, deploy code that writes both, backfill, then deploy code that reads
  the new one, then drop the old
- never ship a migration and the code that depends on it in the same step unless the
  migration is purely additive

## Rules

- **Never edit a migration that has run.** Add a new one.
- **Never drop in the same release that stops using.** One release apart, minimum.
- **Never add NOT NULL without a default to a table with rows.** Nullable, backfill, then
  constrain.
- **Never build an index on a large table without CONCURRENTLY** where the engine supports
  it, and never inside a transaction — Postgres rejects it there.
- **Never assume a rollback exists.** Flyway community has no undo. If the plan is "restore
  from backup", say how long that takes.
- **Say when it is safe.** A purely additive migration on a small table is fine, and saying
  so is as useful as finding a problem.

## Where it stops

- SQL and Liquibase XML only. Java-based Flyway migrations, Alembic, Rails migrations and
  raw JDBC calls at startup are not read.
- It does not know your table sizes. "Locks the table" is a problem at ten million rows and
  noise at ten.
- It cannot tell which migrations have already run — that is in your `flyway_schema_history`
  or `DATABASECHANGELOG` table, and it decides whether a finding is fixable by editing.
- It does not plan the release. Ordering a migration against the code that depends on it is
  a judgement about your deploy, not a static fact.
