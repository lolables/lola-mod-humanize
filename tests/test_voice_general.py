"""Tests for the general voice profile and the bundled-profile symlink invariant."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO_ROOT / 'reference' / 'voices'
BUNDLED_DIR = REPO_ROOT / 'module' / 'skills' / 'humanize' / 'reference' / 'voices'

BUILTIN_PROFILES = ('blog', 'tutorial', 'code-comments', 'code-design',
                    'code-docs', 'rfc', 'general')

REQUIRED_BUILTIN_SECTIONS = (
    'Register',
    'Sentence Structure',
    'Voice and Person',
    'Directness',
    'Formatting',
    'Vocabulary',
    'What This Voice Is NOT',
    'Basis',
)


class TestGeneralProfile:
    def test_canonical_file_exists(self):
        path = CANONICAL_DIR / 'general.md'
        assert path.is_file(), f'Missing {path}'

    def test_title_matches_convention(self):
        text = (CANONICAL_DIR / 'general.md').read_text(encoding='utf-8')
        first_line = text.splitlines()[0]
        assert first_line == '# Voice Profile: General', \
            f'First line should be "# Voice Profile: General", got: {first_line!r}'

    def test_has_all_required_sections(self):
        text = (CANONICAL_DIR / 'general.md').read_text(encoding='utf-8')
        for section in REQUIRED_BUILTIN_SECTIONS:
            assert f'## {section}' in text, f'Missing section: {section}'

    def test_no_em_dashes(self):
        text = (CANONICAL_DIR / 'general.md').read_text(encoding='utf-8')
        assert '\u2014' not in text, 'Voice profile must not contain em dashes'
        assert '\u2013' not in text, 'Voice profile must not contain en dashes'

    def test_mentions_diagrams(self):
        """The general voice should explicitly endorse diagrams when helpful."""
        text = (CANONICAL_DIR / 'general.md').read_text(encoding='utf-8').lower()
        assert 'diagram' in text, 'general voice should mention diagrams'


class TestSymlinkInvariant:
    """Bundled built-in profiles must be symlinks to the canonical reference/voices/ source."""

    @pytest.mark.parametrize('profile', BUILTIN_PROFILES)
    def test_bundled_profile_is_symlink(self, profile):
        bundled = BUNDLED_DIR / f'{profile}.md'
        assert bundled.is_symlink(), \
            f'{bundled} should be a symlink to canonical source'
        assert bundled.exists(), \
            f'{bundled} is a dangling symlink (target missing)'

    @pytest.mark.parametrize('profile', BUILTIN_PROFILES)
    def test_bundled_profile_resolves_to_canonical(self, profile):
        bundled = BUNDLED_DIR / f'{profile}.md'
        canonical = CANONICAL_DIR / f'{profile}.md'
        assert bundled.resolve() == canonical.resolve(), \
            f'{bundled} should resolve to {canonical}'

    @pytest.mark.parametrize('profile', BUILTIN_PROFILES)
    def test_bundled_profile_content_matches_canonical(self, profile):
        bundled = (BUNDLED_DIR / f'{profile}.md').read_text(encoding='utf-8')
        canonical = (CANONICAL_DIR / f'{profile}.md').read_text(encoding='utf-8')
        assert bundled == canonical, \
            f'{profile}.md content differs between bundled and canonical'

    def test_local_example_not_symlinked(self):
        """local.example.md intentionally differs between locations; must stay as separate files."""
        bundled = BUNDLED_DIR / 'local.example.md'
        assert bundled.is_file(), f'{bundled} missing'
        assert not bundled.is_symlink(), \
            'local.example.md must remain a real file (audience-specific content)'


class TestManageVoicesIntegration:
    @classmethod
    def _import_manage_voices(cls):
        spec = importlib.util.spec_from_file_location(
            'manage_voices',
            REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts' / 'manage-voices.py',
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_general_in_profile_types(self):
        mv = self._import_manage_voices()
        assert 'general' in mv.discover_profile_types(), \
            'manage-voices.py discover_profile_types() must include "general"'

    def test_profile_types_count_is_nine(self):
        mv = self._import_manage_voices()
        types = mv.discover_profile_types()
        assert len(types) == 9, \
            f'Expected 9 built-in profile types, got {len(types)}: {types}'

    def test_profile_types_match_canonical_files(self):
        """Every discover_profile_types() entry must have a real file at reference/voices/<type>.md."""
        mv = self._import_manage_voices()
        for ptype in mv.discover_profile_types():
            canonical = CANONICAL_DIR / f'{ptype}.md'
            assert canonical.is_file(), \
                f'discover_profile_types() contains "{ptype}" but {canonical} does not exist'


class TestHumanizeSkillSelection:
    SKILL_PATH = REPO_ROOT / 'module' / 'skills' / 'humanize' / 'SKILL.md'

    def _content(self):
        return self.SKILL_PATH.read_text(encoding='utf-8')

    def test_general_listed_as_known_profile(self):
        content = self._content()
        # The known-profile branch lists profile names in parens.
        assert 'general' in content, 'humanize SKILL.md must mention general'
        match = re.search(
            r'\(blog,[^)]*general[^)]*\)|\([^)]*general[^)]*blog[^)]*\)',
            content,
        )
        assert match, \
            'general must appear in the parenthesized known-profile list alongside blog'

    def test_priority_7_uses_general(self):
        content = self._content()
        row = re.search(r'\|\s*7\s*\|[^|]*\|\s*general[^\n]*', content)
        assert row, 'Priority 7 row in Profile Selection table must use general'
        bad = re.search(r'\|\s*7\s*\|[^|]*\|\s*blog\s*\|', content)
        assert not bad, 'Priority 7 row must not still default to blog'

    def test_fallback_checkpoint_present(self):
        content = self._content()
        assert 'CHECKPOINT: Confirm fallback voice' in content, \
            'New CHECKPOINT block missing'
        assert 'No specific voice detected' in content, \
            'Fallback prompt text missing'
        assert 'autonomous operation' in content or 'autonomous mode' in content, \
            'Autonomous-mode escape hatch must be documented'

    def test_load_fallback_uses_general(self):
        """The 'Load the profile(s)' fallback note should fall back to general, not blog."""
        content = self._content()
        # Find the line "First file found wins. If none found, warn and fall back to ...".
        match = re.search(r'fall back to (\w+)\.', content)
        assert match, 'Fallback statement must exist'
        assert match.group(1) == 'general', \
            f'Should fall back to general, not {match.group(1)!r}'
