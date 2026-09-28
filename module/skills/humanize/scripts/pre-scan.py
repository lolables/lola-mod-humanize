"""pre-scan.py -- Mechanical scanner for AI-detectable patterns.

Reports vocabulary hits, banned phrases, and formulaic transitions
with line numbers. No rewrites, just findings.
"""
from __future__ import annotations
import re
import math
import bisect
import difflib
import subprocess
import argparse
import sys
import importlib.util
from pathlib import Path

# Load vocabulary from sibling module (works from project root and as installed skill).
_vocab_path = Path(__file__).resolve().parent / 'vocabulary.py'
_spec = importlib.util.spec_from_file_location('vocabulary', _vocab_path)
_vocab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vocab)

TIER1_WORDS = _vocab.TIER1_WORDS
TIER2_WORDS = _vocab.TIER2_WORDS
TIER3_WORDS = _vocab.TIER3_WORDS
BANNED_PHRASES = _vocab.BANNED_PHRASES
TRANSITION_STARTERS = _vocab.TRANSITION_STARTERS
GENERIC_OPENERS = _vocab.GENERIC_OPENERS
GENERIC_CLOSERS = _vocab.GENERIC_CLOSERS

# Pre-compile patterns. Split multi-word entries from single-word for matching.
_tier1_re = re.compile(r'\b(' + '|'.join(re.escape(w) for w in TIER1_WORDS) + r')\b', re.I)
_tier2_singles = {w for w in TIER2_WORDS if ' ' not in w}
_tier2_phrases = [w for w in TIER2_WORDS if ' ' in w]
_tier2_single_re = re.compile(r'\b(' + '|'.join(re.escape(w) for w in _tier2_singles) + r')\b', re.I) if _tier2_singles else None
_tier2_phrase_re = re.compile('|'.join(re.escape(p) for p in _tier2_phrases), re.I) if _tier2_phrases else None
_tier3_re = re.compile(r'\b(' + '|'.join(re.escape(w) for w in TIER3_WORDS) + r')\b', re.I)
_banned_re = re.compile('|'.join(re.escape(p) for p in BANNED_PHRASES), re.I)
# Transitions: line start or after sentence-ending punctuation + space
_transition_re = re.compile(
    r'(?:^|(?<=[.!?]\s))(' + '|'.join(re.escape(t) for t in TRANSITION_STARTERS) + r')',
    re.I | re.M,
)
_em_dash_re = re.compile(r'\u2014')
_en_dash_re = re.compile(r'\u2013')
# A table cell holding only an em or en dash marks an empty value; it is
# not a connector dash. Group 1 is the dash itself.
_lone_dash_cell_re = re.compile(r'(?<=\|)[ \t]*([\u2013\u2014])[ \t]*(?=\||[ \t]*$)')
_ascii_dash_re = re.compile(r'\w\s--\s\w')
# A bold span may contain single asterisks (nested italics) but not "**".
_BOLD_BODY = r'(?:[^*]|\*(?!\*))+?'
_inline_header_re = re.compile(
    rf'\*\*{_BOLD_BODY}:\*\*|\*\*{_BOLD_BODY}\*\*\s*:')
_bold_re = re.compile(rf'\*\*{_BOLD_BODY}\*\*')
_neg_parallel_re = re.compile(r'not\s+(?:just|only|merely)\s+.{5,60}?\s+but\s+(?:also\s+)?', re.I)
_despite_challenges_re = re.compile(
    r'[Dd]espite\s+(?:its|their|these|the|this)\s+\w+.*?(?:challeng|difficult|limitation|shortcoming)',
)
_opener_re = re.compile(
    r'^(' + '|'.join(re.escape(p) for p in GENERIC_OPENERS) + r')', re.I,
)
_closer_re = re.compile(
    r'^(' + '|'.join(re.escape(p) for p in GENERIC_CLOSERS) + r')', re.I,
)
COLLABORATIVE_REMNANTS = [
    "i hope this helps",
    "would you like me to",
    "let me know if you",
    "let me know if there",
    "here's a comprehensive",
    "feel free to",
    "don't hesitate to",
    "i'd be happy to",
]
_collab_re = re.compile('|'.join(re.escape(p) for p in COLLABORATIVE_REMNANTS), re.I)


def scan_text(text: str, filename: str) -> list[dict]:
    """Scan text for AI-detectable patterns. Returns list of finding dicts."""
    if not text:
        return []
    findings: list[dict] = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        # Check 1: Tier 1
        for m in _tier1_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'tier1', 'severity': 'HIGH'})
        # Check 2: Tier 2
        if _tier2_single_re:
            for m in _tier2_single_re.finditer(line):
                findings.append({'line': i, 'text': m.group(), 'tag': 'tier2', 'severity': 'HIGH'})
        if _tier2_phrase_re:
            for m in _tier2_phrase_re.finditer(line):
                findings.append({'line': i, 'text': m.group(), 'tag': 'tier2', 'severity': 'HIGH'})
        # Check 3: Tier 3
        for m in _tier3_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'tier3', 'severity': 'MEDIUM'})
        # Check 4: Banned phrases
        for m in _banned_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'banned-phrase', 'severity': 'HIGH'})
        # Check 5: Formulaic transitions
        for m in _transition_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'transition', 'severity': 'HIGH'})
        # Checks 6-7 skip a dash that is a table cell's whole content.
        empty_cells = ({m.start(1) for m in _lone_dash_cell_re.finditer(line)}
                       if line.lstrip().startswith('|') else set())
        # Check 6: Em dash
        for m in _em_dash_re.finditer(line):
            if m.start() in empty_cells:
                continue
            findings.append({'line': i, 'text': m.group(), 'tag': 'em-dash', 'severity': 'HIGH'})
        # Check 7: En dash (skip number ranges like 1–5)
        for m in _en_dash_re.finditer(line):
            s = m.start()
            if s in empty_cells:
                continue
            if s > 0 and s < len(line) - 1 and line[s - 1].isdigit() and line[s + 1].isdigit():
                continue
            findings.append({'line': i, 'text': m.group(), 'tag': 'en-dash', 'severity': 'HIGH'})
        # Check 8: ASCII prose dash (not CLI flags, YAML delimiters, SQL comments)
        for m in _ascii_dash_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'ascii-dash', 'severity': 'HIGH'})
        # Check 9: Inline-header lists (**Bold:** pattern)
        ih_spans = []
        for m in _inline_header_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'inline-header', 'severity': 'MEDIUM'})
            ih_spans.append(m.span())
        # Check 10: Excessive boldface (skip if already caught as inline-header)
        for m in _bold_re.finditer(line):
            if any(m.start() >= s[0] and m.end() <= s[1] for s in ih_spans):
                continue
            findings.append({'line': i, 'text': m.group(), 'tag': 'bold', 'severity': 'MEDIUM'})
        # Check 11: Negative parallelism
        for m in _neg_parallel_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'negative-parallelism', 'severity': 'MEDIUM'})
        # Check 12: Despite-challenges
        for m in _despite_challenges_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'despite-challenges', 'severity': 'MEDIUM'})
        # Check 13: Generic openers/closers (line-start only)
        stripped = line.lstrip()
        for m in _opener_re.finditer(stripped):
            findings.append({'line': i, 'text': m.group(), 'tag': 'generic-opener', 'severity': 'HIGH'})
        for m in _closer_re.finditer(stripped):
            findings.append({'line': i, 'text': m.group(), 'tag': 'generic-closer', 'severity': 'HIGH'})
        # Check 14: Collaborative remnants
        for m in _collab_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'collaborative-remnant', 'severity': 'HIGH'})
    return findings


