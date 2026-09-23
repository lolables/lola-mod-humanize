#!/usr/bin/env python3
"""
analyze-sources.py -- Compare freshly fetched sources against current Humanize
reference files and produce an update report.

This script:
1. Parses fetched HTML into plaintext
2. Extracts AI vocabulary words and structural patterns from sources
3. Compares against current watchlist and pattern files
4. Identifies new words, removed words, and changed patterns
5. Checks for AI-tooling contamination in voice calibration sources
6. Produces a Markdown report with proposed updates

Stdlib only -- no pip dependencies.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# --- HTML to text ---

def strip_html(raw: str) -> str:
    """Strip HTML tags and decode entities. Good enough for keyword extraction."""
    # Remove script/style blocks
    text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    text = re.sub(r'<(?:p|div|br|h[1-6]|li|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# --- Vocabulary extraction ---

# vocabulary.py is the shared word-tier source of truth. Its canonical copy
# lives next to the skill scripts (module/skills/humanize/scripts/); this
# file is also imported by the test suite, which injects that directory via
# conftest. When run standalone (task sources), inject it here so the import
# resolves without depending on the caller's sys.path.
_VOCAB_DIR = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts'
if _VOCAB_DIR.is_dir() and str(_VOCAB_DIR) not in sys.path:
    sys.path.insert(0, str(_VOCAB_DIR))

from vocabulary import (  # noqa: E402
    ALL_KNOWN, AI_REPO_PATTERNS, CANDIDATE_PATTERNS,
    TIER1_WORDS, TIER2_WORDS, TIER3_WORDS,
)


def extract_vocabulary(text: str) -> Counter:
    """Extract AI-characteristic vocabulary from text, returning word counts."""
    text_lower = text.lower()
    counts = Counter()
    for pattern in CANDIDATE_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            counts[match.group(1)] += 1
    return counts


def find_new_vocabulary_candidates(text: str) -> list[str]:
    """Look for words that appear in AI-detection contexts but aren't in our
    current watchlist. Heuristic: words near 'AI', 'LLM', 'chatbot',
    'overuse', 'flag', 'detect' that we don't already track."""
    candidates = set()
    # Find sentences mentioning AI detection
    sentences = re.split(r'[.!?]\s+', text)
    detection_sentences = [
        s for s in sentences
        if re.search(r'\b(AI|LLM|chatbot|overuse|flag|detect|typical|sign)\b', s, re.IGNORECASE)
    ]
    # Extract emphasized/quoted words from those sentences
    for sent in detection_sentences:
        # Words in quotes or italics
        quoted = re.findall(r'["\u201c](\w+)["\u201d]', sent)
        italic = re.findall(r'\*(\w+)\*|_(\w+)_', sent)
        for groups in italic:
            quoted.extend(g for g in groups if g)
        for word in quoted:
            w = word.lower().strip()
            if len(w) > 4 and w.isalpha() and w not in ALL_KNOWN and w not in {
                'the', 'and', 'that', 'this', 'with', 'from', 'have',
                'been', 'will', 'they', 'their', 'what', 'when', 'which',
                'text', 'word', 'words', 'writing', 'written', 'content',
                'article', 'human', 'model', 'detect', 'detection',
                'perplexity', 'burstiness', 'however', 'source', 'about',
                'these', 'those', 'other', 'would', 'could', 'should',
                'where', 'there', 'being', 'using', 'after', 'before',
                'first', 'often', 'every', 'still', 'while', 'since',
                'between', 'through', 'during', 'might', 'think',
                'improve', 'earlier', 'later', 'professional', 'corporate',
                'assistant', 'challenge', 'challenges',
            }:
                candidates.add(w)
    return sorted(candidates)


def check_contamination(text: str, slug: str) -> list[str]:
    """Check for AI-tooling repo references in voice calibration sources."""
    if not slug.startswith('voice-'):
        return []
    issues = []
    for pattern in AI_REPO_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            issues.append(f"AI-tooling pattern '{pattern}' found {len(matches)}x in {slug}")
    return issues


# --- Structural pattern extraction ---

