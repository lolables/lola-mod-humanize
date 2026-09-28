"""Tests for manage-voices.py voice profile management."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import importlib.util

import pytest

from conftest import hermetic_git_env

# Import module with hyphenated filename
_spec = importlib.util.spec_from_file_location(
    "manage_voices",
    Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'humanize' / 'scripts' / 'manage-voices.py',
)
mv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mv)


# -- Fixtures --

MINIMAL_BUILTIN = """\
# Voice Profile: Blog

Professional technical blog writing.

---

## Register
Informed-casual.

## Sentence Structure
Varied.

## Voice and Person
First person, active voice.

## Directness
State opinions directly.

## Formatting
Prose over lists.

## Vocabulary
Technical jargon OK.

## What This Voice Is NOT
Not corporate marketing.

## Source
Example blog posts.

## Metrics
```
words_analyzed: 1000
```
"""

MINIMAL_OVERRIDE = """\
# Voice Profile Override: Blog

Personal blog voice derived from example.com.

---

## Register
Pragmatic-technical.

## Sentence Structure
Short and punchy.

## Voice and Person
First person, active voice.

## Directness
Blunt.

## Courtesy
Low warmth. Soften directives, never grovel. No "Great question!", no
"I'd be happy to". See reference/courtesy.md.

## Formatting
Prose.

## Vocabulary
Heavy jargon.

## What This Voice Is NOT
Not a textbook.

## Source
Derived from example.com blog posts, 2020-2023.

## Metrics
```
words_analyzed: 5000
```
"""

INCOMPLETE_PROFILE = """\
# Voice Profile Override: Blog

Missing several sections.

---

## Register
Informed-casual.

## Sentence Structure
Varied.
"""

EMPTY_SECTION_PROFILE = """\
# Voice Profile Override: Blog

Has an empty section.

---

## Register
Informed-casual.

## Sentence Structure

## Voice and Person
First person.

## Directness
Direct.

## Courtesy
Low warmth. Soften directives, never grovel. No "Great question!", no
"I'd be happy to". See reference/courtesy.md.

## Formatting
Prose.

## Vocabulary
Jargon.

## What This Voice Is NOT
Not bland.

## Source
example.com

## Metrics
```
words: 100
```
"""


@pytest.fixture(autouse=True)
def _isolate_user_state(tmp_path, monkeypatch):
    """Keep every test away from real overrides, including ones that skip patched_dirs.

    `rm` resolves XDG and project-root overrides. A test run from this repo's
    checkout once deleted a real, gitignored reference/voices/blog.local.md.

    BUILTIN_DIR points at a copy of the shipped profiles, minus any
    *.local.md, so the skill-local step never sees a real override. The git
    location variables are cleared because the script deliberately honors
    them, and a value inherited from the caller would redirect every lookup.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "isolated-xdg"))
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
        monkeypatch.delenv(var, raising=False)
    builtin_copy = tmp_path / "isolated-builtin"
    builtin_copy.mkdir()
    for src in mv.BUILTIN_DIR.glob("*.md"):
        if not src.name.endswith(".local.md"):
            shutil.copy2(src, builtin_copy / src.name)
    monkeypatch.setattr(mv, "BUILTIN_DIR", builtin_copy)
    isolated_cwd = tmp_path / "isolated-cwd"
    isolated_cwd.mkdir()
    monkeypatch.chdir(isolated_cwd)


@pytest.fixture
def voice_dirs(tmp_path):
    """Set up mock XDG and builtin directories with test profiles."""
    xdg_dir = tmp_path / "xdg" / "humanize" / "voices"
    xdg_dir.mkdir(parents=True)
    builtin_dir = tmp_path / "skill" / "reference" / "voices"
    builtin_dir.mkdir(parents=True)
    # Write a built-in profile
    (builtin_dir / "blog.md").write_text(MINIMAL_BUILTIN)
    (builtin_dir / "tutorial.md").write_text(
        MINIMAL_BUILTIN.replace("Blog", "Tutorial").replace("blog", "tutorial")
    )
    return xdg_dir, builtin_dir


