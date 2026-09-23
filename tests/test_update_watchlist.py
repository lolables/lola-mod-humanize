"""Unit tests for update-watchlist.py"""
from __future__ import annotations

import textwrap
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from conftest import update_watchlist

parse_candidates = update_watchlist.parse_candidates
add_to_watchlist_md = update_watchlist.add_to_watchlist_md
interactive_review = update_watchlist.interactive_review
main = update_watchlist.main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_WATCHLIST_MD = textwrap.dedent("""\
    ## Tier 1: Strongest Indicators

    | Word/Phrase | Ban | Replacement Strategy |
    |---|---|---|
    | delve | yes | explore |

    ## Tier 2: Strong Indicators

    | Word/Phrase | Ban | Replacement Strategy |
    |---|---|---|
    | bolstered |  | strengthened |

    ## Tier 3: Moderate Indicators

    | Word/Phrase | Ban | Replacement Strategy |
    |---|---|---|
    | crucial |  | important |
""")

REPORT_WITH_CANDIDATES = textwrap.dedent("""\
    # Update Report

    ## Summary

    Some analysis text here.

    ## Potential new watchlist candidates

    | Word | Occurrences |
    |---|---|
    | synergy | 15 |
    | paradigm | 8 |
    | holistic | 3 |

    Some trailing text after the table.
""")


def make_report(tmp_path: Path, content: str) -> Path:
    p = tmp_path / 'update-report.md'
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# TestParseCandidates
# ---------------------------------------------------------------------------

class TestParseCandidates:
    def test_parses_well_formed_table(self, tmp_path):
        report = make_report(tmp_path, REPORT_WITH_CANDIDATES)
        candidates = parse_candidates(report)
        assert candidates == [('synergy', 15), ('paradigm', 8), ('holistic', 3)]

    def test_returns_empty_list_when_no_candidates_section(self, tmp_path):
        report = make_report(tmp_path, '# Report\n\nNo candidates here.\n')
        candidates = parse_candidates(report)
        assert candidates == []

    def test_non_numeric_count_falls_back_to_zero(self, tmp_path):
        content = textwrap.dedent("""\
            ## Potential new watchlist candidates

            | Word | Occurrences |
            |---|---|
            | endeavor | many |
        """)
        report = make_report(tmp_path, content)
        candidates = parse_candidates(report)
        assert candidates == [('endeavor', 0)]

    def test_stops_at_non_pipe_non_empty_non_heading_line(self, tmp_path):
        content = textwrap.dedent("""\
            ## Potential new watchlist candidates

            | Word | Occurrences |
            |---|---|
            | leverage | 5 |

            This line ends the table.

            | Word | Occurrences |
            |---|---|
            | spurious | 99 |
        """)
        report = make_report(tmp_path, content)
        candidates = parse_candidates(report)
        # Only the first row before the blank-then-text break should be returned
        assert candidates == [('leverage', 5)]

    def test_exits_when_report_file_missing(self, tmp_path):
        missing = tmp_path / 'no-such-file.md'
        with pytest.raises(SystemExit) as exc_info:
            parse_candidates(missing)
        assert exc_info.value.code == 1

    def test_exits_writes_hint_to_stderr(self, tmp_path, capsys):
        missing = tmp_path / 'no-such-file.md'
        with pytest.raises(SystemExit):
            parse_candidates(missing)
        err = capsys.readouterr().err
        assert 'update-sources' in err

    def test_parses_table_with_prose_line_before_it(self, tmp_path):
        # Real reports put an explanatory sentence between the header and the
        # table; the parser must not stop on it. Regression for the bug where
        # parse_candidates returned [] against actual gather output.
        content = textwrap.dedent("""\
            ### Potential new watchlist candidates

            Words matching AI-vocabulary patterns found in sources but NOT in current watchlist:

            | Word | Occurrences | Action needed |
            |------|-------------|---------------|
            | seamless | 8 | Review for inclusion |
            | showcase | 5 | Review for inclusion |

            ### Context-extracted candidates
        """)
        report = make_report(tmp_path, content)
        candidates = parse_candidates(report)
        assert candidates == [('seamless', 8), ('showcase', 5)]


# ---------------------------------------------------------------------------
# TestAddToWatchlistMd
# ---------------------------------------------------------------------------

