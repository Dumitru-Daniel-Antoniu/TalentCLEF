import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 60_000,
})

export async function uploadResumes(files: File[], jobId?: string) {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  if (jobId) fd.append('job_id', jobId)
  const res = await api.post('/upload-resumes', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data
}

export async function resetUploads(uploadType: 'jobs' | 'resumes') {
  try {
    const res = await api.delete(`/uploads/${uploadType}`)
    return res.data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      console.warn(`Upload reset endpoint is unavailable for ${uploadType}; continuing with client-side replacement.`)
      return { cleared: false, upload_type: uploadType }
    }
    throw error
  }
}

export async function postJobDescription(text: string) {
  const res = await api.post('/job-description', { text })
  return res.data
}

export async function uploadJobDescriptionFile(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await api.post('/job-description-file', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data
}

export async function getJob(jobId: string) {
  const res = await api.get(`/job/${jobId}`)
  return res.data
}

export async function getResume(resumeId: string) {
  const res = await api.get(`/resume/${resumeId}`)
  return res.data
}

export async function rankCandidates(payload: any) {
  const res = await api.post('/rank', payload)
  return res.data
}

export default api
