import React, { useState } from 'react'
import UploadZone from '../components/UploadZone'
import JobUploadZone from '../components/JobUploadZone'
import LoadingOverlay from '../components/LoadingOverlay'
import RankingTable from '../components/RankingTable'
import { postJobDescription, rankCandidates, getJob } from '../services/api'

export default function Dashboard(){
  const [uploads, setUploads] = useState<any[]>([])
  const [jobUploads, setJobUploads] = useState<any[]>([])
  const [jobText, setJobText] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobFile, setJobFile] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [jobRankings, setJobRankings] = useState<any[]>([])
  

  const handleUploaded = (items: any[]) => {
    setUploads((s) => [...s, ...items])
  }

  const handleRank = async () => {
    if (!jobText && !jobId && jobUploads.length === 0) return alert('Please paste or upload a job description')
    if (uploads.length === 0) return alert('Please upload at least one resume')
    setLoading(true)
    try {
      const ids = uploads.map((u)=>u.id)
      const rankingsPerJob: any[] = []

      if (jobUploads && jobUploads.length > 0) {
        // rank for each uploaded job description
        for (const j of jobUploads) {
          const resp = await rankCandidates({ job_id: j.job_id, resume_ids: ids, top_k: 100 })
          rankingsPerJob.push({ job_id: j.job_id, filename: j.filename || 'Job', rankings: resp.rankings || [] })
        }
      } else {
        // single job: either existing jobId or raw text
        let job
        if (jobId) {
          job = { job_id: jobId }
        } else {
          job = await postJobDescription(jobText)
        }
        const resp = await rankCandidates({ job_id: job.job_id, resume_ids: ids, top_k: 100 })
        rankingsPerJob.push({ job_id: job.job_id, filename: job.fileName || 'Job', rankings: resp.rankings || [] })
      }

      setJobRankings(rankingsPerJob)
      const totalCount = rankingsPerJob.reduce((s, r) => s + (r.rankings?.length || 0), 0)
      window.dispatchEvent(new CustomEvent('app:rankings-available', { detail: { count: totalCount } }))
    } catch (e:any) {
      console.error(e)
      alert('Ranking failed: ' + (e?.message || String(e)))
    } finally {
      setLoading(false)
    }
  }

  const handleJobUploaded = async (job: any) => {
    // server returns job_id and snippet
    setJobId(job.job_id)
    // track uploaded job descriptions (keep history)
    setJobUploads((s) => [...s, job])
    // fetch full stored job text so we can render the complete content
    try {
      const full = await getJob(job.job_id)
      if (full && full.text) {
        setJobText(full.text)
      }
    } catch (e) {
      // fallback to snippet if full fetch fails
      if (job.snippet) setJobText(job.snippet)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-3 gap-6">
        {/* Top-left: JobUploadZone (fixed height) */}
        <div className="col-span-2">
          <div className="mb-2 h-28">
            <JobUploadZone onUploaded={handleJobUploaded} />
          </div>
        </div>

        {/* Top-right: Uploaded Files (smaller than job upload) */}
        <aside className="col-span-1">
          <div className="p-4 glass-card rounded shadow h-28 flex items-center">
            <div className="w-full grid grid-cols-2 gap-4">
              <div className="flex flex-col items-center justify-center">
                <div className="text-sm font-medium text-slate-600 mb-1">Job Descriptions</div>
                <div className="text-3xl font-extrabold text-emerald-600">{jobUploads.length}</div>
              </div>

              <div className="flex flex-col items-center justify-center">
                <div className="text-sm font-medium text-slate-600 mb-1">Resumes</div>
                <div className="text-3xl font-extrabold text-emerald-600">{uploads.length}</div>
              </div>
            </div>
          </div>
        </aside>

        {/* Bottom-left: UploadZone */}
        <div className="col-span-2">
          <div className="h-28">
            <UploadZone onUploaded={handleUploaded} jobId={jobId} />
          </div>
        </div>

        {/* Bottom-right: Rank button, centered to align with the counter box */}
        <div className="col-span-1 flex items-center justify-center">
          <button
            onClick={handleRank}
            disabled={((!(jobText && jobText.trim()) && !jobId) || uploads.length === 0)}
            className="px-6 py-3 bg-emerald-600 text-white rounded disabled:opacity-50"
          >
            Rank Candidates
          </button>
        </div>
      </div>

      <section className="flex justify-center">
        <div className="w-full max-w-4xl">
          <div className="text-xl font-semibold mb-3 text-center">Ranking Results</div>
          {jobRankings.length === 0 ? (
            <div className="text-slate-500 text-center">No rankings yet — upload resumes and click "Rank Candidates".</div>
          ) : (
            <div className="space-y-6">
              {jobRankings.map((jr) => (
                <RankingTable key={jr.job_id} items={jr.rankings} jobId={jr.job_id} filename={jr.filename} />
              ))}
            </div>
          )}
        </div>
      </section>

      <LoadingOverlay show={loading} label="Computing similarities…" />
    </div>
  )
}
