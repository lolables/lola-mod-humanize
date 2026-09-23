"""
test_consistency.py -- Cross-file consistency checks.

Verifies that reference data stays in sync across the project:
- Generated regions (vocabulary.py, AGENTS.md, etc.) match the watchlist
- All URLs hardcoded in update-sources.sh appear in docs/SOURCES.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_script_urls(script_path: Path) -> list[str]:
    """Extract URLs from SOURCES[slug]="https://..." lines."""
    text = script_path.read_text()
    urls = re.findall(r'SOURCES\[\S+\]="(https?://[^"]+)"', text)
    return urls


def _read_sources_doc(sources_path: Path) -> str:
    return sources_path.read_text()


class TestGeneratedRegionsAreCurrent:
    """`sync_vocabulary --check` must be clean on a committed tree."""

    def test_check_reports_no_stale_files(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'scripts' / 'sync_vocabulary.py'), '--check'],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f'Generated regions are stale. Run "task vocab:sync".\n'
            f'{result.stdout}\n{result.stderr}'
        )


class TestScriptUrlsInSourcesDoc:
    """Every URL in update-sources.sh must appear in docs/SOURCES.md."""

    SCRIPT = PROJECT_ROOT / 'scripts' / 'update-sources.sh'
    SOURCES_DOC = PROJECT_ROOT / 'docs' / 'SOURCES.md'

    def test_script_urls_in_sources_doc(self):
        urls = _parse_script_urls(self.SCRIPT)
        assert urls, "No URLs found in update-sources.sh (parser broken?)"

        doc_text = _read_sources_doc(self.SOURCES_DOC)

        missing = [u for u in urls if u not in doc_text]
        assert not missing, (
            f"URLs in update-sources.sh but missing from docs/SOURCES.md:\n"
            + "\n".join(f"  {u}" for u in missing)
        )
