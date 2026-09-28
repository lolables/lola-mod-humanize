# Voice Profile: Release Notes

Changelogs and release announcements. What changed, for the people who use it.

---

## Register

Factual and user-facing. The reader wants to know what changed and whether it
affects them, fast. Not a blog post about the release, not a marketing
launch. A list of changes a user can act on.

- Lead with the user-visible effect, not the internal cause.
- One entry per change. Group by Added / Changed / Fixed / Removed / Security.
- Internal refactors that users never see do not belong here.

## Sentence Structure

Short, parallel, scannable. Each entry is one line where possible. Consistent
sentence length is fine here; this is the one voice where uniformity helps.

- "Added support for YAML config files."
- "Fixed a crash when the output directory does not exist."
- "Removed the --legacy flag. Use --compat instead."

## Voice and Person

- Imperative-past or simple-past, no subject: "Added X", "Fixed Y".
- Second person only for migration instructions: "You must update your config."
- No first person. The project speaks, not an author.

## Directness

- State the change, then the consequence if there is one.
- Breaking changes are flagged explicitly and early, never buried.
- Link to the issue or PR number, not a prose explanation.

## Courtesy

Low, but present. Courtesy here is respect for the user's time and their
existing setup, not warmth.

- Breaking changes always include the migration path, never just the removal:
  "Removed --legacy. Use --compat, which takes the same arguments."
- Deprecations name the replacement and the timeline.
- No blame framing for fixed bugs ("fixed the broken parser nobody noticed").
- Courtesy is not filler: no "Great question!", no "I'd be happy to". The
  release notes state what changed; they do not perform enthusiasm.

See reference/courtesy.md.

## Formatting

- Grouped lists under standard headings (Added / Changed / Fixed / Removed /
  Security / Deprecated). Keep-a-Changelog order.
- Version and date in the header: "## 2.1.0 - 2026-06-26".
- Issue/PR references in parentheses: "(#412)".
- No bold inside entries. No em dashes.
- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## Vocabulary

- Plain change verbs: added, fixed, changed, removed, deprecated.
- Specific identifiers: flag names, function names, config keys, error codes.
- No hype adjectives: not "exciting", "powerful", "major", "huge".

## AI Tells To Avoid

- Promotional entries: "We're thrilled to introduce...".
- Vague entries with no actionable detail: "Various bug fixes and
  improvements." Name them or drop them.
- Restating the same change in Added and Changed.
- A narrative paragraph where a grouped list belongs.

## What This Voice Is NOT

- Blog/announcement prose with a story arc (that's blog).
- Marketing launch copy.
- Commit-message register (that's code-docs; commits explain why, release
  notes state what users see).

## Target Metrics

```
# Targets (human-baseline ranges; refined from public-domain changelogs)
sentence_length_sd:   2-6
sentence_length_mean: 6-14
first_person_per_1k:  0-2
second_person_per_1k: 0-8
em_dash_per_1k:       0
max_sentence_len:     20
structured_density_max: 0.95
heading_style:        noun-phrase
heading_case:         title
```

---

## Basis

Keep-a-Changelog conventions and public-domain project changelogs (CPython,
curl). Not derived from any specific copyrighted work.
