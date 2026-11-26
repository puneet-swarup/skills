#!/usr/bin/env python3
"""
Check database migrations for the statements that lose data or lock a table
in production.

Stdlib only. No network. Never writes to the repo.

    python scan.py <repo-root> [--json] [--out FILE]

Reads Flyway and Liquibase migrations: .sql files under a migration directory,
and Liquibase XML/YAML changelogs. Every finding carries a file and line.

Checks:
  M1  DROP TABLE, DROP COLUMN or TRUNCATE - data is gone, restore is the only undo
  M2  a column type change - rewrites and locks the table
  M3  ADD COLUMN NOT NULL with no default - fails or rewrites on existing rows
  M4  CREATE INDEX without CONCURRENTLY on a table that already exists
  M5  UPDATE or DELETE with no WHERE - the whole table
  M6  ADD CONSTRAINT on an existing table - validates every row while holding a lock
  M7  a Liquibase changeset with no rollback
"""

import argparse
import json
import os
import re
import sys

SKIP_DIRS = {".git", "target", "build", "out", "bin", "node_modules", ".idea", ".mvn", ".venv"}
MIGRATION_HINT = re.compile(r"(^|/)(db/migration|migrations?|changelog|changesets?)(/|$)", re.I)
SQL_EXT = (".sql",)
LIQUIBASE_EXT = (".xml", ".yaml", ".yml")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def strip_sql_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "-" and src[i:i + 2] == "--":
            while i < n and src[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if c == "/" and src[i:i + 2] == "/*":
            i += 2
            while i < n and src[i:i + 2] != "*/":
                out.append("\n" if src[i] == "\n" else " ")
                i += 1
            i += 2
            out.append("  ")
            continue
        out.append(c)
        i += 1
    return "".join(out)


def line_of(src, pos):
    return src.count("\n", 0, pos) + 1


def statements(src):
    """Yield (statement, offset) split on semicolons."""
    start = 0
    for m in re.finditer(r";", src):
        chunk = src[start:m.start()]
        if chunk.strip():
            yield chunk, start
        start = m.end()
    tail = src[start:]
    if tail.strip():
        yield tail, start


def created_tables(src):
    return {m.group(1).strip('"`[]').lower()
            for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"`\[\]]+)",
                                 src, re.I)}


def check_sql(rel, raw, findings):
    src = strip_sql_comments(raw)
    made_here = created_tables(src)

    def add(check, severity, line, message, cost, fix):
        findings.append({"check": check, "severity": severity, "file": rel, "line": line,
                         "message": message, "cost": cost, "fix": fix})

    for stmt, off in statements(src):
        s = " ".join(stmt.split())
        low = s.lower()
        line = line_of(src, off + (len(stmt) - len(stmt.lstrip())))

        # M1 destructive
        for pat, what in ((r"\bdrop\s+table\b", "DROP TABLE"),
                          (r"\bdrop\s+column\b", "DROP COLUMN"),
                          (r"\btruncate\b", "TRUNCATE")):
            if re.search(pat, low):
                add("M1", "high", line, "{} is irreversible".format(what),
                    "the only undo is restoring a backup, and the rows are gone "
                    "between the drop and the restore",
                    "deprecate first: stop writing the column, ship that, then drop in a "
                    "later release once nothing reads it")

        # M2 type change
        if re.search(r"alter\s+table\s+\S+\s+alter\s+column\s+\S+\s+(type|set\s+data\s+type)", low):
            add("M2", "high", line, "column type change rewrites the whole table",
                "the table is locked for the duration on most engines, so a large table "
                "is an outage",
                "add a new column, backfill in batches, switch reads, drop the old one in "
                "a later migration")

        # M3 NOT NULL with no default on ADD COLUMN
        if re.search(r"add\s+column", low) and "not null" in low and "default" not in low:
            add("M3", "high", line, "ADD COLUMN NOT NULL with no default",
                "fails outright on a non-empty table, or rewrites it, depending on the engine",
                "add it nullable, backfill, then add the constraint in a separate migration")

        # M4 CREATE INDEX without CONCURRENTLY on a pre-existing table
        m = re.search(r"create\s+(unique\s+)?index\s+(concurrently\s+)?", low)
        if m and not m.group(2):
            t = re.search(r"\bon\s+([\w.\"`\[\]]+)", low)
            table = t.group(1).strip('"`[]') if t else None
            if table is None or table not in made_here:
                add("M4", "medium", line,
                    "CREATE INDEX without CONCURRENTLY on an existing table",
                    "writes are blocked while the index builds, which on a large table is "
                    "a stall rather than a pause",
                    "use CREATE INDEX CONCURRENTLY outside a transaction, or build it on "
                    "the new table in the same migration")

        # M5 UPDATE / DELETE with no WHERE
        if re.search(r"^\s*delete\s+from\s+\S+\s*$", low) or \
           re.search(r"^\s*update\s+\S+\s+set\b.*?(?!where)", low) and "where" not in low:
            add("M5", "high", line, "UPDATE or DELETE with no WHERE clause",
                "every row in the table is affected, and there is no undo",
                "add the WHERE, and run it as a data migration with a batched loop if the "
                "table is large")

        # M6 constraint on an existing table
        if re.search(r"alter\s+table\s+\S+\s+add\s+constraint", low) and \
           re.search(r"\b(unique|foreign\s+key|check)\b", low):
            add("M6", "medium", line, "constraint added to an existing table",
                "every existing row is validated while an exclusive lock is held",
                "add it NOT VALID, validate in a separate statement, or create a unique "
                "index concurrently and attach it")

    # M1 for Liquibase XML: the destructive operations arrive as tags, not SQL.
    if rel.endswith(LIQUIBASE_EXT):
        for m in re.finditer(r"<\s*(dropTable|dropColumn|dropAllTables|dropAllObjects)\b", src, re.I):
            add("M1", "high", line_of(src, m.start()),
                "{} is irreversible".format(m.group(1)),
                "the only undo is restoring a backup",
                "deprecate first: stop writing the column, ship that, then drop in a "
                "later release once nothing reads it")

    # M7 Liquibase rollback
    if rel.endswith(LIQUIBASE_EXT):
        for m in re.finditer(r"<changeSet\b", src):
            end = src.find("</changeSet>", m.start())
            body = src[m.start():end if end != -1 else len(src)]
            if "<rollback" not in body:
                add("M7", "medium", line_of(src, m.start()),
                    "changeset declares no rollback",
                    "a failed deployment cannot be undone by the tool, so recovery is a "
                    "manual script written under pressure",
                    "add a <rollback> block, or mark the changeset with "
                    "failOnError and a documented manual step")


