import React, { useCallback, useState } from 'react'
import { uploadResumes } from '../services/api'

export default function UploadZone({ onUploaded }: { onUploaded: (items: any[]) => void }){
  const [drag, setDrag] = useState(false)

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return
    const res = await uploadResumes(files)
    onUploaded(res)
  }, [onUploaded])

  const onFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    if (files.length === 0) return
    const res = await uploadResumes(files)
    onUploaded(res)
    e.currentTarget.value = ''
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={`p-6 rounded-lg border-dashed border-2 ${drag ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 bg-white'} shadow-sm`}
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">Upload Resumes</div>
          <div className="text-sm text-slate-500">Drag & drop PDF / DOCX / TXT files here</div>
        </div>
        <div>
          <label className="inline-block px-4 py-2 bg-indigo-600 text-white rounded cursor-pointer">
            <input type="file" multiple onChange={onFiles} className="hidden" />
            Select Files
          </label>
        </div>
      </div>
    </div>
  )
}
