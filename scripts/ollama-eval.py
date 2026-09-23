#!/usr/bin/env python3
"""
ollama-eval.py -- Evaluate Humanize skill effectiveness across Ollama models.

Sends AI-generated text samples through local Ollama models with the Humanize
skill prompt, then scores the output against detection heuristics.

Usage:
    python3 scripts/ollama-eval.py                          # all models, all samples
    python3 scripts/ollama-eval.py --models mistral llama3.2 # specific models
    python3 scripts/ollama-eval.py --samples 01 05           # specific samples
    python3 scripts/ollama-eval.py --host localhost          # override host

Environment:
    OLLAMA_HOST  -- Ollama API host (default: localhost)
    OLLAMA_PORT  -- Ollama API port (default: 11434)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

# --- Config ---

DEFAULT_HOST = os.environ.get('OLLAMA_HOST', 'localhost')
DEFAULT_PORT = int(os.environ.get('OLLAMA_PORT', '11434'))

MIN_SENTENCES_FOR_SD = 5  # burstiness needs enough sentences to be meaningful

# Models to test (must fit in 10GB VRAM)
DEFAULT_MODELS = [
    'granite4:latest',       # 2.1GB -- small, fast baseline
    'llama3.2:latest',       # 2.0GB -- small llama
    'gemma3:4b',             # 3.3GB -- google small
    'mistral:latest',        # 4.4GB -- strong 7B
    'qwen2.5-coder:7b-instruct',  # 4.7GB -- code-focused
    'cogito:latest',         # 4.9GB -- reasoning-focused
    'llama3.1:8b',           # 4.9GB -- larger llama
    'qwen3:8b',              # 5.2GB -- strong 8B
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = PROJECT_ROOT / 'tests' / 'text-samples'
REFERENCE_DIR = PROJECT_ROOT / 'reference'
OUTPUT_DIR = PROJECT_ROOT / '.test-output' / 'ollama-eval'


# --- AI Detection Heuristics ---

# vocabulary.py lives in the skill scripts directory, not in scripts/
import sys as _sys
_skill_scripts = PROJECT_ROOT / 'module' / 'skills' / 'humanize' / 'scripts'
if str(_skill_scripts) not in _sys.path:
    _sys.path.insert(0, str(_skill_scripts))

from vocabulary import (  # noqa: E402
    BANNED_PHRASES, TIER1_WORDS, TIER2_WORDS, TIER3_WORDS,
    TRANSITION_STARTERS,
)


@dataclass
class ScoreCard:
    """Scores for a single Humanize evaluation."""
    model: str
    sample: str
    tier1_count: int = 0
    tier2_count: int = 0
    tier3_count: int = 0
    banned_phrase_count: int = 0
    transition_count: int = 0
    em_dash_count: int = 0
    sentence_length_sd: float = 0.0
    sentence_count: int = 0
    bold_count: int = 0
    word_count: int = 0
    generation_time_s: float = 0.0
    raw_output: str = ''
    tier1_found: list = field(default_factory=list)
    tier2_found: list = field(default_factory=list)
    tier3_found: list = field(default_factory=list)
    phrases_found: list = field(default_factory=list)
    error: str = ''
    binoculars_score: float | None = None
    gltr_profile: dict | None = None

    @property
    def total_ai_words(self) -> int:
        return self.tier1_count + self.tier2_count + self.tier3_count

    @property
    def ai_density(self) -> float:
        """AI words per 500 words."""
        if self.word_count == 0:
            return 0
        return (self.total_ai_words / self.word_count) * 500

    @property
    def passed(self) -> bool:
        return (
            self.tier1_count == 0
            and self.ai_density <= 2.0
            and self.banned_phrase_count == 0
            and self.transition_count == 0
            and self.em_dash_count == 0
            and (self.sentence_count < MIN_SENTENCES_FOR_SD
                 or self.sentence_length_sd >= 5.0)
            and not self.error
        )

    @property
    def grade(self) -> str:
        if self.error:
            return 'ERR'
        score = 100
        score -= self.tier1_count * 15
        score -= self.tier2_count * 8
        score -= self.tier3_count * 3
        score -= self.banned_phrase_count * 10
        score -= self.transition_count * 5
        score -= self.em_dash_count * 5
        score -= self.bold_count * 2
        if self.sentence_count >= MIN_SENTENCES_FOR_SD:
            if self.sentence_length_sd < 5:
                score -= 15
            elif self.sentence_length_sd < 8:
                score -= 5
        score = max(0, min(100, score))
        if score >= 90:
            return 'A'
        if score >= 75:
            return 'B'
        if score >= 60:
            return 'C'
        if score >= 40:
            return 'D'
        return 'F'


def score_text(text: str) -> dict:
    """Run detection heuristics on text, return raw findings."""
    text_lower = text.lower()
    words = text.split()
    word_count = len(words)

    # Vocabulary
    t1_found, t2_found, t3_found = [], [], []
    for w in TIER1_WORDS:
        count = len(re.findall(r'\b' + re.escape(w) + r'\b', text_lower))
        if count:
            t1_found.extend([w] * count)
    for w in TIER2_WORDS:
        count = len(re.findall(r'\b' + re.escape(w) + r'\b', text_lower))
        if count:
            t2_found.extend([w] * count)
    for w in TIER3_WORDS:
        count = len(re.findall(r'\b' + re.escape(w) + r'\b', text_lower))
        if count:
            t3_found.extend([w] * count)

    # Banned phrases
    phrases = []
    for phrase in BANNED_PHRASES:
        count = text_lower.count(phrase)
        if count:
            phrases.extend([phrase] * count)

    # Transitions at sentence start
    transitions = 0
    for starter in TRANSITION_STARTERS:
        transitions += len(re.findall(
            r'(?:^|\.\s+)' + re.escape(starter), text_lower
        ))

    # Em dashes
    em_dashes = len(re.findall(r'\u2014', text))

    # Sentence length SD
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s for s in sentences if len(s.split()) > 2]
    if len(sentences) > 1:
        lengths = [len(s.split()) for s in sentences]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        sd = variance ** 0.5
    else:
        sd = 0.0

    # Bold count
    bold = len(re.findall(r'\*\*[^*]+\*\*', text))

    return {
        'tier1_found': t1_found,
        'tier2_found': t2_found,
        'tier3_found': t3_found,
        'phrases_found': phrases,
        'transition_count': transitions,
        'em_dash_count': em_dashes,
        'sentence_length_sd': round(sd, 1),
        'sentence_count': len(sentences),
        'bold_count': bold,
        'word_count': word_count,
    }


def score_detection(text: str) -> dict:
    """Run Binoculars + GLTR detection. Returns dict or empty if unavailable."""
    try:
        from detect import detect, gpu_available
        if not gpu_available():
            return {}
        results = detect(text)
        out = {}
        for r in results:
            if r.source == "binoculars":
                out["binoculars_score"] = round(r.score, 4)
            elif r.source == "gltr":
                out["gltr_profile"] = r.metadata.get("buckets", {})
        return out
    except Exception as e:
        return {"error": str(e)}


# --- Ollama API ---

def ollama_url(host: str, port: int, path: str) -> str:
    return f'http://{host}:{port}{path}'


def ollama_generate(host: str, port: int, model: str, prompt: str,
                    system: str = '', timeout: int = 300,
                    num_ctx: int = 16384) -> tuple[str, float]:
    """Generate text from Ollama. Returns (text, elapsed_seconds)."""
    url = ollama_url(host, port, '/api/generate')
    payload = {
        'model': model,
        'prompt': prompt,
        'system': system,
        'stream': False,
        'options': {
            'temperature': 0.7,
            'num_predict': 2048,
            'num_ctx': num_ctx,
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                headers={'Content-Type': 'application/json'})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
        elapsed = time.time() - start
        return result.get('response', ''), elapsed
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return f'ERROR: {e}', time.time() - start


def ollama_unload(host: str, port: int, model: str):
    """Unload a model from VRAM by setting keep_alive to 0."""
    url = ollama_url(host, port, '/api/generate')
    payload = {
        'model': model,
        'prompt': '',
        'keep_alive': 0,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except Exception:
        pass  # best-effort unload


def ollama_list_models(host: str, port: int) -> list[str]:
    """List available models."""
    url = ollama_url(host, port, '/api/tags')
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return [m['name'] for m in data.get('models', [])]
    except Exception:
        return []


# --- Prompt Construction ---

def build_humanize_system_prompt() -> str:
    """Build the system prompt from the Humanize skill and reference files."""
    parts = []

    skill_path = REFERENCE_DIR.parent / 'module' / 'skills' / 'humanize' / 'SKILL.md'
    if skill_path.exists():
        parts.append(skill_path.read_text())

    for ref in ['ai-vocabulary-watchlist.md', 'structural-patterns.md']:
        ref_path = REFERENCE_DIR / ref
        if ref_path.exists():
            parts.append(ref_path.read_text())

    # Prefer XDG voice profile, then repo-local, then default (blog for eval)
    xdg_config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    voice_candidates = [
        xdg_config / 'humanize' / 'voices' / 'blog.local.md',
        REFERENCE_DIR / 'voices' / 'blog.local.md',
        REFERENCE_DIR / 'voices' / 'blog.md',
    ]
    voice_path = next((p for p in voice_candidates if p.exists()), None)
    if voice_path:
        parts.append(voice_path.read_text())

    return '\n\n---\n\n'.join(parts)


def build_transform_prompt(sample_text: str) -> str:
    """Build the user prompt asking for transformation."""
    return dedent(f"""\
        Transform the following text using the Humanize methodology. Apply all five
        passes. Output ONLY the transformed text, nothing else. No preamble, no
        explanation, no pass-by-pass breakdown. Just the final result.

        ---

        {sample_text}
    """)


# --- Main Evaluation ---

def evaluate_sample(host: str, port: int, model: str, sample_name: str,
                    sample_text: str, system_prompt: str,
                    num_ctx: int = 16384) -> ScoreCard:
    """Run a single model+sample evaluation."""
    card = ScoreCard(model=model, sample=sample_name)

    prompt = build_transform_prompt(sample_text)
    output, elapsed = ollama_generate(host, port, model, prompt,
                                      system=system_prompt, timeout=600,
                                      num_ctx=num_ctx)
    card.generation_time_s = round(elapsed, 1)

    if output.startswith('ERROR:'):
        card.error = output
        return card

    card.raw_output = output

    findings = score_text(output)
    card.tier1_found = findings['tier1_found']
    card.tier2_found = findings['tier2_found']
    card.tier3_found = findings['tier3_found']
    card.tier1_count = len(findings['tier1_found'])
    card.tier2_count = len(findings['tier2_found'])
    card.tier3_count = len(findings['tier3_found'])
    card.phrases_found = findings['phrases_found']
    card.banned_phrase_count = len(findings['phrases_found'])
    card.transition_count = findings['transition_count']
    card.em_dash_count = findings['em_dash_count']
    card.sentence_length_sd = findings['sentence_length_sd']
    card.sentence_count = findings['sentence_count']
    card.bold_count = findings['bold_count']
    card.word_count = findings['word_count']

    return card


def load_samples(filter_ids: list[str] | None = None) -> dict[str, str]:
    """Load before-samples from the test directory."""
    samples = {}
    for path in sorted(SAMPLES_DIR.glob('*.before.md')):
        name = path.stem.replace('.before', '')
        if filter_ids and not any(fid in name for fid in filter_ids):
            continue
        samples[name] = path.read_text()
    return samples


def print_card(card: ScoreCard, verbose: bool = False):
    """Print a single score card."""
    status = 'PASS' if card.passed else 'FAIL'
    if card.error:
        status = 'ERR '

    print(f'  {status}  {card.grade:>2s}  '
          f't1={card.tier1_count} t2={card.tier2_count} t3={card.tier3_count}  '
          f'phrases={card.banned_phrase_count}  '
          f'trans={card.transition_count}  '
          f'em={card.em_dash_count}  '
          f'sd={card.sentence_length_sd:4.1f}  '
          f'bold={card.bold_count}  '
          f'{card.generation_time_s:5.1f}s  '
          f'{card.sample}')

    if verbose and (card.tier1_found or card.tier2_found or card.phrases_found):
        if card.tier1_found:
            print(f'         T1: {", ".join(card.tier1_found)}')
        if card.tier2_found:
            print(f'         T2: {", ".join(card.tier2_found)}')
        if card.tier3_found:
            print(f'         T3: {", ".join(card.tier3_found)}')
        if card.phrases_found:
            print(f'         Phrases: {", ".join(card.phrases_found)}')
    if card.error:
        print(f'         Error: {card.error[:120]}')


def write_report(all_cards: list[ScoreCard], output_dir: Path):
    """Write detailed Markdown report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = ['# Humanize Ollama Evaluation Report\n']
    lines.append(f'Generated: {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}\n')

    # Summary table
    lines.append('## Summary\n')
    lines.append('| Model | Sample | Grade | T1 | T2 | T3 | Phrases | Trans | EmDash | SD | Bold | Time | Bino | GLTR top10 |')
    lines.append('|-------|--------|-------|----|----|----|---------| ------|--------|-----|------|------|------|------------|')
    for c in all_cards:
        status = 'PASS' if c.passed else ('ERR' if c.error else 'FAIL')
        bino = f'{c.binoculars_score:.3f}' if c.binoculars_score is not None else '-'
        gltr = f'{c.gltr_profile.get("top10", "-")}%' if c.gltr_profile else '-'
        lines.append(
            f'| {c.model} | {c.sample} | {c.grade} ({status}) | '
            f'{c.tier1_count} | {c.tier2_count} | {c.tier3_count} | '
            f'{c.banned_phrase_count} | {c.transition_count} | '
            f'{c.em_dash_count} | {c.sentence_length_sd} | '
            f'{c.bold_count} | {c.generation_time_s}s | {bino} | {gltr} |'
        )
    lines.append('')

    # Per-model summary
    models = sorted(set(c.model for c in all_cards))
    lines.append('## Per-Model Summary\n')
    for model in models:
        model_cards = [c for c in all_cards if c.model == model]
        passed = sum(1 for c in model_cards if c.passed)
        total = len(model_cards)
        avg_t1 = sum(c.tier1_count for c in model_cards) / max(total, 1)
        avg_sd = sum(c.sentence_length_sd for c in model_cards) / max(total, 1)
        avg_time = sum(c.generation_time_s for c in model_cards) / max(total, 1)
        lines.append(f'### {model}\n')
        lines.append(f'- Pass rate: {passed}/{total}')
        lines.append(f'- Avg Tier 1 words: {avg_t1:.1f}')
        lines.append(f'- Avg sentence SD: {avg_sd:.1f}')
        lines.append(f'- Avg generation time: {avg_time:.1f}s')

        failures = [c for c in model_cards if not c.passed and not c.error]
        if failures:
            lines.append(f'- Failure patterns:')
            for c in failures:
                issues = []
                if c.tier1_found:
                    issues.append(f'T1: {", ".join(set(c.tier1_found))}')
                if c.phrases_found:
                    issues.append(f'Phrases: {", ".join(set(c.phrases_found))}')
                if c.transition_count:
                    issues.append(f'{c.transition_count} transitions')
                if c.em_dash_count:
                    issues.append(f'{c.em_dash_count} em dashes')
                if c.sentence_count >= MIN_SENTENCES_FOR_SD and c.sentence_length_sd < 5:
                    issues.append(f'low SD ({c.sentence_length_sd})')
                if c.ai_density > 2.0:
                    extra = sorted(set(c.tier2_found) | set(c.tier3_found))
                    label = f' ({", ".join(extra)})' if extra else ''
                    issues.append(f'AI density {c.ai_density:.1f}/500{label}')
                lines.append(f'  - {c.sample}: {"; ".join(issues)}')
        lines.append('')

    # Write individual outputs
    for c in all_cards:
        if c.raw_output:
            out_path = output_dir / f'{c.model.replace(":", "_")}_{c.sample}.md'
            out_path.write_text(c.raw_output)

    report_path = output_dir / 'eval-report.md'
    report_path.write_text('\n'.join(lines))
    print(f'\nDetailed report: {report_path}')


