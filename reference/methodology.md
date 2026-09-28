# Humanize Transformation Methodology

The complete, step-by-step methodology for transforming LLM-generated text and
code to read as human-authored. This document is the authoritative reference
for the Humanize skill.

---

## Philosophy

Humanize doesn't aim to fool AI detectors. It aims to produce text that a human
reader -- a colleague, a reviewer, an editor -- would read without that nagging
"this sounds like ChatGPT" feeling.

The core insight: AI text is detectable not because it's *bad* but because it's
*uniform*. Uniform vocabulary, uniform sentence length, uniform structure,
uniform tone. Human writing is messy, varied, opinionated, and specific. Humanize
introduces that natural variation.

**The overcorrection trap:** a document with zero AI-characteristic words, zero
formulaic transitions, and perfectly varied sentence length is itself a
statistical anomaly. Real writers occasionally use "comprehensive" or start a
sentence with "Furthermore." The complete absence of every AI-associated pattern
is as suspicious as the presence of too many. The goal is natural frequency, not
zero frequency. Tier 3 words should appear at human-baseline rates (roughly 1
per 500 words is normal). Em dashes are the exception: most people don't type
them, so zero is the genuine human baseline.

## Pipeline: Pass 0 Through Pass 5

### Pass 0: Mechanical Pre-Scan

**Input:** Files on disk
**Output:** Line-numbered findings, grouped by category

Run this before reading the text yourself, so you know where to look. Use
`task scan`, or call the script directly:

    python3 module/skills/humanize/scripts/pre-scan.py --mode llm <target-files>

With no file arguments the script scans every tracked, non-binary file in the
repository. `--diff` narrows it to the changes on the current branch. Full
usage is documented in `module/skills/humanize/SKILL.md`.

The output covers five categories:

- Vocabulary: tiers 1 through 3, banned phrases, formulaic transition starters.
- Dashes: em dash, en dash, and the ASCII ` -- ` form used between words.
- Readability: sentences over the voice's `max_sentence_len`, over-nested
  clauses, and paragraphs past the wall-of-text threshold.
- Structure: inline-header lists, boldface, negative parallelism,
  despite-challenges endings, generic openers and closers, collaborative
  remnants.
- Sentence relations: double colons, near-verbatim repeated sentences, and
  mirrored antithesis between adjacent sentences. Two LOW-severity hints
  join them; Tighten consults them but needs no row for each. `verdict-lead` marks a short, abstract judgment that the
  following text proves. `claim-echo` marks a claim restated in other words
  in a later section. Sections open at ATX headings and `<summary>` lines;
  setext headings are not tracked.

Treat the result as a map, not a hit list. An em dash inside a quoted terminal
session is not an AI pattern, and an inline-header list in a changelog is the
correct format. If the input is a pasted conversation chunk rather than a file,
or the script is unavailable, skip to Pass 1 and scan by hand.

### Pass 1: Vocabulary Scan

**Input:** Raw text or code
**Output:** Annotated text with flagged AI-vocabulary words/phrases

1. Scan the input against the vocabulary watchlist (`reference/ai-vocabulary-watchlist.md`)
2. Count flagged words per 500-word block
3. Flag blocks with 3+ matches as high-priority
4. Flag blocks with 1-2 matches as review-needed
5. Note the specific tier of each flagged word (Tier 1 = strongest indicator)

**Decision framework:**
- Tier 1 words: Replace unless the word is genuinely the best choice for the
  technical context (rare)
- Tier 2 words: Replace if alternatives exist without loss of precision
- Tier 3 words: Replace only if 2+ appear in the same paragraph
- Tier 4 phrases: Replace always -- these are formulaic constructions
- Tier 5 discourse markers: Delete or replace based on whether connection is
  actually needed

### Pass 2: Structural Analysis

**Input:** Text from Pass 1
**Output:** List of structural anti-patterns detected with severity

Scan for patterns from `reference/structural-patterns.md`:

1. **Measure burstiness:** Calculate sentence length variation. Flag if
   standard deviation < 8 words.
