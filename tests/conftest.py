"""
conftest.py -- pytest configuration for Humanize tests.

Adds both script directories to sys.path and provides importlib helpers
for modules with hyphens in their filenames (analyze-sources.py, etc.).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / 'scripts'
SKILL_SCRIPTS_DIR = REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts'


HERMETIC_GIT_CONFIG = Path(__file__).resolve().parent / 'fixtures' / 'git' / 'hermetic.gitconfig'


def hermetic_git_env() -> dict[str, str]:
    """Env dict that isolates git from the developer's host configuration.

    Tests that spawn `git` (or scripts that spawn `git`) must use this so
    they do not inherit `commit.gpgsign`, `core.hooksPath`,
    `init.templateDir`-installed hooks, custom credential helpers, or
    other settings from the developer's `~/.gitconfig` and the host's
    `/etc/gitconfig`. Without this, a host configured to sign commits or
    run a pre-commit hook will hang the test on a captured stdin
    waiting for input that never arrives.

    GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM (git >= 2.32) point at a
    committed fixture file (tests/fixtures/git/hermetic.gitconfig) that
    explicitly neutralizes signing, the pager, and unhelpful advice
    messages. Pointing at a real file rather than /dev/null makes the
    test environment self-documenting: `cat` the fixture to see exactly
    what config is in effect.

    Sets a fixed identity so `git commit` does not require a separate
    `git config user.*` step in each test. Refuses any terminal prompt
    instead of silently blocking.
    """
    env = {
        **os.environ,
        'GIT_CONFIG_GLOBAL': str(HERMETIC_GIT_CONFIG),
        'GIT_CONFIG_SYSTEM': str(HERMETIC_GIT_CONFIG),
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@test.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@test.com',
    }
    # GIT_CONFIG_* only replaces the gitconfig files. A handful of GIT_*
    # env vars bypass config entirely and would still leak from the host:
    # GIT_TEMPLATE_DIR would copy the developer's template hooks into a
    # freshly-init'd test repo (reintroducing the captured-stdin hang via
    # a pre-commit hook); GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE/
    # GIT_OBJECT_DIRECTORY could redirect a test's git operations onto
    # the developer's real repository storage. Strip them.
    for var in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE',
                'GIT_OBJECT_DIRECTORY', 'GIT_NAMESPACE', 'GIT_TEMPLATE_DIR'):
        env.pop(var, None)
    return env

for d in (SCRIPTS_DIR, SKILL_SCRIPTS_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))


def _import_hyphenated(file_stem: str) -> object:
    """Import a Python module whose filename contains hyphens."""
    module_name = file_stem.replace('-', '_')
    # Check skill scripts first, then repo scripts
    for d in (SKILL_SCRIPTS_DIR, SCRIPTS_DIR):
        path = d / f'{file_stem}.py'
        if path.exists():
            spec = importlib.util.spec_from_file_location(module_name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError(f"can't find {file_stem}.py in either scripts dir")


# Import once and cache so test files can do:
#   from conftest import analyze_sources, ollama_eval, extract_text
analyze_sources = _import_hyphenated('analyze-sources')
ollama_eval = _import_hyphenated('ollama-eval')
extract_text = _import_hyphenated('extract-text')
update_watchlist = _import_hyphenated('update-watchlist')
pre_scan = _import_hyphenated('pre-scan')
