// See: specs/dashboard/cache-viewer-page.md
import { useEffect, useRef, useState } from 'react'
import { fetchCache, type CacheEntry } from '../api/client'

const page: React.CSSProperties = { padding: 32, maxWidth: 1100, margin: '0 auto' }
const table: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: 13 }
const th: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', background: '#1a1d27', color: '#94a3b8', borderBottom: '1px solid #2d3148' }
const td: React.CSSProperties = { padding: '8px 12px', borderBottom: '1px solid #1e2235', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
const input: React.CSSProperties = { background: '#1a1d27', border: '1px solid #2d3148', color: '#e2e8f0', padding: '6px 12px', borderRadius: 6, width: 180 }

export default function CacheViewerPage() {
  const [entries, setEntries] = useState<CacheEntry[]>([])
  const [page_, setPage] = useState(1)
  const [userId, setUserId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [selected, setSelected] = useState<CacheEntry | null>(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = (p = page_, uid = userId, tid = teamId) => {
    setLoading(true)
    fetchCache(p, 20, uid || undefined, tid || undefined)
      .then(setEntries)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [page_])

  const handleFilter = (uid: string, tid: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => { setPage(1); load(1, uid, tid) }, 300)
  }

  return (
    <div style={page}>
      <h1 style={{ marginBottom: 16 }}>Cache Viewer</h1>
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <input style={input} placeholder="Filter by user_id" value={userId}
          onChange={(e) => { setUserId(e.target.value); handleFilter(e.target.value, teamId) }} />
        <input style={input} placeholder="Filter by team_id" value={teamId}
          onChange={(e) => { setTeamId(e.target.value); handleFilter(userId, e.target.value) }} />
      </div>

      {loading && <p style={{ color: '#94a3b8' }}>Loading…</p>}
      {!loading && entries.length === 0 && <p style={{ color: '#94a3b8' }}>No cache entries found.</p>}

      {entries.length > 0 && (
        <table style={table}>
          <thead>
            <tr>
              {['Query', 'Response', 'User', 'Team', 'Tokens Saved', 'Cached At'].map((h) => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(e)}>
                <td style={td}>{e.query.slice(0, 60)}{e.query.length > 60 ? '…' : ''}</td>
                <td style={td}>{e.response.slice(0, 60)}{e.response.length > 60 ? '…' : ''}</td>
                <td style={td}>{e.user_id}</td>
                <td style={td}>{e.team_id ?? '—'}</td>
                <td style={{ ...td, color: '#7c6af7' }}>{e.tokens_saved}</td>
                <td style={td}>{new Date(e.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Pagination */}
      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button style={{ background: '#2d3148', color: '#e2e8f0', border: 'none', padding: '6px 16px', borderRadius: 6, cursor: 'pointer' }}
          disabled={page_ === 1} onClick={() => setPage((p) => p - 1)}>← Prev</button>
        <span style={{ color: '#94a3b8', alignSelf: 'center' }}>Page {page_}</span>
        <button style={{ background: '#2d3148', color: '#e2e8f0', border: 'none', padding: '6px 16px', borderRadius: 6, cursor: 'pointer' }}
          disabled={entries.length < 20} onClick={() => setPage((p) => p + 1)}>Next →</button>
      </div>

      {/* Modal */}
      {selected && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
          onClick={() => setSelected(null)}>
          <div style={{ background: '#1a1d27', borderRadius: 12, padding: 32, maxWidth: 700, width: '90%', maxHeight: '80vh', overflowY: 'auto' }}
            onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Query</h3>
            <pre style={{ whiteSpace: 'pre-wrap', color: '#94a3b8', fontSize: 13 }}>{selected.query}</pre>
            <h3>Response</h3>
            <pre style={{ whiteSpace: 'pre-wrap', color: '#a5f3a5', fontSize: 13 }}>{selected.response}</pre>
            <button style={{ marginTop: 16, background: '#7c6af7', color: '#fff', border: 'none', padding: '8px 20px', borderRadius: 6, cursor: 'pointer' }}
              onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
