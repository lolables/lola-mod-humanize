"""Tests for extract-text.py"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import extract_text

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'extract-text.py'


def run_extract(source: str, output: str | None = None) -> tuple[str, str, int]:
    """Run extract-text.py, return (stdout, stderr, returncode)."""
    cmd = ['python3', str(SCRIPT), source]
    if output:
        cmd.extend(['-o', output])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout, result.stderr, result.returncode


class TestPlaintext:
    def test_extracts_markdown(self, tmp_path):
        md = tmp_path / 'test.md'
        md.write_text('# Hello\n\nThis is a test.')
        stdout, stderr, rc = run_extract(str(md))
        assert rc == 0
        assert '# Hello' in stdout
        assert 'This is a test.' in stdout

    def test_extracts_txt(self, tmp_path):
        txt = tmp_path / 'test.txt'
        txt.write_text('Plain text content.')
        stdout, _, rc = run_extract(str(txt))
        assert rc == 0
        assert 'Plain text content.' in stdout

    def test_extracts_html(self, tmp_path):
        html = tmp_path / 'test.html'
        html.write_text('<html><body><p>HTML content</p></body></html>')
        stdout, _, rc = run_extract(str(html))
        assert rc == 0
        assert 'HTML content' in stdout


class TestDirectory:
    def test_concatenates_multiple_files(self, tmp_path):
        (tmp_path / 'a.md').write_text('First file.')
        (tmp_path / 'b.txt').write_text('Second file.')
        stdout, stderr, rc = run_extract(str(tmp_path))
        assert rc == 0
        assert 'First file.' in stdout
        assert 'Second file.' in stdout
        assert 'FILE:' in stdout  # separator comments

    def test_ignores_unsupported_extensions(self, tmp_path):
        (tmp_path / 'good.md').write_text('Keep this.')
        (tmp_path / 'bad.png').write_bytes(b'\x89PNG binary')
        (tmp_path / 'bad.pyc').write_bytes(b'\x00\x00')
        stdout, _, rc = run_extract(str(tmp_path))
        assert rc == 0
        assert 'Keep this.' in stdout
        assert 'PNG' not in stdout

    def test_empty_directory(self, tmp_path):
        stdout, stderr, rc = run_extract(str(tmp_path))
        assert rc == 0
        assert stdout == ''
        assert '0 file(s)' in stderr

    def test_recursive(self, tmp_path):
        sub = tmp_path / 'sub' / 'deep'
        sub.mkdir(parents=True)
        (sub / 'nested.md').write_text('Found in subdirectory.')
        stdout, _, rc = run_extract(str(tmp_path))
        assert rc == 0
        assert 'Found in subdirectory.' in stdout


def _minimal_pdf(text: str) -> bytes:
    """Build a valid single-page PDF containing `text` using fpdf2."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', size=12)
    pdf.text(10, 20, text)
    return pdf.output()


class TestPdf:
    @pytest.mark.skipif(
        subprocess.run(['which', 'pdftotext'], capture_output=True).returncode != 0,
        reason='pdftotext not installed',
    )
    def test_extracts_pdf(self, tmp_path):
        pdf = tmp_path / 'test.pdf'
        pdf.write_bytes(_minimal_pdf('This is PDF test content.'))
        stdout, _, rc = run_extract(str(pdf))
        assert rc == 0
        assert 'PDF test content' in stdout


class TestPandocFormats:
    @pytest.mark.skipif(
        subprocess.run(['which', 'pandoc'], capture_output=True).returncode != 0,
        reason='pandoc not installed',
    )
    def test_extracts_rst(self, tmp_path):
        rst = tmp_path / 'test.rst'
        rst.write_text('Title\n=====\n\nRestructured text content.')
        stdout, _, rc = run_extract(str(rst))
        assert rc == 0
        assert 'Restructured text content' in stdout


class TestEdgeCases:
    def test_nonexistent_path(self):
        _, stderr, rc = run_extract('/nonexistent/path')
        assert rc == 1
        assert 'does not exist' in stderr

    def test_capabilities_flag(self):
        result = subprocess.run(
            ['python3', str(SCRIPT), '--capabilities'],
            capture_output=True, text=True,
        )
        assert 'Plaintext' in result.stderr
        assert 'PDF' in result.stderr
        assert 'Documents' in result.stderr

    def test_output_to_file(self, tmp_path):
        src = tmp_path / 'input.md'
        src.write_text('Output to file test.')
        out = tmp_path / 'output.txt'
        _, _, rc = run_extract(str(src), str(out))
        assert rc == 0
        assert out.read_text() == 'Output to file test.'


# ---------------------------------------------------------------------------
# In-process unit tests (these produce coverage data)
# ---------------------------------------------------------------------------

