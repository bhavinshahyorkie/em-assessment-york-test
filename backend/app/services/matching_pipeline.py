"""
Orchestrates parse → embed → rank. Keeps HTTP routes thin and gives one place to extend
(e.g. reranking, structured filters) without growing the app factory.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.api.helpers import display_file_format, excerpt
from app.core.config import settings
from app.models.schemas import MatchResponse, RankedRow
from app.parsers.base import ParsedDocument
from app.services.embeddings import EmbeddingClient
from app.services.ranking import rank_by_embedding

logger = logging.getLogger(__name__)

COLD_START_NOTE = (
    "Cold start: this posting has no prior applicants or internal match history. Rankings use "
    "general-purpose text embeddings (pretrained on broad language), so each score is cosine "
    "similarity between the job description and that resume—no training data is required for this job. "
    "This is an intentional baseline for greenfield roles; optional refinements (structured requirements, "
    "rerankers, feedback from future hires) can improve calibration but are not required to produce a ranked list."
)


def run_matching_pipeline(
    embedder: EmbeddingClient,
    jd_parsed: ParsedDocument,
    parsed_resumes: list[ParsedDocument],
) -> MatchResponse:
    """
    Embed JD + resumes, score by cosine similarity, build `MatchResponse`.
    Preconditions: API key and non-empty resume list validated by the route; parsed text non-empty.
    """
    if not parsed_resumes:
        raise HTTPException(status_code=400, detail="Upload at least one resume file.")

    texts = [jd_parsed.text] + [p.text for p in parsed_resumes]
    try:
        vectors = embedder.embed_texts(texts)
    except Exception as e:
        logger.exception("Embedding call failed")
        raise HTTPException(
            status_code=502,
            detail="Embedding request failed. Verify OPENAI_API_KEY, network access, and model availability. See server logs.",
        ) from e

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
    formats = [display_file_format(p.source_label, p.format_id) for p in parsed_resumes]
    excerpts = [excerpt(p.text) for p in parsed_resumes]

    ranked = rank_by_embedding(
        job_emb,
        cand_embs,
        labels,
        formats,
        excerpts,
        top_k=min(settings.top_k, len(parsed_resumes)),
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
        cold_start_note=COLD_START_NOTE,
    )
