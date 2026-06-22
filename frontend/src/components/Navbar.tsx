import React from 'react'
import { Aperture, CheckCircle2, Sparkles } from 'lucide-react'

export default function Navbar(){
  return (
    <header className="app-navbar">
      <div className="mx-auto flex h-full w-full max-w-[1380px] items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="brand-orbit">
            <Aperture size={20} strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-display text-xl font-bold leading-none tracking-tight text-white">ResumeRank</div>
          </div>
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-[11px] font-bold text-white/70 sm:flex">
          <Sparkles size={14} className="text-lime" />
          Semantic candidate matching
        </div>

        <div className="flex items-center gap-2 text-[11px] font-bold text-white/60">
          <CheckCircle2 size={15} className="text-mint" />
          <span className="hidden sm:inline">Workspace ready</span>
        </div>
      </div>
    </header>
  )
}