VOCAB_TAGS = {'tier1', 'tier2', 'tier3', 'banned-phrase', 'transition'}

# --- Readability lane (structure-fit spec, Part D) ---
# Absolute, voice-agnostic defaults. --voice refines max_sentence_len and
# replaces the DEFAULT_MIN_SD floor with its sentence_length_sd range.
DEFAULT_MAX_SENTENCE_LEN = 45    # words; longer flags a run-on
# 6, not 4: list commas ("metrics, logs, and traces") and coordinating
# conjunctions inflate the raw count, so a well-structured list-bearing
# sentence reads as ~6 boundaries. 6 still catches genuinely over-nested prose.
DEFAULT_MAX_CLAUSE_DEPTH = 6     # clause boundaries; more flags over-nesting
DEFAULT_MAX_PARA_SENTENCES = 6   # prose sentences per paragraph before wall-of-text
DEFAULT_MIN_SD = 8               # sentence-length SD floor when no voice gives a range

# The readability lane is a prose concern. In code, commas and keywords
# (and/or/if/while) are syntax, not clauses, so running it on source files
# produces false positives. Restrict the lane to prose file types.
PROSE_SUFFIXES = {'.md', '.markdown', '.txt', '.rst', '.adoc', '.org', '.text'}

# Clause boundaries: commas, semicolons, and a closed set of conjunctions.
_clause_marker_re = re.compile(
    r',|;|\b(?:and|but|or|which|that|because|although|though|while|whereas|since|unless)\b',
    re.I,
)
# A structural (non-prose) line: heading, list item, or table row.
# Fence lines never reach this check: _content_lines already drops them.
_structure_line_re = re.compile(r'^\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|\|)')

# CommonMark measures a fence's 0-3 space allowance from the enclosing
# container (e.g. a list item), not column 0, so a scanner that doesn't
# track container nesting has to accept a fence at any indent. The
# original bug was never about indentation: a multi-line HTML comment
# that mentioned a fence toggled the fence state and hid every later
# paragraph. _content_lines skips comment blocks outright instead.
# The run is captured (not just 3 chars) because a closing fence must
# use the same character and at least as many repeats as the opener.
_fence_re = re.compile(r'^\s*(`{3,}|~{3,})')

# A frontmatter delimiter only closes the block at column 0, so an
# indented "---" inside a YAML block scalar does not end it.
_frontmatter_close_re = re.compile(r'^(?:---|\.\.\.)\s*$')

# A list marker, checked only against lines indented under 4 columns (the
# indented-code-block threshold below), matching _structure_line_re's own
# bullet/ordered-list alternatives.
_list_item_re = re.compile(r'^\s*(?:[-*+]\s|\d+\.\s)')

# An ATX heading (CommonMark 4.2: 0-3 space indent, 1-6 #s, then a space
# or end of line). A heading always ends whatever paragraph came before
# it, so it counts as "blank" for the indented-code-block decision below.
_heading_line_re = re.compile(r'^\s{0,3}#{1,6}(?:\s|$)')

# A line opening with a CommonMark type-6 block tag (spec 0.31.2, 4.6),
# open or close: <details>, <summary>...</summary>, </details>, <div>.
# These tags can interrupt a paragraph, and the line is markup (a
# <summary> is a disclosure label, like a heading), so it ends the
# paragraph and is not prose. Inline tags (<kbd>, <code>, <a>) at line
# start stay prose. Text lines between the tags are still prose: the
# reader sees them.
_HTML_BLOCK_TAGS = (
    'address|article|aside|base|basefont|blockquote|body|caption|center|col|'
    'colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|'
    'footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|'
    'link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|'
    'section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul'
)
_html_block_line_re = re.compile(
    rf'^\s*</?(?:{_HTML_BLOCK_TAGS})(?=\s|/?>|$)', re.I)

# A line that is one emphasis span and nothing else: an italic figure
# caption (*Figure 1: ...*), a bold pseudo-heading, or an emphasized
# sentence. Nothing in the line tells a caption from a sentence, so it
# stays prose but becomes its own paragraph: an unpunctuated caption no
# longer glues onto the sentences around it. Dropping it instead would
# hide a real emphasized sentence from the readability checks.
_emphasis_line_re = re.compile(r'^\s*(\*{1,3}|_{1,3})(?=\S)(?:(?!\1).)+(?<=\S)\1\s*$')


def _clause_depth(sentence: str) -> int:
    return len(_clause_marker_re.findall(sentence))


def _indent_width(line: str) -> int:
    """Leading indent in columns, a tab counting as 4 (CommonMark 4.4).

    This is a flat +4 per tab, not tab-stop alignment from the current
    column; no fixture in this repo exercises tabs, so the simpler rule
    stands until one does.
    """
    width = 0
    for ch in line:
        if ch == ' ':
            width += 1
        elif ch == '\t':
            width += 4
        else:
            break
    return width


def _content_lines(text: str) -> list[tuple[int, str]]:
    """Real document content as (line number, raw line) pairs.

    Excludes fence marker lines, lines inside fenced code, lines of a
    multi-line HTML comment, leading YAML frontmatter, and lines inside an
    indented code block. A fence opened with a run of N backticks or
    tildes closes only on a line that, once stripped, is nothing but the
    same character repeated at least N times, so a shorter or mismatched
    run inside an open fence is just fenced content. A backtick run does
    not open a fence at all if another backtick follows it later on the
    same line (CommonMark: a backtick fence's info string cannot contain a
    backtick, so that line is an inline code span in prose); tilde fences
    have no such restriction. HTML block type 2 (CommonMark) starts only
    when a line begins, ignoring indent, with <!--; a single-line comment
    (<!-- x -->) is ordinary content, but if no --> follows the LAST <!--
    on that opening line, it swallows lines up to and including the line
    that closes it.

    A line indented 4+ columns opens an indented code block (CommonMark
    4.4) only if it does not continue a paragraph (the previous line is
    blank, or the file starts there) and it is not list-item continuation:
    if the most recent non-blank line indented under 4 columns was a list
    item, a blank-then-indented run after it is the item's lazy
    continuation, still prose. Once opened, the block continues through
    every line indented 4+ and through blank lines, and ends at the next
    non-blank line indented under 4 columns, which is itself ordinary
    content.

    A heading, a fence's closing marker, a comment block's closing
    marker, and frontmatter's closing delimiter also count as "blank" for
    that continuation check: none of them can leave a paragraph open
    behind them, so an indented line right after one starts a code block,
    with or without an actual blank line between them. A closing fence or
    comment marker also ends the current list item's lazy continuation,
    but only if its opener sat at column 0-1, outside the item; an opener
    indented 2+ is inside the item's own content, so the item stays open
    across it (its own text right after the fence or comment is still the
    item's continuation, not code). An 8-space indent under a nested list
    item (the container's own 4 plus the code's 4), a setext heading
    underline, and an indented closing fence are not handled; all three
    are read as prose, known gaps.
    """
    text = text.lstrip('﻿')
    lines = text.split('\n')
    frontmatter_end = 0
    if len(lines) > 1 and lines[0].rstrip() == '---' and lines[1].strip():
        for j in range(1, len(lines)):
            if _frontmatter_close_re.match(lines[j]):
                frontmatter_end = j + 1
                break
    out: list[tuple[int, str]] = []
    in_fence = False
    fence_char = ''
    fence_len = 0
    fence_opener_indent = 0
    in_comment = False
    comment_opener_indent = 0
    in_indented_code = False
    # True at the start of the file: an indented first line has no
    # preceding paragraph to continue.
    prev_blank = True
    last_list_item = False
    for i, line in enumerate(lines, 1):
        this_blank = not line.strip()
        if i <= frontmatter_end:
            # The closing delimiter line (i == frontmatter_end) cannot
            # leave a paragraph open behind it.
            prev_blank = True if i == frontmatter_end else this_blank
            continue
        if in_comment:
            closed = '-->' in line
            if closed:
                in_comment = False
                # A comment (or fence, below) indented 2+ sits inside a
                # list item's own content -- it does not end the item, so
                # text after it is still the item's continuation. Only a
                # column 0-1 opener, outside the item, ends it.
                if comment_opener_indent < 2:
                    last_list_item = False
            prev_blank = True if closed else this_blank
            continue
        if in_fence:
            stripped = line.strip()
            closed = len(stripped) >= fence_len and set(stripped) == {fence_char}
            if closed:
                in_fence = False
                if fence_opener_indent < 2:
                    last_list_item = False
            prev_blank = True if closed else this_blank
            continue
        if in_indented_code:
            if this_blank:
                prev_blank = True
                continue
            if _indent_width(line) >= 4:
                prev_blank = False
                continue
            in_indented_code = False
            # Falls through: this line, indented under 4, ends the block
            # and is itself ordinary content handled below.
        # Checked before _fence_re/comment-start: a 4+ space indent that
        # continues an open code block (or opens a new one) is code even
        # if its content also happens to look like a fence marker or an
        # HTML comment opener. An indented, unbalanced fence used to open
        # a real fence here and swallow every line after it looking for a
        # closer that was never coming.
        if not this_blank and _indent_width(line) >= 4 and prev_blank and not last_list_item:
            in_indented_code = True
            prev_blank = False
            continue
        m = _fence_re.match(line)
        if m and not (m.group(1)[0] == '`' and '`' in line[m.end():]):
            in_fence = True
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            fence_opener_indent = _indent_width(line)
            prev_blank = this_blank
            continue
        if line.lstrip().startswith('<!--'):
            idx = line.rindex('<!--')
            if '-->' not in line[idx + 4:]:
                in_comment = True
                comment_opener_indent = _indent_width(line)
                prev_blank = this_blank
                continue
        out.append((i, line))
        # A heading cannot leave a paragraph open behind it either.
        prev_blank = True if _heading_line_re.match(line) else this_blank
        if not this_blank and _indent_width(line) < 4:
            last_list_item = bool(_list_item_re.match(line))
    return out


