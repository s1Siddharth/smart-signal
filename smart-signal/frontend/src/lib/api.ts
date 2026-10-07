// lib/api.ts — REST API client with auth token injection
import { auth } from './firebase'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function getToken(): Promise<string | null> {
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    await auth.signOut()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getState: () => apiFetch<object>('/api/state'),
  getHistory: (limit = 50) => apiFetch<object[]>(`/api/history?limit=${limit}`),
  getStats: () => apiFetch<object>('/api/stats'),
  updateConfig: (cfg: object) =>
    apiFetch('/api/config', { method: 'POST', body: JSON.stringify(cfg) }),
  simulateAmbulance: (road: string) =>
    apiFetch(`/api/demo/ambulance/${road}`, { method: 'POST' }),
  switchSource: (source: string) =>
    apiFetch('/api/source', { method: 'POST', body: JSON.stringify({ source }) }),
  uploadVideo: async (file: File) => {
    const token = await getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    
    const formData = new FormData()
    formData.append('file', file)
    
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      headers,
      body: formData
    })
    if (!res.ok) throw new Error(`API error ${res.status}`)
    return res.json()
  },
}
