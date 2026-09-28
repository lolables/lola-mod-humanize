---
name: humanize
description: >-
  Transform LLM-generated text or code to read as naturally human-authored.
  Use when the user asks to "humanize", "make this sound human", "remove AI
  voice", "fix AI writing", "make this not sound like ChatGPT", or wants to
  review text/code for AI-detectable patterns. Also use when the user asks to
  humanize a specific chunk: "humanize the last commit message", "humanize
  this paragraph", "humanize that PR description", "humanize what you just
  wrote". Also use when producing final deliverables (blog posts, documentation,
  README files, commit messages, PR descriptions) that should read as
  human-written. Trigger on any mention of "Humanize" or "humanize" regardless
  of context.
---

# Humanize: Make Your Output Human

You are performing a structured transformation of LLM-generated content to
produce text or code that reads as naturally human-authored. Follow this
methodology exactly. Do not skip passes.

## Before You Start

0. **Locate the skill directory.** This skill's reference files and scripts
   are bundled alongside this `SKILL.md`. Anchor on this file's absolute
   path: `SKILL_DIR=$(dirname "$(realpath /abs/path/to/this/SKILL.md)")`,
   resolving symlinks if needed. Reuse `$SKILL_DIR` for every
   `reference/<x>` and `scripts/<x>` path below; the runnable commands
   already spell it that way. Do **not** hardcode a host-specific skill
   path or search candidate paths. The install destination varies by host
   and scope; helpers are always next to the loaded `SKILL.md`.

1. **Determine mode.** Pick the first matching mode:

   | Mode | Trigger | Passes | Git safety check? |
   |------|---------|--------|-------------|
   | **Input** | User provides or references a chunk of text to humanize (e.g., "humanize the last commit message", "humanize this paragraph", pasted text) | 1-5 on the input chunk; add 0 only when the input names a file | No |
   | **Audit** | User asks to "audit", "review", or "check" for AI patterns | 0-2 only | No |
   | **Code-only** | Input is exclusively source code | 0-5, skip text-specific checks | Yes |
   | **Batch** | More than 3 files | 0-5 per file via subagents | Yes |
   | **Full** | Everything else | 0-5 | Yes |
   | **Politeness** | User asks for a "politeness wash", "soften this", "make this less abrasive", or "make this friendlier" | courtesy pass only | No (chunk) / Yes (files) |

   **Input mode details.** The user wants a specific piece of text transformed,
   not a file rewrite. The input might be:
   - Pasted text in the conversation
   - A reference like "the last commit message", "that PR description",
     "the error message above"
   - Your own earlier output in the conversation ("humanize what you just wrote")

   For references, retrieve the content first (e.g., `git log -1 --format=%B`
   for the last commit message). Run the full pipeline on the retrieved text.
   Present the transformed result inline. If the source is writable (a commit
   message, a file), offer to apply the change:
   > "Here's the humanized version. Want me to amend the commit / update the file?"

   Skip the git safety check for input mode. The user is asking for a quick
   transformation of a chunk, not a file rewrite.

   **Politeness mode details.** The input may be human-written text that is
   merely blunt, not AI-generated. Do NOT run Passes 0-3 (no watchlist, no
   collaborative-remnant deletion, no structural edits). Load
   `reference/courtesy.md` and, if a voice is named or detected, that voice's
   `## Courtesy` calibration. Apply only the abrasive-to-courteous rewrites
   from courtesy.md at the register's level. Never add sycophantic filler.
   Present the softened result inline for a chunk; when the target is files,
   run the step 2 git safety check first and edit in place, like the other
   file-modifying modes.

