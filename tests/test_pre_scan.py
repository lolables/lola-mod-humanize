"""Tests for pre-scan.py checks 1-14."""
from conftest import pre_scan, hermetic_git_env

scan_text = pre_scan.scan_text


def _tags(findings: list[dict]) -> list[str]:
    return [f['tag'] for f in findings]


# -- Check 1: Tier 1 vocabulary --

class TestTier1:
    def test_finds_tier1_word(self):
        hits = scan_text("We must delve into the topic.\n", "test.md")
        assert any(f['tag'] == 'tier1' and f['text'].lower() == 'delve' for f in hits)

    def test_tier1_case_insensitive(self):
        hits = scan_text("The TAPESTRY of life.\n", "test.md")
        assert any(f['tag'] == 'tier1' for f in hits)

    def test_tier1_correct_line(self):
        text = "line one\nThe intricate design\nline three\n"
        hits = [f for f in scan_text(text, "t.md") if f['tag'] == 'tier1']
        assert hits[0]['line'] == 2

    def test_tier1_no_false_positive(self):
        hits = scan_text("The quick brown fox jumps.\n", "test.md")
        assert 'tier1' not in _tags(hits)

    def test_tier1_severity(self):
        hits = scan_text("A vibrant color.\n", "test.md")
        tier1 = [f for f in hits if f['tag'] == 'tier1']
        assert tier1[0]['severity'] == 'HIGH'


# -- Check 2: Tier 2 vocabulary --

class TestTier2:
    def test_finds_tier2_word(self):
        hits = scan_text("Results were bolstered by data.\n", "test.md")
        assert any(f['tag'] == 'tier2' for f in hits)

    def test_finds_tier2_phrase(self):
        hits = scan_text("We align with the standard.\n", "test.md")
        assert any(f['tag'] == 'tier2' and 'align with' in f['text'].lower() for f in hits)

    def test_tier2_correct_line(self):
        text = "first\nsecond\nshowcasing results\n"
        hits = [f for f in scan_text(text, "t.md") if f['tag'] == 'tier2']
        assert hits[0]['line'] == 3

    def test_tier2_no_false_positive(self):
        hits = scan_text("Normal sentence with no triggers.\n", "test.md")
        assert 'tier2' not in _tags(hits)

    def test_tier2_severity(self):
        hits = scan_text("Enhanced performance.\n", "test.md")
        tier2 = [f for f in hits if f['tag'] == 'tier2']
        assert tier2[0]['severity'] == 'HIGH'


# -- Check 3: Tier 3 vocabulary --

class TestTier3:
    def test_finds_tier3_word(self):
        hits = scan_text("A comprehensive review.\n", "test.md")
        assert any(f['tag'] == 'tier3' for f in hits)

    def test_tier3_correct_line(self):
        text = "ok\nok\nok\nThis is a robust system.\n"
        hits = [f for f in scan_text(text, "t.md") if f['tag'] == 'tier3']
        assert hits[0]['line'] == 4

    def test_tier3_no_false_positive(self):
        hits = scan_text("Plain words only here.\n", "test.md")
        assert 'tier3' not in _tags(hits)

    def test_tier3_severity(self):
        hits = scan_text("A paradigm shift.\n", "test.md")
        tier3 = [f for f in hits if f['tag'] == 'tier3']
        assert tier3[0]['severity'] == 'MEDIUM'


# -- Check 4: Banned phrases --

class TestBannedPhrases:
    def test_finds_banned_phrase(self):
        hits = scan_text("This serves as a bridge.\n", "test.md")
        assert any(f['tag'] == 'banned-phrase' for f in hits)

    def test_banned_phrase_case_insensitive(self):
        hits = scan_text("In Today's world, we see change.\n", "test.md")
        assert any(f['tag'] == 'banned-phrase' for f in hits)

    def test_banned_phrase_correct_line(self):
        text = "first\nIt's important to note that we try.\n"
        hits = [f for f in scan_text(text, "t.md") if f['tag'] == 'banned-phrase']
        assert hits[0]['line'] == 2

    def test_banned_phrase_no_false_positive(self):
        hits = scan_text("Clean sentence without issues.\n", "test.md")
        assert 'banned-phrase' not in _tags(hits)

    def test_banned_phrase_severity(self):
        hits = scan_text("It boasts a grand view.\n", "test.md")
        bp = [f for f in hits if f['tag'] == 'banned-phrase']
        assert bp[0]['severity'] == 'HIGH'

    def test_worth_noting_contraction(self):
        for s in ("It's worth noting that the cache is cold.\n",
                  "It’s worth noting that the cache is cold.\n"):
            assert 'banned-phrase' in _tags(scan_text(s, "t.md"))

    def test_worth_noting_sentence_initial(self):
        for s in ("Worth noting: the lockfile pins every transitive dependency.\n",
                  "The build passed. Worth noting that the cache was cold.\n"):
            assert 'banned-phrase' in _tags(scan_text(s, "t.md")), s

    def test_worth_noting_negated_or_predicative_not_flagged(self):
        for s in ("A one-second stall is not worth noting.\n",
                  "The retry count is worth noting in the runbook.\n"):
            assert 'banned-phrase' not in _tags(scan_text(s, "t.md")), s

    def test_want_to_be_clear(self):
        hits = scan_text("I want to be clear that we ship Friday.\n", "t.md")
        assert 'banned-phrase' in _tags(hits)


