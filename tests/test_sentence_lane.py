"""Tests for the sentence lane in pre-scan.py: relations between sentences."""
import random
import subprocess
import sys
from pathlib import Path

from conftest import pre_scan

scan_sentences = pre_scan.scan_sentences
SCRIPT = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts' / 'pre-scan.py'


def _hits(text, tag):
    return [f for f in scan_sentences(text) if f['tag'] == tag]


class TestParagraphSentences:
    def test_maps_sentences_to_source_lines(self):
        para = [(4, 'Alpha beta gamma.'), (5, 'Delta epsilon. Zeta eta')]
        got = [(ln, s) for ln, s, _, _ in pre_scan._paragraph_sentences(para)]
        assert got == [(4, 'Alpha beta gamma'), (5, 'Delta epsilon'), (5, 'Zeta eta')]

    def test_reports_each_sentence_terminator(self):
        got = pre_scan._paragraph_sentences([(1, 'Is it done?" Yes. It needs three things:')])
        assert [end for _, _, _, end in got] == ['?', '.', ':']
        (*_, end), = pre_scan._paragraph_sentences([(1, 'No stop here')])
        assert end == ''

    def test_inline_code_does_not_split_and_is_masked(self):
        got = pre_scan._paragraph_sentences([(1, 'Run `a. b` now. Done')])
        assert [(s, m) for _, s, m, _ in got] == [
            ('Run `a. b` now', 'Run ###### now'), ('Done', 'Done')]

    def test_html_comment_is_masked(self):
        (_, _, masked, _), = pre_scan._paragraph_sentences([(1, '<!-- a: b --> Words')])
        assert ':' not in masked

    def test_closing_quote_ends_sentence(self):
        got = pre_scan._paragraph_sentences([(1, 'He said "stop." Then he left')])
        assert len(got) == 2

    def test_closing_guillemet_ends_sentence(self):
        got = pre_scan._paragraph_sentences([(1, 'She said «ok.» Then went')])
        assert len(got) == 2

    def test_abbreviation_does_not_split_sentence(self):
        got = pre_scan._paragraph_sentences([(1, 'Use a tool, e.g. grep works')])
        assert len(got) == 1

    def test_etc_splits_before_capitalized_word(self):
        # Unlike e.g./i.e./vs./cf., "etc." routinely ends both a list and
        # the sentence: a capitalized next word is a real new sentence.
        got = pre_scan._paragraph_sentences([(1, 'Ships lists, maps, etc. Then it stops')])
        assert len(got) == 2

    def test_etc_does_not_split_before_lowercase_word(self):
        got = pre_scan._paragraph_sentences([(1, 'Ships lists, maps, etc. then it stops')])
        assert len(got) == 1

    def test_parenthesized_abbreviation_still_suppresses_split(self):
        # A token like "(e.g" (paren glued to the abbreviation) must not
        # defeat the abbreviation lookup.
        got = pre_scan._paragraph_sentences([(1, '(e.g. grep works)')])
        assert len(got) == 1

    def test_etc_splits_before_quoted_opener(self):
        got = pre_scan._paragraph_sentences([(1, 'Pick apples, pears, etc. "Foo" is next')])
        assert len(got) == 2

    def test_etc_splits_before_emphasized_opener(self):
        got = pre_scan._paragraph_sentences([(1, 'Pick apples, pears, etc. *Never* is next')])
        assert len(got) == 2

    def test_etc_splits_before_backticked_opener(self):
        # `Foo` is masked to filler in the sentence-splitting text, which
        # would hide the capital F this check needs if it read masked
        # text instead of the raw line.
        got = pre_scan._paragraph_sentences([(1, 'Pick apples, pears, etc. `Foo` is next')])
        assert len(got) == 2

    def test_etc_before_lowercase_opener_still_does_not_split(self):
        got = pre_scan._paragraph_sentences([(1, 'Pick apples, pears, etc. and more')])
        assert len(got) == 1

    def test_backtick_masking_does_not_cross_source_lines(self):
        # A stray, unpaired backtick on one line must not pair with a
        # stray backtick on a later line: masking the joined paragraph
        # text (instead of each line before joining) let that happen and
        # hid a real double colon between them.
        para = [(1, 'A ` stray tick. Label: one: two. More'), (2, 'text ` here.')]
        got = pre_scan._paragraph_sentences(para)
        assert any(':' in masked and masked.count(':') >= 2 for _, _, masked, _ in got)


