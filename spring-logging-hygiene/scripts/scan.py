#!/usr/bin/env python3
"""
Review Java logging for the mistakes that leak data, lose the stack trace, or
make an incident unreadable.

Stdlib only. No network. Never writes to the repo.

    python scan.py <repo-root> [--json] [--out FILE]

Checks:
  L1  personal data or a secret in a log statement
  L2  log.error(e.getMessage()) - the stack trace is thrown away
  L3  logged and then rethrown - the same failure recorded twice
  L4  a log call inside a loop
  L5  string concatenation in a log call instead of a placeholder
  L6  no correlation id anywhere - logs cannot be joined across services
  L7  a whole request body or DTO passed to the logger
"""

import argparse
import json
import os
import re
import sys

SKIP_DIRS = {".git", "target", "build", "out", "bin", "node_modules", ".idea", ".mvn", ".venv"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

LOG_CALL = re.compile(
    r"\b(?:log|logger|LOG|LOGGER)\s*\.\s*(trace|debug|info|warn|error)\s*\((.*?)\)\s*;",
    re.S)
PII = re.compile(
    r"\b(cardNumber|pan|aadhaar|aadhar|ssn|accountNumber|iban|passport|cvv|"
    r"password|secret|token|apiKey|authorization|dateOfBirth|phone|email)\b")
GETTER_PII = re.compile(r"\bget(CardNumber|Pan|Aadhaar|Ssn|AccountNumber|Password|Token|Secret)\b")
MASK = re.compile(r"\b(mask|redact|obfuscat|scrub)\w*", re.IGNORECASE)
MDC = re.compile(r"\bMDC\s*\.|\bcorrelationId\b|\bcorrelation-id\b|\btraceId\b")
LOOP = re.compile(r"\b(for|while)\s*\(")
BODY_PARAM = re.compile(r"@RequestBody\b|\bMultipartFile\b|\bHttpServletRequest\b")


def strip_comments(src):
    out, i, n, state = [], 0, len(src), None
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state, i = "line", i + 2
                out.append("  ")
                continue
            if c == "/" and nxt == "*":
                state, i = "block", i + 2
                out.append("  ")
                continue
            if src.startswith('"""', i):
                state = "textblock"
                out.append('"""')
                i += 3
                continue
            if c == '"':
                state = "str"
            elif c == "'":
                state = "char"
            out.append(c)
            i += 1
            continue
        if state == "line":
            if c == "\n":
                state = None
                out.append(c)
            else:
                out.append(" ")
            i += 1
            continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = None
                out.append("  ")
                i += 2
                continue
            out.append(c if c == "\n" else " ")
            i += 1
            continue
        if state == "textblock":
            if src.startswith('"""', i):
                state = None
                out.append('"""')
                i += 3
                continue
            out.append(c if c == "\n" else " ")
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(c)
            out.append(src[i + 1])
            i += 2
            continue
        if (state == "str" and c == '"') or (state == "char" and c == "'"):
            state = None
        out.append(c)
        i += 1
    return "".join(out)


def line_of(src, pos):
    return src.count("\n", 0, pos) + 1


def check_file(rel, raw, findings, has_mdc):
    src = strip_comments(raw)

    def add(check, severity, line, message, cost, fix):
        findings.append({"check": check, "severity": severity, "file": rel, "line": line,
                         "message": message, "cost": cost, "fix": fix})

    calls = list(LOG_CALL.finditer(src))
    if not calls:
        return

    for m in calls:
        level = m.group(1)
        args = m.group(2)
        line = line_of(src, m.start())

        # L2 getMessage() loses the trace
        if level == "error" and re.search(r"\.\s*getMessage\s*\(\s*\)", args):
            add("L2", "high", line, "log.error passes getMessage() instead of the exception",
                "the stack trace and the cause chain are discarded, so the one line that "
                "explains the failure is gone",
                "pass the throwable as the last argument: log.error(\"failed to {}\", id, e)")

        # L3 log then rethrow
        tail = src[m.end():m.end() + 200]
        if re.search(r"\bthrow\b", tail):
            add("L3", "medium", line, "failure is logged and then rethrown",
                "the same failure is recorded at every level as it unwinds, which buries "
                "the original cause",
                "log where it is handled, not where it is caught")

        # L5 concatenation
        if re.search(r'"\s*\+|\+\s*"', args):
            add("L5", "low", line, "log call uses string concatenation",
                "the message is built whether or not the level is enabled, and the values "
                "are not separable when searched",
                "use placeholders: log.info(\"user {} deleted document {}\", user, id)")

        # L1 personal data or a secret
        hits = sorted({m2.group(1).lower() for m2 in PII.finditer(args)} |
                      {m2.group(1).lower() for m2 in GETTER_PII.finditer(args)})
        if hits and not MASK.search(args):
            add("L1", "high", line,
                "log statement carries personal data or a secret: " + ", ".join(hits[:4]),
                "log files are readable by anyone with host access and rotate slowly; a "
                "card number in a log is a card number in a backup",
                "mask at the call site, or log an id and a count instead of the value")

        # L7 whole body or request
        if BODY_PARAM.search(args) or re.search(r"\b(request|body|payload|dto)\s*\)", args):
            add("L7", "medium", line, "whole request or body passed to the logger",
                "the body is the highest-sensitivity object in the request and it lands in "
                "a file with a long retention",
                "log the fields you need, named individually, masked where required")

        # L4 inside a loop: look back for an unclosed loop header
        before = src[max(0, m.start() - 400):m.start()]
        if LOOP.search(before) and before.count("{") > before.count("}"):
            add("L4", "medium", line, "log call inside a loop",
                "one line per iteration turns an incident into a flood, and the useful "
                "entry scrolls out of the window",
                "log once per batch with a count, or move it to debug")

    if not has_mdc:
        add("L6", "medium", line_of(src, 0), "no correlation id in this file",
            "without one, the lines from a single request cannot be separated from "
            "another request's",
            "put a correlation id in MDC at the edge and include it in the pattern")


def report(findings, root, files):
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f["file"], f["line"]))
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    o = ["# Logging review\n", "Scanned: `{}`\n".format(root)]
    o.append("## Summary\n")
    o.append("- Java files read: **{}**".format(files))
    o.append("- Findings: **{}** ({} high, {} medium, {} low)".format(
        len(findings), counts["high"], counts["medium"], counts["low"]))
    o.append("")
    if not findings:
        o.append("No findings. These seven checks found nothing — that is not a clean bill. "
                 "Read `references/what-goes-wrong.md` and check one real log file from "
                 "production: can you answer 'what did this request do' from it?\n")
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
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description="Review Java logging")
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    if not os.path.isdir(args.path):
        print("Not a directory: {}".format(args.path), file=sys.stderr)
        return 2

    files, findings, has_mdc = 0, [], False
    for dirpath, dirnames, filenames in os.walk(args.path):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if not fn.endswith(".java"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                raw = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            files += 1
            if MDC.search(raw):
                has_mdc = True
            check_file(os.path.relpath(path, args.path).replace(os.sep, "/"),
                       raw, findings, True)

    if files == 0:
        print("No Java files found under {}.".format(args.path), file=sys.stderr)
        return 1

    if not has_mdc:
        findings.append({"check": "L6", "severity": "medium", "file": "(repository)",
                         "line": 1, "message": "no correlation id anywhere in the codebase",
                         "cost": "logs from one request cannot be separated from another's, "
                                 "so an incident is read by timestamp and guesswork",
                         "fix": "set a correlation id in MDC at the edge and include it in "
                                "the log pattern"})

    output = (json.dumps({"root": args.path, "files_read": files, "findings": findings},
                         indent=2)
              if args.json else report(findings, args.path, files))
    if args.out:
        open(args.out, "w", encoding="utf-8").write(output + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
