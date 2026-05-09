// See: specs/dashboard/dashboard-page.md
import { useEffect, useState } from 'react'
import { fetchStats, type StatsResponse } from '../api/client'
import StatCard from '../components/StatCard'

const page: React.CSSProperties = { padding: 32, maxWidth: 960, margin: '0 auto' }
const grid: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24, marginBottom: 32 }

export default function DashboardPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    fetchStats()
      .then((s) => { setStats(s); setError(null) })
      .catch(() => setError('Unable to connect to backend'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={page}>
      <h1 style={{ marginBottom: 8 }}>Dashboard</h1>
      {error && (
        <div style={{ background: '#7f1d1d', padding: '10px 16px', borderRadius: 8, marginBottom: 24 }}>
          {error}
        </div>
      )}
      {loading && !stats && <p style={{ color: '#94a3b8' }}>Loading…</p>}
      {stats && (
        <>
          <div style={grid}>
            <StatCard label="Total Cache Entries" value={stats.total_entries.toLocaleString()} icon="📦" />
            <StatCard label="Cache Hit Ratio" value={`${(stats.hit_ratio * 100).toFixed(1)}%`} icon="🎯" />
            <StatCard label="Total Requests" value={stats.total_requests.toLocaleString()} icon="📊" />
          </div>
          <p style={{ color: '#94a3b8', fontSize: 15 }}>
            💡 Estimated tokens saved: <strong style={{ color: '#7c6af7' }}>{stats.tokens_saved.toLocaleString()}</strong>
          </p>
        </>
      )}
    </div>
  )
}
