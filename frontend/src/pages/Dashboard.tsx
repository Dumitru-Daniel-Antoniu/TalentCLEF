import React, { useState } from 'react'
import { ArrowRight, BarChart3, Briefcase, CheckCircle2, Users } from 'lucide-react'
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
    setUploads(items)
    setJobRankings([])
  }

  const handleResumeUploadStarted = () => {
    setUploads([])
    setJobRankings([])
  }

  const handleJobUploadStarted = () => {
    setJobUploads([])
    setJobId(null)
    setJobText('')
    setJobRankings([])
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

  const handleJobUploaded = async (jobs: any[]) => {
    const job = jobs[jobs.length - 1]
    if (!job) return
    // server returns job_id and snippet
    setJobId(job.job_id)
    // replace the previous job batch with the latest selection
    setJobUploads(jobs)
    setJobRankings([])
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
    <div className="mx-auto max-w-[1380px] space-y-5">
      <section className="relative overflow-hidden rounded-[26px] bg-ink px-6 py-4 text-white shadow-lift sm:px-8 sm:py-5">
        <div className="absolute -right-12 -top-20 h-52 w-52 rounded-full border border-lime/20" />
        <div className="absolute -right-4 -top-10 h-36 w-36 rounded-full border border-mint/20" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <h1 className="font-display text-[30px] font-bold leading-tight tracking-tight sm:text-4xl">Find the fit behind the resume.</h1>
            <p className="mt-2 hidden max-w-2xl text-sm leading-6 text-white/55 sm:block">Bring roles and people together in one clear, explainable ranking workspace.</p>
          </div>
          <div className="hidden shrink-0 items-center gap-3 text-right lg:flex">
            <div>
              <div className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-white/35">Matching engine</div>
              <div className="mt-1 text-sm font-bold text-mint">Ready for analysis</div>
            </div>
            <div className="grid h-11 w-11 place-items-center rounded-full border border-white/10 bg-white/[0.06]"><BarChart3 size={19} className="text-lime" /></div>
          </div>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-4">
          <div className="h-32">
            <JobUploadZone onUploaded={handleJobUploaded} onUploadStarted={handleJobUploadStarted} />
          </div>
          <div className="h-32">
            <UploadZone onUploaded={handleUploaded} jobId={jobId} onUploadStarted={handleResumeUploadStarted} />
          </div>
        </div>

        <aside className="surface-card flex h-[272px] flex-col overflow-hidden rounded-[24px]">
          <div className="shrink-0 border-b border-ink/10 bg-white/45 px-5 py-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="eyebrow text-coral">Step 03</div>
                <div className="font-display mt-1 text-xl font-bold text-ink">Run the comparison</div>
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-lime"><BarChart3 size={18} /></div>
            </div>
          </div>

          <div className="grid shrink-0 grid-cols-2 gap-px bg-ink/10">
            <div className="bg-white/80 px-4 py-2 text-center">
              <Briefcase size={15} className="mx-auto text-coral" />
              <div className="font-display mt-1 text-2xl font-bold text-ink">{jobUploads.length}</div>
              <div className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-ink/40">Job offers</div>
            </div>
            <div className="bg-white/80 px-4 py-2 text-center">
              <Users size={15} className="mx-auto text-emerald-600" />
              <div className="font-display mt-1 text-2xl font-bold text-ink">{uploads.length}</div>
              <div className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-ink/40">Candidates</div>
            </div>
          </div>

          <div className="flex flex-1 flex-col justify-end p-3">
            <div className="mb-2 hidden grid-cols-2 gap-2 text-[9px] font-bold sm:grid">
              <div className={`flex items-center gap-2 ${jobUploads.length || jobId || jobText.trim() ? 'text-ink' : 'text-ink/35'}`}><CheckCircle2 size={14} className="text-mint" /> Job descriptions ready</div>
              <div className={`flex items-center gap-2 ${uploads.length ? 'text-ink' : 'text-ink/35'}`}><CheckCircle2 size={14} className="text-mint" /> Candidate pool ready</div>
            </div>
            <button
              onClick={handleRank}
              disabled={((!(jobText && jobText.trim()) && !jobId) || uploads.length === 0)}
              className="group flex w-full items-center justify-between rounded-2xl bg-lime px-4 py-2.5 text-left text-sm font-extrabold text-ink shadow-sm transition enabled:hover:-translate-y-0.5 enabled:hover:shadow-md disabled:cursor-not-allowed disabled:bg-ink/[0.07] disabled:text-ink/30"
            >
              <span>Rank candidates</span>
              <span className="grid h-8 w-8 place-items-center rounded-full bg-ink text-white transition group-enabled:group-hover:translate-x-0.5"><ArrowRight size={16} /></span>
            </button>
          </div>
        </aside>
      </div>

      <section>
        <div className="mb-3 px-1">
          <h2 className="font-display text-2xl font-bold text-ink">Ranking results</h2>
        </div>

        <div className="w-full">
          {jobRankings.length === 0 ? (
            <div className="surface-card flex min-h-24 items-center justify-center rounded-[22px] px-5 text-center">
              <div className="mr-3 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-ink/[0.05] text-ink/35"><BarChart3 size={18} /></div>
              <div className="text-left"><div className="text-sm font-bold text-ink">Your ranking will appear here</div><div className="mt-1 text-xs text-ink/45">Upload resumes and select candidates to begin.</div></div>
            </div>
          ) : (
            <div className="space-y-6">
              {jobRankings.map((jr) => (
                <RankingTable key={jr.job_id} items={jr.rankings} jobId={jr.job_id} filename={jr.filename} />
              ))}
            </div>
          )}
        </div>
      </section>

      <LoadingOverlay show={loading} label="Computing similarities..." />
    </div>
  )
}
