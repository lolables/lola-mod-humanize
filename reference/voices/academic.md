# Voice Profile: Academic

Academic and technical-research writing: papers, abstracts, literature reviews.

---

## Register

Formal, third-person, evidence-hedged. Every claim is supported by data or
attributed to a citation. No claim rests on a vague "studies suggest"; the
study is named or the assertion is dropped.

- Structure follows the abstract, then body, then references.
- Passive voice is acceptable where the actor is the method, not a person:
  "samples were normalized," not "we normalized the samples" unless the agency
  matters.
- Hedging is calibrated to the evidence. A weak result earns "suggests"; a
  replicated one earns "demonstrates."

## Sentence Structure

Complex but precise. Vary length, but do not drift into the conversational.
Define a term before it carries weight in an argument.

- Subordinate clauses qualify a claim's scope: "Under the stated assumptions,
  the bound holds for n greater than 4."
- A definition precedes its first load-bearing use, not after.
- Avoid the run-on that buries the claim. One result per sentence is still the
  default.

## Voice and Person

- Third person by default. The work, the method, and the data are the subjects.
- "We" is acceptable in methods and contribution statements: "we measured," "we
  propose." Not editorial "we" elsewhere.
- No second person. The reader is not addressed.
- Passive where the method is the actor: "the dataset was partitioned."

## Directness

- State each claim with its evidence in the same passage, not separated by
  paragraphs.
- Acknowledge limitations explicitly. A scope condition stated up front is
  stronger than one a reviewer has to find.
- No overclaiming. "Proves" becomes "provides evidence that" unless a formal
  proof is given. "Shows" requires the result to actually show it.

## Courtesy

Low warmth. Formal and impersonal. Respect is shown through rigor and through
fair representation of prior work.

- Represent cited work as its authors would recognize it. Do not strawman a
  position to make a contribution look larger.
- Disagreement with prior results is stated with the evidence, not the
  adjective: "contradicts the finding of X" with the comparison, not "the flawed
  approach of X."
- No conversational softeners and no sycophancy: no "Great question!", no "I'd be
  happy to."
- See reference/courtesy.md.

## Formatting

- Citations in the project's chosen style, applied consistently throughout. Do
  not mix numbered and author-date.
- Figures and tables are numbered and captioned; every one is referenced in the
  text.
- No em dashes. Use commas, parentheses, colons, or separate sentences.
- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## Vocabulary

- Precise domain terms, defined on first use. An acronym is expanded once.
- Avoid hype ("novel," "powerful," "significant" used non-statistically) and
  false modesty ("merely," "just a small study") alike.
- Specific quantities over qualitative gestures: "a 12 percent reduction," not
  "a large reduction."

## AI Tells To Avoid

- Vague attribution with no citation: "studies suggest," "it is widely known,"
  "researchers agree."
- Hedging without evidence: "may potentially indicate" where there is nothing to
  indicate it.
- The "Despite its challenges, X holds promise" closer that asserts optimism in
  place of a conclusion.
- Uniform paragraph length across an entire section.
- "delve into."

## What This Voice Is NOT

- Blog opinion writing with a personal stance and dry humor.
- RFC normative specification with MUST and SHOULD keywords.
- Marketing or grant-pitch copy that sells the work.

## Target Metrics

```
# Targets (human-baseline ranges, not corpus measurements)
sentence_length_sd:   6-12
first_person_per_1k:  0-4
second_person_per_1k: 0
contraction_per_1k:   0-2
hedge_per_1k:         3-10
em_dash_per_1k:       0
max_sentence_len:     50
structured_density_max: 0.20
```

---

## Basis

General conventions of peer-reviewed technical and computer-science research
writing. Not derived from any specific copyrighted work.
