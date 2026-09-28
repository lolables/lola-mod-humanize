"""Tests for the readability lane in pre-scan.py."""
import pytest

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

    @pytest.mark.parametrize('stop', ['."', '?)', '.*', '!’', '.]'])
    def test_closing_punctuation_ends_the_sentence(self, stop):
        # Two 30-word sentences. Glued, they read as one 60-word run-on.
        half = ' '.join(f'w{i}' for i in range(30))
        text = f'*{half}{stop} {half}.\n'
        assert 'long-sentence' not in _tags(scan_readability(text))

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

    def test_structured_density_excludes_frontmatter(self):
        # Frontmatter lines ("---", "title: x") are metadata, not content:
        # only the two list items count, and both are structural.
        text = "---\ntitle: x\n---\n\n- a\n- b\n"
        assert compute_stats(text)['structured_density'] == 1.0

    def test_max_sentence_len_ignores_fenced_code(self):
        text = "Short prose here.\n\n```\n" + "x " * 60 + "\n```\n"
        assert compute_stats(text)['max_sentence_len'] <= 3

    def test_max_sentence_len_ignores_indented_code(self):
        text = "Short prose here.\n\n    " + "x " * 60 + "\n"
        assert compute_stats(text)['max_sentence_len'] <= 3

    PROSE = ("The cache is cold on the first run. It warms up fast. After that, "
             "most reads skip the database entirely and return in a few milliseconds.\n")

    def test_sd_ignores_tables_and_code(self):
        table = "| step | what happens here |\n|---|---|\n" + "".join(
            f"| {i} | the worker pulls job {i} off the queue. |\n" for i in range(12))
        code = ("```mermaid\ngraph TD\n  A[Client sends a request] --> B. "
                "B --> C[Cache lookup happens]\n```\n")
        doc = "# Cache\n\n" + self.PROSE + "\n" + table + "\n" + code
        prose_sd = compute_stats(self.PROSE)['sd']
        assert prose_sd > 0
        assert compute_stats(doc)['sd'] == prose_sd

    def test_max_sentence_len_splits_after_closing_quote(self):
        text = ('He said "stop the deploy now." Then the team rolled back '
                'every change made that morning.\n')
        assert compute_stats(text)['max_sentence_len'] == 10


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


class TestFenceDetection:
    """A fence opener is indented at most 3 spaces (CommonMark).

    Deeper backticks, such as a fence mentioned inside an indented HTML
    comment, used to toggle the in-fence state and hide all later prose.
    """
    LONG = "This " + "and that ".join(str(i) for i in range(25)) + " end."
    HIDDEN = "<!-- notes:\n        ```mermaid fence stays inline.\n-->\n\n"

    def test_indented_backticks_do_not_open_fence(self):
        hits = scan_readability(self.HIDDEN + self.LONG + "\n")
        assert 'long-sentence' in _tags(hits)

    def test_stats_see_prose_after_indented_backticks(self):
        stats = compute_stats(self.HIDDEN + self.LONG + "\n")
        assert stats['max_sentence_len'] > 45

    def test_density_counts_lines_after_indented_backticks(self):
        # The whole "<!--" .. "-->" span is a comment block now, so it is
        # not content at all: 2 non-blank content lines remain ("- a",
        # "- b"), both structural, so density is 1.0.
        stats = compute_stats("<!--\n        ```x\n-->\n\n- a\n- b\n")
        assert stats['structured_density'] == 1.0

    def test_three_space_indent_fence_still_fences(self):
        hits = scan_readability("   ```\n" + self.LONG + "\n   ```\n")
        assert 'long-sentence' not in _tags(hits)

    def test_list_nested_fence_does_not_leak_into_prose(self):
        # CommonMark measures the 0-3 space fence allowance from the
        # enclosing list item, not column 0. A fence indented 4 spaces
        # under a list item is still a real fence.
        code = "    " + " ".join(f"--flag{i} value{i}" for i in range(30)) + " && echo done."
        doc = "1. Install the tool:\n\n    ```bash\n" + code + "\n    ```\n\n2. Run it.\n"
        assert 'long-sentence' not in _tags(scan_readability(doc))
        assert compute_stats(doc)['max_sentence_len'] == 0

    def test_fence_closer_needs_matching_run_length(self):
        # A ```python info-string line inside an open ``` fence is fenced
        # content, not a closer: it isn't a run of only backticks.
        text = "```\n```python\nstill code?\n```\nafter\n"
        assert pre_scan._prose_paragraphs(text) == [[(5, 'after')]]

    def test_longer_fence_run_requires_matching_closer(self):
        # A 4-backtick opener needs a closer with at least 4 backticks;
        # a 3-backtick line inside it is just more fenced content.
        text = "````markdown\n```python\nx=1\n```\n````\n\nafter prose\n"
        assert pre_scan._prose_paragraphs(text) == [[(7, 'after prose')]]


