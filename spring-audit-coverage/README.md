# spring-audit-coverage

Finds the Spring Boot endpoints that change regulated data and have no audit trail, then
ranks them so you fix the one that matters first.

Most services log some calls and not others, and nobody knows which. The gap is usually
the endpoint that deletes a document or moves money.

## Install

```bash
cp -r spring-audit-coverage ~/.claude/skills/     # Claude Code, user-scoped
# or project-scoped
cp -r spring-audit-coverage .claude/skills/
```

Then ask: *"Is our audit logging complete?"* — the description is written to match that
kind of question.

## Run the scanner on its own

Python 3.8+. Standard library only, no dependencies, no network access.

```bash
python scripts/scan.py /path/to/spring-boot-repo
python scripts/scan.py . --include-tests          # include src/test
python scripts/scan.py . --json                   # machine-readable
python scripts/scan.py . --out report.md          # save the report
```

## What the output looks like

Real run against a Spring Boot service, trimmed to the top rows:

```
## Summary

- Java files read: 35
- Controllers: 5
- Endpoints found: 8
- With audit logging in the method: 0
- **Without audit logging: 8**
- Central infrastructure found, but none of it mentions auditing

## Endpoints without audit logging, worst first

| Endpoint | Method | Operation | Audited? | Risk |
|---|---|---|---|---|
| `/api/documents/{id}` | DELETE | `deleteDocument()` | no | medium (documents, score 35) |
| `/api/documents/upload` | POST | `upload()` | no | medium (documents, score 30) |
| `/api/chat/stream` | POST | `stream()` | no | low (other, score 20) |
```

Every row carries a file and line in a second table, so "not audited" is a claim you can
check rather than one you have to trust.

## How it decides

- Reads each controller method, not each file. A file that mentions `AuditService` in a
  comment is not an audited file.
- Strips comments and masks string literals before parsing, so `// AuditService` does not
  count and a path like `"/{id}"` is not mistaken for a code block.
- Looks for audit infrastructure in one place: `@Aspect`, `OncePerRequestFilter`,
  `HandlerInterceptor`, controller advice, audited base classes. If any of it mentions
  auditing, gaps are marked `unconfirmed` rather than reported as fact.
- Ranks by blast radius: money movement, then customer identity, then documents, then
  everything else. `@Controller` methods returning a template name are ranked last.

## Where it stops

- Regex-based Java parsing, not a compiler. It does not see endpoints defined in Kotlin,
  XML, GraphQL resolvers, RSocket or a `RouterFunction` bean.
- Audit done in a gateway, a proxy or a database trigger is invisible to it.
- "Audited" means the method calls an audit sink or carries an audit annotation. It does
  not mean the record is complete — that is what `references/checklist.md` is for.
- It does not read `application.yml`, so it cannot tell you whether audit is switched off
  in production.

## What's inside

```
SKILL.md                  instructions, workflow, rules
scripts/scan.py           the scanner
references/patterns.md    four implementation patterns, with trade-offs
references/checklist.md   what an audit record must contain
icon.svg                  icon source
icon.png                  512x512, for the marketplace listing logo
```

The icon is a listing asset, so `build.py` leaves it out of the shipped zip.

## Licence

MIT. Use it commercially, fork it, change it.
