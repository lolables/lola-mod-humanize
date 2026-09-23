#!/usr/bin/env bash
# humanize-branch.sh -- Git safety check for Humanize.
#
# Called by the Humanize skill before transforming files in a git repo.
#
# Reports worktree state and nothing else. This script never moves HEAD.
# Humanize edits in place, and it only proceeds on a clean worktree, so
# `git diff` is already exactly the transformation and `git checkout -- .`
# reverts it. An earlier version created a `humanize/review-*` branch here.
# That bought no isolation: `git checkout -b` carries uncommitted changes
# forward, so the branch could only ever be cut from an already-clean tree,
# where the diff was recoverable anyway.
#
# Usage:
#   scripts/humanize-branch.sh check    # verify clean worktree, print status
#
# Exit codes:
#   0 -- success
#   1 -- dirty worktree (uncommitted changes), or bad usage
#   2 -- not a git repo (not an error, just informational)

set -euo pipefail

COMMAND="${1:-check}"

# --- Not a git repo? That's fine, just say so. ---
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "NOT_GIT"
    exit 2
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

case "$COMMAND" in
    check)
        # Check for uncommitted changes (staged or unstaged)
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            echo "DIRTY"
            echo "branch=$CURRENT_BRANCH"
            echo "Uncommitted changes detected. Commit or stash before running Humanize."
            git status --short
            exit 1
        fi

        # Check for untracked files (warn but don't block)
        UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | head -5)
        if [ -n "$UNTRACKED" ]; then
            echo "CLEAN_WITH_UNTRACKED"
            echo "branch=$CURRENT_BRANCH"
            echo "Untracked files present (not blocking):"
            echo "$UNTRACKED"
            exit 0
        fi

        echo "CLEAN"
        echo "branch=$CURRENT_BRANCH"
        exit 0
        ;;

    *)
        echo "Usage: $0 check" >&2
        exit 1
        ;;
esac
