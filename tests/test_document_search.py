import tempfile
import unittest
from pathlib import Path

from document_search import collect_entries, filter_entries


class DocumentSearchTests(unittest.TestCase):
    def test_collects_words_and_sentences_from_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir)
            sample = folder / "sample.txt"
            sample.write_text("Hello road team.\nSecond line here!", encoding="utf-8")

            entries = collect_entries(folder)
            words = filter_entries(entries, "words", None)
            sentences = filter_entries(entries, "sentences", None)

            self.assertTrue(any(entry.text == "Hello" and entry.line == 1 for entry in words))
            self.assertTrue(any(entry.text == "road" and entry.column == 7 for entry in words))
            self.assertTrue(any(entry.text == "Hello road team." and entry.line == 1 for entry in sentences))
            self.assertTrue(any(entry.text == "Second line here!" and entry.line == 2 for entry in sentences))

    def test_filters_entries_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir)
            sample = folder / "sample.txt"
            sample.write_text("Bridge inspection results.\nBridge closed today.", encoding="utf-8")

            entries = collect_entries(folder)
            filtered = filter_entries(entries, "both", "bridge")

            self.assertTrue(filtered)
            self.assertTrue(all("bridge" in entry.text.lower() for entry in filtered))


if __name__ == "__main__":
    unittest.main()
