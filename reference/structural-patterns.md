# Structural Anti-Patterns in AI-Generated Text

Structural patterns that flag text as LLM-generated. Used during Pass 2
(detection) and Pass 3 (transformation) of the Humanize methodology.

---

## 1. Low Burstiness (Uniform Sentence Length)

**What it looks like:** Every sentence is 15-25 words. No short punches, no
long elaborations. The text reads like it was produced by a metronome.

**Why LLMs do it:** Token generation optimizes for the statistically likely
next token, producing sentences of predictable length and complexity.

**How to fix:** Deliberately vary sentence length. A 4-word sentence followed
by a 35-word explanation creates natural rhythm. Aim for a standard deviation
of 8+ words across sentence lengths.

**Ceiling:** variation is not license for run-ons. Keep sentences under the
active voice's `max_sentence_len` (see the voice's `## Target Metrics`). Some
voices ship no `## Target Metrics` block at all, `code-design` among them. For
those the pre-scan falls back to `DEFAULT_MAX_SENTENCE_LEN = 45` words. A
50-word, four-clause sentence is a defect even when it raises the standard
deviation. Vary length *and* cap it.

**Example before:**
> The system provides robust authentication capabilities. It supports multiple
> identity providers through standardized protocols. Users can configure their
> preferred authentication method through the settings panel. The configuration
> process is straightforward and well-documented.

