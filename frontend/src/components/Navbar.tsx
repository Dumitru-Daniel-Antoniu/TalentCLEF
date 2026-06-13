import React from 'react'

export default function Navbar(){
  return (
    <header className="w-full py-4 px-6 flex items-center justify-between bg-gradient-to-r from-slate-900 to-emerald-600 text-white shadow-lg">
      {/* left placeholder to preserve spacing (icon removed) */}
      <div style={{ width: 48 }} />

      {/* centered title + short description */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl font-semibold">ResumeRank</div>
          <div className="text-sm text-white/80">AI Candidate Ranking</div>
        </div>
      </div>

      {/* right placeholder */}
      <div style={{ width: 48 }} />
    </header>
  )
}