def iter_migrations(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        looks_like = bool(MIGRATION_HINT.search(rel_dir)) or rel_dir == "."
        for fn in sorted(filenames):
            low = fn.lower()
            is_mig = looks_like and (low.endswith(SQL_EXT) or
                                     ("changelog" in low or "changeset" in low or
                                      low.endswith(LIQUIBASE_EXT)))
            if low.endswith(SQL_EXT) and re.match(r"^[vur]\d+[_\-.]", low):
                is_mig = True
            if is_mig:
                yield os.path.join(dirpath, fn)


def report(findings, root, files, framework):
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f["file"], f["line"]))
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    o = ["# Migration safety report\n", "Scanned: `{}`\n".format(root)]
    o.append("## Summary\n")
    o.append("- Migration files read: **{}**".format(files))
    o.append("- Framework: **{}**".format(framework))
    o.append("- Findings: **{}** ({} high, {} medium, {} low)".format(
        len(findings), counts["high"], counts["medium"], counts["low"]))
    o.append("")

    if not findings:
        o.append("No findings. These seven checks found nothing — that is not a clean bill. "
                 "Read `references/what-goes-wrong.md` and confirm the risky statements by "
                 "hand, starting with anything already applied to a production table.\n")
        return "\n".join(o)

    o.append("## Findings, worst first\n")
    o.append("| # | Check | Severity | Where | Problem |")
    o.append("|---|---|---|---|---|")
    for i, f in enumerate(findings, 1):
        o.append("| {} | {} | {} | `{}`:{} | {} |".format(
            i, f["check"], f["severity"], f["file"], f["line"],
            f["message"].replace("|", "\\|")))
    o.append("")
    o.append("## What each one costs\n")
    for i, f in enumerate(findings, 1):
        o.append("**{}. {}** — `{}`:{}".format(i, f["check"], f["file"], f["line"]))
        o.append("")
        o.append(f["message"] + ".")
        o.append("")
        o.append("Cost: " + f["cost"] + ".")
        o.append("")
        o.append("Direction: " + f["fix"] + ".")
        o.append("")
    o.append("A migration that has already run in production cannot be edited — Flyway and "
             "Liquibase record a checksum. Anything already applied needs a new migration "
             "that reverses or compensates, not an edit to the old one.")
    o.append("")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description="Check migrations for data loss and locking")
    ap.add_argument("path", help="repository root to scan")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    if not os.path.isdir(args.path):
        print("Not a directory: {}".format(args.path), file=sys.stderr)
        return 2

    findings, files = [], 0
    flyway = liquibase = 0
    for path in iter_migrations(args.path):
        try:
            raw = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        files += 1
        rel = os.path.relpath(path, args.path).replace(os.sep, "/")
        if rel.lower().endswith(SQL_EXT):
            flyway += 1
        else:
            liquibase += 1
        check_sql(rel, raw, findings)

    if files == 0:
        print("No migration files found under {}.".format(args.path), file=sys.stderr)
        print("Looked for .sql under db/migration, migrations or changelog, and for "
              "Liquibase changelogs.", file=sys.stderr)
        return 1

    framework = "Flyway/SQL" if flyway >= liquibase else "Liquibase"
    output = (json.dumps({"root": args.path, "files_read": files, "framework": framework,
                          "findings": findings}, indent=2)
              if args.json else report(findings, args.path, files, framework))

    if args.out:
        open(args.out, "w", encoding="utf-8").write(output + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
