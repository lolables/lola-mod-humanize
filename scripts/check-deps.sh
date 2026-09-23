#!/usr/bin/env bash
# Dependency preflight — checks the tooling and Python packages the task targets assume.
# Usage: bash scripts/check-deps.sh [--mode human|llm] [project-root]
# Exit 0 if every required dependency is satisfied, 1 if any is missing or too old.
#
# Deliberately not `set -e`: every probe runs so one invocation reports the full
# list of problems rather than the first one.
set -uo pipefail

MODE=human
ROOT=.
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-human}"; shift 2 ;;
    *) ROOT="$1"; shift ;;
  esac
done

# lola < 0.4.5 copies the entire repo, .venv/ and .git/ included, into the
# module instead of honouring gitignore. See README Installation.
LOLA_MIN=0.4.5

errors=0
pass() { [ "$MODE" = "human" ] && printf "  \033[32mPASS\033[0m %s\n" "$1"; return 0; }
fail() { errors=$((errors + 1)); printf "  \033[31mFAIL\033[0m %s — %s\n" "$1" "$2"; return 0; }
skip() { [ "$MODE" = "human" ] && printf "  \033[2mSKIP %s — %s\033[0m\n" "$1" "$2"; return 0; }

[ "$MODE" = "human" ] && echo "=== Dependency check: $ROOT ==="

# Tooling the task targets shell out to.
require_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "$1"
  else
    fail "$1" "not on PATH — $2"
  fi
}

require_cmd uv "needed by task setup"
require_cmd python3 "needed by every Python target"
require_cmd git "needed by task scan DIFF=true and the humanize branch helper"
require_cmd curl "needed by task sources"

# The dev virtualenv and the packages task setup puts in it.
PY="$ROOT/.venv/bin/python3"
if [ -x "$PY" ]; then
  pass ".venv"
  # module:package — the import name differs from the install name for two of them.
  for spec in pytest:pytest pytest_cov:pytest-cov fpdf:fpdf2; do
    module="${spec%%:*}"
    package="${spec##*:}"
    if "$PY" -c "import $module" 2>/dev/null; then
      pass "$package"
    else
      fail "$package" "not installed in .venv — run: task setup"
    fi
  done
else
  fail ".venv" "missing at $ROOT/.venv — run: task setup"
fi

# lola is how the module gets installed, so it is optional for development but
# version-gated when present.
if command -v lola >/dev/null 2>&1; then
  version=$(lola --version 2>&1 | awk '{print $2}' | head -1 | cut -d. -f1-3)
  # sort -V so 0.4.10 compares as newer than 0.4.5, which a string compare gets wrong.
  if [ -n "$version" ] && \
     [ "$(printf '%s\n%s\n' "$LOLA_MIN" "$version" | sort -V | head -1)" = "$LOLA_MIN" ]; then
    pass "lola $version"
  else
    fail "lola ${version:-unknown}" \
      "$LOLA_MIN or newer required; older versions copy the whole repo into the module. Upgrade: uv tool install --force git+https://github.com/LobsterTrap/lola"
  fi
else
  skip "lola" "only needed to install the module (see README Installation)"
fi

# Optional extras. Their absence disables a target rather than breaking one.
if [ -x "$PY" ] && "$PY" -c "import torch" 2>/dev/null; then
  pass "torch"
else
  skip "torch" "task test:detect and task eval:detect will be skipped"
fi

if command -v ollama >/dev/null 2>&1; then
  pass "ollama"
else
  skip "ollama" "task eval needs it"
fi

if [ "$errors" -eq 0 ]; then
  [ "$MODE" = "human" ] && echo "Dependencies OK."
else
  echo "$errors dependency problem(s) above."
fi
[ "$errors" -eq 0 ]
