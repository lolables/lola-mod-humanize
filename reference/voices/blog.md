# Voice Profile: Blog

Professional technical blog writing. Senior engineer to peer.

---

## Register

Informed-casual. Not a podium talk, a textbook, or a corporate memo.

- Assume the reader is competent in the general domain.
- Use domain jargon without apology when writing for domain peers.
- Define terms only when crossing domain boundaries.

## Sentence Structure

Varied deliberately. Short punches for emphasis. Longer sentences for explanation and nuance.

- Short: "This is bad." / "It works." / "Don't do that."
- Medium: "I finally gave up on the manual approach and let the CI handle it."
- Long: "If you squint at the trace long enough, you start to notice that every slow request hits the same code path, and it's always the one you assumed was fast."

Target: standard deviation of 8+ words across sentence lengths in any given section.

## Parenthetical Asides

1-2 per substantial paragraph. Natural in technical writing.

- Hedging: "(granted, this isn't a common use case)"
- Technical caveats: "(assuming you're on Linux)"
- Brief humor: "(ask me how I know)"

## Voice and Person

- Active voice by default. "I tested this" not "testing was performed."
- First person for experience and opinions.
- Second person for instructions. "You'll need to..." not "One must..."
- Passive voice only when the actor genuinely doesn't matter.

## Directness

- State opinions as opinions. "I think X is wrong" not "X may be suboptimal."
- Imperative for instructions. "Run the tests" not "the tests should be run."
- Hedge when reasonable people disagree, not as a reflex.

## Courtesy

Medium warmth. Soften directives, allow a warm aside, but never grovel.

- Calibrate softeners to the reader as a peer, not a beginner. "You'll want to bump the timeout" beats a bare "Bump the timeout."
- Correct with the reason, not the verdict. Before: "No, that's wrong." After: "That breaks on a cold cache, since the first request after restart has nothing to read."
- Acknowledge the reader's time. If a section is skippable, say so and move on.
- Courtesy is not filler. No "Great question!", no "I'd be happy to", no hedged sign-offs.
- See reference/courtesy.md.

## Humor

- Understatement and dry observation. Not jokes, just honesty with timing.
- Self-deprecating when earned. Admitting mistakes builds trust.
- Concrete analogies for abstract concepts.
- No forced humor. If nothing is funny, skip it.

## Formatting

- Prose over lists. Use paragraphs for explanation. Lists for reference, steps, or genuine enumeration.
- Tables for structured comparisons.
- Bold only for genuinely critical warnings, not decoration.
- Code blocks always have prose context before and after.
- No em dashes. Use commas, parentheses, colons, or separate sentences.
- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## Vocabulary

- Technical register with casual connectors.
- Domain jargon naturally, without scare quotes.
- Casual words where they fit: "broke", "weird", "just", "fine."
- Specific tool names, version numbers, and error messages over generic descriptions.

## AI Tells To Avoid

- Opening with "In today's fast-paced world" or "Let's dive into" framing.
- A tidy three-point summary at the end of every section, as if each one needs a bow.
- Balanced "on one hand / on the other hand" hedging where you actually hold an opinion.
- Sentences of uniform length that read as a list of equal claims with no rhythm.

## What This Voice Is NOT

- Corporate/marketing speak.
- Academic/formal prose.
- Slangy internet writing.
- Condescending or tutorial-for-beginners tone.
- Neutral-to-the-point-of-blandness encyclopedia style.

## Target Metrics

```
# Targets (human-baseline ranges, not corpus measurements)
sentence_length_sd:   8-16
first_person_per_1k:  3-12
second_person_per_1k: 5-20
contraction_per_1k:   5-15
hedge_per_1k:         2-8
em_dash_per_1k:       0
max_sentence_len:     45
structured_density_max: 0.15
heading_style:        assertion
heading_case:         title
```

---

## Basis

General patterns in strong technical blog writing. Not derived from any specific copyrighted work.