def _list_item_lines(text: str) -> set[int]:
    """Line numbers of list items and of the content lines that continue them.

    Built on _content_lines. A list item opens at a list marker; its
    content column is where the text after the marker starts. A line
    directly after item content continues the item (lazy continuation)
    unless it is structural, an HTML block tag, or a blockquote. After a
    blank line or dropped block, a line continues the innermost open item
    whose content column it reaches; items with a deeper column close. A
    nested marker closes the items deeper than its own indent and opens a
    new one, so text after a sub-list can still continue the outer item.
    """
    out: set[int] = set()
    columns: list[int] = []
    prev = None
    after_gap = True
    for i, line in _content_lines(text):
        if prev is not None and i != prev + 1:
            after_gap = True
        prev = i
        if not line.strip():
            after_gap = True
            continue
        indent = _indent_width(line)
        m = _list_item_re.match(line)
        if m:
            while columns and columns[-1] > indent:
                columns.pop()
            # Measured like _indent_width, a tab counting as 4 columns.
            prefix = line[:len(line) - len(line[m.end():].lstrip(' \t'))]
            columns.append(sum(4 if ch == '\t' else 1 for ch in prefix))
            out.add(i)
        elif columns:
            lazy = not after_gap and not (_structure_line_re.match(line)
                                          or _html_block_line_re.match(line)
                                          or line.lstrip().startswith('>'))
            if not lazy:
                while columns and columns[-1] > indent:
                    columns.pop()
            if lazy or columns:
                out.add(i)
        after_gap = False
    return out


def _prose_paragraphs(text: str) -> list[list[tuple[int, str]]]:
    """Prose paragraphs as lists of (line number, stripped line).

    Built on _content_lines, so fenced code, HTML comment blocks, and
    leading YAML frontmatter are already gone. A paragraph also ends at a
    blank line, a structural line (heading, list item, table row), an
    HTML block tag line (see _html_block_line_re), a blockquote line, or
    a gap in line numbers (content _content_lines dropped). A line that
    is one emphasis span (see _emphasis_line_re) is a paragraph of its
    own. Blockquotes are excluded because quoted text is someone
    else's words; humanize does not rewrite it. A blockquote continues
    lazily: once a `>` line opens one, later non-blank lines belong to
    the quote, not to prose, until a blank line or a structural line
    (heading, list item, table row) ends it, even without their own `>`
    marker.
    """
    paras: list[list[tuple[int, str]]] = []
    buf: list[tuple[int, str]] = []
    prev_line = None
    in_quote = False

    def flush():
        nonlocal buf
        if buf:
            paras.append(buf)
            buf = []

    for i, line in _content_lines(text):
        if prev_line is not None and i != prev_line + 1:
            flush()
            in_quote = False
        prev_line = i
        stripped = line.strip()
        if not stripped:
            flush()
            in_quote = False
            continue
        if line.lstrip().startswith('>'):
            flush()
            in_quote = True
            continue
        if _structure_line_re.match(line) or _html_block_line_re.match(line):
            flush()
            in_quote = False
            continue
        if in_quote:
            continue
        if _emphasis_line_re.match(line):
            flush()
            paras.append([(i, stripped)])
            continue
        buf.append((i, stripped))
    flush()
    return paras


def scan_readability(text: str,
                     max_sentence_len: int = DEFAULT_MAX_SENTENCE_LEN,
                     max_clause_depth: int = DEFAULT_MAX_CLAUSE_DEPTH,
                     max_para_sentences: int = DEFAULT_MAX_PARA_SENTENCES) -> list[dict]:
    """Flag long/over-nested sentences and wall-of-text paragraphs.

    Symptoms only; never rewrites. Skips fenced code, structural lines,
    blockquotes, and frontmatter so prose density is measured against
    prose, not markup.
    """
    findings: list[dict] = []
    for para in _prose_paragraphs(text):
        start_line = para[0][0]
        sents = [s for _, s, _, _ in _paragraph_sentences(para) if len(s.split()) > 2]
        if len(sents) > max_para_sentences:
            findings.append({'line': start_line, 'text': f'{len(sents)} sentences',
                             'tag': 'wall-of-text', 'severity': 'MEDIUM'})
        for s in sents:
            wc = len(s.split())
            if wc > max_sentence_len:
                findings.append({'line': start_line, 'text': f'{wc}-word sentence',
                                 'tag': 'long-sentence', 'severity': 'MEDIUM'})
            else:
                depth = _clause_depth(s)
                if depth > max_clause_depth:
                    findings.append({'line': start_line, 'text': f'{depth} clauses',
                                     'tag': 'clause-heavy', 'severity': 'LOW'})
    return findings


# --- Sentence lane: relations between neighbouring sentences ---
# Findings are prompts for the Pass 4 Tighten step, never verdicts.

