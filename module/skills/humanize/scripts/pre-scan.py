"""pre-scan.py -- Mechanical scanner for AI-detectable patterns.

Reports vocabulary hits, banned phrases, and formulaic transitions
with line numbers. No rewrites, just findings.
"""
from __future__ import annotations
import re
import math
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
_ascii_dash_re = re.compile(r'\w\s--\s\w')
_inline_header_re = re.compile(r'\*\*[^*]+:\*\*|\*\*[^*]+\*\*\s*:')
_bold_re = re.compile(r'\*\*[^*]+\*\*')
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
        # Check 6: Em dash
        for m in _em_dash_re.finditer(line):
            findings.append({'line': i, 'text': m.group(), 'tag': 'em-dash', 'severity': 'HIGH'})
        # Check 7: En dash (skip number ranges like 1–5)
        for m in _en_dash_re.finditer(line):
            s = m.start()
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


_sentence_split_re = re.compile(r'[.!?]+\s+')

VOCAB_TAGS = {'tier1', 'tier2', 'tier3', 'banned-phrase', 'transition'}

# --- Readability lane (structure-fit spec, Part D) ---
# Absolute, voice-agnostic defaults. --voice refines max_sentence_len.
DEFAULT_MAX_SENTENCE_LEN = 45    # words; longer flags a run-on
# 6, not 4: list commas ("metrics, logs, and traces") and coordinating
# conjunctions inflate the raw count, so a well-structured list-bearing
# sentence reads as ~6 boundaries. 6 still catches genuinely over-nested prose.
DEFAULT_MAX_CLAUSE_DEPTH = 6     # clause boundaries; more flags over-nesting
DEFAULT_MAX_PARA_SENTENCES = 6   # prose sentences per paragraph before wall-of-text

# The readability lane is a prose concern. In code, commas and keywords
# (and/or/if/while) are syntax, not clauses, so running it on source files
# produces false positives. Restrict the lane to prose file types.
PROSE_SUFFIXES = {'.md', '.markdown', '.txt', '.rst', '.adoc', '.org', '.text'}

# Clause boundaries: commas, semicolons, and a closed set of conjunctions.
_clause_marker_re = re.compile(
    r',|;|\b(?:and|but|or|which|that|because|although|though|while|whereas|since|unless)\b',
    re.I,
)
# A structural (non-prose) line: heading, list item, table row, or fence.
_structure_line_re = re.compile(r'^\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|\||```|~~~)')


def _clause_depth(sentence: str) -> int:
    return len(_clause_marker_re.findall(sentence))


def scan_readability(text: str,
                     max_sentence_len: int = DEFAULT_MAX_SENTENCE_LEN,
                     max_clause_depth: int = DEFAULT_MAX_CLAUSE_DEPTH,
                     max_para_sentences: int = DEFAULT_MAX_PARA_SENTENCES) -> list[dict]:
    """Flag long/over-nested sentences and wall-of-text paragraphs.

    Symptoms only; never rewrites. Skips fenced code blocks and structural
    lines so prose density is measured against prose, not markup.
    """
    findings: list[dict] = []
    if not text:
        return findings
    in_fence = False
    buf: list[str] = []
    start_line = 0

    def flush():
        nonlocal buf, start_line
        if not buf:
            return
        para = ' '.join(buf).strip()
        buf = []
        if not para:
            return
        sents = [s for s in _sentence_split_re.split(para) if len(s.split()) > 2]
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

    for i, line in enumerate(text.split('\n'), 1):
        if line.lstrip().startswith(('```', '~~~')):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip() or _structure_line_re.match(line):
            flush()
            continue
        if not buf:
            start_line = i
        buf.append(line.strip())
    flush()
    return findings


_VOICES_DIR = Path(__file__).resolve().parent.parent / 'reference' / 'voices'


def load_voice_thresholds(name: str) -> dict:
    """Read max_sentence_len / structured_density_max from a voice profile.

    Falls back to absolute defaults for a missing file or missing keys, so a
    voice without a Target Metrics block (e.g. code-design) is safe.
    """
    out = {'max_sentence_len': DEFAULT_MAX_SENTENCE_LEN,
           'structured_density_max': None}
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
    return out


def _prose_lines(text: str) -> list[str]:
    """Lines that are prose: not fenced code, not headings/lists/tables."""
    out = []
    in_fence = False
    for line in text.split('\n'):
        if line.lstrip().startswith(('```', '~~~')):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip() or _structure_line_re.match(line):
            continue
        out.append(line)
    return out


def compute_stats(text: str) -> dict:
    """Word count, sentence-length SD, bold density, max sentence length,
    structured-content density."""
    wc = len(text.split()) if text else 0
    if text:
        sents = [s.split() for s in _sentence_split_re.split(text)]
        lens = [len(s) for s in sents if len(s) > 2]
    else:
        lens = []
    if len(lens) <= 1:
        sd = 0.0
    else:
        mean = sum(lens) / len(lens)
        var = sum((x - mean) ** 2 for x in lens) / len(lens)
        sd = round(math.sqrt(var), 1)
    bc = len(_bold_re.findall(text)) if text else 0
    bpk = round(bc / (wc / 1000), 1) if wc > 0 else 0.0
    prose = ' '.join(_prose_lines(text))
    plens = [len(s.split()) for s in _sentence_split_re.split(prose) if len(s.split()) > 2]
    max_len = max(plens) if plens else 0
    # Structured-content density: share of non-blank, non-fenced lines that are
    # headings, list items, or table rows.
    nonblank = 0
    structured = 0
    in_fence = False
    for line in text.split('\n'):
        if line.lstrip().startswith(('```', '~~~')):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue
        nonblank += 1
        if _structure_line_re.match(line):
            structured += 1
    density = round(structured / nonblank, 2) if nonblank else 0.0
    return {'words': wc, 'sd': sd, 'bold_per_1000w': bpk,
            'max_sentence_len': max_len, 'structured_density': density}


def format_human(filename: str, findings: list[dict], stats: dict) -> str:
    """Grouped, labeled output for humans."""
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
    sd_label = "LOW" if stats['sd'] < 8 else "OK"
    bold_label = "HIGH" if stats['bold_per_1000w'] >= 3 else "OK"
    parts.append('\nSTATS')
    parts.append(f'  words: {stats["words"]}')
    parts.append(f'  sentence-length SD: {stats["sd"]} ({sd_label}, target >= 8)')
    parts.append(f'  bold density: {stats["bold_per_1000w"]} per 1000w ({bold_label}, target < 3)')
    parts.append(f'  max sentence length: {stats["max_sentence_len"]} words')
    parts.append(f'  structured density: {stats["structured_density"]}')
    parts.append('')
    return '\n'.join(parts)


def format_llm(filename: str, findings: list[dict], stats: dict) -> str:
    """Compact one-per-line output for LLM consumption."""
    lines = []
    for f in sorted(findings, key=lambda f: f['line']):
        lines.append(f'{filename}:{f["line"]}: "{f["text"]}" [{f["tag"]}]')
    lines.append(
        f'{filename}:STATS words={stats["words"]} sd={stats["sd"]} '
        f'bold_per_1000w={stats["bold_per_1000w"]} '
        f'max_sentence_len={stats["max_sentence_len"]} '
        f'structured_density={stats["structured_density"]}'
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

        output = fmt(str(fpath), findings, stats)
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