2. **Count rule-of-three:** Flag if "X, Y, and Z" pattern appears 3+ times.
3. **Detect formulaic transitions:** Flag "Furthermore" / "Moreover" /
   "Additionally" / etc.
4. **Check section symmetry:** Compare section lengths. Flag if all within 20%
   of each other.
5. **Detect negative parallelisms:** "Not just X but Y" / "Not only...but also"
6. **Check endings:** Scan final paragraphs for challenges/future/conclusion
   formulas.
7. **Count dashes:** Flag em dashes, en dashes, and the ASCII ` -- ` form
   between words.
8. **Detect list formats:** Inline-header lists (bold + colon pattern).
9. **Check bold density:** Flag at 3 or more bold spans per 1000 words, or
   any bold inline header or paragraph lead. The scanner's per-span `bold`
   findings only list locations to check; they carry no verdict.
10. **Check for generic openers/closers:** "In this article..." / "In
    conclusion..."
11. **Detect participle analyses:** "...highlighting/underscoring/emphasizing
    its significance"
12. **Check attributions:** "Experts argue" / "Industry reports suggest"
13. **Assess tone:** Promotional/press-release/travel-guide language.
14. **Collaborative remnants:** "I hope this helps" / "Would you like..."
15. **Wall of text / undifferentiated density:** Long paragraphs of run-on
    sentences carrying content that is really a list of steps, options, or
    conditions.
16. **Redundant signposting and filler:** A sentence whose content the
    material right before or after it already carries: count-then-enumerate,
    heading echoes, promissory leads, summaries of an adjacent artifact.
17. **Heading style:** Headings that fight the voice's `heading_style` /
    `heading_case`, or that carry a prefix nothing else needs.

**Checkpoint:** Present findings to the user. Show what was detected, at what
severity, and the proposed fix category for each.

### Pass 3: Structural Transformation

**Input:** Structural analysis from Pass 2
**Output:** Restructured text

Apply fixes in order of impact:

1. **Delete collaborative remnants** (zero risk of harm)
2. **Delete generic openers/closers** (nearly zero risk)
3. **Delete formulaic transitions** or merge sentences they connected
4. **Delete superficial participle phrases** at sentence ends
5. **Remove excessive bold** only where #9 fires (density at 3 per 1000
   words, or a bold inline header or lead). Below that, author emphasis
   stays unless the voice profile bans bold emphasis outright, as `rfc` and
   `release-notes` do (applied in Pass 4). Over it, cut the least necessary bold first; keep warnings and first
   definitions. In a table, remove a contrast's emphasis (bold marking the
   same kind of value across a column or row) from every cell or none