class TestIndentedCodeBlock:
    """CommonMark: a 4+ space indent is a code block only if it does not
    continue a paragraph (previous line blank, or file start) and it is
    not list-item continuation."""

    def test_indented_block_after_blank_is_code(self):
        assert pre_scan._prose_paragraphs("Intro.\n\n    key: value: other\n") == [
            [(1, 'Intro.')]]

    def test_indented_block_after_list_item_is_continuation(self):
        assert pre_scan._prose_paragraphs("- item\n\n    continuation para text.\n") == [
            [(3, 'continuation para text.')]]

    def test_lazy_continuation_is_not_code(self):
        assert pre_scan._prose_paragraphs("Para line one\n    lazy continuation\n") == [
            [(1, 'Para line one'), (2, 'lazy continuation')]]

    def test_code_block_spans_blank_lines(self):
        text = "Intro.\n\n    code\n\n    more code\nback to prose\n"
        assert pre_scan._prose_paragraphs(text) == [
            [(1, 'Intro.')], [(6, 'back to prose')]]

    def test_indented_block_right_after_heading_is_code(self):
        # A heading ends whatever paragraph came before it; there is
        # nothing for the indented line to lazily continue.
        assert pre_scan._prose_paragraphs("# Head\n    code\n") == []

    def test_indented_block_right_after_closing_fence_is_code(self):
        assert pre_scan._prose_paragraphs("```\nx\n```\n    code\n") == []

    def test_lazy_continuation_after_plain_paragraph_still_continues(self):
        assert pre_scan._prose_paragraphs("Para\n    lazy\n") == [
            [(1, 'Para'), (2, 'lazy')]]

    def test_unbalanced_fence_inside_indented_block_does_not_hide_rest(self):
        # An indented block wins over _fence_re: a fence marker inside
        # one used to open a real (unbalanced) fence and hide every line
        # after it, with no closer ever coming.
        text = "Para.\n\n    ```\n    only one fence in indented example\n\nLater prose one.\n\nLater prose two.\n"
        assert pre_scan._prose_paragraphs(text) == [
            [(1, 'Para.')], [(6, 'Later prose one.')], [(8, 'Later prose two.')]]

    def test_closing_fence_resets_list_item_context(self):
        # The fence opens at column 0, outside the item, so it fully
        # interrupts the list item from line 1: the indented block after
        # it is code, not the item's lazy continuation.
        assert pre_scan._prose_paragraphs("- item\n```\nx\n```\n    code\nprose\n") == [
            [(6, 'prose')]]

    def test_closing_comment_at_column_zero_also_resets_list_item_context(self):
        assert pre_scan._prose_paragraphs("- item\n<!--\nx\n-->\n    code\nprose\n") == [
            [(6, 'prose')]]

    def test_fence_indented_inside_list_item_keeps_item_open(self):
        # The fence opens at indent 4, inside the item's own content, so
        # closing it does not end the item: "tail" is still the item's
        # lazy continuation, not a fresh indented code block.
        text = "- item\n\n    ```\n    x\n    ```\n    tail\n"
        assert [i for i, t in pre_scan._content_lines(text) if t.strip()] == [1, 6]

    def test_ordered_list_fence_with_trailing_continuation(self):
        text = ("1. Step\n\n    ```bash\n    code\n    ```\n\n"
                "    Then run the next command.\n\nAfter.\n")
        assert [i for i, t in pre_scan._content_lines(text) if t.strip()] == [1, 7, 9]

    def test_comment_indented_inside_list_item_keeps_item_open(self):
        text = "- item\n\n    <!--\n    hidden\n    -->\n\n    continuation\n"
        assert [i for i, t in pre_scan._content_lines(text) if t.strip()] == [1, 7]

    def test_comment_at_item_indent_with_no_blank_before_keeps_item_open(self):
        text = "- item\n  <!-- a\n  b --> \n\n    cont\n"
        assert [i for i, t in pre_scan._content_lines(text) if t.strip()] == [1, 5]

    def test_closing_comment_marker_counts_as_blank(self):
        assert pre_scan._prose_paragraphs("<!--\nx\n-->\n    code\n") == []

    def test_closing_frontmatter_counts_as_blank(self):
        assert pre_scan._prose_paragraphs("---\na: 1\n---\n    code\n") == []


