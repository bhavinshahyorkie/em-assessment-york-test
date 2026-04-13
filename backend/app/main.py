from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import MatchResponse, RankedRow
from app.parsers import default_registry
from app.parsers.base import ParsedDocument
from app.services.embeddings import EmbeddingClient
from app.services.ranking import rank_by_embedding

logger = logging.getLogger(__name__)

app = FastAPI(title="Talent Intelligence & Ranking Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_registry():
    return default_registry()


def get_embedder():
    return EmbeddingClient()


def _excerpt(text: str, n: int = 500) -> str:
    t = " ".join(text.split())
    return t[:n] if len(t) > n else t


def _as_upload_list(files: list[UploadFile] | UploadFile) -> list[UploadFile]:
    """FastAPI may pass a single UploadFile when one file is sent for a multi-file field."""
    if isinstance(files, UploadFile):
        return [files]
    return files


def _display_file_format(source_label: str, internal_format_id: str) -> str:
    """
    Format shown in the UI: derived from the uploaded filename (pdf / docx / doc).
    Internal parsing may use a different parser for mislabeled files; the column reflects what the user uploaded.
    """
    ext = Path(source_label).suffix.lower()
    if ext in (".docx", ".docm"):
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext == ".doc":
        return "doc"
    return internal_format_id


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/match", response_model=MatchResponse)
async def match_candidates(
    job_description: Annotated[UploadFile, File(description="Job description (PDF or DOCX)")],
    resumes: Annotated[list[UploadFile], File(description="One or more resumes (PDF or DOCX)")],
    registry=Depends(get_registry),
    embedder: EmbeddingClient = Depends(get_embedder),
):
    """
    Ingest → parse → embed (JD + each resume) → cosine similarity → top 10.

    Job description and every resume use the same ParserRegistry (PDF + DOCX); format is chosen per file.
    """
    resumes = _as_upload_list(resumes)

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Configure backend/.env or environment.",
        )

    if not resumes:
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
    for f in resumes:
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

    texts = [jd_parsed.text] + [p.text for p in parsed_resumes]
    try:
        vectors = embedder.embed_texts(texts)
    except Exception as e:
        logger.exception("Embedding call failed")
        raise HTTPException(status_code=502, detail=f"Embedding service error: {e!s}") from e

    if len(vectors) != len(texts):
        raise HTTPException(
            status_code=502,
            detail="Embedding API returned an unexpected number of vectors.",
        )

    job_emb = vectors[0]
    cand_embs = vectors[1:]
    dim = len(job_emb)
    for i, v in enumerate(cand_embs):
        if len(v) != dim:
            raise HTTPException(
                status_code=502,
                detail=f"Embedding dimension mismatch for resume index {i}.",
            )
    labels = [p.source_label for p in parsed_resumes]
    formats = [_display_file_format(p.source_label, p.format_id) for p in parsed_resumes]
    excerpts = [_excerpt(p.text) for p in parsed_resumes]

    ranked = rank_by_embedding(
        job_emb,
        cand_embs,
        labels,
        formats,
        excerpts,
        top_k=min(settings.top_k, len(parsed_resumes)),
    )

    cold_start_note = (
        "Cold start: this posting has no prior applicants or internal match history. Rankings use "
        "general-purpose text embeddings (pretrained on broad language), so each score is cosine "
        "similarity between the job description and that resume—no training data is required for this job. "
        "This is an intentional baseline for greenfield roles; optional refinements (structured requirements, "
        "rerankers, feedback from future hires) can improve calibration but are not required to produce a ranked list."
    )

    rows = [
        RankedRow(
            rank=i + 1,
            candidate_label=r.label,
            score=r.score,
            format_id=r.format_id,
            text_excerpt=r.excerpt,
        )
        for i, r in enumerate(ranked)
    ]

    return MatchResponse(
        job_label=jd_parsed.source_label,
        embedding_model=settings.embedding_model,
        ranked=rows,
        cold_start_note=cold_start_note,
    )
