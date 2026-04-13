from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .sniff import sniff_binary_kind


@dataclass
class ParsedDocument:
    """Normalized output from any format-specific parser."""

    text: str
    source_label: str
    format_id: str


class DocumentParser(ABC):
    """Extend this for new formats (e.g. HTML, RTF) without changing callers."""

    format_id: str

    @abstractmethod
    def supports(self, filename: str, content_type: str | None) -> bool:
        pass

    @abstractmethod
    def parse(self, raw: bytes, source_label: str) -> ParsedDocument:
        pass


_LEGACY_WORD_MSG = (
    "This file is legacy Microsoft Word .doc (binary OLE format), not a modern .docx (Office Open XML). "
    "The filename may be wrong or the file was saved as .doc. Open it in Word or Google Docs, then "
    "Save As Word (.docx) or export PDF and upload that file. "
    "Genuine .docx files are ZIP packages internally; this message means the file bytes are not OOXML—you "
    "are not being asked to upload a ZIP archive."
)


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser]) -> None:
        self._parsers = parsers
        self._by_id = {p.format_id: p for p in parsers}

    def parse(self, raw: bytes, filename: str, content_type: str | None) -> ParsedDocument:
        kind = sniff_binary_kind(raw)
        name_lower = (filename or "").lower()

        # --- Route by actual bytes when the filename is wrong ---
        if name_lower.endswith((".docx", ".docm")):
            if kind == "pdf":
                return self._by_id["pdf"].parse(raw, filename)
            if kind == "ole_legacy":
                raise ValueError(
                    f"{_LEGACY_WORD_MSG} (file: {filename!r})"
                )
        if name_lower.endswith(".doc"):
            if kind == "pdf":
                return self._by_id["pdf"].parse(raw, filename)
            if kind == "ole_legacy":
                raise ValueError(
                    f"{_LEGACY_WORD_MSG} (file: {filename!r})"
                )
            if kind == "zip":
                return self._by_id["docx"].parse(raw, filename)

        if name_lower.endswith(".pdf") and kind == "zip":
            try:
                return self._by_id["docx"].parse(raw, filename)
            except ValueError:
                pass

        for p in self._parsers:
            if p.supports(filename, content_type):
                return p.parse(raw, filename)
        ext = Path(filename).suffix.lower() or "(no extension)"
        raise ValueError(
            f"No parser registered for {filename!r} ({content_type!r}). "
            f"Supported: {', '.join(sorted({x.format_id for x in self._parsers}))}. "
            "Add a new DocumentParser subclass and register it."
        )


def default_registry() -> ParserRegistry:
    from .docx_parser import DocxParser
    from .pdf_parser import PdfParser

    return ParserRegistry([PdfParser(), DocxParser()])
