/**
 * Root UI: uploads and match results. No secrets; API keys exist only on the backend.
 * Add new screens or feature folders under `src/features/` as the app grows.
 */
import { useMemo, useState } from 'react'
import { ACCEPT_DOCUMENTS } from '../lib/constants'
import { getMatchEndpointUrl, parseApiError } from '../lib/matchApi'
import { redactLikelySecrets } from '../lib/redactClientMessage'
import type { MatchResponse } from '../types/match'
import './App.css'

export default function App() {
  const [jobFile, setJobFile] = useState<File | null>(null)
  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MatchResponse | null>(null)

  const resumeSummary = useMemo(() => {
    const n = resumeFiles.length
    if (n === 0) return null
    if (n === 1) return resumeFiles[0].name
    return `${n} files: ${resumeFiles.map((f) => f.name).join(', ')}`
  }, [resumeFiles])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    if (!jobFile) {
      setError('Choose a job description (PDF or DOCX).')
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
      const res = await fetch(getMatchEndpointUrl(), { method: 'POST', body: fd })
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
      const msg = err instanceof Error ? err.message : 'Request failed'
      setError(redactLikelySecrets(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <p className="eyebrow">Proof of concept</p>
        <h1>Talent match ranking</h1>
        <p className="hero-lede">
          Upload one <strong>job description</strong> and several <strong>resumes</strong> (each file may be{' '}
          <strong>PDF</strong> or <strong>Word</strong>). Text is extracted, compared with embeddings, and the closest
          semantic matches are listed first.
        </p>
      </header>

      <section className="panel" aria-labelledby="upload-heading">
        <h2 id="upload-heading" className="panel-title">
          Upload files
        </h2>
        <form className="form" onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="file-field">
              <label htmlFor="job-file" className="file-field-label">
                Job description
              </label>
              <p className="file-field-hint" id="job-hint">
                PDF or DOCX
              </p>
              <input
                id="job-file"
                className="file-input"
                type="file"
                accept={ACCEPT_DOCUMENTS}
                aria-describedby="job-hint"
                onChange={(e) => setJobFile(e.target.files?.[0] ?? null)}
              />
              {jobFile && (
                <p className="file-chosen" aria-live="polite">
                  Selected: {jobFile.name}
                </p>
              )}
            </div>
            <div className="file-field">
              <label htmlFor="resume-files" className="file-field-label">
                Resumes
              </label>
              <p className="file-field-hint" id="resume-hint">
                PDF or DOCX each — use Ctrl/Cmd to select multiple
              </p>
              <input
                id="resume-files"
                className="file-input"
                type="file"
                multiple
                accept={ACCEPT_DOCUMENTS}
                aria-describedby="resume-hint"
                onChange={(e) => setResumeFiles(e.target.files ? Array.from(e.target.files) : [])}
              />
              {resumeSummary && (
                <p className="file-chosen" aria-live="polite">
                  Selected: {resumeSummary}
                </p>
              )}
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Working…' : 'Find top matches'}
          </button>
        </form>
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {result && (
        <section className="panel panel-results" aria-labelledby="results-heading">
          <h2 id="results-heading" className="panel-title">
            Results
          </h2>
          <p className="results-meta">
            Job file: <strong>{result.job_label}</strong>
            <span className="dot" aria-hidden />
            Model: <code className="inline-code">{result.embedding_model}</code>
          </p>
          <aside className="callout">{result.cold_start_note}</aside>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Candidate</th>
                  <th scope="col">Score</th>
                  <th scope="col">Format</th>
                  <th scope="col">Excerpt</th>
                </tr>
              </thead>
              <tbody>
                {result.ranked.map((r) => (
                  <tr key={`${r.rank}-${r.candidate_label}`} className={r.rank <= 3 ? 'row-highlight' : undefined}>
                    <td className="cell-rank">{r.rank}</td>
                    <td className="cell-name" title={r.candidate_label}>
                      {r.candidate_label}
                    </td>
                    <td className="cell-score">{Number(r.score).toFixed(4)}</td>
                    <td>
                      <span className="format-badge">{r.format_id}</span>
                    </td>
                    <td className="cell-excerpt">{r.text_excerpt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