@pytest.fixture
def patched_dirs(voice_dirs, tmp_path, monkeypatch):
    """Patch module globals so manage-voices resolves against tmp dirs.

    Also chdir's to a plain (non-git) directory. Without this, the
    project-root lookup in resolve_profile() would walk up from pytest's
    real cwd (this repo checkout) and pick up its actual
    reference/voices/*.local.md overrides, leaking real state into tests
    that never asked for a project repo.
    """
    xdg_dir, builtin_dir = voice_dirs
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    with mock.patch.object(mv, "BUILTIN_DIR", builtin_dir), \
         mock.patch.object(mv, "xdg_voices_dir", return_value=xdg_dir):
        yield xdg_dir, builtin_dir


@pytest.fixture
def project_repo(tmp_path, monkeypatch):
    """A git repo with reference/voices/, standing in for a project root.

    Chdir's into a subdirectory of the repo (not the root itself) so the
    test also proves `git rev-parse --show-toplevel` walks up from a
    nested cwd, matching how the tool is actually invoked (from wherever
    the file being humanized lives). Returns the reference/voices/ dir.
    """
    repo = tmp_path / "project"
    voices_dir = repo / "reference" / "voices"
    voices_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo,
                    capture_output=True, env=hermetic_git_env(), timeout=15, check=True)
    workdir = repo / "src" / "nested"
    workdir.mkdir(parents=True)
    monkeypatch.chdir(workdir)
    return voices_dir


class TestIsolation:
    """The autouse fixture must hide every piece of real user state."""

    def test_builtin_dir_is_a_copy_without_overrides(self):
        real = Path(mv.__file__).resolve().parent.parent / "reference" / "voices"
        assert mv.BUILTIN_DIR.resolve() != real
        assert "blog" in mv.discover_profile_types()
        assert not list(mv.BUILTIN_DIR.glob("*.local.md"))

    @pytest.mark.parametrize("var", ["GIT_DIR", "GIT_WORK_TREE",
                                     "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"])
    def test_git_location_env_cleared(self, var):
        assert var not in os.environ


class TtyStringIO(StringIO):
    """Captured stream that claims to be a terminal."""

    def isatty(self):
        return True


def run(argv, stderr_tty=False):
    """Run main() capturing stdout/stderr, return (stdout, stderr, exit_code)."""
    out, err = StringIO(), (TtyStringIO() if stderr_tty else StringIO())
    with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
        try:
            rc = mv.main(argv)
        except SystemExit as e:
            rc = e.code if e.code is not None else 0
    return out.getvalue(), err.getvalue(), rc


# -- extract_source --

