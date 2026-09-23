# Voice Profile: Code Comments

In-code commentary: inline comments, docstrings, error messages, TODOs.

---

## Inline Comments

Explain why, not what. The code says what. The comment says why.

**Good:**
```python
# retry limit matches the upstream SLA window
MAX_RETRIES = 3
```

**Bad:**
```python
# set MAX_RETRIES to 3
MAX_RETRIES = 3
```

Rules:
- One line preferred. If you need two lines, consider whether a docstring is better.
- Place near the code being explained, not above an unrelated block.
- No period needed for single-sentence comments.

## Docstrings

Public APIs only. Skip obvious internal helpers.

- Format matches project convention (Google style, NumPy, etc.). Pick one, stick to it.
- Describe behavior, not implementation. "Returns the first matching entry" not "iterates the list and checks each."
- Include types if not obvious from signatures.
- Skip `Returns: None` on functions that return None.

**Good:**
```python
def find_entry(key: str, entries: list[Entry]) -> Entry | None:
    """Return the first entry matching key, or None if not found."""
```

**Bad:**
```python
def find_entry(key: str, entries: list[Entry]) -> Entry | None:
    """
    This function is used to find an entry. It takes a key and a list
    of entries and returns the matching entry or None.
    """
```

## Error Messages

- Include the failing value. "invalid port: 99999" not "invalid port."
- Terse. One sentence.
- No "please" in errors. No apologetic framing.
- Suggest the fix only when there is one obvious fix.

**Good:** `unknown format: "toml" (expected: json, yaml)`
**Bad:** `Please provide a valid format option.`

## Courtesy

Low warmth. Error messages stay terse, but terse is not hostile. State the failing value and the fix; do not blame.

- No "you broke it" framing. The message reports a state, not a verdict on the user.
- Drop the scold words. Before: "Invalid input. You messed up." After: "invalid port: 99999 (expected 1-65535)."
- A comment that corrects a future reader explains the constraint, it does not lecture.
- Courtesy is not filler. No "please" in errors, no "Great question!", no apology for the failure.
- See reference/courtesy.md.

## Formatting

- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## TODOs

Always include a ticket reference or a constraint explanation.

**Good:**
```
# TODO(#412): remove this once the upstream client supports streaming
# TODO: not worth fixing until we drop Python 3.9 support
```

**Bad:**
```
# TODO: fix this later
```

## Categorized Annotations

Use standard prefixes for categorized notes:

- `SAFETY:` -- invariant that must hold for correctness or security
- `HACK:` -- known workaround; explain why and what the clean fix would be
- `PERF:` -- performance-sensitive path; explain the constraint

## AI Tells To Avoid

- A docstring on every trivial helper that just renames the function in a sentence.
- Comments that restate the line below them ("# increment the counter" over `count += 1`).
- A full Args/Returns block on a two-line private function with an obvious signature.
- Apologetic or chatty error strings where a terse one carries the same information.

## What This Voice Is NOT

- Verbose tutorial-style comments explaining every line.
- AI-generated docstrings on every function regardless of complexity.
- Comments that restate what the code already says clearly.

## Target Metrics

```
# Targets (human-baseline ranges, not corpus measurements)
first_person_per_1k:  0-2
second_person_per_1k: 0-3
contraction_per_1k:   0-5
em_dash_per_1k:       0
max_sentence_len:     30
structured_density_max: 0.10
```

---

## Basis

General patterns in well-maintained open source code.
