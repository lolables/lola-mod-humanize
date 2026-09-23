"""detect.py -- AI text detection via Binoculars and GLTR algorithms.

Implements Binoculars (ICML 2024) cross-perplexity ratio and GLTR per-token
rank analysis using torch + transformers. Both algorithms run locally;
no third-party detection packages needed.

Optional dependency: install via `uv pip install -e ".[ai-detect]"`
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Optional

_TORCH_AVAILABLE = False
try:
    import torch
    import transformers
    _TORCH_AVAILABLE = True
except ImportError:
    pass


@dataclass
class TokenScore:
    token: str
    rank: int
    prob: float


@dataclass
class SpanFlag:
    start: int
    end: int
    text: str
    reason: str
    severity: float


@dataclass
class DetectionResult:
    source: str
    score: float
    label: str
    token_scores: list[TokenScore] = field(default_factory=list)
    flagged_spans: list[SpanFlag] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def gpu_available() -> bool:
    return _TORCH_AVAILABLE


def detect(text: str, tools: Optional[list[str]] = None,
           content_type: str = "prose") -> list[DetectionResult]:
    """Run AI detection tools on text.

    content_type: "prose" or "code". Code uses relaxed GLTR span
    thresholds because programming tokens are inherently predictable
    (keywords, syntax, imports). Prose thresholds catch AI-characteristic
    patterns in natural language where predictability signals generation.
    """
    if not _TORCH_AVAILABLE:
        raise RuntimeError(
            "torch and transformers required for AI detection. "
            "Install with: uv pip install -e '.[ai-detect]'"
        )
    results = []
    run_tools = tools or ["binoculars", "gltr"]
    if "binoculars" in run_tools:
        results.append(_run_binoculars(text))
    if "gltr" in run_tools:
        results.append(_run_gltr(text, content_type=content_type))
    return results


# --- Binoculars (ICML 2024) ---
#
# Observer: tiiuae/falcon-rw-1b (~1.3GB fp16)
# Performer: gpt2-xl (~1.5GB fp16)
#
# These are the smallest viable pair from the Binoculars paper. The
# algorithm computes a cross-perplexity ratio between two models.
# Machine-generated text gets similar perplexity from both (ratio ~1.0);
# human text diverges (ratio >> 1.0). Using different model families
# (falcon vs gpt2) is intentional: if both independently find the text
# predictable, it's likely machine-generated.
#
# Threshold rationale (from first detection run, 2026-03-23):
#   Prose .after.* samples scored 0.21-0.59 (Binoculars)
#   Code .after.* samples scored 0.009-0.093
#   Machine threshold 0.55 catches the worst prose samples
#   Human threshold 0.45 gives a 0.10 uncertainty band
#
# These thresholds intentionally allow some AI-characteristic signal
# through. A Binoculars score of 0.0 (perfectly "human") would itself
# be suspicious: real writing occasionally uses predictable phrasing.
# The goal is natural frequency, not zero frequency. See
# reference/methodology.md "The overcorrection trap" for rationale.
#
# To upgrade: swap both constants to larger models (e.g. falcon-7b +
# llama-2-7b) for better accuracy. Needs 16GB+ VRAM. The GLTR model
# (GLTR_MODEL) reuses BINOCULARS_PERFORMER to save VRAM.

# Override via env vars or Taskfile to use larger models:
#   BINOCULARS_OBSERVER=EleutherAI/gpt-neo-1.3B BINOCULARS_PERFORMER=EleutherAI/gpt-neo-2.7B task improve
# Larger models spill into system RAM via device_map="auto" (accelerate).
# Slower than pure VRAM but more accurate detection.
#
# IMPORTANT: observer and performer must be from the SAME model family
# (e.g. both OPT, both GPT-2, both falcon-rw). Cross-family pairs
# (e.g. OPT + Mistral) produce all-zero Binoculars scores because the
# models disagree on everything, not just AI text. The algorithm needs
# models that share enough structure to agree on machine-generated text
# while diverging on human text.
#
# Stick to ungated models to avoid HuggingFace license gates.
BINOCULARS_OBSERVER = os.environ.get("BINOCULARS_OBSERVER", "tiiuae/falcon-rw-1b")
BINOCULARS_PERFORMER = os.environ.get("BINOCULARS_PERFORMER", "gpt2-xl")
BINOCULARS_MACHINE_THRESHOLD = 0.55
BINOCULARS_HUMAN_THRESHOLD = 0.45

_binoculars_models: dict = {}


def _estimate_model_size(model_name: str) -> int:
    """Estimate model size in bytes from cached weight files.

    Returns 0 if model isn't cached yet (caller should assume it fits
    and let the download + load fail naturally if it doesn't).
    """
    from pathlib import Path
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    safe_name = "models--" + model_name.replace("/", "--")
    snapshots = cache_dir / safe_name / "snapshots"
    if not snapshots.exists():
        return 0
    total = 0
    for snapshot in snapshots.iterdir():
        for f in snapshot.glob("*.safetensors"):
            total += f.stat().st_size
        for f in snapshot.glob("*.bin"):
            total += f.stat().st_size
    return total


def _try_local_first(model_name: str) -> bool:
    """Check if a HuggingFace model is fully cached locally.

    Returns True if cached (skip network), False if not (must download).
    After the initial download, all subsequent loads are offline. This
    prevents the transformers library from sending metadata requests
    to the HF Hub on every run.

    Checks for actual model weight files, not just the directory. A
    partial download (directory exists but no weights) returns False
    to trigger a fresh download.
    """
    from pathlib import Path
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    safe_name = "models--" + model_name.replace("/", "--")
    model_dir = cache_dir / safe_name
    if not model_dir.exists():
        return False
    # Check snapshots dir for actual weight files (.bin or .safetensors)
    snapshots = model_dir / "snapshots"
    if not snapshots.exists():
        return False
    for snapshot in snapshots.iterdir():
        weights = list(snapshot.glob("*.safetensors")) + list(snapshot.glob("*.bin"))
        if weights:
            return True
    return False


def _load_binoculars_models():
    if _binoculars_models:
        return _binoculars_models
    import logging
    # falcon-rw-1b ships with tie_word_embeddings=True but includes both
    # weight tensors. transformers warns about this mismatch on every load.
    # The model works correctly either way; suppress the noise.
    logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Prefer local cache to avoid network requests. HuggingFace Hub
    # API calls transmit IP, model names, and User-Agent on every load
    # unless local_files_only=True. We try local first; fall back to
    # download only if the model isn't cached yet.
    local = _try_local_first(BINOCULARS_PERFORMER)
    tok = AutoTokenizer.from_pretrained(BINOCULARS_PERFORMER, local_files_only=local)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # Loading strategy: check if both models fit in VRAM simultaneously.
    # If yes, load both to GPU (fast, both in memory for inference).
    # If no, set sequential mode: _run_binoculars loads one model at a
    # time, saving logits to CPU between runs. This works with any model
    # on any GPU because only one model occupies VRAM at once.
    #
    # We avoid device_map="auto" entirely. It splits layers across GPU
    # and CPU, but some architectures (OPT) break when embeddings land
    # on a different device than inputs. Sequential loading is simpler
    # and works with every model.
    sequential = False
    if torch.cuda.is_available():
        total_vram = torch.cuda.get_device_properties(0).total_memory
        obs_size = _estimate_model_size(BINOCULARS_OBSERVER)
        perf_size = _estimate_model_size(BINOCULARS_PERFORMER)
        needed = obs_size + perf_size
        if needed > 0 and needed > total_vram * 0.7:
            sequential = True

    if os.environ.get("BINOCULARS_SEQUENTIAL", "").lower() == "true":
        sequential = True

    _binoculars_models["sequential"] = sequential
    _binoculars_models["tokenizer"] = tok
    _binoculars_models["device"] = device

    if sequential:
        # Don't load models yet; _run_binoculars loads one at a time
        _binoculars_models["observer"] = None
        _binoculars_models["performer"] = None
        return _binoculars_models

    observer = AutoModelForCausalLM.from_pretrained(
        BINOCULARS_OBSERVER, torch_dtype=torch.float16,
        local_files_only=_try_local_first(BINOCULARS_OBSERVER),
    ).to(device)
    performer = AutoModelForCausalLM.from_pretrained(
        BINOCULARS_PERFORMER, torch_dtype=torch.float16,
        local_files_only=local,
    ).to(device)
    observer.requires_grad_(False)
    performer.requires_grad_(False)
    _binoculars_models["observer"] = observer
    _binoculars_models["performer"] = performer
    return _binoculars_models


def _compute_binoculars_score(observer_logits, performer_logits) -> float:
    """Cross-perplexity ratio (Algorithm 1). Low = models agree = machine."""
    obs_shift = observer_logits[:, :-1, :].contiguous()
    perf_shift = performer_logits[:, :-1, :].contiguous()
    # Truncate to shared vocab size (models may differ, e.g. gpt2-xl=50257 vs falcon=50304)
    min_vocab = min(obs_shift.size(-1), perf_shift.size(-1))
    obs_shift = obs_shift[:, :, :min_vocab]
    perf_shift = perf_shift[:, :, :min_vocab]
    obs_lprobs = torch.nn.functional.log_softmax(obs_shift, dim=-1)
    perf_probs = torch.nn.functional.softmax(perf_shift, dim=-1)
    cross_entropy = -(perf_probs * obs_lprobs).sum(dim=-1).mean().item()
    perf_lprobs = torch.nn.functional.log_softmax(perf_shift, dim=-1)
    ref_entropy = -(perf_probs * perf_lprobs).sum(dim=-1).mean().item()
    if ref_entropy == 0:
        return 1.0
    return cross_entropy / ref_entropy


def _normalize_binoculars(raw_ratio: float) -> float:
    """Sigmoid mapping: ratio near 1.0 -> score ~1.0 (machine)."""
    x = -(raw_ratio - 1.2) * 5.0
    return 1.0 / (1.0 + math.exp(-x))


def _label_from_score(score: float) -> str:
    if score >= BINOCULARS_MACHINE_THRESHOLD:
        return "machine"
    if score <= BINOCULARS_HUMAN_THRESHOLD:
        return "human"
    return "uncertain"


def _load_single_model(name: str, device: str):
    """Load one model to GPU, run inference, return. For sequential mode."""
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(
        name, torch_dtype=torch.float16,
        local_files_only=_try_local_first(name),
    ).to(device)
    model.requires_grad_(False)
    return model


def _run_binoculars(text: str) -> DetectionResult:
    start = time.time()
    models = _load_binoculars_models()
    tok, device = models["tokenizer"], models["device"]
    inputs = tok(text, return_tensors="pt", truncation=True,
                 max_length=512, padding=True).to(device)

    if models["sequential"]:
        # Sequential: one model in VRAM at a time. Unload any leftover
        # performer from a previous sample before loading the observer.
        prev = _binoculars_models.get("performer")
        if prev is not None:
            del prev
            _binoculars_models["performer"] = None
            _gltr_model.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        obs = _load_single_model(BINOCULARS_OBSERVER, device)
        with torch.no_grad():
            obs_logits = obs(**inputs).logits.cpu()
        del obs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        perf = _load_single_model(BINOCULARS_PERFORMER, device)
        with torch.no_grad():
            perf_logits = perf(**inputs).logits.cpu()
        # Keep performer for GLTR reuse on this sample; cleared on next
        _binoculars_models["performer"] = perf
        raw = _compute_binoculars_score(obs_logits, perf_logits)
        del obs_logits, perf_logits
    else:
        with torch.no_grad():
            obs_out = models["observer"](**inputs)
            perf_out = models["performer"](**inputs)
        raw = _compute_binoculars_score(obs_out.logits, perf_out.logits)
        del obs_out, perf_out

    del inputs
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    score = _normalize_binoculars(raw)
    return DetectionResult(
        source="binoculars", score=score, label=_label_from_score(score),
        metadata={
            "raw_ratio": round(raw, 4),
            "observer": BINOCULARS_OBSERVER,
            "performer": BINOCULARS_PERFORMER,
            "device": device,
            "elapsed_s": round(time.time() - start, 2),
        },
    )


# --- GLTR (per-token rank analysis) ---
#
# Reuses BINOCULARS_PERFORMER to avoid loading a third model.
#
# GLTR buckets each token by rank in the model's predicted distribution.
# AI-generated text clusters in the top-10 predictions (60-80%+); human
# prose spreads across top-100 and beyond (30-40% top-10).
#
# Code is fundamentally different: keywords, syntax, and imports are
# always top-10 predictable regardless of authorship. Our first run
# showed code samples at 77-94% top-10 vs prose at 64-87%. To avoid
# false positives, code uses a larger span window (8 vs 5 tokens) and
# higher cluster threshold (0.9 vs 0.7). This means only very long
# stretches of maximally predictable code get flagged.
#
# Score sigmoid centers at 50% top-10 for prose. Code scores are
# reported but not used for vocabulary candidate extraction (code
# tokens like "import", "self", "config" aren't AI-tell vocabulary).

GLTR_MODEL = BINOCULARS_PERFORMER

# Span detection parameters by content type
GLTR_SPAN_PARAMS = {
    # Prose: 5-token window, 70% top-10 threshold.
    # Catches clusters of 4+ predictable tokens in natural language,
    # which typically indicate formulaic or generated phrasing.
    "prose": {"window": 5, "threshold": 0.7},

    # Code: 8-token window, 90% top-10 threshold.
    # Code is inherently predictable (keywords, syntax). Only flag
    # spans where nearly every token in a large window is maximally
    # predictable, which can indicate boilerplate or generated patterns.
    "code": {"window": 8, "threshold": 0.9},
}

_gltr_model: dict = {}


def _load_gltr_model():
    if _gltr_model:
        return _gltr_model
    # Reuse performer model if already loaded
    if "performer" in _binoculars_models:
        _gltr_model["model"] = _binoculars_models["performer"]
        _gltr_model["tokenizer"] = _binoculars_models["tokenizer"]
        _gltr_model["device"] = _binoculars_models["device"]
        return _gltr_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    local = _try_local_first(GLTR_MODEL)
    tok = AutoTokenizer.from_pretrained(GLTR_MODEL, local_files_only=local)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        GLTR_MODEL, torch_dtype=torch.float16,
        local_files_only=local,
    ).to(device)
    model.requires_grad_(False)
    _gltr_model["model"] = model
    _gltr_model["tokenizer"] = tok
    _gltr_model["device"] = device
    return _gltr_model


def _bucket_ranks(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"top10": 0, "top100": 0, "top1000": 0, "beyond": 0}
    n = len(ranks)
    top10 = sum(1 for r in ranks if r <= 10) / n * 100
    top100 = sum(1 for r in ranks if 10 < r <= 100) / n * 100
    top1000 = sum(1 for r in ranks if 100 < r <= 1000) / n * 100
    beyond = sum(1 for r in ranks if r > 1000) / n * 100
    return {"top10": round(top10, 1), "top100": round(top100, 1),
            "top1000": round(top1000, 1), "beyond": round(beyond, 1)}


def _gltr_score_from_buckets(buckets: dict[str, float]) -> float:
    """Sigmoid: 80% top-10 -> ~0.9 (machine), 20% -> ~0.1 (human)."""
    x = (buckets["top10"] - 50.0) / 15.0
    return 1.0 / (1.0 + math.exp(-x))


def _find_suspicious_spans(
    token_scores: list[TokenScore], text: str,
    window: int = 5, threshold: float = 0.7
) -> list[SpanFlag]:
    """Find clusters of consecutive top-10 tokens."""
    spans = []
    n = len(token_scores)
    i = 0
    pos = 0
    while i <= n - window:
        window_tokens = token_scores[i:i + window]
        top10_frac = sum(1 for t in window_tokens if t.rank <= 10) / len(window_tokens)
        if top10_frac >= threshold:
            end = i + window
            while end < n and token_scores[end].rank <= 10:
                end += 1
            span_tokens = token_scores[i:end]
            span_text = " ".join(t.token for t in span_tokens)
            start_pos = text.find(span_tokens[0].token, pos)
            if start_pos == -1:
                start_pos = pos
            end_pos = start_pos + len(span_text)
            spans.append(SpanFlag(
                start=start_pos, end=end_pos, text=span_text,
                reason="top10_cluster", severity=top10_frac,
            ))
            i = end
        else:
            i += 1
    return spans


def _run_gltr(text: str, content_type: str = "prose") -> DetectionResult:
    start = time.time()
    models = _load_gltr_model()
    tok, device = models["tokenizer"], models["device"]
    model = models["model"]
    inputs = tok(text, return_tensors="pt", truncation=True,
                 max_length=512).to(device)
    input_ids = inputs["input_ids"][0]
    with torch.no_grad():
        logits = model(**inputs).logits[0]
    token_scores = []
    for i in range(1, len(input_ids)):
        probs = torch.softmax(logits[i - 1], dim=-1)
        token_id = input_ids[i].item()
        token_prob = probs[token_id].item()
        rank = (probs > token_prob).sum().item() + 1
        token_str = tok.decode([token_id])
        token_scores.append(TokenScore(token=token_str, rank=int(rank), prob=token_prob))
    del logits, inputs, input_ids
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    ranks = [ts.rank for ts in token_scores]
    buckets = _bucket_ranks(ranks)
    score = _gltr_score_from_buckets(buckets)
    params = GLTR_SPAN_PARAMS.get(content_type, GLTR_SPAN_PARAMS["prose"])
    flagged = _find_suspicious_spans(
        token_scores, text, window=params["window"], threshold=params["threshold"]
    )
    return DetectionResult(
        source="gltr", score=score, label=_label_from_score(score),
        token_scores=token_scores, flagged_spans=flagged,
        metadata={
            "buckets": buckets, "model": GLTR_MODEL, "device": device,
            "total_tokens": len(token_scores),
            "elapsed_s": round(time.time() - start, 2),
        },
    )


def unload_models():
    """Free GPU memory by unloading all detection models."""
    _binoculars_models.clear()
    _gltr_model.clear()
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.empty_cache()