# -- Check 5: Formulaic transitions --

class TestTransitions:
    def test_finds_transition_at_line_start(self):
        hits = scan_text("Additionally, we found bugs.\n", "test.md")
        assert any(f['tag'] == 'transition' for f in hits)

    def test_finds_transition_at_sentence_start(self):
        hits = scan_text("We did X. Furthermore, we did Y.\n", "test.md")
        assert any(f['tag'] == 'transition' for f in hits)

    def test_transition_case_insensitive(self):
        hits = scan_text("moreover, the data shows growth.\n", "test.md")
        assert any(f['tag'] == 'transition' for f in hits)

    def test_transition_correct_line(self):
        text = "line one\nline two\nAdditionally, line three\n"
        hits = [f for f in scan_text(text, "t.md") if f['tag'] == 'transition']
        assert hits[0]['line'] == 3

    def test_transition_no_false_positive_mid_sentence(self):
        hits = scan_text("We additionally checked the logs.\n", "test.md")
        assert 'transition' not in _tags(hits)

    def test_transition_severity(self):
        hits = scan_text("Furthermore, the results hold.\n", "test.md")
        t = [f for f in hits if f['tag'] == 'transition']
        assert t[0]['severity'] == 'HIGH'


# -- Cross-check: multiple findings --

def test_multiple_findings_same_line():
    text = "This delves into the rich tapestry of life.\n"
    hits = scan_text(text, "test.md")
    tags = _tags(hits)
    assert 'tier1' in tags
    assert 'banned-phrase' in tags

def test_empty_input():
    assert scan_text("", "empty.md") == []


# -- Check 6: Em dash --

class TestEmDash:
    def test_finds_em_dash(self):
        hits = scan_text("The project\u2014originally small\u2014grew fast.\n", "t.md")
        em = [f for f in hits if f['tag'] == 'em-dash']
        assert len(em) == 2
        assert em[0]['line'] == 1

    def test_no_em_dash_in_plain_text(self):
        hits = scan_text("The project, originally small, grew fast.\n", "t.md")
        assert 'em-dash' not in _tags(hits)

    def test_em_dash_severity(self):
        hits = scan_text("Word\u2014word.\n", "t.md")
        em = [f for f in hits if f['tag'] == 'em-dash']
        assert em[0]['severity'] == 'HIGH'


class TestTableCellDash:
    """A lone dash in a table cell is an empty-value marker, not a connector."""

    def test_lone_em_dash_cell_skipped(self):
        text = "| Runner | Cache hit |\n|---|---|\n| arm64 | \u2014 |\n"
        assert 'em-dash' not in _tags(scan_text(text, "t.md"))

    def test_lone_en_dash_cell_skipped(self):
        text = "| Runner | Cache hit |\n|---|---|\n|\u2013| 91% |\n"
        assert 'en-dash' not in _tags(scan_text(text, "t.md"))

    def test_dash_in_cell_prose_flagged(self):
        text = "| Runner | Note |\n|---|---|\n| arm64 | slow\u2014cold cache |\n"
        em = [f for f in scan_text(text, "t.md") if f['tag'] == 'em-dash']
        assert [f['line'] for f in em] == [3]

    def test_lone_cell_does_not_hide_prose_dash_on_same_row(self):
        text = "| arm64 | \u2014 | slow \u2013 cold cache |\n"
        tags = _tags(scan_text(text, "t.md"))
        assert 'em-dash' not in tags
        assert tags.count('en-dash') == 1

    def test_lone_dash_outside_table_flagged(self):
        em = [f for f in scan_text("Cache hit:\n\u2014\n", "t.md") if f['tag'] == 'em-dash']
        assert [f['line'] for f in em] == [2]


# -- Check 7: En dash --

class TestEnDash:
    def test_finds_en_dash_prose(self):
        hits = scan_text("The policy \u2013 adopted last year \u2013 failed.\n", "t.md")
        en = [f for f in hits if f['tag'] == 'en-dash']
        assert len(en) == 2

    def test_skips_number_range(self):
        hits = scan_text("See pages 1\u20135 for details.\n", "t.md")
        assert 'en-dash' not in _tags(hits)

    def test_skips_year_range(self):
        hits = scan_text("The period 2020\u20132025 was turbulent.\n", "t.md")
        assert 'en-dash' not in _tags(hits)

    def test_no_en_dash_in_plain_text(self):
        hits = scan_text("Normal sentence with a hyphen-word.\n", "t.md")
        assert 'en-dash' not in _tags(hits)

    def test_en_dash_severity(self):
        hits = scan_text("X \u2013 Y.\n", "t.md")
        en = [f for f in hits if f['tag'] == 'en-dash']
        assert en[0]['severity'] == 'HIGH'


# -- Check 8: ASCII prose dash --

