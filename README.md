# Agent skills

Skills for AI coding agents — Claude Code, Codex, Cursor — built and tested by
[Puneet Swarup](https://github.com/puneet-swarup).

A skill is a folder with a `SKILL.md` at the top: YAML frontmatter and markdown
instructions. The agent keeps the name and description in context, loads the body when a
request matches, and opens the bundled scripts and references only when a step calls for
them. Nothing is compiled and nothing runs on a server.

This repo is a home for every skill I publish. Each folder is self-contained and can be
lifted into its own repository unchanged — so the repo-level description and topics stay
deliberately general, and the keywords that make a skill findable live with the skill, in
its `SKILL.md` frontmatter and its README.

## What's here

| Skill | What it does | Price |
|---|---|---|
| [spring-audit-coverage](spring-audit-coverage/) | Finds every Spring Boot endpoint with no audit logging and ranks the gaps by blast radius | Free |

## Using a skill

Copy the skill's folder into your agent's skills directory:

```bash
# Claude Code, project-scoped
cp -r spring-audit-coverage .claude/skills/

# or user-scoped
cp -r spring-audit-coverage ~/.claude/skills/
```

Then ask the question the description promises to answer. For example: *"Is our audit
logging complete?"*

Each skill also runs standalone where it ships a script:

```bash
python spring-audit-coverage/scripts/scan.py /path/to/your/spring/boot/repo
```

## Building the zip

Agensi and similar marketplaces take a zip, not a git checkout. Zips are build outputs
here and are gitignored — never commit one.

```bash
python build.py zip spring-audit-coverage   # builds spring-audit-coverage.zip
python build.py zip --all                   # every skill
python build.py check                       # compile every script in the tree
python build.py list                        # skills and their versions
```

`build.py` is standard-library Python, so it works on Windows, macOS and Linux without
`make` or a `zip` binary. Release tags match the `version:` field in each `SKILL.md`, and
the zip is attached to the tag. So the asset on a release is exactly the artifact that
goes to the marketplace.

Marketplace submission copy lives in [`listings/`](listings/), one file per skill. It stays
outside the skill folder so the shipped zip contains only what the agent needs.

## Adding a skill

1. `mkdir my-skill` and add `SKILL.md` with `name` and `description` in the frontmatter.
2. Keep the body under about 500 lines. Push detail into `references/`.
3. Text and scripts only — no compiled binaries, no network calls.
4. Test it on a real repository before it goes anywhere.
5. Add a row to the table above.

Frontmatter carries the listing metadata as well, so the marketplace form can fill itself
from the file: `summary`, `version`, `tags`, `keywords`, `use_cases`.

## Licence

MIT — see [LICENSE](LICENSE). Use these in commercial work, fork them, change them.
