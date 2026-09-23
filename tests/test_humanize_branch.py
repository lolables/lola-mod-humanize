"""Tests for humanize-branch.sh git safety checks."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conftest import hermetic_git_env

SCRIPT = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts' / 'humanize-branch.sh'

_GIT_ENV = hermetic_git_env()


def run_branch_cmd(cmd: str, cwd: str) -> tuple[str, str, int]:
    """Run humanize-branch.sh with a subcommand, return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ['bash', str(SCRIPT), cmd],
        capture_output=True, text=True, cwd=cwd, timeout=10, env=_GIT_ENV,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def init_repo(path) -> str:
    """Init a repo with one commit. Returns the current branch name."""
    subprocess.run(['git', 'init'], cwd=path, capture_output=True, env=_GIT_ENV)
    subprocess.run(['git', 'commit', '--allow-empty', '-m', 'init'],
                   cwd=path, capture_output=True, env=_GIT_ENV)
    head = subprocess.run(['git', 'branch', '--show-current'],
                          cwd=path, capture_output=True, text=True, env=_GIT_ENV)
    return head.stdout.strip()


class TestCheckCommand:
    def test_clean_repo_returns_clean(self, tmp_path):
        init_repo(tmp_path)
        stdout, _, rc = run_branch_cmd('check', str(tmp_path))
        assert rc == 0
        assert 'CLEAN' in stdout

    def test_dirty_repo_returns_dirty(self, tmp_path):
        init_repo(tmp_path)
        (tmp_path / 'dirty.txt').write_text('uncommitted')
        subprocess.run(['git', 'add', 'dirty.txt'], cwd=tmp_path, capture_output=True, env=_GIT_ENV)
        stdout, _, rc = run_branch_cmd('check', str(tmp_path))
        assert rc == 1
        assert 'DIRTY' in stdout

    def test_not_git_returns_not_git(self, tmp_path):
        stdout, _, rc = run_branch_cmd('check', str(tmp_path))
        assert rc == 2
        assert 'NOT_GIT' in stdout

    def test_untracked_files_returns_clean_with_untracked(self, tmp_path):
        init_repo(tmp_path)
        (tmp_path / 'untracked.txt').write_text('new file')
        stdout, _, rc = run_branch_cmd('check', str(tmp_path))
        assert rc == 0
        assert 'CLEAN_WITH_UNTRACKED' in stdout


class TestNeverMovesHead:
    """The script inspects worktree state. It must never relocate the user.

    Humanize edits files in place on a clean worktree, where `git diff` is
    already exactly the transformation and `git checkout -- .` reverts it.
    Creating a branch bought no isolation `git checkout -b` carries
    uncommitted changes forward, so it only ever ran on an already-clean
    tree and moved HEAD for nothing.
    """

    def test_branch_subcommand_is_gone(self, tmp_path):
        original = init_repo(tmp_path)
        _, stderr, rc = run_branch_cmd('branch', str(tmp_path))
        assert rc == 1
        assert 'Usage' in stderr

        head = subprocess.run(['git', 'branch', '--show-current'],
                              cwd=tmp_path, capture_output=True, text=True, env=_GIT_ENV)
        assert head.stdout.strip() == original

    def test_check_leaves_head_alone(self, tmp_path):
        original = init_repo(tmp_path)
        run_branch_cmd('check', str(tmp_path))

        head = subprocess.run(['git', 'branch', '--show-current'],
                              cwd=tmp_path, capture_output=True, text=True, env=_GIT_ENV)
        assert head.stdout.strip() == original

    def test_no_humanize_branch_is_ever_created(self, tmp_path):
        init_repo(tmp_path)
        for cmd in ('check', 'branch'):
            run_branch_cmd(cmd, str(tmp_path))

        branches = subprocess.run(['git', 'branch', '--list', 'humanize/*'],
                                  cwd=tmp_path, capture_output=True, text=True, env=_GIT_ENV)
        assert branches.stdout.strip() == ''
