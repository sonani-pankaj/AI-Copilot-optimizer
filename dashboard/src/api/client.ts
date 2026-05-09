// See: specs/OVERVIEW.md — Axios client with JWT interceptor
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to /login on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('jwt')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client

// ── API helpers ──────────────────────────────────────────────────────────────

export interface StatsResponse {
  total_entries: number
  total_requests: number
  cache_hits: number
  cache_misses: number
  hit_ratio: number
  tokens_saved: number
}

export interface StatsHistoryPoint {
  date: string
  requests: number
  cache_hits: number
  tokens_saved: number
}

export interface CacheEntry {
  id: string
  user_id: string
  team_id: string | null
  query: string
  response: string
  tokens_saved: number
  model_used: string
  created_at: string
}

export const fetchStats = (): Promise<StatsResponse> =>
  client.get<StatsResponse>('/stats').then((r) => r.data)

export const fetchHistory = (days = 30): Promise<StatsHistoryPoint[]> =>
  client.get<StatsHistoryPoint[]>(`/stats/history?days=${days}`).then((r) => r.data)

export const fetchCache = (page = 1, limit = 20, userId?: string, teamId?: string): Promise<CacheEntry[]> => {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) })
  if (userId) params.set('user_id', userId)
  if (teamId) params.set('team_id', teamId)
  return client.get<CacheEntry[]>(`/upsert?${params}`).then((r) => r.data)
}

export const login = (username: string, password: string): Promise<string> =>
  client
    .post<{ access_token: string }>('/auth/login', { username, password })
    .then((r) => r.data.access_token)
