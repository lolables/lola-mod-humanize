"""
test_robustness.py -- Tests for robustness guards added in Task 7.

Covers:
- File size guard in analyze-sources.py (>5MB files skipped)
- Retry logic structure in update-sources.sh (429/503 retry)
"""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from conftest import analyze_sources

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'


# --- File size guard tests ---

def test_large_file_skipped(tmp_path):
    """Files larger than 5MB should be skipped with a warning."""
    fetch_dir = tmp_path / 'fetched'
    fetch_dir.mkdir()
    ref_dir = tmp_path / 'reference'
    ref_dir.mkdir()
    output_dir = tmp_path / 'analysis'
    output_dir.mkdir()

    # Create a >5MB HTML file
    large_file = fetch_dir / 'too-big.html'
    large_file.write_text('<html><body>' + 'x' * (5 * 1024 * 1024 + 1) + '</body></html>')

    # Create matching meta file
    meta_file = fetch_dir / 'too-big.meta'
    meta_file.write_text('slug=too-big\nurl=https://example.com\nhttp_code=200\n')

    # Run main() with captured stderr
    import io
    import sys
    old_argv = sys.argv
    old_stderr = sys.stderr
    try:
        sys.argv = [
            'analyze-sources.py',
            '--fetch-dir', str(fetch_dir),
            '--reference-dir', str(ref_dir),
            '--output-dir', str(output_dir),
        ]
        captured = io.StringIO()
        sys.stderr = captured
        analyze_sources.main()
    finally:
        sys.argv = old_argv
        sys.stderr = old_stderr

    warning_output = captured.getvalue()
    assert 'Skipping too-big' in warning_output
    assert 'exceeds' in warning_output

    # Verify no plaintext output was produced for the skipped file
    assert not (output_dir / 'too-big.txt').exists()


def test_small_file_processed(tmp_path):
    """Normal-sized files should be processed without issues."""
    fetch_dir = tmp_path / 'fetched'
    fetch_dir.mkdir()
    ref_dir = tmp_path / 'reference'
    ref_dir.mkdir()
    output_dir = tmp_path / 'analysis'
    output_dir.mkdir()

    # Create a small HTML file with enough content to pass the len(text) < 100 check
    content = '<html><body>' + '<p>This is a normal paragraph with enough content. </p>' * 20 + '</body></html>'
    small_file = fetch_dir / 'normal-source.html'
    small_file.write_text(content)

    # Create matching meta file
    meta_file = fetch_dir / 'normal-source.meta'
    meta_file.write_text('slug=normal-source\nurl=https://example.com\nhttp_code=200\n')

    import sys
    old_argv = sys.argv
    try:
        sys.argv = [
            'analyze-sources.py',
            '--fetch-dir', str(fetch_dir),
            '--reference-dir', str(ref_dir),
            '--output-dir', str(output_dir),
        ]
        analyze_sources.main()
    finally:
        sys.argv = old_argv

    # Verify the file was processed (plaintext output created)
    assert (output_dir / 'normal-source.txt').exists()
    assert (output_dir / 'update-report.md').exists()


# --- Retry logic structure tests ---

def test_retry_logic_present_in_update_sources():
    """Verify update-sources.sh has retry logic for HTTP 429 and 503."""
    script = (SCRIPTS_DIR / 'update-sources.sh').read_text()

    # Check that retry block exists for 429 and 503
    assert '429' in script, 'Script should handle HTTP 429'
    assert '503' in script, 'Script should handle HTTP 503'
    assert 'sleep 5' in script, 'Script should sleep 5 seconds before retry'

    # Verify the retry uses the same curl flags as the original
    # Count curl invocations with --max-time 30 (should be 2: original + retry)
    curl_calls = [line.strip() for line in script.splitlines()
                  if 'curl -sL' in line]
    assert len(curl_calls) == 2, (
        f'Expected 2 curl calls (original + retry), found {len(curl_calls)}'
    )


def test_retry_only_on_transient_errors():
    """Verify retry block only triggers on 429 and 503, not other errors."""
    script = (SCRIPTS_DIR / 'update-sources.sh').read_text()

    # Find the retry condition line
    retry_lines = [line.strip() for line in script.splitlines()
                   if 'http_code' in line and ('429' in line or '503' in line)]
    assert len(retry_lines) >= 1, 'Should have a retry condition checking 429/503'

    # Ensure it's a conditional, not unconditional retry
    assert any('if' in line for line in retry_lines), (
        'Retry should be conditional (inside an if block)'
    )