class TestAsciiDash:
    def test_finds_prose_double_dash(self):
        hits = scan_text("The tool -- originally simple -- grew.\n", "t.md")
        ad = [f for f in hits if f['tag'] == 'ascii-dash']
        assert len(ad) == 2

    def test_no_cli_flag(self):
        hits = scan_text("Run it with --verbose to see output.\n", "t.md")
        assert 'ascii-dash' not in _tags(hits)

    def test_no_yaml_delimiter(self):
        hits = scan_text("---\ntitle: test\n", "t.md")
        assert 'ascii-dash' not in _tags(hits)

    def test_no_sql_comment(self):
        hits = scan_text("-- This is a SQL comment\n", "t.md")
        assert 'ascii-dash' not in _tags(hits)

    def test_ascii_dash_severity(self):
        hits = scan_text("word -- another word here.\n", "t.md")
        ad = [f for f in hits if f['tag'] == 'ascii-dash']
        assert ad[0]['severity'] == 'HIGH'


# -- Check 9: Inline-header lists --

class TestInlineHeader:
    def test_finds_inline_header(self):
        hits = scan_text("- **Authentication:** The system supports it.\n", "t.md")
        ih = [f for f in hits if f['tag'] == 'inline-header']
        assert len(ih) == 1
        assert ih[0]['line'] == 1

    def test_no_plain_bold(self):
        hits = scan_text("The **important** thing is speed.\n", "t.md")
        assert 'inline-header' not in _tags(hits)

    def test_inline_header_severity(self):
        hits = scan_text("- **Config:** Set the values.\n", "t.md")
        ih = [f for f in hits if f['tag'] == 'inline-header']
        assert ih[0]['severity'] == 'MEDIUM'


# -- Check 10: Excessive boldface --

class TestBoldface:
    def test_finds_bold(self):
        hits = scan_text("The **important** thing is **speed**.\n", "t.md")
        bold = [f for f in hits if f['tag'] == 'bold']
        assert len(bold) == 2

    def test_no_double_count_with_inline_header(self):
        hits = scan_text("- **Auth:** Supports OAuth.\n", "t.md")
        bold = [f for f in hits if f['tag'] == 'bold']
        assert len(bold) == 0

    def test_no_bold_in_plain_text(self):
        hits = scan_text("Normal sentence without markup.\n", "t.md")
        assert 'bold' not in _tags(hits)

    def test_nested_italic_inside_bold(self):
        # A single * inside bold used to end the match, so the regex paired
        # the gap between two bold spans instead of the spans themselves.
        text = "**Which jobs *really* failed?** Ask the **queue** owner.\n"
        bold = [f['text'] for f in scan_text(text, "t.md") if f['tag'] == 'bold']
        assert bold == ["**Which jobs *really* failed?**", "**queue**"]

    def test_nested_italic_inline_header(self):
        hits = scan_text("- **The *real* cost:** latency.\n", "t.md")
        assert 'inline-header' in _tags(hits)
        assert 'bold' not in _tags(hits)

    def test_bold_severity(self):
        hits = scan_text("Use **caution** here.\n", "t.md")
        bold = [f for f in hits if f['tag'] == 'bold']
        assert bold[0]['severity'] == 'MEDIUM'


# -- Check 11: Negative parallelism --

class TestNegativeParallelism:
    def test_finds_not_just_but_also(self):
        hits = scan_text("It's not just about speed, but also about reliability.\n", "t.md")
        np = [f for f in hits if f['tag'] == 'negative-parallelism']
        assert len(np) == 1
        assert np[0]['severity'] == 'MEDIUM'

    def test_finds_not_only_but(self):
        hits = scan_text("This is not only about speed but about efficiency.\n", "t.md")
        np = [f for f in hits if f['tag'] == 'negative-parallelism']
        assert len(np) == 1

    def test_finds_not_merely_but_also(self):
        hits = scan_text("It is not merely a tool, but also a platform.\n", "t.md")
        np = [f for f in hits if f['tag'] == 'negative-parallelism']
        assert len(np) == 1

    def test_no_plain_negation(self):
        hits = scan_text("This is not the right approach.\n", "t.md")
        assert 'negative-parallelism' not in _tags(hits)

    def test_no_short_gap(self):
        # Gap between "just" and "but" must be 5+ chars
        hits = scan_text("Not just X but Y.\n", "t.md")
        assert 'negative-parallelism' not in _tags(hits)

    def test_correct_line(self):
        text = "line one\nnot just about X here, but also about Y\nline three\n"
        np = [f for f in scan_text(text, "t.md") if f['tag'] == 'negative-parallelism']
        assert np[0]['line'] == 2


# -- Check 12: Despite-challenges pattern --

