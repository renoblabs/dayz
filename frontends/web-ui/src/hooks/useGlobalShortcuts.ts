/**
 * useGlobalShortcuts — registers Vim-style "g <letter>" navigation
 * across the 8 dashboard tabs, plus '/' to focus search.
 *
 * Behavior:
 *   g e -> /ops          g s -> /servers       g p -> /players
 *   g n -> /encounters   g t -> /trophies      g a -> /alerts
 *   g k -> /kb           g , -> /settings
 *   /   -> dispatch a 'dashboard:focus-search' CustomEvent
 *
 * The "first key seen" buffer times out after 1.2s. Key listeners are
 * suppressed when the active element is an <input>/<textarea>/contenteditable.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const ROUTES: Record<string, string> = {
  e: '/ops',
  s: '/servers',
  p: '/players',
  n: '/encounters',
  t: '/trophies',
  a: '/alerts',
  k: '/kb',
  ',': '/settings',
}

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  const tag = el.tagName.toUpperCase()
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (el.isContentEditable) return true
  return false
}

export function useGlobalShortcuts(): void {
  const navigate = useNavigate()

  useEffect(() => {
    let firstKey: string | null = null
    let firstKeyTimer: ReturnType<typeof setTimeout> | null = null

    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return
      // Don't capture modifier-combos
      if (e.metaKey || e.ctrlKey || e.altKey) return

      const k = e.key

      if (k === '/') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('dashboard:focus-search'))
        return
      }

      if (firstKey === 'g') {
        const route = ROUTES[k]
        if (route) {
          e.preventDefault()
          navigate(route)
        }
        firstKey = null
        if (firstKeyTimer) {
          clearTimeout(firstKeyTimer)
          firstKeyTimer = null
        }
        return
      }

      if (k === 'g') {
        firstKey = 'g'
        if (firstKeyTimer) clearTimeout(firstKeyTimer)
        firstKeyTimer = setTimeout(() => {
          firstKey = null
        }, 1200)
      }
    }

    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      if (firstKeyTimer) clearTimeout(firstKeyTimer)
    }
  }, [navigate])
}
