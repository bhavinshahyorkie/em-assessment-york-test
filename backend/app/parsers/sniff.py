"""Detect PDF / ZIP (OOXML) / OLE magic bytes for parser routing and user-facing errors."""

from __future__ import annotations

from typing import Literal

# OLE2 compound document (legacy Microsoft Word .doc, older Excel, etc.)
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def sniff_binary_kind(data: bytes) -> Literal["empty", "pdf", "zip", "ole_legacy", "unknown"]:
    """
    Inspect raw bytes so we can route or explain errors when the filename lies.

    Real .docx is a ZIP archive (bytes start with PK). Legacy Word .doc is OLE binary, not a zip.
    """
    if not data:
        return "empty"
    if len(data) >= 4 and data[:4] == b"%PDF":
        return "pdf"
    if len(data) >= 2 and data[:2] == b"PK":
        return "zip"
    if len(data) >= len(_OLE_MAGIC) and data[: len(_OLE_MAGIC)] == _OLE_MAGIC:
        return "ole_legacy"
    return "unknown"
