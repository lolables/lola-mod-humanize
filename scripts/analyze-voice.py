#!/usr/bin/env python3
"""
analyze-voice.py -- Analyze writing samples and generate a voice profile.

Reads extracted text from personal sources (output of extract-text.py or
the fetch pipeline), computes statistical voice metrics, and generates
a draft voice-profile.local.md.

Usage:
    python3 scripts/analyze-voice.py <input_dir_or_file> [--output <path>]

The input can be:
  - A directory of .html files (from the fetch pipeline's FETCH_DIR)
  - A single text file (from extract-text.py)
  - A directory of raw text files

Only files with "voice-" in the name are analyzed (matching the personal
sources slug convention). If no voice files are found, all files are used.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from textwrap import dedent


# --- Text Cleaning ---

def strip_html_tags(text: str) -> str:
    """Remove HTML tags for analysis of fetched web pages."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    import html
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def extract_prose(text: str) -> str:
    """Strip code blocks, frontmatter, and non-prose content."""
    # Remove YAML frontmatter
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
    # Remove fenced code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Remove markdown images
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove heading markers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove list markers for analysis (keep the text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    return text.strip()


# --- Sentence Analysis ---

def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Handles abbreviations roughly."""
    # Split on sentence-ending punctuation followed by space+capital or newline
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', text)
    # Filter out very short fragments (likely not real sentences)
    return [s.strip() for s in parts if len(s.split()) >= 3]


def sentence_stats(sentences: list[str]) -> dict:
    """Compute sentence length statistics."""
    if not sentences:
        return {'count': 0, 'mean': 0, 'sd': 0, 'min': 0, 'max': 0,
                'short_pct': 0, 'long_pct': 0}
    lengths = [len(s.split()) for s in sentences]
    n = len(lengths)
    mean = sum(lengths) / n
    variance = sum((l - mean) ** 2 for l in lengths) / n
    sd = math.sqrt(variance)
    short = sum(1 for l in lengths if l <= 8)
    long = sum(1 for l in lengths if l >= 25)
    return {
        'count': n,
        'mean': round(mean, 1),
        'sd': round(sd, 1),
        'min': min(lengths),
        'max': max(lengths),
        'short_pct': round(100 * short / n),
        'long_pct': round(100 * long / n),
    }


# --- Voice Metrics ---

def count_parentheticals(text: str) -> int:
    """Count parenthetical asides (text in parentheses)."""
    return len(re.findall(r'\([^)]{5,}\)', text))


def count_questions(text: str) -> int:
    """Count question marks (rhetorical questions, questions as structure)."""
    return len(re.findall(r'\?', text))


def count_first_person(text: str) -> int:
    return len(re.findall(r'\b[Ii]\b(?!\.\w)', text))


def count_second_person(text: str) -> int:
    return len(re.findall(r'\b[Yy]ou\b', text))


def count_passive_voice(text: str) -> int:
    """Rough count of passive constructions (was/were/been/being + past participle)."""
    return len(re.findall(
        r'\b(?:was|were|been|being|is|are)\s+\w+(?:ed|en|t)\b', text, re.IGNORECASE
    ))


def count_active_voice(sentences: list[str]) -> int:
    """Rough count of active constructions (subject + verb patterns)."""
    active = 0
    for s in sentences:
        if re.match(r'^(?:I|We|You|He|She|They|It|The|This|That)\s+\w+', s):
            active += 1
    return active


def count_contractions(text: str) -> int:
    return len(re.findall(r"\w+'(?:t|s|re|ve|ll|d|m)\b", text))


def count_exclamations(text: str) -> int:
    return len(re.findall(r'!', text))


def count_em_dashes(text: str) -> int:
    return len(re.findall(r'\u2014|--', text))


def count_bold(text: str) -> int:
    return len(re.findall(r'\*\*[^*]+\*\*', text))


def count_lists(text: str) -> int:
    return len(re.findall(r'^\s*[-*+]\s+', text, re.MULTILINE))


def count_headers(text: str) -> int:
    return len(re.findall(r'^#{1,6}\s+', text, re.MULTILINE))


def count_question_headers(text: str) -> int:
    return len(re.findall(r'^#{1,6}\s+.*\?\s*$', text, re.MULTILINE))


def count_code_blocks(text: str) -> int:
    return len(re.findall(r'```', text)) // 2


def vocabulary_register(text: str) -> dict:
    """Assess vocabulary characteristics."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    total = len(words)
    if total == 0:
        return {'total_words': 0, 'unique_words': 0, 'lexical_diversity': 0,
                'avg_word_length': 0, 'long_word_pct': 0}
    unique = len(set(words))
    lengths = [len(w) for w in words]
    long_words = sum(1 for l in lengths if l >= 8)
    return {
        'total_words': total,
        'unique_words': unique,
        'lexical_diversity': round(unique / min(total, 1000), 2),
        'avg_word_length': round(sum(lengths) / total, 1),
        'long_word_pct': round(100 * long_words / total),
    }


def detect_humor_signals(text: str) -> list[str]:
    """Look for humor-related patterns."""
    signals = []
    if re.search(r':-[)D(P]|:\)|;-?\)', text):
        signals.append('Emoticons present')
    if re.search(r'\b(?:sigh|ugh|ahem|heh|hah)\b', text, re.IGNORECASE):
        signals.append('Interjections (sigh, ugh, etc.)')
    if re.search(r'(?:I am not|I\'m not)\s+(?:a|an)\s+\w+\s+expert', text, re.IGNORECASE):
        signals.append('Self-deprecating expertise disclaimers')
    if re.search(r'\.{3}', text):
        signals.append('Trailing ellipsis (narrative pause)')
    if count_exclamations(text) > 0:
        signals.append(f'Exclamation marks ({count_exclamations(text)})')
    return signals


def detect_formatting_patterns(raw_text: str) -> dict:
    """Analyze formatting preferences from the raw (non-stripped) text."""
    return {
        'headers': count_headers(raw_text),
        'question_headers': count_question_headers(raw_text),
        'question_header_pct': (
            round(100 * count_question_headers(raw_text) / max(count_headers(raw_text), 1))
        ),
        'bold_instances': count_bold(raw_text),
        'list_items': count_lists(raw_text),
        'code_blocks': count_code_blocks(raw_text),
        'em_dashes': count_em_dashes(raw_text),
    }


# --- Profile Generation ---

def classify_register(stats: dict, vocab: dict, first_person: int,
                      contractions: int, word_count: int) -> str:
    """Classify the overall register based on metrics."""
    formality_score = 0

    # Contractions suggest informality
    contraction_rate = contractions / max(word_count / 1000, 1)
    if contraction_rate > 10:
        formality_score -= 2
    elif contraction_rate > 5:
        formality_score -= 1

    # First person suggests informality
    first_person_rate = first_person / max(word_count / 1000, 1)
    if first_person_rate > 15:
        formality_score -= 2
    elif first_person_rate > 5:
        formality_score -= 1

    # Long words suggest formality
    if vocab['long_word_pct'] > 15:
        formality_score += 2
    elif vocab['long_word_pct'] > 10:
        formality_score += 1

    # High lexical diversity suggests formality
    if vocab['lexical_diversity'] > 0.6:
        formality_score += 1

    # Sentence length variation suggests deliberate style
    if stats['sd'] > 8:
        formality_score -= 1  # varied = less formal/academic

    if formality_score <= -3:
        return 'Casual'
    if formality_score <= -1:
        return 'Informed-casual'
    if formality_score <= 1:
        return 'Professional'
    return 'Formal/academic'


def generate_profile(raw_text: str, source_descriptions: list[str]) -> str:
    """Generate a draft voice-profile.local.md from analyzed text."""
    prose = extract_prose(raw_text)
    # For HTML content, also strip tags
    if '<' in prose and '>' in prose:
        prose = strip_html_tags(prose)

    sentences = split_sentences(prose)
    stats = sentence_stats(sentences)
    vocab = vocabulary_register(prose)
    formatting = detect_formatting_patterns(raw_text)
    humor = detect_humor_signals(raw_text)

    word_count = vocab['total_words']
    first_person = count_first_person(prose)
    second_person = count_second_person(prose)
    passive = count_passive_voice(prose)
    active = count_active_voice(sentences)
    contractions = count_contractions(prose)
    parentheticals = count_parentheticals(prose)
    questions = count_questions(prose)

    register = classify_register(stats, vocab, first_person, contractions, word_count)

    # Per-1000-word rates
    r = max(word_count / 1000, 1)
    fp_rate = round(first_person / r, 1)
    sp_rate = round(second_person / r, 1)
    paren_rate = round(parentheticals / r, 1)
    question_rate = round(questions / r, 1)
    contraction_rate = round(contractions / r, 1)

    # Voice ratio
    total_voice = active + passive
    active_pct = round(100 * active / max(total_voice, 1))

    short_examples = [s for s in sentences if len(s.split()) <= 8][:3]
    long_examples = [s for s in sentences if len(s.split()) >= 20][:3]

    # Build the profile
    source_list = '\n'.join(f'- {d}' for d in source_descriptions) if source_descriptions else '- (no source descriptions available)'

    profile = dedent(f"""\
    # Voice Profile Override: Personal (Auto-Generated Draft)

    Generated by analyze-voice.py from {word_count} words of personal writing.
    **Review and edit this file.** The analysis is statistical, not subjective.
    Some sections need your judgment to fill in or correct.

    ---

    ## Register

    **{register}.** Based on contraction rate ({contraction_rate}/1000 words),
    first-person usage ({fp_rate}/1000 words), vocabulary complexity
    ({vocab['long_word_pct']}% words 8+ letters), and sentence variation
    (SD {stats['sd']}).

    - {"Uses contractions freely" if contraction_rate > 8 else "Moderate contraction usage" if contraction_rate > 3 else "Rarely uses contractions"}
    - {"Heavy first-person usage (I/me/my)" if fp_rate > 15 else "Moderate first-person" if fp_rate > 5 else "Low first-person usage"}
    - {"Addresses reader directly (you/your)" if sp_rate > 5 else "Minimal direct address"}
    - {"High vocabulary complexity" if vocab['long_word_pct'] > 15 else "Moderate vocabulary complexity" if vocab['long_word_pct'] > 10 else "Accessible vocabulary"}

    ## Sentence Structure

    **{"Highly varied" if stats['sd'] > 10 else "Varied" if stats['sd'] > 6 else "Moderately varied" if stats['sd'] > 3 else "Uniform (needs more variation)"}.** Average {stats['mean']} words per sentence (SD {stats['sd']}).

    - Shortest sentences: ~{stats['min']} words
    - Longest sentences: ~{stats['max']} words
    - Short punches (<=8 words): {stats['short_pct']}% of sentences
    - Long explanations (>=25 words): {stats['long_pct']}% of sentences
    """)

    if short_examples:
        profile += '- Short examples from your writing:\n'
        for ex in short_examples:
            profile += f'  - "{ex.strip()[:80]}"\n'

    if long_examples:
        profile += '- Long examples from your writing:\n'
        for ex in long_examples:
            profile += f'  - "{ex.strip()[:120]}..."\n'

    profile += dedent(f"""
    ## Parenthetical asides

    {"**Frequent pattern.** " if paren_rate > 3 else "**Occasional.** " if paren_rate > 1 else "**Rare.** "}{parentheticals} parenthetical asides detected ({paren_rate}/1000 words).

    {"This is a strong voice signature. Use 1-2 per substantial paragraph." if paren_rate > 3 else "Use sparingly where hedges or caveats fit naturally." if paren_rate > 1 else "Consider whether parenthetical asides could add personality."}

    ## Voice and Person

    - **{"Active voice dominant" if active_pct > 60 else "Mixed active/passive" if active_pct > 40 else "Passive voice dominant"}** ({active_pct}% active in sampled sentences)
    - **First person:** {fp_rate}/1000 words {"(heavy)" if fp_rate > 15 else "(moderate)" if fp_rate > 5 else "(light)"}
    - **Second person:** {sp_rate}/1000 words {"(addresses reader frequently)" if sp_rate > 5 else "(occasional)" if sp_rate > 1 else "(rare)"}
    - **Passive voice:** {passive} instances detected

    ## Directness

    <!-- EDIT THIS SECTION: Statistical analysis can't fully capture directness.
         Consider: Do you hedge or state things bluntly? Do you use imperative
         voice for non-negotiable items? Do you soften disagreements? -->

    - {"Uses exclamation marks" if count_exclamations(prose) > 3 else "Rarely uses exclamation marks"} ({count_exclamations(prose)} detected)
    - {"Uses rhetorical questions to structure arguments" if question_rate > 2 else "Occasional questions" if question_rate > 0.5 else "Rarely uses questions"} ({question_rate}/1000 words)

    ## Courtesy

    **{"High warmth" if sp_rate > 8 else "Medium warmth" if sp_rate > 3 else "Low warmth"}.** Suggested from how often the sample addresses the
    reader ({sp_rate}/1000 words) and its exclamation count
    ({count_exclamations(prose)}).

    <!-- EDIT THIS SECTION: Warmth is a judgment call the statistics only hint
         at. Decide which courtesy markers earn their place in this voice, and
         which read as filler. See reference/courtesy.md for the distinction
         between genuine courtesy and padding. -->

    ## Humor style

    <!-- EDIT THIS SECTION: Humor is hard to detect statistically. Review the
         signals below and describe your humor style in your own words. -->

    """)

    if humor:
        profile += 'Detected signals:\n'
        for signal in humor:
            profile += f'- {signal}\n'
    else:
        profile += 'No strong humor signals detected in the sample.\n'

    profile += dedent(f"""
    ## Formatting

    Based on {formatting['headers']} headers, {formatting['list_items']} list items,
    {formatting['code_blocks']} code blocks, and {formatting['bold_instances']} bold
    instances across the sample:

    - {"**Prose over lists.**" if formatting['list_items'] < formatting['headers'] * 3 else "**List-heavy.**"} {"Uses lists for reference material and steps." if formatting['list_items'] > 5 else "Prefers flowing paragraphs."}
    - {"**Questions as headers.**" if formatting['question_header_pct'] > 10 else "**Standard headers.**"} {formatting['question_header_pct']}% of headers are questions.
    - {"**Bold used sparingly.**" if formatting['bold_instances'] < word_count / 200 else "**Bold used frequently.**"} {formatting['bold_instances']} instances.
    - {"**Em dashes present.**" if formatting['em_dashes'] > 0 else "**No em dashes.**"} {formatting['em_dashes']} detected.
    - {"**Code blocks used.**" if formatting['code_blocks'] > 0 else "**No code blocks.**"} {formatting['code_blocks']} blocks.

    ## Vocabulary

    - Total unique words: {vocab['unique_words']} (from {vocab['total_words']} total)
    - Lexical diversity: {vocab['lexical_diversity']} (unique/total, higher = more varied)
    - Average word length: {vocab['avg_word_length']} characters
    - Long words (8+ chars): {vocab['long_word_pct']}% of total
    - Contractions: {contraction_rate}/1000 words

    <!-- ADD: Domain-specific jargon you use without apology. Casual words
         you mix into technical writing. Any verbal tics or signature phrases. -->

    ## Distinctive patterns

    <!-- EDIT THIS SECTION: These require human judgment. Consider:
         1. Do you frame debugging as narrative with emotional beats?
         2. Do you reach for physical-world analogies?
         3. Do you invite collaboration ("PRs welcome")?
         4. Do you use disclaimers casually?
         5. Do you version-number personal content?
         6. Any other signature patterns? -->

    (Fill in based on reviewing your own writing samples.)

    ## What This Voice Is NOT

    <!-- EDIT THIS SECTION: What registers do you actively avoid?
         Examples: corporate speak, academic prose, internet-casual,
         condescending tutorial tone, bland encyclopedia style. -->

    (Fill in based on what you dislike in writing.)

    ---

    ## Source

    Derived from analysis of:
    {source_list}

    ## Metrics

    These numbers were used to generate this profile. Useful for manual
    tuning or for comparing against future samples.

    ```
    words_analyzed: {word_count}
    sentences_analyzed: {stats['count']}
    sentence_length_mean: {stats['mean']}
    sentence_length_sd: {stats['sd']}
    sentence_length_min: {stats['min']}
    sentence_length_max: {stats['max']}
    short_sentence_pct: {stats['short_pct']}
    long_sentence_pct: {stats['long_pct']}
    first_person_per_1k: {fp_rate}
    second_person_per_1k: {sp_rate}
    contraction_per_1k: {contraction_rate}
    parenthetical_per_1k: {paren_rate}
    question_per_1k: {question_rate}
    active_voice_pct: {active_pct}
    lexical_diversity: {vocab['lexical_diversity']}
    avg_word_length: {vocab['avg_word_length']}
    long_word_pct: {vocab['long_word_pct']}
    headers: {formatting['headers']}
    question_headers_pct: {formatting['question_header_pct']}
    bold_instances: {formatting['bold_instances']}
    list_items: {formatting['list_items']}
    code_blocks: {formatting['code_blocks']}
    em_dashes: {formatting['em_dashes']}
    ```
    """)

    return profile


# --- Main ---

def load_sources(source_path: Path) -> tuple[str, list[str]]:
    """Load text from source path. Returns (combined_text, source_descriptions)."""
    if source_path.is_file():
        return source_path.read_text(errors='replace'), [str(source_path)]

    if not source_path.is_dir():
        return '', []

    texts = []
    descriptions = []

    # Look for voice-* files first (from fetch pipeline)
    voice_files = sorted(source_path.glob('voice-*.html')) + sorted(source_path.glob('voice-*.txt'))
    target_files = voice_files if voice_files else sorted(
        f for f in source_path.iterdir()
        if f.is_file() and f.suffix in {'.html', '.txt', '.md', '.rst'}
    )

    for f in target_files:
        content = f.read_text(errors='replace')
        if len(content) > 100:
            texts.append(content)
            # Try to get description from .meta file
            meta = f.with_suffix('.meta')
            if meta.exists():
                for line in meta.read_text().splitlines():
                    if line.startswith('description='):
                        descriptions.append(line.split('=', 1)[1])
                        break
                    if line.startswith('url='):
                        descriptions.append(line.split('=', 1)[1])
                else:
                    descriptions.append(str(f))
            else:
                descriptions.append(str(f))

    return '\n\n'.join(texts), descriptions


def main():
    parser = argparse.ArgumentParser(
        description='Analyze writing samples and generate a voice profile')
    parser.add_argument('source', help='File or directory with writing samples')
    xdg_config = Path(os.environ.get('XDG_CONFIG_HOME',
                                      Path.home() / '.config'))
    xdg_voices = xdg_config / 'humanize' / 'voices'
    if xdg_voices.is_dir():
        default_output = str(xdg_voices / 'blog.local.md')
    else:
        default_output = 'reference/voices/blog.local.md'
    parser.add_argument('--output', '-o',
                        default=default_output,
                        help='Output path (default: XDG voices dir or reference/voices/)')
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f'error: {source} does not exist', file=sys.stderr)
        sys.exit(1)

    text, descriptions = load_sources(source)
    if not text or len(text.split()) < 100:
        print('error: not enough text to analyze (need at least 100 words)',
              file=sys.stderr)
        sys.exit(1)

    word_count = len(text.split())
    print(f'Analyzing {word_count} words from {len(descriptions)} source(s)...',
          file=sys.stderr)

    profile = generate_profile(text, descriptions)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(profile)
    print(f'Draft voice profile written to: {out_path}', file=sys.stderr)
    print(f'Review and edit the generated profile, especially sections marked <!-- EDIT -->',
          file=sys.stderr)


if __name__ == '__main__':
    main()
