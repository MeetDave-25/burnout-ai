import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, ApiError, type Me, type Role } from './api'

interface AuthState {
  me: Me | null
  ready: boolean
  setMe: (me: Me | null) => void
  refresh: () => Promise<Me | null>
  login: (email: string, password: string) => Promise<Me>
  signup: (body: { email: string; password: string; name: string; role_type: Role }) => Promise<Me>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [ready, setReady] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const m = await api.me()
      setMe(m)
      return m
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 401)) console.error(e)
      setMe(null)
      return null
    } finally {
      setReady(true)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    const m = await api.login(email, password)
    setMe(m)
    return m
  }, [])
  const signup = useCallback(async (body: Parameters<typeof api.signup>[0]) => {
    const m = await api.signup(body)
    setMe(m)
    return m
  }, [])
  const logout = useCallback(async () => {
    await api.logout()
    setMe(null)
  }, [])

  return <AuthContext.Provider value={{ me, ready, setMe, refresh, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

/** Redirects to /login (and back again afterwards) when nobody is signed in. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, ready } = useAuth()
  const location = useLocation()
  if (!ready) return null
  const next = encodeURIComponent(location.pathname + location.search)
  if (!me) return <Navigate to={`/login?next=${next}`} replace />
  if (!me.user.email_verified) return <Navigate to={`/verify?next=${next}`} replace />
  return <>{children}</>
}

export const isAdmin = (me: Me | null) => !!me?.membership && ['owner', 'admin'].includes(me.membership.role)
