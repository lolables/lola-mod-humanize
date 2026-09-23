"""detect_candidates.py -- Generate improvement candidates from detection analysis.

Produces vocabulary, pattern, and checklist candidates. Writes to a
staging directory for human review via --review CLI.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

_skill_scripts = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts'
if str(_skill_scripts) not in sys.path:
    sys.path.insert(0, str(_skill_scripts))

from vocabulary import ALL_KNOWN, CANDIDATE_PATTERNS

STAGING_ROOT = Path(__file__).resolve().parent.parent / '.test-output' / 'improvement-candidates'

# GPT-2's BPE tokenizer splits identifiers into subword fragments
# (e.g. "@dataclass" -> "@ dat ac lass"). When we reconstruct span text
# from tokens, these fragments produce garbage like "lasses import dat
# ac lass". This regex catches subword noise: runs of 1-2 char fragments
# separated by spaces that don't form real words.
import re
_SUBWORD_NOISE_RE = re.compile(r'^[a-z]{1,2}$')

# Combined regex from vocabulary.py CANDIDATE_PATTERNS. These are words
# the AI-detection research community has identified as overrepresented
# in LLM output (200%+ frequency increase post-2022). We only propose
# vocabulary candidates that match both signals:
#   1. GLTR flags the word as highly predictable in context
#   2. Research identifies it as AI-characteristic
# This dual-signal filter prevents common English words (config, pool,
# container) from becoming candidates just because they're predictable.
_RESEARCH_VOCAB_RE = re.compile(
    '|'.join(CANDIDATE_PATTERNS), re.IGNORECASE
)


def _clean_span_words(span_text: str) -> list[str]:
    """Extract real words from span text, filtering tokenizer artifacts.

    BPE tokenizers split words into subword units that look like noise
    when joined with spaces. We skip fragments under 3 chars and strip
    common punctuation. This prevents "dat", "ac", "lass" from becoming
    vocabulary candidates when the tokenizer split "@dataclass".
    """
    words = []
    for word in span_text.lower().split():
        word = word.strip(".,;:!?\"'()[]@#{}\\")
        if len(word) < 3:
            continue
        if _SUBWORD_NOISE_RE.match(word):
            continue
        words.append(word)
    return words


@dataclass
class VocabularyCandidate:
    word: str
    proposed_tier: int
    frequency: int
    replacements: list[str]
    evidence: str
    source_file: str


@dataclass
class PatternCandidate:
    name: str
    description: str
    example_before: str
    example_fix: str
    detection_signal: str
    frequency: int
    source_file: str


@dataclass
class ChecklistCandidate:
    pass_number: int
    item_text: str
    rationale: str
    source_file: str


def deduplicate_vocab(candidates: list[VocabularyCandidate]) -> list[VocabularyCandidate]:
    return [c for c in candidates if c.word.lower() not in ALL_KNOWN]


def filter_by_frequency(candidates: list[VocabularyCandidate]) -> list[VocabularyCandidate]:
    # Tier 1 needs 3+ samples to reduce false positives.
    # Lower tiers accept 2+.
    result = []
    for c in candidates:
        min_freq = 3 if c.proposed_tier == 1 else 2
        if c.frequency >= min_freq:
            result.append(c)
    return result


def write_candidates(candidates: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    vocab = candidates.get("vocabulary", [])
    patterns = candidates.get("patterns", [])
    checklist = candidates.get("checklist", [])

    summary = f"# Improvement Candidates\n\n"
    summary += f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
    summary += f"- Vocabulary: {len(vocab)} candidates\n"
    summary += f"- Patterns: {len(patterns)} candidates\n"
    summary += f"- Checklist: {len(checklist)} candidates\n"
    (output_dir / "summary.md").write_text(summary)

    for name, items in [("vocabulary", vocab), ("patterns", patterns), ("checklist", checklist)]:
        data = [asdict(item) for item in items]
        (output_dir / f"{name}.yml").write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )
    return output_dir


def generate_candidates(analyses: list, code_samples: set[str] = None) -> dict:
    """Generate candidates from detect_analyze.analyze_results() output.

    code_samples: set of sample names that are code (not prose). Code
    samples are excluded from vocabulary extraction because programming
    tokens (import, self, config, return) are always GLTR top-10
    predictable regardless of authorship. Including them floods the
    candidate list with language keywords instead of AI-tell vocabulary.

    Note: candidates feed a human review step, not automatic removal.
    The goal is natural frequency, not zero frequency. A document
    scrubbed of every AI-associated word is itself a detection signal
    (see reference/methodology.md "The overcorrection trap"). Reviewers
    should accept candidates only when the word is genuinely overused
    relative to human baselines.
    """
    from detect_analyze import UnknownPattern

    code_samples = code_samples or set()
    vocab_candidates: list[VocabularyCandidate] = []
    pattern_candidates: list[PatternCandidate] = []
    checklist_candidates: list[ChecklistCandidate] = []

    # Extract vocabulary candidates using dual-signal filtering:
    #   Signal 1: GLTR flags the word as highly predictable in context
    #   Signal 2: Word matches CANDIDATE_PATTERNS from vocabulary research
    #
    # Why both signals? GLTR alone produces too many false positives.
    # Common words like "config", "container", "security" are GLTR top-10
    # predictable in technical prose because they're domain vocabulary,
    # not because an AI wrote them. The research patterns filter for words
    # that studies have shown are specifically overrepresented in LLM
    # output (e.g. "noteworthy", "cultivate", "encompass").
    #
    # Code samples are excluded entirely: programming tokens are always
    # predictable regardless of authorship.
    word_freq: dict[str, int] = {}
    for analysis in analyses:
        if analysis.sample in code_samples:
            continue
        for dr in analysis.detection_results:
            if dr.source != "gltr":
                continue
            for span in dr.flagged_spans:
                # Check the full span text against research patterns
                research_hits = _RESEARCH_VOCAB_RE.findall(span.text)
                for word in research_hits:
                    w = word.lower().strip()
                    if w and w not in ALL_KNOWN:
                        word_freq[w] = word_freq.get(w, 0) + 1

    for word, freq in word_freq.items():
        vocab_candidates.append(VocabularyCandidate(
            word=word, proposed_tier=3, frequency=freq,
            replacements=[], evidence=f"GLTR flagged + research-backed ({freq} spans)",
            source_file="scripts/vocabulary.py",
        ))

    # Pattern candidates from unknown cross-sample patterns
    all_unknowns: list[UnknownPattern] = []
    for analysis in analyses:
        all_unknowns.extend(analysis.unknown_patterns)

    for unknown in all_unknowns:
        if unknown.sample_count < 2:
            continue
        # Skip patterns that are just tokenizer noise (subword fragments,
        # whitespace-only spans). These come from GPT-2 BPE splitting
        # identifiers like @dataclass into "@ dat ac lass".
        example = unknown.spans[0].text if unknown.spans else ""
        real_words = _clean_span_words(example)
        if len(real_words) < 2:
            continue
        pattern_candidates.append(PatternCandidate(
            name=unknown.proposed_category,
            description=unknown.proposed_description,
            example_before=example,
            example_fix="(review needed)",
            detection_signal=unknown.spans[0].reason if unknown.spans else "",
            frequency=unknown.sample_count,
            source_file="reference/structural-patterns.md",
        ))

    vocab_candidates = deduplicate_vocab(vocab_candidates)
    vocab_candidates = filter_by_frequency(vocab_candidates)

    return {
        "vocabulary": vocab_candidates,
        "patterns": pattern_candidates,
        "checklist": checklist_candidates,
    }


def review_candidates(staging_dir: Path) -> None:
    if not staging_dir.exists():
        print(f"No candidates at {staging_dir}")
        return
    dirs = sorted([d for d in staging_dir.iterdir() if d.is_dir()], reverse=True)
    if not dirs:
        print("No candidate batches found.")
        return
    latest = dirs[0]
    print(f"Reviewing: {latest.name}\n")
    summary = (latest / "summary.md").read_text()
    print(summary)

    total = 0
    for name in ["vocabulary", "patterns", "checklist"]:
        path = latest / f"{name}.yml"
        if path.exists():
            total += len(json.loads(path.read_text()))

    if total == 0:
        print("No candidates to review. All .after.* samples passed dual-signal")
        print("filtering (GLTR predictability + research-backed vocabulary).")
        print("")
        print("This means the current samples don't contain words that are both")
        print("statistically predictable AND flagged by AI-detection research.")
        print("The feedback loop will surface candidates when new samples or")
        print("skill changes introduce AI-characteristic patterns.")
        return

    for name in ["vocabulary", "patterns", "checklist"]:
        path = latest / f"{name}.yml"
        if not path.exists():
            continue
        items = json.loads(path.read_text())
        if not items:
            continue
        print(f"\n--- {name.upper()} CANDIDATES ---\n")
        for i, item in enumerate(items):
            print(f"[{i+1}] {json.dumps(item, indent=2)}")
            choice = input("  (a)ccept / (r)eject / (s)kip: ").strip().lower()
            if choice == 'a':
                print(f"  -> Accepted: {item.get('word', item.get('name', 'item'))}")
            elif choice == 'r':
                print("  -> Rejected")
            else:
                print("  -> Skipped")


def main():
    parser = argparse.ArgumentParser(description="Detection improvement candidates")
    parser.add_argument('--review', action='store_true', help="Review staged candidates")
    parser.add_argument('--output', type=Path, default=None, help="Output directory")
    args = parser.parse_args()
    if args.review:
        review_candidates(STAGING_ROOT)
    else:
        print("Run 'task improve' first to generate candidates.")


if __name__ == '__main__':
    main()
