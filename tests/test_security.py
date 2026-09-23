"""
test_security.py -- Security tests for Humanize scripts.

Validates that untrusted input (e.g., personal-sources.yml descriptions)
cannot achieve shell injection through the parsing pipeline.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "update-sources.sh"

# Marker file that a successful injection would create
INJECTION_MARKER = "/tmp/humanize-pwned-test"


@pytest.fixture(autouse=True)
def _cleanup_marker():
    """Remove the injection marker before and after each test."""
    try:
        os.unlink(INJECTION_MARKER)
    except FileNotFoundError:
        pass
    yield
    try:
        os.unlink(INJECTION_MARKER)
    except FileNotFoundError:
        pass


class TestPersonalSourcesInjection:
    """Verify that malicious YAML descriptions do not execute as shell code."""

    @staticmethod
    def _build_malicious_yaml(payload: str) -> str:
        """Return a personal-sources.yml with an injected description."""
        return (
            "sources:\n"
            "  - slug: legit-source\n"
            "    url: https://example.com/article\n"
            f"    description: {payload}\n"
        )

    def _run_load_personal_sources(self, yaml_content: str) -> subprocess.CompletedProcess:
        """
        Run only the load_personal_sources function in a temporary environment.

        We source the script up through the function definition, override
        PERSONAL_SOURCES_FILE, then call the function and dump the arrays.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_path = os.path.join(tmpdir, "personal-sources.yml")
            with open(yml_path, "w") as f:
                f.write(yaml_content)

            # Bash harness: source only the function, call it, print arrays
            harness = f"""
set -euo pipefail
SCRIPT_DIR="{PROJECT_ROOT / 'scripts'}"
PROJECT_ROOT="{PROJECT_ROOT}"
PERSONAL_SOURCES_FILE="{yml_path}"

# Disable colors
RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
log()  {{ echo "[update] $*"; }}
warn() {{ echo "[warn] $*"; }}
err()  {{ echo "[error] $*" >&2; }}
ok()   {{ echo "[ok] $*"; }}

declare -A SOURCES
declare -A SOURCE_DESCS

{self._extract_function()}

load_personal_sources

# Dump what was loaded
for slug in "${{!SOURCES[@]}}"; do
    echo "LOADED_SLUG=$slug"
    echo "LOADED_URL=${{SOURCES[$slug]}}"
    echo "LOADED_DESC=${{SOURCE_DESCS[$slug]}}"
done
"""
            result = subprocess.run(
                ["bash", "-c", harness],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result

    @staticmethod
    def _extract_function() -> str:
        """Extract the load_personal_sources function from update-sources.sh."""
        lines = SCRIPT.read_text().splitlines()
        in_func = False
        func_lines = []
        brace_depth = 0
        for line in lines:
            if line.startswith("load_personal_sources()"):
                in_func = True
            if in_func:
                func_lines.append(line)
                brace_depth += line.count("{") - line.count("}")
                if brace_depth == 0 and len(func_lines) > 1:
                    break
        return "\n".join(func_lines)

    def test_command_substitution_in_description(self):
        """A $(cmd) in description must NOT execute."""
        yaml = self._build_malicious_yaml(f"$(touch {INJECTION_MARKER})")
        result = self._run_load_personal_sources(yaml)

        assert not os.path.exists(INJECTION_MARKER), (
            "Shell injection via $() in description field -- "
            "the marker file was created"
        )
        # The source should still load (description stored as literal string)
        assert "LOADED_SLUG=legit-source" in result.stdout

    def test_backtick_injection_in_description(self):
        """Backtick command substitution must NOT execute."""
        yaml = self._build_malicious_yaml(f"`touch {INJECTION_MARKER}`")
        result = self._run_load_personal_sources(yaml)

        assert not os.path.exists(INJECTION_MARKER), (
            "Shell injection via backticks in description field -- "
            "the marker file was created"
        )

    def test_semicolon_injection_in_description(self):
        """Semicolon command chaining must NOT execute."""
        yaml = self._build_malicious_yaml(
            f'legit desc"; touch {INJECTION_MARKER}; echo "'
        )
        result = self._run_load_personal_sources(yaml)

        assert not os.path.exists(INJECTION_MARKER), (
            "Shell injection via semicolon in description field -- "
            "the marker file was created"
        )

    def test_clean_description_loads_correctly(self):
        """A normal description loads without issues."""
        yaml = self._build_malicious_yaml("My personal blog about security")
        result = self._run_load_personal_sources(yaml)

        assert result.returncode == 0
        assert "LOADED_SLUG=legit-source" in result.stdout
        assert "LOADED_URL=https://example.com/article" in result.stdout
        assert "LOADED_DESC=My personal blog about security" in result.stdout
