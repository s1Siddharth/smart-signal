// auth/AuthContext.tsx — Firebase auth context with email/password and Google sign-in
import React, { createContext, useContext, useEffect, useState } from 'react'
import {
  GoogleAuthProvider,
  User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from 'firebase/auth'
import { auth, isFirebaseEnabled } from '@/lib/firebase'

interface AuthContextValue {
  user: User | null
  loading: boolean
  signInEmail: (email: string, password: string) => Promise<void>
  signInGoogle: () => Promise<void>
  logout: () => Promise<void>
  error: string | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

const googleProvider = new GoogleAuthProvider()

function mapError(code: string): string {
  switch (code) {
    case 'auth/wrong-password':
    case 'auth/user-not-found':
    case 'auth/invalid-credential':
      return 'Incorrect email or password.'
    case 'auth/popup-closed-by-user':
      return 'Sign-in popup was closed.'
    case 'auth/network-request-failed':
      return 'Network error. Check your connection.'
    case 'auth/unauthorized-domain':
      return 'This domain is not authorised. Add it in Firebase console.'
    default:
      return `Sign-in failed (${code}).`
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isFirebaseEnabled) {
      // DEV MODE: Auto log-in instantly
      setUser({ uid: 'dev', email: 'dev@example.com' } as unknown as User)
      setLoading(false)
      return
    }

    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u)
      setLoading(false)
    })
    return unsub
  }, [])

  const signInEmail = async (email: string, password: string) => {
    setError(null)
    if (!isFirebaseEnabled) {
      setUser({ uid: 'dev', email } as unknown as User)
      return
    }
    try {
      await signInWithEmailAndPassword(auth, email, password)
    } catch (e: unknown) {
      const code = (e as { code?: string }).code ?? 'unknown'
      setError(mapError(code))
      throw e
    }
  }

  const signInGoogle = async () => {
    setError(null)
    if (!isFirebaseEnabled) {
      setUser({ uid: 'dev', email: 'dev-google@example.com' } as unknown as User)
      return
    }
    try {
      await signInWithPopup(auth, googleProvider)
    } catch (e: unknown) {
      const code = (e as { code?: string }).code ?? 'unknown'
      if (code === 'auth/popup-blocked' || code === 'auth/operation-not-allowed') {
        await signInWithRedirect(auth, googleProvider)
        return
      }
      setError(mapError(code))
      throw e
    }
  }

  const logout = async () => {
    if (!isFirebaseEnabled) {
      setUser(null)
      return
    }
    await signOut(auth)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInEmail, signInGoogle, logout, error }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