class TestDoubleColon:
    def test_flags_two_colons(self):
        hits = _hits("Appendix A: the rollout, as one fleet: 300 runners.\n", 'double-colon')
        assert [(h['line'], h['severity']) for h in hits] == [(1, 'HIGH')]

    def test_single_colon_clean(self):
        assert not _hits("The note is short: it names the version.\n", 'double-colon')

    def test_time_and_url_colons_clean(self):
        assert not _hits("Meet at 10:30: bring notes from https://example.com/a:b today.\n",
                         'double-colon')

    def test_inline_code_colons_ignored(self):
        assert not _hits("Set `a: 1` and `b: 2` in the config: then restart.\n", 'double-colon')

    def test_html_comment_colons_ignored(self):
        assert not _hits("<!-- GENERATED: x --> Words: a, b.\n", 'double-colon')

    def test_colons_in_separate_sentences_clean(self):
        assert not _hits("Anchor it: here. Against: this.\n", 'double-colon')

    def test_heading_fence_and_quote_ignored(self):
        text = "## Part A: setup: basics\n\n```\nkey: value: other\n```\n\n> Before: x: y\n"
        assert not _hits(text, 'double-colon')

    def test_reports_line_where_sentence_starts(self):
        hits = _hits("Intro sentence runs\nhere. Label: one: two.\n", 'double-colon')
        assert [h['line'] for h in hits] == [2]

    def test_stray_backtick_does_not_cross_source_lines(self):
        text = "A ` stray tick. Label: one: two. More\ntext ` here.\n"
        hits = _hits(text, 'double-colon')
        assert [(h['line'], h['severity']) for h in hits] == [(1, 'HIGH')]

    def test_abbreviation_does_not_split_sentence(self):
        hits = _hits("Use a tool, e.g. grep: it works: always.\n", 'double-colon')
        assert len(hits) == 1

    def test_etc_before_capitalized_word_splits_sentence(self):
        # Each half has only one colon; merged into one sentence (the
        # old behavior) the two colons together gave a false positive.
        assert not _hits("Pick one: apples, pears, etc. Note: this is fine.\n", 'double-colon')

    def test_parenthesized_abbreviation_fires_once(self):
        hits = _hits("(e.g. grep: it works: always)\n", 'double-colon')
        assert len(hits) == 1


class TestCLI:
    def _run(self, tmp_path, suffix, body):
        f = tmp_path / f'doc{suffix}'
        f.write_text(body)
        return subprocess.run([sys.executable, str(SCRIPT), '--mode', 'llm', str(f)],
                              capture_output=True, text=True)

    def test_prose_file_reports_tag(self, tmp_path):
        r = self._run(tmp_path, '.md', "Appendix A: the rollout, as one fleet: 300 runners.\n")
        assert r.returncode == 0
        assert '[double-colon]' in r.stdout

    def test_code_file_skips_lane(self, tmp_path):
        r = self._run(tmp_path, '.py', "# Appendix A: the rollout, as one fleet: 300 runners.\n")
        assert '[double-colon]' not in r.stdout

    def test_letterless_duplicate_candidates_do_not_crash(self, tmp_path):
        cyrillic = "Это очень важный пункт для всех наших пользователей сегодня."
        numeric = "10 20 30 40 50 60 70 80."
        body = f"{cyrillic}\n\n{cyrillic}\n\n{numeric}\n\n{numeric}\n"
        r = self._run(tmp_path, '.md', body)
        assert r.returncode == 0
        assert 'Traceback' not in r.stderr


