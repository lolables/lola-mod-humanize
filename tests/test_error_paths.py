"""Error-path and edge-case tests for Humanize scripts."""
from __future__ import annotations

from conftest import analyze_sources, ollama_eval

strip_html = analyze_sources.strip_html
extract_vocabulary = analyze_sources.extract_vocabulary
find_new_vocabulary_candidates = analyze_sources.find_new_vocabulary_candidates
score_text = ollama_eval.score_text
ScoreCard = ollama_eval.ScoreCard


class TestStripHtmlEdgeCases:
    def test_malformed_html(self):
        result = strip_html('<<<>>><<<>broken<//p>>')
        assert isinstance(result, str)

    def test_empty_html(self):
        result = strip_html('')
        assert result == ''

    def test_only_tags(self):
        result = strip_html('<div><span></span></div>')
        assert result.strip() == ''

    def test_nested_scripts(self):
        html = '<script><script>inner</script></script>visible'
        result = strip_html(html)
        assert 'visible' in result


class TestExtractVocabularyEdgeCases:
    def test_empty_string(self):
        counts = extract_vocabulary('')
        assert len(counts) == 0

    def test_whitespace_only(self):
        counts = extract_vocabulary('   \n\t  ')
        assert len(counts) == 0

    def test_no_ai_words(self):
        counts = extract_vocabulary('The cat sat on the mat.')
        assert len(counts) == 0


class TestScoreCardZeroWordCount:
    def test_ai_density_zero(self):
        card = ScoreCard(model='t', sample='t', word_count=0, tier1_count=5)
        assert card.ai_density == 0

    def test_total_ai_words(self):
        card = ScoreCard(model='t', sample='t', word_count=0,
                         tier1_count=1, tier2_count=2, tier3_count=3)
        assert card.total_ai_words == 6

    def test_grade_with_zero_words(self):
        card = ScoreCard(model='t', sample='t', word_count=0)
        # Should not raise; low SD penalizes but should still produce a grade
        grade = card.grade
        assert grade in ('A', 'B', 'C', 'D', 'F', 'ERR')


class TestFindNewVocabularyCandidatesEdgeCases:
    def test_no_detection_keywords(self):
        text = 'The cat sat on the mat. It was warm and sunny.'
        result = find_new_vocabulary_candidates(text)
        assert result == []

    def test_empty_text(self):
        result = find_new_vocabulary_candidates('')
        assert result == []


class TestScoreTextEdgeCases:
    def test_empty_string(self):
        result = score_text('')
        assert result['word_count'] == 0
        assert result['tier1_found'] == []
        assert result['em_dash_count'] == 0

    def test_single_word(self):
        result = score_text('hello')
        assert result['word_count'] == 1
        assert result['sentence_length_sd'] == 0.0
