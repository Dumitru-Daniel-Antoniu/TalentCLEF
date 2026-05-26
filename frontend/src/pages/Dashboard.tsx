import React, { useState } from 'react'
import UploadZone from '../components/UploadZone'
import LoadingOverlay from '../components/LoadingOverlay'
import RankingTable from '../components/RankingTable'
import { postJobDescription, rankCandidates } from '../services/api'

export default function Dashboard(){
  const [uploads, setUploads] = useState<any[]>([])
  const [jobText, setJobText] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any[]>([])

  const handleUploaded = (items: any[]) => {
    setUploads((s) => [...s, ...items])
  }

  const handleRank = async () => {
    if (!jobText) return alert('Please paste a job description')
    if (uploads.length === 0) return alert('Please upload at least one resume')
    setLoading(true)
    try {
      const job = await postJobDescription(jobText)
      const ids = uploads.map((u)=>u.id)
      const resp = await rankCandidates({ job_id: job.job_id, resume_ids: ids, top_k: 20 })
      setResults(resp.rankings || [])
    } catch (e:any) {
      console.error(e)
      alert('Ranking failed: ' + (e?.message || String(e)))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <UploadZone onUploaded={handleUploaded} />
          <div className="mt-4 p-4 bg-white rounded shadow">
            <div className="text-sm text-slate-500">Job description</div>
            <textarea value={jobText} onChange={(e)=>setJobText(e.target.value)} placeholder="Paste job description here" rows={6} className="mt-2 w-full p-3 border rounded" />
            <div className="mt-3 text-right">
              <button onClick={handleRank} className="px-4 py-2 bg-indigo-600 text-white rounded">Rank Candidates</button>
            </div>
          </div>
        </div>

        <aside className="col-span-1 space-y-3">
          <div className="p-4 glass-card rounded shadow">
            <div className="text-sm font-semibold">Uploaded</div>
            <div className="mt-3 text-sm text-slate-600">{uploads.length} files</div>
            <ul className="mt-3 text-sm space-y-1">
              {uploads.map(u => <li key={u.id} className="text-slate-700">{u.filename}</li>)}
            </ul>
          </div>
          <div className="p-4 bg-white rounded shadow">
            <div className="text-sm font-semibold">Tips</div>
            <div className="mt-2 text-xs text-slate-500">Use PDFs or DOCX for richer parsing; resume parsing is heuristic.</div>
          </div>
        </aside>
      </div>

      <section>
        <div className="text-xl font-semibold mb-3">Ranking Results</div>
        {results.length === 0 ? (
          <div className="text-slate-500">No rankings yet — upload resumes and click "Rank Candidates".</div>
        ) : (
          <RankingTable items={results} />
        )}
      </section>

      <LoadingOverlay show={loading} label="Computing similarities…" />
    </div>
  )
}
