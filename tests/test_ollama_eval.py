"""Unit tests for ollama-eval.py functions."""
from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

from conftest import ollama_eval

score_text = ollama_eval.score_text
ScoreCard = ollama_eval.ScoreCard
ollama_url = ollama_eval.ollama_url
ollama_generate = ollama_eval.ollama_generate
ollama_unload = ollama_eval.ollama_unload
ollama_list_models = ollama_eval.ollama_list_models
build_transform_prompt = ollama_eval.build_transform_prompt
build_humanize_system_prompt = ollama_eval.build_humanize_system_prompt
evaluate_sample = ollama_eval.evaluate_sample


# ---------------------------------------------------------------------------
# TestScoreText
# ---------------------------------------------------------------------------

class TestScoreText:
    def test_clean_text_scores_zero_tier1(self):
        text = (
            'The quick brown fox jumped over the lazy dog. '
            'It was a normal day with nothing special happening. '
            'Rain fell on the old tin roof. '
            'She packed her bag and left for the station.'
        )
        result = score_text(text)
        assert result['tier1_found'] == []

    def test_ai_heavy_text_flags_words(self):
        text = (
            'Let us delve into this vibrant tapestry of intricate patterns. '
            'The pivotal landscape underscores the meticulous interplay.'
        )
        result = score_text(text)
        assert len(result['tier1_found']) > 0
        found_words = set(result['tier1_found'])
        assert 'delve' in found_words

    def test_counts_em_dashes(self):
        text = 'First part \u2014 second part \u2014 third part.'
        result = score_text(text)
        assert result['em_dash_count'] == 2

    def test_measures_sentence_sd(self):
        # Sentences of very different lengths should produce nonzero SD
        text = (
            'Short. '
            'A somewhat longer sentence with more words in it for variety. '
            'Tiny. '
            'Another medium length sentence here for testing purposes only.'
        )
        result = score_text(text)
        # SD should be > 0 for varied sentence lengths
        assert result['sentence_length_sd'] >= 0


# ---------------------------------------------------------------------------
# TestScoreCardProperties
# ---------------------------------------------------------------------------

class TestScoreCardProperties:
    def test_ai_density_calculation(self):
        card = ScoreCard(model='test', sample='test',
                         tier1_count=5, tier2_count=3, tier3_count=2,
                         word_count=500)
        # total_ai_words = 10, density = (10/500)*500 = 10.0
        assert card.ai_density == 10.0

    def test_zero_word_count_no_division_error(self):
        card = ScoreCard(model='test', sample='test',
                         tier1_count=1, word_count=0)
        assert card.ai_density == 0


# ---------------------------------------------------------------------------
# TestScoreCardPassed
# ---------------------------------------------------------------------------

