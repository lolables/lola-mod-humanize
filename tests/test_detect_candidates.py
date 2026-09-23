"""Unit tests for detect_candidates.py -- candidate generator."""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


def test_dataclasses_importable():
    from detect_candidates import VocabularyCandidate, PatternCandidate, ChecklistCandidate
    vc = VocabularyCandidate(
        word="synergize", proposed_tier=2, frequency=3,
        replacements=["combine"], evidence="test", source_file="vocabulary.py"
    )
    assert vc.proposed_tier == 2


def test_dedup_filters_known_words():
    from detect_candidates import VocabularyCandidate, deduplicate_vocab
    candidates = [
        VocabularyCandidate("delve", 1, 5, ["explore"], "test", "vocabulary.py"),
        VocabularyCandidate("synergize", 2, 3, ["combine"], "test", "vocabulary.py"),
    ]
    filtered = deduplicate_vocab(candidates)
    words = [c.word for c in filtered]
    assert "delve" not in words
    assert "synergize" in words


def test_tier1_requires_3_samples():
    from detect_candidates import VocabularyCandidate, filter_by_frequency
    candidates = [
        VocabularyCandidate("newword", 1, 2, ["alt"], "test", "vocabulary.py"),
        VocabularyCandidate("another", 1, 3, ["alt"], "test", "vocabulary.py"),
        VocabularyCandidate("lowertier", 2, 2, ["alt"], "test", "vocabulary.py"),
    ]
    filtered = filter_by_frequency(candidates)
    words = [c.word for c in filtered]
    assert "newword" not in words
    assert "another" in words
    assert "lowertier" in words


def test_write_candidates_creates_files(tmp_path):
    from detect_candidates import VocabularyCandidate, write_candidates
    candidates = {
        "vocabulary": [
            VocabularyCandidate("synergize", 2, 3, ["combine"], "test", "vocabulary.py"),
        ],
        "patterns": [],
        "checklist": [],
    }
    write_candidates(candidates, tmp_path)
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "vocabulary.yml").exists()