class TestDuplicateClaim:
    PIN = "All timing figures are from the nightly run on commit 4f2a9c1."

    def test_flags_repeat_on_later_line(self):
        text = f"{self.PIN}\n\nOther text sits here.\n\n{self.PIN}\n"
        hits = _hits(text, 'duplicate-claim')
        assert [(h['line'], h['text'], h['severity']) for h in hits] == [
            (5, 'repeats line 1', 'MEDIUM')]

    def test_near_verbatim_repeat(self):
        text = ("All line references in this issue are against main at commit b47d028.\n\n"
                "All line references in this section are against main at commit b47d028.\n")
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_case_and_spacing_ignored(self):
        text = f"{self.PIN}\n\n{self.PIN.upper().replace(' ', '  ')}\n"
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_short_repeat_clean(self):
        assert not _hits("See Appendix A for details.\n\nSee Appendix A for details.\n",
                         'duplicate-claim')

    def test_paraphrase_clean(self):
        text = ("The schema has no field for the executor of an assessment.\n\n"
                "No assessment records who executed it, because the schema lacks a field.\n")
        assert not _hits(text, 'duplicate-claim')

    def test_each_later_copy_points_at_first(self):
        text = f"{self.PIN}\n\n{self.PIN}\n\n{self.PIN}\n"
        assert [h['text'] for h in _hits(text, 'duplicate-claim')] == [
            'repeats line 1', 'repeats line 1']

    def test_masked_comment_repeat_not_flagged(self):
        # The comment text is real prose by word count, but it is someone
        # else's inline note, not a claim the writer repeated.
        para = "Short one. <!-- the quick brown fox jumps over the lazy dog again -->"
        text = f"{para}\n\nOther text sits here.\n\n{para}\n"
        assert not _hits(text, 'duplicate-claim')

    def test_different_numbers_not_flagged(self):
        text = ("The p95 latency was 120 ms for the first eight runs in total.\n\n"
                "The p95 latency was 180 ms for the first eight runs in total.\n")
        assert not _hits(text, 'duplicate-claim')

    def test_inline_code_identifiers_count_toward_duplicate(self):
        # 6 plain words plus 3 inline-code identifiers: the identifiers
        # are the claim here, not incidental formatting to discard.
        sent = "The system reads config values `alpha` `beta` `gamma` today."
        text = f"{sent}\n\nOther text sits here.\n\n{sent}\n"
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_inflected_near_duplicate_flagged(self):
        # char ratio 0.98, but only singular/plural inflection differs:
        # word-set overlap is 0.727, below the old 0.8 gate.
        text = ("The runner caches the compiled object for each branch in the shared store.\n\n"
                "The runners cache the compiled objects for each branch in the shared store.\n")
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_comma_variant_near_duplicate_flagged(self):
        # Same words, one copy comma-heavy: whitespace-split word sets
        # disagree on every comma-suffixed token even though the words
        # themselves match.
        text = ("The pipeline validates configs, checks credentials, verifies quotas, "
                "and confirms access before every deploy.\n\n"
                "The pipeline validates configs checks credentials verifies quotas "
                "and confirms access before every deploy.\n")
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_cyrillic_duplicate_flagged(self):
        # _word_re is [a-z]-only, so a Cyrillic sentence produced an empty
        # word set on both sides of the gate and crashed on the divide.
        sent = "Это очень важный пункт для всех наших пользователей сегодня."
        text = f"{sent}\n\n{sent}\n"
        assert len(_hits(text, 'duplicate-claim')) == 1

    def test_numeric_only_duplicate_flagged(self):
        # Same crash, different cause: [a-z] does not match digits either.
        sent = "10 20 30 40 50 60 70 80."
        text = f"{sent}\n\n{sent}\n"
        assert len(_hits(text, 'duplicate-claim')) == 1


class TestDuplicateClaimPerfGate:
    def test_gate_skips_difflib_for_low_overlap_pair(self, monkeypatch):
        # An anagram-like pair: same shape as the pathological case (equal
        # length, no shared words). The word-overlap gate must reject it
        # before any SequenceMatcher is built, not just score it low.
        calls = []
        real_matcher = pre_scan.difflib.SequenceMatcher

        def spy(*args, **kwargs):
            calls.append(args)
            return real_matcher(*args, **kwargs)

        monkeypatch.setattr(pre_scan.difflib, 'SequenceMatcher', spy)
        text = ("Eight distinct running words fill this entire clause today.\n\n"
                "Zero matching letters build another unrelated statement here.\n")
        assert not _hits(text, 'duplicate-claim')
        assert calls == []


