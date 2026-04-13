from pydantic import BaseModel, Field


class RankedRow(BaseModel):
    rank: int
    candidate_label: str
    score: float
    format_id: str = Field(
        description="Upload type for display: pdf / docx / doc from filename (not the internal parser id)",
    )
    text_excerpt: str = Field(description="Short excerpt for UI/debug")


class MatchResponse(BaseModel):
    job_label: str
    embedding_model: str
    ranked: list[RankedRow]
    cold_start_note: str
