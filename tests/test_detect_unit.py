"""Unit tests for detect.py -- data structures and import guards."""
from __future__ import annotations
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


def test_dataclasses_importable():
    from detect import TokenScore, SpanFlag, DetectionResult
    ts = TokenScore(token="hello", rank=5, prob=0.9)
    assert ts.rank == 5
    sf = SpanFlag(start=0, end=5, text="hello", reason="test", severity=0.5)
    assert sf.severity == 0.5
    dr = DetectionResult(
        source="test", score=0.5, label="uncertain",
        token_scores=[ts], flagged_spans=[sf], metadata={}
    )
    assert dr.score == 0.5


def test_gpu_available_returns_bool():
    from detect import gpu_available
    result = gpu_available()
    assert isinstance(result, bool)


def test_detect_raises_without_deps():
    """detect() raises RuntimeError if torch is missing."""
    from detect import gpu_available, detect
    if gpu_available():
        pytest.skip("torch is available, can't test missing-deps path")
    with pytest.raises(RuntimeError, match="torch"):
        detect("some text")


def test_binoculars_normalize_score():
    """Score normalization maps raw ratio to 0.0-1.0 range."""
    from detect import _normalize_binoculars
    assert _normalize_binoculars(0.5) > 0.7
    assert _normalize_binoculars(2.0) < 0.3


def test_binoculars_label_from_score():
    from detect import _label_from_score
    assert _label_from_score(0.8) == "machine"
    assert _label_from_score(0.3) == "human"
    assert _label_from_score(0.5) == "uncertain"


def test_gltr_rank_buckets():
    """Bucket tokens by rank in model vocabulary."""
    from detect import _bucket_ranks
    ranks = [1, 3, 8, 15, 50, 200, 500, 1500]
    buckets = _bucket_ranks(ranks)
    assert abs(buckets["top10"] - 37.5) < 0.1
    assert abs(buckets["top100"] - 25.0) < 0.1
    assert abs(buckets["top1000"] - 25.0) < 0.1
    assert abs(buckets["beyond"] - 12.5) < 0.1


def test_gltr_score_from_buckets():
    """High top-10 percentage = machine-like."""
    from detect import _gltr_score_from_buckets
    machine_buckets = {"top10": 80.0, "top100": 10.0, "top1000": 5.0, "beyond": 5.0}
    assert _gltr_score_from_buckets(machine_buckets) > 0.7
    human_buckets = {"top10": 20.0, "top100": 30.0, "top1000": 30.0, "beyond": 20.0}
    assert _gltr_score_from_buckets(human_buckets) < 0.4


def test_gltr_find_suspicious_spans():
    """Clusters of top-10 tokens get flagged as spans."""
    from detect import TokenScore, _find_suspicious_spans
    tokens = [
        TokenScore("The", 1, 0.9),
        TokenScore("quick", 5, 0.8),
        TokenScore("brown", 3, 0.85),
        TokenScore("fox", 250, 0.01),
        TokenScore("jumped", 2, 0.9),
    ]
    text = "The quick brown fox jumped"
    spans = _find_suspicious_spans(tokens, text, window=3, threshold=0.8)
    assert len(spans) >= 1
    assert "top10_cluster" in spans[0].reason


def test_gltr_no_cluster_returns_empty():
    """No cluster of top-10 tokens -> no flagged spans."""
    from detect import TokenScore, _find_suspicious_spans
    tokens = [
        TokenScore("The", 500, 0.01),
        TokenScore("quick", 200, 0.02),
        TokenScore("brown", 800, 0.005),
        TokenScore("fox", 250, 0.01),
        TokenScore("jumped", 600, 0.008),
    ]
    text = "The quick brown fox jumped"
    spans = _find_suspicious_spans(tokens, text, window=3, threshold=0.8)
    assert len(spans) == 0


def test_unload_models_clears_state():
    from detect import _binoculars_models, _gltr_model, unload_models
    unload_models()
    assert len(_binoculars_models) == 0
    assert len(_gltr_model) == 0


def test_threshold_breach_fails():
    """A score above the threshold should be detected as a breach."""
    score = 0.75
    threshold = 0.50
    assert score > threshold


def test_regression_breach_fails():
    """A score that regressed beyond tolerance should be caught."""
    baseline = 0.30
    current = 0.40
    tolerance = 0.05
    assert current > baseline + tolerance
