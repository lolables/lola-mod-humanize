# Courtesy: Warmth Without Sycophancy

Humanize strips AI filler. It should not strip human warmth. These are
different things, and the pipeline used to delete both. This reference
defines the line and the rewrites that cross it safely.

The principle: courtesy is respect for the reader's time, effort, and
intelligence. It lives in how you phrase a directive, how you deliver a
correction, and whether you acknowledge the person on the other end. It does
not live in filler.

## The sycophancy line

These stay deleted. They are filler, not courtesy:

| Banned | Why it is not courtesy |
|--------|------------------------|
| "Great question!" | Flattery, not respect. Says nothing. |
| "I hope this helps!" | Hedged sign-off that adds no information. |
| "Certainly! / Of course!" | Performative compliance. |
| "Let me know if you need anything else." | Generic, automatic, hollow. |
| "I'd be happy to..." | Announces a feeling instead of doing the thing. |

Courtesy is shown by what you write, not by announcing how glad you are to
write it.

## Abrasive tell -> courteous rewrite

- Bare command -> softened directive (calibrate to register):
  - Abrasive: "Bump the timeout."
  - Courteous: "You'll want to bump the timeout to 30s."
- Flat contradiction -> correction with reason:
  - Abrasive: "No, that's wrong."
  - Courteous: "That won't hold up, because the cache is cold on first boot."
- Hostile error framing -> neutral-terse:
  - Abrasive: "Invalid input. You broke it."
  - Courteous: "invalid port: 99999 (expected 1-65535)"
- Dismissive "obviously"/"just" -> removed:
  - Abrasive: "Just restart it, obviously."
  - Courteous: "Restart it; that clears the stale lock."
- Absolute scolding -> acknowledge the tradeoff:
  - Abrasive: "Never use globals."
  - Courteous: "Globals will bite you here once there are two callers."

## Calibration by register

| Voice | Courtesy level | Notes |
|-------|----------------|-------|
| tutorial | high | anticipate failure, reassure, soften directives |
| blog | medium | soften, warm asides, no groveling |
| general, code-docs, code-comments, academic, release-notes | low | soften; neutral, never hostile |
| rfc | none | impersonal; normative |
| code-design | n/a | structural; applies to error/review-comment tone only |

Default for the standalone politeness wash with no voice selected: the
selected voice's level, or `general` (low) if none.
