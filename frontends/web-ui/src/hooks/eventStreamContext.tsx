/* Single SSE connection shared across the app. App.tsx owns one
   useEventStream() and exposes it via EventStreamProvider; consumers
   call useSharedEventStream() to read events / connection / pause toggle. */

import { createContext, useContext, useState, type ReactNode } from 'react'
import { useEventStream, type StreamEvent } from './useEventStream'

interface Ctx {
  events: StreamEvent[]
  isConnected: boolean
  paused: boolean
  togglePause: () => void
}

const EventStreamCtx = createContext<Ctx | null>(null)

export function EventStreamProvider({ children }: { children: ReactNode }) {
  const [paused, setPaused] = useState(false)
  const { events, isConnected, pause, resume } = useEventStream({ paused })

  const togglePause = () => {
    if (paused) {
      setPaused(false)
      resume()
    } else {
      setPaused(true)
      pause()
    }
  }

  return (
    <EventStreamCtx.Provider value={{ events, isConnected, paused, togglePause }}>
      {children}
    </EventStreamCtx.Provider>
  )
}

export function useSharedEventStream(): Ctx {
  const ctx = useContext(EventStreamCtx)
  if (!ctx) throw new Error('useSharedEventStream must be used inside <EventStreamProvider>')
  return ctx
}