class TestProseParagraphs:
    LONG = "This " + "and that ".join(str(i) for i in range(25)) + " end."

    def test_paragraphs_keep_source_line_numbers(self):
        paras = pre_scan._prose_paragraphs("one\ntwo\n\n# H\nthree\n")
        assert paras == [[(1, 'one'), (2, 'two')], [(5, 'three')]]

    def test_blockquote_is_not_prose(self):
        assert 'long-sentence' not in _tags(scan_readability("> " + self.LONG + "\n"))

    def test_blockquote_ends_prior_paragraph(self):
        # A `>` line ends whatever paragraph came before it. "after" has
        # no blank line before it, so lazy continuation (below) makes it
        # part of the quote, not a new paragraph.
        paras = pre_scan._prose_paragraphs("Label:\n> quoted\nafter\n")
        assert paras == [[(1, 'Label:')]]

    def test_blockquote_lazy_continuation(self):
        paras = pre_scan._prose_paragraphs("> quote start\nlazy continuation\n\nreal prose\n")
        assert paras == [[(4, 'real prose')]]

    def test_fence_in_frontmatter_block_scalar_does_not_hide_body(self):
        text = "---\nexample: |\n  ```bash\n  foo\n---\n\nBody prose here.\n"
        assert pre_scan._prose_paragraphs(text) == [[(7, 'Body prose here.')]]

    def test_indented_rule_in_block_scalar_does_not_close_frontmatter(self):
        text = "---\na: |\n  ---\nb: 2\n---\nbody\n"
        assert pre_scan._prose_paragraphs(text) == [[(6, 'body')]]

    def test_bom_does_not_defeat_frontmatter_detection(self):
        text = "﻿---\na: 1\n---\nbody\n"
        assert pre_scan._prose_paragraphs(text) == [[(4, 'body')]]

    def test_tilde_fence_inside_backtick_fence_stays_hidden(self):
        text = "```\n~~~\nhidden\n```\nafter\n"
        assert pre_scan._prose_paragraphs(text) == [[(5, 'after')]]

    def test_inline_backtick_span_does_not_open_fence(self):
        # CommonMark: a backtick fence's info string cannot itself contain
        # a backtick, so a line like this is an inline code span in
        # prose, not a fence opener.
        text = "```inline code``` in prose.\nmore prose\n"
        assert pre_scan._prose_paragraphs(text) == [
            [(1, '```inline code``` in prose.'), (2, 'more prose')],
        ]

    def test_backtick_fence_with_clean_info_string_still_opens(self):
        text = "```python\nx=1\n```\nafter\n"
        assert pre_scan._prose_paragraphs(text) == [[(4, 'after')]]

    def test_multiline_comment_prose_is_skipped(self):
        text = "<!-- note\nlong words here\n-->\nreal\n"
        assert pre_scan._prose_paragraphs(text) == [[(4, 'real')]]

    def test_single_line_comment_is_ordinary_content(self):
        text = "<!-- a --> text\n"
        assert pre_scan._prose_paragraphs(text) == [[(1, '<!-- a --> text')]]

    def test_crlf_line_endings(self):
        assert pre_scan._prose_paragraphs("one\r\ntwo\r\n") == [[(1, 'one'), (2, 'two')]]

    def test_mid_line_comment_open_does_not_hide_rest_of_doc(self):
        # HTML block type 2 only starts when <!-- begins the line. A
        # <!-- quoted mid-sentence is ordinary text.
        text = ("Write `<!--` to start a comment.\n"
                "This prose line should be scanned.\n"
                "\n"
                "So should this one.\n")
        paras = pre_scan._prose_paragraphs(text)
        assert paras == [
            [(1, 'Write `<!--` to start a comment.'), (2, 'This prose line should be scanned.')],
            [(4, 'So should this one.')],
        ]

    def test_last_open_comment_marker_on_line_governs(self):
        # Two <!-- on one line: the first is closed by its own -->, the
        # second is not, so the line still opens a comment block (it
        # starts with <!--) that runs through the first later -->.
        text = "<!-- a --> <!-- b\n```\n-->\nprose after\n"
        assert pre_scan._prose_paragraphs(text) == [[(4, 'prose after')]]

    def test_structural_line_ends_lazy_blockquote(self):
        assert pre_scan._prose_paragraphs("> q\n# H\nprose\n") == [[(3, 'prose')]]

    def test_frontmatter_is_not_prose(self):
        text = "---\ndescription: " + self.LONG + "\n---\n\nShort body.\n"
        assert 'long-sentence' not in _tags(scan_readability(text))

    def test_prose_after_frontmatter_is_scanned(self):
        text = "---\ntitle: x\n---\n\n" + self.LONG + "\n"
        assert 'long-sentence' in _tags(scan_readability(text))

    def test_unclosed_leading_rule_is_not_frontmatter(self):
        assert 'long-sentence' in _tags(scan_readability("---\ntitle: x\n" + self.LONG + "\n"))

    def test_rule_followed_by_blank_is_not_frontmatter(self):
        text = "---\n\n" + self.LONG + "\n\n---\n"
        assert 'long-sentence' in _tags(scan_readability(text))


