from __future__ import annotations

import fitz  # PyMuPDF

from .base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
    format_id = "pdf"

    def supports(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".pdf") or (content_type or "").lower() in (
            "application/pdf",
            "application/x-pdf",
        )

    def parse(self, raw: bytes, source_label: str) -> ParsedDocument:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Invalid or unreadable PDF ({source_label}): {e}") from e
        try:
            parts: list[str] = []
            for page in doc:
                parts.append(page.get_text("text"))
            text = "\n".join(parts)
        finally:
            doc.close()
        return ParsedDocument(text=text.strip(), source_label=source_label, format_id=self.format_id)
