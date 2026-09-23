"""Tests for check-deps.sh, the dependency preflight."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / 'scripts' / 'check-deps.sh'

# /usr/bin and /bin supply python3, git, curl and the coreutils the script uses.
# uv (~/.local/bin) and lola (/usr/local/bin) sit outside them on purpose, so a
# test sees those two only when it stubs them.
BASE_PATH = '/usr/bin:/bin'


def stub(bin_dir: Path, name: str, body: str) -> None:
    """Drop an executable stub onto the synthetic PATH."""
    script = bin_dir / name
    script.write_text(f'#!/usr/bin/env bash\n{body}\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def run_check(bin_dir: Path, root: Path = REPO_ROOT, mode: str = 'human') -> tuple[str, int]:
    """Run check-deps.sh against a synthetic PATH, return (output, returncode)."""
    result = subprocess.run(
        ['bash', str(SCRIPT), '--mode', mode, str(root)],
        capture_output=True, text=True, timeout=60,
        env={'PATH': f'{bin_dir}:{BASE_PATH}', 'HOME': os.environ['HOME']},
    )
    return result.stdout + result.stderr, result.returncode


def healthy_bin(tmp_path: Path) -> Path:
    """A PATH where every tool the script wants is present and current."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    stub(bin_dir, 'uv', 'echo "uv 0.9.0"')
    stub(bin_dir, 'lola', 'echo "lola 0.5.0"')
    return bin_dir


class TestLolaVersionGate:
    """The precondition that used to live in the Taskfile install target."""

    def test_outdated_lola_fails(self, tmp_path):
        bin_dir = healthy_bin(tmp_path)
        stub(bin_dir, 'lola', 'echo "lola 0.4.4"')
        out, rc = run_check(bin_dir)
        assert rc == 1, out
        assert '0.4.5' in out, 'must name the version it needs'

    def test_current_lola_passes(self, tmp_path):
        out, rc = run_check(healthy_bin(tmp_path))
        assert rc == 0, out
        assert '0.4.5' not in out, 'no version complaint when lola is current'

    def test_equal_to_floor_passes(self, tmp_path):
        bin_dir = healthy_bin(tmp_path)
        stub(bin_dir, 'lola', 'echo "lola 0.4.5"')
        out, rc = run_check(bin_dir)
        assert rc == 0, out

    def test_double_digit_patch_is_not_string_compared(self, tmp_path):
        """0.4.10 is newer than 0.4.5, which a plain string compare gets wrong."""
        bin_dir = healthy_bin(tmp_path)
        stub(bin_dir, 'lola', 'echo "lola 0.4.10"')
        out, rc = run_check(bin_dir)
        assert rc == 0, out

    def test_missing_lola_is_advisory(self, tmp_path):
        """lola installs the module; you do not need it to develop."""
        bin_dir = tmp_path / 'bin'
        bin_dir.mkdir()
        stub(bin_dir, 'uv', 'echo "uv 0.9.0"')
        out, rc = run_check(bin_dir)
        assert rc == 0, out
        assert 'lola' in out, 'still worth mentioning'


class TestRequiredTooling:
    def test_missing_uv_fails(self, tmp_path):
        bin_dir = tmp_path / 'bin'
        bin_dir.mkdir()
        stub(bin_dir, 'lola', 'echo "lola 0.5.0"')
        out, rc = run_check(bin_dir)
        assert rc == 1, out
        assert 'uv' in out

    def test_missing_venv_fails_with_the_fix(self, tmp_path):
        root = tmp_path / 'empty-project'
        root.mkdir()
        out, rc = run_check(healthy_bin(tmp_path), root=root)
        assert rc == 1, out
        assert 'task setup' in out, 'must say how to fix it'

    def test_reports_every_missing_dependency_not_just_the_first(self, tmp_path):
        """A preflight that stops at the first failure wastes a round trip."""
        root = tmp_path / 'empty-project'
        root.mkdir()
        bin_dir = tmp_path / 'bin'
        bin_dir.mkdir()
        out, rc = run_check(bin_dir, root=root)
        assert rc == 1, out
        assert 'uv' in out and 'task setup' in out


class TestOutputModes:
    def test_human_mode_shows_passing_checks(self, tmp_path):
        out, rc = run_check(healthy_bin(tmp_path))
        assert rc == 0, out
        assert 'PASS' in out

    def test_llm_mode_stays_quiet_when_healthy(self, tmp_path):
        out, rc = run_check(healthy_bin(tmp_path), mode='llm')
        assert rc == 0, out
        assert 'PASS' not in out, 'llm mode reports problems, not successes'

    def test_llm_mode_still_reports_failures(self, tmp_path):
        bin_dir = healthy_bin(tmp_path)
        stub(bin_dir, 'lola', 'echo "lola 0.4.4"')
        out, rc = run_check(bin_dir, mode='llm')
        assert rc == 1, out
        assert '0.4.5' in out


class TestTaskfileWiring:
    def test_doctor_target_exists(self):
        content = (REPO_ROOT / 'Taskfile.yml').read_text()
        assert 'doctor:' in content, 'Taskfile must expose the check as `task doctor`'
        assert 'check-deps.sh' in content, 'doctor must call the script'
