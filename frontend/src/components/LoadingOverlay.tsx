import React from 'react'
import { Sparkles } from 'lucide-react'

export default function LoadingOverlay({ show, label }: { show: boolean, label?: string }){
  if (!show) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/75 px-5 backdrop-blur-md">
      <div className="surface-card w-full max-w-sm rounded-[28px] p-7 text-center shadow-lift">
        <div className="relative mx-auto mb-5 h-16 w-16">
          <div className="scan-pulse absolute inset-0 rounded-full border border-mint" />
          <div className="absolute inset-2 grid place-items-center rounded-full bg-ink text-lime"><Sparkles size={23} /></div>
        </div>
        <div className="font-display text-xl font-bold text-ink">{label || 'Processing...'}</div>
        <div className="mt-2 text-xs leading-5 text-ink/45">Reading experience, skills, and role context to surface the strongest fit.</div>
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-ink/[0.06]"><div className="h-full w-2/3 animate-pulse rounded-full bg-mint" /></div>
      </div>
    </div>
  )
}
