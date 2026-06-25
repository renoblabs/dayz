/**
 * useEventStream — real EventSource subscription for /api/v1/events/stream.
 *
 * Replaces the design prototype's useFakeEventStream. New events PREPEND
 * to the events buffer (capped at 500 to bound memory). React Query cache
 * key ['events','stream'] is updated on every message so any consumer
 * useQuery(['events','stream']) re-renders.
 *
 * On connection error: marks isConnected=false and reconnects after a 2s
 * linear backoff (capped at 10s after repeated failures). On unmount or
 * pause: closes the EventSource cleanly.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const STREAM_PATH = '/api/v1/events/stream'
const BUFFER_CAP = 500

const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export interface StreamEvent {
  id: string
  event_type: string
  server_id: string
  received_at: string
  data?: Record<string, unknown>
  // Local UI marker — true for the very first render after the event
  // arrived so panels can apply slide-in animations one-shot.
  __fresh?: boolean
}

export interface UseEventStreamOpts {
  paused?: boolean
}

export interface UseEventStreamResult {
  events: StreamEvent[]
  isConnected: boolean
  pause: () => void
  resume: () => void
  reconnect: () => void
}

export function useEventStream(opts: UseEventStreamOpts = {}): UseEventStreamResult {
  const queryClient = useQueryClient()
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [paused, setPaused] = useState<boolean>(opts.paused ?? false)

  const esRef = useRef<EventSource | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const backoffRef = useRef(2000)

  const closeConn = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    setIsConnected(false)
  }, [])

  const connect = useCallback(() => {
    if (paused) return
    closeConn()
    const url = apiBase ? `${apiBase}${STREAM_PATH}` : STREAM_PATH
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setIsConnected(true)
      backoffRef.current = 2000
    }

    es.onmessage = (e: MessageEvent) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent
        ev.__fresh = true
        setEvents((prev) => {
          const next = [ev, ...prev].slice(0, BUFFER_CAP)
          // Mirror into React Query cache so any useQuery(['events','stream']) renders.
          queryClient.setQueryData(['events', 'stream'], next)
          return next
        })
        // Drop the __fresh flag after one render tick so the slide-in
        // animation is applied exactly once.
        window.setTimeout(() => {
          setEvents((prev) =>
            prev.map((p) => (p.id === ev.id ? { ...p, __fresh: false } : p)),
          )
        }, 1700)
      } catch (err) {
        // Bad payload — drop silently; next message will succeed.
        // eslint-disable-next-line no-console
        console.error('SSE parse error:', err)
      }
    }

    es.onerror = () => {
      setIsConnected(false)
      es.close()
      esRef.current = null
      // Backoff reconnect — linear up to 10s
      if (!paused) {
        reconnectTimerRef.current = setTimeout(connect, backoffRef.current)
        backoffRef.current = Math.min(backoffRef.current + 2000, 10_000)
      }
    }
  }, [paused, queryClient, closeConn])

  // Initial connect + reconnect-on-pause-toggle
  useEffect(() => {
    if (paused) {
      closeConn()
      return
    }
    connect()
    return closeConn
  }, [paused, connect, closeConn])

  const pause = useCallback(() => setPaused(true), [])
  const resume = useCallback(() => setPaused(false), [])
  const reconnect = useCallback(() => {
    backoffRef.current = 2000
    connect()
  }, [connect])

  return { events, isConnected, pause, resume, reconnect }
}
