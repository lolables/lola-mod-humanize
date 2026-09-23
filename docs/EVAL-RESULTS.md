# Humanize Ollama Evaluation Results

| Parameter | Value |
|-----------|-------|
| Date | 2026-03-21 |
| VRAM limit | 10GB |
| Context window | 16384 tokens (re-run; initial runs used 2048-4096 defaults, truncating the prompt) |
| System prompt | Full Humanize skill + watchlist + structural patterns + voice profile (~26K chars, ~6.6K tokens) |
| Temperature | 0.7 |
| Test samples | 7 text samples (blog post, readme, commit message, PR description, subtle AI, promotional, mixed content) |

## Important: Context Window Matters

The initial evaluation run used Ollama's default context windows (typically
2048-4096 tokens). The system prompt alone is ~6.6K tokens, meaning most models
were working with a truncated prompt that cut off before the vocabulary
watchlist and structural patterns.

After fixing this with `num_ctx=16384`, vocabulary scrubbing improved
significantly for the better models. Weaker models (granite4, llama3.2) showed
no improvement, suggesting they lack the instruction-following capability
regardless of context size.

## Key Findings

### 1. No local model passes reliably

Across all evaluations (initial + re-run), the strict Humanize pass rate stays
below 15%. A strict pass is a conjunction (`scripts/ollama-eval.py:108-119`).
Every one of these has to hold at once:

- zero Tier 1 words
- AI-word density at or below 2.0 per 500 words
- zero banned phrases
- zero transition starters
- zero em dashes
- sentence-length SD of at least 5.0, checked once the output runs to 5 or more
  sentences
- no generation error

Miss one and the sample fails. A high grade does not imply a pass.

The full five-pass methodology is too complex for sub-14B models
to execute in a single prompt. This is expected: the skill targets frontier
models (Claude, GPT-4+).

### 2. Model ranking (with corrected context window)

Two shorthands run through every row.

T1, T2, and T3 are the vocabulary tiers from
`reference/ai-vocabulary-watchlist.md`, summarized in `docs/METHODOLOGY.md`
under Pass 1. Tier 1 is the strongest detection signal, Tier 2 is strong, and
Tier 3 covers words humans use too, so it counts only when the hits cluster.

SD is the standard deviation of sentence length in words, the burstiness proxy.
Low SD means every sentence comes out about the same length.

The Best Grade column is the letter from a 100-point deduction score
(`scripts/ollama-eval.py:122-147`). Each output starts at 100 and loses:

- 15 per Tier 1 word, 8 per Tier 2 word, 3 per Tier 3 word
- 10 per banned phrase, 5 per transition starter
- 5 per em dash, 2 per bold marker
- 15 when sentence-length SD is below 5, or 5 when it is below 8 (applied only
  once the output reaches 5 sentences)

The result is clamped to 0-100 and mapped to a letter: A at 90 or above, B at
75, C at 60, D at 40, F below 40. A generation failure scores ERR instead.
Grades are per sample; the column reports each model's best single sample.

| Rank | Model | Size | Best Grade | Primary Failure Mode |
|------|-------|------|------------|---------------------|
| 1 | deepseek-r1:8b | 5.2GB | B | Em dashes (vocabulary is clean) |
| 2 | gemma3:4b | 3.3GB | A (pass) | Em dashes on harder samples |
| 3 | qwen3:8b | 5.2GB | B | Low sentence SD, em dashes, some T1 words on promo |
| 4 | cogito:latest | 4.9GB | B | "not just" phrases, bold, T1 leaks |
| 5 | mistral:latest | 4.4GB | F | T1 words persist, low SD |
| 6 | qwen2.5-coder:7b-instruct | 4.7GB | B | Many T1/T3 words, code focus hurts |
| 7 | qwen2.5-coder:14b | 9.0GB | B | No better than 7b, 6x slower |
| 8 | llama3.1:8b | 4.9GB | B | Sometimes *adds* AI words |
| 9 | llama3.2:latest | 2.0GB | B | Ignores vocabulary ban |
| 10 | granite4:latest | 2.1GB | B | Ignores all instructions |
| 11 | granite4:tiny-h | 4.2GB | C | Same as granite4 |

A run without `--models` covers only the eight tags in `DEFAULT_MODELS`
(`scripts/ollama-eval.py:41-50`). Three rows above sit outside that set:

- rank 1, deepseek-r1:8b
- rank 7, qwen2.5-coder:14b
- rank 11, granite4:tiny-h

A default `task eval` therefore will not reproduce the top of this table. Name
those tags explicitly with `--models` to evaluate them.

### 3. Failure patterns by model family

DeepSeek-R1 (8b) is the vocabulary champion. Zero Tier 1 words across all
samples in both runs. Its reasoning step helps it follow the ban list. Primary
failure: em dashes. It understands what to remove but not what to avoid adding.

