from __future__ import annotations

import math
from dataclasses import dataclass


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    v = dot / (na * nb)
    if math.isnan(v):
        return 0.0
    return float(v)


@dataclass
class RankedCandidate:
    label: str
    score: float
    format_id: str
    excerpt: str


def rank_by_embedding(
    job_embedding: list[float],
    candidate_embeddings: list[list[float]],
    labels: list[str],
    format_ids: list[str],
    excerpts: list[str],
    top_k: int,
) -> list[RankedCandidate]:
    scored: list[tuple[float, int]] = []
    for i, emb in enumerate(candidate_embeddings):
        s = cosine_similarity(job_embedding, emb)
        scored.append((s, i))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[RankedCandidate] = []
    for s, i in scored[:top_k]:
        out.append(
            RankedCandidate(
                label=labels[i],
                score=round(s, 6),
                format_id=format_ids[i],
                excerpt=excerpts[i][:400],
            )
        )
    return out
