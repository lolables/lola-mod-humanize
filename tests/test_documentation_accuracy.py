"""
test_documentation_accuracy.py -- Verify that README and skills file claims
match the actual contents of the reference files.

Prevents documentation drift where counts change in reference files but
the claims in README/skills files are not updated.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README = PROJECT_ROOT / 'README.md'
SKILLS_FILE = PROJECT_ROOT / 'module' / 'skills' / 'humanize' / 'SKILL.md'
STRUCTURAL_PATTERNS = PROJECT_ROOT / 'reference' / 'structural-patterns.md'
CODE_PATTERNS = PROJECT_ROOT / 'reference' / 'code-patterns.md'
VOCABULARY_WATCHLIST = PROJECT_ROOT / 'reference' / 'ai-vocabulary-watchlist.md'
WRITING_DISCIPLINE = PROJECT_ROOT / 'reference' / 'writing-discipline.md'


# --- Helpers ---

def _count_vocabulary_entries() -> int:
    """Count table data rows in the vocabulary watchlist (excluding headers/separators)."""
    content = VOCABULARY_WATCHLIST.read_text()
    count = 0
    for line in content.splitlines():
        if not line.startswith('|'):
            continue
        # Skip separator rows and header rows
        cells = [c.strip() for c in line.split('|')]
        # cells[0] and cells[-1] are empty from leading/trailing |
        if len(cells) < 3:
            continue
        inner = cells[1]
        if '---' in inner:
            continue
        if inner in ('Word/Phrase', 'Phrase', 'Pattern'):
            continue
        second = cells[2] if len(cells) > 2 else ''
        if second in ('Replacement Strategy', 'When to Flag'):
            continue
        count += 1
    return count


def _count_structural_patterns() -> int:
    """Count ## N. headings in structural-patterns.md."""
    content = STRUCTURAL_PATTERNS.read_text()
    return len(re.findall(r'^## \d+\.', content, re.MULTILINE))


def _count_code_patterns() -> int:
    """Count ### N. headings in code-patterns.md."""
    content = CODE_PATTERNS.read_text()
    return len(re.findall(r'^### \d+\.', content, re.MULTILINE))


def _extract_readme_claim(pattern: str) -> str | None:
    """Extract a regex match from README."""
    content = README.read_text()
    m = re.search(pattern, content)
    return m.group(1) if m else None


def _count_checklist_items(heading: str) -> int:
    """Count '- [ ]' items under a heading in the skills file."""
    content = SKILLS_FILE.read_text()
    in_section = False
    count = 0
    for line in content.splitlines():
        if heading.lower() in line.lower() and line.startswith('#'):
            in_section = True
            continue
        if in_section and line.startswith('#'):
            break
        if in_section and line.startswith('- [ ]'):
            count += 1
    return count


# --- Tests ---

class TestVocabularyClaim:
    """README claims '~60 flagged words/phrases' -- verify within 20%."""

    def test_readme_vocabulary_count_within_tolerance(self):
        claimed = int(_extract_readme_claim(r'~(\d+) (?:known AI-characteristic |flagged )words'))
        actual = _count_vocabulary_entries()
        low = claimed * 0.8
        high = claimed * 1.2
        assert low <= actual <= high, (
            f'README claims ~{claimed} vocabulary entries, actual is {actual} '
            f'(tolerance: {low:.0f}-{high:.0f})'
        )

    def test_methodology_vocabulary_count_within_tolerance(self):
        methodology = (PROJECT_ROOT / 'docs' / 'METHODOLOGY.md').read_text()
        m = re.search(r'~(\d+) words and phrases', methodology)
        assert m, 'METHODOLOGY.md no longer states a vocabulary count'
        claimed = int(m.group(1))
        actual = _count_vocabulary_entries()
        assert claimed * 0.8 <= actual <= claimed * 1.2, (
            f'METHODOLOGY claims ~{claimed}, actual is {actual}'
        )


