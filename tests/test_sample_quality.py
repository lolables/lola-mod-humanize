"""
test_sample_quality.py -- Validate that each text sample's "after" version
scores better than its "before" version on AI-detection heuristics.

Uses the score_text() function from ollama-eval.py (via conftest.py).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import ollama_eval

score_text = ollama_eval.score_text

SAMPLES_DIR = Path(__file__).resolve().parent / 'text-samples'

# Discover sample pairs: [(id, before_path, after_path), ...]
_SAMPLE_IDS = sorted({
    p.stem.replace('.before', '')
    for p in SAMPLES_DIR.glob('*.before.md')
})

SAMPLE_PAIRS = [
    (sid, SAMPLES_DIR / f'{sid}.before.md', SAMPLES_DIR / f'{sid}.after.md')
    for sid in _SAMPLE_IDS
]


def _ai_density(findings: dict) -> float:
    """AI vocabulary density: flagged words per 500 words."""
    total = (
        len(findings['tier1_found'])
        + len(findings['tier2_found'])
        + len(findings['tier3_found'])
    )
    wc = findings['word_count']
    if wc == 0:
        return 0.0
    return (total / wc) * 500


@pytest.fixture(params=SAMPLE_PAIRS, ids=[s[0] for s in SAMPLE_PAIRS])
def sample_pair(request):
    """Yield (sample_id, before_text, after_text, before_scores, after_scores)."""
    sid, before_path, after_path = request.param
    before_text = before_path.read_text()
    after_text = after_path.read_text()
    return (
        sid,
        before_text,
        after_text,
        score_text(before_text),
        score_text(after_text),
    )


def test_after_file_is_nonempty(sample_pair):
    sid, _, after_text, _, _ = sample_pair
    assert after_text.strip(), f'{sid}: after file is empty'


def test_after_differs_from_before(sample_pair):
    sid, before_text, after_text, _, _ = sample_pair
    assert before_text != after_text, f'{sid}: after file is identical to before'


def test_after_has_lower_ai_density(sample_pair):
    sid, _, _, before_scores, after_scores = sample_pair
    before_density = _ai_density(before_scores)
    after_density = _ai_density(after_scores)
    assert after_density < before_density, (
        f'{sid}: after density ({after_density:.2f}) should be lower than '
        f'before density ({before_density:.2f})'
    )


def test_after_has_zero_tier1_words(sample_pair):
    sid, _, _, _, after_scores = sample_pair
    t1 = after_scores['tier1_found']
    assert len(t1) == 0, (
        f'{sid}: after file has Tier 1 words: {t1}'
    )
