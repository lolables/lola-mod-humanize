# Writing discipline

Compact rules that prevent AI-voice patterns at generation time. Copy this
section into the project instruction file your assistant reads (for example
`AGENTS.md`) to reduce how much the Humanize skill needs to fix after the
fact.

~56 lines, ~680 tokens (GPT-2). The banned-word block below is generated from
the watchlist, so both numbers grow with it; re-measure after `task vocab:sync`.

----

Apply these rules to every file you write or modify.

## Voice

Senior engineer to a peer. Active voice. First person. Vary sentence length.

## Banned

<!-- BEGIN GENERATED: banned -->
Words -- never use: delve (into), tapestry (figurative), landscape
(figurative), meticulous, pivotal, underscore (verb), intricate, interplay,
vibrant, testament (to), enduring, garner, highlight (verb), seamless,
foster, cultivate, bolster, remarkable, commendable, dive into, deep dive,
bolstered, showcasing, fostering, seamlessly, groundbreaking,
transformative, paradigm, embark (on), holistic, synergy, multifaceted,
nuanced (filler).

Phrases -- never use: "It's important to note that", "In today's
[fast-paced/digital/modern] world", "serves as a
[testament/reminder/beacon]", "a diverse array of", "boasts a
[rich/vibrant]", "commitment to [excellence/innovation]", "rich cultural
heritage", "plays a [vital/crucial/key] role", "Not just X, but also Y",
"not only (bare)", "rich tapestry", "In conclusion", "It is worth noting",
"I want to be clear that", "One might argue", "This raises the question".

Never open a sentence with Additionally, Furthermore, or Moreover.
<!-- END GENERATED: banned -->

Generated from `reference/ai-vocabulary-watchlist.md`. To change this list,
edit the watchlist and run `task vocab:sync`.

## Text

- Vary section lengths. No symmetric structure.
- No "Despite [positive], faces challenges..." endings.
- No "Not just X, but also Y." State it directly.
- Bold only for genuine warnings.
- Prose over decorative lists; structure over walls of text. Match the shape
  to the content: prose for explanation and argument; lists, steps, or tables
  only for genuinely enumerable, sequential, or conditional content that reads
  faster structured. Never a bullet per sentence.
- No em dashes. Use commas, parentheses, colons, or separate sentences.
- Name every source. No "experts argue."

## Code

- Locals are short (`auth`, `db`, `cfg`). Public APIs are descriptive.
- Comments explain why, never what. No docstrings on obvious functions.
- Catch specific exceptions. Handle edge cases.
- Error messages: terse, include the failing value.
  `f"can't reach {url}"` not `"Failed to connect. Please try again."`
- No abstractions with one caller. No factories for single implementations.
- Group imports stdlib/third-party/local. Don't alphabetize within groups.
- Tighten whitespace. No blank line between every statement.
- Commit small. `"fix: auth skipping OPTIONS"` not `"Update authentication"`.
