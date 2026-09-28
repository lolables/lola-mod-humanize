# Voice Profile Format

Reference for the `.local.md` profile format. Used by the voice-profile-generator
skill during analysis and generation.

---

## File Structure

A voice profile override follows this structure:

    # Voice Profile Override: [type]

    [One-line summary]. Derived from [source descriptions].

    ---

    ## Register                  (required)
    ## Sentence Structure        (required)
    ## Parenthetical Asides      (include only if the writing shows this pattern)
    ## Voice and Person          (required)
    ## Directness                (required)
    ## Courtesy                  (required)
    ## Humor                     (include only if humor signals detected)
    ## [Content-type sections]   (e.g., "Analogies and Teaching", "Documentation Mode")
    ## Formatting                (required)
    ## Vocabulary                (required)
    ## What This Voice Is NOT    (required)

    ---

    ## Source                    (required)
    ## Metrics                   (required)

Ten of those headings are required. The validator in `manage-voices.py` checks
for every one of them:

1. `## Register`
2. `## Sentence Structure`
3. `## Voice and Person`
4. `## Directness`
5. `## Courtesy`
6. `## Formatting`
7. `## Vocabulary`
8. `## What This Voice Is NOT`
9. `## Source`
10. `## Metrics`

Heading text is matched exactly. Capitalisation and wording have to be
reproduced character for character: `## Vocabulary characteristics` does not
satisfy `## Vocabulary`, and `## What this voice is NOT` does not satisfy
`## What This Voice Is NOT`.

Optional sections may appear anywhere among the required ones. Adding them
never causes a failure.

## Section Rules

### Register

Describe the overall formality level and audience. Use one of: Casual,
Informed-casual, Professional, Formal/academic. Follow with 3-5 bullets
describing assumptions about the reader.

### Sentence Structure

Characterize variation. Include example sentences from the actual writing
at different lengths (short, medium, long). State the target sentence length
SD (8+ for varied writing).

### Parenthetical Asides

Include only if the writing uses parenthetical asides as a pattern. State
frequency (e.g., "1-2 per substantial paragraph"). Give examples by category:
hedging, caveats, humor.

### Voice and Person

State defaults: active vs. passive, first vs. second vs. third person. Describe
when each is used. "First person for experience and opinions. Second person for
instructions."

### Directness

How opinions are stated. How disagreements are handled. Whether the author
hedges, and when hedging is appropriate vs. reflexive.

### Courtesy

Calibrate warmth to the author's voice. How much to soften directives, whether
to acknowledge the reader and their time. Courtesy is not sycophancy: no "Great
question!", no "I'd be happy to", no hedged sign-offs.

The full courtesy rules live with the Humanize skill, not with this one, at
`reference/courtesy.md` under the installed `humanize` skill directory
(`module/skills/humanize/reference/courtesy.md` in the source repo, which also
keeps a copy at the repo's top-level `reference/`). There is no copy inside
`voice-profile-generator/reference/`.

### Humor

Include only if humor signals are detected. Describe the type: dry, self-
deprecating, understatement, sarcasm (rare). State what is NOT acceptable
(forced humor, jokes that undermine credibility).

### Content-Type Sections

Sections specific to the writing context. Examples:
- "Analogies and Teaching" for blog profiles with teaching patterns
- "Documentation Mode" for profiles that shift register in reference contexts
- "Openings" and "Closings" for profiles with distinctive framing patterns

Only add these when the writing shows clear patterns worth codifying.

### Formatting

Prose vs. lists preference. Bold usage rules. Heading style. Code block
conventions. Whether em dashes are used (they should not be). Collapsible
sections, tables, callouts.

### Vocabulary

Technical register level. Casual words mixed into technical writing. Domain
jargon used without apology. Terms avoided. Contraction policy.

### What This Voice Is NOT

3-6 anti-patterns the profile explicitly rejects. Examples: corporate marketing,
condescending tutorial tone, academic prose, internet-casual, bland encyclopedia
style.

### Source

List every writing source used to derive the profile, with descriptions.
Human-authored content only.

### Metrics

Raw output from `analyze-voice.py`, copied verbatim into a fenced block. The
generator emits these keys, in this order:

    words_analyzed
    sentences_analyzed
    sentence_length_mean
    sentence_length_sd
    sentence_length_min
    sentence_length_max
    short_sentence_pct
    long_sentence_pct
    first_person_per_1k
    second_person_per_1k
    contraction_per_1k
    parenthetical_per_1k
    question_per_1k
    active_voice_pct
    lexical_diversity
    avg_word_length
    long_word_pct
    headers
    question_headers_pct
    bold_instances
    list_items
    code_blocks
    em_dashes

Each line is `key: value`. Keep the key names as the generator spells them so
a later run can be diffed against this one.

Two optional keys set heading style. The generator does not emit them; add
them by hand below the generated block, one per line at column 0:

    heading_style: noun-phrase | assertion
    heading_case:  title | sentence

`noun-phrase` headings are terse labels that read as a table of contents.
`assertion` headings state the section's claim. `manage-voices.py check`
rejects any other value. The humanize skill checks each key independently:
omit `heading_style` and it applies only the prefix and cross-reference
rules of text pattern #17; omit `heading_case` and it leaves capitalization
alone.

## Formatting Rules

- Sections use imperative bullets. Not descriptive prose about the voice, but
  directives for how to write in this voice.
- Include concrete examples pulled from the actual writing. Real quotes, not
  fabricated illustrations.
- Scale each section to its significance. Minor traits: 2-3 bullets. Major
  traits: full subsection with examples.
- Follow the project's writing discipline: no AI vocabulary, no em dashes,
  active voice.
- No placeholder or "fill in later" text. Every section must be complete.

## A Partial Override Is Not Legal

"Override" describes what the file does at load time, not how much of it you
have to write. An override replaces the built-in profile wholesale; the two
are never merged section by section. A file carrying only the sections you
wanted to change leaves the rest of the voice undefined.

The validator enforces this. It fails a profile that is missing any of the ten
required headings, and it fails one where a required heading is present but its
body is empty. So write all ten every time, even where your answer restates the
built-in profile.

## Profile Types

Nine built-in profiles ship. `manage-voices.py` discovers them by listing
`reference/voices/*.md` at call time rather than from a hardcoded list, so a
new voice file registers itself.

| Type | Content | Built-in File |
|------|---------|---------------|
| `academic` | Papers, abstracts, literature reviews | `academic.md` |
| `blog` | Technical blog prose | `blog.md` |
| `code-comments` | Inline comments, docstrings, error messages | `code-comments.md` |
| `code-design` | Architecture and design docs | `code-design.md` |
| `code-docs` | READMEs, commits, PRs, CONTRIBUTING | `code-docs.md` |
| `general` | Helpful technical writing, problem-focused | `general.md` |
| `release-notes` | Changelogs and release announcements | `release-notes.md` |
| `rfc` | Formal specifications | `rfc.md` |
| `tutorial` | Instructional writing for a learner | `tutorial.md` |

Override files use the `.local.md` suffix: `blog.local.md` overrides `blog.md`.
