"""Tests for voice discovery and the deepened profile template."""
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MV_PATH = REPO / "module" / "skills" / "humanize" / "scripts" / "manage-voices.py"
VOICES_DIR = REPO / "reference" / "voices"
PROSE_VOICES = ["blog", "general", "tutorial", "rfc", "code-comments", "code-docs"]


def _load_mv():
    spec = importlib.util.spec_from_file_location("manage_voices", MV_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_discover_reads_builtin_dir_live(tmp_path, monkeypatch):
    mv = _load_mv()
    monkeypatch.setattr(mv, "BUILTIN_DIR", tmp_path)
    (tmp_path / "blog.md").write_text("# Voice Profile: Blog\n")
    (tmp_path / "rfc.md").write_text("# Voice Profile: RFC\n")
    (tmp_path / "blog.local.md").write_text("# override\n")  # must be excluded
    assert mv.discover_profile_types() == ("blog", "rfc")


def test_discover_picks_up_new_file(tmp_path, monkeypatch):
    mv = _load_mv()
    monkeypatch.setattr(mv, "BUILTIN_DIR", tmp_path)
    (tmp_path / "zzz.md").write_text("# Voice Profile: Zzz\n")
    assert "zzz" in mv.discover_profile_types()


def test_discover_excludes_overrides_and_examples(tmp_path, monkeypatch):
    mv = _load_mv()
    monkeypatch.setattr(mv, "BUILTIN_DIR", tmp_path)
    (tmp_path / "blog.md").write_text("# Voice Profile: Blog\n")
    (tmp_path / "blog.local.md").write_text("# override\n")
    (tmp_path / "local.example.md").write_text("# template\n")
    got = mv.discover_profile_types()
    assert got == ("blog",)
    assert "local.example" not in got


def test_real_repo_lists_nine_voices():
    mv = _load_mv()
    got = set(mv.discover_profile_types())
    expected = {"blog", "general", "tutorial", "rfc", "code-comments",
                "code-design", "code-docs", "release-notes", "academic"}
    assert expected.issubset(got)


def test_lint_picks_up_new_voice(tmp_path):
    """task lint must lint a newly added voice without editing the Taskfile."""
    voices = REPO / "reference" / "voices"
    probe = voices / "zzprobe.md"
    probe.write_text("# Voice Profile: Zzprobe\n\nbody\n")
    try:
        proc = subprocess.run(
            ["task", "lint"], cwd=str(REPO),
            capture_output=True, text=True, timeout=120,
        )
        assert "zzprobe" in proc.stdout, proc.stdout
    finally:
        probe.unlink()


def test_courtesy_examples_avoid_sycophancy():
    """The courtesy catalog must not present banned AI filler as 'courteous'.
    Guards against the wash reintroducing what Pass 3 deletes."""
    text = (REPO / "reference" / "courtesy.md").read_text()
    banned = ["Great question", "I hope this helps", "I'd be happy to",
              "Let me know if you need anything else"]
    for phrase in banned:
        for line in text.splitlines():
            if phrase in line:
                assert any(m in line for m in ("Banned", "not courtesy", "|")), \
                    f"{phrase!r} appears outside the banned table: {line!r}"


def test_courtesy_symlink_resolves():
    link = REPO / "module" / "skills" / "humanize" / "reference" / "courtesy.md"
    assert link.is_symlink()
    assert link.resolve() == (REPO / "reference" / "courtesy.md").resolve()


EXAMPLE_TEMPLATES = [
    VOICES_DIR / "local.example.md",
    REPO / "module" / "skills" / "humanize" / "reference" / "voices" / "local.example.md",
]


@pytest.mark.parametrize("template", EXAMPLE_TEMPLATES, ids=["canonical", "bundled"])
def test_starter_template_passes_validator(template):
    """The template users are told to copy must validate as shipped.

    README points readers at this file as the manual route to a custom
    profile. If it is missing a required section, every user who follows
    the instructions gets a failing `task voices -- check` before they have
    written anything.
    """
    mv = _load_mv()
    assert mv.validate_profile("blog", template.read_text()) == []


@pytest.mark.parametrize("template", EXAMPLE_TEMPLATES, ids=["canonical", "bundled"])
def test_starter_template_lists_every_profile(template):
    """Both copies must name all discoverable profiles.

    The two files deliberately differ by audience (see
    test_local_example_not_symlinked), which is exactly why the shared
    facts need a guard: the bundled copy silently fell three profiles
    behind while the canonical one stayed current.
    """
    mv = _load_mv()
    text = template.read_text()
    missing = [p for p in mv.discover_profile_types() if p not in text]
    assert not missing, f"{template} omits profiles: {missing}"


def test_writing_discipline_is_shipped():
    """README tells readers to copy this file, so it has to ship.

    lola installs `module/` only. Left unlinked, the file exists in the
    repo but never reaches an installed user.
    """
    link = REPO / "module" / "skills" / "humanize" / "reference" / "writing-discipline.md"
    assert link.is_symlink()
    assert link.resolve() == (REPO / "reference" / "writing-discipline.md").resolve()


@pytest.mark.parametrize("name", PROSE_VOICES)
def test_prose_voice_has_new_sections(name):
    text = (VOICES_DIR / f"{name}.md").read_text()
    assert "## Courtesy" in text
    assert "## AI Tells To Avoid" in text
    assert "## Target Metrics" in text
    assert "em_dash_per_1k:" in text


def test_code_design_has_courtesy_no_metrics():
    text = (VOICES_DIR / "code-design.md").read_text()
    assert "## Courtesy" in text
    assert "## AI Tells To Avoid" in text
    assert "## Target Metrics" not in text


SKILL = REPO / "module" / "skills" / "humanize" / "SKILL.md"


def test_skill_documents_politeness_mode_and_courtesy():
    text = SKILL.read_text()
    assert "Politeness" in text          # mode row
    assert "politeness wash" in text.lower()
    assert "courtesy" in text.lower()
    assert "reference/courtesy.md" in text


NEW_VOICES = ["release-notes", "academic"]


@pytest.mark.parametrize("name", NEW_VOICES)
def test_new_voice_exists_and_symlinked(name):
    canonical = VOICES_DIR / f"{name}.md"
    assert canonical.is_file()
    text = canonical.read_text()
    assert text.startswith("# Voice Profile:")
    assert "## Courtesy" in text
    assert "## AI Tells To Avoid" in text
    link = REPO / "module" / "skills" / "humanize" / "reference" / "voices" / f"{name}.md"
    assert link.is_symlink()
    assert link.resolve() == canonical.resolve()


HEADING_STYLES = {
    "academic": "noun-phrase", "blog": "assertion", "code-docs": "noun-phrase",
    "general": "noun-phrase", "release-notes": "noun-phrase", "rfc": "noun-phrase",
    "tutorial": "noun-phrase",
}


@pytest.mark.parametrize("name,style", sorted(HEADING_STYLES.items()))
def test_text_voice_sets_heading_keys(name, style):
    text = (VOICES_DIR / f"{name}.md").read_text()
    assert re.search(rf"^heading_style:\s+{style}$", text, re.M)
    assert re.search(r"^heading_case:\s+title$", text, re.M)


@pytest.mark.parametrize("name", ["code-comments", "code-design"])
def test_code_voice_has_no_heading_keys(name):
    text = (VOICES_DIR / f"{name}.md").read_text()
    assert "heading_style:" not in text
    assert "heading_case:" not in text
