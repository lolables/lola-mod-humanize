#!/usr/bin/env python3
"""
manage-voices.py -- List, inspect, and manage Humanize voice profiles.

Usage:
    manage-voices.py ls                   List profiles and override status
    manage-voices.py cat <type>           Print active profile contents
    manage-voices.py cat --builtin <type> Print built-in profile
    manage-voices.py path <type>          Print path to active profile
    manage-voices.py rm <type>            Remove user override
    manage-voices.py check [<type>]       Validate profile(s) against schema

All subcommands accept --mode llm for machine-readable output.
"""
from __future__ import annotations

import argparse
import os
import re
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


def resolve_profile(profile_type: str, builtin_only: bool = False) -> tuple[Path | None, str]:
    """Return (path, kind) for the active profile. kind is 'override' or 'built-in'."""
    if not builtin_only:
        xdg = xdg_voices_dir() / f"{profile_type}.local.md"
        if xdg.is_file():
            return xdg, "override"
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


# -- Subcommands --

def cmd_ls(args: argparse.Namespace) -> int:
    llm = args.mode == "llm"
    overrides = []
    builtins = []
    for pt in discover_profile_types():
        path, kind = resolve_profile(pt)
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
    return 0


def cmd_cat(args: argparse.Namespace) -> int:
    pt = args.type
    if not require_known_type(pt):
        return 1
    path, kind = resolve_profile(pt, builtin_only=args.builtin)
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
    path, kind = resolve_profile(pt)
    if path is None:
        print(f"no profile found for: {pt}", file=sys.stderr)
        return 1
    print(path)
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    pt = args.type
    if not require_known_type(pt):
        return 1
    # Mirror resolve_profile's lookup order so anything reported as an
    # active override can also be removed. XDG wins when both exist.
    target = None
    for candidate in (xdg_voices_dir() / f"{pt}.local.md",
                      BUILTIN_DIR / f"{pt}.local.md"):
        if candidate.is_file():
            target = candidate
            break
    if target is None:
        print(f"no user override for: {pt}", file=sys.stderr)
        return 1
    target.unlink()
    llm = args.mode == "llm"
    if llm:
        print(f"removed|{target}")
    else:
        print(f"  removed {shorten_path(target)}")
        builtin, _ = resolve_profile(pt, builtin_only=True)
        if builtin:
            print(f"  active  {shorten_path(builtin)} (built-in)")
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
        path, kind = resolve_profile(pt)
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
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage-voices",
        description="List, inspect, and manage Humanize voice profiles.",
    )
    parser.add_argument("--mode", choices=["human", "llm"], default="human",
                        help="Output format (default: human)")

    # --mode is accepted on either side of the subcommand. The shared parent
    # suppresses its default so `--mode llm ls` is not clobbered by the
    # subparser re-applying "human" when the flag comes first.
    mode_parent = argparse.ArgumentParser(add_help=False)
    mode_parent.add_argument("--mode", choices=["human", "llm"],
                             default=argparse.SUPPRESS,
                             help="Output format (default: human)")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("ls", parents=[mode_parent],
                   help="List profiles and override status")

    cat_p = sub.add_parser("cat", parents=[mode_parent],
                           help="Print active profile contents")
    cat_p.add_argument("type", help="Profile type")
    cat_p.add_argument("--builtin", action="store_true", help="Show built-in even if override exists")

    path_p = sub.add_parser("path", parents=[mode_parent],
                            help="Print path to active profile")
    path_p.add_argument("type", help="Profile type")

    rm_p = sub.add_parser("rm", parents=[mode_parent],
                          help="Remove user override")
    rm_p.add_argument("type", help="Profile type")

    check_p = sub.add_parser("check", parents=[mode_parent],
                             help="Validate profile(s)")
    check_p.add_argument("type", nargs="?", help="Profile type (all if omitted)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    cmds = {"ls": cmd_ls, "cat": cmd_cat, "path": cmd_path, "rm": cmd_rm, "check": cmd_check}
    return cmds[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
