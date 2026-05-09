import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import DashboardPage from './pages/Dashboard'
import CacheViewerPage from './pages/CacheViewer'
import MetricsPage from './pages/Metrics'
import LoginPage from './pages/Login'

const nav: React.CSSProperties = {
  display: 'flex', gap: 24, padding: '12px 24px',
  background: '#1a1d27', borderBottom: '1px solid #2d3148',
}
const linkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  color: isActive ? '#7c6af7' : '#94a3b8', textDecoration: 'none', fontWeight: 600,
})

function RequireAuth({ children }: { children: JSX.Element }) {
  return localStorage.getItem('jwt') ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <>
                <nav style={nav}>
                  <span style={{ color: '#7c6af7', fontWeight: 700, marginRight: 16 }}>⚡ AI Copilot Optimizer</span>
                  <NavLink to="/" end style={linkStyle}>Dashboard</NavLink>
                  <NavLink to="/cache" style={linkStyle}>Cache Viewer</NavLink>
                  <NavLink to="/metrics" style={linkStyle}>Metrics</NavLink>
                  <span
                    style={{ marginLeft: 'auto', cursor: 'pointer', color: '#94a3b8' }}
                    onClick={() => { localStorage.removeItem('jwt'); window.location.href = '/login' }}
                  >
                    Logout
                  </span>
                </nav>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/cache" element={<CacheViewerPage />} />
                  <Route path="/metrics" element={<MetricsPage />} />
                </Routes>
              </>
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
