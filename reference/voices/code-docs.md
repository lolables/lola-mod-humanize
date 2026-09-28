# Voice Profile: Code Docs

READMEs, commit messages, PR descriptions, changelogs, CONTRIBUTING docs.

---

## README Structure

Three sections, in this order:

1. **What it does.** One sentence. No marketing.
2. **How to install.** Exact commands. Specify prerequisites.
3. **How to use.** The most common case first. Link to fuller docs.

No preamble. No "welcome to the project." No mission statement.

**Good opening:**
```
humanize removes AI-detectable patterns from text and code.
```

**Bad opening:**
```
Welcome to Humanize! This powerful tool helps you create more authentic content
by leveraging advanced pattern detection to enhance your writing.
```

## Commit Messages

- Imperative subject line, under 72 characters. "Fix null deref in auth handler" not "Fixed..."
- Body explains the why, not the what. What is visible in the diff.
- Reference issues by number. "Closes #42."
- No period at the end of the subject line.

```
Fix null deref when token cache is empty

The cache can be empty on first run before any auth succeeds.
Previously this caused a panic. Now returns ErrNotAuthenticated.

Closes #87.
```

## PR Descriptions

- Summary: what changed and why. Two to four sentences.
- Test plan: what was tested and how.
- No "This PR does X" filler opener. Start with the substance.

```
Replaced the hand-rolled retry loop with the stdlib backoff package.
The old loop had off-by-one errors on the attempt count and didn't
respect context cancellation.

Tested: ran the existing retry tests plus added cases for cancellation
mid-retry and for the max-attempts boundary.
```

## Courtesy

Low warmth. Direct and neutral. A README or a PR is a document, not a conversation, but it is read by a person.

- Direct instructions can still be considerate. "You need Node 18+; install it first if you don't have it" is direct and helpful at once.
- A PR that requests a change names the reason, not just the objection. "This drops context cancellation, which the old loop respected" beats "this is wrong."
- A CONTRIBUTING doc states expectations plainly without scolding contributors who have not read it yet.
- Courtesy is not filler. No "Thanks for reading!", no "Great question!", no "I'd be happy to" in a doc.
- See reference/courtesy.md.

## Formatting

- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## Changelogs

User-facing only. No internal refactors unless they affect users.

Format: `Added X` / `Fixed Y` / `Removed Z` / `Changed X to Y`

**Good:**
```
Added support for YAML config files.
Fixed a crash when the output directory does not exist.
Removed the --legacy flag (use --compat instead).
```

**Bad:**
```
Refactored the internal configuration parser to use a visitor pattern.
```

## CONTRIBUTING Docs

Direct instructions. No motivational preamble.

1. Fork the repo.
2. Create a branch: `git checkout -b your-feature`.
3. Make changes. Add tests.
4. Submit a PR against `main`.

State reviewer expectations up front. If there is a CLA, say so.

## AI Tells To Avoid

- A README opener that sells the project ("powerful," "seamless") instead of saying what it does.
- "This PR does X" as the first line, where X just renames the diff.
- A changelog entry describing an internal refactor users never see.
- A bulleted feature list where every item starts with the same verb in the same shape.

## What This Voice Is NOT

- Marketing or promotional framing.
- Blog-style opinion writing.
- Tutorial hand-holding for basic git operations.

## Target Metrics

```
# Targets (human-baseline ranges, not corpus measurements)
sentence_length_sd:   6-12
first_person_per_1k:  0-4
second_person_per_1k: 2-12
contraction_per_1k:   3-12
hedge_per_1k:         1-5
em_dash_per_1k:       0
max_sentence_len:     40
structured_density_max: 0.55
heading_style:        noun-phrase
heading_case:         title
```

---

## Basis

General patterns in respected open source project documentation.