def extract_structural_signals(text: str) -> dict:
    """Extract counts of structural AI signals from text."""
    signals = {}

    # Title case headings (Markdown-style)
    headings = re.findall(r'^#{1,4}\s+(.+)$', text, re.MULTILINE)
    title_case = sum(
        1 for h in headings
        if re.match(r'^(?:[A-Z][a-z]+\s+){2,}', h.strip())
    )
    signals['title_case_headings'] = title_case

    # Formulaic transitions at sentence start
    transitions = len(re.findall(
        r'(?:^|\.\s+)(Furthermore|Moreover|Additionally|In addition)[,\s]',
        text, re.IGNORECASE
    ))
    signals['formulaic_transitions'] = transitions

    # Em-dash density
    em_dashes = len(re.findall(r'\u2014|--', text))
    word_count = len(text.split())
    signals['em_dash_per_500w'] = round(em_dashes / max(word_count / 500, 1), 1)

    # "Despite...challenges" pattern
    despite = len(re.findall(
        r'despite\s+(?:its|their|these|the)\s+\w+.*?(?:challenges?|difficulties)',
        text, re.IGNORECASE
    ))
    signals['despite_challenges'] = despite

    # Rule of three
    threes = len(re.findall(r'\w+,\s+\w+,\s+and\s+\w+', text))
    signals['rule_of_three'] = threes

    # Negative parallelism
    neg_par = len(re.findall(
        r'not\s+(?:just|only|merely)\s+.{5,60}?\s+but\s+(?:also)?',
        text, re.IGNORECASE
    ))
    signals['negative_parallelism'] = neg_par

    # Inline-header lists (bold + colon)
    inline_headers = len(re.findall(r'\*\*[^*]+\*\*\s*:', text))
    signals['inline_header_lists'] = inline_headers

    return signals


# --- Report generation ---

def load_current_watchlist(ref_dir: Path) -> set[str]:
    """Load words currently in the AI vocabulary watchlist."""
    watchlist_path = ref_dir / 'ai-vocabulary-watchlist.md'
    if not watchlist_path.exists():
        return set()
    text = watchlist_path.read_text()
    # Extract words from the table cells (first column after |)
    words = set()
    for match in re.finditer(r'\|\s*(\w[\w\s]*?)\s*\|', text):
        w = match.group(1).strip().lower()
        if w and w not in {'word', 'phrase', 'pattern', 'replacement strategy',
                           'when to flag'}:
            words.add(w)
    return words