# Inline code and HTML comments are masked, not removed, so offsets still
# map back to source lines. The mask character is excluded from _word_re's
# alphabet on purpose: a masked span then contributes no words at all to
# antithesis's word extraction, with no separate filtering step needed.
_masked_re = re.compile(r'`[^`]*`|<!--.*?-->')
_MASK_CHAR = '#'
# The one sentence splitter for the file: the readability lane, the stats,
# and the sentence lane all split through _paragraph_sentences. Closing
# quotes, brackets, and emphasis may sit between the stop and the space.
_sentence_end_re = re.compile(r'[.!?]+["\'”’)\]*_»]*\s+')
_colon_re = re.compile(r':\s')
# The same closers as _sentence_end_re, plus a colon, which never splits
# a sentence but can end the last one in a paragraph.
_terminator_re = re.compile(r'([.!?:]+)["\'”’)\]*_»]*\s*$')
# A sentence-end match right after one of these is a false split: the
# period belongs to the abbreviation, not the sentence. Checked against
# the token immediately before the match rather than folded into
# _sentence_end_re, so the list can grow without a bigger lookbehind.
_ABBREVIATIONS = frozenset({'e.g.', 'i.e.', 'etc.', 'vs.', 'cf.'})
# "etc." is the one abbreviation in the set that routinely ends both a
# list and the sentence, so a capitalized word right after it is treated
# as a real new sentence. The others (e.g., i.e., vs., cf.) are
# mid-sentence connectives; a capital right after them ("e.g. It ...")
# is still the same sentence continuing, so they keep suppressing the
# split unconditionally.
_ETC = 'etc.'
# Quote, emphasis, bracket, and backtick characters that can open the
# next sentence without hiding its first real letter ("Foo", *Never*,
# `Foo`). Stripped before the etc. capitalization check, on the raw
# (unmasked) text: a backtick-wrapped opener is masked to filler in
# `masked`, which would otherwise hide the capital letter it wraps.
_ETC_OPENER_RE = re.compile(r'^[\'"“”‘’*_`\[({]+')
_TRAILING_TOKEN_RE = re.compile(r'\S+$')
# A token like "(e.g" (opening paren glued to the abbreviation) must not
# defeat the lookup: only the abbreviation itself is compared.
_LEADING_PUNCT_RE = re.compile(r'^[^\w]+')

DUPLICATE_MIN_WORDS = 8   # shorter repeats are usually labels or refrains
DUPLICATE_RATIO = 0.9     # difflib ratio at or above this counts as a repeat
# Below this word-set overlap, skip difflib entirely. This is a heuristic
# prefilter, not a lossless one: it trades a little recall for speed. A
# pure inflection difference ("runner"/"runners", "caches"/"cache" across
# a whole sentence) can still pull overlap down into the 0.6-0.75 range
# even at a 0.98 char ratio, so 0.5 is tuned to keep passing inflection
# and punctuation variants through, not to reject everything below the
# real duplicate threshold. It still cuts the O(n*m) ratio() call for the
# large majority of unrelated same-length pairs.
DUPLICATE_WORD_OVERLAP_GATE = 0.5
_number_re = re.compile(r'\d+(?:\.\d+)?')
# _word_re is [a-z]-only (it feeds antithesis's English stopword/negation
# logic and must stay that way). The overlap gate needs a tokenizer that
# actually covers the sentence: [^\W_] is any Unicode letter or digit, so
# a Cyrillic (or other non-Latin) sentence and a numbers-only sentence
# both produce a real, non-empty word set instead of silently falling
# back to English words alone.
_dup_word_re = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
# Duplicate detection reads a different view of the sentence than
# double-colon/antithesis: an HTML comment is someone else's aside, so it
# is dropped outright, but inline code is kept, with only the backticks
# stripped, because the identifier is often the claim itself (the same
# schema field name quoted twice is exactly the copy-paste this lane
# exists to catch).
_dup_comment_re = re.compile(r'<!--.*?-->')
_dup_code_re = re.compile(r'`([^`]*)`')

ANTITHESIS_MAX_WORDS = 25
# Shorter/longer word-count ratio. A lopsided pair is the repair pattern #5
# recommends, so it is not flagged.
ANTITHESIS_MIN_LEN_RATIO = 0.4
_word_re = re.compile(r"[a-z][a-z'’]*")
_NEG_SUFFIXES = ("n't", "n’t")
_NEGATIONS = frozenset({'not', 'no', 'never', 'cannot', 'nothing', 'none', 'nobody'})
# Personal pronouns only. A demonstrative ("This is the field...") usually
# points at an object, not back at the first sentence's subject.
_ANTITHESIS_PRONOUNS = frozenset({'it', 'they', 'he', 'she', 'we'})
_STOPWORDS = frozenset("""
    the and but for with from that this these those then than there here what which
    who whom whose why how when where are was were been being have has had does did
    doing can could will would shall should may might must its their theirs our ours
    your yours his her hers him them they she you into onto about over under just
    only also very more most some such each every any all one ones both either
    neither other same own
""".split()) | _NEGATIONS | _ANTITHESIS_PRONOUNS


def _paragraph_sentences(para: list[tuple[int, str]]) -> list[tuple[int, str, str, str]]:
    """Split a prose paragraph into (line, sentence, masked sentence, end).

    `end` is the punctuation run that closed the sentence ('.', '?', a
    paragraph-final ':'), or '' if it had none. A split sentence's own
    text excludes its terminator, so this is the one place that sees it.

    Each line is masked before the paragraph is joined, not after:
    masking the joined text would let a stray, unpaired backtick on one
    line pair with a stray backtick on a later line and hide everything
    between them as a fake code span. CommonMark code spans can cross
    lines; this scanner accepts that rarer miss (a real cross-line span
    stays unmasked past its own line) to avoid the far more common one.
    Masking preserves each line's length, so offsets into the joined
    string still land on the right source line.

    A sentence-end match right after a common abbreviation (see
    _ABBREVIATIONS) is not a real sentence boundary and is skipped, unless
    the abbreviation is "etc." and the next sentence is capitalized (see
    _ETC, _ETC_OPENER_RE). Leading punctuation glued to the abbreviation
    ("(e.g") is stripped before the lookup, so a parenthetical does not
    defeat it.
    """
    offsets, pos = [], 0
    for _, t in para:
        offsets.append(pos)
        pos += len(t) + 1
    joined = ' '.join(t for _, t in para)
    masked = ' '.join(_masked_re.sub(lambda m: _MASK_CHAR * len(m.group()), t)
                       for _, t in para)
    spans, start = [], 0
    for m in _sentence_end_re.finditer(masked):
        preceding = _TRAILING_TOKEN_RE.search(masked[:m.start()])
        token = (preceding.group() if preceding else '') + masked[m.start()]
        token = _LEADING_PUNCT_RE.sub('', token).lower()
        if token in _ABBREVIATIONS:
            starts_sentence = False
            if token == _ETC:
                # The raw text, not masked: a backtick-wrapped opener is
                # masked to filler, which would hide the capital letter
                # it wraps from this check.
                after = _ETC_OPENER_RE.sub('', joined[m.end():])
                starts_sentence = after[:1].isupper()
            if not starts_sentence:
                continue
        spans.append((start, m.start(), m.end()))
        start = m.end()
    spans.append((start, len(masked), len(masked)))
    out = []
    for a, b, e in spans:
        if not joined[a:b].strip():
            continue
        end = _terminator_re.search(masked[a:e])
        out.append((para[bisect.bisect_right(offsets, a) - 1][0], joined[a:b], masked[a:b],
                    end.group(1) if end else ''))
    return out


