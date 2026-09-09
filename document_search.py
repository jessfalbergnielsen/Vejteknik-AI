from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised when dependency is missing
    PdfReader = None


WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


@dataclass
class FoundEntry:
    kind: str
    text: str
    file: str
    page: int | None
    line: int | None
    column: int | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a local folder and report words and sentences found in .txt and .pdf files."
        )
    )
    parser.add_argument("folder", type=Path, help="Folder to scan")
    parser.add_argument(
        "--kind",
        choices=("words", "sentences", "both"),
        default="both",
        help="Select which results to return",
    )
    parser.add_argument(
        "--contains",
        help="Only include results containing this text (case-insensitive)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print results as JSON",
    )
    return parser.parse_args()


def iter_supported_files(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def extract_words(text: str, file_path: Path, page: int | None, line_number: int) -> list[FoundEntry]:
    entries: list[FoundEntry] = []
    for match in WORD_PATTERN.finditer(text):
        entries.append(
            FoundEntry(
                kind="word",
                text=match.group(0),
                file=str(file_path),
                page=page,
                line=line_number,
                column=match.start() + 1,
            )
        )
    return entries


def extract_sentences(
    text: str, file_path: Path, page: int | None, line_number: int
) -> list[FoundEntry]:
    entries: list[FoundEntry] = []
    for match in SENTENCE_PATTERN.finditer(text):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        entries.append(
            FoundEntry(
                kind="sentence",
                text=sentence,
                file=str(file_path),
                page=page,
                line=line_number,
                column=match.start() + 1,
            )
        )
    return entries


def read_text_entries(file_path: Path) -> list[FoundEntry]:
    entries: list[FoundEntry] = []
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            entries.extend(extract_words(line, file_path, None, line_number))
            entries.extend(extract_sentences(line, file_path, None, line_number))
    return entries


def read_pdf_entries(file_path: Path) -> list[FoundEntry]:
    if PdfReader is None:
        raise RuntimeError(
            "PDF support requires pypdf. Install dependencies with: pip install -r requirements.txt"
        )

    entries: list[FoundEntry] = []
    reader = PdfReader(str(file_path))
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        for line_number, line in enumerate(page_text.splitlines(), start=1):
            entries.extend(extract_words(line, file_path, page_number, line_number))
            entries.extend(extract_sentences(line, file_path, page_number, line_number))
    return entries


def collect_entries(folder: Path) -> list[FoundEntry]:
    entries: list[FoundEntry] = []
    for file_path in iter_supported_files(folder):
        if file_path.suffix.lower() == ".txt":
            entries.extend(read_text_entries(file_path))
        elif file_path.suffix.lower() == ".pdf":
            entries.extend(read_pdf_entries(file_path))
    return entries


def filter_entries(
    entries: Iterable[FoundEntry], kind: str, contains: str | None
) -> list[FoundEntry]:
    contains_lower = contains.lower() if contains else None
    filtered: list[FoundEntry] = []

    for entry in entries:
        if kind == "words" and entry.kind != "word":
            continue
        if kind == "sentences" and entry.kind != "sentence":
            continue
        if contains_lower and contains_lower not in entry.text.lower():
            continue
        filtered.append(entry)

    return filtered


def format_entry(entry: FoundEntry) -> str:
    location_parts = [f"file={entry.file}"]
    if entry.page is not None:
        location_parts.append(f"page={entry.page}")
    if entry.line is not None:
        location_parts.append(f"line={entry.line}")
    if entry.column is not None:
        location_parts.append(f"column={entry.column}")
    return f"[{entry.kind}] {entry.text} ({', '.join(location_parts)})"


def main() -> int:
    args = parse_args()
    folder = args.folder.resolve()

    if not folder.exists() or not folder.is_dir():
        print(f"Folder not found: {folder}", file=sys.stderr)
        return 1

    try:
        entries = collect_entries(folder)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    filtered_entries = filter_entries(entries, args.kind, args.contains)

    if args.json:
        print(json.dumps([asdict(entry) for entry in filtered_entries], indent=2, ensure_ascii=False))
    else:
        for entry in filtered_entries:
            print(format_entry(entry))

    print(
        f"Found {len(filtered_entries)} matches in {len(list(iter_supported_files(folder)))} files.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
