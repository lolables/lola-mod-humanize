# Voice Profile: Tutorial

Instructional writing. Addressing a learner, not a peer.

---

## Register

Patient and direct. Not condescending. The reader is capable; they just haven't done this before.

- Assume the reader can follow instructions but may not know why they work.
- Explain just enough context to avoid confusion. Save deep theory for a reference doc.
- Acknowledge common failure modes before they happen.

## Sentence Structure

Clear and sequential. Shorter than blog prose. Each sentence carries one idea.

- Steps: "Run `npm install`." Direct, no hedging.
- Context: "This installs the dependencies listed in `package.json`." Brief follow-up.
- Avoid: "You might want to consider running `npm install`, which could help."

## Voice and Person

- Second person throughout. "You" is the subject of every step.
- First person only when noting personal verification. "I tested this on Ubuntu 22.04."
- Never "we" unless there is a literal team involved.

## Directness

- Direct on instructions. "Run X" not "you might want to run X."
- Gentle on errors. "If you see `EACCES`, check your file permissions."
- No apologies for prerequisites. "You need Node 18+. If you don't have it, install it."

## Courtesy

High warmth. Anticipate the stumble, reassure, and soften the directive. The reader is new to this, not slow.

- Warn before the trap, not after. "Before you run this, make sure the service is stopped, or you'll see a lock error."
- When something looks alarming but is fine, say so. "The first run prints a long warning. That's expected; it goes away on the second run."
- Soften directives without burying the action. Before: "Delete the cache." After: "Go ahead and delete the cache; it rebuilds on the next start."
- If a step fails for a common reason, name the reason kindly. The reader did not do anything wrong by hitting it.
- Courtesy is warmth, not filler. No "Great question!", no "I'd be happy to", no praise for finishing a step.
- See reference/courtesy.md.

## Formatting

- Numbered steps. Each step is one action.
- Prerequisites section at the top, before anything else.
- Each step produces a visible, verifiable result. State what the reader should see.
- Code blocks for every command. Expected output in a separate code block, labeled.
- Prose bridges between steps to explain the "why" briefly.
- No long prose paragraphs mid-tutorial. If explanation grows, link to a reference doc.
- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

Example step structure:
````
3. Initialize the database.

   Run:
   ```
   task db:init
   ```

   You should see:
   ```
   migrations applied: 4
   seed data loaded
   ```
````

## Vocabulary

- Plain language. No jargon without definition on first use.
- Define terms at the point of first use, not in a glossary the reader may skip.
- Specific tool names and versions. "Run `git 2.40+`" not "run a recent version of git."

## AI Tells To Avoid

- Explaining why a step works before the reader has run it. Action first, the brief "why" after.
- "Simply" and "just" in front of a step that is not simple for a learner.
- A wall of theory dropped between two commands. Link out instead.
- Congratulating the reader at the end of every step.

## What This Voice Is NOT

- Academic lecture.
- Marketing copy.
- Reference documentation (that is code-docs).
- Blog-style opinion writing.

## Target Metrics

```
# Targets (human-baseline ranges, not corpus measurements)
sentence_length_sd:   5-11
first_person_per_1k:  0-3
second_person_per_1k: 15-35
contraction_per_1k:   3-12
hedge_per_1k:         2-6
em_dash_per_1k:       0
max_sentence_len:     30
structured_density_max: 0.70
```

---

## Basis

General patterns in effective technical tutorials.
