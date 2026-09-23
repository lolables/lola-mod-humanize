# Updating from upstream sources

How to refresh the research behind the humanize rules, and what you have to
finish by hand afterward.

Read this before running `task watchlist`. That step edits one tracked file
and leaves work behind that the test suite will fail on.

## The short version

```bash
task sources                # 1. fetch and analyze. Touches nothing tracked.
task watchlist AUTO=true    # 2. preview candidates. Still touches nothing.
task watchlist              # 3. interactive. WRITES the watchlist.
task vocab:sync             # 4. regenerate every derived copy.
                            # 5. finish by hand (see below). Not optional.
task check                  # 6. verify
```

Steps 1 and 2 are safe to run any time. Step 3 is the one to be deliberate
about, and step 5 is the one people skip.

## Step 1: fetch and analyze

```bash
task sources
```

Downloads every URL in the source registry, compares each against the previous
fetch and against the current reference files, and writes a report to
`.test-output/update-report/analysis/update-report.md`. That directory is
gitignored, so nothing tracked changes.

Needs network access and `curl`. Split the stages if you want to fetch once and
re-analyze:

```bash
task sources STAGE=fetch      # download only
task sources STAGE=analyze    # re-analyze what is already cached
```

The script is advisory by design. It reports; it never rewrites a reference
file on its own.

### Personal voice sources are optional

If `personal-sources.yml` exists, the fetch step also pulls your own writing for
voice calibration. It is not committed. Create it first if you want it:

```bash
cp personal-sources.yml.example personal-sources.yml
```

`$XDG_CONFIG_HOME/humanize/personal-sources.yml` is checked first and wins if
present. Without either file you get a warning and the rest of the run
continues normally.

## Step 2: preview the candidates

```bash
task watchlist AUTO=true
```

Prints the vocabulary candidates the analysis found and exits. Nothing is
written. Always do this before step 3 so you know what you are agreeing to.

## Step 3: apply, interactively

```bash
task watchlist
```

For each candidate you get a prompt:

```
  "spearhead" (14 occurrences in sources)
  Add to tier [1/2/3], (s)kip, (q)uit?
```

Tier 1 is the strongest AI signal, tier 3 the weakest. Press `s` to skip a word
and `q` to stop.

The prompt offers tiers 1 to 3 because those are the single-word tiers. Tier 4
(phrase-level patterns) and tier 5 (discourse markers) are added by hand, since
they need the `Role` and `Match` columns this step cannot infer. The column
reference at the top of the watchlist covers both.

Every word you accept is written to `reference/ai-vocabulary-watchlist.md`.
That file is the single source of truth for AI-vocabulary data; it is the
only tracked file this step touches.

To back out of the whole thing:

```bash
git checkout reference/ai-vocabulary-watchlist.md && task vocab:sync
```

## Step 4: regenerate the derived files

```bash
task vocab:sync
```

Reads the watchlist and rewrites the marked regions (`# BEGIN/END GENERATED:
...` or `<!-- BEGIN/END GENERATED: ... -->`) in four files:

- `module/skills/humanize/scripts/vocabulary.py`, the tier sets the scanner imports
- `AGENTS.md`, the banned-words block
- `reference/writing-discipline.md`
- `module/skills/humanize/SKILL.md`

Never hand-edit inside a generated region. `task lint` fails when a region
drifts from the watchlist; `task vocab:check` runs that same check on its own.

## Step 5: finish the job by hand

The script gets you most of the way and then stops. Four things are left,
and two of them are enforced by tests.

### Fill in the replacement strategies

A row added to tier 2 or 3 looks like this, with an empty `Ban` cell in the
middle. A tier 1 row is the same shape with `yes` in that cell:

```
| spearhead |  | (review: suggest replacements) |
```

That placeholder is the whole point of the watchlist. A row without real
alternatives tells an agent to flag a word and offers nothing to replace it
with. Write two to five concrete substitutes, matching the surrounding rows:

```
| spearhead |  | lead, head, run, drive, start |
```

Keep all three cells. A row with the wrong number makes `task vocab:sync` exit
2 with a `WatchlistError` naming the row.

### Decide whether the word is banned outright

`task watchlist` sets `Ban` to `yes` for tier 1 and leaves it empty for tiers 2
and 3. Empty means the scanner flags the word but no prose list names it, so it
never reaches the banned-word sentences in `AGENTS.md`,
`reference/writing-discipline.md`, or the skill checklist. Set it to `yes` if
the word belongs there. The column reference at the top of the watchlist
explains the rest of the schema.

### Update the entry count in README.md and docs/METHODOLOGY.md

README states the total twice (the pipeline description near the top, and
the file-tree further down); METHODOLOGY states it once. All three have to
stay within 20% of the real row count. Enforced by
`tests/test_documentation_accuracy.py::TestVocabularyClaim`. To get the
current number:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'tests'); \
  from test_documentation_accuracy import _count_vocabulary_entries as c; print(c())"
```

### Cite anything new in docs/SOURCES.md

Every URL in the registry has to appear there. Enforced by
`tests/test_consistency.py::TestScriptUrlsInSourcesDoc`.

## Step 6: verify

```bash
task check
```

Runs the reference lint, the module lint, and the test suite. On a machine
without a GPU, note that `check` includes `test:detect`, which runs model
inference on CPU and takes a long time. While iterating, prefer:

```bash
task lint && task test:python
```

## Adding a new upstream source

Sources live in a registry near the top of `scripts/update-sources.sh`. Add
both entries, keyed by the same slug:

```bash
SOURCES[my-slug]="https://example.com/article"
SOURCE_DESCS[my-slug]="One line describing what it covers"
```

Then add the citation to `docs/SOURCES.md`, or `TestScriptUrlsInSourcesDoc`
fails. Fetch it with `task sources STAGE=fetch`.

## Refreshing a voice profile

Separate workflow, same spirit. To build a profile from your own writing:

```bash
task voices:profile FROM=~/writing/blog-posts/
```

`FROM` takes a file or a directory. Left out, it uses the sources fetched by
`task sources`. The draft lands in your config directory as
`<profile-type>.local.md` and carries `<!-- EDIT -->` markers where the
statistics cannot decide for you.

Inspect what is installed with the `ls`, `cat`, `path`, `rm`, and `check`
subcommands:

```bash
task voices -- ls
task voices -- check blog
```

## Why this is not one command

Each accepted word changes what the scanner flags across every document in
every repo the skill runs against. The interactive prompt and the manual
follow-up are the review step. Automating them end to end would let a bad
source fetch quietly rewrite the rules.
