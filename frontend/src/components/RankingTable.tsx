import React, { useEffect, useState } from 'react'
import { Briefcase, ChevronDown, ChevronUp, FileText, Trophy } from 'lucide-react'
import { getResume, getJob } from '../services/api'

export default function RankingTable({ items, jobId, filename }: { items: any[], jobId?: string, filename?: string }){
  const [expandedResumes, setExpandedResumes] = useState<Record<string, boolean>>({})
  const [resumeFullText, setResumeFullText] = useState<Record<string, string>>({})
  const [jobExpanded, setJobExpanded] = useState(false)
  const [jobFullText, setJobFullText] = useState<string | null>(null)
  const [jobTitle, setJobTitle] = useState<string>(filename || 'Job Description')

  useEffect(() => {
    // fetch job full text to extract title (first line)
    let mounted = true
    const fetch = async () => {
      if (jobId) {
        try {
          const res = await getJob(jobId)
          if (!mounted) return
          const text = res.text || ''
          setJobFullText(text)
          const firstLine = text.split(/\r?\n/).find((l: string) => l.trim().length > 0) || filename || 'Job Description'
          setJobTitle(firstLine)
        } catch (e) {
          if (!mounted) return
          setJobTitle(filename || 'Job Description')
        }
      } else {
        setJobTitle(filename || 'Job Description')
      }
    }
    fetch()
    return () => { mounted = false }
  }, [jobId, filename])

  const toggleResume = async (id: string) => {
    const next = !expandedResumes[id]
    if (next && !resumeFullText[id]) {
      try {
        const res = await getResume(id)
        setResumeFullText((s) => ({ ...s, [id]: res.text || '' }))
      } catch (e) {
        setResumeFullText((s) => ({ ...s, [id]: 'Failed to load full resume.' }))
      }
    }
    setExpandedResumes((s) => ({ ...s, [id]: next }))
  }

  const toggleJob = () => {
    setJobExpanded((v) => !v)
  }

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-[24px] bg-ink text-white shadow-soft transition hover:shadow-lift">
        <div className="flex items-center gap-4 px-5 py-4 sm:px-6">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-lime text-ink"><Briefcase size={19} /></div>
          <div className="min-w-0 flex-1 pr-3">
            <div className="font-display truncate text-xl font-bold">{filename || jobTitle}</div>
          </div>
          <button
            type="button"
            onClick={toggleJob}
            aria-expanded={jobExpanded}
            aria-label={jobExpanded ? `Collapse ${filename || jobTitle}` : `Expand ${filename || jobTitle}`}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/10 text-white/60 transition hover:bg-white/20 hover:text-white"
          >
            {jobExpanded ? <ChevronUp size={17} /> : <ChevronDown size={17} />}
          </button>
        </div>
        {jobExpanded && (
          <div className="border-t border-white/10 bg-white/[0.04] px-5 py-5 sm:px-6">
            <div className="mb-3 flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[0.16em] text-lime"><FileText size={13} /> Full job description</div>
            <div className="document-scroll document-text max-h-[55vh] overflow-y-auto rounded-2xl border border-white/10 bg-black/10 p-4 pr-3 text-xs text-white/70">
              {jobFullText || 'Loading job...'}
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-3">
        {items.map((it: any, idx: number) => {
          const score = Number(it.score_pct) || 0
          const scoreTone = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-coral'
          return (
            <div key={it.id} className="result-card surface-card overflow-hidden rounded-[22px]">
              <div className="flex items-center gap-4 px-5 py-4 sm:px-6">
                <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl font-display text-sm font-bold ${idx === 0 ? 'bg-lime text-ink' : 'bg-ink/[0.06] text-ink/55'}`}>
                  {idx === 0 ? <Trophy size={18} /> : `#${idx + 1}`}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-extrabold text-ink">{it.name}</div>
                </div>

                <div className="w-32 shrink-0 text-right sm:w-44">
                  <div className="flex items-baseline justify-end gap-1">
                    <span className={`text-xl font-black ${scoreTone}`}>{it.score_pct}%</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink/[0.07]">
                    <div className="h-full rounded-full bg-gradient-to-r from-mint to-emerald-500" style={{width: `${it.score_pct}%`}} />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => toggleResume(it.id)}
                  aria-expanded={Boolean(expandedResumes[it.id])}
                  aria-label={expandedResumes[it.id] ? `Collapse ${it.name}` : `Expand ${it.name}`}
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-ink/[0.05] text-ink/35 transition hover:bg-ink/10 hover:text-ink"
                >
                  {expandedResumes[it.id] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
              </div>

              {expandedResumes[it.id] && (
                <div className="border-t border-ink/10 bg-canvas/55 px-5 py-5 sm:px-6">
                  <div className="mb-3 flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[0.16em] text-ink/40"><FileText size={13} className="text-coral" /> Resume content</div>
                  <div className="document-scroll document-text max-h-[55vh] overflow-y-auto rounded-2xl border border-ink/10 bg-white/70 p-4 pr-3 text-xs text-ink/65">
                    {resumeFullText[it.id] || 'Loading full resume...'}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
