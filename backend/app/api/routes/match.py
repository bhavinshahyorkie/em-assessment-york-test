"""
Candidate matching endpoint: multipart upload → parse → `run_matching_pipeline`.

Add new endpoints (e.g. async job status, batch) as separate modules beside this file.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_embedder, get_registry
from app.api.helpers import as_upload_list
from app.core.config import settings
from app.models.schemas import MatchResponse
from app.parsers.base import ParsedDocument
from app.services.embeddings import EmbeddingClient
from app.services.matching_pipeline import run_matching_pipeline

router = APIRouter(tags=["matching"])


@router.post("/match", response_model=MatchResponse)
async def match_candidates(
    job_description: Annotated[UploadFile, File(description="Job description (PDF or DOCX)")],
    resumes: Annotated[list[UploadFile], File(description="One or more resumes (PDF or DOCX)")],
    registry=Depends(get_registry),
    embedder: EmbeddingClient = Depends(get_embedder),
) -> MatchResponse:
    """
    Ingest → parse → embed (JD + each resume) → cosine similarity → top K.

    Job description and every resume use the same `ParserRegistry` (PDF + DOCX).
    """
    resumes_list = as_upload_list(resumes)

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Configure backend/.env or environment.",
        )
    if not resumes_list:
        raise HTTPException(status_code=400, detail="Upload at least one resume file.")

    jd_raw = await job_description.read()
    jd_name = job_description.filename or "job_description"
    try:
        jd_parsed: ParsedDocument = registry.parse(jd_raw, jd_name, job_description.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not jd_parsed.text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty after parsing.")

    parsed_resumes: list[ParsedDocument] = []
    for f in resumes_list:
        raw = await f.read()
        name = f.filename or "resume"
        try:
            parsed_resumes.append(registry.parse(raw, name, f.content_type))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{name}: {e}") from e

    for p in parsed_resumes:
        if not p.text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Resume {p.source_label!r} has no extractable text.",
            )

    return run_matching_pipeline(embedder, jd_parsed, parsed_resumes)
