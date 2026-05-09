import { useState } from 'react'
import { login } from '../api/client'

const wrap: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }
const card: React.CSSProperties = { background: '#1a1d27', borderRadius: 12, padding: 40, width: 360 }
const field: React.CSSProperties = { width: '100%', background: '#0f1117', border: '1px solid #2d3148', color: '#e2e8f0', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 15 }
const btn: React.CSSProperties = { width: '100%', background: '#7c6af7', color: '#fff', border: 'none', padding: '12px', borderRadius: 8, fontWeight: 700, fontSize: 15, cursor: 'pointer' }

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const token = await login(username, password)
      localStorage.setItem('jwt', token)
      window.location.href = '/'
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={wrap}>
      <div style={card}>
        <h2 style={{ textAlign: 'center', marginTop: 0, color: '#7c6af7' }}>⚡ AI Copilot Optimizer</h2>
        <form onSubmit={handleSubmit}>
          <input style={field} placeholder="Username" value={username}
            onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          <input style={field} type="password" placeholder="Password" value={password}
            onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          {error && <p style={{ color: '#f87171', marginBottom: 12 }}>{error}</p>}
          <button style={btn} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
