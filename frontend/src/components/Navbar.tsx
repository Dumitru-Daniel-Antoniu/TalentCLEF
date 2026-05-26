import React from 'react'

export default function Navbar({ onNavigate }: { onNavigate: (p: 'landing'|'dashboard') => void }){
  return (
    <header className="w-full py-4 px-6 flex items-center justify-between glass-card shadow-sm">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-pink-500 rounded-lg flex items-center justify-center text-white font-bold">JR</div>
        <div>
          <div className="text-lg font-semibold">ResumeRank</div>
          <div className="text-xs text-slate-500">AI Candidate Ranking</div>
        </div>
      </div>
      <nav className="flex gap-3">
        <button onClick={() => onNavigate('landing')} className="px-3 py-2 rounded-md hover:bg-slate-100">Home</button>
        <button onClick={() => onNavigate('dashboard')} className="px-3 py-2 rounded-md bg-indigo-600 text-white">Dashboard</button>
      </nav>
    </header>
  )
}
