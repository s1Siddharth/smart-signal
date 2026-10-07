// pages/Analytics.tsx — Fixed-vs-Adaptive comparison charts with trends
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface HistoryEntry {
  ts: number
  fixed_wasted_green_s: number
  adaptive_wasted_green_s: number
  saved_green_s: number
  fixed_wait_vehicle_s: number
  adaptive_wait_vehicle_s: number
}

interface Stats {
  saved_green_s: number
  fixed_wasted_green_s: number
  adaptive_wasted_green_s: number
  fixed_wait_vehicle_s: number
  adaptive_wait_vehicle_s: number
}

export default function Analytics() {
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsData = await api.getStats()
        setStats(statsData as Stats)

        const historyData = await api.getHistory(100)
        const processedHistory: HistoryEntry[] = historyData.map((entry: any) => ({
          ts: entry.ts,
          fixed_wasted_green_s: entry.fixed_wasted_s || 0,
          adaptive_wasted_green_s: entry.adaptive_wasted_s || 0,
          saved_green_s: entry.saved_green_s || 0,
          fixed_wait_vehicle_s: entry.fixed_wait_vehicle_s || 0,
          adaptive_wait_vehicle_s: entry.adaptive_wait_vehicle_s || 0,
        }))
        setHistory(processedHistory)
      } catch (error) {
        console.error('Failed to fetch analytics data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="p-6 text-text-muted">Loading analytics...</div>

  const formatTime = (ts: number) => {
    const date = new Date(ts * 1000)
    return date.toTimeString().slice(0, 5) // HH:MM
  }

  // Transform current stats for the non-technical Bar Chart comparison
  const comparisonData = [
    {
      category: 'Wasted Green Time',
      'Old System': Math.round(stats?.fixed_wasted_green_s || 0),
      'Our System': Math.round(stats?.adaptive_wasted_green_s || 0),
    },
    {
      category: 'Vehicle Wait Time',
      'Old System': Math.round(stats?.fixed_wait_vehicle_s || 0),
      'Our System': Math.round(stats?.adaptive_wait_vehicle_s || 0),
    }
  ]

  // Calculate percentage improvement for the hero metric
  const oldTotal = Math.round(stats?.fixed_wasted_green_s || 0)
  const newTotal = Math.round(stats?.adaptive_wasted_green_s || 0)
  let improvement = 0
  if (oldTotal > 0) {
    improvement = Math.round(((oldTotal - newTotal) / oldTotal) * 100)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Performance & Analytics</h1>
        <p className="text-text-secondary text-sm">
          A clear comparison between a traditional fixed-timer traffic light and our AI-powered adaptive system.
        </p>
      </div>

      {/* Hero Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-panel p-5 rounded-lg border border-border shadow-lg flex flex-col justify-center">
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Overall Efficiency Gain</h2>
          <div className="text-4xl font-mono text-signal-green font-bold">
            {improvement > 0 ? `+${improvement}%` : '0%'}
          </div>
          <div className="text-xs text-text-muted mt-2">Less time wasted overall</div>
        </div>
        
        <div className="bg-panel p-5 rounded-lg border border-border shadow-lg">
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Total Time Saved</h2>
          <div className="text-3xl font-mono text-signal-green">{Math.round(stats?.saved_green_s || 0)}s</div>
          <div className="text-xs text-text-muted mt-2">Green time given back to commuters</div>
        </div>

        <div className="bg-panel p-5 rounded-lg border border-border opacity-75">
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Old System Wasted</h2>
          <div className="text-3xl font-mono text-signal-red">{Math.round(stats?.fixed_wasted_green_s || 0)}s</div>
          <div className="text-xs text-text-muted mt-2">Time wasted by fixed timers</div>
        </div>

        <div className="bg-panel p-5 rounded-lg border border-signal-green/30 bg-signal-green/5 shadow-[0_0_15px_rgba(46,229,157,0.1)]">
          <h2 className="text-xs font-semibold text-signal-green uppercase tracking-wider mb-2">Our System Wasted</h2>
          <div className="text-3xl font-mono text-signal-green">{Math.round(stats?.adaptive_wasted_green_s || 0)}s</div>
          <div className="text-xs text-text-muted mt-2">Time wasted by AI adaptation</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Simple Bar Chart Comparison */}
        <div className="bg-panel p-6 rounded-lg border border-border shadow-lg">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-text-primary">System Comparison</h2>
            <p className="text-xs text-text-secondary">Comparing total seconds wasted and waited. Lower is better.</p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={comparisonData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#253045" vertical={false} />
              <XAxis dataKey="category" stroke="#94A3B8" tick={{ fill: '#94A3B8', fontSize: 12 }} />
              <YAxis stroke="#94A3B8" tick={{ fill: '#94A3B8', fontSize: 12 }} />
              <Tooltip 
                cursor={{ fill: '#1A2236' }} 
                contentStyle={{ backgroundColor: '#0A0E14', borderColor: '#253045', color: '#E2E8F0' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Bar dataKey="Old System" fill="#FF4D5E" radius={[4, 4, 0, 0]} maxBarSize={60} />
              <Bar dataKey="Our System" fill="#2EE59D" radius={[4, 4, 0, 0]} maxBarSize={60} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Growth of Time Saved (Area Chart) */}
        <div className="bg-panel p-6 rounded-lg border border-border shadow-lg">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-text-primary">Cumulative Time Saved Over Time</h2>
            <p className="text-xs text-text-secondary">Watch the system continuously recover lost time (Up is better).</p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={history} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="colorSaved" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2EE59D" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#2EE59D" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#253045" />
              <XAxis 
                dataKey="ts" 
                tickFormatter={formatTime} 
                stroke="#94A3B8" 
                tick={{ fill: '#94A3B8', fontSize: 12 }} 
              />
              <YAxis stroke="#94A3B8" tick={{ fill: '#94A3B8', fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0A0E14', borderColor: '#253045', color: '#E2E8F0' }}
                labelFormatter={(label) => `Time: ${formatTime(label as number)}`}
              />
              <Area 
                type="monotone" 
                dataKey="saved_green_s" 
                name="Seconds Saved"
                stroke="#2EE59D" 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorSaved)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}