import React from 'react'

export default function LoadingOverlay({ show, label }: { show: boolean, label?: string }){
  if (!show) return null
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30 z-50">
      <div className="p-6 bg-white rounded shadow flex items-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-emerald-200 border-t-emerald-600 animate-spin" />
        <div className="text-sm">{label || 'Processing...'}</div>
      </div>
    </div>
  )
}