def _run_detect_only(args):
    """Score existing .after.* samples with detection only (no Ollama)."""
    from detect import gpu_available
    if not gpu_available():
        print("Detection requires torch + transformers.", file=sys.stderr)
        print("Install with: uv pip install -e '.[ai-detect]'", file=sys.stderr)
        sys.exit(1)

    from detect import detect, unload_models
    from detect_analyze import analyze_results
    from detect_candidates import generate_candidates, write_candidates, STAGING_ROOT
    from datetime import datetime, timezone

    # Load .after.* samples, tracking content type for detection tuning.
    # Code samples use relaxed GLTR thresholds because programming tokens
    # are inherently predictable (see detect.py GLTR_SPAN_PARAMS).
    after_dir = PROJECT_ROOT / 'tests'
    samples = {}       # name -> text
    sample_types = {}  # name -> "prose" or "code"
    for subdir in ('text-samples', 'code-samples'):
        d = after_dir / subdir
        if not d.exists():
            continue
        ctype = "code" if "code" in subdir else "prose"
        for f in sorted(d.glob('*.after.*')):
            name = f.name.split('.after.')[0]
            samples[name] = f.read_text()
            sample_types[name] = ctype

    if not samples:
        print('No .after.* samples found.', file=sys.stderr)
        sys.exit(1)

    print(f'Detection-only mode: {len(samples)} samples')
    print()

    all_cards = []
    sample_results = []

    for name, text in samples.items():
        card = ScoreCard(model='(static)', sample=name)
        card.raw_output = text

        # Heuristic scoring
        findings = score_text(text)
        card.tier1_found = findings['tier1_found']
        card.tier2_found = findings['tier2_found']
        card.tier3_found = findings['tier3_found']
        card.tier1_count = len(findings['tier1_found'])
        card.tier2_count = len(findings['tier2_found'])
        card.tier3_count = len(findings['tier3_found'])
        card.phrases_found = findings['phrases_found']
        card.banned_phrase_count = len(findings['phrases_found'])
        card.transition_count = findings['transition_count']
        card.em_dash_count = findings['em_dash_count']
        card.sentence_length_sd = findings['sentence_length_sd']
        card.sentence_count = findings['sentence_count']
        card.bold_count = findings['bold_count']
        card.word_count = findings['word_count']

        # Detection scoring
        det_results = detect(text, content_type=sample_types.get(name, "prose"))
        for r in det_results:
            if r.source == 'binoculars':
                card.binoculars_score = round(r.score, 4)
            elif r.source == 'gltr':
                card.gltr_profile = r.metadata.get('buckets', {})
        sample_results.append((name, det_results))

        all_cards.append(card)
        print_card(card)
        if card.binoculars_score is not None:
            print(f'         Binoculars: {card.binoculars_score:.3f}')
        if card.gltr_profile:
            p = card.gltr_profile
            print(f'         GLTR: top10={p.get("top10", "?")}% top100={p.get("top100", "?")}%')

    unload_models()

    # Run correlation + candidate generation
    analyses = analyze_results(sample_results)
    code_names = {n for n, t in sample_types.items() if t == "code"}
    candidates = generate_candidates(analyses, code_samples=code_names)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%S')
    staging = STAGING_ROOT / ts
    write_candidates(candidates, staging)

    # Write report
    out_dir = args.output or OUTPUT_DIR
    write_report(all_cards, out_dir)

    total = len(all_cards)
    passed = sum(1 for c in all_cards if c.passed)
    print(f'\n=== {passed}/{total} passed ===')
    print(f'Candidates: {staging}')


