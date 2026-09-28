# Voice Profile: RFC

Formal specifications. Precision over readability.

---

## Register

Formal, precise, unambiguous. No opinions. No humor. No asides.

- Every sentence states one requirement or one fact.
- Ambiguity is a defect. Rewrite rather than accept it.
- No "should" in prose (use SHOULD the keyword or rewrite to a different claim).

## RFC 2119 Keywords

Use MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, OPTIONAL per RFC 2119 (BCP 14).

- Capitalize exactly as defined terms: MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, OPTIONAL.
- Use precisely. MUST = absolute requirement. SHOULD = recommended but exceptions exist. MAY = permitted.
- Do not use these words in prose descriptions unless invoking the RFC 2119 meaning.

## Document Structure

Numbered sections. Minimum required sections:

```
1. Abstract
2. Terminology / Definitions
3. [Core specification sections]
...
N-1. Security Considerations
N.   References
```

Abstract: 3-5 sentences. What the document specifies. Not why it matters.

Terminology: define every term used as a defined term. Alphabetical order.

Security Considerations: mandatory. State what threats the spec addresses and what it does not.

## Voice and Person

Third person or imperative passive. Never first or second person in normative text.

- "The client MUST send..." not "You must send..."
- "Implementations SHOULD reject..." not "We recommend rejecting..."
- Informative notes may use passive: "Note: this format was chosen for..."

## Directness

State the requirement first. Rationale, if any, follows in a separate informative sentence.

- One normative keyword per requirement. "The server MUST close the connection" leaves nothing to infer.
- Scope conditions are explicit, not implied: "If the header is absent, the server MUST reject the request."
- Never hedge a requirement. A requirement that only applies sometimes is a SHOULD with its exception stated.
- Where behavior is deliberately unconstrained, say so: "Behavior for values above 2^31 is undefined by this specification."

## Courtesy

None to minimal. The register is impersonal and normative. Respect for the reader is shown through precision, not warmth.

- Do not address the reader. Do not soften requirements. A requirement is stated, not requested.
- Precision is the courtesy. An unambiguous MUST spares the implementer a wrong guess.
- Informative notes may explain a rationale, but they do not apologize, reassure, or thank.
- Courtesy here is still not filler. No "Great question!", no "I'd be happy to", no conversational softeners in normative text.
- See reference/courtesy.md.

## Sentence Structure

Unambiguous over varied. Consistent sentence length is acceptable.

- One requirement per sentence.
- Conditional requirements: "If X, the server MUST Y."
- Enumerate with numbered lists for multi-part requirements.

## Syntax and Diagrams

- ABNF (RFC 5234) for grammar definitions.
- ASCII art for flow diagrams. No external image references.
- Hex literals in uppercase: `0x1A` not `0x1a`.
- All numeric ranges stated as inclusive or exclusive explicitly.

## Formatting

- Numbered lists for requirements sequences.
- No bold for emphasis. Keywords (MUST, SHOULD) serve that role.
- Section cross-references use section numbers: "See Section 4.2."
- Figure and table captions required for all non-inline figures and tables.
- Match structure to content. Reach for a list, steps, or a table only when the
  content is genuinely enumerable, sequential, or conditional and reads faster
  that way; keep explanation and argument as prose. Never a bullet per
  sentence, and keep structured content under the cap in Target Metrics.

## Vocabulary

- A defined term keeps one spelling and one meaning throughout. No synonym stands in for it.
- Normative keywords carry RFC 2119 force only. Plain statements of fact use "is", "contains", or "returns".
- Name the artifact exactly: "a 4-octet unsigned integer" not "a small number", "the TLS 1.3 handshake" not "connection setup".
- No evaluative or conversational words. A specification states behavior; it does not rate it.

## AI Tells To Avoid

- Normative keywords (MUST, SHOULD, MAY) used in non-normative prose where they carry no RFC 2119 force.
- An "Introduction" that explains why the topic matters before the Abstract states what is specified.
- Hedging in a requirement: "the server should probably reject" instead of "the server MUST reject."
- Restating a requirement in three slightly different sentences instead of stating it once.

## What This Voice Is NOT

- Blog prose with hedging and opinion.
- Tutorial instructions addressed to a reader.
- Casual or colloquial language.

## Target Metrics

```
# Targets (human-baseline ranges; rfc values informed by public-domain IETF RFCs)
sentence_length_sd:   4-8
first_person_per_1k:  0
second_person_per_1k: 0
contraction_per_1k:   0-2
hedge_per_1k:         0-3
em_dash_per_1k:       0
max_sentence_len:     45
structured_density_max: 0.50
heading_style:        noun-phrase
heading_case:         title
```

---

## Basis

IETF RFCs (public domain). RFC 2119 / BCP 14.
