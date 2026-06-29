import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'



(function ensureInitialScrollLock(){
  try {
    var STYLE_ID = 'initial-scroll-style'
    var CSS = 'html, body, #root { overflow: hidden !important; height: 100%; margin: 0; } html::-webkit-scrollbar, body::-webkit-scrollbar, #root::-webkit-scrollbar { width: 0 !important; height: 0 !important; display: none !important; }'
    if (!document.getElementById(STYLE_ID)){
      var s = document.createElement('style')
      s.id = STYLE_ID
      s.textContent = CSS
      try { document.head.appendChild(s) } catch(e) {}
    }

    if (!document.getElementById('initial-scroll-overlay')){
      var ov = document.createElement('div')
      ov.id = 'initial-scroll-overlay'
      ov.style.position = 'fixed'
      ov.style.top = '0'
      ov.style.left = '0'
      ov.style.right = '0'
      ov.style.bottom = '0'
      ov.style.zIndex = '2147483647'
      ov.style.background = 'transparent'

      ov.style.pointerEvents = 'none'
      var wheelHandler = function(e:any){ try{ e.preventDefault() }catch(err){} }
      var touchHandler = function(e:any){ try{ e.preventDefault() }catch(err){} }
      var keyHandler = function(e:any){ try{ var keys=['ArrowUp','ArrowDown','PageUp','PageDown','Home','End',' ']; if (keys.indexOf(e.key)!==-1) e.preventDefault() }catch(err){} }

      try { (window as any).__initialWheelHandler = wheelHandler } catch(e) {}
      try { (window as any).__initialTouchHandler = touchHandler } catch(e) {}
      try { (window as any).__initialKeyHandler = keyHandler } catch(e) {}
      try {

        window.addEventListener('wheel', wheelHandler, { passive: false, capture: true })
        window.addEventListener('touchmove', touchHandler, { passive: false, capture: true })
        window.addEventListener('keydown', keyHandler, { passive: false, capture: true })
        document.body.appendChild(ov)
      } catch(e) {}
    }


    const _prevRelease = (window as any).__releaseInitialScrollLock
    ;(window as any).__releaseInitialScrollLock = function(){
      try {
        if (typeof _prevRelease === 'function') {
          try { _prevRelease() } catch(e) {}
        }
      } catch(e) {}
      try { var s = document.getElementById(STYLE_ID); if (s && s.parentNode) s.parentNode.removeChild(s) } catch(e) {}
      try { var ov = document.getElementById('initial-scroll-overlay'); if (ov && ov.parentNode) ov.parentNode.removeChild(ov) } catch(e) {}
      try { window.removeEventListener('wheel', (window as any).__initialWheelHandler, { capture: true }) } catch(e) {}
      try { window.removeEventListener('touchmove', (window as any).__initialTouchHandler, { capture: true }) } catch(e) {}
      try { window.removeEventListener('keydown', (window as any).__initialKeyHandler, { capture: true }) } catch(e) {}
      try { delete (window as any).__initialWheelHandler } catch(e) {}
      try { delete (window as any).__initialTouchHandler } catch(e) {}
      try { delete (window as any).__initialKeyHandler } catch(e) {}
      try { delete (window as any).__releaseInitialScrollLock } catch(e) {}
    }
  } catch(e) {}
})()

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
