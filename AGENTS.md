# Humanize

Humanize is a [lola](https://lobstertrap.org/lola/) module that transforms
LLM-generated text and code to read as human-authored. It uses a six-pass
pipeline: a mechanical pre-scan (Pass 0), then vocabulary scan, structural
analysis, structural transformation, voice transformation, and
self-verification. The module installs across
Claude Code, Cursor, Gemini CLI, OpenClaw, and OpenCode via lola.

## Rules

1. **Do not use AI-characteristic vocabulary in any file.** This project exists
   to eliminate AI voice. Run `grep -inE` against the watchlist
   (`reference/ai-vocabulary-watchlist.md`) on any file you create or modify.

2. **Voice calibration sources must be human-authored.** Never cite AI-tooling
   repos (claude-*, gpt-*, llm-*, copilot, ollama, langchain, etc.) as sources
   for the voice profile. The contamination checker in `scripts/analyze-sources.py`
   enforces this.

3. **`reference/ai-vocabulary-watchlist.md` is the single source of truth for
   vocabulary data.** The tier sets in `module/skills/humanize/scripts/vocabulary.py`
   are generated from it; run `task vocab:sync` after editing the watchlist,
   never hand-edit the generated sets. Both `analyze-sources.py` and
   `ollama-eval.py` import the generated constants from `vocabulary.py` at
   runtime. The test suite enforces consistency.

4. **Reference files are lookup tables, not prose.** Keep them scannable:
   tables, short descriptions, concrete examples. The skill reads these at
   runtime and the LLM needs to extract information quickly.

5. **Test samples must have all three files:** `*.before.*`, `*.after.*`, and
   `*.rules.md`. The rules file documents exactly which Humanize passes and rules
   were applied.

6. **The skill file is a structured prompt.** Changes to `module/skills/humanize/SKILL.md`
   should maintain the pass-by-pass checklist format. Do not convert it to
   prose or narrative.

7. **Run `task validate` before committing.** It checks reference file presence,
   test sample completeness, and runs 600+ pytest tests.

8. **Run `task sources` periodically.** It fetches fresh internet sources
   and reports vocabulary changes, new patterns, and contamination issues. The
   report is advisory -- review before applying.

## Writing discipline

Apply these rules to every file you write or modify in this repo.

### Voice

Senior engineer to a peer. Active voice. First person. Vary sentence length.

### Banned

<!-- BEGIN GENERATED: banned -->
Words -- never use: delve (into), tapestry (figurative), landscape
(figurative), meticulous, pivotal, underscore (verb), intricate, interplay,
vibrant, testament (to), enduring, garner, highlight (verb), seamless,
foster, cultivate, bolster, remarkable, commendable, dive into, deep dive,
bolstered, showcasing, fostering, seamlessly, groundbreaking,
transformative, paradigm, embark (on), holistic, synergy, multifaceted,
nuanced (filler).

Phrases -- never use: "It's important to note that", "In today's
[fast-paced/digital/modern] world", "serves as a
[testament/reminder/beacon]", "a diverse array of", "boasts a
[rich/vibrant]", "commitment to [excellence/innovation]", "rich cultural
heritage", "plays a [vital/crucial/key] role", "Not just X, but also Y",
"not only (bare)", "rich tapestry", "In conclusion", "It is worth noting",
"One might argue", "This raises the question".

Never open a sentence with Additionally, Furthermore, or Moreover.
<!-- END GENERATED: banned -->

Generated from `reference/ai-vocabulary-watchlist.md`. To change this list,
edit the watchlist and run `task vocab:sync`.

### Text

- Vary section lengths. No symmetric structure.
- No "Despite [positive], faces challenges..." endings.
- No "Not just X, but also Y." State it directly.
- Bold only for genuine warnings.
- Prose over decorative lists; structure over walls of text. Match the shape
  to the content: prose for explanation and argument; lists, steps, or tables
  only for genuinely enumerable, sequential, or conditional content that reads
  faster structured. Never a bullet per sentence.
- No em dashes. Use commas, parentheses, colons, or separate sentences.
- Name every source. No "experts argue."

### Code

- Locals are short (`auth`, `db`, `cfg`). Public APIs are descriptive.
- Comments explain why, never what. No docstrings on obvious functions.
- Catch specific exceptions. Handle edge cases.
- Error messages: terse, include the failing value.
  `f"can't reach {url}"` not `"Failed to connect. Please try again."`
- No abstractions with one caller. No factories for single implementations.
- Group imports stdlib/third-party/local. Don't alphabetize within groups.
- Tighten whitespace. No blank line between every statement.
- Commit small. `"fix: auth skipping OPTIONS"` not `"Update authentication"`.

## Working in this repo

This repo has many reference files, voice profiles, test samples, and scripts.
Do not read everything into the main context. If your host supports subagents,
decompose work with them:

- **Research tasks** (finding patterns, checking consistency across files):
  dispatch a read-only research subagent with a focused question.
- **Implementation tasks** (writing profiles, updating scripts, adding tests):
  dispatch an implementation subagent with the task description, relevant file
  contents, and the writing discipline rules above. One task per subagent.
- **Validation**: always run `task validate` in the main session after
  subagent work completes, not inside the subagent.

The main session should coordinate, review, and commit. Subagents should
read, write, and report. This keeps the main context window focused on
decisions rather than file contents.

## Key commands

```bash
task setup              # install dev deps via uv
task doctor             # check those deps are present (MODE=llm for problems only)
task validate           # lint + samples + pytest (the gate for commits)
task test:python        # Python tests with coverage
task sources            # fetch internet sources, produce update report
task watchlist          # review and add new vocabulary candidates
task vocab:sync         # regenerate vocabulary.py, AGENTS.md, and other derived copies
task voices:profile     # generate voice profile (FROM=<file|dir>, else fetched sources)
task voices             # manage installed voice profiles (ls, cat, rm, check)
task eval               # Ollama model evaluation
task scan               # mechanical pre-scan for AI patterns (DIFF=true for changed lines)
task test:detect        # AI detection tests (requires torch + transformers)
task eval:detect        # Binoculars + GLTR scoring on .after.* samples
task improve            # detection analysis + generate improvement candidates
task review-candidates  # interactive review of generated candidates
```

## Adding test samples

```
tests/text-samples/NN-description.before.md   # AI-generated input
tests/text-samples/NN-description.after.md    # Human-voiced output
tests/text-samples/NN-description.rules.md    # Which rules were applied and why
```

Same pattern for `code-samples/` with the appropriate file extension.
The pytest suite validates that after files have zero Tier 1 AI vocabulary
and lower overall AI density than their before files.

## Adding vocabulary or patterns

**Vocabulary (tier words or phrases):**

1. Add a row to `reference/ai-vocabulary-watchlist.md`. It needs a `Ban` value
   (`yes`, empty, or `regex`); tiers 4 and 5 also need `Role` and `Match`. The
   column reference at the top of that file defines all three.
2. Include replacement suggestions and cite the source.
3. Run `task vocab:sync` to regenerate `vocabulary.py`, `AGENTS.md`,
   `writing-discipline.md`, and the skill file's checklist from the watchlist.
4. Run `task validate` (tests enforce consistency across files).

**Structural patterns:**

1. Add to the appropriate reference file (`structural-patterns.md` or
   `code-patterns.md`) directly.
2. Include fix strategies and cite the source.
3. Update the skill file's checklist counts if totals change.
4. Run `task validate` (tests enforce consistency across files).

## Install for testing

Install with lola directly; there is no `task` target for it. lola 0.4.5 or
newer is required, since earlier versions copy the whole repo into the module.

```bash
lola mod add -n humanize ./                            # re-run after editing sources
lola install humanize -a <assistant> --scope user      # -f to overwrite
```

`--scope user` is deliberate: lola defaults to project scope. `-a` takes
`claude-code`, `opencode`, `cursor`, `gemini-cli`, or `openclaw`.

Uninstall with `lola uninstall humanize -a <assistant> --scope user`. Only
deregister the module once nothing has it installed anywhere, because
`lola mod rm` does not clean up installs and orphans managed-section markers
on other hosts:

```bash
lola list | grep -q '^humanize$' || lola mod rm -f humanize
```

`.lola/`, `.opencode/`, `.cursor/` are gitignored: these are install
destinations or lola registry caches that can land in the working tree
during local install testing.

## Skill-relative helper paths

Both `module/skills/humanize/SKILL.md` and
`module/skills/voice-profile-generator/SKILL.md` instruct the agent to
anchor on the loaded SKILL.md path:

```bash
SKILL_DIR=$(dirname "$(realpath <skill-md>)")
python3 "$SKILL_DIR/scripts/pre-scan.py" …
cat "$SKILL_DIR/reference/ai-vocabulary-watchlist.md"
```

Do not hardcode a host-specific skill path or search candidate paths. The
install destination varies by host and scope; helpers are always next to
the loaded `SKILL.md`. Reference files are symlinks into the repo-root
`reference/` directory, which lola resolves and copies at install
time.

## What NOT to change without explicit user direction

- The tier assignments in `reference/ai-vocabulary-watchlist.md` (which words
  are tier 1/2/3, which phrases are banned): both the skill checklist and the
  pytest suite key off them. `vocabulary.py` itself is generated output;
  `task vocab:sync` rewrites it freely and needs no permission.
- The six-pass pipeline structure in `module/skills/humanize/SKILL.md`
  (Pass 0 plus five rewriting passes). Tests and detection baselines assume it.
- The bundled voice profile names in `reference/voices/`: voice loading
  resolves by name.
- The rule that the skill edits in place and never moves HEAD. It creates no
  branches, switches none, and does not stash or commit. The dirty-worktree
  refusal in `humanize-branch.sh` is what makes an in-place edit recoverable,
  so the two go together.