Gemma3 (4b) is the best small model. The only one to produce a clean pass on the
subtle sample. Fails on em dashes and sentence length variation on harder
inputs. Surprisingly good value at 3.3GB.

Qwen3 (8b) does good vocabulary scrubbing but produces uniformly flat output
(low sentence length SD, typically 2-5). Also prone to em dashes. The context
window fix helped it eliminate some T3 words it previously kept.

Cogito is a reasoning-focused model that thinks about the rules but still leaks
"not just X, but Y" constructions (3 occurrences on the blog post sample) and
Tier 1 words on complex inputs.

Qwen2.5-coder's code-focused training hurts text transformation. Both 7b and
14b versions performed poorly. The 14b was no better and 6x slower.

Llama family (3.1 and 3.2) treated the ban list as suggestions. Llama
3.1:8b actually *increased* AI vocabulary on the commit message sample (7 T1
words in output). Context window fix made no difference.

Granite4 are the worst performers. Essentially reproduced the input with all AI
markers intact. Context window fix made no difference.

### 4. Failure patterns by sample type

01-blog-post is the hardest. Dense AI markers in the input "infect" the output.
Best result: deepseek-r1 got B (zero AI words but em dashes and low SD).

05-subtle-ai is the easiest. Gemma3:4b passed cleanly. Deepseek-r1, qwen3, and
cogito all got B. Models are better at surgical fixes than major rewrites.

06-promotional is the second hardest. Promotional register is deeply embedded.
Gemma3:4b got B (only em dashes). All other models leaked AI vocabulary.

### 5. Most common surviving AI vocabulary

With corrected context window, the sticky words shifted:

| Word | Pre-fix instances | Post-fix instances | Tier |
|------|-------------------|-------------------|------|
| robust | 28 | 6 | T3 |
| comprehensive | 25 | 4 | T3 |
| landscape | 10 | 5 | T1 |
| holistic | 15 | 2 | T3 |
| fostering | 8 | 4 | T2 |
| navigate | 6 | 2 | T3 |

Context window fix cut "robust" survival by ~80%. The remaining instances are
concentrated in weaker models that ignore the ban list regardless.

### 6. Em dashes are the universal failure mode

After vocabulary, em dashes are the most common failure. Even deepseek-r1
(which eliminates all AI vocabulary) produces 1-3 em dashes per sample. This
is a model-level habit that even explicit "no em dashes" instructions in the
system prompt fail to override for local models.

## Recommendations

### For local model usage

1. Deepseek-r1:8b for vocabulary, gemma3:4b for short text. Deepseek
   produces the cleanest vocabulary. Gemma3 is the only model to pass any
   sample cleanly.

2. Always set `num_ctx` to at least 16384. The default context windows
   truncate the Humanize system prompt, making the vocabulary ban invisible
   to the model.

3. Post-process em dashes. No local model reliably avoids them. A simple
   regex pass to replace em dashes with appropriate punctuation would fix the
   most common failure mode.

4. Multiple light passes beat one heavy pass. Feed local models partially
   cleaned text. The subtle sample (05) had the highest pass rate.

### For the Humanize skill

1. Create a "lite" system prompt for local models (~2K tokens). Include
   only the banned word list and top-5 structural rules. The full methodology
   is wasted on sub-14B models.

2. "robust" and "comprehensive" survive most. Consider promoting them to
   Tier 1 or adding explicit replacement examples.

3. Separate content rules from formatting rules. Deepseek-r1 proves
   models can handle one but not both. A two-phase approach (vocabulary first,
   formatting second) could improve results.

## Running the evaluation

Two prerequisites. An Ollama server has to be running and reachable. Every model
you intend to evaluate has to be pulled first (`ollama pull qwen3:8b`), because
the script only queries the server. It never pulls for you, so a missing model
surfaces as a generation error.

`OLLAMA_HOST` defaults to `localhost` (`Taskfile.yml:230`), which is what you
want when Ollama runs on the same machine. The `host.containers.internal` value
below is the container case: it lets an eval running inside Podman or Docker
reach an Ollama server on the host. Verbosity is a variable rather than a
separate task, so pass `VERBOSE=true`.

```bash
# Full eval with all defaults (localhost, DEFAULT_MODELS, num_ctx 16384)
task eval

# Same, but reaching a host Ollama from inside a container
task eval OLLAMA_HOST=host.containers.internal

# Specific models, verbose output
task eval VERBOSE=true -- --models qwen3:8b deepseek-r1:8b

# Custom context window
task eval -- --num-ctx 32768
```

## Raw Data

Full model outputs are in `.test-output/ollama-eval/`.
Detailed per-evaluation reports are in `.test-output/ollama-eval/eval-report.md`.