class TestMirroredAntithesis:
    def _flagged(self, text):
        return [(h['line'], h['severity']) for h in _hits(text, 'mirrored-antithesis')]

    def test_flags_parallel_pair(self):
        text = ("The build cache can store compiled objects for every branch. "
                "It cannot store the flags each object was built with.\n")
        assert self._flagged(text) == [(1, 'MEDIUM')]

    def test_flags_negated_first_half(self):
        text = "I don't think the parser needs a rewrite. It needs one more rule.\n"
        assert self._flagged(text) == [(1, 'MEDIUM')]

    def test_flags_curly_apostrophe(self):
        text = "The parser can validate headers. It doesn’t validate bodies.\n"
        assert len(self._flagged(text)) == 1

    def test_reports_line_of_first_sentence(self):
        text = "Intro.\n\nThe cache can store objects.\nIt cannot store flags.\n"
        assert self._flagged(text) == [(3, 'MEDIUM')]

    def test_both_negated_clean(self):
        assert not self._flagged("The log does not record the executor. It does not record the method.\n")

    def test_demonstrative_opener_clean(self):
        assert not self._flagged("There is no field for the method. This is the field auditors ask for.\n")

    def test_non_pronoun_opener_clean(self):
        assert not self._flagged("The cache can store objects. Nobody can store flags there.\n")

    def test_no_shared_word_clean(self):
        assert not self._flagged("The cache is warm today. It does not help the first request.\n")

    def test_lopsided_pair_clean(self):
        text = ("The log parses. It does not record which instance ran the check, how the "
                "evidence was obtained, or what share of the estate it covered.\n")
        assert not self._flagged(text)

    def test_long_sentence_clean(self):
        long_half = "It cannot store " + " ".join(["flags"] * 25) + "."
        assert not self._flagged("The cache can store objects for every branch in the fleet. "
                                 + long_half + "\n")

    def test_across_paragraphs_clean(self):
        assert not self._flagged("The cache can store objects.\n\nIt cannot store flags.\n")

    def test_inline_code_does_not_create_shared_word(self):
        assert not self._flagged("The `cache` stores. It does not `cache` flags.\n")

    def test_abbreviation_keeps_sentence_whole(self):
        assert not self._flagged("Use a tool, e.g. It is not a toy tool.\n")

    def test_etc_before_capitalized_word_enables_antithesis(self):
        # Merged into one sentence (the old behavior), there was nothing
        # to pair for the antithesis check at all.
        text = ("The build cache can store objects, logs, etc. "
                "It cannot store objects after a restart.\n")
        assert len(self._flagged(text)) == 1


FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'prescan' / 'filler-excerpt.md'


def test_fixture_flags_exactly_the_planted_shapes():
    """Line 3 antithesis, line 9 double colon, line 23 repeat of line 19,
    line 13 verdict lead ("The cache is warm." then its evidence).

    Near-misses: line 7 (one colon), line 11 (colons inside inline code),
    and line 21 stay clean. Line 13 (a lopsided contrast) stays clean of
    mirrored-antithesis but is the verdict-lead hit above.
    """
    got = {(f['tag'], f['line']) for f in scan_sentences(FIXTURE.read_text())}
    assert got == {('mirrored-antithesis', 3), ('double-colon', 9), ('duplicate-claim', 23),
                   ('verdict-lead', 13)}


