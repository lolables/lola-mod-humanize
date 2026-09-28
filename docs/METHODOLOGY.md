# Humanize Methodology: How It Works

Maintainer documentation for the Humanize skill internals.

---

## Architecture

Humanize is an agent skill, a structured Markdown prompt with supporting
reference files. It has no runtime code, no external dependencies, and no build
step. The skill works by giving the LLM a disciplined, research-backed checklist
for transforming text and code.

### Why a skill and not a script?

AI text detection operates at the semantic level. The patterns that make text
"sound like ChatGPT" are about voice, register, vocabulary distribution, and
structural uniformity. These are judgment calls, not regex matches. A script
that replaces "delve" with "explore" everywhere would produce worse output than
the original, producing stilted substitutions that break meaning and flow.

The LLM already has the capability to write naturally. What it lacks is the
discipline to consistently avoid its own statistical habits. Humanize provides that
discipline through a structured methodology.

### Components

```
module/skills/humanize/       The skill as it ships. Canonical repo path.
  SKILL.md                    The main skill. Loaded when invoked.
  reference/                  Symlinks back to the top-level reference/ tree.
  scripts/vocabulary.py       Shared vocabulary constants. Generated from the
                              watchlist by `task vocab:sync`; do not hand-edit.
  scripts/pre-scan.py         Mechanical scanner: vocabulary hits, banned phrases,
                              formulaic transitions, with line numbers.
  scripts/manage-voices.py    Voice profile management (ls, cat, rm, check).
  scripts/humanize-branch.sh  Git worktree safety check. Never moves HEAD.
reference/*.md                Lookup tables and rules. Read during execution.
scripts/analyze-sources.py    Internet source analysis and vocabulary extraction.
scripts/analyze-voice.py      Voice profile generation from writing samples.
scripts/detect.py             Binoculars and GLTR detection, run locally on
                              torch + transformers.
scripts/detect_analyze.py     Maps flagged spans from detect.py onto the Humanize
                              pattern taxonomy.
scripts/detect_candidates.py  Turns that analysis into vocabulary, pattern, and
                              checklist candidates staged for human review.
scripts/extract-text.py       Text extraction (PDF, DOCX, ODT, EPUB, etc.).
scripts/lint-module.sh        Structural lint for the lola module layout.
scripts/ollama-eval.py        Local model evaluation runner.
scripts/update-sources.sh     Source fetching orchestrator.
scripts/update-watchlist.py   Interactive updater that folds new candidates into
                              the watchlist.
scripts/sync_vocabulary.py    Regenerates every derived copy from the watchlist.
tests/text-samples/           Before/after text examples with rule annotations.
tests/code-samples/           Before/after code examples with rule annotations.
tests/test_*.py               480+ pytest unit and integration tests.
docs/SOURCES.md               All research sources with full citations.
```

The top-level `reference/` tree is canonical. `module/skills/humanize/reference/`
is symlinks pointing back at it, plus a couple of module-local example files, so
edit the top-level copy and the module picks the change up.

The installed skill lands in a host-specific skill directory that depends on
the assistant and scope; that is not a path in this repo.

## The Six-Pass Pipeline

### Pass 0: Mechanical pre-scan

`module/skills/humanize/scripts/pre-scan.py` reads the target files and reports
everything a regex can catch, with line numbers. Three categories:

- Vocabulary: tiers 1-3, banned phrases, formulaic transitions.
- Dashes: em, en, and the ASCII form in prose.
- Structure: inline-header lists, boldface, negative parallelism, the
  challenges-and-future ending, generic openers and closers, collaborative
  remnants.

With no file arguments the scanner walks every tracked, non-binary file in the
repo. `--diff` narrows it to the changes on the current branch, which is the
useful mode when humanizing a PR.

The output is a map of where to look, not a list of things to delete. A Tier 3
word can be the right word in technical context. An em dash inside a quoted
terminal session is not an AI pattern, and an inline-header list in a changelog
is the correct format. Passes 1 through 3 supply the judgment; Pass 5 re-runs
the same scanner on the transformed output and compares the two reports.

