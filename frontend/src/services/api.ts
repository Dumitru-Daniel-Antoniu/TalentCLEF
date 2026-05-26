import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 60_000,
})

export async function uploadResumes(files: File[]) {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  const res = await api.post('/upload-resumes', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data
}

export async function postJobDescription(text: string) {
  const res = await api.post('/job-description', { text })
  return res.data
}

export async function rankCandidates(payload: any) {
  const res = await api.post('/rank', payload)
  return res.data
}

export default api
