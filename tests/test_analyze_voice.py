"""Tests for analyze-voice.py voice analysis functions."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'analyze-voice.py'

# Import the module for unit testing
import importlib.util
import sys

_spec = importlib.util.spec_from_file_location('analyze_voice', SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules['analyze_voice'] = _mod
_spec.loader.exec_module(_mod)

from analyze_voice import (
    split_sentences, sentence_stats, count_parentheticals, count_first_person,
    count_contractions, classify_register, extract_prose, vocabulary_register,
    detect_humor_signals, generate_profile, detect_formatting_patterns,
    strip_html_tags, load_sources, count_exclamations, main,
)


SAMPLE_CASUAL = """\
I finally gave up on the manual approach and let the CI handle it. This is bad.
You'll need to configure the auth provider first (granted, it's not obvious how).
Being from the 1900's, I went down the traditional troubleshooting route. Sigh.
The system doesn't care about your feelings. It works or it doesn't.
"""

SAMPLE_FORMAL = """\
The authentication subsystem was designed to accommodate multiple identity
providers through a standardized protocol interface. Configuration of the
authorization boundaries is accomplished through the administrative console.
The implementation was validated against the published specification to ensure
compliance with the documented requirements for the interoperability framework.
"""


class TestSentenceAnalysis:
    def test_split_sentences_basic(self):
        sents = split_sentences('This is one. This is two. And three.')
        assert len(sents) >= 2

    def test_sentence_stats_varied(self):
        sents = split_sentences(SAMPLE_CASUAL)
        stats = sentence_stats(sents)
        assert stats['sd'] > 0
        assert stats['count'] > 0

    def test_sentence_stats_empty(self):
        stats = sentence_stats([])
        assert stats['count'] == 0
        assert stats['sd'] == 0


class TestVoiceMetrics:
    def test_parentheticals_detected(self):
        assert count_parentheticals(SAMPLE_CASUAL) >= 1

    def test_first_person_casual(self):
        assert count_first_person(SAMPLE_CASUAL) >= 2

    def test_first_person_formal(self):
        assert count_first_person(SAMPLE_FORMAL) == 0

    def test_contractions_casual(self):
        assert count_contractions(SAMPLE_CASUAL) >= 3

    def test_contractions_formal(self):
        assert count_contractions(SAMPLE_FORMAL) == 0

    def test_humor_signals(self):
        signals = detect_humor_signals(SAMPLE_CASUAL)
        assert any('Interjection' in s for s in signals)


class TestRegisterClassification:
    def test_casual_register(self):
        # Use repeated sample to get stable per-1000-word rates
        text = SAMPLE_CASUAL * 10
        stats = sentence_stats(split_sentences(text))
        vocab = vocabulary_register(text)
        fp = count_first_person(text)
        contractions = count_contractions(text)
        wc = vocab['total_words']
        register = classify_register(stats, vocab, fp, contractions, wc)
        assert register in ('Casual', 'Informed-casual')

    def test_formal_register(self):
        stats = sentence_stats(split_sentences(SAMPLE_FORMAL))
        vocab = vocabulary_register(SAMPLE_FORMAL)
        fp = count_first_person(SAMPLE_FORMAL)
        contractions = count_contractions(SAMPLE_FORMAL)
        wc = vocab['total_words']
        register = classify_register(stats, vocab, fp, contractions, wc)
        assert register in ('Professional', 'Formal/academic')


class TestExtractProse:
    def test_removes_code_blocks(self):
        text = 'Before code.\n```python\nprint("hi")\n```\nAfter code.'
        prose = extract_prose(text)
        assert 'print' not in prose
        assert 'Before code' in prose
        assert 'After code' in prose

    def test_removes_inline_code(self):
        prose = extract_prose('Use the `foo` command to start.')
        assert '`' not in prose
        assert 'Use the' in prose

    def test_removes_heading_markers(self):
        prose = extract_prose('## My Heading\n\nContent here.')
        assert '##' not in prose
        assert 'Content here' in prose


class TestProfileGeneration:
    def test_generates_valid_markdown(self, tmp_path):
        profile = generate_profile(SAMPLE_CASUAL * 5, ['test source'])
        assert '# Voice Profile' in profile
        assert '## Register' in profile
        assert '## Sentence Structure' in profile
        assert '## Source' in profile
        assert 'test source' in profile
        assert '## Metrics' in profile

    def test_generated_profile_passes_override_validator(self):
        """A generated draft must satisfy manage-voices' override schema.

        The generator and the validator are two halves of one contract: a
        draft is written here and checked by `task voices -- check`. If the
        section names drift apart, every generated profile fails validation
        the moment a user drops it into their voices directory.
        """
        manage_voices = importlib.util.spec_from_file_location(
            'manage_voices',
            Path(__file__).resolve().parent.parent
            / 'module' / 'skills' / 'humanize' / 'scripts' / 'manage-voices.py',
        )
        mv = importlib.util.module_from_spec(manage_voices)
        manage_voices.loader.exec_module(mv)

        profile = generate_profile(SAMPLE_CASUAL * 5, ['test source'])
        issues = mv.validate_profile('blog', profile)
        assert issues == [], f'generated draft fails validation: {issues}'

    def test_includes_statistics(self):
        profile = generate_profile(SAMPLE_CASUAL * 5, [])
        assert 'words_analyzed:' in profile
        assert 'sentence_length_sd:' in profile
        assert 'first_person_per_1k:' in profile

    def test_marks_sections_for_editing(self):
        profile = generate_profile(SAMPLE_CASUAL * 5, [])
        assert '<!-- EDIT' in profile


class TestCLI:
    def test_generates_profile_from_file(self, tmp_path):
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'profile.md'
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text()
        assert '# Voice Profile' in content

    def test_fails_on_too_little_text(self, tmp_path):
        src = tmp_path / 'tiny.md'
        src.write_text('Too short.')
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0
        assert 'not enough text' in result.stderr

    def test_refuses_to_overwrite_existing_output(self, tmp_path):
        """A real, often gitignored profile must not be clobbered silently."""
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'blog.local.md'
        out.write_text('my hand-tuned profile\n')
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 1
        assert f'refusing to overwrite {out}; pass --force to replace it' in result.stderr
        assert out.read_text() == 'my hand-tuned profile\n'

    def test_refuses_to_write_through_symlink(self, tmp_path):
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'blog.local.md'
        out.symlink_to(tmp_path / 'missing-target.md')
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 1
        assert not (tmp_path / 'missing-target.md').exists()

    def test_force_replaces_existing_output(self, tmp_path):
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'blog.local.md'
        out.write_text('old profile\n')
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out), '--force'],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert '# Voice Profile' in out.read_text()

    def test_force_replaces_symlink_not_its_target(self, tmp_path):
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        target = tmp_path / 'secret.txt'
        target.write_text('do not touch\n')
        out = tmp_path / 'blog.local.md'
        out.symlink_to(target)
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out), '--force'],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert target.read_text() == 'do not touch\n'
        assert not out.is_symlink()
        assert '# Voice Profile' in out.read_text()
        assert sorted(p.name for p in tmp_path.iterdir()) == \
            ['blog.local.md', 'sample.md', 'secret.txt']

    def test_missing_output_written_without_force(self, tmp_path):
        src = tmp_path / 'sample.md'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'new' / 'dir' / 'blog.local.md'
        result = subprocess.run(
            ['python3', str(SCRIPT), str(src), '-o', str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert '# Voice Profile' in out.read_text()

    def test_generates_from_directory(self, tmp_path):
        (tmp_path / 'voice-blog.html').write_text(SAMPLE_CASUAL * 10)
        (tmp_path / 'voice-github.html').write_text(SAMPLE_CASUAL * 5)
        out = tmp_path / 'profile.md'
        result = subprocess.run(
            ['python3', str(SCRIPT), str(tmp_path), '-o', str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert '# Voice Profile' in out.read_text()

    def test_fails_on_nonexistent_source(self):
        result = subprocess.run(
            ['python3', str(SCRIPT), '/tmp/no-such-path-xyz'],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0
        assert 'does not exist' in result.stderr


class TestStripHtmlTags:
    def test_strips_tags(self):
        assert strip_html_tags('<p>hello</p>') == 'hello'

    def test_strips_script_and_style(self):
        html = '<script>alert(1)</script><style>body{}</style><b>text</b>'
        result = strip_html_tags(html)
        assert 'alert' not in result
        assert 'body' not in result
        assert 'text' in result

    def test_unescapes_entities(self):
        assert 'rock & roll' in strip_html_tags('<p>rock &amp; roll</p>')

    def test_collapses_whitespace(self):
        result = strip_html_tags('<p>  lots   of   space  </p>')
        assert '  ' not in result


class TestVocabularyRegisterEmpty:
    def test_empty_string(self):
        result = vocabulary_register('')
        assert result['total_words'] == 0
        assert result['lexical_diversity'] == 0
        assert result['avg_word_length'] == 0

    def test_numbers_only(self):
        # No alphabetic words
        result = vocabulary_register('123 456 789')
        assert result['total_words'] == 0


class TestHumorSignals:
    def test_emoticons(self):
        signals = detect_humor_signals('This is fun :-) really :)')
        assert any('Emoticon' in s for s in signals)

    def test_wink(self):
        signals = detect_humor_signals('Just kidding ;)')
        assert any('Emoticon' in s for s in signals)

    def test_interjections(self):
        signals = detect_humor_signals('Ugh, this broke again.')
        assert any('Interjection' in s for s in signals)

    def test_self_deprecating(self):
        signals = detect_humor_signals("I'm not a security expert, but this looks wrong.")
        assert any('Self-deprecating' in s for s in signals)

    def test_trailing_ellipsis(self):
        signals = detect_humor_signals('So that happened...')
        assert any('ellipsis' in s for s in signals)

    def test_exclamation_marks(self):
        signals = detect_humor_signals('Wow! That worked!')
        assert any('Exclamation' in s for s in signals)

    def test_no_signals(self):
        signals = detect_humor_signals('The system processed the request.')
        assert signals == []


class TestClassifyRegisterBranches:
    """Hit every branch in classify_register."""
    def _classify(self, contraction_rate=0, fp_rate=0, long_word_pct=0,
                  lexical_diversity=0.3, sd=5):
        # Build minimal stats/vocab dicts with enough control over inputs
        word_count = 1000  # so rate = raw count
        stats = {'sd': sd, 'count': 50, 'mean': 15, 'min': 3, 'max': 40,
                 'short_pct': 10, 'long_pct': 10}
        vocab = {'total_words': word_count, 'unique_words': 300,
                 'lexical_diversity': lexical_diversity,
                 'avg_word_length': 5, 'long_word_pct': long_word_pct}
        return classify_register(stats, vocab, fp_rate, contraction_rate, word_count)

    def test_casual(self):
        # High contractions + high first person + high SD -> Casual
        reg = self._classify(contraction_rate=15, fp_rate=20, sd=9)
        assert reg == 'Casual'

    def test_informed_casual(self):
        # score: contraction 6 -> -1, fp 6 -> -1 = -2 -> Informed-casual
        reg = self._classify(contraction_rate=6, fp_rate=6, sd=5)
        assert reg == 'Informed-casual'

    def test_professional(self):
        # score: long_word_pct 12 -> +1, lexical_diversity 0.65 -> +1 = +2 -> Professional
        #   but +2 is Formal/academic, so use only one positive factor
        reg = self._classify(contraction_rate=2, fp_rate=2, long_word_pct=12)
        assert reg == 'Professional'

    def test_formal_academic(self):
        reg = self._classify(contraction_rate=0, fp_rate=0,
                             long_word_pct=20, lexical_diversity=0.7, sd=3)
        assert reg == 'Formal/academic'

    def test_high_contraction_rate_minus2(self):
        # contraction_rate > 10 -> -2
        reg = self._classify(contraction_rate=12, fp_rate=0, long_word_pct=12)
        assert reg in ('Informed-casual', 'Professional')

    def test_moderate_contraction_rate_minus1(self):
        # 5 < contraction_rate <= 10 -> -1
        reg = self._classify(contraction_rate=7, fp_rate=0)
        assert reg in ('Informed-casual', 'Professional')

    def test_high_first_person_minus2(self):
        reg = self._classify(fp_rate=20, contraction_rate=0, long_word_pct=12)
        assert reg in ('Informed-casual', 'Professional')

    def test_moderate_first_person_minus1(self):
        reg = self._classify(fp_rate=8, contraction_rate=0)
        assert reg in ('Informed-casual', 'Professional')

    def test_very_high_long_word_pct(self):
        # long_word_pct > 15 -> +2
        reg = self._classify(long_word_pct=20)
        assert reg in ('Professional', 'Formal/academic')

    def test_moderate_long_word_pct(self):
        # 10 < long_word_pct <= 15 -> +1
        reg = self._classify(long_word_pct=12)
        assert reg in ('Professional', 'Formal/academic')

    def test_high_lexical_diversity(self):
        reg = self._classify(lexical_diversity=0.7, long_word_pct=12)
        assert reg in ('Professional', 'Formal/academic')

    def test_high_sd_minus1(self):
        # sd > 8 -> -1
        reg = self._classify(sd=10)
        assert reg in ('Informed-casual', 'Professional')


class TestProfileLongExamples:
    def test_long_examples_included(self):
        # Build text with sentences > 25 words to trigger long_examples branch
        long_sent = ' '.join(['word'] * 30) + '.'
        short_sent = 'This is short enough right here.'
        text = (long_sent + ' ' + short_sent + ' ') * 10
        profile = generate_profile(text, ['test'])
        assert 'Long examples' in profile

    def test_html_in_prose_triggers_strip(self):
        # Text with HTML tags in prose triggers strip_html_tags inside generate_profile
        html_text = '<p>I wrote this blog post about systems.</p> ' * 30
        profile = generate_profile(html_text, ['test'])
        assert '# Voice Profile' in profile
        assert '<p>' not in profile

    def test_parenthetical_rate_branches(self):
        # Text with many parenthetical asides (>3 per 1000 words)
        paren_text = 'I tried this approach (which was risky and complicated). ' * 50
        profile = generate_profile(paren_text, ['test'])
        assert 'parenthetical' in profile.lower()


class TestLoadSources:
    def test_single_file(self, tmp_path):
        f = tmp_path / 'sample.txt'
        f.write_text('Hello world. ' * 50)
        text, descs = load_sources(f)
        assert 'Hello world' in text
        assert str(f) in descs[0]

    def test_nonexistent_path(self, tmp_path):
        text, descs = load_sources(tmp_path / 'nope')
        assert text == ''
        assert descs == []

    def test_directory_with_voice_files(self, tmp_path):
        content = 'Voice content here. ' * 20
        (tmp_path / 'voice-blog.html').write_text(content)
        (tmp_path / 'other.txt').write_text('Should be ignored. ' * 20)
        text, descs = load_sources(tmp_path)
        assert 'Voice content' in text
        # voice files take priority, other.txt excluded
        assert len(descs) == 1

    def test_directory_fallback_to_all_files(self, tmp_path):
        content = 'General content here and more words. ' * 20
        (tmp_path / 'notes.txt').write_text(content)
        text, descs = load_sources(tmp_path)
        assert 'General content' in text

    def test_skips_short_files(self, tmp_path):
        (tmp_path / 'tiny.txt').write_text('short')
        (tmp_path / 'ok.txt').write_text('Long enough content. ' * 20)
        text, descs = load_sources(tmp_path)
        assert len(descs) == 1  # only the longer file

    def test_reads_meta_description(self, tmp_path):
        (tmp_path / 'notes.txt').write_text('Content here for analysis. ' * 20)
        (tmp_path / 'notes.meta').write_text('description=My blog post\nurl=https://example.com\n')
        text, descs = load_sources(tmp_path)
        assert descs[0] == 'My blog post'

    def test_reads_meta_url_fallback(self, tmp_path):
        (tmp_path / 'notes.txt').write_text('Content here for analysis. ' * 20)
        (tmp_path / 'notes.meta').write_text('url=https://example.com\n')
        text, descs = load_sources(tmp_path)
        assert descs[0] == 'https://example.com'

    def test_meta_no_matching_keys(self, tmp_path):
        (tmp_path / 'notes.txt').write_text('Content here for analysis. ' * 20)
        (tmp_path / 'notes.meta').write_text('author=someone\n')
        text, descs = load_sources(tmp_path)
        # Falls through for/else -> uses filename
        assert str(tmp_path / 'notes.txt') in descs[0]


class TestMainFunction:
    def test_main_creates_output(self, tmp_path, monkeypatch):
        src = tmp_path / 'input.txt'
        src.write_text(SAMPLE_CASUAL * 10)
        out = tmp_path / 'out.md'
        monkeypatch.setattr('sys.argv', ['analyze-voice', str(src), '-o', str(out)])
        main()
        assert out.exists()
        assert '# Voice Profile' in out.read_text()

    def test_main_nonexistent_source(self, tmp_path, monkeypatch):
        monkeypatch.setattr('sys.argv', ['analyze-voice', '/tmp/no-such-xyz'])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_too_little_text(self, tmp_path, monkeypatch):
        src = tmp_path / 'tiny.txt'
        src.write_text('Short.')
        monkeypatch.setattr('sys.argv', ['analyze-voice', str(src), '-o', str(tmp_path / 'out.md')])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