def _is_mirrored_antithesis(first: str, second: str) -> bool:
    """Two short sentences in near parallel, reversed by a single negation.

    Stands in for the ticket's rule (pronoun referring to the first subject,
    shared verb lemma) without an NLP dependency. Callers pass the masked
    sentence text: _word_re never matches _MASK_CHAR, so a masked
    inline-code or comment span contributes no words here and cannot
    manufacture a shared content word.
    """
    n1, n2 = len(first.split()), len(second.split())
    if not (3 <= n1 <= ANTITHESIS_MAX_WORDS and 3 <= n2 <= ANTITHESIS_MAX_WORDS):
        return False
    if min(n1, n2) / max(n1, n2) < ANTITHESIS_MIN_LEN_RATIO:
        return False
    w1, w2 = _word_re.findall(first.lower()), _word_re.findall(second.lower())
    if not w2 or w2[0] not in _ANTITHESIS_PRONOUNS:
        return False
    neg1 = any(w in _NEGATIONS or w.endswith(_NEG_SUFFIXES) for w in w1)
    neg2 = any(w in _NEGATIONS or w.endswith(_NEG_SUFFIXES) for w in w2)
    if neg1 == neg2:
        return False

    def content(words):
        return {w for w in words
                if len(w) >= 3 and w not in _STOPWORDS and not w.endswith(_NEG_SUFFIXES)}
    return bool(content(w1) & content(w2))


VERDICT_MAX_WORDS = 12   # a longer sentence usually carries its own evidence
_COPULAS = frozenset({'am', 'is', 'are', 'was', 'were', "isn't", "aren't", "wasn't", "weren't"})
# Contractions that are always a copula ("I'm", "they're").
_COPULA_CONTRACTIONS = ("'m", "'re")
# After a noun, "'s" is as often a possessive ("the cache's size") as a
# copula, so the contraction only counts after a pronoun or deictic.
_S_CONTRACTION_HOSTS = frozenset({'it', 'that', 'this', 'there', 'here', 'what', 'he', 'she'})
_DEICTIC_OPENERS = frozenset({'this', 'that', 'these', "that's", "there's", "here's", "it's"})
# A copula after one of these sits in a subordinate clause ("unless the
# file is large"), which qualifies the main clause instead of judging.
# "before", "after", and "since" are left out: as prepositions ("the cost
# before caching is high") they are too common to end the main clause.
_SUBORDINATORS = frozenset({'when', 'unless', 'if', 'because', 'while', 'although', 'until',
                            'once', 'whenever'})
# A spelled-out count is as concrete as a digit. "One" is left out: in
# "this one" and "the one catch" it points rather than counts.
_NUMBER_WORDS = frozenset('''
    two three four five six seven eight nine ten eleven twelve thirteen
    fourteen fifteen sixteen seventeen eighteen nineteen twenty hundred thousand
'''.split())
# Participles that judge rather than describe an action, so the -ing/-ed
# guard below must not drop them ("The docs are confusing").
_EVALUATIVE_PARTICIPLES = frozenset({
    'confusing', 'misleading', 'surprising', 'interesting', 'limiting', 'frustrating',
    'promising', 'overstated', 'understated', 'outdated', 'overloaded', 'complicated',
    'underspecified', 'misplaced', 'unfinished', 'unsupported'})
# Words ending in -er that precede "than" without comparing degree
# ("other than", "rather than").
_NOT_COMPARATIVES = frozenset({'under', 'other', 'rather', 'either', 'never', 'over', 'after',
                               'whether', 'together'})
# Adverbs that can sit between a copula and its adjective ("is really
# slow"); any other -ly word is treated the same way.
_COPULA_ADVERBS = frozenset({'very', 'quite', 'rather', 'really', 'so', 'too', 'still',
                             'also', 'just', 'often', 'always', 'pretty', 'fairly'})
# A word after a copula that opens a noun phrase, place, or clause, not an
# adjective. _STOPWORDS covers pronouns and most determiners already.
_NOT_ADJECTIVES = _STOPWORDS | frozenset({
    'a', 'an', 'in', 'on', 'at', 'of', 'to', 'by', 'as', 'off', 'out', 'up', 'down',
    'within', 'without', 'via', 'per', 'like', 'my', 'it', 'itself'})
_link_re = re.compile(r'\]\(|\]\[|://')
# A link target or bare URL: its words are an address, not the author's usage.
_link_target_re = re.compile(r'\]\([^)]*\)|\S+://\S+')
# Double quotes anywhere; a single quote only where it opens a word, so an
# apostrophe inside a contraction ("isn't") is not mistaken for a quote.
_quote_re = re.compile(r'["“”«»‘]|(?:^|\s)[\'’]')


def _is_action_participle(word: str) -> bool:
    """An -ing or -ed word after a copula that reads as a verb, not a judgment."""
    return word.endswith(('ing', 'ed')) and word not in _EVALUATIVE_PARTICIPLES


def _is_copula(word: str) -> bool:
    return (word in _COPULAS or word.endswith(_COPULA_CONTRACTIONS)
            or (word.endswith("'s") and word[:-2] in _S_CONTRACTION_HOSTS))


def _is_verdict_lead(sent: str, masked: str, end: str, doc_lower: frozenset[str]) -> bool:
    """A short, abstract, non-question sentence shaped like a judgment.

    Short: at most VERDICT_MAX_WORDS words outside inline code. Abstract:
    no digit or spelled-out number, code span, link, quotation, or
    capitalized word after the first (except "I"); names and figures make
    a sentence concrete. Case cannot tell "Rollbacks" from "Postgres" at
    sentence start, so a capitalized first word that is not "I" or a
    function word counts as a name unless the document's prose also uses
    it in lowercase (`doc_lower`).

    Verdict shape, any of: a deictic or existential opener ("This",
    "There's"); "the" plus one or two words plus a copula ("The catch
    is"), unless a progressive or passive verb follows ("The job is
    running"); or a copula followed by a negation, a comparative, or what
    looks like an adjective. Only a copula before the first subordinator
    counts. Where the sentence sits is the caller's check.
    """
    if '?' in end or '`' in sent:
        return False
    tokens = _dup_word_re.findall(masked)
    if not tokens or len(tokens) > VERDICT_MAX_WORDS:
        return False
    if any(ch.isdigit() for ch in masked) or _link_re.search(masked) or _quote_re.search(masked):
        return False
    if any(t[0].isupper() and re.split("['’]", t)[0] != 'I' for t in tokens[1:]):
        return False
    first = tokens[0].lower().replace('’', "'")
    if (tokens[0][0].isupper() and first not in doc_lower and first not in _DEICTIC_OPENERS
            and first.split("'")[0] not in _NOT_ADJECTIVES | {'i'}):
        return False
    words = [w.replace('’', "'") for w in _word_re.findall(masked.lower())]
    if not words or any(w in _NUMBER_WORDS for w in words):
        return False
    if words[0] in _DEICTIC_OPENERS or words[:2] in (['there', 'is'], ['there', 'are']):
        return True
    main = words[:next((k for k, w in enumerate(words) if w in _SUBORDINATORS), len(words))]
    if main[:1] == ['the']:
        for j in (2, 3):
            if j < len(main) and _is_copula(main[j]):
                if not main[j + 1:j + 2] or not _is_action_participle(main[j + 1]):
                    return True
                break
    i = next((k for k, w in enumerate(main) if _is_copula(w)), None)
    if i is None:
        return False
    if main[i].endswith("n't"):
        return True
    rest = main[i + 1:]
    if any(r in _NEGATIONS or r in ('more', 'less') for r in rest):
        return True
    if any(r.endswith('er') and r not in _NOT_COMPARATIVES and nxt == 'than'
           for r, nxt in zip(rest, rest[1:])):
        return True
    rest = [r for r in rest if r not in _COPULA_ADVERBS and not r.endswith('ly')]
    return bool(rest) and rest[0] not in _NOT_ADJECTIVES and not _is_action_participle(rest[0])


