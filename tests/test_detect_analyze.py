"""Unit tests for detect_analyze.py -- correlation engine."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


def test_dataclasses_importable():
    from detect_analyze import PatternCorrelation, UnknownPattern, AnalysisResult
    assert PatternCorrelation is not None


def test_direct_match_tier1_word():
    from detect import SpanFlag
    from detect_analyze import correlate_span
    span = SpanFlag(start=0, end=5, text="delve into the topic",
                    reason="top10_cluster", severity=0.8)
    correlations = correlate_span(span)
    categories = [c.pattern_category for c in correlations]
    assert "tier1_vocab" in categories


def test_direct_match_transition():
    from detect import SpanFlag
    from detect_analyze import correlate_span
    span = SpanFlag(start=0, end=30, text="Additionally, this is important",
                    reason="top10_cluster", severity=0.7)
    correlations = correlate_span(span)
    categories = [c.pattern_category for c in correlations]
    assert "formulaic_transition" in categories


def test_no_match_returns_empty():
    from detect import SpanFlag
    from detect_analyze import correlate_span
    span = SpanFlag(start=0, end=10, text="the cat sat",
                    reason="top10_cluster", severity=0.5)
    correlations = correlate_span(span)
    assert len(correlations) == 0


def test_analyze_groups_unknowns():
    from detect import SpanFlag, DetectionResult
    from detect_analyze import analyze_results
    results = [
        ("sample1", [DetectionResult(
            source="gltr", score=0.6, label="uncertain",
            flagged_spans=[SpanFlag(0, 20, "xyz pattern here ok", "top10_cluster", 0.8)],
            token_scores=[], metadata={},
        )]),
        ("sample2", [DetectionResult(
            source="gltr", score=0.6, label="uncertain",
            flagged_spans=[SpanFlag(0, 20, "xyz pattern here ok", "top10_cluster", 0.7)],
            token_scores=[], metadata={},
        )]),
    ]
    analysis = analyze_results(results)
    assert isinstance(analysis, list)
    all_unknowns = []
    for a in analysis:
        all_unknowns.extend(a.unknown_patterns)
    assert len(all_unknowns) >= 1
    assert all_unknowns[0].sample_count >= 2


def test_single_sample_unknown_not_surfaced():
    from detect import SpanFlag, DetectionResult
    from detect_analyze import analyze_results
    results = [
        ("sample1", [DetectionResult(
            source="gltr", score=0.6, label="uncertain",
            flagged_spans=[SpanFlag(0, 20, "unique one-off text", "top10_cluster", 0.8)],
            token_scores=[], metadata={},
        )]),
    ]
    analysis = analyze_results(results)
    all_unknowns = []
    for a in analysis:
        all_unknowns.extend(a.unknown_patterns)
    surfaced = [u for u in all_unknowns if u.sample_count >= 2]
    assert len(surfaced) == 0
