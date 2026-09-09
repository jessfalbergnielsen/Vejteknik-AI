import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import document_search


class DocumentSearchTests(unittest.TestCase):
    def test_search_directory_returns_txt_line_and_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "lovtekst.txt").write_text(
                "Indledning\nDenne lovtekst beskriver vejbredde og sikkerhed.\nAfslutning\n",
                encoding="utf-8",
            )

            matches, errors = document_search.search_directory(root, ["vejbredde"])

            self.assertEqual(errors, [])
            self.assertEqual(len(matches), 1)
            match = matches[0]
            self.assertEqual(match.file_path, str(root / "lovtekst.txt"))
            self.assertEqual(match.line, 2)
            self.assertIsNone(match.page)
            self.assertIn("vejbredde", match.excerpt)
            self.assertIn("linje 2", match.location)

    def test_search_in_segment_reports_multiple_phrase_hits(self) -> None:
        segment = document_search.TextSegment(
            path="/tmp/eksempel.txt",
            document_type="txt",
            text="vejlov og vejlov igen",
            line=1,
        )

        matches = document_search.search_in_segment(segment, ["vejlov"])

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].start_char, 1)
        self.assertEqual(matches[1].start_char, 11)

    def test_extract_pdf_segments_uses_page_and_line_numbers(self) -> None:
        class FakePage:
            def __init__(self, text: str) -> None:
                self._text = text

            def extract_text(self) -> str:
                return self._text

        class FakeReader:
            def __init__(self, _: str) -> None:
                self.pages = [FakePage("første linje\nanden linje"), FakePage("tredje linje")]

        fake_module = types.SimpleNamespace(PdfReader=FakeReader)

        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            sys.modules, {"pypdf": fake_module}
        ):
            path = Path(temp_dir) / "haandbog.pdf"
            path.write_bytes(b"%PDF-1.4")

            segments = document_search.extract_segments(path)
            matches = document_search.search_in_segment(segments[1], ["anden"])

            self.assertEqual(segments[1].page, 1)
            self.assertEqual(segments[1].line, 2)
            self.assertEqual(matches[0].location, f"{path}, side 1, linje 2, tegn 1-5")

    def test_extract_doc_segments_uses_cli_converter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "document_search.shutil.which", return_value="/usr/bin/antiword"
        ), patch("document_search.subprocess.run") as run_mock:
            path = Path(temp_dir) / "vejledning.doc"
            path.write_bytes(b"fake")
            run_mock.return_value = subprocess.CompletedProcess(
                args=["antiword", str(path)],
                returncode=0,
                stdout="Sagsbehandling\nTeknisk vejledning\n",
                stderr="",
            )

            segments = document_search.extract_segments(path)

            self.assertEqual([segment.line for segment in segments], [1, 2])
            self.assertEqual(segments[1].text, "Teknisk vejledning")


if __name__ == "__main__":
    unittest.main()
