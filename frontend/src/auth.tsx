import { createContext, useContext, useState, type ReactNode } from 'react'
import { api, loadSession, saveSession, type Session } from './api'

interface AuthValue {
  session: Session | null
  signIn: (username: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession)

  async function signIn(username: string, password: string) {
    const r = await api.login(username, password)
    const s = { token: r.access_token, username: r.username, role: r.role }
    saveSession(s)
    setSession(s)
  }

  function signOut() {
    saveSession(null)
    setSession(null)
  }

  return <AuthContext.Provider value={{ session, signIn, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const v = useContext(AuthContext)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}
