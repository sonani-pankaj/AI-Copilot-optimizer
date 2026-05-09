// See: specs/dashboard/metrics-page.md
import { useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { fetchHistory, type StatsHistoryPoint } from '../api/client'

const page: React.CSSProperties = { padding: 32, maxWidth: 1000, margin: '0 auto' }
const card: React.CSSProperties = { background: '#1a1d27', borderRadius: 12, padding: 24, marginBottom: 32 }
const btnGroup: React.CSSProperties = { display: 'flex', gap: 8, marginBottom: 24 }

const RANGES = [7, 14, 30] as const

export default function MetricsPage() {
  const [days, setDays] = useState<7 | 14 | 30>(30)
  const [data, setData] = useState<StatsHistoryPoint[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchHistory(days)
      .then(setData)
      .finally(() => setLoading(false))
  }, [days])

  const isEmpty = data.every((d) => d.requests === 0)

  return (
    <div style={page}>
      <h1 style={{ marginBottom: 16 }}>Metrics</h1>

      <div style={btnGroup}>
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setDays(r)}
            style={{
              background: days === r ? '#7c6af7' : '#2d3148',
              color: '#e2e8f0', border: 'none', padding: '6px 20px',
              borderRadius: 6, cursor: 'pointer', fontWeight: days === r ? 700 : 400,
            }}
          >
            {r}d
          </button>
        ))}
      </div>

      {loading && <p style={{ color: '#94a3b8' }}>Loading…</p>}

      {!loading && isEmpty && (
        <p style={{ color: '#94a3b8' }}>No data for selected period.</p>
      )}

      {!loading && !isEmpty && (
        <>
          <div style={card}>
            <h3 style={{ marginTop: 0 }}>Requests vs Cache Hits</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2d3148', color: '#e2e8f0' }} />
                <Legend wrapperStyle={{ color: '#94a3b8' }} />
                <Line type="monotone" dataKey="requests" stroke="#7c6af7" strokeWidth={2} dot={false} name="Requests" />
                <Line type="monotone" dataKey="cache_hits" stroke="#4ade80" strokeWidth={2} dot={false} name="Cache Hits" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={card}>
            <h3 style={{ marginTop: 0 }}>Tokens Saved per Day</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2d3148', color: '#e2e8f0' }} />
                <Bar dataKey="tokens_saved" fill="#f97316" name="Tokens Saved" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