class TestCheckTool:
    def test_existing_tool(self):
        # python3 is always present in this environment
        assert extract_text.check_tool('python3') is True

    def test_missing_tool(self):
        assert extract_text.check_tool('_no_such_tool_xyz_') is False


class TestExtractPlaintextInProcess:
    def test_reads_file_content(self, tmp_path):
        f = tmp_path / 'hello.txt'
        f.write_text('hello world')
        assert extract_text.extract_plaintext(f) == 'hello world'

    def test_returns_empty_on_oserror(self, tmp_path):
        missing = tmp_path / 'ghost.txt'
        result = extract_text.extract_plaintext(missing)
        assert result == ''

    def test_replaces_bad_bytes(self, tmp_path):
        f = tmp_path / 'bad.txt'
        f.write_bytes(b'good \xff text')
        result = extract_text.extract_plaintext(f)
        assert 'good' in result
        assert 'text' in result


class TestExtractPdfInProcess:
    def test_skips_when_pdftotext_missing(self, tmp_path, capsys):
        f = tmp_path / 'doc.pdf'
        f.write_bytes(b'%PDF-1.4')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', False):
            result = extract_text.extract_pdf(f)
        assert result == ''
        assert 'pdftotext not installed' in capsys.readouterr().err

    def test_returns_stdout_on_success(self, tmp_path):
        f = tmp_path / 'doc.pdf'
        f.write_bytes(b'%PDF-1.4')
        mock_result = MagicMock(returncode=0, stdout='extracted text\n')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_pdf(f)
        assert result == 'extracted text\n'

    def test_returns_empty_on_nonzero_returncode(self, tmp_path, capsys):
        f = tmp_path / 'doc.pdf'
        f.write_bytes(b'%PDF-1.4')
        mock_result = MagicMock(returncode=1, stderr='bad pdf', stdout='')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_pdf(f)
        assert result == ''
        assert 'warn' in capsys.readouterr().err

    def test_returns_empty_on_timeout(self, tmp_path, capsys):
        f = tmp_path / 'doc.pdf'
        f.write_bytes(b'%PDF-1.4')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', True), \
             patch('subprocess.run', side_effect=subprocess.TimeoutExpired('pdftotext', 60)):
            result = extract_text.extract_pdf(f)
        assert result == ''
        assert 'timed out' in capsys.readouterr().err


