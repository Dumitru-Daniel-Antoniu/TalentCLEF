import React, { useEffect, useState } from 'react'
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
    <div className="space-y-4">
      {/* Job description block (collapsed shows only first line as title) */}
      <div onClick={toggleJob} className="p-6 rounded-lg bg-white shadow-sm cursor-pointer">
        <div className="flex items-center justify-between">
          <div className="flex-1 pr-4">
            <div className="font-semibold">{jobTitle}</div>
          </div>
        </div>
        {jobExpanded && (
          <div className="mt-3 whitespace-pre-wrap text-sm text-slate-800 border-t pt-3">{jobFullText || 'Loading job...'}</div>
        )}
      </div>

      {/* Resumes list */}
      <div className="space-y-3">
        {items.map((it: any, idx: number) => (
          <div key={it.id} onClick={() => toggleResume(it.id)} className="p-6 rounded-lg bg-white shadow-sm cursor-pointer">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-teal-400 text-white flex items-center justify-center font-bold">{idx+1}</div>
                <div className="text-center">
                  <div className="font-semibold">{it.name}</div>
                </div>
              </div>

              <div className="flex flex-col items-end">
                <div className="text-sm font-medium">{it.score_pct}%</div>
                <div className="h-3 bg-slate-100 rounded mt-2 overflow-hidden w-40">
                  <div className="h-3 bg-emerald-600 rounded" style={{width: `${it.score_pct}%`}} />
                </div>
              </div>
            </div>

            {expandedResumes[it.id] && (
              <div className="mt-3 whitespace-pre-wrap text-sm text-slate-800 border-t pt-3">{resumeFullText[it.id] || 'Loading full resume...'}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
