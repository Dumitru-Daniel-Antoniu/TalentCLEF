import React, { useCallback, useState } from 'react'
import { uploadResumes } from '../services/api'

export default function UploadZone({ onUploaded, jobId }: { onUploaded: (items: any[]) => void, jobId?: string | null }){
  const [drag, setDrag] = useState(false)

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return
    try {
      console.log('UploadZone.onDrop files', files)
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
    try {
      console.log('UploadZone.onFiles files', files)
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
      className={`p-6 rounded-lg border-dashed border-2 ${drag ? 'border-emerald-400 bg-emerald-50' : 'border-slate-200 bg-white'} shadow-sm h-full flex items-center`}
    >
      <div className="flex items-center w-full relative">
        <div>
          <div className="text-lg font-semibold">Upload Resumes</div>
          <div className="text-sm text-slate-500">Drag & drop PDF / DOCX / TXT files here{jobId ? ' — attached to job' : ''}</div>
        </div>
        <div className="absolute right-6">
          <label className="inline-block px-5 py-2 bg-emerald-600 text-white rounded cursor-pointer min-w-[120px] text-center">
            <input type="file" multiple accept=".pdf,.docx,.txt" onChange={onFiles} className="hidden" />
            Select Files
          </label>
        </div>
      </div>
    </div>
  )
}
