import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { clearTokens, getAccessToken, setOnAuthExpired, setTokens } from './api'

const USER_STORAGE_KEY = 'univote_user'

const AuthContext = createContext(null)

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function storeUser(user) {
  if (user) localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_STORAGE_KEY)
}

function userFromMeResponse(data) {
  return {
    userId: data.id,
    role: data.role,
    fullName: data.full_name,
    mustChangePassword: data.must_change_password,
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)
  const [isReady, setIsReady] = useState(false)

  const logout = useCallback(() => {
    clearTokens()
    storeUser(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setOnAuthExpired(logout)
  }, [logout])

  useEffect(() => {
    if (!getAccessToken()) {
      setIsReady(true)
      return
    }
    api
      .get('/me/')
      .then(({ data }) => {
        const nextUser = userFromMeResponse(data)
        storeUser(nextUser)
        setUser(nextUser)
      })
      .catch(() => logout())
      .finally(() => setIsReady(true))
    // Runs once on mount to reconcile a token that survived a hard refresh
    // with the current server-side account state, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login/', { email, password })
    setTokens({ access: data.access, refresh: data.refresh })
    const nextUser = {
      userId: data.user_id,
      role: data.role,
      fullName: data.full_name,
      mustChangePassword: data.must_change_password,
    }
    storeUser(nextUser)
    setUser(nextUser)
    return nextUser
  }, [])

  const markPasswordChanged = useCallback(() => {
    setUser((previous) => {
      if (!previous) return previous
      const next = { ...previous, mustChangePassword: false }
      storeUser(next)
      return next
    })
  }, [])

  const value = { user, isReady, login, logout, markPasswordChanged }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
