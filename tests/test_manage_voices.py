"""Tests for manage-voices.py voice profile management."""
from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import importlib.util

import pytest

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
def patched_dirs(voice_dirs):
    """Patch module globals so manage-voices resolves against tmp dirs."""
    xdg_dir, builtin_dir = voice_dirs
    with mock.patch.object(mv, "BUILTIN_DIR", builtin_dir), \
         mock.patch.object(mv, "xdg_voices_dir", return_value=xdg_dir):
        yield xdg_dir, builtin_dir


def run(argv):
    """Run main() capturing stdout/stderr, return (stdout, stderr, exit_code)."""
    out, err = StringIO(), StringIO()
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
        out, err, rc = run(["rm", "blog"])
        assert rc == 0
        assert not override.exists()
        assert "removed" in out

    def test_shows_builtin_after_rm(self, patched_dirs):
        xdg_dir, _ = patched_dirs
        (xdg_dir / "blog.local.md").write_text(MINIMAL_OVERRIDE)
        out, err, rc = run(["rm", "blog"])
        assert "built-in" in out

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
        out, err, rc = run(["--mode", "llm", "rm", "blog"])
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
        out, err, rc = run(["rm", "blog"])
        assert rc == 0, err
        assert not override.exists()


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
