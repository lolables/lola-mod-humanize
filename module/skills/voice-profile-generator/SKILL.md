---
name: voice-profile-generator
description: >-
  Generate voice profiles from writing samples. Analyzes paths, URLs, or
  directories of human-authored text and interactively produces .local.md
  voice profile overrides for the Humanize skill. Use when the user asks to
  "generate voice profile", "create voice profile", "analyze my writing",
  "build voice profile from", or "voice profile from my writing".
---

# Voice Profile Generator

Generate voice profiles from writing samples by dispatching parallel analysis
agents, detecting distinct registers, and interactively producing `.local.md`
overrides for the Humanize skill. The pipeline reads human-authored text,
runs statistical and qualitative analysis, presents findings to the user for
refinement, and writes profile files that the Humanize skill loads at runtime.

## Before You Start

0. **Locate the skill directory.** Your host loaded this file from a specific
   absolute path and tells you what that path is, in the skill-activation
   message or in the tool result that delivered this text. That path is
   `<skill-md>` below. If your host quotes a relative path, resolve it against
   your working directory first. Anchor on it:

   ```bash
   SKILL_DIR=$(dirname "$(realpath <skill-md>)")
   ```

   `realpath` resolves symlinks, which matters because most hosts install
   skills as symlinks into their own skill directory. Reuse `$SKILL_DIR` for
   every `reference/<x>` and `scripts/<x>` reference below. Do **not** hardcode
   a host-specific skill path or search candidate paths. The install
   destination varies by host and scope; helpers are always next to the
   loaded `SKILL.md`.

1. **Determine input sources.** Check in this order:
   - Arguments passed by the user (file paths, directory paths, URLs).
   - `personal-sources.yml` in `$XDG_CONFIG_HOME/humanize/` or the repo root.
   - If neither exists, ask the user for writing sample locations.

## Phase 1: Source Ingestion

1. **Resolve inputs.** Arguments (paths/URLs) take priority over
   `personal-sources.yml`, which takes priority over asking the user.

2. **Validate sources.** Confirm paths exist and identify types. For
   directories, scan recursively for supported formats: `.md`, `.rst`,
   `.txt`, `.html`, `.adoc`, `.pdf`, `.docx`.

3. **Prepare text.** Run `python3 "$SKILL_DIR/scripts/extract-text.py"`
   for non-plaintext formats (PDF, DOCX, etc.). Fetch URLs with the host's
   web-fetch tool.
   Write the extracted plain text into the scratch directory
   `.test-output/voice-gen/`, one file per source, named
   `voice-<source-label>.txt`. That directory is the corpus every later step
   reads; nothing downstream re-reads the originals.

   `analyze-voice.py` accepts either a single file or a directory. Given a
   directory it picks up `voice-*.html` and `voice-*.txt` first. If it finds
   none, it falls back to every `.html`, `.txt`, `.md`, and `.rst` file
   sitting directly inside. It does not recurse, and it drops any file under
   100 characters. Keep the corpus flat so nothing goes missing.

4. **Dispatch parallel read-only subagents.** One per source or logical group.
   Each subagent receives the content of `reference/subagent-prompt.md` as
   instructions, with `reference/profile-schema.md` appended for format
   context. Subagents return structured voice analysis covering all nine
   dimensions from the subagent prompt. If the host cannot dispatch
   subagents, run the same prompt against each source in turn in the main
   session.

5. **Generate the statistical draft.** Run:

   ```bash
   python3 "$SKILL_DIR/scripts/analyze-voice.py" .test-output/voice-gen/ \
       -o .test-output/voice-gen/draft-<type>.local.md --force
   ```

   The script prints only progress lines to stderr. Everything of value goes
   into the file named by `--output` / `-o`. What lands there is a draft
   profile, not a metrics dump. It runs a full section for every voice trait
   the script can infer. A `## Metrics` block of raw numbers closes it out.
   Read the file back to get the statistics.

   Always pass `-o`. The default is
   `$XDG_CONFIG_HOME/humanize/voices/blog.local.md` whenever that directory
   already exists, which is usually the user's real blog profile. The script
   refuses to replace an existing file unless you pass `--force`. Pass
   `--force` only for the scratch draft above, never for a path outside
   `.test-output/voice-gen/`.

   Treat the draft as raw input for Phase 2, not as a finished profile. Its
   headings already match the ten that `reference/profile-schema.md` requires.
   The sections statistics cannot settle, humor and courtesy among them, are
   left as `<!-- EDIT -->` comments. Phase 3 and Phase 4 replace those with
   real content before the profile is valid.

## Phase 2: Synthesis

1. **Merge subagent findings.** Patterns consistent across sources are
   high-confidence traits. Patterns unique to one source signal register
   differences.

2. **Detect distinct registers.** If analyses show clear voice shifts
   between sources, flag them as candidates for separate profiles.