class TestVerdictLead:
    TAIL = ("The old job rebuilt every layer on each push. "
            "Pinning the base image let the runner reuse them.\n")

    def _flagged(self, text):
        return [(h['line'], h['text'], h['severity']) for h in _hits(text, 'verdict-lead')]

    def test_flags_verdict_opening_longer_paragraph(self):
        text = f"The fix is simple. {self.TAIL}"
        assert self._flagged(text) == [(1, 'The fix is simple', 'LOW')]

    def test_flags_deictic_comparative_opener(self):
        text = f"Intro line here.\n\nThis is harder than it looks. {self.TAIL}"
        assert [ln for ln, _, _ in self._flagged(text)] == [3]

    def test_flags_sentence_ending_with_colon(self):
        text = f"The catch is subtle:\n\n{self.TAIL}"
        assert self._flagged(text) == [(1, 'The catch is subtle:', 'LOW')]

    def test_flags_verdict_right_before_list(self):
        text = ("The cache warms on the first build. The rest is easy.\n"
                "\n- restore the layer\n- run the tests\n")
        assert [ln for ln, _, _ in self._flagged(text)] == [1]
        assert self._flagged(text)[0][1] == 'The rest is easy.'

    def test_flags_verdict_before_table_fence_and_quote(self):
        for block in ("| a | b |\n|---|---|\n| 1 | 2 |\n", "```\nmake all\n```\n",
                      "> quoted words\n"):
            text = f"The answer is dull.\n\n{block}"
            assert len(self._flagged(text)) == 1, block

    def test_text_truncated_to_80_chars(self):
        # Twelve long words: short by word count, long by characters.
        sent = ("The internationalization ramifications are "
                "extraordinarily counterproductive, unquestionably disproportionate, "
                "overwhelmingly")
        (_, text, _), = self._flagged(f"{sent}. {self.TAIL}")
        assert text == sent[:80]

    def test_number_is_concrete(self):
        assert not self._flagged(f"The cache holds 40 GB. {self.TAIL}")

    def test_code_span_is_concrete(self):
        assert not self._flagged(f"The `cache` is small. {self.TAIL}")

    def test_proper_noun_is_concrete(self):
        assert not self._flagged(f"Postgres is slower here. {self.TAIL}")
        assert not self._flagged(f"This is slower than Postgres. {self.TAIL}")

    def test_pronoun_i_is_not_a_proper_noun(self):
        assert self._flagged(f"This is harder than I thought. {self.TAIL}")

    def test_link_and_quotes_are_concrete(self):
        assert not self._flagged(f"This is [the fix](x.md) we need. {self.TAIL}")
        assert not self._flagged(f'This is the "fast" path. {self.TAIL}')

    def test_single_sentence_paragraph_with_nothing_after(self):
        assert not self._flagged("The fix is simple.\n")
        assert not self._flagged("The fix is simple.\n\nAnother paragraph follows here.\n")

    def test_long_sentence(self):
        text = ("The fix is simple once the runner keeps its build cache between "
                f"jobs on the same branch. {self.TAIL}")
        assert not self._flagged(text)

    def test_question(self):
        assert not self._flagged(f"Is the fix simple? {self.TAIL}")
        assert not self._flagged("Why is this slow?\n\n- the cache is cold\n")

    def test_concrete_instruction(self):
        assert not self._flagged(f"Run the migration first. {self.TAIL}")

    def test_verdict_mid_paragraph(self):
        text = ("The old job rebuilt every layer on each push. The fix is simple. "
                "Pinning the base image let the runner reuse them.\n")
        assert not self._flagged(text)

    def test_last_sentence_before_prose_paragraph(self):
        text = f"The cache warms on the first run. The rest is easy.\n\n{self.TAIL}"
        assert not self._flagged(text)

    def test_heading_and_list_item_ignored(self):
        assert not self._flagged("# The fix is simple\n\nMore words here. And here.\n")
        assert not self._flagged("- The fix is simple. It pins the image.\n")

    def test_list_item_continuation_ignored(self):
        # The walker keeps an item's wrapped or loose continuation lines as
        # prose; they are still list content.
        assert not self._flagged("- The first item wraps onto\n  the next line. The rest is easy.\n\n"
                                 "- second item\n")
        assert not self._flagged("1. Step one.\n\n   The fix is simple. It pins the image.\n")

    def test_copula_without_verdict_shape_clean(self):
        # A copula followed by a noun phrase with no adjective, comparative,
        # or negation, and no deictic or "the X is" opener.
        assert not self._flagged("Caching is a trade. Warm caching saves time.\n")

    def test_copula_with_negation_flagged(self):
        tail = "Each warm caching layer costs disk. Cold runners pay twice.\n"
        assert self._flagged(f"Caching isn't free. {tail}")
        assert self._flagged(f"Caching is not a fix. {tail}")

    def test_unknown_capitalized_first_word_is_a_name(self):
        # Case cannot tell "Rollbacks" from "Postgres" at sentence start.
        # A first word the document never uses in lowercase reads as a name.
        assert not self._flagged(f"Rollbacks are rare. {self.TAIL}")
        assert self._flagged(f"Rollbacks are rare. Most rollbacks follow a bad image. {self.TAIL}")

    def test_name_used_lowercase_only_in_code_or_url_stays_a_name(self):
        claim = f"Postgres is slower here. {self.TAIL}"
        assert not self._flagged(f"{claim}\n```\ndocker run postgres\n```\n")
        assert not self._flagged(f"{claim}\nSee [the site](https://postgres.org) first.\n")
        assert not self._flagged(f"{claim}\nSee https://postgres.org first.\n")

    def test_copula_after_subordinator_does_not_count(self):
        assert not self._flagged("When it's done, it puts the connection back. "
                                 f"{self.TAIL}")
        assert not self._flagged(f"No section comments unless the file is large. {self.TAIL}")

    def test_copula_before_subordinator_counts(self):
        assert self._flagged(f"The build is slow when the cache is cold. {self.TAIL}")
        tail = "Warm caching layers help. Cold runners pay twice.\n"
        assert self._flagged(f"Caching is slow when disks are full. {tail}")

    def test_first_person_and_contracted_copulas(self):
        assert self._flagged(f"I am wary of this change. {self.TAIL}")
        assert self._flagged(f"I'm not convinced. {self.TAIL}")
        assert self._flagged(f"We're not done yet. {self.TAIL}")
        assert self._flagged(f"That's the whole trick. {self.TAIL}")

    def test_the_x_is_progressive_or_passive_clean(self):
        assert not self._flagged(f"The job is running. {self.TAIL}")
        assert not self._flagged(f"The image is pinned. {self.TAIL}")

    def test_spelled_out_number_is_concrete(self):
        assert self._flagged(f"The images are slow. {self.TAIL}")
        assert not self._flagged(f"The twelve images are slow. {self.TAIL}")
        assert not self._flagged(f"The hundred builds are slow. {self.TAIL}")

    def test_comparative_needs_a_real_comparative(self):
        # "other than" and "rather than" are not comparisons of degree.
        tail = "Caching needs disks. Warm caching helps.\n"
        assert not self._flagged(f"Caching is a step other than a fix. {tail}")
        assert self._flagged(f"Caching is a step cheaper than a fix. {tail}")

    def test_verdict_before_indented_code_block(self):
        assert self._flagged("The answer is dull.\n\n    make all\n")

    def test_indented_top_level_paragraph_scanned(self):
        assert self._flagged(f"  The fix is simple. {self.TAIL}")
        # One space is short of the item's 2-column content offset, so
        # after the blank line this paragraph is back at top level.
        assert self._flagged(f"- item one\n\n The fix is simple. {self.TAIL}")

    def test_details_body_scanned(self):
        text = f"<details>\n<summary>Why</summary>\n\nThe fix is simple. {self.TAIL}\n</details>\n"
        assert self._flagged(text)

    def test_lazy_and_nested_list_continuations_ignored(self):
        assert not self._flagged(f"- item one\nThe fix is simple. {self.TAIL}")
        assert not self._flagged(f"- item\n  - nested\n\n    The fix is simple. {self.TAIL}")
        assert not self._flagged(f"- item\n\n  para one here.\n\n  The fix is simple. {self.TAIL}")

    def test_outer_item_continuation_after_nested_list_ignored(self):
        text = f"1. Outer item.\n   - sub a\n   - sub b\n\n   The fix is simple. {self.TAIL}"
        assert not self._flagged(text)
        assert self._flagged(f"1. Outer item.\n   - sub a\n\nThe fix is simple. {self.TAIL}")

    def test_one_is_not_a_count(self):
        assert self._flagged(f"This one is better. {self.TAIL}")
        assert self._flagged(f"The one catch is subtle. {self.TAIL}")

    def test_preposition_before_copula_does_not_end_main_clause(self):
        assert self._flagged(f"The cost before caching is high. {self.TAIL}")
        assert not self._flagged(f"When it's done, it puts the connection back. {self.TAIL}")

    def test_evaluative_participles_still_flag(self):
        tail = "Every page repeats the old flag names. Nobody updated them.\n"
        assert self._flagged(f"The docs are confusing. {tail}")
        assert self._flagged(f"The result is misleading. {tail}")
        assert not self._flagged(f"The job is running. {tail}")

    def test_tab_after_list_marker_counts_in_columns(self):
        # "-\t" puts the item's content at column 5 (a tab counts as 4),
        # so a 2-space line after a blank line is back at top level.
        assert self._flagged(f"-\titem\n\n  The fix is simple. {self.TAIL}")

    def test_existential_opener_flagged(self):
        assert self._flagged(f"There's a catch. {self.TAIL}")
        assert self._flagged(f"Here’s the problem. {self.TAIL}")


