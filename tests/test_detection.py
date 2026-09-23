"""test_detection.py -- CI gate: Binoculars scores on .after.* samples.

Skips when torch/transformers are not installed. It does NOT skip on a
CPU-only machine: `gpu_available()` reports whether torch imported, not
whether a GPU is present, and CPU inference is supported.

Budget the time before assuming it has hung. The first run pulls several
GB of weights, and the default observer/performer pair puts gpt2-xl (6GB)
through CPU inference for every sample, which runs far longer than the
30-60 seconds per sample the README quotes for smaller models. `task
check` includes this suite, so on a GPU-less machine prefer the other
targets while iterating.

Run via: task test:detect
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from detect import gpu_available

pytestmark = pytest.mark.skipif(
    not gpu_available(),
    reason="AI detection requires torch + transformers (install via: uv pip install -e '.[ai-detect]')"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO_ROOT / 'tests'
BASELINES_PATH = REPO_ROOT / 'tests' / 'detection-baselines.yml'
REGRESSION_TOLERANCE = 0.05

THRESHOLDS = {
    "prose": 0.60,
    "short": 0.65,
    "code": 0.70,
}

SAMPLE_TIERS = {
    "01-blog-post": "prose",
    "02-readme": "prose",
    "03-commit-message": "short",
    "04-pr-description": "short",
    "05-subtle-ai": "prose",
    "06-promotional": "prose",
    "07-mixed-content": "prose",
}


def _infer_tier(name: str) -> str:
    if name in SAMPLE_TIERS:
        return SAMPLE_TIERS[name]
    lower = name.lower()
    for keyword in ("blog", "readme", "subtle", "promotional", "mixed"):
        if keyword in lower:
            return "prose"
    for keyword in ("commit", "pr-"):
        if keyword in lower:
            return "short"
    return "code"


def _load_baselines() -> dict:
    if not BASELINES_PATH.exists():
        return {}
    return json.loads(BASELINES_PATH.read_text())


def _save_baselines(baselines: dict) -> None:
    BASELINES_PATH.write_text(json.dumps(baselines, indent=2))


def _collect_after_samples() -> list[tuple[str, Path]]:
    samples = []
    for subdir in ("text-samples", "code-samples"):
        d = SAMPLES_DIR / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.after.*")):
            name = f.name.split(".after.")[0]
            samples.append((name, f))
    return samples


_after_samples = _collect_after_samples()


@pytest.fixture(scope="module")
def baselines():
    return _load_baselines()


@pytest.mark.parametrize("name,path", _after_samples, ids=[n for n, _ in _after_samples])
def test_sample_below_threshold(name, path, baselines):
    from detect import detect
    text = path.read_text()
    results = detect(text, tools=["binoculars"])
    score = results[0].score
    tier = _infer_tier(name)
    threshold = THRESHOLDS[tier]
    assert score <= threshold, (
        f"{name}: Binoculars score {score:.3f} exceeds {tier} threshold {threshold}. "
        f"Flagged spans: {[s.text[:40] for s in results[0].flagged_spans]}"
    )
    if name in baselines:
        baseline = baselines[name]
        assert score <= baseline + REGRESSION_TOLERANCE, (
            f"{name}: Binoculars score {score:.3f} regressed from baseline {baseline:.3f} "
            f"(tolerance: {REGRESSION_TOLERANCE})"
        )


def test_update_baselines():
    """After all tests pass, update baseline scores."""
    from detect import detect, unload_models
    baselines = _load_baselines()
    updated = False
    for name, path in _after_samples:
        if name not in baselines:
            text = path.read_text()
            results = detect(text, tools=["binoculars"])
            baselines[name] = round(results[0].score, 4)
            updated = True
    if updated:
        _save_baselines(baselines)
    unload_models()