def _block_after(lines: list[str], line_no: int) -> str | None:
    """The block that follows 1-based line `line_no`, skipping blank lines.

    Returns 'code', 'fence', 'list', 'table', or 'quote' when the next
    non-blank raw line opens one of those blocks, else None. The caller
    passes a paragraph's last line, so a 4+ column indent after it can
    only open an indented code block. _content_lines drops code and
    _prose_paragraphs drops the rest, so this reads the raw lines.
    """
    for line in lines[line_no:]:
        if not line.strip():
            continue
        if _indent_width(line) >= 4:
            return 'code'
        if _fence_re.match(line):
            return 'fence'
        if _list_item_re.match(line):
            return 'list'
        if line.lstrip().startswith('|'):
            return 'table'
        if line.lstrip().startswith('>'):
            return 'quote'
        return None
    return None


ECHO_MIN_WORDS = 6      # fewer content words make a high overlap coincidental
ECHO_JACCARD = 0.6      # at or above this, two sentences share most of one claim
# Word-index prefilter. Sets of a and b stems reach ECHO_JACCARD only if
# they share at least 0.375 * (a + b) stems, so two 6+ stem sets need 5:
# the prefilter drops no match.
ECHO_MIN_SHARED = 5
# Adverb-shaped words that are not an adjective plus -ly.
_LY_NOT_ADVERBS = frozenset({'apply', 'early', 'only', 'family', 'supply', 'reply', 'rely', 'fly'})
_VOWELS = frozenset('aeiouy')
# A <summary> label opens a new disclosure section, like a heading, with
# or without its <details> tag on the same line.
_summary_line_re = re.compile(r'^\s*(?:<details[^>]*>\s*)?<summary\b', re.I)


def _stem(word: str) -> str:
    """Light suffix stripping so inflections of one word compare equal.

    Tries -ing, -ed, -es, -s, -ly in that order and strips the first that
    fits. -ing, -ed, and -es need a stem with a vowel ("string" stays
    whole); -ed skips -eed and -es skips -ees; -s skips -ss, -us, -is,
    and -ias ("class", "status", "bias") and needs 3 letters left; -ly
    needs 4 letters left and a word outside _LY_NOT_ADVERBS. After -ing
    or -ed, a doubled final consonant other than l, s, or z collapses
    ("running" to "run"). A final "e" is always dropped, so "use", "uses",
    "used", and "using" all become "us" instead of restoring the "e" on
    some of them. "ee" counts as part of the stem: a final "e" after
    another "e" stays, and a stem ending in "eed" loses its "d", so
    "agree", "agrees", "agreed" all become "agree" and "need", "needs",
    "needed" all become "nee".
    """
    w = word
    if w.endswith('ing') and _VOWELS & set(w[:-3]) and len(w) > 4:
        w = w[:-3]
        doubled = True
    elif w.endswith('ed') and not w.endswith('eed') and _VOWELS & set(w[:-2]) and len(w) > 3:
        w = w[:-2]
        doubled = True
    else:
        doubled = False
        if w.endswith('es') and not w.endswith('ees') and _VOWELS & set(w[:-2]) and len(w) > 3:
            w = w[:-2]
        elif w.endswith('s') and not w.endswith(('ss', 'us', 'is', 'ias')) and len(w) > 3:
            w = w[:-1]
        elif w.endswith('ly') and len(w) >= 6 and w not in _LY_NOT_ADVERBS:
            w = w[:-2]
    if doubled and len(w) > 3 and w[-1] == w[-2] and w[-1] not in _VOWELS | set('lsz'):
        w = w[:-1]
    if w.endswith('eed'):
        w = w[:-1]
    if w.endswith('e') and not w.endswith('ee') and _VOWELS & set(w[:-1]) and len(w) > 2:
        w = w[:-1]
    return w


def _echo_stems(masked: str) -> frozenset[str]:
    """Content-word stems of a masked sentence, for claim-echo matching.

    Any-script words (_dup_word_re), lowercased; _STOPWORDS and words
    under 3 letters are dropped, and the rest go through _stem.
    """
    stems = set()
    for w in _dup_word_re.findall(masked.lower()):
        w = w.replace('’', "'")
        if w.endswith("'s"):
            w = w[:-2]
        if len(w) < 3 or w in _STOPWORDS:
            continue
        stems.add(_stem(w))
    return frozenset(stems)


def _echo_of(stems: frozenset[str], section: int,
             earlier: list[tuple[int, int, frozenset[str]]],
             index: dict[str, list[int]]) -> int | None:
    """Line of the first earlier sentence in another section that `stems` echoes.

    `earlier` holds (line, section, stems) per sentence in document
    order; `index` maps a stem to the positions in `earlier` that contain
    it. Only sentences sharing ECHO_MIN_SHARED stems get a Jaccard test.
    """
    shared: dict[int, int] = {}
    for stem in stems:
        for j in index.get(stem, ()):
            shared[j] = shared.get(j, 0) + 1
    for j in sorted(j for j, n in shared.items() if n >= ECHO_MIN_SHARED):
        line, other_section, other = earlier[j]
        if other_section != section and shared[j] / len(stems | other) >= ECHO_JACCARD:
            return line
    return None


