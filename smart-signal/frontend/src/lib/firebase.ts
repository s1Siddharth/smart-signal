// lib/firebase.ts — Firebase initialisation from VITE_ env vars
import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getAnalytics } from 'firebase/analytics'

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY?.replace(/"/g, ''),
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.replace(/"/g, ''),
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID?.replace(/"/g, ''),
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.replace(/"/g, ''),
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.replace(/"/g, ''),
  appId:             import.meta.env.VITE_FIREBASE_APP_ID?.replace(/"/g, ''),
  measurementId:     import.meta.env.VITE_FIREBASE_MEASUREMENT_ID?.replace(/"/g, ''),
}

export const isFirebaseEnabled = !!firebaseConfig.apiKey

export const app = isFirebaseEnabled ? initializeApp(firebaseConfig) : ({} as any)
export const analytics = isFirebaseEnabled && firebaseConfig.measurementId ? getAnalytics(app) : ({} as any)
export const auth = isFirebaseEnabled ? getAuth(app) : {
  currentUser: {
    getIdToken: async () => 'mock-token-dev-mode'
  },
  signOut: async () => {}
} as any

export default app