class TestScoreCardPassed:
    def _make_passing_card(self, **overrides):
        """Create a card that passes by default, then apply overrides."""
        defaults = dict(
            model='test', sample='test',
            tier1_count=0, tier2_count=0, tier3_count=0,
            banned_phrase_count=0, transition_count=0,
            em_dash_count=0, sentence_length_sd=8.0,
            sentence_count=10,
            word_count=500, error='',
        )
        defaults.update(overrides)
        return ScoreCard(**defaults)

    def test_all_clean_passes(self):
        card = self._make_passing_card()
        assert card.passed is True

    def test_tier1_count_0_passes(self):
        card = self._make_passing_card(tier1_count=0)
        assert card.passed is True

    def test_tier1_count_1_fails(self):
        card = self._make_passing_card(tier1_count=1)
        assert card.passed is False

    def test_density_at_exactly_2_passes(self):
        # density = (total_ai_words / word_count) * 500
        # For density=2.0 with word_count=500: total=2
        card = self._make_passing_card(tier2_count=2, word_count=500)
        assert card.ai_density == 2.0
        assert card.passed is True

    def test_density_above_2_fails(self):
        # density = (3/500)*500 = 3.0
        card = self._make_passing_card(tier2_count=3, word_count=500)
        assert card.ai_density == 3.0
        assert card.passed is False

    def test_sd_at_exactly_5_passes(self):
        card = self._make_passing_card(sentence_length_sd=5.0)
        assert card.passed is True

    def test_sd_below_5_fails(self):
        card = self._make_passing_card(sentence_length_sd=4.9)
        assert card.passed is False

    def test_few_sentences_not_failed_for_low_sd(self):
        # Code / short-form content with too few prose sentences to measure
        # burstiness must not fail on SD.
        card = self._make_passing_card(sentence_length_sd=0.0)
        card.sentence_count = 1
        assert card.passed is True

    def test_multi_sentence_low_sd_still_fails(self):
        # Genuine prose with enough sentences but uniform length still fails.
        card = self._make_passing_card(sentence_length_sd=0.0)
        card.sentence_count = 8
        assert card.passed is False

    def test_grade_no_sd_penalty_when_few_sentences(self):
        card = self._make_passing_card(sentence_length_sd=0.0)
        card.sentence_count = 1
        assert card.grade == 'A'  # no -15 SD penalty applied

    def test_score_text_reports_sentence_count(self):
        # score_text must report how many prose sentences it found.
        findings = score_text(
            "Short. Two words only here now. A third sentence appears. "
            "And a fourth one. Plus a fifth sentence here."
        )
        assert findings['sentence_count'] >= 3

    def test_em_dash_0_passes(self):
        card = self._make_passing_card(em_dash_count=0)
        assert card.passed is True

    def test_em_dash_1_fails(self):
        card = self._make_passing_card(em_dash_count=1)
        assert card.passed is False

    def test_error_fails(self):
        card = self._make_passing_card(error='connection refused')
        assert card.passed is False


# ---------------------------------------------------------------------------
# TestScoreCardGrade
# ---------------------------------------------------------------------------

class TestScoreCardGrade:
    def test_grade_a_at_90_plus(self):
        card = ScoreCard(model='t', sample='t', sentence_length_sd=10.0,
                         word_count=500)
        assert card.grade == 'A'

    def test_grade_b_at_75_to_89(self):
        # tier2_count=2 => -16, score=84
        card = ScoreCard(model='t', sample='t', tier2_count=2,
                         sentence_length_sd=10.0, word_count=500)
        assert card.grade == 'B'

    def test_grade_c_at_60_to_74(self):
        # tier1_count=2 => -30, tier2_count=1 => -8, score=62
        card = ScoreCard(model='t', sample='t', tier1_count=2, tier2_count=1,
                         sentence_length_sd=10.0, word_count=500)
        assert card.grade == 'C'

    def test_grade_d_at_40_to_59(self):
        # tier1_count=3 => -45, score=55; minus low SD if needed
        card = ScoreCard(model='t', sample='t', tier1_count=3,
                         sentence_length_sd=10.0, word_count=500)
        assert card.grade == 'D'

    def test_grade_f_below_40(self):
        # tier1_count=4 => -60, banned=1 => -10, score=30
        card = ScoreCard(model='t', sample='t', tier1_count=4,
                         banned_phrase_count=1,
                         sentence_length_sd=10.0, word_count=500)
        assert card.grade == 'F'

    def test_grade_err_on_error(self):
        card = ScoreCard(model='t', sample='t', error='timeout')
        assert card.grade == 'ERR'


# ---------------------------------------------------------------------------
# TestOllamaUrl
# ---------------------------------------------------------------------------

class TestOllamaUrl:
    def test_formats_url(self):
        assert ollama_url('localhost', 11434, '/api/generate') == \
            'http://localhost:11434/api/generate'

    def test_custom_host_port(self):
        assert ollama_url('gpu-box', 9999, '/api/tags') == \
            'http://gpu-box:9999/api/tags'


# ---------------------------------------------------------------------------
# TestBuildTransformPrompt
# ---------------------------------------------------------------------------

class TestBuildTransformPrompt:
    def test_contains_sample_text(self):
        result = build_transform_prompt('Hello world sample')
        assert 'Hello world sample' in result

    def test_contains_transform_instruction(self):
        result = build_transform_prompt('anything')
        assert 'Transform' in result

    def test_no_leading_whitespace(self):
        result = build_transform_prompt('test')
        assert not result.startswith(' ')
        assert not result.startswith('\n')