class TestAddToWatchlistMd:
    def test_adds_word_to_tier1_section(self, tmp_path):
        wl = tmp_path / 'ai-vocabulary-watchlist.md'
        wl.write_text(MINIMAL_WATCHLIST_MD)
        with patch.object(update_watchlist, 'WATCHLIST_MD', wl):
            result = add_to_watchlist_md('nascent', 1)
        assert result is True
        content = wl.read_text()
        assert '| nascent | yes | (review: suggest replacements) |' in content
        # Confirm it appears before Tier 2 section
        tier1_idx = content.index('Tier 1:')
        tier2_idx = content.index('Tier 2:')
        word_idx = content.index('| nascent |')
        assert tier1_idx < word_idx < tier2_idx

    def test_adds_word_to_tier2_section(self, tmp_path):
        wl = tmp_path / 'ai-vocabulary-watchlist.md'
        wl.write_text(MINIMAL_WATCHLIST_MD)
        with patch.object(update_watchlist, 'WATCHLIST_MD', wl):
            result = add_to_watchlist_md('salient', 2)
        assert result is True
        content = wl.read_text()
        assert '| salient |  | (review: suggest replacements) |' in content
        tier2_idx = content.index('Tier 2:')
        tier3_idx = content.index('Tier 3:')
        word_idx = content.index('| salient |')
        assert tier2_idx < word_idx < tier3_idx

    def test_returns_false_for_unsupported_tier(self, tmp_path):
        wl = tmp_path / 'ai-vocabulary-watchlist.md'
        wl.write_text(MINIMAL_WATCHLIST_MD)
        with patch.object(update_watchlist, 'WATCHLIST_MD', wl):
            assert add_to_watchlist_md('word', 4) is False
            assert add_to_watchlist_md('word', 5) is False

    def test_returns_false_when_no_table_rows_in_section(self, tmp_path):
        # Tier section exists but has only a header row and separator, no data rows
        content = textwrap.dedent("""\
            ## Tier 1: Strongest Indicators

            | Word/Phrase | Ban | Replacement Strategy |
            |---|---|---|

            ## Tier 2: Strong Indicators

            | Word/Phrase | Ban | Replacement Strategy |
            |---|---|---|
            | bolstered |  | strengthened |
        """)
        wl = tmp_path / 'ai-vocabulary-watchlist.md'
        wl.write_text(content)
        with patch.object(update_watchlist, 'WATCHLIST_MD', wl):
            result = add_to_watchlist_md('nascent', 1)
        # No data rows found in Tier 1, so insert_idx stays None
        assert result is False


# ---------------------------------------------------------------------------
# TestInteractiveReview
# ---------------------------------------------------------------------------

class TestInteractiveReview:
    def test_prints_message_and_returns_when_no_candidates(self, capsys):
        interactive_review([])
        out = capsys.readouterr().out
        assert 'No new vocabulary candidates found.' in out

    def test_skip_all_candidates(self, capsys):
        candidates = [('synergy', 15), ('paradigm', 8)]
        with patch('builtins.input', side_effect=['s', 's']):
            interactive_review(candidates)
        out = capsys.readouterr().out
        assert 'Added 0, skipped 2' in out

    def test_add_candidates_to_tiers(self, capsys):
        candidates = [('synergy', 15), ('paradigm', 8), ('holistic', 3)]
        with patch('builtins.input', side_effect=['1', 's', '2']), \
             patch.object(update_watchlist, 'add_to_watchlist_md', return_value=True) as mock_md:
            interactive_review(candidates)
        out = capsys.readouterr().out
        assert 'Added 2, skipped 1' in out
        mock_md.assert_any_call('synergy', 1)
        mock_md.assert_any_call('holistic', 2)

    def test_quit_stops_early(self, capsys):
        candidates = [('synergy', 15), ('paradigm', 8), ('holistic', 3)]
        with patch('builtins.input', side_effect=['s', 'q']):
            interactive_review(candidates)
        out = capsys.readouterr().out
        assert 'Stopped' in out
        assert 'Added 0, skipped 1' in out

    def test_invalid_input_reprompts(self, capsys):
        candidates = [('synergy', 15)]
        with patch('builtins.input', side_effect=['x', 'bad', 's']):
            interactive_review(candidates)
        out = capsys.readouterr().out
        assert out.count('Invalid choice') == 2
        assert 'Added 0, skipped 1' in out

    def test_add_failure_prints_error(self, capsys):
        candidates = [('synergy', 15)]
        with patch('builtins.input', side_effect=['1']), \
             patch.object(update_watchlist, 'add_to_watchlist_md', return_value=False):
            interactive_review(candidates)
        out, err = capsys.readouterr()
        assert 'Could not add' in err
        assert 'Added 0, skipped 0' in out

    def test_added_nonzero_prints_sync_hint(self, capsys):
        candidates = [('synergy', 15)]
        with patch('builtins.input', side_effect=['1']), \
             patch.object(update_watchlist, 'add_to_watchlist_md', return_value=True):
            interactive_review(candidates)
        out = capsys.readouterr().out
        assert 'task vocab:sync' in out


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_auto_mode_prints_candidates(self, tmp_path, capsys):
        report = make_report(tmp_path, REPORT_WITH_CANDIDATES)
        with patch('sys.argv', ['update-watchlist', '--report', str(report), '--auto']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert '3 candidates:' in out
        assert 'synergy (15)' in out

    def test_auto_mode_no_candidates(self, tmp_path, capsys):
        report = make_report(tmp_path, '# Report\n\nNo candidates.\n')
        with patch('sys.argv', ['update-watchlist', '--report', str(report), '--auto']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert 'No new vocabulary candidates.' in out

    def test_interactive_mode_calls_review(self, tmp_path):
        report = make_report(tmp_path, REPORT_WITH_CANDIDATES)
        with patch('sys.argv', ['update-watchlist', '--report', str(report)]), \
             patch.object(update_watchlist, 'interactive_review') as mock_review:
            main()
        mock_review.assert_called_once()
        args = mock_review.call_args[0][0]
        assert len(args) == 3
        assert args[0] == ('synergy', 15)

    def test_missing_report_exits_with_error(self, tmp_path):
        missing = tmp_path / 'no-such-file.md'
        with patch('sys.argv', ['update-watchlist', '--report', str(missing)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