class TestClaimEcho:
    A = "The runner caches compiled objects between builds on the same branch."
    B = "Compiled objects are cached by the runner between branch builds."

    def _flagged(self, text):
        return [(h['line'], h['text'], h['severity']) for h in _hits(text, 'claim-echo')]

    def test_stems_strip_one_suffix_and_a_final_e(self):
        got = pre_scan._echo_stems("caches cache cached caching files file quickly the is ok")
        assert got == {'cach', 'fil', 'quick'}

    def test_word_families_share_one_stem(self):
        families = [('class', 'classes'), ('process', 'processes'), ('status', 'statuses'),
                    ('use', 'uses', 'used', 'using'), ('run', 'runs', 'running'),
                    ('stop', 'stops', 'stopped'), ('release', 'releases', 'released', 'releasing'),
                    ('need', 'needs')]
        for family in families:
            stems = {pre_scan._echo_stems(w) for w in family}
            assert len(stems) == 1 and all(stems), family

    def test_ly_stripped_only_from_adverbs(self):
        words = "early apply family supply reply rely fly ugly"
        assert pre_scan._echo_stems(words) == set(words.split())
        assert pre_scan._echo_stems("quickly really") == {'quick', 'real'}

    def test_ee_and_ias_families_share_one_stem(self):
        for family in (('agree', 'agrees', 'agreed', 'agreeing'), ('free', 'frees', 'freed'),
                       ('need', 'needs', 'needed'), ('bias', 'biases', 'biased'),
                       ('alias', 'aliases')):
            stems = {pre_scan._echo_stems(w) for w in family}
            assert len(stems) == 1 and all(stems), family

    def test_short_stems_kept_whole(self):
        # No vowel or too little left: "string" is not "str" + "ing".
        assert pre_scan._echo_stems("string thing bring king yes gas") == {
            'string', 'thing', 'bring', 'king', 'yes', 'gas'}

    def test_flags_echo_across_sections(self):
        text = f"# Caching\n\n{self.A}\n\n## Summary\n\n{self.B}\n"
        assert self._flagged(text) == [(7, 'echoes line 3', 'LOW')]

    def test_flags_echo_across_details_summary(self):
        text = (f"# Caching\n\n{self.A}\n\n<details>\n<summary>Why builds stay fast</summary>\n\n"
                f"{self.B}\n\n</details>\n")
        assert self._flagged(text) == [(8, 'echoes line 3', 'LOW')]

    def test_flags_echo_across_one_line_details_summary(self):
        text = (f"# Caching\n\n{self.A}\n\n<details><summary>Why builds stay fast</summary>\n\n"
                f"{self.B}\n\n</details>\n")
        assert self._flagged(text) == [(7, 'echoes line 3', 'LOW')]

    def test_flags_cyrillic_echo(self):
        a = "Кэш сборки хранит скомпилированные объекты для каждой ветки проекта."
        b = "Для каждой ветки проекта кэш сборки хранит скомпилированные объекты."
        text = f"# Кэш\n\n{a}\n\n# Итог\n\n{b}\n"
        assert self._flagged(text) == [(7, 'echoes line 3', 'LOW')]
        assert not _hits(text, 'duplicate-claim')

    def test_reports_first_earlier_match(self):
        a2 = self.A.replace('same', 'current')
        text = f"# One\n\n{self.A}\n\n# Two\n\n{a2}\n\n# Three\n\n{self.B}\n"
        assert self._flagged(text)[-1] == (11, 'echoes line 3', 'LOW')

    def test_same_section_not_flagged(self):
        text = f"# Caching\n\n{self.A}\n\nOther words sit here.\n\n{self.B}\n"
        assert not self._flagged(text)

    def test_near_verbatim_repeat_is_only_duplicate_claim(self):
        text = f"# One\n\n{self.A}\n\n# Two\n\n{self.A}\n"
        assert len(_hits(text, 'duplicate-claim')) == 1
        assert not self._flagged(text)

    def test_under_six_content_words_not_flagged(self):
        text = ("# One\n\nThe runner caches compiled objects.\n\n"
                "# Two\n\nCompiled objects are cached by the runner.\n")
        assert not self._flagged(text)

    def test_unrelated_pair_sharing_two_words_not_flagged(self):
        text = ("# One\n\nThe runner caches compiled objects for nightly release pipelines.\n\n"
                "# Two\n\nEvery database migration locks tables while the runner caches schemas.\n")
        assert not self._flagged(text)

    def test_list_item_continuation_ignored(self):
        text = f"# Caching\n\n{self.A}\n\n## Summary\n\n- Short item\n  {self.B}\n"
        assert not self._flagged(text)

    def test_heading_inside_fence_does_not_open_section(self):
        text = f"# Caching\n\n{self.A}\n\n```\n# not a heading\n```\n\n{self.B}\n"
        assert not self._flagged(text)


