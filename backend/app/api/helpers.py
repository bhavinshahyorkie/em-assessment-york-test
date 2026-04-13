"""Small HTTP/multipart helpers used by route handlers."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile


def excerpt(text: str, n: int = 500) -> str:
    """Shorten parsed text for API excerpts."""
    t = " ".join(text.split())
    return t[:n] if len(t) > n else t


def as_upload_list(files: list[UploadFile] | UploadFile) -> list[UploadFile]:
    """Normalize FastAPI's handling of one vs many files for the same field name."""
    if isinstance(files, UploadFile):
        return [files]
    return files


def display_file_format(source_label: str, internal_format_id: str) -> str:
    """
    UI column value from the uploaded filename (pdf / docx / doc).
    May differ from the internal parser id when a file is mislabeled.
    """
    ext = Path(source_label).suffix.lower()
    if ext in (".docx", ".docm"):
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext == ".doc":
        return "doc"
    return internal_format_id
