# Humanize Acceptance Results: Filler, Clarity, and Headings

| Parameter | Value |
|-----------|-------|
| Date | 2026-09-26 |
| Skill commit | `ffa4e57` (the rule fixes listed under "Changes after measurement" landed in `2263984` through `f972992` and are unmeasured) |
| Executor | Claude, following `module/skills/humanize/SKILL.md` from this repo, Full mode, `general` voice, autonomous |
| Inputs | Two long GitHub issue drafts from one software project: a 9,600-word draft (the "tuning draft") and a 4,600-word draft (the "held-out draft") |
| Scoring | Independent judge agents; see Method |

These runs measure whether the Tighten step, patterns #16 and #17, and the
clarity catalogue catch what a human editor catches. The earlier Ollama
evaluation in `EVAL-RESULTS.md` measures something else (vocabulary and dash
scrubbing by local models).

## Method

Each run used three roles that never shared context:

1. The executor ran the skill on a scratch copy of one draft. It could not
   read the ticket, the human-edited version, or any other run.
2. The tuning-draft judge scored that draft against the defect list in the
   improvement ticket that motivated this work (clarity defects, signposting,
   terseness shapes, headings), using the human-edited final version as the
   reference shape.
3. The held-out auditor built an exhaustive defect list and a keep list for
   the held-out draft before any skill output existed, then scored the output
   against its own list.

Items whose exact text appeared in the skill's own files were marked
contaminated and scored separately. The rules for #16 and #17 were written
from the tuning draft's findings, so the held-out score is the honest one.

## Results

| Measure | Run 1 | Run 2 |
|---------|-------|-------|
| Tuning draft, prose defects fixed (same 33 uncontaminated items) | 30% | 42% |
| Tuning draft, clarity defects fixed | 2 of 10 | 3 of 10 |
| Tuning draft, headings fixed | 24 of 33 | 30 of 33 |
| Held-out draft, non-dash defects fixed | not run | 43% (47% counting partial fixes at half) |
| Facts, numbers, citations, links lost | 0 | 0 on both drafts |

Run 1 used reference files that quoted six sentences from the tuning draft
verbatim. It fixed all six and 30% of the rest. After those examples were
replaced with invented ones (run 2), two of the six came back as misses: run
1 had matched phrases, not patterns.

Held-out recall by class:

| Class | Recall |
|-------|--------|
| Heading style, signposting phrases, and sentences summarizing the table above | 100% |
| Em dashes in rendered prose | 93% |
| Entailment, duplicate claims, assert-then-prove | 33% |
| Clarity (referents, dangling modifiers, coinage, wrong conjunction) | 23% to 30% |
| Closing flourishes | 20% |
| Factual inconsistencies reported rather than edited | 38% |

## What the numbers say

- Phrase- and format-level rules work. Signpost phrases, counts before a
  list, dashes, and (in run 2) heading shape were caught almost every time.
  Closing flourishes also sit in a single sentence but need judgment, and
  were caught only 20% of the time.
- Relational judgment does not. Defects that only show when two sentences or
  two sections are read together (an earlier claim that already forces this
  one, the same claim in two appendices, a pronoun whose referent drifted) are
  caught about a third of the time.
- Results vary between runs. Across all 39 listed prose items on the tuning
  draft, run 1 fixed 16 and run 2 fixed 18, but not the same ones. Six items
  run 1 fixed were not fixed in run 2 (two of them contaminated in run 1), and
  eight items run 1 missed were fixed. Part of that change is the rule edits
  between the runs, so the variance figure is an upper bound. Judge any change
  on at least three runs and report the union and intersection, not one run.
- Protected content held. Code spans, Mermaid blocks, HTML comments, and quoted
  material were unchanged, and no hedge was hardened in run 2.
- The ticket's acceptance criterion (surface every listed defect without being
  asked) is not met, and prompt changes alone are unlikely to meet it.

## Changes after measurement

Run 2 exposed regressions caused by the new rules. These were fixed after
`ffa4e57` and have not been re-measured:

- `<summary>` lines of collapsed sections were cut down to Title Case labels,
  deleting the only visible description of hidden content.
- Author emphasis was stripped where no rule asked for it, and bold paragraph
  leads were removed without keeping their navigation. Bold leads still go
  (#8), but each now becomes a peer heading or folds its label into the first
  sentence.
- Inherited clause headings survived under the noun-phrase style.
- A cut filler sentence was sometimes replaced by a reworded one, and cuts left
  connectives such as "also" without an antecedent.
- A "not Y" clause that limited the scope of a request was dropped.
- Numbered or bold-labelled items lost their enumeration when turned into
  prose.
- Several rules the executors reported as ambiguous were settled: GitHub
  admonitions count as the author's words, a lone dash in a table cell is not a
  connector dash, lowercase brand names keep their case, and prose that
  disagrees with an adjacent table is reported rather than edited.
- A review of those fixes tightened them further. The bold rule now fires on
  density (3 per 1000 words) or inline headers rather than on every span, and
  Pass 5 edits only mechanical items and reports the rest. A wrongly cut
  sentence is restored verbatim, and pre-scan no longer flags a lone dash in a
  table cell.

## Round 3: scanner checks

The two next steps this document first proposed were built as pre-scan tags
(`verdict-lead` and `claim-echo`, commit `d68ddf7`), with Tighten requiring an
inventory row per finding. Three blind runs on the held-out draft, scored by
the same auditor against the same defect list:

| Run | Non-dash defects fixed | With half credit |
|-----|------------------------|------------------|
| Earlier single run, before the tags | 43% | 47% |
| Round 3, run 1 | 32% | 34% |
| Round 3, run 2 | 34% | 36% |
| Round 3, run 3 | 43% | 46% |
| Round 3 mean | 36.5% | 38.5% |

Across the three runs, 50% of items were fixed at least once and 26% in every
run. The stable 26% is headings, signposts, summaries of the table above, and
a few mechanical fixes.

The tags produced no measurable gain. The spread between runs (11 points) is
larger than any difference from the earlier run. On this draft the scanner
raised five `verdict-lead` flags and no `claim-echo` flag, and the model kept
most flagged sentences as the author's stance. Several verdict leads the
auditor listed never matched the tag's shape rules.

Signpost recall fell from 8 of 8 to 5 or 6 of 8 in every run. The likely
cause is the keep rules added after run 2 (keep a lead's navigation, keep a
topic sentence that absorbed a bold lead), which made runs more conservative.
Three runs cannot separate that from noise.

One run promoted 19 bold paragraph leads to headings, and 8 of them state
claims, which the house style forbids. Heading promotion is still left largely
to judgment.

After this measurement the tags were kept as LOW-severity hints for human
reviewers, and Tighten no longer requires an inventory row per finding.

## Next steps

Prompt and scanner changes have stopped moving the mean. What remains:

1. Measure before tuning. Any rule change needs at least three runs per draft
   to be distinguishable from noise.
2. Relational defects (entailment, cross-section restatement, clarity) are
   where recall is lowest, and neither the rules nor the tags reach them
   reliably. A second model pass dedicated to those classes, or a human
   review step, is the remaining lever.

## Limitations

- The executor and the judges are the same model family, so shared blind spots
  are possible.
- The held-out ground truth is one auditor's list. It marked its judgment calls
  "(soft)"; on the non-soft items alone, held-out recall was 60%.
- Two drafts from one project and one author. Results on other genres are
  unmeasured.
- The pre-scan sentence checks skip every blockquote, including GitHub
  admonitions (`> [!NOTE]`), which SKILL.md treats as the author's own words.
  The model checks admonition sentences by hand until the walker learns the
  difference.
