# How to submit a skill to Agensi

A reusable checklist. The per-skill copy lives beside this file, named after the skill.

## Before you start

| You need | Where it comes from |
|---|---|
| The zip | the latest release asset on this repo, not a local build |
| The logo | the skill's `icon.png`, 512 × 512 |
| The listing copy | `listings/<skill>.md` |

Turn on Creator Mode once: Dashboard → Settings. A free listing needs no payout method;
a paid one needs Stripe Connect or Zoneless first.

## The form, in order

| Field | What to do |
|---|---|
| ZIP | Upload the release asset. Agensi finds the `SKILL.md` at any depth — one file means one skill. |
| Agensi tools | Skip. Only for skills that make images, video, voice or need live data. |
| Logo | Upload `icon.png`. Square, 512 × 512, under 5 MB. |
| Name | From the skill's frontmatter. Under 60 characters, unique on Agensi. |
| Summary | Under 300 characters. The form fills this from the frontmatter `summary`. |
| Description | Markdown. Say what it does, how it works and where it stops. |
| See it in action | A real request and the full result. 700+ characters works best. |
| Compatibility note | What it needs, e.g. "Requires Python 3.8+". |
| Pricing | Free for a first listing. |
| Categories | Up to 3 of 32. The first decides the category page. Use the form's own names. |
| Tags and use cases | Free text. Fills from the frontmatter `tags` and `use_cases`. |
| Permissions | Detected from the zip. Read them and make sure they are true. |
| Limitations and FAQ | Recommended. Say where the skill stops. |
| Screenshots and video | Optional, up to 6. |
| Docs link | Optional. A link to this repo is allowed. |

## Before you press submit

- [ ] Description promises nothing the files do not deliver — the reviewer runs it.
- [ ] No links to outside checkouts, unlock codes or paid versions sold elsewhere.
- [ ] Name and package are not duplicates of an existing listing.
- [ ] Permissions shown match what the code actually does.
- [ ] The zip came from a release tag, and the tag matches `version:` in `SKILL.md`.

## Paid listings

A paid listing cannot be submitted until a payout method is connected — for India that is
Zoneless, with its own identity check. Do that first; it is the only hard gate.

- Minimum price is $1. Under $5, buyers can only pay from their Agensi balance; from $5 they
  can also use a card.
- A free skill converted to paid makes everyone already using it buy it to keep using it.
  Past buyers are never charged again. Prefer a separate paid listing over a conversion.
- Price changes go live immediately, with no review.

## Linking listings to each other

Ranked by effort, cheapest first.

1. **Cross-reference in the copy.** Text edits go live with no review. The free listing's
   description should end by naming the paid companion; the paid listing's FAQ should say
   which free skill to run first. Both are one sentence.
2. **The storefront.** Every creator page lists all your skills, so anyone who arrives from
   one listing can see the rest. Nothing to configure — it happens when they are live.
3. **The "Start here" collection** in Creator Studio → Growth. Curate the order you want a
   newcomer to meet the skills in.
4. **A bundle** of two or more live paid listings, priced below the sum of the parts. Only
   possible once both are live.
5. **The repo.** The public repo's README table lists the free skills; paid ones are named
   in the paid listing's FAQ rather than linked to a private repo.

**Docs link field:** never point it at a private repository. Buyers cannot open it, so it
reads as a broken link. Leave it empty or point at the storefront.

## After you submit

Status goes Draft → Pending → Live or Rejected. Scan, AI review, then a person; most are
approved within hours, allow up to 48. Text and price edits go live immediately once live;
a new zip goes through review as an update.

Then set the listing URL as the repo's Homepage field, and tell the platform contact it
is live.

## Things that get a listing rejected

- Compiled executables anywhere in the zip.
- Obfuscated code, or network calls that are not disclosed.
- A description that promises more than the files deliver.
- Repackaged work that is not yours.
- A vague description with no clear trigger for the agent.
