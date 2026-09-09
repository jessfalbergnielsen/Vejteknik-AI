from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree
from zipfile import ZipFile


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}


@dataclass(frozen=True)
class TextSegment:
    path: str
    document_type: str
    text: str
    line: int | None = None
    page: int | None = None
    paragraph: int | None = None


@dataclass(frozen=True)
class SearchMatch:
    query: str
    file_path: str
    document_type: str
    excerpt: str
    start_char: int
    end_char: int
    line: int | None = None
    page: int | None = None
    paragraph: int | None = None

    @property
    def location(self) -> str:
        parts: list[str] = [self.file_path]
        if self.page is not None:
            parts.append(f"side {self.page}")
        if self.paragraph is not None:
            parts.append(f"afsnit {self.paragraph}")
        if self.line is not None:
            parts.append(f"linje {self.line}")
        parts.append(f"tegn {self.start_char}-{self.end_char}")
        return ", ".join(parts)


def _ensure_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def list_supported_documents(root: Path) -> list[Path]:
    resolved_root = root.resolve()
    documents: list[Path] = []
    for path in resolved_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if _ensure_within_root(path, resolved_root):
            documents.append(path)
    return sorted(documents)


def extract_segments(path: Path) -> list[TextSegment]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _extract_txt_segments(path)
    if suffix == ".pdf":
        return _extract_pdf_segments(path)
    if suffix == ".doc":
        return _extract_doc_segments(path)
    if suffix == ".docx":
        return _extract_docx_segments(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _extract_txt_segments(path: Path) -> list[TextSegment]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [
        TextSegment(path=str(path), document_type="txt", text=line, line=index)
        for index, line in enumerate(text.splitlines(), start=1)
    ]


def _extract_pdf_segments(path: Path) -> list[TextSegment]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF-søgning kræver pypdf. Installer afhængighederne fra requirements.txt."
        ) from exc

    segments: list[TextSegment] = []
    for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
        page_text = page.extract_text() or ""
        for line_number, line in enumerate(page_text.splitlines(), start=1):
            segments.append(
                TextSegment(
                    path=str(path),
                    document_type="pdf",
                    text=line,
                    page=page_number,
                    line=line_number,
                )
            )
    return segments


def _extract_doc_segments(path: Path) -> list[TextSegment]:
    extractor = next(
        (tool for tool in ("antiword", "catdoc") if shutil.which(tool)),
        None,
    )
    if not extractor:
        raise RuntimeError(
            "DOC-søgning kræver antiword eller catdoc installeret i miljøet."
        )

    result = subprocess.run(
        [extractor, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        TextSegment(path=str(path), document_type="doc", text=line, line=index)
        for index, line in enumerate(result.stdout.splitlines(), start=1)
    ]


def _extract_docx_segments(path: Path) -> list[TextSegment]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)

    segments: list[TextSegment] = []
    paragraph_number = 0
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(
            node.text or "" for node in paragraph.findall(".//w:t", namespace)
        ).strip()
        if not text:
            continue
        paragraph_number += 1
        segments.append(
            TextSegment(
                path=str(path),
                document_type="docx",
                text=text,
                paragraph=paragraph_number,
            )
        )
    return segments


def search_directory(root: Path, queries: Iterable[str]) -> tuple[list[SearchMatch], list[str]]:
    resolved_root = root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        raise ValueError(f"Rodmappen findes ikke: {resolved_root}")

    cleaned_queries = [query.strip() for query in queries if query and query.strip()]
    if not cleaned_queries:
        raise ValueError("Mindst én søgestreng skal angives.")

    matches: list[SearchMatch] = []
    errors: list[str] = []
    for path in list_supported_documents(resolved_root):
        try:
            segments = extract_segments(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
            continue

        for segment in segments:
            matches.extend(search_in_segment(segment, cleaned_queries))

    return matches, errors


def search_in_segment(segment: TextSegment, queries: Iterable[str]) -> list[SearchMatch]:
    matches: list[SearchMatch] = []
    haystack = segment.text.casefold()
    for query in queries:
        needle = query.casefold()
        offset = 0
        while True:
            found_at = haystack.find(needle, offset)
            if found_at == -1:
                break
            start_char = found_at + 1
            end_char = found_at + len(query)
            matches.append(
                SearchMatch(
                    query=query,
                    file_path=segment.path,
                    document_type=segment.document_type,
                    excerpt=_build_excerpt(segment.text, found_at, found_at + len(query)),
                    start_char=start_char,
                    end_char=end_char,
                    line=segment.line,
                    page=segment.page,
                    paragraph=segment.paragraph,
                )
            )
            offset = found_at + len(needle)
    return matches


def _build_excerpt(text: str, start: int, end: int, context: int = 60) -> str:
    left = max(0, start - context)
    right = min(len(text), end + context)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return f"{prefix}{text[left:right].strip()}{suffix}"


def _matches_to_json(matches: list[SearchMatch], errors: list[str]) -> str:
    payload = {
        "matches": [
            {**asdict(match), "location": match.location}
            for match in matches
        ],
        "errors": errors,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _matches_to_text(matches: list[SearchMatch], errors: list[str]) -> str:
    if not matches and not errors:
        return "Ingen fund."

    lines: list[str] = []
    for match in matches:
        lines.extend(
            [
                f"[{match.query}] {match.location}",
                f"  Uddrag: {match.excerpt}",
                "",
            ]
        )

    for error in errors:
        lines.append(f"FEJL: {error}")

    return "\n".join(lines).rstrip()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Søg efter ord eller sætninger i en lukket dokumentmappe."
    )
    parser.add_argument("root", type=Path, help="Mappe med dokumenter der må søges i.")
    parser.add_argument(
        "--query",
        action="append",
        required=True,
        help="Ord eller sætning der skal findes. Kan angives flere gange.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Udskriv resultater som JSON.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    matches, errors = search_directory(args.root, args.query)
    if args.json:
        print(_matches_to_json(matches, errors))
    else:
        print(_matches_to_text(matches, errors))
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
