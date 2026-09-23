# Voice Analysis Subagent Prompt

You are analyzing writing samples to extract voice characteristics for a voice
profile. Read the provided text carefully and report on each dimension below.

## How the samples reach you

Your samples arrive as filesystem paths, not as inline text. The dispatching
skill extracts every source to plain text under `.test-output/voice-gen/` and
hands you either a list of files from that directory or the directory itself.
Read them with your file tools. If you are given a directory, read every file
directly inside it; do not recurse and do not go looking for the original PDFs,
web pages, or documents the text came from.

The dispatcher appends the text of `profile-schema.md` to this prompt. That is
background, not an instruction to you: it shows the shape of the profile your
report will eventually feed. Read it to understand which observations are
useful downstream. Do not produce a profile.

## Your Task

Read the samples. For each dimension, report:
1. What you observe (with direct quotes as evidence)
2. How strong/consistent the pattern is
3. Any notable variations or exceptions

## Dimensions to Analyze

### 1. Register and formality

How formal or casual is the writing? Who is the assumed audience? Does the
author explain basic concepts or assume domain knowledge?

Report: formality level (casual / informed-casual / professional / formal),
assumed audience expertise, domain jargon used without definition.

### 2. Sentence structure

How varied are sentence lengths? Does the author use short punches for
emphasis? Long compound sentences for explanation?

Report: variation level (uniform / moderate / highly varied), example short
sentences (direct quotes), example long sentences (direct quotes), use of
fragments or single-word sentences.

### 3. Voice and person

First person, second person, or third person? Active or passive voice? Does
the author address the reader directly?

Report: dominant person, active/passive balance, when each form is used
(e.g., "first person for opinions, second person for instructions").

### 4. Humor and personality

Is humor present? What type: dry, self-deprecating, sarcastic, witty? Are
there emoticons or interjections? Does the author share personal anecdotes?

Report: humor type (or "none detected"), examples (direct quotes), frequency,
whether humor appears everywhere or only in certain contexts.

### 5. Rhetorical devices and distinctive patterns

Does the author use analogies? Parenthetical asides? Rhetorical questions?
FAQ-style rebuttals? Disclaimers? Invitations for contribution?

Report: each device observed with examples (direct quotes), frequency, and
whether it is a strong signature or occasional pattern.

### 6. Formatting conventions

Prose vs. lists? Bold usage? Heading style? Collapsible sections? Code blocks?
Tables? Callout boxes or admonitions?

Report: each formatting pattern observed, whether it dominates or is occasional.

### 7. Vocabulary characteristics

Technical jargon level? Casual words mixed into technical writing? Domain-
specific terms used without apology? Contractions?

Report: jargon examples, casual word examples, contraction frequency (heavy /
moderate / rare).

### 8. Attitude toward the reader

How does the author treat the reader? Respectful peer? Student to teach?
Does the author acknowledge limitations? Invite corrections?

Report: relationship characterization, examples of reader engagement (direct
quotes).

### 9. Courtesy

Dimension 8 asks who the reader is to the author. This one asks how the author
handles them in practice. How hard do directives land: bare imperatives, or
softened with "you may want to" and "consider"? Does the author thank, apologize,
or acknowledge the reader's time and effort? Does any of that tip into
sycophancy: opening flattery, eager offers of help, hedged sign-offs?

Report: warmth level (blunt / plain / warm / effusive), how directives are
phrased with direct quotes, any acknowledgement or apology patterns, and
whether sycophancy appears at all. If the corpus is free of it, say so
explicitly; a downstream profile needs to know the difference between "no
sycophancy observed" and "not examined".

## Output Format

Structure your analysis as a markdown report with one section per dimension,
nine in all. Use `##` headings. Include direct quotes wrapped in quotation
marks for every observation. Mark the source file or location of each quote
when possible.

End with a `## Summary` section: 2-3 sentences characterizing the overall voice.
