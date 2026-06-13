import React, { useCallback, useState } from 'react'
import { uploadJobDescriptionFile } from '../services/api'

export default function JobUploadZone({ onUploaded }: { onUploaded: (job: any) => void }){
  const [drag, setDrag] = useState(false)

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return
    try {
      console.log('JobUploadZone.onDrop files', files)
      const res = await uploadJobDescriptionFile(files[0])
      console.log('JobUploadZone.upload result', res)
      onUploaded(res)
    } catch (err:any) {
      console.error('JobUploadZone upload failed', err)
      alert('Job upload failed: ' + (err?.message || String(err)))
    }
  }, [onUploaded])

  const onFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputEl = e.currentTarget as HTMLInputElement
    const file = inputEl.files ? inputEl.files[0] : null
    if (!file) return
    // clear the input immediately to avoid issues with React pooled events
    inputEl.value = ''
    try {
      console.log('JobUploadZone.onFiles file', file)
      const res = await uploadJobDescriptionFile(file)
      console.log('JobUploadZone.upload result', res)
      onUploaded(res)
    } catch (err:any) {
      console.error('JobUploadZone upload failed', err)
      alert('Job upload failed: ' + (err?.message || String(err)))
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
          <div className="text-lg font-semibold">Upload Job Description</div>
          <div className="text-sm text-slate-500">Drag & drop PDF / DOCX / TXT files here</div>
        </div>
        <div className="absolute right-6">
          <label className="inline-block px-5 py-2 bg-emerald-600 text-white rounded cursor-pointer min-w-[120px] text-center">
            <input type="file" accept=".pdf,.docx,.txt" onChange={onFiles} className="hidden" />
            Select Files
          </label>
        </div>
      </div>
    </div>
  )
}