**Example after:**
> Authentication supports multiple identity providers: SAML, OIDC, and LDAP
> out of the box. Configuration is in the settings panel. If you need something
> beyond the built-in providers, the plugin interface lets you wire in custom
> authenticators (though fair warning, the callback dance for OAuth2 is as
> painful as you'd expect).

---

## 2. Rule of Three Overuse

**What it looks like:** "X, Y, and Z" constructions appear repeatedly.
Adjective triplets. Three-item lists. Three bullet points per section.

**Why LLMs do it:** The rule of three is a well-known rhetorical device
prominent in training data. LLMs lean on it as a default structuring mechanism.

**How to fix:** Break some triplets into pairs. Expand others into specific,
uneven lists. Vary the count.

---

## 3. Formulaic Transitions

**What it looks like:** Paragraphs connected by "Furthermore," "Moreover,"
"Additionally," "In addition to this," "It is also worth noting that."

**Why LLMs do it:** Safety-trained models produce cautious, well-connected
prose. Transition words are statistically safe connectors.

**How to fix:** Delete most transitions. Let paragraph breaks do the work. If
connection is truly needed, use contextual bridges: reference the prior point
by name, not with a generic connector.

---

## 4. Symmetric Section Structure

**What it looks like:** Three sections of equal length with parallel title
patterns ("Understanding X" / "Implementing X" / "Evaluating X").

**Why LLMs do it:** Outline generation tends toward balanced structures.

**How to fix:** Let content drive length. A complex topic gets more space. A
simple one gets a sentence. Merge thin sections. Split dense ones.

---

## 5. Negative Parallelism ("Not Just X, But Also Y")

**What it looks like:** "It's not just about performance, but also about
developer experience." / "Not only does it provide X, it also enables Y."

**Why LLMs do it:** Trained on persuasive writing that uses this device to
appear balanced and insightful.

**How to fix:** Make direct statements. "It improves both performance and
developer experience." Or separate into distinct points if they merit it.

**Structural form (mirrored antithesis):** two adjacent sentences in near
parallel with a reversal at the pivot. No fixed phrase marks it, so a
watchlist cannot catch it:

> The build cache can store compiled objects. It cannot store the flags they
> were built with.

Same subject, same verb, "can" against "cannot", halves of nearly equal
length. Nothing in the content asked for that symmetry. The shape clusters:
once a draft uses it, check the title, the opening line, and every section
closer. The pre-scan tags candidates as `mirrored-antithesis`.

**How to fix the structural form:** keep the contrast and break the symmetry.
Make one side concrete, so a short sentence faces a long one or an
abstraction faces a list: "The build cache stores compiled objects. Its key
has no field for compiler flags, target triple, or build environment."

Keep a "not Y" clause when Y names something the reader would otherwise
assume is included (a scope limit), or when it answers a real objection and
its halves differ clearly in length. "This raises the
CI timeout for integration jobs, not for unit jobs" stays, because a reader
would assume unit jobs were included. "The trouble isn't that the job skipped the lockfile check;
the pipeline never runs one" stays too.

A rewrite must not end on a new "X, not Y" tail. "The cache stores objects,
not the flags behind them" is the same mirror folded into one sentence.
State the missing half on its own terms, as in the example above.

---

## 6. Challenges-and-Future-Prospects Endings

**What it looks like:** "Despite its [positive qualities], [subject] faces
several challenges including..." followed by "However, ongoing initiatives
suggest a promising future."

**Why LLMs do it:** This is a formulaic essay-conclusion pattern baked deep
into training data from academic and Wikipedia sources.

**How to fix:** Delete these sections entirely. If challenges are real and
specific, integrate them into the relevant technical sections where they
actually apply. Never end with speculative optimism.

---

## 7. Connector Dashes (Em, En, and ASCII)

**What it looks like:** A dash doing the job of a comma, a parenthesis, a
colon, or a sentence break. Three forms count, and `scripts/pre-scan.py` flags
each of them at HIGH severity:

- Em dash, `U+2014`. The classic tell.
- En dash, `U+2013`. Usually a transliteration of the em dash. A digit-to-digit
  numeric range is exempt.
- ASCII double hyphen with a space on each side, matched by the pattern
  `\w\s--\s\w`. This is what an em dash turns into when text is flattened to
  ASCII, and it reads the same way on the page.

**Why LLMs do it:** The em dash is versatile and appears frequently in
well-edited training data. LLMs over-index on it as a stylistic device. The
other two forms inherit the habit through downstream conversion.

**How to fix:** Replace all three with the punctuation that actually fits:
commas for mild pauses, parentheses for asides, colons for introductions,
periods for new thoughts. A double hyphen is still correct as a CLI flag prefix
(`--verbose`), as a SQL comment, or inside a quoted terminal session. This
pattern is about prose. A dash standing alone in a table cell marks an empty
value and is exempt; `pre-scan.py` skips it.

---

## 8. Inline-Header Lists

**What it looks like:**
- **Authentication:** The system supports...
- **Authorization:** Role-based access control enables...
- **Audit Logging:** All operations are recorded...

**Why LLMs do it:** This is the default output format for most chatbot
interfaces (rendered Markdown).

**How to fix:** Convert to prose paragraphs if the content warrants it.
Use actual sub-headings if the items are substantial enough. For genuine
lists (feature matrices, option comparisons), tables are often better.

A removed bold lead keeps its navigation value: it becomes a heading when
#17's promotion criteria apply; otherwise the label word folds into the
paragraph's first sentence. Prose made from numbered or labelled items
keeps the enumeration visible (the numbers, or a real list), or introduces
each term before anything refers to it as "the" term.

---

## 9. Excessive Boldface

**What it looks like:** Every **key term**, **framework name**, and **concept**
is bolded, often in a "key takeaways" pattern.

**Why LLMs do it:** Trained on readmes, slide decks, and listicles that use
bold as a scanning aid.

**When it fires:** only when bold density reaches 3 per 1000 words, or when
a bold span is an inline header or bold paragraph lead (#8). The pre-scan
reports every bold span as a `bold` finding. That is a list of locations to
check, and it carries no verdict.

**How to fix:** below the threshold, author emphasis stays, unless the
active voice profile bans bold emphasis outright (Pass 4 applies that ban
as a flag; "bold only for warnings" restates this pattern and is no ban). Over the threshold, remove the least
necessary bold first, and keep warnings and first definitions. In a table,
a contrast is bold marking the same kind of value across a column or row;
remove its emphasis from every cell or from none.

---

## 10. Generic Openings and Closings

**What it looks like:**
- "In today's fast-paced digital landscape..."
- "As organizations increasingly adopt..."
- "In conclusion, we have explored..."
- "By following these best practices, you can..."

**How to fix:** Start with the point. End when you're done. No preamble, no
recap.

---

## 11. Superficial Analysis via Present Participles

**What it looks like:** "...highlighting its importance in the broader
ecosystem." / "...underscoring the significance of this approach."

**Why LLMs do it:** The -ing phrase is a statistically safe way to add a
sentence-final clause that sounds analytical without committing to a specific
claim.

**How to fix:** Either make a specific analytical claim ("which reduced build
times by 40%") or delete the phrase entirely.

---

## 12. Vague Attributions

**What it looks like:** "Experts argue that..." / "Industry reports suggest..."
/ "Research has shown that..."

**How to fix:** Name the expert. Cite the report. Link the research. If you
can't, the claim probably shouldn't be there.

---

## 13. Promotional Tone

**What it looks like:** Reads like a press release or travel brochure even when
describing mundane technical topics. "Boasts a vibrant ecosystem" / "Nestled in
the heart of the container orchestration landscape."

**How to fix:** Strip all evaluative language. State facts. Let the reader
form their own opinion.

---

## 14. Collaborative Communication Remnants

**What it looks like:** "I hope this helps!" / "Would you like me to..." /
"Let me know if you need..." / "Here's a comprehensive overview of..."

**How to fix:** Delete. These are chatbot-to-user responses, not authored text.

---

## 15. Wall of Text / Undifferentiated Density

**What it looks like:** A long paragraph of uniformly long, multi-clause
sentences carrying content that is really a list: a sequence of steps, a set of
options, or a branch of conditions, all run together as prose. Often the
by-product of over-correcting "AI uses too many lists" into "never use lists".

**Why it happens:** The pipeline's prose bias and the "lists to prose"
transformation push every structure into paragraphs, while the burstiness rule
rewards long sentences with no upper bound. Enumerable content ends up buried.

**How to fix:** Judge the content shape, then match structure to it under the
active voice's budget:
- Sequential content (do X, then Y, then Z) -> numbered steps.
- A set of parallel options or items -> a bulleted list, only if each item is
  substantial enough to stand alone (not one bullet per sentence).
- Two-plus dimensions compared -> a table.
- Genuine explanation or argument -> keep it as prose, but split the run-on
  sentences (see #1's ceiling).

The structure you introduce must still pass #8 (no inline-header lists as a
default format) and #9 (no decorative boldface), and must stay under the
voice's `structured_density_max`. A voice with no `## Target Metrics` block,
`code-design` for instance, sets no density cap, so the pre-scan will not flag
over-structuring there; judge it yourself against #8 and #9. When in doubt,
prose wins; this pattern targets buried *enumerable* content, not dense
argument.

**Example before:**
> To set up the service you first need to install the dependencies, and after
> that you should configure the database connection string in the environment,
> which then lets you run the migrations, though you must make sure the
> database is actually reachable before running them, and finally you start the
> server, remembering that it binds to port 8000 unless you override it.

**Example after:**
> Setup, in order:
>
> 1. Install dependencies: `pip install -r requirements.txt`.
> 2. Set `DATABASE_URL` in the environment.
> 3. Run migrations (`task db:init`). The database must be reachable first, or
>    you'll get a connection error.
> 4. Start the server. It binds to port 8000 unless you set `PORT`.

---

## 16. Redundant Signposting and Filler

**What it looks like:** a sentence whose content the material right before
or after it already carries. Its position only changes the name:

| Form | Example |
|---|---|
| Count-then-enumerate | "Four steps get you there:" above a four-step list |
| Heading echo | "This section covers caching." under `### Caching` |
| Promissory lead | "Retries are one piece of the story." before the two sentences that give the rest |
| Summary of the artifact above | "Five endpoints, zero coverage." under a five-row table whose coverage column already reads 0% |
| Closing flourish | A section ending on a punchy restatement of a claim made properly elsewhere |

It also covers a claim an earlier one already entails: "No replica received
the write" after "The primary rejected the write before replication."

**Why LLMs do it:** each sentence is fluent and true on its own, so nothing
flags it. The model announces, delivers, then summarizes. Restructuring
leaves scaffolding too: when Pass 3 turns bold lead-ins into headings, the
sentence that introduced them now introduces nothing.

**How to fix:** delete the sentence and read its neighbours. If nothing is
lost, it was filler, wherever it sat. Leave the slot empty; a new sentence in
the same slot is usually filler again, and the same claim in new words is
not a fix. After the cut, repair any "also", "so", "this", or similar word
that pointed at the deleted sentence.

Keep a sentence that carries a reason, navigation the reader cannot infer, a
scope limit, a real hedge (uncertainty nothing later resolves), a pre-empted
objection, or a topic sentence that absorbed a removed bold lead. "Either
lock strategy would work for me" stays when the reader needs it to weigh the
proposal. Keep a "not Y" clause when Y names something the reader would otherwise
assume is included (a scope limit), or when it answers a real objection and
its halves differ clearly in length.

A colon lead is the same shape at clause scale. "The slowdown spreads: each
query hits it, and the delay grows with table size" gestures at two claims
before stating them. Keep colon leads that label a list item,
introduce a quote, or gloss an abstraction with something concrete.

**Where to look.** Filler collects at seams. Check these positions every
time, whether or not anything there looks wrong:

- the first sentence after every heading, bold lead, or `<summary>`
- the last sentence before every heading or `</details>`
- the sentences directly before and after every table, list, code block, and
  blockquote

**Same shape elsewhere.** After any hit, search the whole document for
siblings: the same form with a different count word or different phrasing.
A hit on "Four steps get you there:" means checking for "Two caveats apply:"
and "A few options exist:" too.

**Entailment.** For each paragraph, ask whether an earlier claim already
forces this one to be true. If it does, cut it.

**Attribution.** A lead that carries attribution ("from that discussion", "in
the benchmark run") keeps the attribution when you cut the lead. "In the
load test, one number stood out: p99 latency doubled" becomes "In the load
test, p99 latency doubled."

**Closing flourish.** Delete it. A rewrite that still pivots on "X, not Y",
"all of it, not some", or a trailing intensifier ("every single time") has
not resolved it.

**Example before:**
> The cache design has a gap. It is keyed on source hash and compiler path,
> and it ignores flags. So flags never reach the key.

**Example after:**
> The cache is keyed on source hash and compiler path, and it ignores flags.

---

## 17. Heading Style

**What it looks like:** headings that fight the outline. A bold lead-in
converted mechanically keeps its inert label (`**The shape.**` becomes
`### The shape`). Headings rewritten as sentences ("Four failure modes the
retry logic misses") turn a table of contents into a list of claims.

**Why LLMs do it:** "make the headings informational" reads equally well as
"state the thesis" and "label the content", and the text alone does not say
which one the document needs.

**How to fix:** follow the voice profile's Target Metrics.

- `heading_style: noun-phrase`: a terse label that reads as a table-of-contents
  entry ("Cache Design", "Rollout Plan"). The narrative stays in the prose.
  A heading with a finite verb is a clause and fails this style, noun clauses
  included: rewrite "How the Scheduler Picks a Runner" as "Runner Selection"
  and "Why the Lock Times Out" as "Lock Timeouts". Re-casing a clause does
  not fix it.
- `heading_style: assertion`: the heading carries the section's claim ("The
  cache ignores compiler flags").
- `heading_case: sentence`: capitalize the first word and proper nouns only.
- `heading_case: title`: capitalize every word except articles, coordinating
  conjunctions, and prepositions of four letters or fewer. The first and last
  words are always capitalized: "Rolling Back a Failed Deploy", "Retries in
  the Upload Step". Code spans keep their case: ``Tuning the `max_conns`
  Setting``.
- Under either case, a name with deliberate lowercase keeps it, even as the
  first word: "etcd Snapshot Schedule", "pnpm workspace layout".
- The document's H1 title follows the same style and case.

These rules apply whatever the profile sets:

| Check | Rule |
|---|---|
| Prefixes | Strip prefixes that carry nothing ("Takeaway 2:", "Part B:"). An ordinal prefix must not survive as prose ("The second takeaway:"); fold its content into a real heading or a sentence. |
| `<summary>` lines | Not a heading; `heading_style` and `heading_case` never apply. It is the only visible description of the collapsed content, so it stays a descriptive abstract in the author's case. Remove only a count, a gloss joined by a dash, or an empty ordinal prefix: "Query plans for the six slowest reports" becomes "Query plans for the slowest reports", never "Query Plans". |
| Inert bold labels | Promote the label to a noun-phrase heading at the right level when its section runs past about three paragraphs or holds parallel items. A promoted heading must pass this pattern itself and be a true peer of the headings beside it: same heading level, same scope, and same grammatical form. Otherwise the label word folds into the paragraph's first sentence. |
| Duplicates | Flag two headings with the same text in one document. |
| Issue-number headings | Flag a heading that is only a list of issue numbers ("#412, #415"); name what the issues share. |
| Renames | Check cross-references and anchor links before renaming. |
| Fixed headings | Never rename a heading the user dictated or one a template the document follows requires (a GitHub issue template's section headings, for example). |

Check `heading_style` and `heading_case` independently; each applies only
when the profile sets it. Without `heading_style`, apply only the table above.
Without `heading_case`, leave capitalization alone.

---

## Sources

- Wikipedia:Signs of AI writing -- sections on Content, Language, Style
- GPTZero -- perplexity and burstiness analysis methodology
- Beutler Ink, "How to Spot AI Writing, According to Wikipedia" (2025)
- The Augmented Educator, "Ten Telltale Signs" (2025)
- Louis Bouchard, "How to Clean Up AI-Generated Drafts" (2025)
- Humanize maintainers, eight manual review rounds on a 9,600-word issue
  draft (2026) -- #5 structural form, #16, #17