def scan_sentences(text: str) -> list[dict]:
    """Flag sentence-relation defects in prose.

    Tags: double-colon, duplicate-claim, mirrored-antithesis, verdict-lead
    (see _is_verdict_lead; it must open a paragraph, end in a colon, or
    precede a list, table, fence, or quote per _block_after), and
    claim-echo (see _echo_of; a sentence already flagged duplicate-claim
    is not also reported as an echo).

    Double-colon and antithesis detection read the fully masked sentence:
    comment or inline-code content must not create a match that isn't
    really there. Duplicate detection reads a different view (see
    _dup_comment_re/_dup_code_re): HTML comments are dropped, but inline
    code is kept as real content, because the code identifier is often
    the claim. A duplicate also requires identical number tokens, so two
    otherwise near-identical sentences that cite different measurements
    ("120 ms" vs. "180 ms") are not flagged. A word-overlap gate runs
    before any difflib comparison: same-length sentences built from
    unrelated words are common in real documents and defeat difflib's own
    cheap length-based bound, so without this gate every such pair still
    pays for a full ratio() call.
    """
    findings: list[dict] = []
    seen: list[tuple[int, str, list[str], frozenset[str]]] = []
    lines = text.lstrip('﻿').split('\n')
    paras = [(para, _paragraph_sentences(para)) for para in _prose_paragraphs(text)]
    # Lowercase words from masked prose only: a name written lowercase in
    # code or a URL ("docker run postgres") is not the author calling it
    # a common noun.
    doc_lower = frozenset(w for _, sents in paras for _, _, masked, _ in sents
                          for w in _dup_word_re.findall(_link_target_re.sub(' ', masked))
                          if w.islower())
    item_lines = _list_item_lines(text)
    section_starts = [i for i, ln in _content_lines(text)
                      if _heading_line_re.match(ln) or _summary_line_re.match(ln)]
    echo_sents: list[tuple[int, int, frozenset[str]]] = []
    echo_index: dict[str, list[int]] = {}
    for para, sents in paras:
        # A list item's wrapped, lazy, or loose continuation is prose to
        # the walker but list content to the reader. The two relational
        # tags below skip it, as they skip list items.
        list_continuation = para[0][0] in item_lines
        for idx, (line, sent, masked, end) in enumerate(sents):
            if len(_colon_re.findall(masked)) >= 2:
                findings.append({'line': line, 'text': sent.strip()[:80],
                                 'tag': 'double-colon', 'severity': 'HIGH'})
            if not list_continuation and _is_verdict_lead(sent, masked, end, doc_lower) and (
                    (idx == 0 and len(sents) > 1) or ':' in end
                    or (idx == len(sents) - 1 and _block_after(lines, para[-1][0]))):
                findings.append({'line': line, 'text': sent.strip()[:80],
                                 'tag': 'verdict-lead', 'severity': 'LOW'})
            dup_text = _dup_code_re.sub(r'\1', _dup_comment_re.sub('', sent))
            duplicated = False
            if len(dup_text.split()) >= DUPLICATE_MIN_WORDS:
                norm = ' '.join(dup_text.lower().split()).rstrip('.!?')
                nums = _number_re.findall(norm)
                # _dup_word_re, not .split(): a punctuation-attached token
                # ("configs," vs "configs") must not defeat the overlap gate.
                words = frozenset(_dup_word_re.findall(norm))
                for prev_line, prev_norm, prev_nums, prev_words in seen:
                    if words and prev_words:
                        overlap = len(words & prev_words) / max(len(words), len(prev_words))
                    else:
                        # A sentence can clear the 8-word floor with no
                        # [^\W_] token at all (pure punctuation/symbols) --
                        # vanishingly rare, but dividing by zero crashed the
                        # whole run for it. There is nothing cheap to compare,
                        # so the gate steps aside instead of guessing; difflib
                        # still makes the real call below.
                        overlap = 1.0
                    # Numbers are checked here, before any difflib call, not
                    # only in the final verdict: a big batch of otherwise
                    # identical sentences that differ only in their numbers
                    # has high overlap on every pair, so without this early
                    # exit every pair still pays for a full ratio() call.
                    if overlap < DUPLICATE_WORD_OVERLAP_GATE or nums != prev_nums:
                        continue
                    # The quick ratios are cheap upper bounds; ratio() is the real test.
                    sm = difflib.SequenceMatcher(None, prev_norm, norm)
                    if (sm.real_quick_ratio() >= DUPLICATE_RATIO
                            and sm.quick_ratio() >= DUPLICATE_RATIO
                            and sm.ratio() >= DUPLICATE_RATIO):
                        duplicated = True
                        findings.append({'line': line, 'text': f'repeats line {prev_line}',
                                         'tag': 'duplicate-claim', 'severity': 'MEDIUM'})
                        break
                seen.append((line, norm, nums, words))
            stems = _echo_stems(masked)
            if list_continuation or len(stems) < ECHO_MIN_WORDS:
                continue
            section = bisect.bisect_right(section_starts, line)
            if not duplicated:
                echoed = _echo_of(stems, section, echo_sents, echo_index)
                if echoed is not None:
                    findings.append({'line': line, 'text': f'echoes line {echoed}',
                                     'tag': 'claim-echo', 'severity': 'LOW'})
            for stem in stems:
                echo_index.setdefault(stem, []).append(len(echo_sents))
            echo_sents.append((line, section, stems))
        for (line, a, ma, _), (_, b, mb, _) in zip(sents, sents[1:]):
            if _is_mirrored_antithesis(ma, mb):
                findings.append({'line': line, 'text': f'{a.strip()} / {b.strip()}'[:80],
                                 'tag': 'mirrored-antithesis', 'severity': 'MEDIUM'})
    return findings


_VOICES_DIR = Path(__file__).resolve().parent.parent / 'reference' / 'voices'


def load_voice_thresholds(name: str) -> dict:
    """Read max_sentence_len, structured_density_max, and the
    sentence_length_sd range (as a (lo, hi) tuple, key sd_range) from a
    voice profile.

    Falls back to absolute defaults for a missing file or missing keys, so a
    voice without a Target Metrics block (e.g. code-design) is safe. An SD
    written as one number rather than a lo-hi range gives no sd_range.
    """
    out = {'max_sentence_len': DEFAULT_MAX_SENTENCE_LEN,
           'structured_density_max': None,
           'sd_range': None}
    path = _VOICES_DIR / f'{name}.md'
    if not path.exists():
        return out
    content = path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'max_sentence_len:\s*(\d+)', content)
    if m:
        out['max_sentence_len'] = int(m.group(1))
    m = re.search(r'structured_density_max:\s*([0-9]+(?:\.[0-9]+)?)', content)
    if m:
        out['structured_density_max'] = float(m.group(1))
    m = re.search(r'sentence_length_sd:[ \t]*([0-9]+(?:\.[0-9]+)?)[ \t]*-[ \t]*([0-9]+(?:\.[0-9]+)?)',
                  content)
    if m:
        out['sd_range'] = (float(m.group(1)), float(m.group(2)))
    return out


def _sd_verdict(sd: float, sd_range: tuple[float, float] | None) -> tuple[str, str]:
    """(label, target) for a sentence-length SD.

    With a voice range, below it is LOW and above it is HIGH: too little
    variation reads as machine rhythm, too much as a voice other than the
    one asked for. With no range, only the DEFAULT_MIN_SD floor applies.
    """
    if sd_range is None:
        return ('LOW' if sd < DEFAULT_MIN_SD else 'OK'), f'>= {DEFAULT_MIN_SD}'
    lo, hi = sd_range
    label = 'LOW' if sd < lo else 'HIGH' if sd > hi else 'OK'
    return label, f'{lo:g}-{hi:g}'


def compute_stats(text: str) -> dict:
    """Word count, sentence-length SD, bold density, max sentence length,
    structured-content density.

    Word count and bold density read the whole file. The sentence stats
    (SD, max length) read prose paragraphs only, split the same way the
    sentence lane splits them: a table row or a Mermaid edge is not a
    sentence, and counting one skews both numbers.
    """
    wc = len(text.split()) if text else 0
    lens = [n for para in _prose_paragraphs(text)
            for n in (len(s.split()) for _, s, _, _ in _paragraph_sentences(para))
            if n > 2]
    if len(lens) <= 1:
        sd = 0.0
    else:
        mean = sum(lens) / len(lens)
        var = sum((x - mean) ** 2 for x in lens) / len(lens)
        sd = round(math.sqrt(var), 1)
    bc = len(_bold_re.findall(text)) if text else 0
    bpk = round(bc / (wc / 1000), 1) if wc > 0 else 0.0
    max_len = max(lens) if lens else 0
    # Structured-content density: share of non-blank, non-fenced lines that are
    # headings, list items, or table rows.
    nonblank = 0
    structured = 0
    for _, line in _content_lines(text):
        if not line.strip():
            continue
        nonblank += 1
        if _structure_line_re.match(line):
            structured += 1
    density = round(structured / nonblank, 2) if nonblank else 0.0
    return {'words': wc, 'sd': sd, 'bold_per_1000w': bpk,
            'max_sentence_len': max_len, 'structured_density': density}