3. **Map to profile types.**

   | Register Signal | Profile Type |
   |----------------|--------------|
   | Informal first-person technical prose | `blog` |
   | Helpful technical Q&A, problem-focused prose | `general` |
   | Instructional second-person | `tutorial` |
   | Reference docs, READMEs, CONTRIBUTING | `code-docs` |
   | Inline code comments | `code-comments` |
   | Architecture/design docs | `code-design` |
   | Formal specification | `rfc` |
   | CHANGELOG, release bodies, version announcements | `release-notes` |
   | Papers, technical reports with citations | `academic` |

4. **Present recommendations to the user.** Example format:

   > "I found two distinct registers in your writing:
   > - **Blog** (from source A): conversational, first-person, heavy on
   >   parenthetical asides
   > - **Reference docs** (from source B): direct, second-person, terse
   >
   > I'd recommend generating `blog.local.md` and `code-docs.local.md`.
   > Sound right?"

   The user can accept, adjust the mapping, or request a single unified
   profile.

## Phase 3: Interactive Refinement

For each profile, present 4-6 decisions. One at a time, multiple choice when
possible.

**Decision categories** (select per profile based on findings):

1. **Register characterization** -- confirm formality level, audience
   assumptions, and domain context.
2. **Humor and personality** -- confirm whether humor is present, its type,
   and appropriate frequency.
3. **Analogy and teaching style** (if applicable) -- confirm patterns around
   analogies, examples, or instructional framing.
4. **Formatting conventions** -- confirm prose vs. lists preference, heading
   style, bold usage, code block conventions.
5. **Distinctive patterns** -- confirm signature devices: parenthetical
   asides, rhetorical questions, specific phrases, sentence-level habits.
6. **What this voice is NOT** -- confirm anti-patterns the profile should
   explicitly reject.

**Skip logic:**

- Unambiguous traits (e.g., active voice at 85%) are stated as findings, not
  asked about. Only present decisions where the data is ambiguous or where
  user preference matters.
- If the user says "just generate it" or passes `--no-interactive`,
  auto-resolve all decisions from the data. Present the finished profile for
  a single yes/no approval.
- If the user says "looks good, skip the rest" at any point, short-circuit
  remaining questions and generate from what you have.

## Phase 4: Profile Generation

Write `.local.md` files following `reference/profile-schema.md` format.

**Rules:**

- Use real quotes from the writing samples as examples. Never fabricate
  examples or invent quotes.
- Scale sections to their significance. Minor traits: 2-3 bullets. Major
  defining traits: full subsection with examples.
- Follow the project writing discipline: no AI vocabulary, no em dashes,
  active voice. Check against the banned word list from the Humanize project.
- Include a `## Metrics` section. Copy the `## Metrics` block out of the
  Phase 1 draft for that profile's sources. `analyze-voice.py` emits these
  keys, in this order, inside a fenced block:

  ```
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
  ```

  Carry the numbers over verbatim. Do not round them or drop keys.

**Output location:**

Create the output directory and write each profile there:

```bash
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/humanize/voices"
```

Write each profile to
`${XDG_CONFIG_HOME:-$HOME/.config}/humanize/voices/<type>.local.md`.
If that file already exists, ask the user before replacing it; it may be a
hand-tuned profile with no other copy.

This is the user-global path that the Humanize skill loads first. It works
in every project directory, not just this repo.

Tell the user where each file was written. Record the absolute path of each
one; Phase 5 needs it.

## Phase 5: Validation

1. **Scan each generated profile.** The scanner ships as a repo task, and
   `task` only finds `Taskfile.yml` when you run it from the repo root, while
   the profiles you just wrote live outside the repo in the XDG config
   directory. So change into the repo first and pass an absolute path:

   ```bash
   cd /path/to/the/humanize/repo
   task scan -- "${XDG_CONFIG_HOME:-$HOME/.config}/humanize/voices/blog.local.md"
   ```

   Everything after `--` reaches the task as `CLI_ARGS` and is forwarded to
   `pre-scan.py`, so you can list several profiles in one call. Fix any
   violations and re-scan until clean.

2. **Verify content integrity:**
   - Every example quote appears verbatim in the source writing.
   - All required sections from `reference/profile-schema.md` are present.
   - No sections are empty or contain placeholder text.

3. **Present summary:** list the generated files, pre-scan status, and offer
   the user a chance to review.

4. **Handle revisions.** If the user wants changes, edit in place and
   re-validate. Keep this loop light: change, scan, confirm.

## Important Notes

- No AI vocabulary in your own output. Follow the banned word list from the
  Humanize project. Do not use words the project bans, including Tier 1
  terms from `"$SKILL_DIR/scripts/vocabulary.py"`.
- No em dashes. Use commas, parentheses, colons, or separate sentences.
- Do not open sentences with Additionally, Furthermore, or Moreover.
- Preserve technical accuracy in all examples and quotes.
- When quoting source writing, reproduce the text exactly. Do not clean up
  or normalize the author's original words.
