# What each statement does to a live table

Read this to judge a finding, not to copy a fix. The right fix depends on table size, write
traffic and your deploy window — a scanner has none of those.

## M1 — DROP TABLE, DROP COLUMN, TRUNCATE

The data is gone and the transaction log will not save you: after the commit, recovery means
a backup, and everything written since that backup is lost too.

What makes this dangerous is not the drop, it is the *timing*. If the previous release still
reads the column, rolling back the deploy fails against a schema that no longer has it. You
have removed the rollback path at the same moment you deployed.

Direction: stop writing first, ship that, then drop in a later release. On a large table,
TRUNCATE takes an exclusive lock — deleting in batches is slower but does not stop the app.

## M2 — column type change

Most engines rewrite the table. On Postgres, `ALTER COLUMN TYPE` takes an ACCESS EXCLUSIVE
lock for the whole rewrite, so reads block as well as writes. Ten million rows is minutes of
outage.

Direction: add a new column of the target type, backfill in batches, switch reads, then drop
the old column — three releases, no lock longer than a batch.

## M3 — ADD COLUMN NOT NULL without a default

On an existing table with rows, this either fails immediately or rewrites the table to fill
the missing values. On Postgres 11+ a *constant* default is cheap; a non-constant one
(`now()`, a subquery) still rewrites.

Direction: add it nullable, backfill, then `SET NOT NULL` — and that last step takes a lock
too, so do it in a separate migration with a short statement timeout.

## M4 — CREATE INDEX without CONCURRENTLY

A plain index build blocks writes to the table for its duration. On a large table that is a
stall, not a pause, and it looks like an outage from the outside.

Direction: `CREATE INDEX CONCURRENTLY`, run outside a transaction — Postgres refuses it
inside one, so it cannot live in a migration that Flyway wraps. That is the awkward part:
it usually means a separate, manually-run step or a migration with transactional DDL
disabled. Say that out loud rather than pretending the tool will do it.

## M5 — UPDATE or DELETE with no WHERE

Every row. There is no undo, and on a large table the statement holds locks while it runs.

Direction: add the WHERE. If the intent really is every row, run it in batches with a
progress table, so it can be stopped.

## M6 — constraint added to an existing table

`ADD CONSTRAINT UNIQUE` builds an index and validates every row while holding an exclusive
lock. `ADD FOREIGN KEY` validates every row too.

Direction: `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` in a separate
statement — the validation takes a weaker lock and does not block writes. For uniqueness,
build a unique index concurrently and attach it.

## M7 — no rollback

Flyway community has no undo, so this is mostly a Liquibase concern: a changeset with no
`<rollback>` cannot be reverted by the tool. When a deployment half-fails, the recovery is a
script written under pressure by whoever is on call.

Direction: write the rollback, or write down the manual step. An undocumented "we'd restore
from backup" is the answer that turns a bad deploy into a bad week.

## The question that decides the severity

> How many rows does this table have in production, and how long does a lock on it stop the
> business?

Ask it before ranking anything. A DROP on an empty table nobody reads is housekeeping; a
DROP on a table with an hour of downtime behind it is an incident.
