"""Regression tests for scripts/update-sources.sh."""
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "update-sources.sh"


def test_fetch_only_runs_without_personal_sources(tmp_path):
    """update-sources.sh --fetch-only must not crash when no
    personal-sources.yml exists (the default state). Regression for the
    `LOCAL_SOURCES: unbound variable` bug under set -u with an empty
    associative array.

    No network-skip marker is needed: the assertions are network-independent.
    The script catches curl failures with `|| http_code="000"`, always writes
    a .meta file, and never exits non-zero on fetch failures, so the
    "unbound variable" and returncode-0 assertions hold whether or not the
    test runner has network access.
    """
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    assert not (REPO / "personal-sources.yml").exists()

    proc = subprocess.run(
        ["bash", str(SCRIPT), "--fetch-only"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=180,
    )
    assert "unbound variable" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, f"rc={proc.returncode}\n{proc.stderr}"
    fetched = REPO / ".test-output" / "update-report" / "fetched"
    assert fetched.is_dir()
    assert list(fetched.glob("*.meta")), "no source metadata written"
