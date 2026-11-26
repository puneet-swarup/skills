#!/usr/bin/env python3
"""Build and check skills in this repo.

Stdlib only, no network, works on Windows, macOS and Linux without `make` or `zip`.

    python build.py zip <skill>                 build <skill>.zip for upload
    python build.py zip --all                   build every skill
    python build.py check                       compile every script in the tree
    python build.py clean                       remove zips and __pycache__
    python build.py list                        show skills and their versions
"""

import argparse
import os
import re
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".idea", ".vscode"}
# Listing assets, not shipped: the marketplace takes the logo through its own
# form field, and an agent cannot read a PNG.
SKIP_FILES = {".DS_Store", "icon.png", "icon.svg"}
SKIP_EXT = {".zip", ".pyc"}


def skills():
    """Every directory in the repo root that has a SKILL.md."""
    found = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md")):
            found.append(name)
    return found


def frontmatter(skill):
    with open(os.path.join(ROOT, skill, "SKILL.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def build_one(skill):
    meta = frontmatter(skill)
    if not meta.get("name"):
        print("  {}: SKILL.md has no name in frontmatter".format(skill), file=sys.stderr)
        return None

    target = os.path.join(ROOT, skill + ".zip")
    if os.path.exists(target):
        os.remove(target)

    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, skill)):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fn in sorted(filenames):
                if fn in SKIP_FILES or os.path.splitext(fn)[1] in SKIP_EXT:
                    continue
                full = os.path.join(dirpath, fn)
                arc = os.path.relpath(full, ROOT).replace(os.sep, "/")
                zf.write(full, arc)
                count += 1

    size = os.path.getsize(target)
    print("  {} -> {}.zip  {} files, {} bytes, version {}".format(
        skill, skill, count, size, meta.get("version", "?")))
    if count > 0 and size > 50 * 1024 * 1024:
        print("  WARNING: over the 50 MB marketplace limit", file=sys.stderr)
    return target


def cmd_zip(args):
    targets = skills() if args.all else args.names
    if not targets:
        print("name a skill, or use --all. Skills here: " + ", ".join(skills()),
              file=sys.stderr)
        return 2
    for skill in targets:
        if not os.path.isdir(os.path.join(ROOT, skill)):
            print("no such skill: {}".format(skill), file=sys.stderr)
            return 2
    print("building:")
    for skill in targets:
        build_one(skill)
    return 0


def cmd_check(_args):
    failures = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding="utf-8") as f:
                    compile(f.read(), full, "exec")
            except SyntaxError as exc:
                print("  {}:{}: {}".format(os.path.relpath(full, ROOT), exc.lineno, exc.msg),
                      file=sys.stderr)
                failures += 1
    for dirpath, dirnames, _ in os.walk(ROOT):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
    if failures:
        print("{} file(s) failed to compile".format(failures), file=sys.stderr)
        return 1
    print("all scripts compile")
    return 0


def cmd_clean(_args):
    for name in os.listdir(ROOT):
        if name.endswith(".zip"):
            os.remove(os.path.join(ROOT, name))
    for dirpath, dirnames, _ in os.walk(ROOT):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
    print("clean")
    return 0


SHEET_SECTIONS = [
    ("Name", "name"),
    ("Summary", "summary"),
    ("Description", "description"),
    ("See it in action", "see_it"),
    ("Compatibility note", "compatibility"),
    ("Tags and use cases", "tags"),
    ("Limitations and FAQ", "faq"),
]


