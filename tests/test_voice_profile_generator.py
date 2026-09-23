"""Tests for voice-profile-generator skill reference files."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent / 'module' / 'skills' / 'voice-profile-generator'
REPO_ROOT = Path(__file__).resolve().parent.parent

_vspec = importlib.util.spec_from_file_location(
    'vocabulary',
    REPO_ROOT / 'module' / 'skills' / 'humanize' / 'scripts' / 'vocabulary.py',
)
_vmod = importlib.util.module_from_spec(_vspec)
sys.modules['vocabulary'] = _vmod
_vspec.loader.exec_module(_vmod)

from vocabulary import TIER1_WORDS


def _banned_in_prose(line: str, word: str) -> bool:
    """Return True if a banned word appears in running prose (not in a rejection/quote context)."""
    low = line.lower()
    if word not in low:
        return False
    if re.search(r'`[^`]*' + re.escape(word) + r'[^`]*`', low):
        return False
    if 'not' in low or 'avoid' in low or 'ban' in low:
        return False
    return True


REQUIRED_PROFILE_SECTIONS = [
    'Register',
    'Sentence Structure',
    'Voice and Person',
    'Directness',
    'Courtesy',
    'Formatting',
    'Vocabulary',
    'What This Voice Is NOT',
    'Source',
    'Metrics',
]


class TestProfileSchema:
    def test_schema_file_exists(self):
        schema = SKILL_DIR / 'reference' / 'profile-schema.md'
        assert schema.exists(), f'Missing {schema}'

    def test_schema_has_required_sections(self):
        schema = SKILL_DIR / 'reference' / 'profile-schema.md'
        content = schema.read_text()
        for section in REQUIRED_PROFILE_SECTIONS:
            assert section in content, f'Schema missing section: {section}'

    def test_schema_no_tier1_ai_vocabulary(self):
        schema = SKILL_DIR / 'reference' / 'profile-schema.md'
        lines = schema.read_text().splitlines()
        for word in TIER1_WORDS:
            for i, line in enumerate(lines, 1):
                if _banned_in_prose(line, word):
                    pytest.fail(f'Tier 1 AI word "{word}" used in schema line {i}: {line.strip()}')


REQUIRED_ANALYSIS_DIMENSIONS = [
    'Register',
    'Sentence structure',
    'Voice and person',
    'Humor',
    'Rhetorical devices',
    'Formatting',
    'Vocabulary',
    'Attitude toward the reader',
]


class TestSubagentPrompt:
    def test_prompt_file_exists(self):
        prompt = SKILL_DIR / 'reference' / 'subagent-prompt.md'
        assert prompt.exists(), f'Missing {prompt}'

    def test_prompt_covers_all_dimensions(self):
        prompt = SKILL_DIR / 'reference' / 'subagent-prompt.md'
        content = prompt.read_text()
        for dim in REQUIRED_ANALYSIS_DIMENSIONS:
            assert dim.lower() in content.lower(), f'Subagent prompt missing dimension: {dim}'

    def test_prompt_specifies_output_format(self):
        prompt = SKILL_DIR / 'reference' / 'subagent-prompt.md'
        content = prompt.read_text()
        assert 'example' in content.lower() or 'output' in content.lower(), \
            'Subagent prompt should specify expected output format'

    def test_prompt_no_tier1_ai_vocabulary(self):
        prompt = SKILL_DIR / 'reference' / 'subagent-prompt.md'
        lines = prompt.read_text().splitlines()
        for i, line in enumerate(lines, 1):
            for word in TIER1_WORDS:
                if _banned_in_prose(line, word):
                    pytest.fail(f'Tier 1 AI word "{word}" in subagent prompt line {i}: {line.strip()}')


class TestSkillFile:
    def test_skill_file_exists(self):
        skill = SKILL_DIR / 'SKILL.md'
        assert skill.exists(), f'Missing {skill}'

    def test_skill_has_frontmatter(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        assert content.startswith('---'), 'Skill must start with YAML frontmatter'
        second_marker = content.index('---', 3)
        frontmatter = content[3:second_marker]
        assert 'name:' in frontmatter, 'Frontmatter must include name'
        assert 'description:' in frontmatter, 'Frontmatter must include description'

    def test_skill_name_is_correct(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        second_marker = content.index('---', 3)
        frontmatter = content[3:second_marker]
        assert 'voice-profile-generator' in frontmatter

    def test_skill_references_all_phases(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        for phase in ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Phase 5']:
            assert phase in content, f'Skill missing {phase}'

    def test_skill_phases_in_order(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        positions = [content.index(f'Phase {n}') for n in range(1, 6)]
        assert positions == sorted(positions), 'Phases must appear in ascending order'

    def test_skill_frontmatter_has_trigger_phrases(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        second_marker = content.index('---', 3)
        frontmatter = content[3:second_marker].lower()
        triggers = ['generate voice profile', 'create voice profile', 'analyze my writing']
        found = sum(1 for t in triggers if t in frontmatter)
        assert found >= 2, f'Frontmatter should contain trigger phrases, found {found} of {len(triggers)}'

    def test_skill_has_all_profile_types(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        for ptype in ['blog', 'general', 'tutorial', 'code-docs', 'code-comments',
                      'code-design', 'rfc', 'release-notes', 'academic']:
            assert ptype in content, f'Skill missing profile type: {ptype}'

    def test_skill_references_subagent_prompt(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        assert 'subagent-prompt' in content, 'Skill must reference subagent prompt'

    def test_skill_references_profile_schema(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        assert 'profile-schema' in content, 'Skill must reference profile schema'

    def test_skill_references_analyze_voice(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        assert 'analyze-voice' in content or 'analyze_voice' in content, \
            'Skill must reference analyze-voice.py'

    def test_skill_defines_interactive_decisions(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text()
        decision_keywords = ['register', 'humor', 'formatting', 'distinctive', 'voice is not']
        found = sum(1 for kw in decision_keywords if kw.lower() in content.lower())
        assert found >= 4, f'Skill should define at least 4 interactive decision categories, found {found}'

    def test_skill_defines_skip_logic(self):
        skill = SKILL_DIR / 'SKILL.md'
        content = skill.read_text().lower()
        assert 'no-interactive' in content or 'skip' in content, \
            'Skill must define skip/non-interactive logic'

    def test_skill_no_tier1_ai_vocabulary(self):
        skill = SKILL_DIR / 'SKILL.md'
        lines = skill.read_text().splitlines()
        for i, line in enumerate(lines, 1):
            for word in TIER1_WORDS:
                if _banned_in_prose(line, word):
                    pytest.fail(f'Tier 1 AI word "{word}" in SKILL.md line {i}: {line.strip()}')


class TestTaskfileIntegration:
    def test_taskfile_owns_no_install_target(self):
        """lola installs the module. Task covers development only."""
        content = (REPO_ROOT / 'Taskfile.yml').read_text()
        stale = re.findall(r'^  (install|uninstall):', content, re.M)
        assert not stale, \
            f'Taskfile defines {stale}; lola owns installation, so these must not exist'

    def test_readme_documents_the_lola_commands(self):
        """The four commands a user needs, including the ones easy to get wrong."""
        readme = (REPO_ROOT / 'README.md').read_text()
        for command in (
            # Registering the checkout is a separate step from installing it,
            # and has to be repeated after every source change.
            'lola mod add -n humanize ./',
            # lola defaults to project scope, so user scope must be explicit.
            'lola install humanize -a <assistant> --scope user',
            'lola uninstall humanize -a <assistant> --scope user',
            # Deregistering is guarded: mod rm does not remove installs.
            "lola list | grep -q '^humanize$' || lola mod rm -f humanize",
        ):
            assert command in readme, f'README must document `{command}`'

    def test_skill_present_at_module_location(self):
        """voice-profile-generator must live under module/skills/ for lola to discover it."""
        skill_md = REPO_ROOT / 'module' / 'skills' / 'voice-profile-generator' / 'SKILL.md'
        assert skill_md.is_file(), f'{skill_md} missing — lola would not install it'
