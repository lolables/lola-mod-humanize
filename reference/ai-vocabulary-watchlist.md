# AI Vocabulary Watchlist

Words and phrases that statistically cluster in LLM-generated text. Organized
by detection strength and era. Use this as a lookup during Pass 1, the
vocabulary scan, which is defined in `reference/methodology.md` and in
`module/skills/humanize/SKILL.md`.

## How to Use This List

- **High-signal words** appearing 3+ times in a document are a strong indicator.
- **Context matters.** "Crucial" in a FIPS compliance document is fine. "Crucial"
  describing a color picker library is suspect.
- **Not every occurrence needs replacement.** The goal is to reduce density below
  detection thresholds (~2 flagged words per 500 words of output).

## Column reference

This file is the single source of truth for the vocabulary. Every other copy
is generated from these tables by `task vocab:sync`, so the columns are a
contract rather than presentation. Tiers 1 to 3 carry `Ban`; tiers 4 and 5 add
`Role` and `Match`.

- **The first column is the term.** A slash (`dive into/deep dive`) makes each
  side its own scan term, and the first side is the one prose lists name. A
  parenthetical (`delve (into)`) is dropped for matching and kept for display.
- **`Ban`** is `yes`, empty, or `regex`. `yes` puts the term in the banned-word
  and banned-phrase lists rendered into `AGENTS.md`,
  `reference/writing-discipline.md`, and the humanize `SKILL.md`. Empty means
  the scanner still flags the term, but no prose list names it. `regex` means
  a hand-written pattern in `pre-scan.py` enforces the row, so it is
  deliberately left out of the generated lists.
- **`Role`** is `opener`, `closer`, or empty, and applies to tiers 4 and 5 only.
  It fills `GENERIC_OPENERS` and `GENERIC_CLOSERS` in `vocabulary.py`. A row can
  carry both `Ban` and a `Role`.
- **`Match`** gives the literal string the scanner looks for when it differs
  from the display form, which is what a bracketed alternate needs
  (`plays a [vital/crucial] role` matches on `plays a vital role`). Several
  forms can be separated by commas. Left empty, the term itself is the match.
- **The last column is prose** for a human or an agent to read. Nothing parses
  it, so write whatever helps.

`TRANSITION_STARTERS` is not driven by `Role`. It collects the tier 3 terms
carrying the literal marker `(sentence-start)`, such as
`Additionally (sentence-start)`.

Every row needs exactly as many cells as its tier's header. A row that does not
makes `task vocab:sync` exit 2 with a `WatchlistError` naming the row.
`task watchlist` writes tiers 1 to 3; tier 4 and 5 rows are added by hand. See
`docs/UPDATING.md` in the humanize repository for the full refresh workflow.
That path is deliberately not a link: this file also ships inside the installed
skill, where there is no `docs/` directory to point at.

---

## Tier 1: Strongest Indicators

These words saw 200%+ frequency increases in post-2022 text. Their presence in
clusters is one of the strongest AI tells.

| Word/Phrase | Ban | Replacement Strategy |
|---|---|---|
| delve (into) | yes | explore, examine, dig into, look at, get into |
| tapestry (figurative) | yes | mix, combination, fabric, history, tradition |
| landscape (figurative) | yes | field, space, market, world, scene, domain |
| meticulous/meticulously | yes | careful, precise, thorough, painstaking, exacting |
| pivotal | yes | important, key, critical, decisive, central |
| underscore (verb) | yes | show, reveal, demonstrate, make clear, reinforce |
| intricate/intricacies | yes | complex, detailed, involved, fiddly, tricky |
| interplay | yes | interaction, relationship, tension, connection, dynamic |
| vibrant | yes | active, lively, energetic, thriving, busy |
| testament (to) | yes | proof, evidence, sign, demonstration, indicator |
| enduring | yes | lasting, persistent, long-standing, durable, ongoing |
| garner | yes | earn, gain, attract, receive, collect, win |
| highlight (verb) | yes | show, point out, call out, flag, mark |
| seamless | yes | smooth, direct, drop-in, automatic, [name the step that disappears] |
| foster | yes | encourage, build, support, promote, grow |
| cultivate | yes | build, grow, develop, establish, train |
| bolster | yes | strengthen, support, reinforce, shore up, boost |
| remarkable | yes | striking, unusual, surprising, [give the number instead] |
| commendable | yes | good, solid, well handled, [name what was done right] |
| dive into | yes | explore, examine, walk through, break down, [just start explaining] |
| deep dive | yes | walkthrough, breakdown, close look, [name what you examined] |