6. **Convert inline-header lists** to prose or proper sub-headings. A
   removed bold lead becomes a heading only when #17's promotion criteria
   hold and the heading is a true peer of its siblings (#17); otherwise
   the label word folds into the paragraph's first sentence. Enumerated
   items turned into prose follow #8
7. **Delete the announce sentence** left behind when the inline-header
   conversion turned its lead-in into a heading ("Two details deserve a
   closer look." above two new headings). Only those
8. **Break section symmetry** by merging thin sections or splitting dense ones
9. **Rewrite negative parallelisms** as direct statements
10. **Delete/integrate challenges-and-future sections**
11. **Replace vague attributions** with specific sources or delete
12. **Flatten promotional tone** to neutral factual statements
13. **Replace all connector dashes** (em dash, en dash, ASCII ` -- `) with
    commas, parentheses, colons, or periods. Pick a colon only if the
    sentence has none; a second colon chains it (pre-scan tag `double-colon`)

### Pass 4: Voice Transformation

**Input:** Structurally fixed text from Pass 3
**Output:** Text in target voice

Apply the voice profile chosen for this job. Profiles live in
`reference/voices/`; the selection rules and the auto-detect table that maps
content type to a default voice are in
`module/skills/humanize/SKILL.md` under "Profile Selection".

1. **Replace AI vocabulary** with contextually appropriate alternatives from
   the watchlist
2. **Vary sentence length:** Break long uniform sentences. Combine short ones.
   Insert punchy declarations. Target SD > 8 words, with a ceiling: no sentence
   longer than the voice's `max_sentence_len`. Voices that ship no
   `## Target Metrics` block fall back to 45 words
   (`DEFAULT_MAX_SENTENCE_LEN` in `scripts/pre-scan.py`). Variation is not a
   license for run-ons.
3. **Add parenthetical asides** where hedges, caveats, or humor fit naturally
   (1-2 per substantial paragraph)
4. **Activate passive voice:** Convert passive constructions to active where
   the actor is known
5. **Increase specificity:** Replace generic claims with concrete details,
   measurements, examples
6. **Add domain vocabulary:** Use field-appropriate jargon naturally
7. **Introduce rhetorical questions** where they'd help structure an argument
   (sparingly, 1 per major section max)
8. **Relax formatting:** Convert excessive lists to prose. Ensure code blocks
   have prose context.
9. **Apply courtesy:** Soften abrasive constructions to the voice's
   `## Courtesy` level (see `reference/courtesy.md`). Warmth and softened
   directives, never sycophantic filler.

**Tighten:** Run last, on the final wording, text only. Covers filler and
redundant signposting (#16), heading style (#17), the structural form of
negative parallelism (mirrored antithesis, #5), and the copy-edit defects in
`reference/clarity.md`. It owns every #16 cut except those of Pass 3's
announce-sentence step. Three stages, kept apart:

1. **Inventory**, before any edit, in four sweeps:
   - Positional: one row, with a keep/cut/rewrite decision and a reason, for
     every sentence at a #16 position. Do not filter the list.
     - first after a heading, bold lead, or `<summary>`
     - last before a heading or `</details>`
     - beside a table, list, code block, or blockquote
   - Paragraph: does an earlier claim already force this one? Would a
     copy-editor reword any sentence? Classify it with `clarity.md`.
   - Same-shape: after each hit, find its siblings elsewhere.
   - Heading: every heading against #17. Under `noun-phrase`, rewrite
     clause headings (noun clauses too); re-casing is no fix. `<summary>`
     lines follow #17's `<summary>` row.
2. **Resolve** by applying the inventory. Cuts follow #16's slot rule; a
   `rewrite` decision fixes a defect in a sentence that carries its own claim,
   and rewording filler is not one. Delete flourishes rather than rephrasing
   them. Keep a "not Y" clause when Y names something the reader would
   otherwise assume is included (a scope limit), or when it answers a real
   objection and its halves differ clearly in length. Keep the author's
   stance, so a hedged opinion never becomes a bare assertion. Leave fenced
   code, Mermaid, HTML comments, and quoted material (punctuation included)
   untouched. A GitHub admonition (`> [!NOTE]`) is the author's own text and
   gets no such exemption; the Tighten sweeps and the Pass 5 checklist cover
   it. Keep attribution when cutting a lead. Promote an inert label to a
   heading when #17 says so. Report apparent factual inconsistencies,
   including prose that enumerates rows an adjacent table lacks; never guess a
   fix. Wording the user dictated verbatim and template-required headings are
   exempt; text submitted for humanization is not.
3. **Re-read** the whole document. Fix damage your own cuts caused: after
   each cut, repair a following connective or deictic ("also", "so", "this")
   that pointed at the cut sentence. If the cut sentence carried a claim
   nothing else does, restore it verbatim.
   Problems already in the input go on the Pass 5 follow-up list.

### Pass 5: Self-Verification

**Input:** Transformed text from Pass 4
**Output:** Final text with verification report

Fix only mechanical items here (dashes, double colons, bold density,
watchlist vocabulary, generic openers and closers, collaborative remnants,
heading case and style, the sentence-length ceiling)
and name each fix. Report filler, entailment, clarity, and authorial
questions without editing them; Tighten does not run twice.

Run verification checks:

- [ ] AI vocabulary density: <= 2 flagged words per 500 words
- [ ] Sentence length SD: the scanner's `sd_verdict` is OK against the
      voice's `sentence_length_sd` range (>= 8 words without one)
- [ ] Longest sentence: <= the voice's `max_sentence_len` (45 words when the
      voice ships no `## Target Metrics` block)
- [ ] No wall of text: no prose paragraph runs past 6 sentences, and enumerable
      content is in steps, bullets, or a table. Structured density is under
      the voice's cap, or the excess is tabular and justified.
- [ ] Formulaic transitions: 0 remaining
- [ ] Section length variation: >= 30% difference between longest and shortest
- [ ] Promotional tone: None detected
- [ ] Bold density: < 3 per 1000 words, quoted material exempt
- [ ] No "In conclusion" or equivalent formulaic closers
- [ ] Specificity: >= 1 concrete detail per paragraph
- [ ] Voice: Matches target profile characteristics
- [ ] Dashes: no em dashes, no en dashes, no ASCII ` -- ` between words,
      outside quoted material and empty-cell markers
- [ ] No collaborative communication remnants
- [ ] Positional sweep complete: every sentence at a #16 position has a
      decision, siblings of each hit checked, nothing left that its neighbours
      or an earlier claim already carry
- [ ] No mirrored antithesis and no "X, not Y" tail left by a rewrite;
      flourishes deleted and no cut slot refilled; title and opening line
      checked first; scope-limiting "not Y" clauses kept
- [ ] Headings pass #17, no clause heading under `noun-phrase`;
      `heading_style` / `heading_case` checked only when the profile sets
      them; `<summary>` lines still descriptive, in the author's case
- [ ] No sentence a copy-editor would reword (`reference/clarity.md`); no
      sentence carries two colons
- [ ] Stance, quotes, attribution, and code, Mermaid, or HTML comments
      unchanged; factual inconsistencies reported, not guessed
- [ ] Tighten follow-up items: mechanical ones fixed and named in the
      report, every other item reported unedited
- [ ] No placeholder text or template language

**Checkpoint:** Present verification results. Note any checks that failed and
why (sometimes a "failure" is acceptable in context).

---

## Code-Specific Pipeline

For code, the five passes adapt:

### Pass 1: Pattern Detection

Scan for code-specific AI signatures from `reference/code-patterns.md`:
- Variable naming uniformity
- Comment density and style
- Error handling patterns
- Import organization
- Error message formality
- Structural over-engineering
- Whitespace and formatting uniformity
- Commit patterns (a delivery-stage check, not a code edit)

### Pass 2: Context Assessment

Determine what to fix based on:
- Project's existing style (match it, don't impose a new one)
- Language conventions (Go naming differs from Python)
- File's purpose (library API vs internal helper vs script)

### Pass 3: Naming and Structure

- Shorten local variables where context is clear
- Flatten unnecessary abstractions
- Inline single-caller helpers
- Relax import ordering

### Pass 4: Comments and Messages

- Remove comments that restate code
- Add comments explaining *why* for non-obvious logic
- Shorten error messages to terse, contextual form
- Add edge case handling where missing

### Pass 5: Verification

- Naming conventions match project style
- Comment density appropriate for complexity
- Error handling covers edge cases
- No over-engineered abstractions for simple operations
- Code passes lint and tests

---

## When NOT to Use Humanize

- **Formal academic writing** with specific style requirements (APA, Chicago)
- **Legal or regulatory text** where precision trumps voice
- **Existing human-written text** that doesn't need transformation
- **Text that will be significantly edited anyway** (waste of a pass)
- **Content where AI authorship is disclosed** and accepted

---

## Sources

Full source list in `docs/SOURCES.md`. Key references:

- Wikipedia:Signs of AI writing (WP:AISIGNS) -- the most detailed public field guide
- GPTZero -- perplexity/burstiness methodology documentation
- Pangram Labs -- deep learning detection research
- Kobak et al. (2024) -- "Delving into ChatGPT usage in academic writing through
  excess vocabulary"
- Liang et al. (2024) -- "Monitoring AI-Modified Content at Scale"
- BlueOptima (2025) -- AI-generated code detection
- HackerRank (2025) -- multi-signal code detection (93% accuracy)
- Louis Bouchard (2025) -- "How to Clean Up AI-Generated Drafts"
