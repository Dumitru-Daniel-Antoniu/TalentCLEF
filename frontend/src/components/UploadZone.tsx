import React, { useCallback, useState } from 'react'
import { Files, UploadCloud } from 'lucide-react'
import { resetUploads, uploadResumes } from '../services/api'

export default function UploadZone({ onUploaded, jobId, onUploadStarted }: { onUploaded: (items: any[]) => void, jobId?: string | null, onUploadStarted?: () => void }){
  const [drag, setDrag] = useState(false)

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return
    onUploadStarted?.()
    try {
      console.log('UploadZone.onDrop files', files)
      await resetUploads('resumes')
      const res = await uploadResumes(files, jobId || undefined)
      console.log('UploadZone.upload result', res)
      onUploaded(res)
    } catch (err:any) {
      console.error('UploadZone upload failed', err)
      alert('Resume upload failed: ' + (err?.message || String(err)))
    }
  }, [onUploaded, jobId])

  const onFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    if (files.length === 0) return
    onUploadStarted?.()
    try {
      console.log('UploadZone.onFiles files', files)
      await resetUploads('resumes')
      const res = await uploadResumes(files, jobId || undefined)
      console.log('UploadZone.upload result', res)
      onUploaded(res)
    } catch (err:any) {
      console.error('UploadZone upload failed', err)
      alert('Resume upload failed: ' + (err?.message || String(err)))
    } finally {
      e.currentTarget.value = ''
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={`upload-surface ${drag ? 'is-dragging' : ''}`}
    >
      <div className="relative flex h-full w-full items-center gap-4 px-5 py-4 sm:px-6">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-coral/15 text-coral shadow-sm">
          {drag ? <UploadCloud size={21} /> : <Files size={21} />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="eyebrow text-coral">Step 02</span>
            <span className="h-px w-6 bg-ink/15" />
            <Files size={12} className="text-ink/35" />
          </div>
          <div className="font-display truncate text-xl font-bold text-ink">Build the candidate pool</div>
          <div className="mt-1 truncate text-xs font-medium text-ink/45">Drop one or more PDF, DOCX, or TXT resumes here</div>
        </div>
        <div className="shrink-0">
          <label className="inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-full bg-ink text-xs font-extrabold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-ink/90 hover:shadow-md sm:h-auto sm:w-auto sm:min-w-[120px] sm:px-5 sm:py-2.5">
            <input type="file" multiple accept=".pdf,.docx,.txt" onChange={onFiles} className="hidden" />
            <UploadCloud size={15} className="sm:mr-2" /> <span className="hidden sm:inline">Select files</span>
          </label>
        </div>
      </div>
    </div>
  )
}
