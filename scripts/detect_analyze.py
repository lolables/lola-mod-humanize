"""detect_analyze.py -- Correlation engine for AI detection results.

Maps flagged spans from detect.py to Humanize's pattern taxonomy.
Three layers: direct match (vocabulary/pre-scan), statistical match,
and residual grouping for unknown patterns.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from detect import SpanFlag, DetectionResult

# Import vocabulary directly rather than calling pre-scan as a subprocess.
# pre-scan.scan_text() expects full documents with line numbers;
# correlate_span() operates on short text snippets (flagged spans),
# so we match vocabulary patterns directly.
_skill_scripts = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts'
if str(_skill_scripts) not in sys.path:
    sys.path.insert(0, str(_skill_scripts))

from vocabulary import (
    TIER1_WORDS, TIER2_WORDS, TIER3_WORDS,
    BANNED_PHRASES, TRANSITION_STARTERS,
)


@dataclass
class PatternCorrelation:
    span: SpanFlag
    pattern_category: str
    pattern_source: str
    confidence: float
    evidence: str


@dataclass
class UnknownPattern:
    spans: list[SpanFlag] = field(default_factory=list)
    proposed_category: str = ""
    proposed_description: str = ""
    sample_count: int = 0


@dataclass
class AnalysisResult:
    sample: str
    detection_results: list[DetectionResult]
    correlations: list[PatternCorrelation]
    unknown_patterns: list[UnknownPattern]
    summary: str = ""


_tier1_re = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in TIER1_WORDS) + r')\b', re.I
)
_tier2_re = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in TIER2_WORDS) + r')\b', re.I
)
_tier3_re = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in TIER3_WORDS) + r')\b', re.I
)
_banned_re = re.compile(
    '|'.join(re.escape(p) for p in BANNED_PHRASES), re.I
)
_transition_re = re.compile(
    r'(?:^|(?<=[.!?]\s))(' + '|'.join(re.escape(t) for t in TRANSITION_STARTERS) + r')',
    re.I | re.M,
)
_em_dash_re = re.compile(r'\u2014')


def correlate_span(span: SpanFlag) -> list[PatternCorrelation]:
    matches = []
    text = span.text

    if _tier1_re.search(text):
        found = _tier1_re.findall(text)
        matches.append(PatternCorrelation(
            span=span, pattern_category="tier1_vocab",
            pattern_source="vocabulary.py", confidence=0.95,
            evidence=f"tier 1 words: {', '.join(found)}",
        ))
    if _tier2_re.search(text):
        found = _tier2_re.findall(text)
        matches.append(PatternCorrelation(
            span=span, pattern_category="tier2_vocab",
            pattern_source="vocabulary.py", confidence=0.85,
            evidence=f"tier 2 words: {', '.join(found)}",
        ))
    if _tier3_re.search(text):
        found = _tier3_re.findall(text)
        matches.append(PatternCorrelation(
            span=span, pattern_category="tier3_vocab",
            pattern_source="vocabulary.py", confidence=0.7,
            evidence=f"tier 3 words: {', '.join(found)}",
        ))
    if _banned_re.search(text):
        found = _banned_re.findall(text)
        matches.append(PatternCorrelation(
            span=span, pattern_category="banned_phrase",
            pattern_source="vocabulary.py", confidence=0.95,
            evidence=f"banned phrases: {', '.join(found)}",
        ))
    if _transition_re.search(text):
        matches.append(PatternCorrelation(
            span=span, pattern_category="formulaic_transition",
            pattern_source="structural-patterns.md", confidence=0.9,
            evidence="sentence-opening transition word",
        ))
    if _em_dash_re.search(text):
        matches.append(PatternCorrelation(
            span=span, pattern_category="em_dash",
            pattern_source="structural-patterns.md", confidence=0.8,
            evidence="em dash usage",
        ))
    return matches


def analyze_results(
    sample_results: list[tuple[str, list[DetectionResult]]]
) -> list[AnalysisResult]:
    analyses = []
    all_unmatched: list[tuple[str, SpanFlag]] = []

    for sample_name, det_results in sample_results:
        correlations = []
        sample_unmatched = 0
        for dr in det_results:
            for span in dr.flagged_spans:
                span_corrs = correlate_span(span)
                if span_corrs:
                    correlations.extend(span_corrs)
                else:
                    all_unmatched.append((sample_name, span))
                    sample_unmatched += 1

        analyses.append(AnalysisResult(
            sample=sample_name, detection_results=det_results,
            correlations=correlations, unknown_patterns=[],
            summary=f"{len(correlations)} known, {sample_unmatched} unknown",
        ))

    unknowns = _group_unknown_spans(all_unmatched)
    # Only surface unknowns that appear across multiple samples
    for unknown in unknowns:
        if unknown.sample_count >= 2 and analyses:
            analyses[0].unknown_patterns.append(unknown)

    return analyses


def _group_unknown_spans(
    unmatched: list[tuple[str, SpanFlag]]
) -> list[UnknownPattern]:
    # Group by first 5 words as a rough fingerprint
    groups: dict[str, list[tuple[str, SpanFlag]]] = {}
    for sample, span in unmatched:
        key = " ".join(span.text.lower().split()[:5])
        groups.setdefault(key, []).append((sample, span))

    unknowns = []
    for key, entries in groups.items():
        samples = set(s for s, _ in entries)
        unknowns.append(UnknownPattern(
            spans=[sp for _, sp in entries],
            proposed_category=f"unknown_{key.replace(' ', '_')[:30]}",
            proposed_description=f"Unmatched pattern in {len(samples)} samples: '{key}...'",
            sample_count=len(samples),
        ))
    return unknowns