class TestLineBoundaries:
    """Lines that end a paragraph even without a blank line before them."""

    def test_colon_line_before_list_is_its_own_sentence(self):
        text = "We tried two fixes. The setup needs three things:\n- a cache\n- a queue\n"
        paras = pre_scan._prose_paragraphs(text)
        assert paras == [[(1, 'We tried two fixes. The setup needs three things:')]]
        assert [s for _, s, _, _ in pre_scan._paragraph_sentences(paras[0])] == [
            'We tried two fixes', 'The setup needs three things:']

    DETAILS = ("<details>\n"
               "<summary>Why the cache stays cold on start</summary>\n"
               "The first run misses every key in the store. Later runs hit.\n"
               "</details>\n"
               "Next the worker starts up.\n")

    def test_html_block_tag_lines_are_not_prose(self):
        assert pre_scan._prose_paragraphs(self.DETAILS) == [
            [(3, 'The first run misses every key in the store. Later runs hit.')],
            [(5, 'Next the worker starts up.')],
        ]

    def test_summary_does_not_glue_into_max_sentence_len(self):
        assert compute_stats(self.DETAILS)['max_sentence_len'] == 9

    def test_inline_tag_at_line_start_stays_prose(self):
        # <kbd> is not a CommonMark block tag, so the line is a sentence.
        assert pre_scan._prose_paragraphs("<kbd>Ctrl</kbd> opens the menu.\n") == [
            [(1, '<kbd>Ctrl</kbd> opens the menu.')]]

    def test_block_tag_name_prefix_is_not_a_block_tag(self):
        # The tag name must match a block tag whole: <paragraph> is not <p>.
        assert pre_scan._prose_paragraphs("<paragraph> is a made-up tag.\n") == [
            [(1, '<paragraph> is a made-up tag.')]]

    def test_emphasis_only_line_is_its_own_paragraph(self):
        text = ("![flow](flow.png)\n"
                "*Figure 1: Request flow through the cache*\n"
                "The cache sits in front of the database.\n")
        assert pre_scan._prose_paragraphs(text) == [
            [(1, '![flow](flow.png)')],
            [(2, '*Figure 1: Request flow through the cache*')],
            [(3, 'The cache sits in front of the database.')],
        ]

    def test_bold_only_line_is_its_own_paragraph(self):
        text = "Run the tests first\n__Never skip this step__\nThen merge.\n"
        assert len(pre_scan._prose_paragraphs(text)) == 3

    def test_line_with_two_emphasis_spans_stays_in_paragraph(self):
        text = "*Fast* and *cheap* both matter\nhere and now.\n"
        assert pre_scan._prose_paragraphs(text) == [
            [(1, '*Fast* and *cheap* both matter'), (2, 'here and now.')]]

    def test_other_delimiter_inside_emphasis_line_is_still_one_span(self):
        text = "Name things clearly\n*Use snake_case for module names*\nThen commit.\n"
        assert len(pre_scan._prose_paragraphs(text)) == 3