2. **Git safety check** (full, code-only, batch, and file-targeted
   politeness modes):

   If a `scripts/humanize-branch.sh` exists in the skill directory, run
   `bash "$SKILL_DIR/scripts/humanize-branch.sh" check` to verify the worktree.

   - If it returns **DIRTY**: STOP. Tell the user to commit or stash first.
   - If it returns **CLEAN** or **CLEAN_WITH_UNTRACKED**: proceed. Edit the
     files in place on the branch the user is already on.
   - If it returns **NOT_GIT**: warn the user that files will be modified in
     place with no undo. Ask for confirmation before proceeding.
   - If the script is not found, check whether the current directory is a git
     repo (`git rev-parse --git-dir`). If yes, verify it is clean yourself
     (`git status --porcelain`) and apply the same rules. If no, warn the user.

   Never create a branch, switch branches, stash, or commit. The clean-worktree
   precondition is what makes the transformation recoverable: with nothing else
   modified, `git diff` is exactly your changes and `git checkout -- .` undoes
   them. Moving the user somewhere they did not ask to go adds no safety on top
   of that.

3. Read the reference files from the skill directory:
   - `reference/ai-vocabulary-watchlist.md` -- words and phrases to flag
   - `reference/structural-patterns.md` -- structural anti-patterns
   - `reference/code-patterns.md` -- code-specific patterns (if processing code)
   - `reference/courtesy.md` -- courtesy calibration (warmth without sycophancy)
   - Voice profile: determined by content type. See "Profile Selection"
     section below. Pass 3 runs it first, because Pass 3, Pass 4, and the
     Pass 5 checklist all read values from the profile.

4. Identify the content type:
   - **Text:** prose, documentation, blog posts, commit messages, PR descriptions
   - **Code:** source code, configuration files, scripts
   - **Mixed:** documentation with embedded code (process text and code sections
     separately)

5. Identify the audience and context:
   - Who will read this? (peers, public, management, reviewers)
   - What publication context? (GitHub README, blog post, internal doc, code review)
   - Any specific style guide to follow?

## Pass 0: Mechanical pre-scan

**Input mode:** If the input is a conversation chunk (pasted text, your own
earlier output), skip this pass. The pre-scan tool operates on files. If the
input references a file, you can scan that file. Proceed to Pass 1.

Run the pre-scan tool. With no arguments, it scans every file in the repo
(respecting .gitignore, skipping binaries and generated files):

    python3 "$SKILL_DIR/scripts/pre-scan.py" --mode llm --voice general

"Everything" means everything: config files, tests, scripts, docs, YAML,
Taskfiles, Dockerfiles, CI configs. If git tracks it and it's not binary,
scan it.

Three flags shape the run:

- `--mode llm` gives terse output for an agent; `--mode human` gives the
  readable report.
