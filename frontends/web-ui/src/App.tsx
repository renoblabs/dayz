/* ─────────────────────────────────────────────────────────────────
   App — 8-tab DayZ Ops Dashboard. Top rail is sticky on every route.
   Routes: /ops /servers /players /encounters /trophies /alerts /kb
           /settings  (default redirects to /ops)
   ───────────────────────────────────────────────────────────────── */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { TopRail } from './components/TopRail'
import { TweaksPanel } from './components/TweaksPanel'
import { EventStreamProvider, useSharedEventStream } from './hooks/eventStreamContext'
import { useGlobalShortcuts } from './hooks/useGlobalShortcuts'
import OpsPage from './pages/OpsPage'
import ServersPage from './pages/ServersPage'
import PlayersPage from './pages/PlayersPage'
import EncountersPage from './pages/EncountersPage'
import TrophiesPage from './pages/TrophiesPage'
import AlertsPage from './pages/AlertsPage'
import KnowledgePage from './pages/KnowledgePage'
import SettingsPage from './pages/SettingsPage'

function Shell() {
  const { isConnected, paused, togglePause } = useSharedEventStream()
  useGlobalShortcuts()

  return (
    <>
      <TopRail
        isConnected={isConnected}
        paused={paused}
        onTogglePause={togglePause}
      />
      <Routes>
        <Route path="/" element={<Navigate to="/ops" replace />} />
        <Route path="/ops" element={<OpsPage />} />
        <Route path="/servers" element={<ServersPage />} />
        <Route path="/players" element={<PlayersPage />} />
        <Route path="/encounters" element={<EncountersPage />} />
        <Route path="/trophies" element={<TrophiesPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/kb" element={<KnowledgePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/ops" replace />} />
      </Routes>
      <TweaksPanel />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <EventStreamProvider>
        <Shell />
      </EventStreamProvider>
    </BrowserRouter>
  )
}