def split_sections(text):
    """Split markdown on '## ' headings that are not inside a fenced block."""
    sections, cur, buf, in_fence = {}, None, [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if cur is not None:
                sections[cur] = "\n".join(buf).strip()
            cur, buf = line[3:].strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip()
    return sections


def unwrap(body):
    """A section that is exactly one fenced block yields its inner text."""
    stripped = body.strip()
    if not stripped.startswith("```"):
        return stripped
    first_nl = stripped.find("\n")
    close = stripped.rfind("```")
    if close <= first_nl:
        return stripped
    inner = stripped[first_nl + 1:close].strip()
    if stripped[close + 3:].strip():
        return stripped          # more content after the block: keep it all
    return inner


def listing_sections(skill):
    path = os.path.join(ROOT, "listings", skill + ".md")
    if not os.path.isfile(path):
        return {}
    raw = split_sections(open(path, encoding="utf-8").read())
    out = {}
    for heading, key in SHEET_SECTIONS:
        for name, body in raw.items():
            if name.startswith(heading):
                out[key] = unwrap(body)
                break
    return out


def cmd_agensi(args):
    """Write one self-contained submission sheet per skill, at the repo root."""
    for skill in args.names:
        meta = frontmatter(skill)
        sec = listing_sections(skill)
        if not sec:
            print("  {}: no listings/{}.md".format(skill, skill), file=sys.stderr)
            continue
        price_line = ""
        path = os.path.join(ROOT, "listings", skill + ".md")
        for line in open(path, encoding="utf-8").read().splitlines():
            if line.lower().startswith(("free", "$")) or "one-time" in line.lower():
                price_line = line.strip()
                break
        rows = [
            ("ZIP", "{}.zip".format(skill)),
            ("Agensi tools", "Skip. No image, video, voice or live-data service."),
            ("Logo", "{}/icon.png".format(skill)),
            ("Name", meta.get("name", skill)),
            ("Summary", sec.get("summary", "")),
            ("Description", sec.get("description", "")),
            ("See it in action", sec.get("see_it", "")),
            ("Compatibility note", sec.get("compatibility", "")),
            ("Pricing", price_line or "(set on the form)"),
            ("Categories", "Up to 3 of the 32 on the form. Closest developer-tools "
                           "first, then security or compliance. Use the form's own names."),
            ("Tags and use cases", sec.get("tags", "")),
            ("Permissions", "Read what the scan detected. Expect: reads local files, "
                            "no network."),
            ("Limitations and FAQ", sec.get("faq", "")),
            ("Screenshots and video", "Skip."),
            ("Docs link", "Leave empty. Never a private repo."),
        ]
        out = ["# Agensi submission sheet — {}".format(skill), "",
               "Generated from `listings/{}.md` and the skill frontmatter.".format(skill),
               "Every field below is the exact text to paste. Nothing to look up.",
               "Regenerate with `python build.py agensi {}`.".format(skill), "",
               "| # | Field | Value |", "|---|---|---|"]
        for i, (field, value) in enumerate(rows, 1):
            short = value if len(value) <= 60 and "\n" not in value else "see below"
            out.append("| {} | {} | {} |".format(i, field, short.replace("|", "\\|")))
        out.append("")
        for i, (field, value) in enumerate(rows, 1):
            out.append("## {}. {}".format(i, field))
            out.append("")
            out.append("````")
            out.append(value)
            out.append("````")
            out.append("")
        target = os.path.join(ROOT, "AGENSI-{}.md".format(skill))
        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
        print("  wrote {}".format(os.path.relpath(target, ROOT)))
    return 0


def cmd_list(_args):
    for skill in skills():
        meta = frontmatter(skill)
        print("{:<28} {:<10} {}".format(
            skill, meta.get("version", "?"), meta.get("summary", "")[:70]))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Build and check skills")
    sub = ap.add_subparsers(dest="cmd", required=True)

    z = sub.add_parser("zip", help="build a skill zip")
    z.add_argument("names", nargs="*")
    z.add_argument("--all", action="store_true")
    z.set_defaults(func=cmd_zip)

    sub.add_parser("check", help="compile every script").set_defaults(func=cmd_check)
    sub.add_parser("clean", help="remove zips and caches").set_defaults(func=cmd_clean)
    sub.add_parser("list", help="list skills").set_defaults(func=cmd_list)
    a = sub.add_parser("agensi", help="write a submission sheet per skill")
    a.add_argument("names", nargs="*")
    a.set_defaults(func=cmd_agensi)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
