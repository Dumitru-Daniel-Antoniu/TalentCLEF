import React from 'react'

export default function ResumeCard({ item }: { item: any }){
  return (
    <div className="p-4 rounded-lg glass-card shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-md font-semibold">{item.name}</div>
          <div className="text-sm text-slate-500">{item.summary}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold">{item.score_pct}%</div>
          <div className="text-xs text-slate-500">similarity</div>
        </div>
      </div>
      <div className="mt-3">
        <div className="text-xs text-slate-600">Top skills:</div>
        <div className="flex gap-2 mt-2 flex-wrap">
          {(item.skills || []).slice(0,6).map((s:string,i:number)=> (
            <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs">{s}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
