/* OPS — flagship operator view.
   Hero strip > 3-row grid:
     Row 1: ServerStatusPanel (full width)
     Row 2: EventFeed (1fr) + Sidebar (360px) [Top Hunters + Recent Encounters]
     Row 3: HealthStrip (sticky bottom)
*/
import { HeroStrip } from '../components/ops/HeroStrip'
import { ServerStatusPanel } from '../components/ops/ServerStatusPanel'
import { EventFeed } from '../components/ops/EventFeed'
import { SidebarTopHunters } from '../components/ops/SidebarTopHunters'
import { SidebarRecentEncounters } from '../components/ops/SidebarRecentEncounters'
import { HealthStrip } from '../components/ops/HealthStrip'
import { useServers } from '../hooks/useDashboardData'

export default function OpsPage() {
  const { data: servers, isLoading } = useServers()

  return (
    <main style={{ display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 48px)' }}>
      <HeroStrip />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 16, flex: 1 }}>
        {/* Row 1 — server status panels */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {isLoading && <ServerStatusPanel isLoading={true} />}
          {!isLoading && (!servers || servers.length === 0) && <ServerStatusPanel />}
          {servers?.map(s => (
            <ServerStatusPanel key={s.server_id} server={s} />
          ))}
        </div>

        {/* Row 2 — event feed (flex) + sidebar 360 */}
        <div className="stack-on-mobile" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 360px', gap: 16, alignItems: 'start' }}>
          <EventFeed />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SidebarTopHunters />
            <SidebarRecentEncounters />
          </div>
        </div>
      </div>

      {/* Row 3 — bottom health strip */}
      <HealthStrip />
    </main>
  )
}
