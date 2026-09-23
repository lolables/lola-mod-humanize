"""
vocabulary.py -- Canonical AI-detection vocabulary for Humanize.

Single source of truth for tier words, banned phrases, and transition
starters.  Imported by analyze-sources.py, ollama-eval.py, and tests.
"""
from __future__ import annotations

# --- Tier words ---
# Generated from reference/ai-vocabulary-watchlist.md. Edit that file,
# then run `task vocab:sync`. Hand edits here are reverted by `task lint`.
# BEGIN GENERATED: tier-words
TIER1_WORDS: set[str] = {
    'delve', 'tapestry', 'landscape', 'meticulous', 'meticulously',
    'pivotal', 'underscore', 'intricate', 'intricacies', 'interplay',
    'vibrant', 'testament', 'enduring', 'garner', 'highlight', 'seamless',
    'foster', 'cultivate', 'bolster', 'remarkable', 'commendable',
    'dive into', 'deep dive',
}

TIER2_WORDS: set[str] = {
    'align with', 'bolstered', 'showcasing', 'fostering', 'highlighting',
    'emphasizing', 'enhance', 'enhanced', 'showcase', 'innovative',
    'emphasized', 'cutting-edge', 'showcased', 'resonate with',
    'encompassing', 'ever-evolving',
}

TIER3_WORDS: set[str] = {
    'additionally', 'furthermore', 'moreover', 'crucial', 'robust',
    'comprehensive', 'seamlessly', 'groundbreaking', 'transformative',
    'compelling', 'facilitate', 'illuminate', 'endeavor', 'paradigm',
    'harness', 'navigate', 'realm', 'leverage', 'embark', 'holistic',
    'synergy', 'multifaceted', 'nuanced', 'highlighted', 'noteworthy',
    'utilize', 'paramount', 'invaluable', 'thrive',
}
# END GENERATED: tier-words

ALL_KNOWN: set[str] = TIER1_WORDS | {w.split()[-1] for w in TIER2_WORDS} | TIER3_WORDS

# --- Candidate extraction patterns (analyze-sources.py) ---

CANDIDATE_PATTERNS: list[str] = [
    r'\b(delve|tapestry|landscape|pivotal|underscore|intricate|vibrant)\b',
    r'\b(testament|enduring|garner|bolster(?:ed)?|showcase(?:ing|d)?)\b',
    r'\b(foster(?:ing|ed)?|highlight(?:ing|ed)?|emphasiz(?:ing|ed)?)\b',
    r'\b(enhance(?:d|ment)?|crucial|robust|comprehensive|seamless(?:ly)?)\b',
    r'\b(groundbreaking|transformative|compelling|facilitate|illuminate)\b',
    r'\b(endeavor|paradigm|harness|navigate|realm|leverage|embark)\b',
    r'\b(multifaceted|holistic|synergy|innovative|cutting-?edge)\b',
    r'\b(nuanced|noteworthy|commendable|exemplary|remarkable)\b',
    r'\b(spearhead|catalyze|galvanize|propel|cultivate)\b',
    r'\b(underscore|overarching|encompass|juxtapose|dichotomy)\b',
    r'\b(burgeoning|nascent|seminal|salient|pertinent)\b',
    r'\b(utilize[sd]?|paramount|invaluable|thrive[sd]?|resonate[sd]?)\b',
    r'\b(deep dive|dive into|ever-evolving|encompassing)\b',
]

# --- AI-tooling repo patterns (contamination check) ---

AI_REPO_PATTERNS: list[str] = [
    r'claude[-_]', r'gpt[-_]', r'llm[-_]', r'ai[-_](?!signs|writing|detection)',
    r'copilot', r'ollama', r'langchain', r'llamaindex', r'autogpt',
    r'chatgpt', r'openai[-_]', r'anthropic[-_]',
]

# --- Phrases, transitions, and positional openers/closers ---
# Generated from reference/ai-vocabulary-watchlist.md. Edit that file,
# then run `task vocab:sync`.
# BEGIN GENERATED: phrases
BANNED_PHRASES: list[str] = [
    "it's important to note", "in today's", 'serves as a', 'diverse array',
    'boasts a', 'commitment to excellence', 'rich cultural',
    'plays a vital role', 'not just', 'not only', 'rich tapestry',
    'in conclusion', 'it is worth noting', 'one might argue',
    'this raises the question',
]

TRANSITION_STARTERS: list[str] = [
    'additionally,', 'furthermore,', 'moreover,',
]

GENERIC_OPENERS: list[str] = [
    "in today's", 'as organizations increasingly', 'in an era of',
    'in the rapidly evolving', 'as the world becomes',
]

GENERIC_CLOSERS: list[str] = [
    'in conclusion', 'to summarize', 'as we have seen', 'in this article',
    'in this section', 'by following these best practices',
]
# END GENERATED: phrases