class TestWritingDisciplineSizeClaim:
    """writing-discipline.md advertises its own size so readers can budget context.

    The banned-word region is regenerated from the watchlist by `task vocab:sync`,
    so the block grows whenever vocabulary is added and the claim silently rots.
    """

    def test_line_count_claim_within_tolerance(self):
        content = WRITING_DISCIPLINE.read_text()
        m = re.search(r'~(\d+) lines', content)
        assert m, 'writing-discipline.md no longer states a line count'
        claimed = int(m.group(1))

        # The copy-pasteable block is everything after the `----` separator that
        # closes the preamble. That is what a reader actually pastes.
        lines = content.splitlines()
        sep = next(i for i, line in enumerate(lines) if line.strip() == '----')
        actual = len(lines[sep + 1:])

        assert claimed * 0.8 <= actual <= claimed * 1.2, (
            f'writing-discipline.md claims ~{claimed} lines, block is {actual}. '
            f'Re-measure the line and token counts on line 8 after `task vocab:sync`.'
        )


class TestStructuralPatternClaim:
    """README claims '14 text patterns' -- verify against structural-patterns.md."""

    def test_readme_structural_pattern_count(self):
        claimed = int(_extract_readme_claim(r'(\d+) text patterns'))
        actual = _count_structural_patterns()
        assert claimed == actual, (
            f'README claims {claimed} text patterns, '
            f'structural-patterns.md has {actual}'
        )

    def test_structural_pattern_numbering_contiguous(self):
        """Pattern numbering should have no gaps (1, 2, 3, ..., N)."""
        content = STRUCTURAL_PATTERNS.read_text()
        numbers = [
            int(m.group(1))
            for m in re.finditer(r'^## (\d+)\.', content, re.MULTILINE)
        ]
        expected = list(range(1, len(numbers) + 1))
        assert numbers == expected, (
            f'Pattern numbering has gaps: {numbers} (expected {expected})'
        )


class TestCodePatternClaim:
    """README claims '8 code patterns' -- verify against code-patterns.md."""

    def test_readme_code_pattern_count(self):
        claimed = int(_extract_readme_claim(r'(\d+) code patterns'))
        actual = _count_code_patterns()
        assert claimed == actual, (
            f'README claims {claimed} code patterns, '
            f'code-patterns.md has {actual}'
        )


class TestSkillsChecklist:
    """Skills file checklist counts match reference file counts."""

    def test_text_checklist_matches_readme(self):
        claimed = int(_extract_readme_claim(r'(\d+)-point text checklist'))
        actual = _count_checklist_items('Text verification')
        assert claimed == actual, (
            f'README claims {claimed}-point text checklist, '
            f'SKILL.md has {actual} items'
        )

    def test_code_checklist_matches_readme(self):
        claimed = int(_extract_readme_claim(r'(\d+)-point code checklist'))
        actual = _count_checklist_items('Code verification')
        assert claimed == actual, (
            f'README claims {claimed}-point code checklist, '
            f'SKILL.md has {actual} items'
        )

    def test_skills_structural_pattern_count_matches(self):
        """The skills file enumeration should match structural-patterns.md."""
        content = SKILLS_FILE.read_text()
        # Count numbered items in the pattern enumeration within Pass 2
        # These are lines like "1. Low burstiness..." under the structural check
        in_text_patterns = False
        pattern_count = 0
        for line in content.splitlines():
            if 'check all' in line and 'patterns from' in line:
                in_text_patterns = True
                continue
            if in_text_patterns:
                if re.match(r'^\d+\.\s', line.strip()):
                    pattern_count += 1
                elif line.strip() and not re.match(r'^\d+\.\s', line.strip()):
                    break
        actual = _count_structural_patterns()
        assert pattern_count == actual, (
            f'SKILL.md enumerates {pattern_count} text patterns, '
            f'structural-patterns.md has {actual}'
        )