Two cases skip this pass. Conversation chunks (pasted text, earlier model
output) have no file for the tool to read. So does any run where the script is
out of reach, which falls back to manual scanning.

### Pass 1: Vocabulary scan

Scans input against `reference/ai-vocabulary-watchlist.md`. The watchlist
organizes ~95 words and phrases into five tiers by detection strength:

- **Tier 1 (strongest):** Words with 200%+ frequency increase post-2022.
  "delve", "tapestry", "landscape" (figurative), "meticulous", "pivotal".
- **Tier 2 (strong):** GPT-4o era markers. "showcasing", "fostering",
  "bolstered".
- **Tier 3 (moderate):** Common LLM words that humans also use. "crucial",
  "robust", "comprehensive". Flagged only when clustered.
- **Tier 4 (phrases):** Multi-word constructions. "It's important to note
  that", "In today's fast-paced world", "serves as a testament".
- **Tier 5 (discourse):** Overused transitions. "In conclusion",
  "Furthermore", "Moreover".

The decision framework is: replace Tier 1 almost always, replace Tier 2 when
alternatives exist, replace Tier 3 only when clustered, replace Tier 4 always,
delete/replace Tier 5 based on whether the connection is needed.

### Pass 2: Structural analysis

Checks for 17 text patterns and 8 code patterns from the reference files.
Key insight: these patterns are detectable because LLMs produce **uniform**
output. Human writing varies: paragraph lengths differ, sentence complexity
oscillates, transitions are contextual rather than formulaic. Pattern 15 (wall
of text) is the counterweight to the prose bias: it flags enumerable content
buried in over-long paragraphs and restructures it. How far it can go is set by
`structured_density_max` in the active voice profile, the cap on what share of
non-blank lines may be headings, list items, or table rows (0.35 in `general`).

The most reliable structural indicators (from research):
- **Low burstiness** (uniform sentence length) -- measurable, hard to fake
- **Formulaic transitions** -- "Furthermore", "Moreover", "Additionally"
- **Symmetric structure** -- equal-length sections with parallel titles
- **Challenges/Future endings** -- "Despite its X, faces challenges..."

### Pass 3: Structural transformation

Fixes are applied in priority order: zero-risk deletions first (collaborative
remnants, generic openers), then structural changes (transitions, section
balance), then tonal changes (promotional flattening, attribution specificity).
Each fix changes only what a pattern flagged. The scanner lists every bold
span, but bold goes only when density reaches 3 per 1000 words or the span
is an inline header or paragraph lead; below that, author emphasis stays
unless the voice profile bans bold emphasis outright. A bold lead that goes becomes
a heading that is a true peer of its siblings (same level, scope, and
grammatical form), or the label word folds into the paragraph's first sentence.

### Pass 4: Voice transformation

Applies the target voice profile. When auto-detection finds no specific
signal, the skill prompts the user to confirm the default `general` voice
or pick another. `general` targets helpful, problem-focused technical
prose: pragmatic, active voice, specific details, recommendation-bearing
without strong personality.

Nine voice profiles live in `reference/voices/` (academic, blog, code-comments,
code-design, code-docs, general, release-notes, rfc, tutorial), auto-detected by
content type. Personal overrides go in `$XDG_CONFIG_HOME/humanize/voices/`, the
root of the project being humanized (`reference/voices/*.local.md`), or the
installed skill's own `reference/voices/`, checked in that order. A
project-root override counts only when git does not track it, no part of its
path is a symlink, and it is not inside a nested repo or submodule. The skill
resolves the path with `manage-voices.py path --for <file>`, which applies
those checks, and tells the user when a project-root profile is in use. A
profile is style guidance only: the skill never follows tool, command,
file-access, or network instructions found in one. The agent still acts on
its register and wording guidance, so a repo's author must not be able to
inject a profile by committing one or a symlink to one of the user's files.

