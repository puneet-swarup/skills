# spring-migration-review

Reviews Flyway and Liquibase migrations for the seven statements that lose data or lock a
table in production.

A migration is the one change you cannot roll back by deploying the previous version. Code
rolls back. A dropped column does not.

## Install

```bash
cp -r spring-migration-review ~/.claude/skills/
```

Then ask: *"Review these migrations before we deploy"* or *"why did this migration lock the
database?"*

## Run the scanner on its own

Python 3.8+. Standard library only, no network access.

```bash
python scripts/scan.py /path/to/repo
python scripts/scan.py . --json
```

## What it checks

| Check | Severity | Finds |
|---|---|---|
| M1 | high | DROP TABLE, DROP COLUMN, TRUNCATE — irreversible |
| M2 | high | column type change — rewrites and locks the table |
| M3 | high | ADD COLUMN NOT NULL with no default |
| M4 | medium | CREATE INDEX without CONCURRENTLY on an existing table |
| M5 | high | UPDATE or DELETE with no WHERE |
| M6 | medium | constraint added to an existing table |
| M7 | medium | Liquibase changeset with no rollback |

Real output against a migration that does all of it:

```
| # | Check | Severity | Where | Problem |
|---|---|---|---|---|
| 1 | M1 | high | `V10__cleanup.sql`:2 | DROP TABLE is irreversible |
| 2 | M1 | high | `V10__cleanup.sql`:4 | DROP COLUMN is irreversible |
| 3 | M2 | high | `V10__cleanup.sql`:6 | column type change rewrites the whole table |
| 4 | M3 | high | `V10__cleanup.sql`:8 | ADD COLUMN NOT NULL with no default |
| 5 | M4 | medium | `V10__cleanup.sql`:10 | CREATE INDEX without CONCURRENTLY on an existing table |
| 6 | M5 | high | `V10__cleanup.sql`:12 | UPDATE or DELETE with no WHERE clause |
| 7 | M6 | medium | `V10__cleanup.sql`:14 | constraint added to an existing table |
```

A new table created in the same migration, with its index, is quiet — the risk is only on
tables that already hold data.

## What's inside

```
SKILL.md                       workflow, rules, where it stops
scripts/scan.py                the seven checks
references/what-goes-wrong.md  what each statement does to a live table
icon.svg                       icon source
icon.png                       512x512, for the marketplace listing logo
```

The icon files are listing assets and are not part of the distributed zip.

## Where it stops

SQL and Liquibase XML only — not Java-based Flyway migrations, Alembic or Rails. It does not
know your table sizes, and it cannot tell which migrations have already run: that is in
`flyway_schema_history`, and it decides whether a finding can be fixed by editing or needs a
new migration.

## Licence

MIT. Use it commercially, fork it, change it.