- `--voice <profile>` loads that profile's `max_sentence_len` and
  `structured_density_max`. Always pass it. Without it the scan falls back
  to the generic sentence-length limit and leaves the density cap unset,
  which disables the over-structured check, so both voice-derived limits go
  unchecked. Use the profile you expect Pass 3 to select (see "Profile
  Selection"). If none is known yet, scan with `general` and re-run under
  the real profile in Pass 5.
- `--diff` narrows the scan to lines changed against the base branch.

To scan specific files only:

    python3 "$SKILL_DIR/scripts/pre-scan.py" --mode llm --voice general <target-files>

To scan only the changes on the current branch (useful when humanizing a PR
or someone else's work):

    python3 "$SKILL_DIR/scripts/pre-scan.py" --mode llm --voice general --diff

The output lists every mechanically detectable finding with line numbers. It
covers vocabulary (tiers 1-3, banned phrases, transitions), dashes (em, en,
ASCII prose), and structural patterns (inline-header lists, boldface, negative
parallelism, despite-challenges, generic openers/closers, collaborative
remnants).

It also emits readability findings, under four tags. Three are prose-only:
`wall-of-text` (paragraph over the sentence budget), `long-sentence` (over
`max_sentence_len`), and `clause-heavy` (over-nested prose). The scanner runs
that lane for prose suffixes only (`.md` / `.markdown` / `.txt` / `.rst` /
`.adoc` / `.org` / `.text`), so a code-only run produces none of the three.
The fourth tag, `over-structured`, is a whole-file stat. It fires on any file
type, but only when `--voice` supplied a `structured_density_max`. Pass 3
acts on the `wall-of-text` findings; when there are none, there is nothing to
restructure.

**This is a guide, not a hit list.** Every finding needs your judgment:
- A Tier 3 word in its natural technical context ("robust encryption") may be
  fine. Keep it if it's the right word.
- An em dash in a quoted terminal session is not an AI pattern.
- An inline-header list in a changelog is the correct format.
- "Not just" in dialogue or a direct quote should stay.

Use the pre-scan output to focus your attention during Passes 1-3. You still
read the full content and apply context. The pre-scan tells you WHERE to look,
not WHAT to do.

If the script is not available (e.g., running outside the skill directory),
skip this pass and proceed with manual scanning as before.

## Pass 1: Vocabulary scan

If Pass 0 ran, cross-reference against its vocabulary findings. Add any items
the pre-scan missed (it only catches mechanical patterns, not contextual ones
like figurative use of "landscape"). Remove any pre-scan findings that are
contextually appropriate.

Scan the input against the AI vocabulary watchlist.

For text:
- Flag every word/phrase from Tiers 1-5 of the watchlist
- Count flagged items per 500-word block
- Note the tier of each flagged item

For code:
- Flag uniformly verbose variable names
- Flag formal, high-density comments
- Flag grammatically complete error messages
- Flag perfectly alphabetized imports

**Report findings.** List each flagged item with its location and tier.

## Pass 2: Structural analysis

If Pass 0 ran, start from its structural findings. Assess each one in context.
Add patterns the pre-scan cannot detect: burstiness feel, promotional tone,
vague attributions, symmetric section structure, rule-of-three overuse.

Scan for structural anti-patterns.

For text, check all 15 patterns from `reference/structural-patterns.md`:
1. Low burstiness (uniform sentence length)
2. Rule-of-three overuse
3. Formulaic transitions
4. Symmetric section structure
5. Negative parallelisms
6. Challenges-and-future-prospects endings
7. Connector dashes (em, en, and the ASCII form)
8. Inline-header lists
9. Excessive boldface
10. Generic openings/closings
11. Superficial participle analyses
12. Vague attributions
13. Promotional tone
14. Collaborative communication remnants
15. Wall of text / undifferentiated density

For code, check patterns from `reference/code-patterns.md`:
1. Naming convention uniformity
2. Comment density and style
3. Error handling (common-case only)
4. Import over-organization
5. Error message formality
6. Structural over-engineering
7. Whitespace and formatting
8. Commit patterns

**CHECKPOINT: Present findings to the user.**

Show a summary table:

```
Pattern                    | Severity | Count | Action
---------------------------|----------|-------|--------
AI vocabulary (Tier 1)     | HIGH     | 5     | Replace all
Uniform sentence length    | HIGH     | yes   | Vary
Formulaic transitions      | MEDIUM   | 3     | Delete/merge
Wall of text / long sentences | MEDIUM   | 2     | Restructure/split
...
```

For code files, also report comment categories:

```
Code comments: N total what-comments found
  Dense syntax (regexes, transforms):  M  -> recommend KEEP
  Section markers (long functions):    K  -> recommend KEEP
  Truly redundant (restate obvious):   R  -> recommend DELETE
```

Ask: "Proceed with transformation, or adjust the plan?"

If the user has indicated autonomous operation (e.g., "go ahead", "do it",
"knock yourself out"), proceed without waiting. For code comments in autonomous
mode, keep dense-syntax and section-marker comments by default; only delete
truly redundant ones.

## Pass 3: Structural transformation

Run "Profile Selection" (the section after this one) before you touch
anything, and load the voice profile. Pass 3 reads the profile's paragraph
budget, `structured_density_max`, and `max_sentence_len`; Pass 4 and the
Pass 5 checklist read it too. Load it once, here.

Apply fixes from the structural patterns reference, in this order:

**Zero-risk deletions first:**
1. Delete collaborative remnants ("I hope this helps", etc.)
2. Delete generic openers ("In today's fast-paced world...")
3. Delete generic closers ("In conclusion, we have explored...")
4. Delete superficial participle phrases ("...highlighting its significance")

**Restructure buried enumerable content:**
For each wall-of-text finding, judge the content shape. If it is genuinely
sequential, enumerable, or conditional and reads faster structured, restructure
it under the active voice's budget (numbered steps / bulleted list / table),
keeping structured content under the voice's `structured_density_max`. Any
structure you add must still pass text pattern #8 (no inline-header lists as
default format) and text pattern #9 (no decorative boldface). Genuine
explanation or argument stays prose; split its run-on sentences against the
voice's `max_sentence_len` ceiling instead (text pattern #1, low burstiness).

Restructuring is the most consequential and subjective edit, so it follows the
skill's autonomous-operation rule with a conservative default:
- **Autonomous ("go ahead"):** restructure only high-confidence walls (clearly
  sequential/enumerable content over the paragraph budget); leave borderline
  argument-prose as prose.
- **Interactive (default):** after the Pass 2 report, step through each proposed
  restructure one at a time for accept / reject / skip, then apply the accepted
  ones. This per-finding walk applies to restructuring only; the other passes
  keep their coarse proceed/adjust checkpoint.

**Structural changes next:**
5. Delete or merge formulaic transitions
6. Remove excessive boldface
7. Convert inline-header lists to prose or proper sub-headings
8. Break section symmetry (vary lengths)
9. Rewrite negative parallelisms as direct statements
10. Delete or integrate challenges/future sections
11. Replace vague attributions with specifics or delete
12. Flatten promotional tone
13. Replace all em dashes with commas, parentheses, colons, or periods

**For code:**
1. Shorten local variable names where context is clear
2. Flatten unnecessary abstractions (inline single-caller helpers)
3. Relax import ordering (logical grouping, not alphabetical)
4. Remove over-engineered patterns (factories for single implementations)

## Profile Selection

Determine which voice profile to load. Pass 3 runs this section first; Pass 4
and the Pass 5 checklist reuse the profile it selects.

**If the user specified a profile** (e.g., "humanize this as an rfc", "use the
tutorial voice"), use that profile. If the name does not match a known profile
(blog, general, tutorial, code-comments, code-docs, code-design, rfc,
release-notes, academic), list the available profiles and ask the user to pick
one.

**Otherwise, auto-detect** using the first matching rule:

| Priority | Signal | Profile(s) |
|----------|--------|-----------|
| 1 | Source file by extension (any programming language) | code-comments + code-design |
| 2 | CHANGELOG*, RELEASES*, HISTORY*, or a release/tag body | release-notes |
| 3 | README*, CONTRIBUTING*, commit message, PR description | code-docs |
| 4 | 3+ RFC 2119 keywords in caps (MUST/SHOULD/MAY/SHALL/REQUIRED) AND numbered sections | rfc |
| 5 | Abstract + inline citations + a numbered references section | academic |
| 6 | Sequential numbered steps, "Prerequisites" section, second-person throughout | tutorial |
| 7 | Everything else | general (CHECKPOINT) |

**CHECKPOINT: Confirm fallback voice.**

When priority 7 fires (no specific signal matched), ask the user before
loading the profile:

> No specific voice detected. Default is `general` (helpful technical,
> problem-focused). Other options: `academic` / `blog` (opinion-bearing) /
> `code-comments` / `code-design` / `code-docs` / `release-notes` / `rfc` /
> `tutorial`. Which voice?

If the user has indicated autonomous operation (e.g., "go ahead", "do it",
"knock yourself out") earlier in the conversation, skip the prompt and use
`general`. The user can re-invoke with an explicit profile to override.

**Load the profile(s).** For each profile name X, check in order:
1. `$XDG_CONFIG_HOME/humanize/voices/X.local.md` (default `~/.config/humanize/voices/`)
2. `$SKILL_DIR/reference/voices/X.local.md`
3. `$SKILL_DIR/reference/voices/X.md`

First file found wins. If none found, warn and fall back to general.

**When multiple profiles apply** (source code gets both code-comments and
code-design), concatenate them under section headers:

```
## Voice Profile: code-comments
[contents of code-comments profile]

## Voice Profile: code-design
[contents of code-design profile]
```

Apply as a single Pass 4. Do not run the pipeline twice.

## Pass 4: Voice transformation

Apply the guidance from the voice profile loaded in Profile Selection. The
profile defines the target register, sentence structure, formatting, and
vocabulary for the selected content type. Follow the profile's guidance
rather than the generic rules below; the profile is more specific.

**Courtesy step.** After applying the voice, apply the courtesy calibration
from the selected voice's `## Courtesy` section (mechanism in
`reference/courtesy.md`). Soften abrasive constructions to the register's
level: bare imperatives, flat contradictions, hostile error framing,
dismissive "obviously"/"just". Do NOT add sycophantic filler; the Pass 3
deletions stand. Courtesy is warmth and respect for the reader, not the
"Great question!" / "I hope this helps!" filler the watchlist removes.

**Generic rules (apply when the profile does not specify otherwise):**

For text:
1. Replace remaining AI vocabulary with contextual alternatives
2. Vary sentence length into the profile's `sentence_length_sd` range; with
   no profile loaded, target SD > 8 words
3. Convert passive to active voice where the actor is known
4. Replace generic claims with specific details

For code:
1. Shorten error messages to terse, contextual form
2. Remove comments that restate code; keep "why" comments. Exceptions: keep
   "what" comments above dense syntax (regexes, bitwise ops, complex
   comprehensions), inside transform chains (where comments form a narrative
   across pipeline steps), and section markers in long functions (comments
   that act as headings to help scan 40+ line functions).
3. Match the project's existing style conventions

**Examples** (before/after for calibration):

Text:
> Before: "The system provides robust authentication capabilities.
> Furthermore, it supports multiple identity providers through
> standardized protocols."
>
> After: "Authentication supports SAML, OIDC, and LDAP out of the box.
> Configuration is in the settings panel."

Code comment:
> Before: `// Increment the counter variable to track the total number
> of processed items`
>
> After: `// track processed count`

Error message:
> Before: `"An unexpected error occurred while processing the request.
> Please try again later."`
>
> After: `f"request failed: {err}"`

## Pass 5: Self-verification

If the pre-scan tool is available, re-run it on the transformed output:

    python3 "$SKILL_DIR/scripts/pre-scan.py" --mode llm --voice <profile> <output-files>

Use the profile Pass 3 loaded, so the sentence-length and structured-density
limits match the voice you just applied.

Compare against the original scan. Any remaining HIGH-severity findings need
explicit justification in the verification report.

Run the verification checklist. Report results honestly.

### Text verification

- [ ] AI vocabulary density: <= 2 flagged words per 500 words
- [ ] Sentence length variation: SD inside the voice's `sentence_length_sd`
      range (fallback when no profile is loaded, or when the profile omits
      the key: SD >= 8 words)
- [ ] Sentence length ceiling: no sentence over the voice's max_sentence_len
- [ ] No wall-of-text: enumerable/sequential/conditional content is not buried in an over-long paragraph
- [ ] Formulaic transitions: 0 remaining
- [ ] Section length variation: >= 30% between longest and shortest
- [ ] No promotional or press-release tone
- [ ] Bold usage: < 3 instances per 1000 words
- [ ] No formulaic conclusions ("In conclusion", "To summarize")
- [ ] Specificity: >= 1 concrete detail per paragraph
- [ ] Voice matches selected profile (blog/general/tutorial/rfc/code-comments/code-docs/code-design/release-notes/academic)
- [ ] Connector dashes: none (em, en, or the ASCII form)
- [ ] No collaborative remnants
- [ ] No placeholder text

### Code verification

- [ ] Naming conventions match project style
- [ ] Comment density appropriate for code complexity
- [ ] Error handling covers edge cases
- [ ] No over-engineered abstractions for simple operations
- [ ] Error messages are terse and contextual
- [ ] Imports organized logically (not obsessively)
- [ ] Code passes existing lint rules and tests

**CHECKPOINT: Present verification results.**

Show which checks passed and which failed. For failures, explain why and
whether the failure is acceptable in context. If a flagged word remains because
it's genuinely the best word, note that explicitly.

## Output

Present the transformed content with a brief summary of changes made:
- Number of vocabulary replacements
- Structural patterns fixed
- Voice adjustments applied
- Any verification failures and rationale

## Mode-specific behavior

Mode is determined at the start (see "Before You Start", step 1). Each mode
adjusts the pipeline, not the methodology.

### Input mode

Run the full pipeline on the provided chunk. Present the result inline. If the
source is writable (a file, a commit message, a PR body), offer to apply:

> "Want me to amend the commit / update the file?"

No git safety check. No batch dispatch. No checkpoint prompts unless the chunk
is large enough to warrant them (roughly 500+ words).

For short inputs (under ~100 words, e.g., a commit message or error string),
skip the summary table and verification checklist. Report changes inline:

> Replaced 2 AI-vocabulary items, fixed 1 em dash. Here's the result:

### Audit mode

Run Passes 0-2 only. Present findings. Change nothing.

### Code-only mode

Skip text-specific checks (burstiness, transitions, section symmetry). Focus
on code patterns from `reference/code-patterns.md`.

### Batch mode

Dispatch a subagent per file or per small group of related files. Each subagent
gets the skill instructions, reference files, and its assigned files. The main
session coordinates, reviews outputs, and commits.

For 3 or fewer files, or when the host cannot dispatch subagents, process
sequentially in the main session.

## After transformation (any mode that modified files)

This section covers full, code-only, batch, and file-targeted politeness
modes. It does not apply to input or audit modes, or to a politeness wash on
a chunk.

Report:
- Files modified (list each one)
- Vocabulary replacements: total count across all files
- Structural fixes: total count across all files

### In a git repo

The worktree was clean before the transformation, so every uncommitted change
in it is now yours to accept or reject. Tell the user that, and give them the
commands:

> Changes are in place on `<current-branch>`, uncommitted. Review them with:
>
> ```
> git diff
> ```
>
> Then choose one of:
>
> 1. **Keep them** (default) -- review, edit, and commit when you are ready.
>    Nothing happens until you do.
> 2. **Reject one file** -- reverts that file, keeps the rest:
>    ```
>    git checkout -- path/to/file
>    ```
> 3. **Reject everything**:
>    ```
>    git checkout -- .
>    ```

Do not run any of these for the user. Reverting is their call.

### If not in a git repo

Remind the user that the files were modified in place with no undo path.
Encourage them to review each changed file before treating the output as final.

## Important notes

- **Do not introduce artificial errors.** No fake typos, no deliberate
  grammatical mistakes. Human writing has natural imperfection through
  variation, not through manufactured errors.
- **Preserve technical accuracy.** Never change a technically correct statement
  to sound more human if it would reduce accuracy.
- **Context overrides rules.** If a flagged word is genuinely the best word
  for the technical context, keep it and note it in verification.
- **Match existing conventions.** When transforming code, match the project's
  existing style, not an idealized style.
- **Professional voice, not casual.** The goal is professional writing with
  personality, not internet-casual writing.

## Your own output

<!-- BEGIN GENERATED: banned -->
Your transformed text must also follow these rules. Do not use these words
in your output: delve (into), tapestry (figurative), landscape (figurative),
meticulous, pivotal, underscore (verb), intricate, interplay, vibrant,
testament (to), enduring, garner, highlight (verb), seamless, foster,
cultivate, bolster, remarkable, commendable, dive into, deep dive,
bolstered, showcasing, fostering, seamlessly, groundbreaking,
transformative, paradigm, embark (on), holistic, synergy, multifaceted,
nuanced (filler).

Do not use "It's important to note that", "In today's
[fast-paced/digital/modern] world", "serves as a
[testament/reminder/beacon]", "a diverse array of", "boasts a
[rich/vibrant]", "commitment to [excellence/innovation]", "rich cultural
heritage", "plays a [vital/crucial/key] role", "Not just X, but also Y",
"not only (bare)", "rich tapestry", "In conclusion", "It is worth noting",
"I want to be clear that", "One might argue", "This raises the question".

Do not open sentences with Additionally, Furthermore, or Moreover.
<!-- END GENERATED: banned -->

Do not use em dashes.

The list above is generated from `reference/ai-vocabulary-watchlist.md`.
