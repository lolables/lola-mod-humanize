"""
test_vocabulary_regression.py -- Pins the derived vocabulary values.

Written before the single-source migration so that migration is provably
behavior-preserving. Its baseline is the state at the START of the migration,
which already included the corpus-backed vocabulary additions made earlier on
this branch. It therefore constrains the MIGRATION, not the branch as a whole.

The migration's only intended change is three Tier 5 phrases becoming
scannable: they were documented in the watchlist but never reached the
scanner.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts'))

import vocabulary as v

TIER1 = {
    'delve', 'tapestry', 'landscape', 'meticulous', 'meticulously',
    'pivotal', 'underscore', 'intricate', 'intricacies', 'interplay',
    'vibrant', 'testament', 'enduring', 'garner', 'highlight', 'seamless',
    'foster', 'cultivate', 'bolster', 'remarkable', 'commendable',
    'dive into', 'deep dive',
}
TIER2 = {
    'align with', 'bolstered', 'showcasing', 'fostering', 'highlighting',
    'emphasizing', 'enhance', 'enhanced', 'showcase', 'innovative',
    'emphasized', 'cutting-edge', 'showcased', 'resonate with',
    'encompassing', 'ever-evolving',
}
TIER3 = {
    'additionally', 'furthermore', 'moreover', 'crucial', 'robust',
    'comprehensive', 'seamlessly', 'groundbreaking', 'transformative',
    'compelling', 'facilitate', 'illuminate', 'endeavor', 'paradigm',
    'harness', 'navigate', 'realm', 'leverage', 'embark', 'holistic',
    'synergy', 'multifaceted', 'nuanced', 'highlighted', 'noteworthy',
    'utilize', 'paramount', 'invaluable', 'thrive',
}
BANNED_PHRASES = {
    'serves as a', 'boasts a', 'diverse array', 'plays a vital role',
    "in today's", 'in conclusion', "it's important to note",
    'rich tapestry', 'rich cultural', 'commitment to excellence',
    'not just', 'not only',
}
TRANSITIONS = {'additionally,', 'furthermore,', 'moreover,'}
OPENERS = {
    "in today's", 'as organizations increasingly', 'in an era of',
    'in the rapidly evolving', 'as the world becomes',
}
CLOSERS = {
    'in conclusion', 'to summarize', 'by following these best practices',
    'as we have seen', 'in this article', 'in this section',
}
# Tier 5 rows documented but never scanned before the migration.
NEWLY_SCANNED = {'it is worth noting', 'one might argue', 'this raises the question'}


def test_tier_word_sets_unchanged():
    assert v.TIER1_WORDS == TIER1
    assert v.TIER2_WORDS == TIER2
    assert v.TIER3_WORDS == TIER3


def test_transition_starters_unchanged():
    assert set(v.TRANSITION_STARTERS) == TRANSITIONS


def test_banned_phrases_are_superset_of_today():
    """Migration may only add NEWLY_SCANNED; nothing may disappear."""
    actual = set(v.BANNED_PHRASES)
    assert BANNED_PHRASES <= actual, f'lost: {BANNED_PHRASES - actual}'
    assert actual - BANNED_PHRASES <= NEWLY_SCANNED, (
        f'unexpected additions: {actual - BANNED_PHRASES - NEWLY_SCANNED}'
    )


def test_openers_and_closers_unchanged():
    """Before Task 9 these live in pre-scan.py; after, in vocabulary.py."""
    openers = getattr(v, 'GENERIC_OPENERS', None)
    closers = getattr(v, 'GENERIC_CLOSERS', None)
    if openers is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'prescan',
            REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts' / 'pre-scan.py',
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        openers, closers = mod.GENERIC_OPENERS, mod.GENERIC_CLOSERS
    assert set(openers) == OPENERS
    assert set(closers) == CLOSERS