# ---------------------------------------------------------------------------
# TestBuildHumanizeSystemPrompt
# ---------------------------------------------------------------------------

class TestBuildHumanizeSystemPrompt:
    def test_returns_nonempty(self):
        result = build_humanize_system_prompt()
        assert len(result) > 0

    def test_contains_skill_content(self):
        result = build_humanize_system_prompt()
        # The skill file should mention Humanize or vocabulary or passes
        assert 'humanize' in result.lower() or 'vocabulary' in result.lower()


# ---------------------------------------------------------------------------
# TestOllamaGenerate
# ---------------------------------------------------------------------------

class TestOllamaGenerate:
    def _mock_response(self, body: dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch('urllib.request.urlopen')
    def test_success_returns_text_and_elapsed(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response(
            {'response': 'transformed text'}
        )
        text, elapsed = ollama_generate('localhost', 11434, 'test-model', 'hi')
        assert text == 'transformed text'
        assert elapsed >= 0

    @patch('urllib.request.urlopen')
    def test_missing_response_key_returns_empty(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({})
        text, elapsed = ollama_generate('localhost', 11434, 'test-model', 'hi')
        assert text == ''

    @patch('urllib.request.urlopen')
    def test_url_error_returns_error_string(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError('connection refused')
        text, elapsed = ollama_generate('localhost', 11434, 'test-model', 'hi')
        assert text.startswith('ERROR:')
        assert elapsed >= 0

    @patch('urllib.request.urlopen')
    def test_timeout_returns_error_string(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError('timed out')
        text, elapsed = ollama_generate('localhost', 11434, 'test-model', 'hi')
        assert text.startswith('ERROR:')


# ---------------------------------------------------------------------------
# TestOllamaListModels
# ---------------------------------------------------------------------------

class TestOllamaListModels:
    def _mock_response(self, body: dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch('urllib.request.urlopen')
    def test_success_returns_model_names(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({
            'models': [
                {'name': 'llama3.2:latest'},
                {'name': 'mistral:latest'},
            ]
        })
        result = ollama_list_models('localhost', 11434)
        assert result == ['llama3.2:latest', 'mistral:latest']

    @patch('urllib.request.urlopen')
    def test_empty_models_returns_empty(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({'models': []})
        result = ollama_list_models('localhost', 11434)
        assert result == []

    @patch('urllib.request.urlopen')
    def test_error_returns_empty_list(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError('refused')
        result = ollama_list_models('localhost', 11434)
        assert result == []


# ---------------------------------------------------------------------------
# TestOllamaUnload
# ---------------------------------------------------------------------------

class TestOllamaUnload:
    def _mock_response(self):
        resp = MagicMock()
        resp.read.return_value = b'{}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch('urllib.request.urlopen')
    def test_success_no_exception(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response()
        ollama_unload('localhost', 11434, 'test-model')  # should not raise

    @patch('urllib.request.urlopen')
    def test_error_swallowed(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError('refused')
        ollama_unload('localhost', 11434, 'test-model')  # should not raise


# ---------------------------------------------------------------------------
# TestEvaluateSample
# ---------------------------------------------------------------------------

class TestEvaluateSample:
    @patch.object(ollama_eval, 'ollama_generate')
    def test_success_populates_scorecard(self, mock_gen):
        clean_text = (
            'The rain fell on the old tin roof. '
            'She packed her bag and left for the station. '
            'A cold wind blew through the open window. '
            'He sat down and wrote a short letter to his friend.'
        )
        mock_gen.return_value = (clean_text, 2.5)
        card = evaluate_sample(
            'localhost', 11434, 'test-model', '01-test',
            'some ai text', 'system prompt',
        )
        assert card.model == 'test-model'
        assert card.sample == '01-test'
        assert card.generation_time_s == 2.5
        assert card.word_count > 0
        assert card.error == ''
        assert card.raw_output == clean_text

    @patch.object(ollama_eval, 'ollama_generate')
    def test_error_response_sets_error_field(self, mock_gen):
        mock_gen.return_value = ('ERROR: connection refused', 0.1)
        card = evaluate_sample(
            'localhost', 11434, 'test-model', '01-test',
            'input', 'system',
        )
        assert card.error == 'ERROR: connection refused'
        assert card.raw_output == ''

    @patch.object(ollama_eval, 'ollama_generate')
    def test_ai_heavy_output_scores_findings(self, mock_gen):
        ai_text = (
            'Let us delve into this vibrant tapestry of intricate patterns. '
            'The pivotal landscape underscores the meticulous interplay. '
            'This is a short filler sentence for word count padding. '
            'Another sentence here to keep things going for the scoring.'
        )
        mock_gen.return_value = (ai_text, 1.0)
        card = evaluate_sample(
            'localhost', 11434, 'test-model', '02-ai',
            'input', 'system',
        )
        assert card.tier1_count > 0
        assert 'delve' in card.tier1_found


# ---------------------------------------------------------------------------
# TestWriteReportDensityFailure
# ---------------------------------------------------------------------------

class TestWriteReportDensityFailure:
    """write_report must surface AI-density as a failure reason.

    A card with zero Tier-1 words but ai_density > 2.0 fails the `passed`
    gate, yet the old code emitted an empty failure line because it only
    checked tier1_found, phrases, transitions, em-dashes, and SD.
    """

    def _make_density_only_failing_card(self):
        """Return a ScoreCard that fails solely on ai_density."""
        # 4 tier3 words in 200-word text → density = (4/200)*500 = 10.0
        return ScoreCard(
            model='test-model',
            sample='02-readme',
            tier1_count=0,
            tier2_count=0,
            tier3_count=4,
            tier3_found=['landscape', 'intricate', 'interplay', 'intricacies'],
            word_count=200,
            sentence_length_sd=12.0,
            sentence_count=10,
            banned_phrase_count=0,
            transition_count=0,
            em_dash_count=0,
            error='',
        )

    def _get_failure_pattern_line(self, report: str, sample: str) -> str | None:
        """Return the indented failure-pattern line for a sample, or None."""
        # The failure-pattern lines are indented with two spaces: '  - <sample>: ...'
        # The summary table rows start with '|', so filtering by leading spaces
        # correctly isolates the per-model failure list.
        for ln in report.splitlines():
            if ln.startswith('  - ') and sample in ln:
                return ln
        return None

    def test_density_only_failure_line_is_nonempty(self, tmp_path):
        """Failure line for a density-only fail must not be blank."""
        card = self._make_density_only_failing_card()
        assert card.passed is False, 'card must fail for this test to be meaningful'
        assert card.tier1_count == 0, 'tier1 must be zero so density is the sole driver'

        write_report = ollama_eval.write_report
        write_report([card], tmp_path)

        report = (tmp_path / 'eval-report.md').read_text()
        failure_line = self._get_failure_pattern_line(report, '02-readme')
        assert failure_line is not None, 'failure-pattern line not found in report'
        # The portion after the sample label must not be empty
        after_label = failure_line.split('02-readme:', 1)[-1].strip()
        assert after_label, (
            f'failure line for density-only fail was empty: {failure_line!r}'
        )

    def test_density_failure_line_mentions_density_and_words(self, tmp_path):
        """Failure line must mention 'AI density' and at least one tier3 word."""
        card = self._make_density_only_failing_card()
        write_report = ollama_eval.write_report
        write_report([card], tmp_path)

        report = (tmp_path / 'eval-report.md').read_text()
        failure_line = self._get_failure_pattern_line(report, '02-readme')
        assert failure_line is not None, 'failure-pattern line not found in report'
        assert 'AI density' in failure_line, (
            f'expected "AI density" in failure line: {failure_line!r}'
        )
        tier3_words = {'landscape', 'intricate', 'interplay', 'intricacies'}
        assert any(w in failure_line for w in tier3_words), (
            f'expected at least one tier3 word in failure line: {failure_line!r}'
        )
