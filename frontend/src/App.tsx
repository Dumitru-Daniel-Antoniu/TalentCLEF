import React, { useRef, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Navbar from './components/Navbar'

export default function App() {
  const shellRef = useRef<HTMLDivElement | null>(null)
  const allowScrollRef = useRef(false)

  useEffect(() => {
    const el = shellRef.current
    if (!el) return

    let touchStartY = 0

    const onWheel = (e: WheelEvent) => {
      const deltaY = e.deltaY
      const atTop = el.scrollTop <= 0
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1
      if ((atTop && deltaY < 0) || (atBottom && deltaY > 0)) {
        e.preventDefault()
      }
    }

    const onTouchStart = (ev: TouchEvent) => {
      touchStartY = ev.touches[0]?.clientY || 0
    }

    const onTouchMove = (ev: TouchEvent) => {
      const currentY = ev.touches[0]?.clientY || 0
      const dy = touchStartY - currentY
      const atTop = el.scrollTop <= 0
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1
      if ((atTop && dy < 0) || (atBottom && dy > 0)) {
        ev.preventDefault()
      }
    }

    el.addEventListener('wheel', onWheel as EventListener, { passive: false })
    el.addEventListener('touchstart', onTouchStart as EventListener, { passive: false })
    el.addEventListener('touchmove', onTouchMove as EventListener, { passive: false })

    // Manage overflow: hide scrollbar when content fits, enable when content needs it
    const updateOverflow = () => {
      if (!el) return
      // Use a buffer to avoid showing the scrollbar for tiny rounding differences
      const BUFFER = 12
      const needsScroll = el.scrollHeight > el.clientHeight + BUFFER
      const rootEl = document.getElementById('root') as HTMLElement | null

      // Only enable the internal scrollbar when the app explicitly allows scrolling
      if (needsScroll && allowScrollRef.current) {
        el.style.overflowY = 'auto'
        el.classList.add('show-scrollbar')
        // release initial page-level lock if present
        if ((window as any).__releaseInitialScrollLock) {
          try { (window as any).__releaseInitialScrollLock() } catch (e) {}
        } else {
          try { (window as any).__initialScrollLockActive = false } catch (e) {}
          try {
            const s = document.getElementById('initial-scroll-style')
            if (s && s.parentNode) s.parentNode.removeChild(s)
          } catch (e) {}
        }
        if (rootEl) {
          rootEl.style.marginRight = ''
          rootEl.style.width = ''
        }
      } else {
        el.style.overflowY = 'hidden'
        el.classList.remove('show-scrollbar')
        if (rootEl) {
          rootEl.style.marginRight = ''
          rootEl.style.width = ''
        }
      }
    }

    // Initial checks at multiple ticks to account for font/layout shifts
    requestAnimationFrame(updateOverflow)
    const t1 = window.setTimeout(updateOverflow, 50)
    const t2 = window.setTimeout(updateOverflow, 250)
    const t3 = window.setTimeout(updateOverflow, 800)
    const t4 = window.setTimeout(updateOverflow, 1600)
    const t5 = window.setTimeout(updateOverflow, 3000)

    // No automatic removal of the initial style here — it will be removed only when
    // `updateOverflow` detects content actually needs scrolling.

    // Observe size/content changes
    let ro: ResizeObserver | null = null
    if ((window as any).ResizeObserver) {
      ro = new (window as any).ResizeObserver(() => requestAnimationFrame(updateOverflow))
      ro.observe(el)
    }

    const mo = new MutationObserver(() => requestAnimationFrame(updateOverflow))
    mo.observe(el, { childList: true, subtree: true, characterData: true })
    window.addEventListener('resize', updateOverflow)

    // Listen for explicit app event signalling rankings exist — only then release initial lock and allow scrollbar
    const onRankingsAvailable = (ev: Event) => {
      // Allow internal scrolling from now on
      allowScrollRef.current = true
      try {
        if ((window as any).__releaseInitialScrollLock) {
          (window as any).__releaseInitialScrollLock()
        } else {
          try { (window as any).__initialScrollLockActive = false } catch (e) {}
          try {
            const s = document.getElementById('initial-scroll-style')
            if (s && s.parentNode) s.parentNode.removeChild(s)
          } catch (e) {}
        }
      } catch (e) {}
      requestAnimationFrame(updateOverflow)
    }
    window.addEventListener('app:rankings-available', onRankingsAvailable as EventListener)

    return () => {
      el.removeEventListener('wheel', onWheel as EventListener)
      el.removeEventListener('touchstart', onTouchStart as EventListener)
      el.removeEventListener('touchmove', onTouchMove as EventListener)
      if (ro) ro.disconnect()
      mo.disconnect()
      window.removeEventListener('resize', updateOverflow)
      window.removeEventListener('app:rankings-available', onRankingsAvailable as EventListener)
      window.clearTimeout(t1)
      window.clearTimeout(t2)
      window.clearTimeout(t3)
      window.clearTimeout(t4)
      window.clearTimeout(t5)
      const rootEl = document.getElementById('root') as HTMLElement | null
      if (rootEl) {
        rootEl.style.marginRight = ''
        rootEl.style.width = ''
      }
    }
  }, [])

  return (
    <div ref={shellRef} className="h-screen app-shell" style={{ overflowY: 'hidden' }}>
      <Navbar onNavigate={() => {}} />
      <main className="p-6 page-pattern">
        <Dashboard />
      </main>
    </div>
  )
}
