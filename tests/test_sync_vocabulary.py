"""test_sync_vocabulary.py -- Unit tests for the watchlist sync generator."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'scripts'))

import sync_vocabulary as sv

SAMPLE = """\
# Watchlist

## Tier 1: Strongest

| Word/Phrase | Ban | Replacement Strategy |
|---|---|---|
| delve (into) | yes | explore, examine |
| meticulous/meticulously | yes | careful, precise |
| highlight |  | show, point out |

## Tier 4: Phrase-Level Patterns

| Phrase | Ban | Match | Replacement Strategy |
|---|---|---|---|
| in the heart of | yes |  | in / at the center of |
| plays a [vital/key] role | yes | plays a vital role, plays a key role | matters |
| Despite its [positive], faces challenges | regex |  | [integrate specifics] |

## Tier 5: Discourse Markers

| Pattern | Ban | Role | Match | When to Flag |
|---|---|---|---|---|
| In conclusion | yes | closer |  | Almost always |
| In this [article/section] |  | closer | in this article, in this section | Delete |
| In an era of |  | opener |  | Delete |
| It is worth noting | yes |  |  | Delete |

---

## Sources

| Source | Note |
|---|---|
| Kobak et al. | frequency analysis |
"""


def test_parses_rows_with_tier_numbers():
    rows = sv.parse_watchlist(SAMPLE)
    assert [r.tier for r in rows] == [1, 1, 1, 4, 4, 4, 5, 5, 5, 5]


def test_skips_header_and_separator_rows():
    rows = sv.parse_watchlist(SAMPLE)
    assert 'Word/Phrase' not in [r.term for r in rows]
    assert not any(set(r.term) <= {'-', ':'} for r in rows)


def test_reads_ban_match_and_role_by_header_name():
    rows = sv.parse_watchlist(SAMPLE)
    delve = rows[0]
    assert (delve.term, delve.ban, delve.match, delve.role) == ('delve (into)', 'yes', '', '')
    plays = rows[4]
    assert plays.match == 'plays a vital role, plays a key role'
    conclusion = rows[6]
    assert (conclusion.role, conclusion.ban) == ('closer', 'yes')


def test_blank_ban_cell_is_empty_string():
    rows = sv.parse_watchlist(SAMPLE)
    assert rows[2].ban == ''


def test_ban_and_role_are_lowercased():
    rows = sv.parse_watchlist('## Tier 1: X\n\n| Word/Phrase | Ban | Replacement Strategy |\n|---|---|---|\n| x | YES | y |\n')
    assert rows[0].ban == 'yes'


def test_ignores_content_after_non_tier_heading():
    rows = sv.parse_watchlist(SAMPLE)
    assert [r.tier for r in rows] == [1, 1, 1, 4, 4, 4, 5, 5, 5, 5]
    terms = [r.term for r in rows]
    assert 'Source' not in terms
    assert 'Kobak et al.' not in terms


def test_short_row_raises_watchlist_error():
    text = (
        '## Tier 5: Discourse Markers\n\n'
        '| Pattern | Role | Match | When to Flag |\n'
        '|---|---|---|---|\n'
        '| In conclusion | closer | Almost always |\n'
    )
    with pytest.raises(sv.WatchlistError):
        sv.parse_watchlist(text)


def test_long_row_raises_watchlist_error():
    text = (
        '## Tier 1: X\n\n'
        '| Word/Phrase | Ban | Replacement Strategy |\n'
        '|---|---|---|\n'
        '| x | yes | y | extra |\n'
    )
    with pytest.raises(sv.WatchlistError):
        sv.parse_watchlist(text)


def test_header_only_table_yields_no_rows():
    text = (
        '## Tier 1: X\n\n'
        '| Word/Phrase | Ban | Replacement Strategy |\n'
        '|---|---|---|\n'
    )
    assert sv.parse_watchlist(text) == []


def test_table_before_any_tier_heading_is_ignored():
    text = (
        '# Watchlist\n\n'
        '| Word/Phrase | Ban | Replacement Strategy |\n'
        '|---|---|---|\n'
        '| x | yes | y |\n\n'
        '## Tier 1: X\n\n'
        '| Word/Phrase | Ban | Replacement Strategy |\n'
        '|---|---|---|\n'
        '| z | yes | w |\n'
    )
    rows = sv.parse_watchlist(text)
    assert [r.term for r in rows] == ['z']


def test_dash_only_data_row_is_not_mistaken_for_separator():
    text = (
        '## Tier 1: X\n\n'
        '| Word/Phrase | Ban |\n'
        '|---|---|\n'
        '| - | - |\n'
    )
    rows = sv.parse_watchlist(text)
    assert [(r.term, r.ban) for r in rows] == [('-', '-')]


class TestTermAccessors:
    def test_variants_splits_slashes_and_strips_parens(self):
        assert sv.variants('meticulous/meticulously') == ['meticulous', 'meticulously']
        assert sv.variants('delve (into)') == ['delve']
        assert sv.variants('dive into/deep dive') == ['dive into', 'deep dive']

    def test_variants_lowercases(self):
        assert sv.variants('Additionally (sentence-start)') == ['additionally']

    def test_display_keeps_parenthetical_and_case(self):
        assert sv.display('landscape (figurative)') == 'landscape (figurative)'
        assert sv.display('meticulous/meticulously') == 'meticulous'

    def test_bare_drops_parenthetical_keeps_case(self):
        assert sv.bare('Additionally (sentence-start)') == 'Additionally'
        assert sv.bare('Furthermore') == 'Furthermore'

    def test_matches_uses_match_cell_when_present(self):
        row = sv.Row(tier=4, term='plays a [vital/key] role', ban='yes',
                     match='plays a vital role, plays a key role')
        assert sv.matches(row) == ['plays a vital role', 'plays a key role']

    def test_matches_falls_back_to_term_when_match_blank(self):
        row = sv.Row(tier=4, term='in the heart of', ban='yes')
        assert sv.matches(row) == ['in the heart of']

    def test_matches_strips_parens_before_splitting_on_comma(self):
        """The 'not only' row has a comma inside its parenthetical."""
        row = sv.Row(tier=4, term='not only (bare, and in "Not only X, but also Y")', ban='yes')
        assert sv.matches(row) == ['not only']


class TestDerive:
    @pytest.fixture
    def d(self):
        return sv.derive(sv.parse_watchlist(SAMPLE))

    def test_tier_words_expand_slash_variants_in_document_order(self, d):
        assert d.tier1 == ['delve', 'meticulous', 'meticulously', 'highlight']

    def test_prose_words_use_display_form_and_respect_ban(self, d):
        assert d.prose_words == ['delve (into)', 'meticulous']

    def test_banned_phrases_from_any_banned_row(self, d):
        assert d.banned_phrases == [
            'in the heart of', 'plays a vital role', 'plays a key role',
            'in conclusion', 'it is worth noting',
        ]

    def test_regex_ban_rows_are_skipped(self, d):
        assert not any('despite' in p for p in d.banned_phrases)

    def test_openers_and_closers_route_by_role(self, d):
        assert d.generic_openers == ['in an era of']
        assert d.generic_closers == ['in conclusion', 'in this article', 'in this section']

    def test_prose_phrases_use_readable_phrase_cell(self, d):
        assert d.prose_phrases == [
            'in the heart of', 'plays a [vital/key] role', 'In conclusion', 'It is worth noting',
        ]

    def test_a_row_can_be_both_banned_and_positional(self, d):
        """'In conclusion' must appear in BOTH banned_phrases and closers."""
        assert 'in conclusion' in d.banned_phrases
        assert 'in conclusion' in d.generic_closers

    def test_transitions_come_from_tier3_sentence_start_rows(self):
        text = (
            '## Tier 3: Moderate\n\n'
            '| Word/Phrase | Ban | Replacement Strategy |\n|---|---|---|\n'
            '| Additionally (sentence-start) |  | Also |\n'
            '| Furthermore (sentence-start) |  | [delete] |\n'
            '| crucial |  | important |\n'
        )
        d = sv.derive(sv.parse_watchlist(text))
        assert d.transition_starters == ['additionally,', 'furthermore,']
        assert d.prose_transitions == ['Additionally', 'Furthermore']
        assert d.tier3 == ['additionally', 'furthermore', 'crucial']

    def test_duplicate_variants_are_deduped_preserving_order(self):
        text = (
            '## Tier 1: S\n\n| Word/Phrase | Ban | Replacement Strategy |\n|---|---|---|\n'
            '| alpha | yes | a |\n| alpha | yes | b |\n| beta | yes | c |\n'
        )
        assert sv.derive(sv.parse_watchlist(text)).tier1 == ['alpha', 'beta']


class TestRenderers:
    def test_literal_prefers_single_quotes(self):
        assert sv.literal('delve') == "'delve'"

    def test_literal_uses_double_quotes_when_apostrophe_present(self):
        assert sv.literal("in today's") == '"in today\'s"'

    def test_render_py_set_wraps_and_indents(self):
        out = sv.render_py_set('TIER1_WORDS', ['alpha', 'beta'])
        assert out == "TIER1_WORDS: set[str] = {\n    'alpha', 'beta',\n}"

    def test_render_py_list_uses_list_type(self):
        out = sv.render_py_list('BANNED_PHRASES', ['not just'])
        assert out == "BANNED_PHRASES: list[str] = [\n    'not just',\n]"

    def test_render_py_set_wraps_at_76_columns(self):
        out = sv.render_py_set('T', [f'word{i:02d}' for i in range(20)])
        assert all(len(line) <= 76 for line in out.splitlines())
        assert out.count('\n') > 2

    def test_join_or_uses_oxford_or(self):
        assert sv.join_or(['A', 'B', 'C']) == 'A, B, or C'
        assert sv.join_or(['A', 'B']) == 'A, or B'
        assert sv.join_or(['A']) == 'A'

    def test_render_prose_agents_lead_ins(self):
        d = sv.derive(sv.parse_watchlist(SAMPLE))
        out = sv.render_prose('agents', d)
        assert out.startswith('Words -- never use: delve (into), meticulous.')
        assert 'Phrases -- never use: "in the heart of"' in out
        assert out.rstrip().endswith('.')

    def test_render_prose_skill_uses_its_own_lead_in(self):
        d = sv.derive(sv.parse_watchlist(SAMPLE))
        out = sv.render_prose('skill', d)
        assert out.startswith('Your transformed text must also follow these rules.')
        assert 'in your output: delve (into), meticulous.' in out

    def test_render_prose_wraps_at_76_columns(self):
        d = sv.derive(sv.parse_watchlist(SAMPLE))
        for target in ('agents', 'skill'):
            assert all(len(line) <= 76 for line in sv.render_prose(target, d).splitlines())

    def test_render_prose_omits_transition_sentence_when_none(self):
        """SAMPLE has no (sentence-start) rows, so that sentence must not appear."""
        d = sv.derive(sv.parse_watchlist(SAMPLE))
        assert 'Never open a sentence with' not in sv.render_prose('agents', d)

    def test_multi_word_literals_are_never_split(self):
        import ast
        items = ['dive into', 'deep dive', 'align with', 'resonate with',
                 'ever-evolving', 'commitment to excellence', 'plays a vital role',
                 'it is worth noting', 'this raises the question']
        out = sv.render_py_set('T', items)
        ast.parse(out)                       # must be valid Python
        assert all(len(line) <= 76 for line in out.splitlines())
        ns = {}
        exec(out.replace('T: set[str]', 'T'), ns)
        assert ns['T'] == set(items)         # every value survives intact

    def test_empty_set_renders_as_set_call(self):
        import ast
        out = sv.render_py_set('T', [])
        assert out == 'T: set[str] = set()'
        ast.parse(out)

    def test_empty_list_renders_as_empty_brackets(self):
        import ast
        out = sv.render_py_list('T', [])
        assert out == 'T: list[str] = []'
        ast.parse(out)

    def test_long_list_round_trips_through_exec(self):
        items = [f'phrase number {i}' for i in range(30)]
        out = sv.render_py_list('T', items)
        ns = {}
        exec(out.replace('T: list[str]', 'T'), ns)
        assert ns['T'] == items


class TestReplaceRegion:
    MD = ('intro\n\n<!-- BEGIN GENERATED: banned -->\nOLD\n'
          '<!-- END GENERATED: banned -->\n\noutro\n')
    PY = 'header\n# BEGIN GENERATED: tier-words\nOLD\n# END GENERATED: tier-words\nfooter\n'

    def test_replaces_markdown_region_body(self):
        out = sv.replace_region(self.MD, 'banned', 'NEW', 'md')
        assert 'NEW' in out and 'OLD' not in out

    def test_preserves_content_outside_markers(self):
        out = sv.replace_region(self.MD, 'banned', 'NEW', 'md')
        assert out.startswith('intro\n\n') and out.endswith('outro\n')

    def test_replaces_python_region_body(self):
        out = sv.replace_region(self.PY, 'tier-words', 'NEW', 'py')
        assert 'NEW' in out and 'OLD' not in out
        assert out.startswith('header\n') and out.endswith('footer\n')

    def test_is_idempotent(self):
        once = sv.replace_region(self.MD, 'banned', 'NEW', 'md')
        assert sv.replace_region(once, 'banned', 'NEW', 'md') == once

    def test_missing_begin_marker_raises(self):
        with pytest.raises(sv.MarkerError, match='banned'):
            sv.replace_region('no markers here\n', 'banned', 'NEW', 'md')

    def test_end_before_begin_raises(self):
        swapped = ('<!-- END GENERATED: banned -->\n'
                   '<!-- BEGIN GENERATED: banned -->\n')
        with pytest.raises(sv.MarkerError):
            sv.replace_region(swapped, 'banned', 'NEW', 'md')

    def test_multiline_body_round_trips(self):
        out = sv.replace_region(self.PY, 'tier-words', 'A\nB\nC', 'py')
        assert '# BEGIN GENERATED: tier-words\nA\nB\nC\n# END GENERATED' in out


class TestSyncTargets:
    def test_targets_cover_all_five_regions(self):
        """Structural only -- the real files gain their markers in Task 9."""
        assert [(t.path.name, t.marker) for t in sv.TARGETS] == [
            ('vocabulary.py', 'tier-words'),
            ('vocabulary.py', 'phrases'),
            ('AGENTS.md', 'banned'),
            ('writing-discipline.md', 'banned'),
            ('SKILL.md', 'banned'),
        ]

    def test_build_outputs_applies_both_regions_of_a_shared_file(self, tmp_path, monkeypatch):
        shared = tmp_path / 'shared.py'
        shared.write_text(
            '# BEGIN GENERATED: a\nOLD_A\n# END GENERATED: a\n'
            '# BEGIN GENERATED: b\nOLD_B\n# END GENERATED: b\n'
        )
        monkeypatch.setattr(sv, 'TARGETS', [
            sv.Target(shared, 'a', 'py', lambda d: 'NEW_A'),
            sv.Target(shared, 'b', 'py', lambda d: 'NEW_B'),
        ])
        outputs = sv.build_outputs(sv.derive(sv.parse_watchlist(SAMPLE)))
        assert set(outputs) == {shared}
        assert 'NEW_A' in outputs[shared] and 'NEW_B' in outputs[shared]

    def test_check_mode_returns_zero_when_current(self, tmp_path, monkeypatch):
        path = tmp_path / 'x.py'
        path.write_text('# BEGIN GENERATED: t\nBODY\n# END GENERATED: t\n')
        monkeypatch.setattr(sv, 'TARGETS', [sv.Target(path, 't', 'py', lambda d: 'BODY')])
        assert sv.run(check=True) == 0

    def test_check_mode_returns_one_and_diffs_when_stale(self, tmp_path, monkeypatch, capsys):
        path = tmp_path / 'x.py'
        path.write_text('# BEGIN GENERATED: t\nSTALE\n# END GENERATED: t\n')
        monkeypatch.setattr(sv, 'TARGETS', [sv.Target(path, 't', 'py', lambda d: 'FRESH')])
        assert sv.run(check=True) == 1
        out = capsys.readouterr().out
        assert 'FRESH' in out and 'STALE' in out

    def test_write_mode_updates_the_file(self, tmp_path, monkeypatch):
        path = tmp_path / 'x.py'
        path.write_text('# BEGIN GENERATED: t\nSTALE\n# END GENERATED: t\n')
        monkeypatch.setattr(sv, 'TARGETS', [sv.Target(path, 't', 'py', lambda d: 'FRESH')])
        assert sv.run(check=False) == 0
        assert 'FRESH' in path.read_text()

    def test_marker_error_returns_two(self, tmp_path, monkeypatch, capsys):
        path = tmp_path / 'x.py'
        path.write_text('no markers\n')
        monkeypatch.setattr(sv, 'TARGETS', [sv.Target(path, 't', 'py', lambda d: 'BODY')])
        assert sv.run(check=False) == 2
        assert 'marker' in capsys.readouterr().err.lower()

    def test_malformed_watchlist_returns_two(self, tmp_path, monkeypatch, capsys):
        """A row whose cell count disagrees with its header exits 2, not a traceback."""
        bad = tmp_path / 'bad.md'
        bad.write_text(
            '## Tier 1: X\n\n| Word/Phrase | Ban | Replacement Strategy |\n'
            '|---|---|---|\n| oops | yes |\n'
        )
        monkeypatch.setattr(sv, 'WATCHLIST', bad)
        monkeypatch.setattr(sv, 'TARGETS', [])
        assert sv.run(check=False) == 2
        assert 'cells' in capsys.readouterr().err.lower()


class TestPreScanImportsSharedLists:
    def test_pre_scan_no_longer_defines_openers_or_closers(self):
        src = (REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts' / 'pre-scan.py').read_text()
        assert 'GENERIC_OPENERS = [' not in src
        assert 'GENERIC_CLOSERS = [' not in src

    def test_vocabulary_exports_openers_and_closers(self):
        sys.path.insert(0, str(REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts'))
        import vocabulary
        assert 'in an era of' in vocabulary.GENERIC_OPENERS
        assert 'to summarize' in vocabulary.GENERIC_CLOSERS
