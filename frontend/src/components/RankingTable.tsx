import React from 'react'

export default function RankingTable({ items }: { items: any[] }){
  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={it.id} className="p-3 rounded-lg bg-white shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-pink-400 text-white flex items-center justify-center font-bold">{idx+1}</div>
            <div>
              <div className="font-semibold">{it.name}</div>
              <div className="text-xs text-slate-500">{it.summary}</div>
            </div>
          </div>
          <div style={{width: 260}}>
            <div className="text-right text-sm font-medium">{it.score_pct}%</div>
            <div className="h-3 bg-slate-100 rounded mt-2 overflow-hidden">
              <div className="h-3 bg-indigo-500 rounded" style={{width: `${it.score_pct}%`}} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