## Tier 2: Strong Indicators

Common in GPT-4o era output. Still heavily flagged.

| Word/Phrase | Ban | Replacement Strategy |
|---|---|---|
| align with |  | match, fit, support, follow, agree with |
| bolstered | yes | strengthened, supported, reinforced, boosted |
| showcasing | yes | showing, displaying, presenting, demonstrating |
| fostering | yes | encouraging, building, developing, promoting, growing |
| highlighting |  | showing, pointing out, drawing attention to, noting |
| emphasizing |  | stressing, focusing on, calling out, noting |
| enhance |  | improve, strengthen, boost, increase, extend |
| enhanced |  | improved, strengthened, upgraded, extended, better |
| showcase |  | show, demonstrate, present, feature, demo |
| innovative |  | new, original, unconventional, [say what it does differently] |
| emphasized |  | stressed, called out, focused on, repeated |
| cutting-edge |  | latest, current, experimental, [name the version or technique] |
| showcased |  | showed, demonstrated, presented, featured |
| resonate with |  | appeal to, land with, connect with, speak to |
| encompassing |  | covering, including, spanning, made up of |
| ever-evolving |  | changing, shifting, active, [name what actually changed] |

## Tier 3: Moderate Indicators

Common in general LLM output but also used by humans. Flag when clustered.

| Word/Phrase | Ban | Replacement Strategy |
|---|---|---|
| Additionally (sentence-start) |  | Also / And / [merge sentences] / [delete] |
| Furthermore (sentence-start) |  | [delete or merge] / Beyond that / What's more |
| Moreover (sentence-start) |  | [delete or merge] / On top of that |
| crucial |  | important, critical, essential, key, vital |
| robust |  | strong, solid, reliable, capable, proven |
| comprehensive |  | full, complete, thorough, broad, wide-ranging |
| seamlessly | yes | smoothly, cleanly, without friction, naturally |
| groundbreaking | yes | new, novel, first-of-its-kind, [say what it did first] |
| transformative | yes | significant, game-changing, major, fundamental |
| compelling |  | strong, convincing, persuasive, clear |
| facilitate |  | enable, support, allow, help, make possible |
| illuminate |  | clarify, explain, shed light on, reveal |
| endeavor |  | effort, project, attempt, work, initiative |
| paradigm | yes | model, framework, approach, way of thinking |
| harness |  | use, tap, put to work, apply, run |
| navigate (figurative) |  | handle, manage, work through, deal with |
| realm |  | area, domain, field, space, world |
| leverage (verb) |  | use, apply, take advantage of, build on |
| embark (on) | yes | start, begin, launch, kick off, undertake |
| holistic | yes | whole, overall, end-to-end, system-wide |
| synergy | yes | overlap, combined effect, fit, payoff from pairing them |
| multifaceted | yes | many-sided, layered, complex, has several parts |
| nuanced (filler) | yes | subtle, detailed, mixed, case-by-case, [state the distinction] |
| highlighted |  | showed, pointed out, called out, flagged, noted |
| noteworthy |  | notable, unusual, worth knowing, [say why it matters] |
| utilize |  | use, apply, run, work with |
| paramount |  | critical, essential, top priority, [say what breaks without it] |
| invaluable |  | useful, essential, hard to replace, [say what it saves] |
| thrive |  | grow, succeed, do well, hold up, [give the metric] |

