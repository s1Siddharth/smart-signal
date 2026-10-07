// pages/Profile.tsx — User profile page showing account info and usage stats
import { useEffect, useState } from 'react'
import { useAuth } from '@/auth/AuthContext'
import { api } from '@/lib/api'

export default function Profile() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadProfileData = async () => {
      if (!user) return

      try {
        setLoading(true)
        // Fetch user-specific stats (if we had user-specific endpoints)
        // For now, we'll show general stats as placeholder
        const statsData = await api.getStats()
        setStats(statsData)

        // Fetch recent history (limited)
        const historyData = await api.getHistory(20)
        setHistory(historyData)
      } catch (err) {
        setError('Failed to load profile data')
        console.error('Profile data error:', err)
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      loadProfileData()
    }
  }, [user])

  if (loading) return <div className="p-6 text-text-muted">Loading profile...</div>
  if (error) return <div className="p-6 text-text-red">{error}</div>
  if (!user) return <div className="p-6 text-text-muted">Please log in to view your profile</div>

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">User Profile</h1>
        <p className="text-text-secondary">Manage your Smart Signal account and view your usage statistics.</p>
      </div>

      {/* User Info Card */}
      <div className="bg-panel p-6 rounded border border-border mb-6">
        <h2 className="text-xl font-bold mb-4 text-text-primary">Account Information</h2>
        <div className="grid gap-4">
          <div className="text-sm">
            <p className="mb-2"><strong className="text-text-primary">Email:</strong> <span className="text-text-secondary">${user.email ?? 'N/A'}</span></p>
            <p className="mb-2"><strong className="text-text-primary">User ID:</strong> <span className="text-text-secondary">${user.uid}</span></p>
            <p className="mb-2"><strong className="text-text-primary">Email Verified:</strong> <span className="text-text-secondary">${user.emailVerified ? 'Yes' : 'No'}</span></p>
            <p className="mb-2"><strong className="text-text-primary">Account Created:</strong> <span className="text-text-secondary">${user.metadata.creationTime ? new Date(user.metadata.creationTime).toLocaleDateString() : 'N/A'}</span></p>
            <p className="mb-2"><strong className="text-text-primary">Last Sign-in:</strong> <span className="text-text-secondary">${user.metadata.lastSignInTime ? new Date(user.metadata.lastSignInTime).toLocaleDateString() : 'N/A'}</span></p>
          </div>

          {/* Avatar placeholder */}
          <div className="flex items-center justify-center">
            <div className="w-24 h-24 rounded-full bg-panel border border-border flex items-center justify-center">
              <span className="text-accent font-bold text-2xl">${user?.email?.[0] ?? 'U'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Card */}
      {stats && (
        <div className="bg-panel p-6 rounded border border-border mb-6">
          <h2 className="text-xl font-bold mb-4 text-text-primary">Usage Statistics</h2>
          <div className="grid gap-4">
            <div className="text-center">
              <h3 className="text-2xl font-mono text-signal-green">${Math.round(stats.saved_green_s || 0)}s</h3>
              <p className="text-text-secondary">Total Time Saved</p>
            </div>
            <div className="text-center">
              <h3 className="text-2xl font-mono text-signal-red">${Math.round(stats.fixed_wasted_green_s || 0)}s</h3>
              <p className="text-text-secondary">Fixed-time Wasted</p>
            </div>
            <div className="text-center">
              <h3 className="text-2xl font-mono text-signal-green">${Math.round(stats.adaptive_wasted_green_s || 0)}s</h3>
              <p className="text-text-secondary">Adaptive Wasted</p>
            </div>
            <div className="text-center">
              <h3 className="text-2xl font-mono text-signal-amber">${Math.round(((stats.fixed_wasted_green_s || 0) - (stats.adaptive_wasted_green_s || 0)) / Math.max(1, (stats.fixed_wasted_green_s || 1)) * 100)}%</h3>
              <p className="text-text-secondary">Improvement</p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {history.length > 0 && (
        <div className="bg-panel p-6 rounded border border-border">
          <h2 className="text-xl font-bold mb-4 text-text-primary">Recent Activity</h2>
          <div className="space-y-4">
            {history.map((entry: any, index: number) => (
              <div key={index} className="p-4 bg-border rounded border border-border">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-mono text-text-secondary">${new Date(entry.ts * 1000).toLocaleTimeString()}</span>
                  <span className="text-xs text-text-muted">Activity</span>
                </div>
                <div className="text-sm">
                  <p className="mb-1"><strong>Saved:</strong> ${Math.round(entry.saved_green_s || 0)}s</p>
                  <p className="mb-1"><strong>Fixed Wasted:</strong> ${Math.round(entry.fixed_wasted_green_s || 0)}s</p>
                  <p className="mb-1"><strong>Adaptive Wasted:</strong> ${Math.round(entry.adaptive_wasted_green_s || 0)}s</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Logout Button */}
      <div className="mt-8">
        <button
          onClick={logout}
          className="w-full py-3 px-6 bg-border text-text-primary hover:bg-signal-red hover:text-white transition-colors font-bold rounded"
        >
          Log Out
        </button>
      </div>
    </div>
  )
}