A personal profile can be auto-generated from writing samples via
`task voices:profile`, which analyzes sentence structure, vocabulary register,
active/passive ratio, parenthetical frequency, formatting patterns, and humor
signals. Key characteristics are measurable: sentence length standard deviation,
parenthetical frequency, active/passive ratio, contraction rate, lexical
diversity.

### Pass 5: Self-verification

A checklist with 20 text checks and 7 code checks. Each check has a threshold
(e.g., "AI vocabulary density <= 2 per 500 words"). The sentence-length SD
check reads the pre-scan's verdict against the voice's range instead of a hand
count, and quoted material is exempt from the dash and bold checks. A GitHub
admonition is the author's own text, so it gets no such exemption and the
checklist covers it. Pass 5 fixes only mechanical items (dashes, double
colons, bold density, watchlist vocabulary, generic openers and closers,
collaborative remnants, heading case and style, the sentence-length ceiling) and names each fix. Relational problems such as
filler, entailment, and clarity are reported without edits. Failures are
reported with context, because sometimes a "failure" is acceptable (a Tier 3
word that's genuinely the best choice).


## Research Foundation

The methodology draws from three research streams:

### 1. Statistical detection (perplexity and burstiness)

AI text has **low perplexity** (predictable word choices) and **low burstiness**
(uniform sentence complexity). Humanize addresses this by increasing both:
vocabulary variation and sentence length oscillation.

Key limitation: perplexity-based detection has high false-positive rates for
non-native English speakers (61.22% per Liang et al. 2023) and well-known texts.
Humanize targets the uniformity behind low perplexity scores rather than the
scores themselves.

### 2. Linguistic pattern detection (Wikipedia/editorial)

The Wikipedia AI Cleanup project maintains the most detailed public taxonomy of
LLM writing tells. Their field guide covers vocabulary, structure, formatting,
and markup across multiple LLM generations. Humanize's watchlist and structural
pattern list are derived primarily from this source.

### 3. Code detection (classifier-based)

Code detectors use feature extraction (naming conventions, comment patterns,
error handling, import organization) fed into classifiers. Best accuracy is ~95%
for Python/JS/TS. Humanize addresses the features these classifiers look for.

## Updating the Methodology

### Adding new AI vocabulary

Edits go to the top-level `reference/` tree, the canonical one. The module's
`reference/` directory symlinks to it, so there is nothing to copy over.

When new LLM-characteristic words are identified:

1. Add the word to `reference/ai-vocabulary-watchlist.md` in the tier its
   frequency data supports. Fill every column the tier's header declares; the
   column reference at the top of that file explains what each one drives.
2. Include replacement suggestions next to it.
3. Note the source and the frequency data.
4. Run `task vocab:sync` to push the change into `vocabulary.py` and the prose
   copies. Nothing reads the watchlist at runtime, so a word that skips this
   step is never scanned, and `task lint` fails until it is run.

### Adding new structural patterns

When new structural tells are documented:

1. Add the pattern to `reference/structural-patterns.md` with examples.
2. Add a fix strategy.
3. Update the Pass 2 checklist in `module/skills/humanize/SKILL.md`.

### Updating the voice profile

The voice profile can be regenerated at any time:

```bash
# From cached personal sources (after task sources)
task voices:profile

# From a specific file or directory
task voices:profile FROM=~/writing/blog-posts/
```

The generator (`scripts/analyze-voice.py`) measures sentence statistics,
vocabulary register, voice/person ratios, formatting preferences, and humor
signals. The output is a draft with `<!-- EDIT -->` markers where statistical
analysis falls short (directness, humor intent, distinctive patterns).

Regenerate when:
- You add new writing samples to `personal-sources.yml`. That file is
  gitignored and does not ship; copy `personal-sources.yml.example` to
  `personal-sources.yml` first and fill in your own entries.
- Your writing style has evolved (compare raw metrics blocks)
- You want to calibrate for a different context (e.g., formal vs casual)

## AI Detection Feedback Loop

The detection system scores `.after.*` test samples with two statistical
detectors, maps results to the pattern taxonomy, and generates improvement
candidates for human review.

### Detectors

**Binoculars (ICML 2024)** computes a cross-perplexity ratio between two
language models. Machine-generated text gets similar perplexity from both
models (ratio near 1.0); human text diverges (ratio >> 1.0). Returns a
single 0.0-1.0 score.

The two models take fixed roles, and the code names them that way. The
performer supplies the next-token probability distribution over the text; the
observer scores that same text with its own distribution. The ratio divides
the cross-perplexity of the pair by the performer's own entropy, so it measures
how much the observer disagrees with the performer relative to how uncertain
the performer already was. `BINOCULARS_OBSERVER` and `BINOCULARS_PERFORMER`
select the two models.

**GLTR** checks where each token falls in the model's predicted vocabulary
distribution. AI text clusters in the top-10 predictions (60-80%+); human
text spreads across top-100 and beyond. Returns per-token ranks and flags
clusters of highly predictable tokens.

### Model selection rules

Both Binoculars models must come from the **same model family** (e.g. both
GPT-2, both OPT, both falcon-rw). The algorithm relies on models sharing
enough internal structure that machine-generated text looks equally
predictable to both. Cross-family pairs (e.g. OPT + Mistral) disagree on
everything and produce all-zero scores. We tested this: OPT-6.7b + Mistral-7B
gave 0.000 across all 11 samples.

Default pair: `tiiuae/falcon-rw-1b` (observer) + `gpt2-xl` (performer).
These are the smallest viable pair, using ~3GB VRAM in fp16. Both are
ungated (no HuggingFace account needed).

Large pair (`task improve:large`, or `SIZE=large` on `task eval:detect`):
`EleutherAI/gpt-neo-1.3B` (observer) + `EleutherAI/gpt-neo-2.7B` (performer),
also ungated, also one family. That preset exports
`BINOCULARS_SEQUENTIAL=true`, so the two models never sit in VRAM together.
Slower than the default pair, and see "Small vs large model behavior" below
before reading anything into its absolute scores.

GLTR reuses the Binoculars performer model to avoid loading a third model.

### Threshold rationale

From the first detection run (2026-03-23) with default models:

| Sample type | Binoculars range | GLTR top-10 range |
|-------------|-----------------|-------------------|
| Prose .after.* | 0.21 - 0.59 | 64 - 87% |
| Code .after.* | 0.009 - 0.093 | 77 - 94% |

CI gate thresholds (in `tests/test_detection.py`):
- Prose: 0.60 (blog posts, READMEs, high-stakes text)
- Short: 0.65 (commit messages, PR descriptions)
- Code: 0.70 (code comments, docstrings)

The prose threshold sits just above the documented prose ceiling (0.59) so
that the gate catches genuine regression rather than the sample corpus's
documented worst case. Day-to-day drift is caught by the ±0.05 regression
tolerance against `tests/detection-baselines.yml`.

These thresholds intentionally allow some AI-characteristic signal through.
See "The overcorrection trap" in `reference/methodology.md`.

### Small vs large model behavior

The default small pair (falcon-rw-1b + gpt2-xl) and the large pair
(gpt-neo-1.3B + gpt-neo-2.7B) produce very different score distributions:

| Sample | Small pair | Large pair |
|--------|-----------|-----------|
| 01-blog-post | 0.587 | 0.621 |
| 02-readme | 0.259 | 0.579 |
| 05-subtle-ai | 0.581 | 0.634 |
| 01-auth-service (code) | 0.093 | 0.599 |
| 03-go-naming (code) | 0.009 | 0.517 |

The small pair has wide spread (0.009-0.587) with clear separation between
prose and code. The large pair compresses everything into a narrow 0.52-0.63
band. Both models in the large pair were trained on The Pile (which includes
code), so they find code moderately predictable from both sides, reducing
discrimination.

**Practical consequence:** the CI gate thresholds are calibrated for the
default small models. The `task improve:large` preset is for advisory
benchmarking: use it to rank samples relative to each other and spot which
ones the larger models flag hardest, not to make absolute "human" vs
"machine" calls. The normalization sigmoid (`_normalize_binoculars`) would
need recalibration per model pair to produce meaningful absolute labels
with larger models.

### Code vs prose separation

Code tokens (keywords, syntax, imports) are inherently top-10 predictable
regardless of authorship. Without separation, GLTR flags every `import`,
`self`, and `return` as suspicious, and the candidate generator floods with
programming keywords instead of AI-tell vocabulary.

GLTR span detection uses content-type-specific parameters:
- Prose: window=5 tokens, threshold=70% top-10. Catches clusters of 4+
  predictable tokens that indicate formulaic phrasing.
- Code: window=8 tokens, threshold=90% top-10. Only flags very long
  stretches of maximally predictable code (boilerplate patterns).

Vocabulary candidates are extracted from prose samples only.

### Dual-signal candidate filtering

A word becomes a vocabulary candidate only when both signals fire:
1. GLTR flags it as highly predictable in a flagged span
2. The word matches `CANDIDATE_PATTERNS` from `vocabulary.py` (research-
   backed AI-characteristic words with 200%+ post-2022 frequency increase)

Without the dual-signal filter, common domain words ("config", "container",
"security") become candidates because they're GLTR-predictable in technical
prose. They're predictable because they're domain vocabulary, not because an
AI wrote them.

### Tokenizer artifacts

GPT-2's BPE tokenizer splits identifiers into subword fragments:
`@dataclass` becomes `@ dat ac lass`. When span text is reconstructed from
tokens, these fragments produce garbage patterns ("lasses import dat ac
lass"). The `_clean_span_words()` filter in `detect_candidates.py` strips
fragments under 3 characters and common punctuation.

### Network behavior

Model loading uses `local_files_only=True` when weights exist in
`~/.cache/huggingface/hub/`. The first run downloads models (~3GB for
default, ~16GB for large). All subsequent runs are fully offline. Without
this, the transformers library sends IP, model names, and User-Agent to
HuggingFace servers on every load.

### Memory management

`detect.py` picks one of two loading strategies at startup. It estimates the
fp16 size of the observer and the performer, and if the pair needs more than
70% of total VRAM it switches to sequential mode. Setting
`BINOCULARS_SEQUENTIAL=true` forces the same switch regardless of the estimate,
which is what the large-model preset does.

Both-resident mode is the fast path: each model is loaded in fp16, moved to the
GPU once, and reused for every sample.

Sequential mode keeps one model in VRAM at a time. The observer loads, runs a
forward pass, and its logits are moved to CPU before the model is deleted and
`torch.cuda.empty_cache()` runs. Then the performer loads and does the same.
The performer stays resident just long enough for GLTR to reuse it on that
sample, and is cleared at the start of the next one. Peak VRAM is therefore set
by the larger single model, not by the pair.

`device_map="auto"` is deliberately not used. Splitting layers across GPU and
CPU breaks some architectures (OPT among them) when embeddings land on a
different device than the inputs. Sequential loading costs a reload per sample
but works with every model.

Either way, intermediate tensors are deleted and `torch.cuda.empty_cache()` is
called after each sample. Without that, the 11-sample loop accumulates
allocations until it hits OOM.

## Limitations

- Not a detector evasion tool. Works on readability, not scores.
- Cannot fix bad content. Shallow analysis stays shallow after Humanize.
- Voice profile is approximate. No prompt can perfectly replicate a
  specific human's voice. It can only approximate the statistical patterns.
- Single-model calibration. Trained against ChatGPT/Claude-era patterns.
  Future LLMs with different tells will need watchlist updates.
- No watermark handling. Watermarked text is a separate problem that Humanize
  does not address.
