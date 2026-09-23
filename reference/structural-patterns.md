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
pattern is about prose.

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

---

## 9. Excessive Boldface

**What it looks like:** Every **key term**, **framework name**, and **concept**
is bolded, often in a "key takeaways" pattern.

**Why LLMs do it:** Trained on readmes, slide decks, and listicles that use
bold as a scanning aid.

**How to fix:** Remove all decorative bold. Bold should be reserved for
genuinely critical warnings or first-definition of terms (and even then,
sparingly).

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

## Sources

- Wikipedia:Signs of AI writing -- sections on Content, Language, Style
- GPTZero -- perplexity and burstiness analysis methodology
- Beutler Ink, "How to Spot AI Writing, According to Wikipedia" (2025)
- The Augmented Educator, "Ten Telltale Signs" (2025)
- Louis Bouchard, "How to Clean Up AI-Generated Drafts" (2025)