def generate_report(
    fetch_dir: Path,
    ref_dir: Path,
    output_dir: Path,
    vocab_by_source: dict,
    new_candidates: dict,
    structural_by_source: dict,
    contamination_issues: list[str],
    fetch_meta: dict,
) -> str:
    """Generate the Markdown update report."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    current_words = load_current_watchlist(ref_dir)

    lines = [
        f'# Humanize Source Update Report',
        f'',
        f'Generated: {now}',
        f'',
        f'---',
        f'',
    ]

    # --- Fetch Summary ---
    lines.append('## Fetch summary\n')
    lines.append('| Source | Status | Size | Description |')
    lines.append('|--------|--------|------|-------------|')
    for slug, meta in sorted(fetch_meta.items()):
        status = meta.get('http_code', '?')
        size = meta.get('file_size', '?')
        desc = meta.get('description', '')
        icon = 'OK' if str(status).startswith('2') else 'WARN'
        lines.append(f'| {slug} | {icon} ({status}) | {size}B | {desc} |')
    lines.append('')

    # --- Contamination Check ---
    lines.append('## Voice calibration contamination check\n')
    if contamination_issues:
        lines.append('**ISSUES FOUND** -- AI-tooling references in voice sources:\n')
        for issue in contamination_issues:
            lines.append(f'- {issue}')
        lines.append('')
        lines.append('These should be excluded from voice profile calibration.')
    else:
        lines.append('No AI-tooling contamination found in voice calibration sources.')
    lines.append('')

    # --- Vocabulary Analysis ---
    lines.append('## Vocabulary analysis\n')

    # Aggregate all vocabulary counts
    total_counts = Counter()
    for counts in vocab_by_source.values():
        total_counts += counts

    known_found = {w: c for w, c in total_counts.items()
                   if w in current_words or w in ALL_KNOWN}
    new_found = {w: c for w, c in total_counts.items()
                 if w not in current_words and w not in ALL_KNOWN}

    lines.append('### Words in current watchlist (confirmed still active)\n')
    lines.append('| Word | Occurrences across sources |')
    lines.append('|------|---------------------------|')
    for word, count in sorted(known_found.items(), key=lambda x: -x[1]):
        lines.append(f'| {word} | {count} |')
    lines.append('')

    if new_found:
        lines.append('### Potential new watchlist candidates\n')
        lines.append('Words matching AI-vocabulary patterns found in sources but '
                      'NOT in current watchlist:\n')
        lines.append('| Word | Occurrences | Action needed |')
        lines.append('|------|-------------|---------------|')
        for word, count in sorted(new_found.items(), key=lambda x: -x[1]):
            lines.append(f'| {word} | {count} | Review for inclusion |')
        lines.append('')

    # New candidates from context analysis
    all_candidates = set()
    for cands in new_candidates.values():
        all_candidates.update(cands)
    all_candidates -= current_words
    all_candidates -= ALL_KNOWN

    if all_candidates:
        lines.append('### Context-extracted candidates\n')
        lines.append('Words found near AI-detection discussion in sources, '
                      'not yet in watchlist:\n')
        for w in sorted(all_candidates):
            lines.append(f'- `{w}`')
        lines.append('')

    # --- Structural Pattern Analysis ---
    lines.append('## Structural pattern analysis\n')
    lines.append('Signal counts found in source documents (confirms these '
                 'patterns are still being discussed/documented):\n')
    lines.append('| Pattern | Total across sources |')
    lines.append('|---------|---------------------|')
    agg = Counter()
    for signals in structural_by_source.values():
        for k, v in signals.items():
            if isinstance(v, (int, float)):
                agg[k] += v
    for pattern, count in sorted(agg.items(), key=lambda x: -x[1]):
        lines.append(f'| {pattern} | {count} |')
    lines.append('')

    # --- Recommendations ---
    lines.append('## Recommendations\n')

    rec_num = 0
    if new_found:
        rec_num += 1
        top_new = sorted(new_found.items(), key=lambda x: -x[1])[:5]
        lines.append(f'{rec_num}. **Review new vocabulary candidates:** '
                      f'{", ".join(f"`{w}`({c})" for w, c in top_new)}')

    if contamination_issues:
        rec_num += 1
        lines.append(f'{rec_num}. **Fix voice contamination:** '
                      f'{len(contamination_issues)} AI-tooling references '
                      f'found in voice calibration sources')

    missing_sources = [
        slug for slug, meta in fetch_meta.items()
        if not str(meta.get('http_code', '')).startswith('2')
    ]
    if missing_sources:
        rec_num += 1
        lines.append(f'{rec_num}. **Check failed fetches:** '
                      f'{", ".join(missing_sources)} -- may need URL updates')

    if rec_num == 0:
        lines.append('No updates required. Current reference files are up to date.')

    lines.append('')
    lines.append('---')
    lines.append(f'*Report generated by scripts/update-sources.sh + '
                 f'scripts/analyze-sources.py*')

    return '\n'.join(lines)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='Analyze Humanize sources')
    parser.add_argument('--fetch-dir', required=True, help='Directory with fetched HTML')
    parser.add_argument('--reference-dir', required=True, help='Directory with current reference files')
    parser.add_argument('--output-dir', required=True, help='Directory for analysis output')
    args = parser.parse_args()

    fetch_dir = Path(args.fetch_dir)
    ref_dir = Path(args.reference_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fetch_meta = {}
    for metafile in sorted(fetch_dir.glob('*.meta')):
        meta = {}
        for line in metafile.read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                meta[k.strip()] = v.strip()
        slug = meta.get('slug', metafile.stem)
        fetch_meta[slug] = meta

    # Process each fetched source
    vocab_by_source = {}
    new_candidates = {}
    structural_by_source = {}
    contamination_issues = []

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    for html_file in sorted(fetch_dir.glob('*.html')):
        slug = html_file.stem

        file_size = html_file.stat().st_size
        if file_size > MAX_FILE_SIZE:
            print(f'WARNING: Skipping {slug} ({file_size} bytes) -- exceeds {MAX_FILE_SIZE} byte limit',
                  file=sys.stderr)
            continue

        raw = html_file.read_text(errors='replace')
        text = strip_html(raw)

        if not text or len(text) < 100:
            continue

        # Vocabulary extraction
        vocab_by_source[slug] = extract_vocabulary(text)

        # New candidate discovery
        new_candidates[slug] = find_new_vocabulary_candidates(text)

        # Structural signals
        structural_by_source[slug] = extract_structural_signals(text)

        # Contamination check (voice sources only)
        issues = check_contamination(text, slug)
        contamination_issues.extend(issues)

        # Save plaintext for reference
        (output_dir / f'{slug}.txt').write_text(text[:50000])

    # Generate report
    report = generate_report(
        fetch_dir, ref_dir, output_dir,
        vocab_by_source, new_candidates,
        structural_by_source, contamination_issues,
        fetch_meta,
    )

    report_path = output_dir / 'update-report.md'
    report_path.write_text(report)
    print(f'Report written to: {report_path}')


if __name__ == '__main__':
    main()