## Tier 4: Phrase-Level Patterns

Multi-word constructions that are AI-characteristic.

| Phrase | Ban | Role | Match | Replacement Strategy |
|---|---|---|---|---|
| It's important to note that | yes |  | it's important to note | [delete -- just state the thing] |
| In today's [fast-paced/digital/modern] world | yes | opener | in today's | [delete entirely] |
| serves as a [testament/reminder/beacon] | yes |  | serves as a | is / acts as / works as |
| a diverse array of | yes |  | diverse array | various / many / a range of / several |
| in the heart of |  |  |  | in / at the center of / in central |
| boasts a [rich/vibrant] | yes |  | boasts a | has / features / includes |
| nestled in/among |  |  |  | located in / set in / situated in |
| commitment to [excellence/innovation] | yes |  | commitment to excellence | [be specific about what they actually do] |
| rich cultural heritage | yes |  | rich cultural | [name the specific cultural elements] |
| natural beauty |  |  |  | [describe what's actually beautiful] |
| plays a [vital/crucial/key] role | yes |  | plays a vital role | matters / contributes / helps with |
| Not just X, but also Y | yes |  | not just | [rewrite as direct statement] |
| not only (bare) | yes |  |  | [rewrite as a direct statement; the bigram is flagged on its own, without needing the "but also" tail] |
| Despite its [positive], faces challenges | regex |  |  | [integrate specifics into prior sections] |
| stands as a |  |  |  | is |
| marks a [significant] shift |  |  |  | changed / moved / shifted |
| reflects broader [trends] |  |  |  | [name the specific trend or delete] |
| valuable insights |  |  |  | findings, results, what we learned, [state the finding] |
| unlock the [potential/power] of |  |  |  | use / enable / [say what it lets you do] |
| rich tapestry | yes |  |  | mix, combination, history |

## Tier 5: Discourse Markers to Watch

Not AI-exclusive, but overused by LLMs in specific positions.

| Pattern | Ban | Role | Match | When to Flag |
|---|---|---|---|---|
| In conclusion | yes | closer |  | Almost always -- delete or rewrite naturally |
| To summarize |  | closer |  | Almost always -- trust the reader |
| As we have seen |  | closer |  | Delete -- forward reference is fine, backward is padding |
| It is worth noting | yes |  | it is worth noting, it's worth noting, it’s worth noting, worth noting:, worth noting that | Delete -- just note it |
| I want to be clear that | yes |  |  | Delete the lead-in; the rest of the sentence is the claim |
| One might argue | yes |  |  | Name who argues this, or delete |
| This raises the question | yes |  |  | Ask the question directly |
| In this [article/section] |  | closer | in this article, in this section | Delete -- the reader knows where they are |
| As organizations increasingly |  | opener |  | Delete |
| In an era of |  | opener |  | Delete |
| In the rapidly evolving |  | opener |  | Delete |
| As the world becomes |  | opener |  | Delete |
| By following these best practices |  | closer |  | Delete |

---

## Sources

- Wikipedia:Signs of AI writing (WP:AISIGNS, WP:AIWORDS)
- Liang et al., "Monitoring AI-Modified Content at Scale" (2024)
- Gray & Dang, "ChatGPT is more likely to be perceived as male" (2024) -- word
  frequency analysis
- Kobak et al., "Delving into ChatGPT usage in academic writing through excess
  vocabulary" (2024) -- PubMed frequency analysis showing ~400% increase in
  "delve" post-2022
- GPTZero vocabulary documentation (2025)
- Beutler Ink, "How to Spot AI Writing, According to Wikipedia" (2025)
- The Augmented Educator, "Ten Telltale Signs of AI-Generated Text" (2025)
- Undetectable.ai, "Ultimate List of Common AI Words" (2025)