class TestExtractSource:
    def test_extracts_first_line(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("## Source\nDerived from example.com blog posts.\n\n## Metrics\n")
        assert mv.extract_source(p) == "Derived from example.com blog posts."

    def test_skips_separator(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("## Source\n\n---\n\nDerived from example.com.\n\n## Metrics\n")
        assert mv.extract_source(p) == "Derived from example.com."

    def test_empty_source(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("## Register\nCasual.\n")
        assert mv.extract_source(p) == ""

    def test_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        assert mv.extract_source(p) == ""

    def test_reads_basis_from_builtin(self, tmp_path):
        """Built-in profiles record provenance under `## Basis`, not `## Source`.

        All nine shipped profiles use `## Basis`, so reading only `## Source`
        means `ls` can never show provenance for a built-in.
        """
        p = tmp_path / "builtin.md"
        p.write_text("## Basis\nDerived from RFC 2119 and IETF style.\n")
        assert mv.extract_source(p) == "Derived from RFC 2119 and IETF style."

    def test_source_wins_over_basis(self, tmp_path):
        p = tmp_path / "both.md"
        p.write_text("## Source\nOverride provenance.\n\n## Basis\nBuilt-in provenance.\n")
        assert mv.extract_source(p) == "Override provenance."


# -- extract_sections --

class TestExtractSections:
    def test_parses_sections(self):
        sections = mv.extract_sections(MINIMAL_BUILTIN)
        assert "Register" in sections
        assert sections["Register"] == "Informed-casual."
        assert "Source" in sections

    def test_empty_input(self):
        assert mv.extract_sections("") == {}

    def test_no_sections(self):
        assert mv.extract_sections("Just some text\nwith no headings.") == {}


# -- resolve_profile --

class TestResolveProfile:
    def test_xdg_override_wins(self, patched_dirs):
        xdg_dir, builtin_dir = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog")
        assert kind == "override"
        assert path == xdg_dir / "blog.local.md"

    def test_skill_local_override(self, patched_dirs):
        xdg_dir, builtin_dir = patched_dirs
        (builtin_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog")
        assert kind == "override"
        assert path == builtin_dir / "blog.local.md"

    def test_builtin_fallback(self, patched_dirs):
        path, kind = mv.resolve_profile("blog")
        assert kind == "built-in"
        assert path.name == "blog.md"

    def test_xdg_over_skill_local(self, patched_dirs):
        xdg_dir, builtin_dir = patched_dirs
        (xdg_dir / "blog.local.md").write_text("xdg wins")
        (builtin_dir / "blog.local.md").write_text("skill local")
        path, kind = mv.resolve_profile("blog")
        assert path == xdg_dir / "blog.local.md"

    def test_builtin_only_skips_overrides(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog", builtin_only=True)
        assert kind == "built-in"
        assert path.name == "blog.md"

    def test_missing_type(self, patched_dirs):
        path, kind = mv.resolve_profile("code-comments")
        assert path is None
        assert kind == "missing"


# -- resolve_profile: project-root override --

class TestResolveProfileProject:
    def test_project_override_found(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog")
        assert kind == "override"
        assert path == project_repo / "blog.local.md"

    def test_xdg_wins_over_project(self, patched_dirs, project_repo):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        (project_repo / "blog.local.md").write_text("project version")
        path, kind = mv.resolve_profile("blog")
        assert path == xdg_dir / "blog.local.md"

    def test_project_wins_over_skill_local(self, patched_dirs, project_repo):
        _, builtin_dir = patched_dirs
        (builtin_dir / "blog.local.md").write_text("skill local version")
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog")
        assert path == project_repo / "blog.local.md"

    def test_non_git_cwd_skips_project_step(self, patched_dirs, tmp_path, monkeypatch):
        non_git = tmp_path / "not-a-repo"
        non_git.mkdir()
        monkeypatch.chdir(non_git)
        _, builtin_dir = patched_dirs
        (builtin_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        path, kind = mv.resolve_profile("blog")
        assert kind == "override"
        assert path == builtin_dir / "blog.local.md"

    def test_git_missing_skips_project_step(self, patched_dirs, project_repo, monkeypatch):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        _, builtin_dir = patched_dirs
        (builtin_dir / "blog.local.md").write_text("skill local fallback")

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("git: command not found")

        monkeypatch.setattr(mv.subprocess, "run", fake_run)
        path, kind = mv.resolve_profile("blog")
        assert path == builtin_dir / "blog.local.md"


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, capture_output=True,
                   env=hermetic_git_env(), timeout=15, check=True)


class TestProjectOverrideTrust:
    """A repo's author must not be able to inject instructions via a voice file.

    Only an untracked, non-symlink reference/voices/<type>.local.md at the
    project root is honored. Anything else falls through to skill-local,
    then built-in.
    """

    def test_tracked_override_ignored(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        git(project_repo.parent.parent, "commit", "-q", "-m", "plant")
        path, kind = mv.resolve_profile("blog")
        assert kind == "built-in"
        assert mv.project_override("blog") == (override, "tracked by git")

    def test_staged_override_ignored(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        assert mv.resolve_profile("blog")[1] == "built-in"

    def test_tracked_falls_through_to_skill_local(self, patched_dirs, project_repo):
        _, builtin_dir = patched_dirs
        (builtin_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        assert mv.resolve_profile("blog") == (builtin_dir / "blog.local.md", "override")

    def test_untracked_override_honored(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        assert mv.resolve_profile("blog") == (override, "override")
        assert mv.project_override("blog") == (override, None)

    def test_gitignored_override_honored(self, patched_dirs, project_repo):
        repo = project_repo.parent.parent
        (repo / ".gitignore").write_text("*.local.md\n")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-q", "-m", "ignore overrides")
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        assert mv.resolve_profile("blog") == (override, "override")

    def test_symlinked_override_ignored(self, patched_dirs, project_repo, tmp_path):
        target = tmp_path / "valid-profile.md"
        target.write_text(MINIMAL_OVERRIDE)
        link = project_repo / "blog.local.md"
        link.symlink_to(target)
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog") == (link, "symlink")

    def test_symlinked_voices_dir_ignored(self, patched_dirs, project_repo, tmp_path):
        outside = tmp_path / "outside-voices"
        outside.mkdir()
        (outside / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        project_repo.rmdir()
        project_repo.symlink_to(outside)
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog")[1] == "symlink"

    def test_symlinked_reference_dir_inside_repo_ignored(self, patched_dirs, project_repo):
        """A symlink that stays inside the repo still bypasses the tracked check.

        git refuses to look beyond a symlink and reports the path as
        unmatched, which would otherwise read as "untracked".
        """
        repo = project_repo.parent.parent
        real = repo / "elsewhere" / "voices"
        real.mkdir(parents=True)
        (real / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        git(repo, "add", "elsewhere")
        project_repo.rmdir()
        (repo / "reference").rmdir()
        (repo / "reference").symlink_to("elsewhere")
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog")[1] == "symlink"

    @pytest.mark.parametrize("failure", ["exit", "oserror", "timeout"])
    def test_git_failure_in_tracked_check_rejects(self, patched_dirs, project_repo,
                                                   monkeypatch, failure):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        real_run = subprocess.run

        def flaky_run(cmd, *args, **kwargs):
            if "ls-files" not in cmd:
                return real_run(cmd, *args, **kwargs)
            if failure == "exit":
                return subprocess.CompletedProcess(cmd, 128, "", "fatal: broken")
            if failure == "oserror":
                raise OSError("git vanished")
            raise subprocess.TimeoutExpired(cmd, 5)

        monkeypatch.setattr(mv.subprocess, "run", flaky_run)
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog") == (override, "git check failed")

    def test_git_failure_in_nested_repo_check_rejects(self, patched_dirs, project_repo,
                                                       monkeypatch):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        real_run = subprocess.run

        def flaky_run(cmd, *args, **kwargs):
            if "rev-parse" in cmd and Path(kwargs.get("cwd") or ".") == project_repo:
                return subprocess.CompletedProcess(cmd, 128, "", "fatal: broken")
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(mv.subprocess, "run", flaky_run)
        assert mv.project_override("blog") == (override, "git check failed")

    def test_submodule_override_ignored(self, patched_dirs, project_repo, tmp_path):
        """The parent repo's ls-files can't see files a submodule tracks."""
        upstream = tmp_path / "attacker-voices"
        (upstream / "voices").mkdir(parents=True)
        (upstream / "voices" / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        git(upstream, "init", "-b", "main")
        git(upstream, "add", "voices/blog.local.md")
        git(upstream, "commit", "-q", "-m", "plant")
        repo = project_repo.parent.parent
        project_repo.rmdir()
        (repo / "reference").rmdir()
        git(repo, "-c", "protocol.file.allow=always", "submodule", "add",
            str(upstream), "reference")
        override = project_repo / "blog.local.md"
        assert override.is_file()
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog") == (override, "inside a nested repo or submodule")

    def test_nested_repo_override_ignored(self, patched_dirs, project_repo):
        git(project_repo.parent, "init", "-b", "main")
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        assert mv.resolve_profile("blog")[1] == "built-in"
        assert mv.project_override("blog") == (override, "inside a nested repo or submodule")

    def test_tracked_check_ignores_case(self, project_repo):
        """On macOS and Windows, Reference/voices/... opens as reference/voices/..."""
        repo = project_repo.parent.parent
        cased = repo / "Reference" / "voices"
        cased.mkdir(parents=True)
        (cased / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        git(repo, "add", "Reference/voices/blog.local.md")
        rel = Path("reference", "voices", "blog.local.md")
        assert mv.tracked_check(repo, rel) == "tracked by git"

    def test_tracked_check_untracked(self, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        rel = Path("reference", "voices", "blog.local.md")
        assert mv.tracked_check(project_repo.parent.parent, rel) is None

    def test_repo_fsmonitor_never_runs(self, patched_dirs, project_repo, tmp_path):
        """core.fsmonitor in a repo's config names a program git runs on index reads."""
        marker = tmp_path / "fsmonitor-ran"
        hook = tmp_path / "fsmonitor.sh"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
        hook.chmod(0o755)
        repo = project_repo.parent.parent
        git(repo, "config", "core.fsmonitor", str(hook))
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["ls"])
        assert rc == 0, err
        assert not marker.exists()

    def test_no_project_file(self, patched_dirs, project_repo):
        assert mv.project_override("blog") == (None, None)

    def test_check_reports_ignored_llm(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        out, err, rc = run(["--mode", "llm", "check", "blog"])
        assert f"blog|ignored|{override}|tracked by git" in out.splitlines()
        assert rc == 1

    def test_check_reports_ignored_human(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        out, err, rc = run(["check"])
        assert "ignored" in out
        assert "tracked by git" in out
        assert rc == 0

    def test_ls_reports_ignored(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        out, err, rc = run(["--mode", "llm", "ls"])
        assert rc == 0
        lines = out.splitlines()
        assert "blog|built-in||" in lines
        assert f"blog|ignored|{override}|tracked by git" in lines

    def test_path_reports_ignored_on_stderr(self, patched_dirs, project_repo):
        _, builtin_dir = patched_dirs
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        out, err, rc = run(["path", "blog"])
        assert rc == 0
        assert out.strip() == str(builtin_dir / "blog.md")
        assert "ignored" in err and "tracked by git" in err

    def test_rm_never_touches_ignored_file(self, patched_dirs, project_repo):
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        git(project_repo.parent.parent, "add", "reference/voices/blog.local.md")
        out, err, rc = run(["rm", "blog", "--yes"])
        assert rc == 1
        assert override.exists()


class TestForOption:
    """--for resolves the project root from the file being humanized, not the cwd."""

    @pytest.fixture
    def other_repo(self, tmp_path):
        repo = tmp_path / "other"
        voices = repo / "reference" / "voices"
        voices.mkdir(parents=True)
        git(repo, "init", "-b", "main")
        (voices / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        doc = repo / "docs" / "post.md"
        doc.parent.mkdir()
        doc.write_text("draft\n")
        return repo

    @pytest.mark.parametrize("target", ["docs/post.md", "docs", "."])
    def test_path_resolves_other_repo(self, patched_dirs, project_repo, other_repo, target):
        out, err, rc = run(["path", "blog", "--for", str(other_repo / target)])
        assert rc == 0, err
        assert out.strip() == str(other_repo / "reference" / "voices" / "blog.local.md")

    def test_without_for_uses_cwd_repo(self, patched_dirs, project_repo, other_repo):
        _, builtin_dir = patched_dirs
        out, err, rc = run(["path", "blog"])
        assert out.strip() == str(builtin_dir / "blog.md")

    @pytest.mark.parametrize("argv, expected", [
        (["ls"], "blog|override|"),
        (["cat", "blog"], "# Voice Profile Override: Blog"),
        (["check", "blog"], "blog|ok|"),
    ])
    def test_other_subcommands_accept_for(self, patched_dirs, project_repo, other_repo,
                                          argv, expected):
        out, err, rc = run([*argv, "--mode", "llm", "--for", str(other_repo / "docs")])
        assert rc == 0, err
        assert any(line.startswith(expected) for line in out.splitlines())

    def test_rm_honors_for(self, patched_dirs, project_repo, other_repo):
        override = other_repo / "reference" / "voices" / "blog.local.md"
        out, err, rc = run(["rm", "blog", "--yes", "--for", str(other_repo)])
        assert rc == 0, err
        assert not override.exists()

    @pytest.mark.parametrize("before", [True, False])
    def test_for_on_either_side_of_subcommand(self, patched_dirs, project_repo,
                                              other_repo, before):
        flag = ["--for", str(other_repo / "docs")]
        argv = [*flag, "path", "blog"] if before else ["path", "blog", *flag]
        out, err, rc = run(argv)
        assert rc == 0, err
        assert out.strip() == str(other_repo / "reference" / "voices" / "blog.local.md")

    @pytest.mark.parametrize("argv", [["--for", "", "path", "blog"],
                                      ["path", "blog", "--for", ""]])
    def test_empty_for_errors(self, patched_dirs, argv):
        out, err, rc = run(argv)
        assert rc == 1
        assert "--for" in err
        assert out == ""

    def test_missing_for_path_errors(self, patched_dirs, tmp_path):
        missing = tmp_path / "no-such-file.md"
        out, err, rc = run(["path", "blog", "--for", str(missing)])
        assert rc == 1
        assert str(missing) in err
        assert out == ""


# -- ls --

class TestLs:
    def test_lists_builtins(self, patched_dirs):
        out, err, rc = run(["ls"])
        assert rc == 0
        assert "blog" in out
        assert "built-in" in out

    def test_shows_override(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["ls"])
        assert rc == 0
        assert "override" in out

    def test_shows_source(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["ls"])
        assert "example.com" in out

    def test_shows_project_override(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["ls"])
        assert rc == 0
        assert "override" in out
        assert str(project_repo / "blog.local.md") in out

    def test_overrides_listed_first(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "tutorial.local.md").write_text(
            MINIMAL_OVERRIDE.replace("Blog", "Tutorial")
        )
        out, err, rc = run(["ls"])
        lines = [l for l in out.splitlines() if l.strip()]
        # tutorial override should appear before blog built-in
        override_idx = next(i for i, l in enumerate(lines) if "tutorial" in l)
        builtin_idx = next(i for i, l in enumerate(lines) if "blog" in l and "built-in" in l)
        assert override_idx < builtin_idx

    def test_llm_mode(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["--mode", "llm", "ls"])
        assert rc == 0
        assert "|" in out
        lines = out.strip().splitlines()
        blog_line = [l for l in lines if l.startswith("blog|")][0]
        parts = blog_line.split("|")
        assert parts[0] == "blog"
        assert parts[1] == "override"


# -- cat --

class TestCat:
    def test_prints_builtin(self, patched_dirs):
        out, err, rc = run(["cat", "blog"])
        assert rc == 0
        assert "Voice Profile: Blog" in out

    def test_prints_override_when_present(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["cat", "blog"])
        assert rc == 0
        assert "Voice Profile Override: Blog" in out

    def test_builtin_flag(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["cat", "--builtin", "blog"])
        assert rc == 0
        assert "Voice Profile: Blog" in out
        assert "Override" not in out

    def test_unknown_type(self, patched_dirs):
        out, err, rc = run(["cat", "nonexistent"])
        assert rc == 1
        assert "unknown" in err

    def test_missing_profile(self, patched_dirs):
        # With discovery, a type not present in BUILTIN_DIR is simply unknown.
        # The "no profile found" path is unreachable without a TOCTOU window;
        # the reachable error for an absent type is "unknown profile type".
        out, err, rc = run(["cat", "code-comments"])
        assert rc == 1
        assert "unknown" in err


# -- path --

class TestPath:
    def test_prints_builtin_path(self, patched_dirs):
        _, builtin_dir = patched_dirs
        out, err, rc = run(["path", "blog"])
        assert rc == 0
        assert str(builtin_dir / "blog.md") in out.strip()

    def test_prints_override_path(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["path", "blog"])
        assert rc == 0
        assert str(xdg_dir / "blog.local.md") in out.strip()

    def test_prints_project_override_path(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["path", "blog"])
        assert rc == 0
        assert str(project_repo / "blog.local.md") in out.strip()

    def test_unknown_type(self, patched_dirs):
        out, err, rc = run(["path", "invalid"])
        assert rc == 1


# -- rm --

class TestRm:
    def test_removes_override(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        override = xdg_dir / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        assert override.exists()
        out, err, rc = run(["rm", "blog", "--yes"])
        assert rc == 0
        assert not override.exists()
        assert "removed" in out

    def test_shows_builtin_after_rm(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["rm", "blog", "--yes"])
        assert "built-in" in out

    def test_reports_next_override_after_rm(self, patched_dirs, project_repo):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["rm", "blog", "--yes"])
        assert rc == 0
        assert not (xdg_dir / "blog.local.md").exists()
        assert (project_repo / "blog.local.md").exists()
        assert "(override)" in out
        assert "built-in" not in out

    def test_no_override_to_remove(self, patched_dirs):
        out, err, rc = run(["rm", "blog"])
        assert rc == 1
        assert "no user override" in err

    def test_unknown_type(self, patched_dirs):
        out, err, rc = run(["rm", "invalid"])
        assert rc == 1
        assert "unknown" in err

    def test_llm_mode(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["--mode", "llm", "rm", "blog", "--yes"])
        assert rc == 0
        assert out.startswith("removed|")

    def test_removes_skill_dir_override(self, patched_dirs):
        """rm must reach the skill-dir override, not just the XDG one.

        resolve_profile() honors both locations, so an override the tool
        reports as active must also be removable with the same tool.
        """
        _, builtin_dir = patched_dirs
        override = builtin_dir / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["rm", "blog", "-y"])
        assert rc == 0, err
        assert not override.exists()

    def test_removes_project_override(self, patched_dirs, project_repo):
        """rm must also reach the project-root override.

        resolve_profile() honors the project-root location too, so
        whatever it reports as active must be removable.
        """
        override = project_repo / "blog.local.md"
        override.write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["rm", "blog", "--yes"])
        assert rc == 0, err
        assert not override.exists()


class TestRmConfirmation:
    """rm deletes files that may be gitignored and unrecoverable, so it asks first."""

    @pytest.fixture
    def override(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        path = xdg_dir / "blog.local.md"
        path.write_text(MINIMAL_OVERRIDE)
        return path

    @staticmethod
    def _tty(answer):
        """Patch stdin as a terminal whose input() returns `answer` (or raises it)."""
        stdin = mock.patch.object(sys, "stdin", mock.Mock(isatty=lambda: True))
        side = answer if isinstance(answer, BaseException) else None
        reply = mock.patch("builtins.input", return_value=answer, side_effect=side)
        return stdin, reply

    def test_refuses_without_yes_when_not_a_terminal(self, override):
        with mock.patch.object(sys, "stdin", mock.Mock(isatty=lambda: False)):
            out, err, rc = run(["rm", "blog"])
        assert rc == 1
        assert override.exists()
        assert "--yes" in err
        assert str(override) in err

    def test_llm_mode_never_prompts(self, override):
        stdin, reply = self._tty("y")
        with stdin, reply as prompt:
            out, err, rc = run(["--mode", "llm", "rm", "blog"], stderr_tty=True)
        assert rc == 1
        assert override.exists()
        prompt.assert_not_called()

    @pytest.mark.parametrize("answer", ["y", "Y", "yes", " yes "])
    def test_terminal_confirmation_removes(self, override, answer):
        stdin, reply = self._tty(answer)
        with stdin, reply as prompt:
            out, err, rc = run(["rm", "blog"], stderr_tty=True)
        assert rc == 0
        assert not override.exists()
        assert prompt.call_args.args == ()
        assert f"remove {override}? [y/N] " in err
        assert "[y/N]" not in out

    @pytest.mark.parametrize("answer", ["", "n", "no", "nope"])
    def test_terminal_default_declines(self, override, answer):
        stdin, reply = self._tty(answer)
        with stdin, reply:
            out, err, rc = run(["rm", "blog"], stderr_tty=True)
        assert rc == 1
        assert override.exists()
        assert "not removed" in err

    def test_terminal_eof_declines(self, override):
        stdin, reply = self._tty(EOFError())
        with stdin, reply:
            out, err, rc = run(["rm", "blog"], stderr_tty=True)
        assert rc == 1
        assert override.exists()

    def test_yes_skips_prompt(self, override):
        stdin, reply = self._tty("n")
        with stdin, reply as prompt:
            out, err, rc = run(["rm", "blog", "--yes"], stderr_tty=True)
        assert rc == 0
        assert not override.exists()
        prompt.assert_not_called()

    def test_refuses_when_stderr_is_not_a_terminal(self, override):
        """The prompt is written to stderr; if nobody can see it, don't ask."""
        stdin, reply = self._tty("y")
        with stdin, reply as prompt:
            out, err, rc = run(["rm", "blog"])
        assert rc == 1
        assert override.exists()
        assert "--yes" in err
        prompt.assert_not_called()

    def test_ctrl_c_at_prompt_keeps_file(self, override):
        stdin, reply = self._tty(KeyboardInterrupt())
        with stdin, reply:
            out, err, rc = run(["rm", "blog"], stderr_tty=True)
        assert rc == 130
        assert override.exists()
        assert "not removed" in err

    def test_unlink_failure_reported(self, override, monkeypatch):
        def refuse(self, *args, **kwargs):
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(Path, "unlink", refuse)
        out, err, rc = run(["rm", "blog", "--yes"])
        assert rc == 1
        assert f"can't remove {override}:" in err
        assert "Permission denied" in err
        assert "removed" not in out


# -- check --

class TestCheck:
    def test_skips_builtin(self, patched_dirs):
        # check on a type with no override reports "no user override"
        out, err, rc = run(["check", "blog"])
        assert rc == 1
        assert "no user override" in out

    def test_valid_override(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["check", "blog"])
        assert rc == 0
        assert "ok" in out

    def test_valid_project_override(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["check", "blog"])
        assert rc == 0
        assert "ok" in out

    def test_invalid_project_override(self, patched_dirs, project_repo):
        (project_repo / "blog.local.md").write_text(INCOMPLETE_PROFILE)
        out, err, rc = run(["check", "blog"])
        assert rc == 2
        assert "missing section" in out

    def test_missing_sections(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(INCOMPLETE_PROFILE)
        out, err, rc = run(["check", "blog"])
        assert rc == 2
        assert "missing section" in out

    def test_empty_section(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(EMPTY_SECTION_PROFILE)
        out, err, rc = run(["check", "blog"])
        assert rc == 2
        assert "empty section: Sentence Structure" in out

    def test_bad_title(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        bad = MINIMAL_OVERRIDE.replace("# Voice Profile Override: Blog", "# Blog Profile")
        (xdg_dir / "blog.local.md").write_text(bad)
        out, err, rc = run(["check", "blog"])
        assert rc == 2
        assert "title" in out

    def test_check_all_no_overrides(self, patched_dirs):
        # No overrides installed; check all returns 0 with informational message
        out, err, rc = run(["check"])
        assert rc == 0
        assert "no user overrides installed" in out

    def test_check_all_with_overrides(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        (xdg_dir / "tutorial.local.md").write_text(
            MINIMAL_OVERRIDE.replace("Blog", "Tutorial")
        )
        out, err, rc = run(["check"])
        assert rc == 0
        assert "blog" in out
        assert "tutorial" in out

    def test_unknown_type(self, patched_dirs):
        out, err, rc = run(["check", "invalid"])
        assert rc == 1
        assert "unknown" in err

    def test_llm_mode_ok(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["--mode", "llm", "check", "blog"])
        assert rc == 0
        assert "blog|ok|" in out

    def test_llm_mode_fail(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(INCOMPLETE_PROFILE)
        out, err, rc = run(["--mode", "llm", "check", "blog"])
        assert rc == 2
        assert "blog|fail|" in out

    def test_llm_mode_no_overrides(self, patched_dirs):
        out, err, rc = run(["--mode", "llm", "check"])
        assert rc == 0
        assert "none" in out


# -- validate_profile --

class TestValidateProfile:
    def test_empty_file(self):
        issues = mv.validate_profile("blog", "")
        assert any("empty" in i for i in issues)

    def test_valid_override(self):
        issues = mv.validate_profile("blog", MINIMAL_OVERRIDE)
        assert issues == []

    def test_missing_override_title(self):
        # Built-in title format flagged when validated as override
        issues = mv.validate_profile("blog", MINIMAL_BUILTIN)
        assert any("title" in i for i in issues)

    def test_incomplete_override(self):
        issues = mv.validate_profile("blog", INCOMPLETE_PROFILE)
        assert any("missing section" in i for i in issues)

    def test_valid_heading_keys(self):
        text = MINIMAL_OVERRIDE + "\n```\nheading_style: assertion\nheading_case: sentence\n```\n"
        assert mv.validate_profile("blog", text) == []

    def test_bad_heading_style(self):
        text = MINIMAL_OVERRIDE + "\n```\nheading_style: statement\n```\n"
        issues = mv.validate_profile("blog", text)
        assert any("heading_style 'statement'" in i for i in issues)

    def test_empty_heading_case(self):
        issues = mv.validate_profile("blog", MINIMAL_OVERRIDE + "\nheading_case:\n")
        assert any("heading_case ''" in i for i in issues)

    def test_commented_heading_key_ignored(self):
        text = MINIMAL_OVERRIDE + "\n# heading_style: anything\n"
        assert mv.validate_profile("blog", text) == []


# -- no command --

class TestModeFlagPlacement:
    """`--mode` must work on either side of the subcommand.

    README documents it as "all subcommands accept --mode llm", and a caller
    piping output naturally writes `ls --mode llm`. Accepting only the
    leading position makes the documented form fail.
    """

    def test_mode_before_subcommand(self, patched_dirs):
        out, err, rc = run(["--mode", "llm", "ls"])
        assert rc == 0, err

    def test_mode_after_subcommand(self, patched_dirs):
        out, err, rc = run(["ls", "--mode", "llm"])
        assert rc == 0, err

    def test_both_positions_agree(self, patched_dirs):
        before, _, _ = run(["--mode", "llm", "ls"])
        after, _, _ = run(["ls", "--mode", "llm"])
        assert before == after


class TestNoCommand:
    def test_no_args_prints_help(self, patched_dirs):
        out, err, rc = run([])
        assert rc == 1


# -- shorten_path --

class TestShortenPath:
    def test_shortens_home(self):
        home = Path.home()
        p = home / "something" / "file.md"
        assert mv.shorten_path(p).startswith("~")

    def test_leaves_other_paths(self):
        p = Path("/tmp/file.md")
        assert mv.shorten_path(p) == "/tmp/file.md"
