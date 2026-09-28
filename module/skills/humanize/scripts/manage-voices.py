#!/usr/bin/env python3
"""
manage-voices.py: list, inspect, and manage Humanize voice profiles.

Usage:
    manage-voices.py ls                   List profiles and override status
    manage-voices.py cat <type>           Print active profile contents
    manage-voices.py cat --builtin <type> Print built-in profile
    manage-voices.py path <type>          Print path to active profile
    manage-voices.py rm [--yes] <type>    Remove user override (asks first;
                                          --yes required off a terminal)
    manage-voices.py check [<type>]       Validate profile(s) against schema

All subcommands accept --mode llm for machine-readable output, and
--for <file-or-dir> to find the project root from the file being
humanized instead of the current directory.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_SECTIONS = (
    "Register",
    "Sentence Structure",
    "Voice and Person",
    "Directness",
    "Courtesy",
    "Formatting",
    "Vocabulary",
    "What This Voice Is NOT",
    "Source",
    "Metrics",
)

HEADING_KEYS = {
    "heading_style": ("noun-phrase", "assertion"),
    "heading_case": ("title", "sentence"),
}

SCRIPT_DIR = Path(__file__).resolve().parent
BUILTIN_DIR = SCRIPT_DIR.parent / "reference" / "voices"


def discover_profile_types() -> tuple[str, ...]:
    """Built-in voice types, discovered from BUILTIN_DIR at call time.

    Reads BUILTIN_DIR live (not cached at import) so tests can monkeypatch
    it and so new voices register themselves with no code change. Excludes
    *.local.md overrides and *.example.md templates.
    """
    if not BUILTIN_DIR.is_dir():
        return ()
    names = set()
    for p in BUILTIN_DIR.glob("*.md"):
        if p.name.endswith(".local.md") or p.name.endswith(".example.md"):
            continue
        names.add(p.name[:-3])  # strip ".md"
    return tuple(sorted(names))


def xdg_voices_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "humanize" / "voices"


def run_git(args: list[str], cwd: Path | None) -> subprocess.CompletedProcess:
    """Run git in `cwd` with repo-configured program execution turned off.

    These lookups run inside repos the user may have just cloned. A repo's
    own config can name a program in core.fsmonitor, which git runs on any
    index read, so it is forced off. Raises OSError or TimeoutExpired.
    """
    return subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        cwd=cwd, capture_output=True, text=True, timeout=5,
    )


def project_root(start: Path | None = None) -> Path | None:
    """The top level of the git repo containing `start` (default: cwd), or None.

    "Project" means `git rev-parse --show-toplevel` run in `start`, or in
    the current working directory when it is None, matching how the file
    being humanized (or the pasted-input cwd) relates to its enclosing
    repo. Returns None when that directory is not inside a git repo, git
    is not installed, or the call times out.
    """
    try:
        result = run_git(["rev-parse", "--show-toplevel"], start)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    top = result.stdout.strip()
    if not top:
        return None
    return Path(top)


def tracked_check(root: Path, rel: Path) -> str | None:
    """Return why `rel` must be rejected as tracked, or None if git does not track it.

    Matches case-insensitively: on macOS and Windows a tracked
    Reference/voices/X.local.md opens as reference/voices/X.local.md.
    `literal` keeps the profile name from acting as a glob. Any git failure
    rejects the file.
    """
    try:
        result = run_git(
            ["ls-files", "--error-unmatch", "--", f":(literal,icase){rel.as_posix()}"],
            root,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "git check failed"
    if result.returncode == 0:
        return "tracked by git"
    if result.returncode != 1:
        return "git check failed"
    return None


def project_override(profile_type: str,
                     start: Path | None = None) -> tuple[Path | None, str | None]:
    """Find the project-root override and decide whether to trust it.

    Returns (path, None) for a file that may be honored, (path, reason)
    for one that exists but must be ignored, and (None, None) when there
    is no project root or no file.

    The agent obeys a voice profile as instructions, and a cloned repo is
    untrusted input. Only a file the user created locally counts: one the
    project's git does not track, reached without following a symlink, and
    not inside a nested repo or submodule. The parent repo's ls-files
    cannot see what a submodule tracks, and git reports any path beyond a
    symlink as unmatched, so both would otherwise read as "untracked".
    Those checks run first. Any git failure rejects the file.
    """
    root = project_root(start)
    if root is None:
        return None, None
    rel = Path("reference", "voices", f"{profile_type}.local.md")
    path = root / rel
    if not (path.is_file() or path.is_symlink()):
        return None, None
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return path, "symlink"
    try:
        result = run_git(["rev-parse", "--show-toplevel"], path.parent)
    except (OSError, subprocess.TimeoutExpired):
        return path, "git check failed"
    if result.returncode != 0:
        return path, "git check failed"
    if Path(result.stdout.strip()).resolve() != root.resolve():
        return path, "inside a nested repo or submodule"
    return path, tracked_check(root, rel)


def resolve_profile(profile_type: str, builtin_only: bool = False,
                    start: Path | None = None) -> tuple[Path | None, str]:
    """Return (path, kind) for the active profile. kind is 'override' or 'built-in'.

    Override lookup order: XDG config dir, then the project root (the git
    repo containing `start`, or the cwd; untracked non-symlink files only),
    then the skill's own reference/voices/.
    """
    if not builtin_only:
        xdg = xdg_voices_dir() / f"{profile_type}.local.md"
        if xdg.is_file():
            return xdg, "override"
        project_local, rejected = project_override(profile_type, start)
        if project_local is not None and rejected is None:
            return project_local, "override"
        skill_local = BUILTIN_DIR / f"{profile_type}.local.md"
        if skill_local.is_file():
            return skill_local, "override"
    builtin = BUILTIN_DIR / f"{profile_type}.md"
    if builtin.is_file():
        return builtin, "built-in"
    return None, "missing"


def extract_sections(text: str) -> dict[str, str]:
    """Return {section_name: body_text} for all ## headings."""
    sections: dict[str, str] = {}
    current = None
    lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = m.group(1).strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def extract_source(path: Path) -> str:
    """Pull first content line from the provenance section.

    Overrides record provenance under `## Source` (the name the validator
    requires); the shipped built-ins use `## Basis`. Both are read so `ls`
    can show provenance for either kind of profile.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    sections = extract_sections(text)
    body = sections.get("Source") or sections.get("Basis", "")
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("---"):
            return stripped
    return ""


def shorten_path(p: Path) -> str:
    """Replace $HOME with ~ for display."""
    home = str(Path.home())
    s = str(p)
    if s.startswith(home):
        return "~" + s[len(home):]
    return s


def require_known_type(pt: str) -> bool:
    """Print error and return False if pt is not a known profile type."""
    if pt not in discover_profile_types():
        print(f"unknown profile type: {pt}", file=sys.stderr)
        return False
    return True


def print_ignored(pt: str, llm: bool, start: Path | None, file=None) -> None:
    """Say so when a project-root override exists but project_override() rejects it."""
    path, reason = project_override(pt, start)
    if path is None or reason is None:
        return
    if llm:
        print(f"{pt}|ignored|{path}|{reason}", file=file)
    else:
        print(f"  {pt}: ignored {shorten_path(path)} ({reason})", file=file)


# -- Subcommands --

def cmd_ls(args: argparse.Namespace) -> int:
    llm = args.mode == "llm"
    overrides = []
    builtins = []
    for pt in discover_profile_types():
        path, kind = resolve_profile(pt, start=args.start)
        if kind == "override":
            overrides.append((pt, path, kind))
        else:
            builtins.append((pt, path, kind))
    rows = overrides + builtins
    for pt, path, kind in rows:
        if kind == "override" and path:
            src = extract_source(path)
            if llm:
                print(f"{pt}|override|{path}|{src}")
            else:
                print(f"  {pt:<15s} override  {shorten_path(path)}")
                if src:
                    print(f"  {'':<15s}           ({src})")
        else:
            if llm:
                print(f"{pt}|built-in||")
            else:
                print(f"  {pt:<15s} built-in")
    for pt in discover_profile_types():
        print_ignored(pt, llm, args.start)
    return 0


def cmd_cat(args: argparse.Namespace) -> int:
    pt = args.type
    if not require_known_type(pt):
        return 1
    path, kind = resolve_profile(pt, builtin_only=args.builtin, start=args.start)
    if path is None:
        print(f"no profile found for: {pt}", file=sys.stderr)
        return 1
    try:
        print(path.read_text(encoding="utf-8"), end="")
    except OSError as e:
        print(f"can't read {path}: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_path(args: argparse.Namespace) -> int:
    pt = args.type
    if not require_known_type(pt):
        return 1
    path, kind = resolve_profile(pt, start=args.start)
    if path is None:
        print(f"no profile found for: {pt}", file=sys.stderr)
        return 1
    print_ignored(pt, args.mode == "llm", args.start, file=sys.stderr)
    print(path)
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    pt = args.type
    if not require_known_type(pt):
        return 1
    # Remove whichever override is active, so rm always undoes what ls reports.
    target, kind = resolve_profile(pt, start=args.start)
    if kind != "override":
        print(f"no user override for: {pt}", file=sys.stderr)
        return 1
    llm = args.mode == "llm"
    # Overrides are often gitignored, so a deletion cannot be undone. Only a
    # person at a terminal may confirm interactively; agents and scripts must
    # say --yes, since a prompt would hang them or be answered blindly. The
    # prompt goes to stderr so it stays visible when stdout is piped.
    if not args.yes:
        if llm or not sys.stdin.isatty() or not sys.stderr.isatty():
            print(f"refusing to remove {target} without --yes", file=sys.stderr)
            return 1
        print(f"remove {target}? [y/N] ", end="", file=sys.stderr, flush=True)
        try:
            answer = input()
        except EOFError:
            answer = ""
        except KeyboardInterrupt:
            print(f"\nnot removed: {target}", file=sys.stderr)
            return 130
        if answer.strip().lower() not in ("y", "yes"):
            print(f"not removed: {target}", file=sys.stderr)
            return 1
    try:
        target.unlink()
    except OSError as e:
        print(f"can't remove {target}: {e}", file=sys.stderr)
        return 1
    if llm:
        print(f"removed|{target}")
    else:
        print(f"  removed {shorten_path(target)}")
        # A lower-priority override may now be active, not the built-in.
        active, active_kind = resolve_profile(pt, start=args.start)
        if active:
            print(f"  active  {shorten_path(active)} ({active_kind})")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    llm = args.mode == "llm"
    if args.type:
        if not require_known_type(args.type):
            return 1
        types = [args.type]
    else:
        types = list(discover_profile_types())
    # Only check user overrides; built-ins are managed upstream
    checked = 0
    failures = 0
    for pt in types:
        print_ignored(pt, llm, args.start)
        path, kind = resolve_profile(pt, start=args.start)
        if kind != "override":
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            if llm:
                print(f"{pt}|error|can't read: {e}")
            else:
                print(f"  {pt}: can't read {path}: {e}")
            failures += 1
            continue
        issues = validate_profile(pt, text)
        if issues:
            failures += 1
            for issue in issues:
                if llm:
                    print(f"{pt}|fail|{issue}")
                else:
                    print(f"  {pt}: {issue}")
        else:
            if llm:
                print(f"{pt}|ok|")
            else:
                print(f"  {pt}: ok")
    if checked == 0:
        msg = f"no user override for: {args.type}" if args.type else "no user overrides installed"
        if llm:
            print(f"|none|{msg}")
        else:
            print(f"  {msg}")
        return 1 if args.type else 0
    return 2 if failures else 0


def validate_profile(profile_type: str, text: str) -> list[str]:
    """Return list of validation issues for a user override. Empty means valid."""
    issues: list[str] = []
    lines = text.strip().splitlines()
    if not lines:
        return ["file is empty"]
    title = lines[0]
    expected = re.compile(r"^#\s+Voice Profile Override:\s+.+", re.IGNORECASE)
    if not expected.match(title):
        issues.append("title should match '# Voice Profile Override: <Name>'")
    sections = extract_sections(text)
    for req in REQUIRED_SECTIONS:
        if req not in sections:
            issues.append(f"missing section: {req}")
        elif not sections[req]:
            issues.append(f"empty section: {req}")
    for key, allowed in HEADING_KEYS.items():
        for m in re.finditer(rf"^{key}:[ \t]*(\S*)", text, re.MULTILINE):
            if m.group(1) not in allowed:
                issues.append(f"{key} '{m.group(1)}' not one of: {', '.join(allowed)}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage-voices",
        description="List, inspect, and manage Humanize voice profiles.",
    )
    for_help = "Find the project root from this file or directory instead of the cwd"
    parser.add_argument("--mode", choices=["human", "llm"], default="human",
                        help="Output format (default: human)")
    parser.add_argument("--for", dest="for_path", metavar="PATH", help=for_help)

    # --mode and --for are accepted on either side of the subcommand. The
    # shared parent suppresses their defaults so `--mode llm ls` is not
    # clobbered by the subparser re-applying "human" when the flag comes first.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--mode", choices=["human", "llm"],
                        default=argparse.SUPPRESS,
                        help="Output format (default: human)")
    shared.add_argument("--for", dest="for_path", metavar="PATH",
                        default=argparse.SUPPRESS, help=for_help)

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("ls", parents=[shared],
                   help="List profiles and override status")

    cat_p = sub.add_parser("cat", parents=[shared],
                           help="Print active profile contents")
    cat_p.add_argument("type", help="Profile type")
    cat_p.add_argument("--builtin", action="store_true", help="Show built-in even if override exists")

    path_p = sub.add_parser("path", parents=[shared],
                            help="Print path to active profile")
    path_p.add_argument("type", help="Profile type")

    rm_p = sub.add_parser("rm", parents=[shared],
                          help="Remove user override")
    rm_p.add_argument("type", help="Profile type")
    rm_p.add_argument("-y", "--yes", action="store_true",
                      help="Remove without asking (required when not at a terminal)")

    check_p = sub.add_parser("check", parents=[shared],
                             help="Validate profile(s)")
    check_p.add_argument("type", nargs="?", help="Profile type (all if omitted)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    args.start = None
    if args.for_path is not None:
        if not args.for_path:
            print("--for needs a file or directory, not an empty string", file=sys.stderr)
            return 1
        target = Path(args.for_path)
        if not target.exists():
            print(f"--for path does not exist: {target}", file=sys.stderr)
            return 1
        args.start = target if target.is_dir() else target.parent

    cmds = {"ls": cmd_ls, "cat": cmd_cat, "path": cmd_path, "rm": cmd_rm, "check": cmd_check}
    return cmds[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