class TestDespiteChallenges:
    def test_finds_despite_challenges(self):
        hits = scan_text("Despite its strengths, the project faces challenges.\n", "t.md")
        dc = [f for f in hits if f['tag'] == 'despite-challenges']
        assert len(dc) == 1
        assert dc[0]['severity'] == 'MEDIUM'

    def test_finds_despite_limitations(self):
        hits = scan_text("Despite these gains, the team hit limitations.\n", "t.md")
        dc = [f for f in hits if f['tag'] == 'despite-challenges']
        assert len(dc) == 1

    def test_finds_despite_difficulties(self):
        hits = scan_text("Despite the improvements, difficulties arose.\n", "t.md")
        dc = [f for f in hits if f['tag'] == 'despite-challenges']
        assert len(dc) == 1

    def test_no_despite_without_challenges(self):
        hits = scan_text("Despite the rain, we went outside.\n", "t.md")
        assert 'despite-challenges' not in _tags(hits)

    def test_correct_line(self):
        text = "ok\nDespite their success, shortcomings remain.\nok\n"
        dc = [f for f in scan_text(text, "t.md") if f['tag'] == 'despite-challenges']
        assert dc[0]['line'] == 2


# -- Check 13: Generic openers/closers --

class TestGenericOpeners:
    def test_finds_in_todays(self):
        hits = scan_text("In today's fast-paced world, speed matters.\n", "t.md")
        go = [f for f in hits if f['tag'] == 'generic-opener']
        assert len(go) == 1
        assert go[0]['severity'] == 'HIGH'

    def test_finds_as_organizations(self):
        hits = scan_text("As organizations increasingly adopt AI, costs rise.\n", "t.md")
        go = [f for f in hits if f['tag'] == 'generic-opener']
        assert len(go) == 1

    def test_finds_in_an_era_of(self):
        hits = scan_text("In an era of rapid change, we adapt.\n", "t.md")
        go = [f for f in hits if f['tag'] == 'generic-opener']
        assert len(go) == 1

    def test_case_insensitive(self):
        hits = scan_text("IN TODAY'S market, competition is fierce.\n", "t.md")
        go = [f for f in hits if f['tag'] == 'generic-opener']
        assert len(go) == 1

    def test_no_opener_mid_line(self):
        hits = scan_text("We live in today's world and adapt.\n", "t.md")
        assert 'generic-opener' not in _tags(hits)

    def test_correct_line(self):
        text = "ok\nIn the rapidly evolving field, we adapt.\nok\n"
        go = [f for f in scan_text(text, "t.md") if f['tag'] == 'generic-opener']
        assert go[0]['line'] == 2


class TestGenericClosers:
    def test_finds_in_conclusion(self):
        hits = scan_text("In conclusion, the results are clear.\n", "t.md")
        gc = [f for f in hits if f['tag'] == 'generic-closer']
        assert len(gc) == 1
        assert gc[0]['severity'] == 'HIGH'

    def test_finds_to_summarize(self):
        hits = scan_text("To summarize, three patterns emerged.\n", "t.md")
        gc = [f for f in hits if f['tag'] == 'generic-closer']
        assert len(gc) == 1

    def test_finds_best_practices(self):
        hits = scan_text("By following these best practices, teams ship faster.\n", "t.md")
        gc = [f for f in hits if f['tag'] == 'generic-closer']
        assert len(gc) == 1

    def test_case_insensitive(self):
        hits = scan_text("IN CONCLUSION, we proved the hypothesis.\n", "t.md")
        gc = [f for f in hits if f['tag'] == 'generic-closer']
        assert len(gc) == 1

    def test_no_closer_mid_line(self):
        hits = scan_text("He reached a conclusion quickly.\n", "t.md")
        assert 'generic-closer' not in _tags(hits)

    def test_correct_line(self):
        text = "ok\nok\nAs we have seen, the data supports this.\n"
        gc = [f for f in scan_text(text, "t.md") if f['tag'] == 'generic-closer']
        assert gc[0]['line'] == 3


# -- Check 14: Collaborative remnants --

