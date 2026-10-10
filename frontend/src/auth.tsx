import { createContext, useContext, useState, type ReactNode } from 'react'
import { api, loadSession, saveSession, type Role, type Session } from './api'

interface AuthValue {
  session: Session | null
  signIn: (username: string, password: string) => Promise<void>
  /** Store a token returned by sign-up, password change or "sign out everywhere". */
  adopt: (r: { access_token: string; username: string; role: Role }) => void
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession)

  function adopt(r: { access_token: string; username: string; role: Role }) {
    const s = { token: r.access_token, username: r.username, role: r.role }
    saveSession(s)
    setSession(s)
  }

  async function signIn(username: string, password: string) {
    adopt(await api.login(username, password))
  }

  function signOut() {
    saveSession(null)
    setSession(null)
  }

  return <AuthContext.Provider value={{ session, signIn, adopt, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const v = useContext(AuthContext)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}
