import { useState } from 'react'
import './App.css'

/** Empty = use Vite dev proxy `/api` → `http://127.0.0.1:8000`. If set, must be API root only, e.g. `http://127.0.0.1:8000` (no `/api` suffix). */
const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

function matchUrl(): string {
  if (API_BASE) {
    return `${API_BASE}/match`
  }
  return '/api/match'
}

type RankedRow = {
  rank: number
  candidate_label: string
  score: number
  format_id: string
  text_excerpt: string
}

type MatchResponse = {
  job_label: string
  embedding_model: string
  ranked: RankedRow[]
  cold_start_note: string
}

function parseApiError(res: Response, raw: string, data: unknown): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const d = (data as { detail: unknown }).detail
    if (typeof d === 'string') {
      return d
    }
    if (Array.isArray(d)) {
      return JSON.stringify(d)
    }
  }
  const lower = raw.toLowerCase()
  if (
    lower.includes('econnrefused') ||
    lower.includes('connect refused') ||
    lower.includes('socket hang up') ||
    lower.includes('econnreset')
  ) {
    return (
      'The UI could not reach the API on port 8000. Open a second terminal, run from the repo: ' +
      'cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
    )
  }
  if (
    res.status === 500 &&
    (!raw.trim() || lower.includes('<!doctype') || lower.includes('<html') || lower.includes('internal server error'))
  ) {
    return (
      'Request failed (500). If the API is not running, start it on port 8000 (see README). ' +
      'If it is running, check the terminal where uvicorn is running for the traceback.'
    )
  }
  if (raw.trim()) {
    return raw.length > 500 ? `${raw.slice(0, 500)}…` : raw
  }
  return `${res.status} ${res.statusText}`
}

export default function App() {
  const [jobFile, setJobFile] = useState<File | null>(null)
  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MatchResponse | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    if (!jobFile) {
      setError('Choose a job description file (PDF or DOCX).')
      return
    }
    if (resumeFiles.length === 0) {
      setError('Add at least one resume (PDF or DOCX).')
      return
    }

    const fd = new FormData()
    fd.append('job_description', jobFile)
    for (const f of resumeFiles) {
      fd.append('resumes', f)
    }

    setLoading(true)
    try {
      const res = await fetch(matchUrl(), {
        method: 'POST',
        body: fd,
      })
      const raw = await res.text()
      let data: unknown = {}
      try {
        data = raw ? JSON.parse(raw) : {}
      } catch {
        throw new Error(parseApiError(res, raw, {}))
      }
      if (!res.ok) {
        throw new Error(parseApiError(res, raw, data))
      }
      setResult(data as MatchResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }



  return (
    <div className="layout">
      <header className="header">
        <h1>Talent Intelligence &amp; Ranking</h1>
        <p className="lede">
          The <strong>job description</strong> and <strong>each resume</strong> may be <strong>PDF</strong> or{' '}
          <strong>Word (.docx / .docm)</strong> — the same parsers run on every file. Text is extracted (including
          tables in Word), embedded with OpenAI, and ranked by semantic match.
        </p>
      </header>

      <form className="card" onSubmit={onSubmit}>
        <label className="field">
          <span>Job description — PDF or DOCX</span>
          <input
            type="file"
            accept=".pdf,.docx,.docm,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-word.document.macroEnabled.12"
            onChange={(e) => setJobFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="field">
          <span>Resumes — PDF or DOCX each (multi-select)</span>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.docm,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-word.document.macroEnabled.12"
            onChange={(e) => setResumeFiles(e.target.files ? Array.from(e.target.files) : [])}
          />
        </label>
        <button type="submit" className="primary" disabled={loading}>
          {loading ? 'Ranking…' : 'Find top matches'}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {result && (
        <section className="results">
          <h2>Top matches</h2>
          <p className="meta">
            Job file: <strong>{result.job_label}</strong> · Model:{' '}
            <code>{result.embedding_model}</code>
          </p>
          <p className="cold">{result.cold_start_note}</p>
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Candidate</th>
                <th>Score</th>
                <th>Format (upload)</th>
                <th>Excerpt</th>
              </tr>
            </thead>
            <tbody>
              {result.ranked.map((r) => (
                <tr key={r.rank + r.candidate_label}>
                  <td>{r.rank}</td>
                  <td className="nowrap">{r.candidate_label}</td>
                  <td>{r.score}</td>
                  <td>{r.format_id}</td>
                  <td className="excerpt">{r.text_excerpt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
