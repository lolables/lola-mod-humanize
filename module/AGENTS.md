# Humanize

Humanize is a six-pass pipeline that transforms LLM-generated text and code so
it reads as naturally human-authored. A mechanical pre-scan (Pass 0) flags known
tells by line number. Five rewriting passes then scan for AI-characteristic
vocabulary, detect structural anti-patterns (uniform sentence length, formulaic
transitions, symmetric structure), rewrite the text against a content-type voice
profile, and verify the result against a checklist.

## What this module provides

- **`humanize` skill**: the main transformation pipeline. Operates on prose,
  source code, or mixed content. Modes include full file rewrite, input-mode
  (a single chunk such as a commit message), audit-only, and batch-via-subagents.
- **`voice-profile-generator` skill**: analyzes a corpus of human-authored
  writing (paths, URLs, directories) and produces a `.local.md` voice profile
  override for the `humanize` skill, with interactive refinement.

## When to use

- Polishing a deliverable before publication: blog posts, READMEs, PR
  descriptions, commit messages, design docs.
- Auditing existing prose for AI tells without changing it.
- Generating a personal voice calibration from your own writing samples so
  `humanize` matches your style instead of the bundled defaults.

## Output contract

The `humanize` skill rewrites files in place, uncommitted, on whatever branch
the user is already on (full and batch modes), or returns the transformed chunk
inline (input mode). Audit mode reports findings only and changes nothing. The
skill never creates or switches branches, stashes, or commits; it refuses to
run against a dirty worktree so that `git diff` stays a clean review surface.

The `voice-profile-generator` skill writes `.local.md` files into the user's
voice profile directory, typically `$XDG_CONFIG_HOME/humanize/voices/`. These
overrides are loaded at runtime by the `humanize` skill and take precedence
over bundled built-ins.

## Usage

Both skills are auto-invoked from natural-language phrasing. Trigger
`humanize` by asking to "humanize this", "make this sound human", "remove AI
voice", or naming a chunk like "humanize the last commit message". Trigger
`voice-profile-generator` by asking to "generate a voice profile", "analyze
my writing", or pointing at a directory of writing samples.

## Notes for AI assistants

- Both skills carry a "Locate the skill directory" preamble at the top of
  their `SKILL.md`. Anchor on the loaded path
  (`SKILL_DIR=$(dirname "$(realpath <skill-md>)")`) and reference every
  `scripts/<x>` and `reference/<x>` helper as `"$SKILL_DIR/..."`. Do not
  hardcode a host-specific skill path or search candidate paths. The install
  destination varies by host and scope, but helpers are always next to
  the loaded `SKILL.md`. (Reference files in the source repo are
  symlinks; lola resolves and copies the targets at install time, so the
  installed skill has plain files next to `SKILL.md`.)
- Do not introduce AI-characteristic vocabulary into rewritten output.
  The watchlist at `reference/ai-vocabulary-watchlist.md` is the source
  of truth.
- Voice profile overrides at `$XDG_CONFIG_HOME/humanize/voices/<type>.local.md`
  win over bundled built-ins. Always check for them before applying a voice.
