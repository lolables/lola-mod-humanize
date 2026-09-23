"""Tests for the readability lane in pre-scan.py."""
from conftest import pre_scan

scan_readability = pre_scan.scan_readability


def _tags(findings):
    return [f['tag'] for f in findings]


class TestLongSentence:
    def test_flags_run_on_sentence(self):
        # 50-word single sentence, one paragraph.
        s = "This " + "and that ".join(str(i) for i in range(25)) + " end."
        assert len(s.split()) > 45
        hits = scan_readability(s + "\n")
        assert 'long-sentence' in _tags(hits)

    def test_short_sentence_clean(self):
        hits = scan_readability("This is fine. So is this.\n")
        assert 'long-sentence' not in _tags(hits)

    def test_clause_heavy_sentence_flagged(self):
        s = ("The system works, and it scales, but it fails, although rarely, "
             "because the cache, which is cold, misses.\n")
        hits = scan_readability(s)
        assert 'clause-heavy' in _tags(hits)

    def test_respects_max_sentence_len_arg(self):
        s = "one two three four five six seven eight nine ten eleven twelve.\n"
        assert 'long-sentence' not in _tags(scan_readability(s, max_sentence_len=45))
        assert 'long-sentence' in _tags(scan_readability(s, max_sentence_len=5))


compute_stats = pre_scan.compute_stats


class TestWallOfText:
    def test_flags_dense_paragraph(self):
        # 8 short prose sentences, no blank lines, no structure.
        para = " ".join(f"Point number {i} stands alone here." for i in range(8))
        hits = scan_readability(para + "\n")
        assert 'wall-of-text' in _tags(hits)

    def test_list_block_not_wall(self):
        text = "\n".join(f"- item {i}" for i in range(8)) + "\n"
        assert 'wall-of-text' not in _tags(scan_readability(text))

    def test_fenced_code_skipped(self):
        text = "```\n" + "\n".join(f"x{i} = {i}" for i in range(8)) + "\n```\n"
        assert scan_readability(text) == []


class TestStats:
    def test_max_sentence_len(self):
        s = "one two three four five six seven eight nine ten eleven. Short.\n"
        assert compute_stats(s)['max_sentence_len'] == 11

    def test_structured_density_prose(self):
        assert compute_stats("Just a sentence of prose here.\n")['structured_density'] == 0.0

    def test_structured_density_list(self):
        text = "Intro line.\n- a\n- b\n- c\n"
        d = compute_stats(text)['structured_density']
        assert 0.7 <= d <= 0.76  # 3 of 4 non-blank lines are structure

    def test_max_sentence_len_ignores_fenced_code(self):
        text = "Short prose here.\n\n```\n" + "x " * 60 + "\n```\n"
        assert compute_stats(text)['max_sentence_len'] <= 3


class TestVoiceThresholds:
    def test_load_known_voice(self):
        # release-notes has a low max_sentence_len (set in Task 6).
        t = pre_scan.load_voice_thresholds('release-notes')
        assert t['max_sentence_len'] <= 25

    def test_unknown_voice_defaults(self):
        t = pre_scan.load_voice_thresholds('does-not-exist')
        assert t['max_sentence_len'] == pre_scan.DEFAULT_MAX_SENTENCE_LEN
        assert t['structured_density_max'] is None


class TestLoadVoiceHappyPath:
    def test_parses_both_keys(self, tmp_path, monkeypatch):
        v = tmp_path / 'demo.md'
        v.write_text('max_sentence_len: 20\nstructured_density_max: 0.9\n', encoding='utf-8')
        monkeypatch.setattr(pre_scan, '_VOICES_DIR', tmp_path)
        t = pre_scan.load_voice_thresholds('demo')
        assert t['max_sentence_len'] == 20
        assert t['structured_density_max'] == 0.9


class TestProseGating:
    """The readability lane runs on prose files only, not code."""

    _SCRIPT = pre_scan.__file__

    def _run(self, path):
        import subprocess
        import sys
        r = subprocess.run(
            [sys.executable, self._SCRIPT, '--mode', 'llm', str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout

    def test_code_file_gets_no_readability_flags(self, tmp_path):
        f = tmp_path / 'x.py'
        # Commas + keywords are syntax here, not prose clauses.
        f.write_text('def f(a, b, c):\n    return a and b or c and not b\n',
                     encoding='utf-8')
        out = self._run(f)
        assert 'clause-heavy' not in out
        assert 'long-sentence' not in out
        assert 'wall-of-text' not in out

    def test_markdown_file_gets_readability(self, tmp_path):
        f = tmp_path / 'x.md'
        f.write_text(('word ' * 60) + '.\n', encoding='utf-8')
        assert 'long-sentence' in self._run(f)
