# humanize

A [lola](https://lobstertrap.org/lola/) module that transforms LLM-generated text and code so it more pleasant for
humans to read. Installs across Claude Code, OpenCode, Cursor, Gemini CLI, and OpenClaw.

----

> 🤖 LLM/AI WARNING 🤖
>
> This project was written with LLM (AI) assistance.

----

## What it does

Humanize runs a six-pass transformation pipeline. Pass 0 is a mechanical
pre-scan: a script flags known tells (vocabulary hits, dash characters,
uniform sentence length) before any rewriting starts. The five rewriting
passes are:

1. **Vocabulary scan** -- flags ~95 known AI-characteristic words and phrases,
   organized by detection strength
2. **Structural analysis** -- detects 15 text patterns and 8 code patterns that
   signal AI generation (uniform sentence length, formulaic transitions,
   symmetric structure, etc.)
3. **Structural transformation** -- fixes detected patterns (lists to prose,
   symmetry to variation, deletions of formulaic elements)
4. **Voice transformation** -- applies a content-type-specific voice profile
   (sentence length variation, active voice, specificity, parenthetical asides)
5. **Self-verification** -- checks the output against a 14-point text checklist
   and 7-point code checklist

## Usage

Trigger the skill by asking your AI assistant to "humanize this", "make
this sound human", "fix the AI voice", or "remove AI tells". The skill is
auto-invoked from natural language. It does not ship a slash command.

The skill works on:
- Prose (blog posts, documentation, READMEs)
- Code (any language: naming, comments, error messages, structure)
- Mixed content (documentation with embedded code)

### Modes

- **Full mode** (default): runs all six passes on files, editing them in place.
  Requires a clean worktree, so `git diff` shows exactly what changed and
  `git checkout -- .` undoes it. The skill never switches branches or commits.
- **Input mode**: humanize a chunk of text ("humanize the last commit message",
  "humanize this paragraph") -- runs the full pipeline on the input, presents
  the result inline, offers to apply if the source is writable
- **Audit mode**: "audit this for AI patterns" -- runs passes 0-2 only, reports
  findings without changing anything
- **Code-only mode**: source code files only, skips text-specific checks
- **Batch mode**: more than 3 files, dispatches subagents per file
- **Politeness wash**: "soften this", "make this less abrasive", "make this
  friendlier" -- applies only the courtesy rewrites from `reference/courtesy.md`,
  softening blunt or hostile output without adding sycophantic filler

### Voice profiles

Nine content-type profiles ship with Humanize. The skill auto-detects the right
one from content signals; you can also name one explicitly ("humanize this as
a tutorial").

| Profile | Use for |
|---------|---------|
| `general` | Default fallback -- helpful technical prose, problem-focused |
| `blog` | Opinion-bearing posts and informal long-form writing |
| `tutorial` | Step-by-step instructional content, second-person throughout |
| `rfc` | Formal specifications with RFC 2119 keywords and numbered sections |
| `code-comments` | Inline source comments and docstrings |
| `code-design` | Architecture docs, design notes, code-adjacent prose |
| `code-docs` | READMEs, CONTRIBUTING guides, commit messages, PR descriptions |
| `release-notes` | CHANGELOG entries, release bodies, version announcements |
| `academic` | Papers and technical reports with abstract, citations, references |

### Politeness wash

A standalone mode for human-written text that is merely blunt, not AI-generated.
Trigger it with "soften this", "make this less abrasive", or "politeness wash".
The skill loads `reference/courtesy.md` and applies only the abrasive-to-courteous
rewrites at the selected register's level. It does not run the vocabulary or
structural passes, and it never adds sycophantic filler.

### Preventing AI voice at generation time

`reference/writing-discipline.md` is a
copy-pasteable block of writing rules that prevents AI-voice patterns at
generation time, reducing how much the humanize skill needs to fix after
the fact. Copy it into the project instruction file your assistant reads
(for example `AGENTS.md`).

## Research basis

The methodology draws from three research streams:

- **Wikipedia: Signs of AI writing** ([WP:AISIGNS](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)) --
  the most detailed public taxonomy of LLM writing tells, maintained by
  the Wikipedia AI Cleanup project
- **AI detection research** -- perplexity/burstiness analysis (GPTZero),
  deep learning classifiers (Pangram Labs, Copyleaks), and code detection
  (HackerRank, Span). Full citations in [docs/SOURCES.md](docs/SOURCES.md)
- **Voice profiles** -- nine content-type-specific profiles (blog, general,
  tutorial, code-comments, code-docs, code-design, rfc, release-notes,
  academic) based on general patterns in each genre

See [docs/SOURCES.md](docs/SOURCES.md) for the complete source list with URLs.

## What Humanize does NOT do

- Introduce artificial errors or fake typos
- Evade AI watermarking
- Guarantee undetectability by classifier tools
- Fix shallow or incorrect content

The goal is natural reading, not tool evasion.

## Project structure

```
module/                                     lola module (installable surface)
  AGENTS.md                                 Module-level overview for AI assistants
  skills/
    humanize/SKILL.md                       Main Humanize skill
    humanize/scripts/                       Runtime skill scripts (pre-scan, manage-voices, vocabulary)
    humanize/reference/                     Symlinks to canonical reference files
    voice-profile-generator/SKILL.md        Voice profile generator skill
reference/
  ai-vocabulary-watchlist.md     ~95 flagged words/phrases by tier, single source of truth for the vocabulary
  structural-patterns.md         15 text anti-patterns with fixes
  code-patterns.md               8 code detection signatures with fixes
  courtesy.md                    Abrasive-to-courteous rewrites (politeness wash)
  writing-discipline.md          Copy-pasteable rules for generation-time prevention
  voices/                        9 voice profiles by content type
  methodology.md                 Full six-pass methodology (Pass 0 through Pass 5)
scripts/
  analyze-sources.py             Vocabulary extraction from fetched sources
  analyze-voice.py               Voice profile generation from writing samples
  check-deps.sh                  Tooling and dependency check behind `task doctor`
  detect.py                      Binoculars + GLTR detection scoring
  detect_analyze.py              Maps flagged spans to the pattern taxonomy
  detect_candidates.py           Improvement candidate generation and review
  extract-text.py                Text extraction (PDF, DOCX, ODT, EPUB, etc.)
  lint-module.sh                 lola module layout validation
  ollama-eval.py                 Local model evaluation runner
  sync_vocabulary.py             Regenerates every derived copy from the watchlist
  update-sources.sh              Source fetching and analysis orchestrator
  update-watchlist.py            Interactive vocabulary watchlist updater
personal-sources.yml             YOUR writing samples (gitignored, see .example)
docs/
  METHODOLOGY.md                 How it works (maintainer docs)
  SOURCES.md                     All research sources with citations
  EVAL-RESULTS.md                Ollama model evaluation results
tests/
  text-samples/                  7 before/after text transformation examples
  code-samples/                  4 before/after code transformation examples
  test_*.py                      500+ pytest unit and integration tests
```

## Customization

Humanize ships with nine built-in voice profiles. To calibrate them to your own style:

### Option A: Auto-generate from your writing (recommended)

```bash
# 1. Clone this repo (the remaining steps run from its root)
git clone https://github.com/lolables/lola-mod-humanize
cd lola-mod-humanize

# 2. Create your config directories
mkdir -p ~/.config/humanize/voices

# 3. Add your writing sources
cp personal-sources.yml.example ~/.config/humanize/personal-sources.yml
# Edit: add URLs to your blog, or path: to local files/directories
# Supports: .md, .txt, .rst, .html, .pdf, .docx, .odt, .epub, .rtf

# 4. Fetch and extract text
task sources

# 5. Generate your voice profile
task voices:profile
```

This analyzes your writing for sentence structure, vocabulary register,
active/passive voice ratio, parenthetical frequency, formatting patterns,
and more. The output is a draft `<profile-type>.local.md` in your config
directory (`blog.local.md` unless you pass `--output`), with measured sections
and `<!-- EDIT -->` markers where your judgment is needed.

You can also point directly at a file or directory:

```bash
task voices:profile FROM=~/writing/blog-posts/
```

### Option B: Write it manually

Copy `reference/voices/local.example.md` to
`~/.config/humanize/voices/<profile-type>.local.md` (for a blog override, that
is `blog.local.md`) and fill in your writing patterns. The filename must carry
the profile type; a file named plain `local.md` is never read.

### Config file locations

Humanize checks for user config in this order:

1. `$XDG_CONFIG_HOME/humanize/voices/` (defaults to `~/.config/humanize/voices/`)
2. Repo-local paths (`reference/voices/*.local.md`, `personal-sources.yml`)

The XDG path is recommended because it works across all Humanize-enabled
repos. Repo-local files are gitignored and work if you prefer per-project
configuration.

### Supported document formats for local sources

Check what your system can extract:

```bash
python3 scripts/extract-text.py --capabilities
```

| Format | Tool | Install |
|--------|------|---------|
| .md .txt .rst .adoc .html .htm .org | built-in | none |
| .pdf | pdftotext | `apt/dnf install poppler-utils` |
| .docx .odt .epub .rtf .tex .latex | pandoc | `apt/dnf install pandoc` |

## Voice Profile Generator

Generate personal voice profiles from your own writing samples, with
interactive refinement.

Trigger it by asking your AI assistant to "generate a voice profile from my
writing" or "analyze my writing style". Name the paths in the request, as in
"generate a voice profile from ~/blog and ~/docs". Like `humanize`, this skill
is auto-invoked from natural language and ships no slash command.

The skill reads your writing, dispatches parallel analysis agents, detects
distinct registers (blog vs. docs vs. code), and interactively produces
`.local.md` voice profile overrides. These profiles are consumed by the
Humanize skill during voice transformation.

### What it analyzes

- Register and formality
- Sentence structure patterns
- Voice and person preferences
- Humor and personality signals
- Rhetorical devices and distinctive patterns
- Formatting conventions
- Vocabulary characteristics

### Input sources

Accepts paths (files or directories), URLs, or falls back to
`personal-sources.yml` if configured. Supports `.md`, `.rst`, `.txt`,
`.html`, `.adoc`, `.pdf`, `.docx` formats.

### Interactive mode

By default, the skill presents 4-6 decisions per profile for you to shape:
register characterization, humor style, formatting rules, distinctive
patterns, and anti-patterns. Say "just generate it" to skip interaction
and get a single approval pass at the end.

## Managing Voice Profiles

List, inspect, validate, and remove installed voice profile overrides.

```bash
task voices -- ls              # show all profiles and override status
task voices -- cat blog        # print the active blog profile
task voices -- cat --builtin blog  # print the built-in, ignoring overrides
task voices -- path blog       # print filesystem path to active profile
task voices -- check           # validate all installed overrides
task voices -- check blog      # validate a specific override
task voices -- rm blog         # remove your blog override, revert to built-in
```

In this repo the script lives at
`module/skills/humanize/scripts/manage-voices.py`. Installing the module copies
it next to the installed `SKILL.md`, so the destination depends on your
assistant and scope: each assistant has its own skill directory.

It reads and writes user overrides from
`$XDG_CONFIG_HOME/humanize/voices/` (`~/.config/humanize/voices/` by
default). Built-in profiles are listed for reference but cannot be
modified through this tool.

All subcommands accept `--mode llm` for pipe-friendly output:

```bash
task voices -- --mode llm ls
```

## Installation

Humanize is distributed as a [lola](https://lobstertrap.org/lola/) module. Use
`lola` directly. The `task` targets in this repo are for development, not
installation.

```bash
# 1. Install lola (one time). 0.4.5 or newer, because earlier versions copy
#    the whole repo, .venv/ and .git/ included, into the module.
uv tool install git+https://github.com/LobsterTrap/lola

# 2. Register this checkout with lola.
lola mod add -n humanize ./

# 3. Install it. Pass --scope user deliberately: lola defaults to project.
lola install humanize -a <assistant> --scope user
```

Replace `<assistant>` with `claude-code`, `opencode`, `cursor`, `gemini-cli`,
or `openclaw`. Add `-f` to overwrite an existing install, or `--scope project`
to install into the current directory instead of your user config.

Uninstalling mirrors it:

```bash
lola uninstall humanize -a <assistant> --scope user
```

That removes the installed files and leaves the registry entry alone, so your
other assistants keep working. Drop the registry entry only when nothing has
the module installed anywhere. `lola mod rm` does not remove installs, and
running it early orphans skills and managed-section markers on the other
hosts:

```bash
lola list | grep -q '^humanize$' || lola mod rm -f humanize
```

After installing, start a new session in your AI assistant to pick up the
skills. Both `humanize` and `voice-profile-generator` are auto-invoked
from natural-language phrases (see Usage above). There are no slash
commands.

### Update after source changes

`lola mod add` copies the source, so pulling changes is not enough on its own:

```bash
git pull
lola mod add -n humanize ./                            # refresh the registered copy
lola install humanize -a <assistant> --scope user -f   # overwrite what is installed
```

## Development

Run `task` with no arguments for a map of the targets grouped by what you are
trying to do, and `task --list-all` for the complete set.

Refreshing the research that backs the rules has its own guide, because the
apply step edits tracked files and leaves follow-up work the tests check:
[docs/UPDATING.md](docs/UPDATING.md).

```bash
task setup            # create .venv/ via uv, install pytest, pytest-cov, fpdf2
                      # (adds transformers + accelerate when torch is present)
task doctor           # check the tooling and packages are in place (MODE=llm for problems only)
task check            # lint + lint:module + test + test:detect (gate for commits)
task validate         # alias for check
task test:python      # Python tests with coverage
task sources          # fetch + analyze internet sources, produce update report
task sources STAGE=fetch    # fetch sources only (STAGE=analyze for analysis only)
task watchlist        # review and add new vocabulary candidates (AUTO=true to list only)
task vocab:sync       # regenerate every copy derived from the watchlist
task vocab:check      # verify those copies are current (also runs inside lint)
task voices:profile   # generate voice profile from fetched sources (FROM=path for a file/dir)
task voices           # manage installed voice profiles (ls, cat, rm, check)
task eval OLLAMA_HOST=host.containers.internal  # Ollama model evaluation (VERBOSE=true for detail)
task scan             # mechanical pre-scan of the repo (DIFF=true for changed lines only)
task test:detect      # AI detection tests (requires GPU + torch)
task eval:detect      # detection analysis on .after.* samples (SIZE=large for bigger models)
task improve          # run detection + generate improvement candidates (SIZE=large for bigger models)
task review-candidates # review and apply improvement candidates
```

Requires [uv](https://docs.astral.sh/uv/) and [Task](https://taskfile.dev).
Python >= 3.9.

For full test coverage, install the optional document extraction tools:

```bash
# Fedora/CentOS
dnf install poppler-utils pandoc

# Debian/Ubuntu
apt install poppler-utils pandoc
```

Tests that need these tools skip gracefully when they are missing.

For AI detection tests (Binoculars + GLTR), install torch and transformers:

```bash
uv pip install --python .venv/bin/python3 torch transformers
```

Detection tests skip gracefully without these dependencies.

### Improving Humanize with detection feedback

Humanize includes a closed-loop improvement cycle. Two statistical AI
detectors (Binoculars and GLTR) score the `.after.*` test samples, a
correlation engine maps flagged regions to the pattern taxonomy, and a
candidate generator proposes additions to the vocabulary watchlist,
structural patterns, and skill checklist. You review each candidate
before anything changes.

```bash
# 1. Install detection deps (one-time)
uv pip install --python .venv/bin/python3 torch transformers

# 2. Run detection and generate improvement candidates
task improve

# 3. Review candidates interactively (accept / reject / skip each one)
task review-candidates

# 4. Validate that accepted changes don't break anything
task validate

# 5. Re-score to confirm detection scores improved
task eval:detect

# 6. Commit
git add -A && git commit -m "fix: apply detection feedback improvements"
```

The first run downloads two HuggingFace models (~3GB total, cached in
`~/.cache/huggingface/`). On CPU, expect 30-60 seconds per sample. On
GPU, under 5 seconds.

`task improve` writes candidates to `.test-output/improvement-candidates/`
with a summary, YAML files for vocabulary/pattern/checklist proposals, and
the detection evidence behind each one. `task review-candidates` walks you
through them one at a time.

The first detection run also creates `tests/detection-baselines.yml` with
initial Binoculars scores for each sample. Commit this file. Future runs
fail if a sample's score regresses by more than 0.05 from its baseline,
catching changes that make humanized text more detectable.

For CPU-only torch (no CUDA needed, smaller download):

```bash
uv pip install --python .venv/bin/python3 torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python3 transformers
```

The default models use ~3GB VRAM. For larger, more accurate models:

```bash
task improve:large    # GPT-Neo 1.3B + 2.7B (~8GB, spills to CPU RAM)
                      # equivalent to: task improve SIZE=large
```

Or set custom models via environment variables (must be from the same model
family). See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for model selection
rules, threshold rationale, and detection architecture.

## License

MIT
