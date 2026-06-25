import { useEffect, useState } from 'react';
import { apiClient, hiveClient } from '../api/client';
import type { ServerStatus, Event, StreamedEvent, HiveOverview, HiveEvent } from '../types';

export function useServers(pollMs = 5000) {
  const [data, setData] = useState<ServerStatus[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const result = await apiClient.getServers();
        if (mounted) { setData(result); setError(null); }
      } catch (err) {
        if (mounted) setError(err as Error);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchData();
    const id = setInterval(fetchData, pollMs);
    return () => { mounted = false; clearInterval(id); };
  }, [pollMs]);

  return { data, loading, error };
}

export function useEvents(params?: { limit?: number; event_type?: string; server_id?: string }, pollMs = 3000) {
  const [data, setData] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Stable key so dependency array works cleanly.
  const key = JSON.stringify(params ?? {});

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const result = await apiClient.getEvents(params);
        if (mounted) { setData(result); setError(null); }
      } catch (err) {
        if (mounted) setError(err as Error);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchData();
    const id = setInterval(fetchData, pollMs);
    return () => { mounted = false; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, pollMs]);

  return { data, loading, error };
}

// HiveAPI hooks (separate product)

export function useHiveOverview(pollMs = 5000) {
  const [data, setData] = useState<HiveOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const result = await hiveClient.getOverview();
        if (mounted) { setData(result); setError(null); }
      } catch (err) {
        if (mounted) setError(err as Error);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchData();
    const id = setInterval(fetchData, pollMs);
    return () => { mounted = false; clearInterval(id); };
  }, [pollMs]);

  return { data, loading, error };
}

export function useHiveEvents(limit = 50, pollMs = 5000) {
  const [data, setData] = useState<HiveEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const result = await hiveClient.getEvents({ limit });
        if (mounted) { setData(result); setError(null); }
      } catch (err) {
        if (mounted) setError(err as Error);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchData();
    const id = setInterval(fetchData, pollMs);
    return () => { mounted = false; clearInterval(id); };
  }, [limit, pollMs]);

  return { data, loading, error };
}

export function useEventStream(serverId?: string) {
  const [events, setEvents] = useState<StreamedEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = apiClient.createEventStream(
      (evt) => {
        setEvents((prev) => [evt, ...prev].slice(0, 200));
      },
      () => setConnected(false),
      () => setConnected(true),
      serverId,
    );
    return () => {
      es.close();
      setConnected(false);
    };
  }, [serverId]);

  return { events, connected };
}
