#!/usr/bin/env python3
"""
sync_vocabulary.py -- Generate every derived copy of the AI vocabulary.

reference/ai-vocabulary-watchlist.md is the single source of truth. This
script parses its tier tables and rewrites the marked regions in
vocabulary.py, AGENTS.md, reference/writing-discipline.md, and the humanize
SKILL.md.

Usage:
    python3 scripts/sync_vocabulary.py            # rewrite in place
    python3 scripts/sync_vocabulary.py --check    # exit 1 if any copy is stale

    Backslash-escaped pipes (\\|) inside table cells are NOT supported; table
    cells must not contain literal pipe characters.

Exit codes: 0 clean, 1 stale (--check only), 2 malformed markers.
"""
from __future__ import annotations

import argparse
import dataclasses
import difflib
import re
import sys
import textwrap
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = PROJECT_ROOT / 'reference' / 'ai-vocabulary-watchlist.md'

TIER_HEADING_RE = re.compile(r'^## Tier (\d+)')
SEPARATOR_CELL_RE = re.compile(r':?-+:?')


class MarkerError(RuntimeError):
    """A target file is missing a well-formed generated-region marker pair."""


class WatchlistError(RuntimeError):
    """A watchlist table row does not match its header row."""


@dataclasses.dataclass(frozen=True)
class Row:
    """One table row from a tier section of the watchlist."""
    tier: int
    term: str
    ban: str = ''
    match: str = ''
    role: str = ''


def parse_watchlist(text: str) -> list[Row]:
    """Parse tier tables into Row records.

    Ban/Match/Role are located by header name; the term is always column 0.
    """
    rows: list[Row] = []
    tier: int | None = None
    headers: list[str] = []
    expect_separator = False

    for line in text.splitlines():
        heading = TIER_HEADING_RE.match(line)
        if heading:
            tier = int(heading.group(1))
            headers = []
            expect_separator = False
            continue
        if line.startswith('## '):
            tier = None
            continue
        if tier is None or not line.startswith('|'):
            continue

        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if not headers:
            headers = [c.lower() for c in cells]
            expect_separator = True
            continue
        if expect_separator:
            expect_separator = False
            if cells and all(SEPARATOR_CELL_RE.fullmatch(c) for c in cells):
                continue
        if len(cells) != len(headers):
            raise WatchlistError(
                f'Tier {tier}: row has {len(cells)} cells but the header has '
                f'{len(headers)}: {line.strip()!r}'
            )

        def col(name: str) -> str:
            if name not in headers:
                return ''
            return cells[headers.index(name)]

        rows.append(Row(
            tier=tier,
            term=cells[0],
            ban=col('ban').lower(),
            match=col('match'),
            role=col('role').lower(),
        ))
    return rows


PAREN_RE = re.compile(r'\s*\(.*?\)')


def variants(term: str) -> list[str]:
    """Every lowercase form a term contributes to a Python set."""
    base = PAREN_RE.sub('', term).strip()
    return [v.strip().lower() for v in base.split('/') if v.strip()]


def display(term: str) -> str:
    """Canonical prose form: first slash-variant, parenthetical intact."""
    return term.split('/')[0].strip()


def bare(term: str) -> str:
    """First slash-variant with the parenthetical removed, case preserved."""
    return PAREN_RE.sub('', term).split('/')[0].strip()


def matches(row: Row) -> list[str]:
    """Literal strings the scanner should look for."""
    raw = row.match.strip() if row.match.strip() else PAREN_RE.sub('', row.term)
    return [m.strip().lower() for m in raw.split(',') if m.strip()]


@dataclasses.dataclass(frozen=True)
class Derived:
    """Every list generated from the watchlist."""
    tier1: list[str]
    tier2: list[str]
    tier3: list[str]
    banned_phrases: list[str]
    transition_starters: list[str]
    generic_openers: list[str]
    generic_closers: list[str]
    prose_words: list[str]
    prose_phrases: list[str]
    prose_transitions: list[str]


