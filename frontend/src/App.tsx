import React, { useState } from 'react'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Navbar from './components/Navbar'

export default function App() {
  const [page, setPage] = useState<'landing'|'dashboard'>('landing')
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50">
      <Navbar onNavigate={setPage} />
      <main className="p-6">
        {page === 'landing' ? <Landing onEnter={() => setPage('dashboard')} /> : <Dashboard />}
      </main>
    </div>
  )
}
