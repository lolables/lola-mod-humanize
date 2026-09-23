#!/usr/bin/env python3
"""
extract-text.py -- Extract plain text from various document formats.

Supports: .md, .txt, .rst, .adoc, .org, .tex, .html, .htm,
          .pdf (via pdftotext), .docx/.odt/.epub/.rtf (via pandoc)

Usage:
    python3 extract-text.py <file_or_directory> [--output <outfile>]

If given a directory, recursively finds all supported files and
concatenates their extracted text. Unsupported formats are skipped
with a warning to stderr.

Tools used (graceful fallback if missing):
    pdftotext  (poppler-utils)  -- PDF extraction
    pandoc                      -- DOCX, ODT, EPUB, RTF, LaTeX conversion

If a tool is missing, files requiring it are skipped with a warning.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# File extensions grouped by extraction method
PLAINTEXT_EXTS = {'.md', '.txt', '.org'}
# These have markup that pandoc can strip to plain text (falls back to raw read)
PANDOC_STRIP_EXTS = {'.html', '.htm', '.rst', '.adoc'}
PDF_EXTS = {'.pdf'}
PANDOC_CONVERT_EXTS = {'.docx', '.odt', '.epub', '.rtf', '.tex', '.latex'}

ALL_SUPPORTED = PLAINTEXT_EXTS | PANDOC_STRIP_EXTS | PDF_EXTS | PANDOC_CONVERT_EXTS


def check_tool(name: str) -> bool:
    return shutil.which(name) is not None


HAS_PDFTOTEXT = check_tool('pdftotext')
HAS_PANDOC = check_tool('pandoc')


def extract_plaintext(path: Path) -> str:
    try:
        return path.read_text(errors='replace')
    except OSError as e:
        print(f'  warn: cannot read {path}: {e}', file=sys.stderr)
        return ''


def extract_pdf(path: Path) -> str:
    if not HAS_PDFTOTEXT:
        print(f'  skip: {path} (pdftotext not installed, `apt/dnf install poppler-utils`)',
              file=sys.stderr)
        return ''
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', str(path), '-'],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return result.stdout
        print(f'  warn: pdftotext failed on {path}: {result.stderr.strip()}',
              file=sys.stderr)
        return ''
    except subprocess.TimeoutExpired:
        print(f'  warn: pdftotext timed out on {path}', file=sys.stderr)
        return ''


def extract_pandoc(path: Path) -> str:
    if not HAS_PANDOC:
        print(f'  skip: {path} (pandoc not installed, `apt/dnf install pandoc`)',
              file=sys.stderr)
        return ''
    try:
        result = subprocess.run(
            ['pandoc', '--to=plain', '--wrap=none', str(path)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return result.stdout
        print(f'  warn: pandoc failed on {path}: {result.stderr.strip()}',
              file=sys.stderr)
        return ''
    except subprocess.TimeoutExpired:
        print(f'  warn: pandoc timed out on {path}', file=sys.stderr)
        return ''


def extract_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in PLAINTEXT_EXTS:
        return extract_plaintext(path)
    if ext in PANDOC_STRIP_EXTS:
        # Use pandoc to strip markup (HTML tags, RST directives, etc.)
        # Falls back to raw read if pandoc is unavailable
        if HAS_PANDOC:
            return extract_pandoc(path)
        return extract_plaintext(path)
    if ext in PDF_EXTS:
        return extract_pdf(path)
    if ext in PANDOC_CONVERT_EXTS:
        return extract_pandoc(path)
    return ''


def find_supported_files(directory: Path) -> list[Path]:
    files = []
    for root, _dirs, filenames in os.walk(directory):
        for fname in sorted(filenames):
            p = Path(root) / fname
            if p.suffix.lower() in ALL_SUPPORTED:
                files.append(p)
    files.sort()
    return files


def extract_source(source_path: Path) -> tuple[str, int]:
    """Extract text from a file or directory. Returns (text, file_count)."""
    if source_path.is_file():
        text = extract_file(source_path)
        return text, 1 if text else 0

    if source_path.is_dir():
        files = find_supported_files(source_path)
        if not files:
            return '', 0
        parts = []
        for f in files:
            text = extract_file(f)
            if text:
                parts.append(f'<!-- FILE: {f} -->\n{text}')
        return '\n\n'.join(parts), len(parts)

    return '', 0


def report_capabilities():
    """Print which extraction tools are available."""
    print('Text extraction capabilities:', file=sys.stderr)
    print(f'  Plaintext ({", ".join(sorted(PLAINTEXT_EXTS))}): always available',
          file=sys.stderr)
    status = 'available' if HAS_PDFTOTEXT else 'NOT available (install poppler-utils)'
    print(f'  PDF (.pdf): {status}', file=sys.stderr)
    status = 'available' if HAS_PANDOC else 'NOT available (install pandoc)'
    strip_exts = ', '.join(sorted(PANDOC_STRIP_EXTS))
    conv_exts = ', '.join(sorted(PANDOC_CONVERT_EXTS))
    print(f'  Markup stripping ({strip_exts}): {status} (falls back to raw read)',
          file=sys.stderr)
    print(f'  Documents ({conv_exts}): {status}', file=sys.stderr)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract text from documents')
    parser.add_argument('source', nargs='?', help='File or directory to extract from')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--capabilities', action='store_true',
                        help='Report available extraction tools and exit')
    args = parser.parse_args()

    if args.capabilities:
        report_capabilities()
        sys.exit(0)

    if not args.source:
        parser.error('source is required (use --capabilities to check tools)')

    source = Path(args.source)
    if not source.exists():
        print(f'error: {source} does not exist', file=sys.stderr)
        sys.exit(1)

    text, count = extract_source(source)

    if args.output:
        Path(args.output).write_text(text)
    else:
        sys.stdout.write(text)

    print(f'Extracted {count} file(s) from {source}', file=sys.stderr)


if __name__ == '__main__':
    main()