class TestCollaborativeRemnants:
    def test_finds_hope_this_helps(self):
        hits = scan_text("I hope this helps you get started.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1
        assert cr[0]['severity'] == 'HIGH'

    def test_finds_would_you_like(self):
        hits = scan_text("Would you like me to explain further?\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_finds_let_me_know(self):
        hits = scan_text("Let me know if you need more details.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_finds_feel_free_to(self):
        hits = scan_text("Feel free to reach out with questions.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_finds_heres_comprehensive(self):
        hits = scan_text("Here's a comprehensive guide to setting up CI.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_finds_dont_hesitate(self):
        hits = scan_text("Don't hesitate to ask for clarification.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_finds_id_be_happy(self):
        hits = scan_text("I'd be happy to walk through the details.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_case_insensitive(self):
        hits = scan_text("FEEL FREE TO modify the config.\n", "t.md")
        cr = [f for f in hits if f['tag'] == 'collaborative-remnant']
        assert len(cr) == 1

    def test_no_false_positive(self):
        hits = scan_text("The system runs without intervention.\n", "t.md")
        assert 'collaborative-remnant' not in _tags(hits)

    def test_correct_line(self):
        text = "ok\nok\nLet me know if there are issues.\n"
        cr = [f for f in scan_text(text, "t.md") if f['tag'] == 'collaborative-remnant']
        assert cr[0]['line'] == 3


# -- compute_stats --

compute_stats = pre_scan.compute_stats


class TestComputeStats:
    def test_word_count(self):
        text = "one two three four five"
        st = compute_stats(text)
        assert st['words'] == 5

    def test_sd_uniform_sentences(self):
        # Four sentences, each 5 words. SD should be 0.0.
        text = "I wrote five words here. I wrote five words here. I wrote five words here. I wrote five words here. "
        st = compute_stats(text)
        assert st['sd'] == 0.0

    def test_sd_varied_sentences(self):
        # Mix short and long. SD should be well above 0.
        text = "Short one here. This sentence is quite a bit longer than the others in this text. Tiny. Another moderately sized sentence appears here. "
        st = compute_stats(text)
        assert st['sd'] > 3.0

    def test_sd_single_sentence(self):
        text = "Only one sentence with several words in it"
        st = compute_stats(text)
        assert st['sd'] == 0.0

    def test_bold_density(self):
        # 100 words, 3 bold patterns = 30.0 per 1000w
        words = ' '.join(['word'] * 97)
        text = f"**bold1** **bold2** **bold3** {words}"
        st = compute_stats(text)
        assert st['bold_per_1000w'] == 30.0

    def test_bold_density_zero(self):
        text = "No bold patterns at all in this sentence."
        st = compute_stats(text)
        assert st['bold_per_1000w'] == 0.0

    def test_empty_text(self):
        st = compute_stats("")
        assert st['words'] == 0
        assert st['sd'] == 0.0
        assert st['bold_per_1000w'] == 0.0


# -- format_human --

format_human = pre_scan.format_human

VOCAB_TAGS = {'tier1', 'tier2', 'tier3', 'banned-phrase', 'transition'}


class TestFormatHuman:
    def test_contains_vocabulary_section(self):
        findings = [{'line': 5, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'}]
        stats = {'words': 100, 'sd': 4.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_human("t.md", findings, stats)
        assert "VOCABULARY" in out
        assert 'delve' in out

    def test_contains_structural_section(self):
        findings = [{'line': 3, 'text': '\u2014', 'tag': 'em-dash', 'severity': 'HIGH'}]
        stats = {'words': 100, 'sd': 10.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_human("t.md", findings, stats)
        assert "STRUCTURAL" in out

    def test_omits_vocabulary_if_none(self):
        findings = [{'line': 3, 'text': '\u2014', 'tag': 'em-dash', 'severity': 'HIGH'}]
        stats = {'words': 100, 'sd': 10.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_human("t.md", findings, stats)
        assert "VOCABULARY" not in out

    def test_omits_structural_if_none(self):
        findings = [{'line': 5, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'}]
        stats = {'words': 100, 'sd': 10.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_human("t.md", findings, stats)
        assert "STRUCTURAL" not in out

    def test_stats_always_present(self):
        out = format_human("t.md", [], {'words': 50, 'sd': 9.0, 'bold_per_1000w': 1.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        assert "STATS" in out
        assert "words: 50" in out

    def test_sd_label_low(self):
        out = format_human("t.md", [], {'words': 50, 'sd': 4.2, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        assert "LOW" in out

    def test_sd_label_ok(self):
        out = format_human("t.md", [], {'words': 50, 'sd': 8.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        assert "OK" in out

    def test_bold_label_high(self):
        out = format_human("t.md", [], {'words': 50, 'sd': 10.0, 'bold_per_1000w': 5.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        assert "HIGH" in out

    def test_bold_label_ok(self):
        out = format_human("t.md", [], {'words': 50, 'sd': 10.0, 'bold_per_1000w': 2.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        # bold OK
        assert "bold density: 2.0 per 1000w (OK" in out

    def test_findings_sorted_by_line(self):
        findings = [
            {'line': 20, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'},
            {'line': 5, 'text': 'tapestry', 'tag': 'tier1', 'severity': 'HIGH'},
        ]
        stats = {'words': 100, 'sd': 10.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_human("t.md", findings, stats)
        pos5 = out.index('line 5')
        pos20 = out.index('line 20')
        assert pos5 < pos20

    def test_header_contains_filename(self):
        out = format_human("README.md", [], {'words': 10, 'sd': 0.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0})
        assert "README.md" in out


# -- format_llm --

format_llm = pre_scan.format_llm


class TestFormatLLM:
    def test_one_line_per_finding(self):
        findings = [
            {'line': 5, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'},
            {'line': 10, 'text': '\u2014', 'tag': 'em-dash', 'severity': 'HIGH'},
        ]
        stats = {'words': 100, 'sd': 4.2, 'bold_per_1000w': 1.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_llm("f.md", findings, stats)
        lines = [l for l in out.strip().split('\n') if l]
        assert len(lines) == 3  # 2 findings + 1 stats

    def test_file_line_format(self):
        findings = [{'line': 12, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'}]
        stats = {'words': 50, 'sd': 0.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_llm("README.md", findings, stats)
        assert 'README.md:12: "delve" [tier1]' in out

    def test_stats_line(self):
        stats = {'words': 847, 'sd': 4.2, 'bold_per_1000w': 12.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_llm("f.md", [], stats)
        assert "f.md:STATS words=847 sd=4.2 bold_per_1000w=12.0" in out

    def test_sorted_by_line(self):
        findings = [
            {'line': 20, 'text': 'delve', 'tag': 'tier1', 'severity': 'HIGH'},
            {'line': 3, 'text': '\u2014', 'tag': 'em-dash', 'severity': 'HIGH'},
        ]
        stats = {'words': 100, 'sd': 5.0, 'bold_per_1000w': 0.0, 'max_sentence_len': 0, 'structured_density': 0.0}
        out = format_llm("f.md", findings, stats)
        lines = out.strip().split('\n')
        # first finding should be line 3
        assert ':3:' in lines[0]
        assert ':20:' in lines[1]


# -- CLI tests --

import subprocess
import tempfile
import os
import sys
from pathlib import Path

# Hermetic git env shared by every test class that spawns `git`.
# See conftest.hermetic_git_env() for what it neutralizes (gpgsign, hooks,
# template hooks, prompts) and why every git invocation in this file must
# pass `env=_GIT_ENV` -- a single missed call site reintroduces the hang.
_GIT_ENV = hermetic_git_env()


class TestIsBinary:
    def test_text_file_is_not_binary(self):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Hello, this is plain text.\n')
            f.flush()
            assert pre_scan.is_binary(Path(f.name)) is False
            os.unlink(f.name)

    def test_null_bytes_is_binary(self):
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(b'Header\x00\x00\x00binary content')
            f.flush()
            assert pre_scan.is_binary(Path(f.name)) is True
            os.unlink(f.name)


class TestCLI:
    _script = str(Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts' / 'pre-scan.py')

    def _run(self, *args):
        cmd = [sys.executable, self._script] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_human_mode_default(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write('We must delve into the topic.\n')
            f.flush()
            r = self._run(f.name)
            assert r.returncode == 0
            assert 'VOCABULARY' in r.stdout
            os.unlink(f.name)

    def test_llm_mode(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write('We must delve into the topic.\n')
            f.flush()
            r = self._run('--mode', 'llm', f.name)
            assert r.returncode == 0
            assert '[tier1]' in r.stdout
            os.unlink(f.name)

    def test_empty_file_no_crash(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write('')
            f.flush()
            r = self._run(f.name)
            assert r.returncode == 0
            os.unlink(f.name)

    def test_multiple_files(self):
        paths = []
        for i in range(2):
            f = tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False)
            f.write(f'File {i} has a vibrant tapestry.\n')
            f.flush()
            paths.append(f.name)
            f.close()
        r = self._run(*paths)
        assert r.returncode == 0
        for p in paths:
            assert os.path.basename(p) in r.stdout
            os.unlink(p)

    def test_exit_code_zero_with_findings(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write('Delve into the vibrant tapestry of the intricate landscape.\n')
            f.flush()
            r = self._run(f.name)
            assert r.returncode == 0
            os.unlink(f.name)

    def test_binary_file_skipped(self):
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(b'\x00\x01\x02binary\x00')
            f.flush()
            r = self._run(f.name)
            assert r.returncode == 0
            assert 'skip' in r.stderr.lower() or 'binary' in r.stderr.lower()
            os.unlink(f.name)

    def test_nonexistent_file(self):
        r = self._run('/tmp/nonexistent_pre_scan_test_file.md')
        assert r.returncode == 0
        assert 'error' in r.stderr.lower() or 'not found' in r.stderr.lower() or 'skip' in r.stderr.lower()

    def test_summary_line_human_mode(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write('We must delve into the topic.\n')
            f.flush()
            r = self._run(f.name)
            assert 'Total:' in r.stdout
            assert 'finding' in r.stdout
            os.unlink(f.name)

    def test_directory_scanning(self):
        # Scanning a directory should pick up files inside it
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'test.md'
            p.write_text('We must delve into the vibrant topic.\n')
            r = self._run(d)
            assert r.returncode == 0
            assert 'test.md' in r.stdout


class TestDiffMode:
    _script = str(Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts' / 'pre-scan.py')

    def _run(self, *args, cwd=None):
        cmd = [sys.executable, self._script] + list(args)
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd,
            timeout=30, env=_GIT_ENV,
        )

    def _git(self, *args, cwd=None):
        return subprocess.run(
            ['git'] + list(args),
            capture_output=True, text=True, cwd=cwd,
            timeout=30, env=_GIT_ENV,
        )

    def _make_repo(self, d):
        """Init a git repo with an initial commit on main."""
        self._git('init', '-b', 'main', cwd=d)
        # Identity comes from GIT_AUTHOR_*/GIT_COMMITTER_* in hermetic env;
        # no need to write user.email/user.name into the local repo config.
        (Path(d) / 'init.txt').write_text('init\n')
        self._git('add', 'init.txt', cwd=d)
        self._git('commit', '-m', 'init', cwd=d)

    def test_diff_finds_only_changed_lines(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_repo(d)
            fp = Path(d) / 'doc.md'
            fp.write_text('Line one is clean.\nLine two is clean.\n')
            self._git('add', 'doc.md', cwd=d)
            self._git('commit', '-m', 'add doc', cwd=d)
            # Create branch
            self._git('checkout', '-b', 'feature', cwd=d)
            fp.write_text('Line one is clean.\nWe must delve into the vibrant tapestry.\n')
            self._git('add', 'doc.md', cwd=d)
            self._git('commit', '-m', 'modify doc', cwd=d)
            r = self._run('--diff', 'main', '--mode', 'llm', cwd=d)
            assert r.returncode == 0
            # Should find tier1 hits on modified line 2
            for line in r.stdout.strip().split('\n'):
                if '[tier1]' in line:
                    assert ':2:' in line

    def test_diff_auto_detects_main(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_repo(d)
            fp = Path(d) / 'doc.md'
            fp.write_text('Clean text.\n')
            self._git('add', 'doc.md', cwd=d)
            self._git('commit', '-m', 'add doc', cwd=d)
            self._git('checkout', '-b', 'feature', cwd=d)
            fp.write_text('We delve into tapestry.\n')
            self._git('add', 'doc.md', cwd=d)
            self._git('commit', '-m', 'modify', cwd=d)
            r = self._run('--diff', '--mode', 'llm', cwd=d)
            assert r.returncode == 0
            assert 'tier1' in r.stdout

    def test_diff_with_explicit_base(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_repo(d)
            fp = Path(d) / 'doc.md'
            fp.write_text('Delve into tapestry.\n')
            self._git('add', 'doc.md', cwd=d)
            self._git('commit', '-m', 'add doc', cwd=d)
            r = self._run('--diff', 'HEAD~1', '--mode', 'llm', cwd=d)
            assert r.returncode == 0
            assert 'tier1' in r.stdout

    def test_diff_no_git_prints_error(self):
        with tempfile.TemporaryDirectory() as d:
            fp = Path(d) / 'doc.md'
            fp.write_text('Delve.\n')
            r = self._run('--diff', fp.name, cwd=d)
            # Should handle gracefully
            assert r.returncode == 0


# -- Direct unit tests for CLI/utility functions (lines 207-391) --

from unittest.mock import patch


class TestIsBinaryUnit:
    def test_text_file(self, tmp_path):
        f = tmp_path / 'hello.txt'
        f.write_bytes(b'plain text content\n')
        assert pre_scan.is_binary(f) is False

    def test_null_bytes(self, tmp_path):
        f = tmp_path / 'data.bin'
        f.write_bytes(b'head\x00\x00tail')
        assert pre_scan.is_binary(f) is True

    def test_empty_file(self, tmp_path):
        f = tmp_path / 'empty'
        f.write_bytes(b'')
        assert pre_scan.is_binary(f) is False

    def test_oserror_returns_false(self, tmp_path):
        # nonexistent path triggers OSError
        assert pre_scan.is_binary(tmp_path / 'nope') is False

    def test_permission_denied(self, tmp_path):
        f = tmp_path / 'locked'
        f.write_bytes(b'secret')
        f.chmod(0o000)
        assert pre_scan.is_binary(f) is False
        f.chmod(0o644)  # restore for cleanup


class TestGitTrackedFiles:
    def _init_repo(self, d):
        subprocess.run(['git', 'init', '-b', 'main'], cwd=d, capture_output=True, env=_GIT_ENV, timeout=15)

    def test_returns_paths_in_git_repo(self, tmp_path):
        self._init_repo(tmp_path)
        (tmp_path / 'a.txt').write_text('a\n')
        subprocess.run(['git', 'add', 'a.txt'], cwd=tmp_path, capture_output=True, env=_GIT_ENV, timeout=15)
        result = pre_scan.git_tracked_files(tmp_path)
        assert result is not None
        names = [p.name for p in result]
        assert 'a.txt' in names

    def test_returns_none_outside_git(self, tmp_path):
        result = pre_scan.git_tracked_files(tmp_path)
        assert result is None

    def test_returns_none_on_timeout(self, tmp_path):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('git', 10)):
            result = pre_scan.git_tracked_files(tmp_path)
        assert result is None


class TestDetectMainBranch:
    def _init_repo(self, d, branch='main'):
        subprocess.run(['git', 'init', '-b', branch], cwd=d, capture_output=True, env=_GIT_ENV, timeout=15)
        (d / 'init.txt').write_text('init\n')
        subprocess.run(['git', 'add', '.'], cwd=d, capture_output=True, env=_GIT_ENV, timeout=15)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=d, capture_output=True, env=_GIT_ENV, timeout=15)

    def test_detects_main(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path, 'main')
        monkeypatch.chdir(tmp_path)
        assert pre_scan.detect_main_branch() == 'main'

    def test_detects_master(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path, 'master')
        monkeypatch.chdir(tmp_path)
        assert pre_scan.detect_main_branch() == 'master'

    def test_neither_returns_none(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path, 'develop')
        monkeypatch.chdir(tmp_path)
        assert pre_scan.detect_main_branch() is None


class TestDiffChangedLines:
    def _git(self, args, cwd):
        return subprocess.run(
            ['git'] + args, cwd=cwd, capture_output=True, env=_GIT_ENV, timeout=15,
        )

    def _make_repo(self, d):
        self._git(['init', '-b', 'main'], cwd=d)
        (d / 'init.txt').write_text('init\n')
        self._git(['add', '.'], cwd=d)
        self._git(['commit', '-m', 'init'], cwd=d)

    def test_real_diff_returns_correct_lines(self, tmp_path, monkeypatch):
        self._make_repo(tmp_path)
        f = tmp_path / 'doc.md'
        f.write_text('line one\nline two\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'add doc'], cwd=tmp_path)
        self._git(['checkout', '-b', 'feat'], cwd=tmp_path)
        f.write_text('line one\nchanged line two\nline three\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'edit'], cwd=tmp_path)
        monkeypatch.chdir(tmp_path)
        result = pre_scan.diff_changed_lines('main')
        assert result is not None
        assert 'doc.md' in result
        assert 2 in result['doc.md']  # changed line
        assert 3 in result['doc.md']  # added line

    def test_pure_deletion_hunk_skipped(self, tmp_path, monkeypatch):
        self._make_repo(tmp_path)
        f = tmp_path / 'doc.md'
        f.write_text('keep\ndelete me\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'add'], cwd=tmp_path)
        self._git(['checkout', '-b', 'feat'], cwd=tmp_path)
        f.write_text('keep\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'del'], cwd=tmp_path)
        monkeypatch.chdir(tmp_path)
        result = pre_scan.diff_changed_lines('main')
        assert result is not None
        # pure deletion: doc.md may be absent or have empty set
        lines = result.get('doc.md', set())
        assert len(lines) == 0

    def test_single_line_hunk_no_comma(self, tmp_path, monkeypatch):
        self._make_repo(tmp_path)
        f = tmp_path / 'doc.md'
        f.write_text('aaa\nbbb\nccc\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'add'], cwd=tmp_path)
        self._git(['checkout', '-b', 'feat'], cwd=tmp_path)
        # change only middle line (single-line hunk)
        f.write_text('aaa\nBBB\nccc\n')
        self._git(['add', '.'], cwd=tmp_path)
        self._git(['commit', '-m', 'edit'], cwd=tmp_path)
        monkeypatch.chdir(tmp_path)
        result = pre_scan.diff_changed_lines('main')
        assert result is not None
        assert 2 in result.get('doc.md', set())

    def test_failed_diff_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # not a git repo
        result = pre_scan.diff_changed_lines('main')
        assert result is None


class TestResolvePaths:
    def test_nonexistent_skipped(self, tmp_path, capsys):
        bogus = str(tmp_path / 'nope.md')
        result = pre_scan.resolve_paths([bogus])
        assert result == []
        assert 'not found' in capsys.readouterr().err

    def test_binary_skipped(self, tmp_path, capsys):
        f = tmp_path / 'data.bin'
        f.write_bytes(b'\x00binary')
        result = pre_scan.resolve_paths([str(f)])
        assert result == []
        assert 'binary' in capsys.readouterr().err

    def test_text_file_included(self, tmp_path):
        f = tmp_path / 'readme.md'
        f.write_text('hello\n')
        result = pre_scan.resolve_paths([str(f)])
        assert len(result) == 1
        assert result[0].name == 'readme.md'

    def test_directory_expands(self, tmp_path):
        (tmp_path / 'a.txt').write_text('a\n')
        (tmp_path / 'b.txt').write_text('b\n')
        result = pre_scan.resolve_paths([str(tmp_path)])
        names = {p.name for p in result}
        assert 'a.txt' in names
        assert 'b.txt' in names


class TestRelPath:
    def test_under_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / 'sub' / 'file.md'
        f.parent.mkdir()
        f.write_text('x\n')
        rel = pre_scan._rel_path(f)
        assert rel == 'sub/file.md'

    def test_outside_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path / 'inner' if False else tmp_path)
        # create a path that's clearly outside cwd by using /tmp
        other = Path('/tmp/_prescan_relpath_test_dir')
        other.mkdir(exist_ok=True)
        target = other / 'out.md'
        target.write_text('x\n')
        monkeypatch.chdir(tmp_path)
        # If target is not under cwd, _rel_path falls back to str(fpath)
        result = pre_scan._rel_path(target)
        assert 'out.md' in result
        target.unlink()
        other.rmdir()


class TestMainUnit:
    def test_no_args_scans_cwd(self, tmp_path, monkeypatch, capsys):
        """No file args and no --diff should scan the current directory."""
        (tmp_path / 'doc.md').write_text('We delve into tapestry.\n')
        monkeypatch.chdir(tmp_path)
        with patch('sys.argv', ['pre-scan.py']):
            with pytest.raises(SystemExit) as exc:
                pre_scan.main()
            assert exc.value.code == 0
        out = capsys.readouterr().out
        assert 'doc.md' in out

    def test_diff_no_repo_prints_error(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch('sys.argv', ['pre-scan.py', '--diff']):
            with pytest.raises(SystemExit) as exc:
                pre_scan.main()
            assert exc.value.code == 0
        err = capsys.readouterr().err
        assert 'error' in err.lower() or 'detect' in err.lower()


import pytest
