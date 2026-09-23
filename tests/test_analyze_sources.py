"""Unit tests for analyze-sources.py functions."""
from __future__ import annotations

from conftest import analyze_sources

strip_html = analyze_sources.strip_html
extract_vocabulary = analyze_sources.extract_vocabulary
extract_structural_signals = analyze_sources.extract_structural_signals
check_contamination = analyze_sources.check_contamination
load_current_watchlist = analyze_sources.load_current_watchlist
find_new_vocabulary_candidates = analyze_sources.find_new_vocabulary_candidates


# ---------------------------------------------------------------------------
# TestStripHtml
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_removes_script_tags(self):
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        result = strip_html(html)
        assert 'alert' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_preserves_text(self):
        html = '<div>Some <b>bold</b> text</div>'
        result = strip_html(html)
        assert 'Some' in result
        assert 'bold' in result
        assert 'text' in result

    def test_decodes_entities(self):
        html = '<p>Tom &amp; Jerry &lt;3</p>'
        result = strip_html(html)
        assert 'Tom & Jerry <3' in result

    def test_handles_unclosed_tags(self):
        html = '<p>Start<br>Middle<div>End'
        result = strip_html(html)
        assert 'Start' in result
        assert 'Middle' in result
        assert 'End' in result


# ---------------------------------------------------------------------------
# TestExtractVocabulary
# ---------------------------------------------------------------------------

class TestExtractVocabulary:
    def test_finds_tier1_words(self):
        text = 'This landscape is a tapestry of intricate patterns.'
        counts = extract_vocabulary(text)
        assert counts['landscape'] >= 1
        assert counts['tapestry'] >= 1
        assert counts['intricate'] >= 1

    def test_empty_text_returns_empty(self):
        counts = extract_vocabulary('')
        assert len(counts) == 0

    def test_case_insensitive(self):
        text = 'The LANDSCAPE is DELVE into PIVOTAL matters.'
        counts = extract_vocabulary(text)
        assert counts['landscape'] >= 1
        assert counts['delve'] >= 1
        assert counts['pivotal'] >= 1


# ---------------------------------------------------------------------------
# TestExtractStructuralSignals
# ---------------------------------------------------------------------------

class TestExtractStructuralSignals:
    def test_counts_formulaic_transitions(self):
        text = 'First point. Furthermore, second point. Moreover, third point.'
        signals = extract_structural_signals(text)
        assert signals['formulaic_transitions'] >= 2

    def test_detects_em_dashes(self):
        text = 'This is text \u2014 with an em dash. And another -- double dash.'
        signals = extract_structural_signals(text)
        assert signals['em_dash_per_500w'] > 0

    def test_rule_of_three(self):
        text = 'We need speed, quality, and reliability in our work.'
        signals = extract_structural_signals(text)
        assert signals['rule_of_three'] >= 1


# ---------------------------------------------------------------------------
# TestCheckContamination
# ---------------------------------------------------------------------------

class TestCheckContamination:
    def test_flags_ai_tooling_in_voice_sources(self):
        text = 'We used claude-api and chatgpt to build this.'
        issues = check_contamination(text, 'voice-profile')
        assert len(issues) > 0

    def test_ignores_non_voice_sources(self):
        text = 'We used claude-api and chatgpt to build this.'
        issues = check_contamination(text, 'blog-post')
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# TestLoadCurrentWatchlist
# ---------------------------------------------------------------------------

class TestLoadCurrentWatchlist:
    def test_returns_set_from_valid_file(self, tmp_path):
        watchlist = tmp_path / 'ai-vocabulary-watchlist.md'
        watchlist.write_text(
            '| Word | When to flag |\n'
            '|------|-------------|\n'
            '| delve | Always |\n'
            '| tapestry | Always |\n'
        )
        result = load_current_watchlist(tmp_path)
        assert isinstance(result, set)
        assert 'delve' in result
        assert 'tapestry' in result

    def test_returns_empty_set_for_missing_file(self, tmp_path):
        result = load_current_watchlist(tmp_path)
        assert result == set()
