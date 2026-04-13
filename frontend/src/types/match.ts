/** Types aligned with FastAPI `MatchResponse` / `RankedRow` from `POST /match`. */

export type RankedRow = {
  rank: number
  candidate_label: string
  score: number
  format_id: string
  text_excerpt: string
}

export type MatchResponse = {
  job_label: string
  embedding_model: string
  ranked: RankedRow[]
  cold_start_note: string
}