class TestExtractPandocInProcess:
    def test_skips_when_pandoc_missing(self, tmp_path, capsys):
        f = tmp_path / 'doc.rst'
        f.write_text('Title\n=====\n')
        with patch.object(extract_text, 'HAS_PANDOC', False):
            result = extract_text.extract_pandoc(f)
        assert result == ''
        assert 'pandoc not installed' in capsys.readouterr().err

    def test_returns_stdout_on_success(self, tmp_path):
        f = tmp_path / 'doc.rst'
        f.write_text('Title\n=====\n')
        mock_result = MagicMock(returncode=0, stdout='Title\n')
        with patch.object(extract_text, 'HAS_PANDOC', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_pandoc(f)
        assert result == 'Title\n'

    def test_returns_empty_on_nonzero_returncode(self, tmp_path, capsys):
        f = tmp_path / 'doc.rst'
        f.write_text('bad content')
        mock_result = MagicMock(returncode=1, stderr='conversion failed', stdout='')
        with patch.object(extract_text, 'HAS_PANDOC', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_pandoc(f)
        assert result == ''
        assert 'warn' in capsys.readouterr().err

    def test_returns_empty_on_timeout(self, tmp_path, capsys):
        f = tmp_path / 'doc.rst'
        f.write_text('content')
        with patch.object(extract_text, 'HAS_PANDOC', True), \
             patch('subprocess.run', side_effect=subprocess.TimeoutExpired('pandoc', 60)):
            result = extract_text.extract_pandoc(f)
        assert result == ''
        assert 'timed out' in capsys.readouterr().err


class TestExtractFileInProcess:
    def test_plaintext_extensions(self, tmp_path):
        for ext in ('.md', '.txt', '.org'):
            f = tmp_path / f'file{ext}'
            f.write_text(f'content for {ext}')
            assert extract_text.extract_file(f) == f'content for {ext}'

    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = tmp_path / 'image.png'
        f.write_bytes(b'\x89PNG')
        assert extract_text.extract_file(f) == ''

    def test_html_with_pandoc_available(self, tmp_path):
        f = tmp_path / 'page.html'
        f.write_text('<p>Hello</p>')
        mock_result = MagicMock(returncode=0, stdout='Hello\n')
        with patch.object(extract_text, 'HAS_PANDOC', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_file(f)
        assert result == 'Hello\n'

    def test_html_without_pandoc_falls_back_to_raw(self, tmp_path):
        f = tmp_path / 'page.html'
        f.write_text('<p>Hello</p>')
        with patch.object(extract_text, 'HAS_PANDOC', False):
            result = extract_text.extract_file(f)
        assert '<p>Hello</p>' in result

    def test_pdf_extension_delegates_to_extract_pdf(self, tmp_path):
        f = tmp_path / 'doc.pdf'
        f.write_bytes(b'%PDF-1.4')
        mock_result = MagicMock(returncode=0, stdout='pdf text\n')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_file(f)
        assert result == 'pdf text\n'

    def test_pandoc_convert_extension_delegates(self, tmp_path):
        f = tmp_path / 'doc.docx'
        f.write_bytes(b'PK\x03\x04')  # zip magic (docx is a zip)
        mock_result = MagicMock(returncode=0, stdout='docx text\n')
        with patch.object(extract_text, 'HAS_PANDOC', True), \
             patch('subprocess.run', return_value=mock_result):
            result = extract_text.extract_file(f)
        assert result == 'docx text\n'


class TestFindSupportedFilesInProcess:
    def test_finds_supported_files(self, tmp_path):
        (tmp_path / 'a.md').write_text('A')
        (tmp_path / 'b.txt').write_text('B')
        (tmp_path / 'c.png').write_bytes(b'\x89PNG')
        found = extract_text.find_supported_files(tmp_path)
        names = [f.name for f in found]
        assert 'a.md' in names
        assert 'b.txt' in names
        assert 'c.png' not in names

    def test_results_are_sorted(self, tmp_path):
        for name in ('z.md', 'a.md', 'm.txt'):
            (tmp_path / name).write_text('x')
        found = extract_text.find_supported_files(tmp_path)
        paths = [f.name for f in found]
        assert paths == sorted(paths)

    def test_recurses_into_subdirectories(self, tmp_path):
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'nested.md').write_text('nested')
        found = extract_text.find_supported_files(tmp_path)
        names = [f.name for f in found]
        assert 'nested.md' in names

    def test_skips_all_unsupported_extensions(self, tmp_path):
        for name in ('img.jpg', 'data.json', 'binary.bin'):
            (tmp_path / name).write_bytes(b'\x00')
        found = extract_text.find_supported_files(tmp_path)
        assert found == []


class TestExtractSourceInProcess:
    def test_single_file_returns_text_and_count_one(self, tmp_path):
        f = tmp_path / 'doc.txt'
        f.write_text('hello')
        text, count = extract_text.extract_source(f)
        assert text == 'hello'
        assert count == 1

    def test_single_file_empty_returns_count_zero(self, tmp_path):
        f = tmp_path / 'doc.txt'
        f.write_text('')
        text, count = extract_text.extract_source(f)
        assert text == ''
        assert count == 0

    def test_nonexistent_path_returns_empty(self, tmp_path):
        missing = tmp_path / 'does_not_exist.md'
        text, count = extract_text.extract_source(missing)
        assert text == ''
        assert count == 0

    def test_directory_with_no_supported_files(self, tmp_path):
        (tmp_path / 'data.json').write_bytes(b'{}')
        text, count = extract_text.extract_source(tmp_path)
        assert text == ''
        assert count == 0

    def test_directory_concatenates_files_with_markers(self, tmp_path):
        (tmp_path / 'a.md').write_text('first')
        (tmp_path / 'b.txt').write_text('second')
        text, count = extract_text.extract_source(tmp_path)
        assert count == 2
        assert 'first' in text
        assert 'second' in text
        assert '<!-- FILE:' in text

    def test_directory_skips_files_that_produce_no_text(self, tmp_path):
        (tmp_path / 'good.txt').write_text('keep')
        bad = tmp_path / 'bad.pdf'
        bad.write_bytes(b'%PDF-1.4')
        with patch.object(extract_text, 'HAS_PDFTOTEXT', False):
            text, count = extract_text.extract_source(tmp_path)
        # Only the .txt file produced text; the .pdf was skipped
        assert count == 1
        assert 'keep' in text


class TestReportCapabilitiesInProcess:
    def test_prints_to_stderr(self, capsys):
        extract_text.report_capabilities()
        err = capsys.readouterr().err
        assert 'Plaintext' in err
        assert 'PDF' in err
        assert 'Documents' in err

    def test_reflects_pdftotext_availability(self, capsys):
        with patch.object(extract_text, 'HAS_PDFTOTEXT', False):
            extract_text.report_capabilities()
        err = capsys.readouterr().err
        assert 'NOT available' in err

    def test_reflects_pandoc_availability(self, capsys):
        with patch.object(extract_text, 'HAS_PANDOC', False):
            extract_text.report_capabilities()
        err = capsys.readouterr().err
        assert 'NOT available' in err
