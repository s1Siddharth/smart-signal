// pages/Login.tsx — Split-layout login with animated mini junction + form
import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

export default function Login() {
  const { signInEmail, signInGoogle, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleEmail = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await signInEmail(email, password)
      navigate('/')
    } catch {
      // error shown via context
    } finally {
      setLoading(false)
    }
  }

  const handleGoogle = async () => {
    setLoading(true)
    try {
      await signInGoogle()
      navigate('/')
    } catch {
      // error shown via context
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg grid-bg flex">
      {/* Left panel — animated decorative junction */}
      <div className="hidden md:flex flex-1 items-center justify-center bg-panel border-r border-border relative overflow-hidden">
        <DecorativeJunction />
        <div className="absolute bottom-8 left-0 right-0 text-center">
          <p className="font-mono text-xs text-text-muted">SMART ADAPTIVE TRAFFIC SIGNAL</p>
          <p className="font-mono text-xs text-accent">v1.0 — OE Design Thinking</p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 max-w-md mx-auto w-full">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded bg-panel border border-border flex items-center justify-center">
              <span className="text-accent font-mono font-bold text-lg">S</span>
            </div>
            <div>
              <h1 className="font-sans font-bold text-text-primary text-lg leading-tight">Smart Signal</h1>
              <p className="text-text-muted text-xs">Traffic Control System</p>
            </div>
          </div>

          <h2 className="font-sans font-semibold text-text-primary text-xl mb-1">Sign in</h2>
          <p className="text-text-secondary text-sm mb-6">Access the traffic control dashboard.</p>

          {/* Error */}
          {error && (
            <div
              className="mb-4 p-3 rounded border text-sm text-signal-red"
              style={{ background: 'rgba(255,77,94,0.08)', borderColor: '#FF4D5E44' }}
            >
              {error}
            </div>
          )}

          {/* Email form */}
          <form onSubmit={handleEmail} className="flex flex-col gap-3">
            <div>
              <label className="block text-text-secondary text-xs mb-1.5" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 bg-panel border border-border rounded text-text-primary text-sm font-mono focus:outline-none focus:border-accent transition-colors"
                placeholder="operator@example.com"
              />
            </div>
            <div>
              <label className="block text-text-secondary text-xs mb-1.5" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 bg-panel border border-border rounded text-text-primary text-sm font-mono focus:outline-none focus:border-accent transition-colors"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              id="btn-email-signin"
              className="w-full py-2.5 rounded bg-accent text-bg font-sans font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-2 bg-bg text-text-muted text-xs">or</span>
            </div>
          </div>

          {/* Google button */}
          <button
            id="btn-google-signin"
            onClick={handleGoogle}
            disabled={loading}
            className="w-full py-2.5 rounded border border-border bg-panel text-text-primary text-sm font-sans font-medium flex items-center justify-center gap-2 hover:border-accent transition-colors disabled:opacity-50"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <p className="mt-6 text-center text-text-muted text-xs">
            Demo access — contact the administrator for credentials
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Decorative animated mini junction (CSS only, no JS) ────────

function DecorativeJunction() {
  const STATES = ['GREEN', 'RED', 'AMBER', 'GREEN']
  const COLORS: Record<string, string> = {
    GREEN: '#2EE59D', RED: '#FF4D5E', AMBER: '#FFB020', OFF: '#1E2736',
  }

  return (
    <div className="relative w-64 h-64">
      {/* SVG junction */}
      <svg viewBox="0 0 200 200" className="w-full h-full opacity-80">
        <rect x={80} y={0}   width={40} height={200} fill="#1A2236" />
        <rect x={0}  y={80}  width={200} height={40} fill="#1A2236" />
        <rect x={80} y={80}  width={40} height={40}  fill="#253045" />
        {[
          { cx: 100, cy: 30 },
          { cx: 170, cy: 100 },
          { cx: 100, cy: 170 },
          { cx: 30,  cy: 100 },
        ].map(({ cx, cy }, i) => (
          <circle key={i} cx={cx} cy={cy} r={10} fill={COLORS[STATES[i]]}>
            <animate attributeName="opacity" values="0.7;1;0.7" dur={`${1.5 + i * 0.3}s`} repeatCount="indefinite" />
          </circle>
        ))}
      </svg>
      <p className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-mono text-accent text-xs opacity-60">
        LIVE
      </p>
    </div>
  )
}