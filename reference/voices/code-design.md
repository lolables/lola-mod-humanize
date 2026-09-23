# Voice Profile: Code Design

Naming, structure, decomposition, and anti-patterns.

---

## Naming

- Short locals are fine: `i`, `n`, `buf`, `cfg`, `err`, `ctx`.
- Descriptive public APIs. `ParseConfigFile` not `Parse`. `UserID` not `ID` on exported types.
- Boolean names state the condition: `isReady`, `hasErrors`, `found`.
- Avoid `Manager`, `Handler`, `Helper`, `Util` in type names unless the domain uses them.
- Match existing project conventions before applying personal preferences.

## Decomposition

A function earns its existence with non-trivial logic or 3+ callers.

- Do not extract a function for 2-3 lines called once. Inline it.
- Do not split a function just because it is "long." Split on logical boundaries.
- One level of abstraction per function. Don't mix SQL generation and HTTP responses in one call.

**Threshold:** if the extracted function name just restates what the code does, it doesn't belong as a function.

## Abstractions

- No factory for a single implementation.
- No strategy pattern for one strategy.
- No interface with one implementor (unless testing requires it).
- Add abstraction when the second real use case arrives, not in anticipation of it.

## Imports

Group in this order: stdlib, third-party, local. Separate groups with a blank line.

Within groups, logical order beats alphabetical. Things that belong together stay together.

## Whitespace

Blank lines separate logical blocks. Not every statement, not every declaration.

- One blank line between methods in a class.
- One blank line between the imports and the first declaration.
- No trailing blank lines at end of function bodies.

## Error Handling

- Catch specific exceptions. Not bare `except:` or `catch (Exception e)`.
- Handle errors near where they occur. Don't bubble up a raw `IOException` to a UI handler.
- Error messages follow code-comments.md: include the failing value, no "please."
- Log at the boundary where context is richest. Don't log at every layer.

## Courtesy

Low warmth. This voice is structural, so courtesy applies to two outputs it shapes: error-message tone and code-review-comment tone.

- Error messages report a state, not a verdict. "config not found: /etc/app.conf" beats "you forgot the config."
- Review comments acknowledge before they correct. "This reads cleanly. One catch: the lock is held across the network call, which can stall every caller."
- Suggest the fix when there is one obvious fix; do not just flag the problem and walk off.
- Courtesy is not filler. No "Great work!" padding, no "Great question!", no "I'd be happy to" preamble on a review note.
- See reference/courtesy.md.

## Formatting

- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence. This profile ships no Target Metrics block, so the pre-scan falls
  back to its built-in default of 45 words for run-on detection
  (`DEFAULT_MAX_SENTENCE_LEN`) and applies no structured-density cap.

## AI Tells To Avoid

- A factory, registry, or interface introduced for a single implementation "for extensibility."
- A function extracted only so its name can narrate the three lines it wraps.
- Review comments that restate the diff instead of judging it.
- Uniform decomposition where every function is the same length regardless of its logical seams.

## What This Voice Is NOT

- Over-engineered "enterprise" code with factories, registries, and abstract base everything.
- Hasty spaghetti that skips decomposition for "simplicity."
- Obsessively formatted code where alignment takes priority over clarity.

---

## Basis

General patterns in pragmatic, human-written code. Informed by `reference/code-patterns.md`.
