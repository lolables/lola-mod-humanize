#!/usr/bin/env python3
"""
update-watchlist.py -- Interactive vocabulary watchlist updater.

Reads the update report from analyze-sources.py and presents new vocabulary
candidates for inclusion into reference/ai-vocabulary-watchlist.md, the
single source of truth. Run "task vocab:sync" afterward to regenerate the
derived copies (vocabulary.py, AGENTS.md, etc.).

Usage:
    python3 scripts/update-watchlist.py [--report <path>] [--auto]

    --report  Path to update-report.md (default: .test-output/update-report/analysis/update-report.md)
    --auto    Non-interactive mode: print candidates and exit without modifying files
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = PROJECT_ROOT / '.test-output' / 'update-report' / 'analysis' / 'update-report.md'
WATCHLIST_MD = PROJECT_ROOT / 'reference' / 'ai-vocabulary-watchlist.md'


def parse_candidates(report_path: Path) -> list[tuple[str, int]]:
    """Extract vocabulary candidates from the update report.
    Returns list of (word, occurrence_count) tuples."""
    if not report_path.exists():
        print(f'Report not found: {report_path}', file=sys.stderr)
        print('Run "task update-sources" first.', file=sys.stderr)
        sys.exit(1)

    text = report_path.read_text()

    # Find the "Potential new watchlist candidates" table
    candidates = []
    in_section = False
    seen_row = False
    for line in text.splitlines():
        if 'Potential new watchlist candidates' in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith('|'):
            if '---' in line or 'Word' in line:
                continue  # table separator or header row
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                word = parts[0].strip()
                try:
                    count = int(parts[1].strip())
                except ValueError:
                    count = 0
                if word and word not in ('Word', 'Occurrences'):
                    candidates.append((word, count))
                    seen_row = True
            continue
        # Non-table line. Only ends the table once we have started collecting
        # rows; prose/blank lines BEFORE the table are skipped, not treated as
        # the end (the report puts an explanatory sentence above the table).
        if seen_row and line.strip() and not line.startswith('#'):
            break

    return candidates


def add_to_watchlist_md(word: str, tier: int):
    """Add a word to the appropriate tier section in the watchlist markdown."""
    content = WATCHLIST_MD.read_text()
    tier_headers = {
        1: 'Tier 1:',
        2: 'Tier 2:',
        3: 'Tier 3:',
    }
    header = tier_headers.get(tier)
    if not header:
        return False

    # Find the last table row in the tier section (before next tier or end of section)
    lines = content.splitlines()
    in_tier = False
    insert_idx = None
    for i, line in enumerate(lines):
        if header in line:
            in_tier = True
        elif in_tier and line.startswith('## Tier') and header not in line:
            break
        elif in_tier and line.startswith('|') and '---' not in line and 'Word' not in line:
            insert_idx = i + 1

    if insert_idx is not None:
        ban = 'yes' if tier == 1 else ''
        lines.insert(insert_idx, f'| {word} | {ban} | (review: suggest replacements) |')
        WATCHLIST_MD.write_text('\n'.join(lines) + '\n')
        return True
    return False


def interactive_review(candidates: list[tuple[str, int]]):
    """Present candidates one by one for inclusion/exclusion."""
    if not candidates:
        print('No new vocabulary candidates found.')
        return

    print(f'\n{len(candidates)} vocabulary candidates to review:\n')

    added = 0
    skipped = 0

    for word, count in candidates:
        print(f'  "{word}" ({count} occurrences in sources)')
        while True:
            choice = input('  Add to tier [1/2/3], (s)kip, (q)uit? ').strip().lower()
            if choice == 'q':
                print(f'\nStopped. Added {added}, skipped {skipped}.')
                return
            if choice == 's':
                skipped += 1
                break
            if choice in ('1', '2', '3'):
                tier = int(choice)
                if add_to_watchlist_md(word, tier):
                    print(f'    Added "{word}" to Tier {tier}.')
                    added += 1
                else:
                    print(f'    Could not add "{word}" to Tier {tier}.', file=sys.stderr)
                break
            print('    Invalid choice. Enter 1, 2, 3, s, or q.')

    print(f'\nDone. Added {added}, skipped {skipped}.')
    if added > 0:
        print('Run "task vocab:sync" to regenerate derived files.')


def main():
    parser = argparse.ArgumentParser(description='Update vocabulary watchlist from source analysis')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT,
                        help='Path to update-report.md')
    parser.add_argument('--auto', action='store_true',
                        help='Non-interactive: list candidates and exit')
    args = parser.parse_args()

    candidates = parse_candidates(args.report)

    if args.auto:
        if not candidates:
            print('No new vocabulary candidates.')
        else:
            print(f'{len(candidates)} candidates:')
            for word, count in candidates:
                print(f'  {word} ({count})')
        sys.exit(0)

    interactive_review(candidates)


if __name__ == '__main__':
    main()