def main():
    parser = argparse.ArgumentParser(description='Humanize Ollama evaluation')
    parser.add_argument('--host', default=DEFAULT_HOST,
                        help=f'Ollama host (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Ollama port (default: {DEFAULT_PORT})')
    parser.add_argument('--models', nargs='+', default=None,
                        help='Models to test (default: all under 10GB)')
    parser.add_argument('--samples', nargs='+', default=None,
                        help='Sample IDs to test (e.g., 01 05)')
    parser.add_argument('--num-ctx', type=int, default=16384,
                        help='Context window size for Ollama (default: 16384)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed findings per card')
    parser.add_argument('--with-detect', action='store_true',
                        help='Include Binoculars + GLTR detection scoring')
    parser.add_argument('--detect-only', action='store_true',
                        help='Run detection on .after.* samples only (no Ollama)')
    parser.add_argument('--output', type=Path, default=None,
                        help='Output directory for reports')
    args = parser.parse_args()

    if args.detect_only:
        _run_detect_only(args)
        return

    # Verify connectivity
    available = ollama_list_models(args.host, args.port)
    if not available:
        print(f'Cannot reach Ollama at {args.host}:{args.port}', file=sys.stderr)
        sys.exit(1)

    models = args.models or DEFAULT_MODELS
    models = [m for m in models if m in available]
    if not models:
        print(f'None of the requested models are available.', file=sys.stderr)
        print(f'Available: {", ".join(available)}', file=sys.stderr)
        sys.exit(1)

    samples = load_samples(args.samples)
    if not samples:
        print('No samples found.', file=sys.stderr)
        sys.exit(1)

    system_prompt = build_humanize_system_prompt()

    print(f'Humanize Ollama Evaluation')
    print(f'Host: {args.host}:{args.port}')
    print(f'Models: {", ".join(models)}')
    print(f'Samples: {", ".join(samples.keys())}')
    print(f'System prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)')
    print(f'Context window: {args.num_ctx} tokens')
    print()

    all_cards = []

    for model in models:
        print(f'=== {model} ===')

        for sample_name, sample_text in samples.items():
            card = evaluate_sample(
                args.host, args.port, model, sample_name,
                sample_text, system_prompt, num_ctx=args.num_ctx,
            )
            all_cards.append(card)
            print_card(card, verbose=args.verbose)
            if args.with_detect:
                det = score_detection(card.raw_output)
                card.binoculars_score = det.get('binoculars_score')
                card.gltr_profile = det.get('gltr_profile')
                if card.binoculars_score is not None:
                    print(f'         Binoculars: {card.binoculars_score:.3f}')

        # Unload model to free VRAM
        print(f'  Unloading {model}...')
        ollama_unload(args.host, args.port, model)
        time.sleep(2)  # brief pause for VRAM release
        print()

    # Summary
    total = len(all_cards)
    passed = sum(1 for c in all_cards if c.passed)
    errors = sum(1 for c in all_cards if c.error)
    print(f'=== TOTAL: {passed}/{total} passed, {errors} errors ===')

    write_report(all_cards, OUTPUT_DIR)


if __name__ == '__main__':
    main()