class TestSdVerdict:
    """The SD verdict compares against the voice's sentence_length_sd range."""

    STATS = {'words': 100, 'bold_per_1000w': 0.0, 'max_sentence_len': 0,
             'structured_density': 0.0}

    def _human(self, sd, sd_range):
        return pre_scan.format_human('t.md', [], {**self.STATS, 'sd': sd}, sd_range=sd_range)

    def _llm(self, sd, sd_range):
        return pre_scan.format_llm('t.md', [], {**self.STATS, 'sd': sd}, sd_range=sd_range)

    def test_loads_range_from_voice(self):
        assert pre_scan.load_voice_thresholds('general')['sd_range'] == (6.0, 12.0)

    def test_unknown_voice_has_no_range(self):
        assert pre_scan.load_voice_thresholds('does-not-exist')['sd_range'] is None

    @pytest.mark.parametrize('body', ['max_sentence_len: 30\n',
                                      'sentence_length_sd: 54.6\n',
                                      '# sentence_length_sd:\n'])
    def test_missing_or_single_value_key_has_no_range(self, tmp_path, monkeypatch, body):
        (tmp_path / 'demo.md').write_text(body, encoding='utf-8')
        monkeypatch.setattr(pre_scan, '_VOICES_DIR', tmp_path)
        assert pre_scan.load_voice_thresholds('demo')['sd_range'] is None

    @pytest.mark.parametrize('sd', [6.0, 9.0, 12.0])
    def test_in_range(self, sd):
        assert f'sentence-length SD: {sd} (OK, target 6-12)' in self._human(sd, (6.0, 12.0))
        assert 'sd_verdict=OK sd_target=6-12' in self._llm(sd, (6.0, 12.0))

    def test_below_range(self):
        assert '(LOW, target 6-12)' in self._human(5.9, (6.0, 12.0))
        assert 'sd_verdict=LOW sd_target=6-12' in self._llm(5.9, (6.0, 12.0))

    def test_above_range(self):
        assert '(HIGH, target 6-12)' in self._human(15.0, (6.0, 12.0))
        assert 'sd_verdict=HIGH sd_target=6-12' in self._llm(15.0, (6.0, 12.0))

    def test_fractional_range_bounds_print_as_given(self):
        assert '(OK, target 4.5-8)' in self._human(5.0, (4.5, 8.0))

    @pytest.mark.parametrize('sd,label', [(4.0, 'LOW'), (8.0, 'OK'), (30.0, 'OK')])
    def test_no_voice_falls_back_to_floor_of_8(self, sd, label):
        assert f'({label}, target >= 8)' in self._human(sd, None)
        assert f'sd_verdict={label} sd_target=>=8' in self._llm(sd, None)

    def test_cli_uses_voice_range(self, tmp_path):
        import subprocess
        import sys
        f = tmp_path / 'x.md'
        f.write_text('The cache is cold. It warms up after the first few runs.\n',
                     encoding='utf-8')
        cmd = [sys.executable, pre_scan.__file__, '--mode', 'human']
        with_voice = subprocess.run(cmd + ['--voice', 'rfc', str(f)],
                                    capture_output=True, text=True, timeout=30).stdout
        without = subprocess.run(cmd + [str(f)],
                                 capture_output=True, text=True, timeout=30).stdout
        assert 'target 4-8)' in with_voice
        assert 'target >= 8)' in without
