"""Consistency tests for the structure-fit reference content."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WRITING_DISCIPLINE = PROJECT_ROOT / 'reference' / 'writing-discipline.md'


class TestWritingDiscipline:
    def test_no_unconditional_prose_over_lists(self):
        text = WRITING_DISCIPLINE.read_text(encoding='utf-8')
        # The blanket rule must be gone; only the fit-based wording remains.
        assert '- Prose over lists.' not in text

    def test_fit_based_rule_present(self):
        text = WRITING_DISCIPLINE.read_text(encoding='utf-8')
        assert 'Prose over decorative lists' in text
        assert 'structure over walls of text' in text


STRUCTURAL_PATTERNS = PROJECT_ROOT / 'reference' / 'structural-patterns.md'


class TestStructuralPatterns:
    def test_wall_of_text_pattern_present(self):
        text = STRUCTURAL_PATTERNS.read_text(encoding='utf-8')
        assert '## 15. Wall of Text' in text

    def test_burstiness_has_ceiling(self):
        text = STRUCTURAL_PATTERNS.read_text(encoding='utf-8')
        # Pattern #1 must mention an upper bound, not only "vary".
        assert 'max_sentence_len' in text


VOICES_DIR = PROJECT_ROOT / 'reference' / 'voices'
METRIC_VOICES = ['general', 'blog', 'tutorial', 'rfc', 'code-comments',
                 'code-docs', 'release-notes', 'academic']


class TestVoiceStructurePolicy:
    def test_all_voices_have_structure_budget_line(self):
        for name in METRIC_VOICES + ['code-design']:
            text = (VOICES_DIR / f'{name}.md').read_text(encoding='utf-8')
            assert 'Match structure to content' in text, name

    def test_metric_voices_have_new_keys(self):
        for name in METRIC_VOICES:
            text = (VOICES_DIR / f'{name}.md').read_text(encoding='utf-8')
            assert 'max_sentence_len:' in text, name
            assert 'structured_density_max:' in text, name

    def test_code_design_has_no_metrics_block(self):
        text = (VOICES_DIR / 'code-design.md').read_text(encoding='utf-8')
        assert 'max_sentence_len:' not in text