class _Touches:
    count = 0


class _CountingList:
    """A read-only view of a list that counts every element it hands out."""

    def __init__(self, items, touches):
        self.items = items
        self.touches = touches

    def __getitem__(self, j):
        self.touches.count += 1
        return self.items[j]

    def __iter__(self):
        for item in self.items:
            self.touches.count += 1
            yield item

    def __len__(self):
        return len(self.items)


class _CountingIndex:
    """A read-only view of the stem index whose posting lists count reads."""

    def __init__(self, index, touches):
        self.index = index
        self.touches = touches

    def get(self, key, default=()):
        return _CountingList(self.index.get(key, default), self.touches)


class TestClaimEchoScaling:
    def test_echo_lookup_reads_stay_under_three_eighths_of_n_squared(self, monkeypatch):
        # A small shared vocabulary gives every stem a long posting list:
        # a hard case for the word index. Comparing each sentence with
        # every earlier one touches n*(n-1)/2 entries. The count covers
        # posting-list reads and `earlier` reads alike. ECHO_MIN_SHARED
        # caps the Jaccard computations, not this index traffic, which
        # still grows with n*n/|vocabulary| on input this dense.
        rng = random.Random(7)
        vocab = [f"{a}{b}" for a in ('cach', 'build', 'queu', 'index', 'shard', 'lock', 'pipe',
                                     'deploy', 'stag', 'tabl', 'row', 'job', 'lint', 'test')
                 for b in ('er', 'ment', 'ion', 'ity', 'ness', 'ward', 'ful', 'ist',
                           'ure', 'ism', 'ance', 'ology')]
        parts = []
        for sec in range(40):
            parts.append(f"## Section {sec}\n")
            for _ in range(50):
                parts.append(' '.join(rng.choice(vocab) for _ in range(10)).capitalize() + '.\n')
        real_echo_of = pre_scan._echo_of
        touches = _Touches()
        calls = []

        def counting_echo_of(stems, section, earlier, index):
            calls.append(1)
            return real_echo_of(stems, section, _CountingList(earlier, touches),
                                _CountingIndex(index, touches))

        monkeypatch.setattr(pre_scan, '_echo_of', counting_echo_of)
        scan_sentences('\n'.join(parts))
        n = len(calls)
        assert n > 1900
        # 3/8 of n*n: the index measures about 0.28 n*n here; a scan of
        # every earlier sentence measures about 0.5 n*n and fails.
        assert touches.count < 3 * n * n // 8
