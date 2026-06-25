/* KNOWLEDGE — KB browser. Sidebar + Browse / Search / Read tab content. */

import { useState } from 'react'
import { KnowledgeSidebar } from '../components/kb/KnowledgeSidebar'
import { KnowledgeBrowse } from '../components/kb/KnowledgeBrowse'
import { KnowledgeSearch } from '../components/kb/KnowledgeSearch'
import { KnowledgeRead } from '../components/kb/KnowledgeRead'

export default function KnowledgePage() {
  const [mode, setMode] = useState<'browse' | 'search' | 'read'>('browse')
  const [type, setType] = useState('all')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const handleSelect = (id: string) => {
    setSelectedId(id)
    setMode('read')
  }

  return (
    <main style={{ display: 'flex', height: 'calc(100vh - 48px - 30px)' }}>
      <KnowledgeSidebar
        activeType={type}
        onChange={(t) => {
          setType(t)
          setPage(1)
          if (mode === 'read') setMode('browse')
        }}
        mode={mode}
        onModeChange={setMode}
      />
      <section style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {mode === 'browse' && (
          <KnowledgeBrowse type={type} page={page} onPage={setPage} onSelect={handleSelect} />
        )}
        {mode === 'search' && <KnowledgeSearch onSelectSource={handleSelect} />}
        {mode === 'read' && <KnowledgeRead sourceId={selectedId} />}
      </section>
    </main>
  )
}