def format_human(filename: str, findings: list[dict], stats: dict,
                 sd_range: tuple[float, float] | None = None) -> str:
    """Grouped, labeled output for humans. sd_range: see _sd_verdict."""
    parts = [f'=== Humanize Pre-Scan: {filename} ===\n']
    vocab = sorted([f for f in findings if f['tag'] in VOCAB_TAGS], key=lambda f: f['line'])
    struct = sorted([f for f in findings if f['tag'] not in VOCAB_TAGS], key=lambda f: f['line'])
    if vocab:
        parts.append(f'\nVOCABULARY ({len(vocab)} findings)')
        for f in vocab:
            parts.append(f'  line {f["line"]}: "{f["text"]}" [{f["tag"]}]')
    if struct:
        parts.append(f'\nSTRUCTURAL ({len(struct)} findings)')
        for f in struct:
            parts.append(f'  line {f["line"]}: {f["text"]} [{f["tag"]}]')
    sd_label, sd_target = _sd_verdict(stats['sd'], sd_range)
    bold_label = "HIGH" if stats['bold_per_1000w'] >= 3 else "OK"
    parts.append('\nSTATS')
    parts.append(f'  words: {stats["words"]}')
    parts.append(f'  sentence-length SD: {stats["sd"]} ({sd_label}, target {sd_target})')
    parts.append(f'  bold density: {stats["bold_per_1000w"]} per 1000w ({bold_label}, target < 3)')
    parts.append(f'  max sentence length: {stats["max_sentence_len"]} words')
    parts.append(f'  structured density: {stats["structured_density"]}')
    parts.append('')
    return '\n'.join(parts)


def format_llm(filename: str, findings: list[dict], stats: dict,
               sd_range: tuple[float, float] | None = None) -> str:
    """Compact one-per-line output for LLM consumption. sd_range: see
    _sd_verdict."""
    sd_label, sd_target = _sd_verdict(stats['sd'], sd_range)
    lines = []
    for f in sorted(findings, key=lambda f: f['line']):
        lines.append(f'{filename}:{f["line"]}: "{f["text"]}" [{f["tag"]}]')
    lines.append(
        f'{filename}:STATS words={stats["words"]} sd={stats["sd"]} '
        f'bold_per_1000w={stats["bold_per_1000w"]} '
        f'max_sentence_len={stats["max_sentence_len"]} '
        f'structured_density={stats["structured_density"]} '
        f'sd_verdict={sd_label} sd_target={sd_target.replace(" ", "")}'
    )
    return '\n'.join(lines)


# -- File handling --

def is_binary(path: Path) -> bool:
    """True if first 8KB contains null bytes."""
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
        return b'\x00' in chunk
    except OSError:
        return False


def git_tracked_files(directory: Path) -> list[Path] | None:
    """Files git tracks in directory. None if not a git repo."""
    try:
        r = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            capture_output=True, text=True, cwd=directory, timeout=10,
        )
        if r.returncode != 0:
            return None
        return [directory / line for line in r.stdout.strip().split('\n') if line]
    except (OSError, subprocess.TimeoutExpired):
        return None


def detect_main_branch() -> str | None:
    for name in ('main', 'master'):
        r = subprocess.run(
            ['git', 'rev-parse', '--verify', name],
            capture_output=True, timeout=5,
        )
        if r.returncode == 0:
            return name
    return None


def diff_changed_lines(base: str) -> dict[str, set[int]] | None:
    """Changed line numbers per file from git diff base...HEAD."""
    try:
        r = subprocess.run(
            ['git', 'diff', '--unified=0', f'{base}...HEAD'],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
    except (OSError, subprocess.TimeoutExpired):
        return None

    result: dict[str, set[int]] = {}
    cur_file = None
    hunk_re = re.compile(r'^@@\s.*?\+(\d+)(?:,(\d+))?\s@@')

    for line in r.stdout.split('\n'):
        if line.startswith('+++ b/'):
            cur_file = line[6:]
        elif line.startswith('@@') and cur_file:
            m = hunk_re.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) else 1
                if count == 0:
                    continue  # pure deletion hunk
                if cur_file not in result:
                    result[cur_file] = set()
                result[cur_file].update(range(start, start + count))

    return result


def resolve_paths(paths: list[str]) -> list[Path]:
    """Expand directories, filter binaries, return file list."""
    out = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f'skip: {p} not found', file=sys.stderr)
            continue
        if path.is_file():
            if is_binary(path):
                print(f'skip: {p} (binary)', file=sys.stderr)
                continue
            out.append(path)
        elif path.is_dir():
            tracked = git_tracked_files(path)
            if tracked is not None:
                files = tracked
            else:
                files = list(path.rglob('*'))
            for f in sorted(files):
                if f.is_file() and not is_binary(f):
                    out.append(f)
    return out


def main():
    parser = argparse.ArgumentParser(description='Humanize pre-scan: detect AI patterns.')
    parser.add_argument('--mode', choices=['human', 'llm'], default='human',
                        help='output format (default: human)')
    parser.add_argument('--diff', nargs='?', const='AUTO', default=None,
                        help='scan only changed lines vs base branch')
    parser.add_argument('--voice', default=None,
                        help='apply a voice profile\'s readability thresholds')
    parser.add_argument('files', nargs='*', metavar='file',
                        help='files or directories to scan')
    args = parser.parse_args()

    thresholds = load_voice_thresholds(args.voice) if args.voice else {
        'max_sentence_len': DEFAULT_MAX_SENTENCE_LEN,
        'structured_density_max': None,
        'sd_range': None,
    }

    # Resolve diff line ranges if requested
    changed = None
    diff_files = None
    if args.diff is not None:
        base = args.diff
        if base == 'AUTO':
            base = detect_main_branch()
            if base is None:
                print('error: --diff could not detect main/master branch', file=sys.stderr)
                sys.exit(0)
        changed = diff_changed_lines(base)
        if changed is None:
            print(f'error: git diff against {base} failed', file=sys.stderr)
            sys.exit(0)
        diff_files = set(changed.keys())

    # Build file list
    if args.files:
        files = resolve_paths(args.files)
        # If diff active, intersect with diff file set
        if diff_files is not None:
            files = [f for f in files if _rel_path(f) in diff_files]
    elif diff_files is not None:
        # No file args but --diff: scan all diff files
        files = []
        for fp in sorted(diff_files):
            p = Path(fp)
            if p.exists() and p.is_file() and not is_binary(p):
                files.append(p)
    else:
        # No files and no --diff: scan the current directory (entire repo).
        files = resolve_paths(['.'])

    fmt = format_llm if args.mode == 'llm' else format_human
    total_findings = 0
    files_with_findings = 0

    for fpath in files:
        try:
            text = fpath.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            print(f'skip: {fpath} ({e})', file=sys.stderr)
            continue

        findings = scan_text(text, str(fpath))
        if fpath.suffix.lower() in PROSE_SUFFIXES:
            findings += scan_readability(text, max_sentence_len=thresholds['max_sentence_len'])
            findings += scan_sentences(text)
        stats = compute_stats(text)
        cap = thresholds['structured_density_max']
        if cap is not None and stats['structured_density'] > cap:
            findings.append({'line': 1, 'text':
                             f'structured density {stats["structured_density"]} > cap {cap}',
                             'tag': 'over-structured', 'severity': 'LOW'})

        # Filter to changed lines when in diff mode
        if changed is not None:
            rel = _rel_path(fpath)
            if rel in changed:
                lines_set = changed[rel]
                findings = [f for f in findings if f['line'] in lines_set]

        output = fmt(str(fpath), findings, stats, sd_range=thresholds['sd_range'])
        if output.strip():
            print(output)

        if findings:
            total_findings += len(findings)
            files_with_findings += 1

    if args.mode == 'human':
        print(f'---\nTotal: {total_findings} findings in {files_with_findings} file(s)')

    sys.exit(0)


def _rel_path(fpath: Path) -> str:
    """Best-effort relative path from cwd, matching git diff output."""
    try:
        return str(fpath.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(fpath)


if __name__ == '__main__':
    main()
