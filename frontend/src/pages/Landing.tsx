import React from 'react'

export default function Landing({ onEnter }: { onEnter: () => void }){
  return (
    <section className="max-w-5xl mx-auto py-12">
      <div className="grid grid-cols-2 gap-8 items-center">
        <div>
          <h1 className="text-4xl font-bold">ResumeRank — AI Candidate Matching</h1>
          <p className="mt-4 text-slate-600">Upload resumes, paste a job description, and rank candidates by semantic relevance. Built with modern embeddings and a sleek UI.</p>
          <div className="mt-6">
            <button onClick={onEnter} className="px-6 py-3 bg-indigo-600 text-white rounded shadow">Try the Dashboard</button>
          </div>
        </div>
        <div>
          <div className="p-6 rounded-lg glass-card shadow">
            <div className="text-sm text-slate-500">Example</div>
            <div className="mt-3 text-sm">
              Upload resumes or use the sample files included in the repository. The system computes embeddings and ranks candidates with cosine similarity.
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