def _dedup(items: list[str]) -> list[str]:
    """Order-preserving dedup; document order is the generated order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def derive(rows: list[Row]) -> Derived:
    """Compute every generated list from parsed watchlist rows."""
    def tier_words(n: int) -> list[str]:
        return _dedup([v for r in rows if r.tier == n for v in variants(r.term)])

    transitions = [r for r in rows if r.tier == 3 and '(sentence-start)' in r.term]
    phrase_rows = [r for r in rows if r.tier in (4, 5) and r.ban == 'yes']

    def positional(role: str) -> list[str]:
        return _dedup([m for r in rows if r.tier in (4, 5) and r.role == role
                       for m in matches(r)])

    return Derived(
        tier1=tier_words(1),
        tier2=tier_words(2),
        tier3=tier_words(3),
        banned_phrases=_dedup([m for r in phrase_rows for m in matches(r)]),
        transition_starters=_dedup([v + ',' for r in transitions for v in variants(r.term)]),
        generic_openers=positional('opener'),
        generic_closers=positional('closer'),
        prose_words=_dedup(
            [display(r.term) for r in rows if r.tier in (1, 2, 3) and r.ban == 'yes']
        ),
        prose_phrases=_dedup([r.term for r in phrase_rows]),
        prose_transitions=_dedup([bare(r.term) for r in transitions]),
    )


WRAP_WIDTH = 76


def literal(value: str) -> str:
    """Python string literal, switching quote style to avoid escapes."""
    return f'"{value}"' if "'" in value else f"'{value}'"


def _pack_literals(items: list[str], indent: str = '    ') -> list[str]:
    """Pack literals into lines, breaking only between items, never inside one."""
    lines: list[str] = []
    current = ''
    for item in items:
        piece = f'{item},'
        if not current:
            current = indent + piece
        elif len(current) + 1 + len(piece) <= WRAP_WIDTH:
            current += ' ' + piece
        else:
            lines.append(current)
            current = indent + piece
    if current:
        lines.append(current)
    return lines


def _render_py_collection(name: str, items: list[str], open_c: str, close_c: str, kind: str) -> str:
    if not items:
        empty = 'set()' if kind == 'set' else '[]'
        return f'{name}: {kind}[str] = {empty}'
    body = '\n'.join(_pack_literals([literal(i) for i in items]))
    return f'{name}: {kind}[str] = {open_c}\n{body}\n{close_c}'


def render_py_set(name: str, items: list[str]) -> str:
    return _render_py_collection(name, items, '{', '}', 'set')


def render_py_list(name: str, items: list[str]) -> str:
    return _render_py_collection(name, items, '[', ']', 'list')


def join_or(items: list[str]) -> str:
    """Join for prose: 'A, B, or C'."""
    if len(items) == 1:
        return items[0]
    return ', '.join(items[:-1]) + ', or ' + items[-1]


PROSE_TEMPLATES = {
    'agents': {
        'words': 'Words -- never use: {words}.',
        'phrases': 'Phrases -- never use: {phrases}.',
        'transitions': 'Never open a sentence with {transitions}.',
    },
    'skill': {
        'words': ('Your transformed text must also follow these rules. Do not use '
                  'these words in your output: {words}.'),
        'phrases': 'Do not use {phrases}.',
        'transitions': 'Do not open sentences with {transitions}.',
    },
}


def render_prose(target: str, d: Derived) -> str:
    """Render the banned-word/phrase/transition sentences for one prose target."""
    tpl = PROSE_TEMPLATES[target]
    paragraphs: list[str] = []
    if d.prose_words:
        paragraphs.append(tpl['words'].format(words=', '.join(d.prose_words)))
    if d.prose_phrases:
        quoted = ', '.join(f'"{p}"' for p in d.prose_phrases)
        paragraphs.append(tpl['phrases'].format(phrases=quoted))
    if d.prose_transitions:
        paragraphs.append(tpl['transitions'].format(transitions=join_or(d.prose_transitions)))
    return '\n\n'.join(
        textwrap.fill(p, width=WRAP_WIDTH, break_long_words=False, break_on_hyphens=False)
        for p in paragraphs
    )


def _markers(name: str, syntax: str) -> tuple[str, str]:
    if syntax == 'md':
        return f'<!-- BEGIN GENERATED: {name} -->', f'<!-- END GENERATED: {name} -->'
    return f'# BEGIN GENERATED: {name}', f'# END GENERATED: {name}'


def replace_region(text: str, name: str, body: str, syntax: str) -> str:
    """Swap the body between a marker pair. Raises MarkerError if malformed."""
    begin, end = _markers(name, syntax)
    start = text.find(begin)
    stop = text.find(end)
    if start == -1 or stop == -1 or stop < start:
        raise MarkerError(
            f'{name}: expected marker pair {begin!r} ... {end!r} in order'
        )
    return f'{text[:start + len(begin)]}\n{body}\n{text[stop:]}'


SKILL_DIR = PROJECT_ROOT / 'module' / 'skills' / 'humanize'
VOCABULARY_PY = SKILL_DIR / 'scripts' / 'vocabulary.py'


@dataclasses.dataclass(frozen=True)
class Target:
    """One file region this script owns."""
    path: Path
    marker: str
    syntax: str
    render: Callable[[Derived], str]


def _py_tier_words(d: Derived) -> str:
    return '\n\n'.join([
        render_py_set('TIER1_WORDS', d.tier1),
        render_py_set('TIER2_WORDS', d.tier2),
        render_py_set('TIER3_WORDS', d.tier3),
    ])


def _py_phrases(d: Derived) -> str:
    return '\n\n'.join([
        render_py_list('BANNED_PHRASES', d.banned_phrases),
        render_py_list('TRANSITION_STARTERS', d.transition_starters),
        render_py_list('GENERIC_OPENERS', d.generic_openers),
        render_py_list('GENERIC_CLOSERS', d.generic_closers),
    ])


TARGETS: list[Target] = [
    Target(VOCABULARY_PY, 'tier-words', 'py', _py_tier_words),
    Target(VOCABULARY_PY, 'phrases', 'py', _py_phrases),
    Target(PROJECT_ROOT / 'AGENTS.md', 'banned', 'md',
           lambda d: render_prose('agents', d)),
    Target(PROJECT_ROOT / 'reference' / 'writing-discipline.md', 'banned', 'md',
           lambda d: render_prose('agents', d)),
    Target(SKILL_DIR / 'SKILL.md', 'banned', 'md',
           lambda d: render_prose('skill', d)),
]


def build_outputs(d: Derived) -> dict[Path, str]:
    """Map each target path to its fully rewritten text.

    Two targets share vocabulary.py, so regions are applied cumulatively.
    """
    outputs: dict[Path, str] = {}
    for target in TARGETS:
        current = outputs.get(target.path, target.path.read_text())
        outputs[target.path] = replace_region(
            current, target.marker, target.render(d), target.syntax
        )
    return outputs


def run(check: bool) -> int:
    """Rewrite or verify every target. Returns the process exit code."""
    try:
        d = derive(parse_watchlist(WATCHLIST.read_text()))
        outputs = build_outputs(d)
    except (MarkerError, WatchlistError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2

    stale = []
    for path, new_text in outputs.items():
        old_text = path.read_text()
        if old_text == new_text:
            continue
        stale.append(path)
        if check:
            try:
                rel = path.relative_to(PROJECT_ROOT)
            except ValueError:
                rel = path
            print(''.join(difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f'{rel} (on disk)', tofile=f'{rel} (generated)',
            )))
        else:
            path.write_text(new_text)

    if check and stale:
        names = ', '.join(str(p) for p in stale)
        print(f'\n{len(stale)} file(s) stale: {names}', file=sys.stderr)
        print('Run "task vocab:sync" to regenerate.', file=sys.stderr)
        return 1
    if not check:
        print(f'Synced {len(stale)} file(s) from {WATCHLIST.name}.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='verify without writing; exit 1 if stale')
    return run(check=parser.parse_args().check)


if __name__ == '__main__':
    sys.exit(main())
