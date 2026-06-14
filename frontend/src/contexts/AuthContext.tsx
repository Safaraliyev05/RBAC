import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { authApi } from '@/api/auth'
import { tokenStorage } from '@/api/axios'
import type { AuthUser } from '@/types'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: {
    email: string
    first_name: string
    last_name: string
    password: string
    password_confirm: string
  }) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (codename: string) => boolean
  hasRole: (roleName: string) => boolean
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const initialized = useRef(false)

  const refreshProfile = useCallback(async () => {
    try {
      const { data } = await authApi.getProfile()
      setUser(data)
    } catch {
      setUser(null)
      tokenStorage.clear()
    }
  }, [])

  // On mount: restore session if tokens exist
  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    const access = tokenStorage.getAccess()
    if (!access) {
      setIsLoading(false)
      return
    }
    refreshProfile().finally(() => setIsLoading(false))
  }, [refreshProfile])

  // Listen for forced logout events (from axios interceptor)
  useEffect(() => {
    const handler = () => {
      setUser(null)
      tokenStorage.clear()
    }
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authApi.login({ email, password })
    tokenStorage.setTokens(data.access, data.refresh)
    await refreshProfile()
  }, [refreshProfile])

  const register = useCallback(async (formData: {
    email: string
    first_name: string
    last_name: string
    password: string
    password_confirm: string
  }) => {
    const { data } = await authApi.register(formData)
    tokenStorage.setTokens(data.tokens.access, data.tokens.refresh)
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    if (refresh) {
      try {
        await authApi.logout(refresh)
      } catch {
        // Silently ignore errors on logout (token may already be expired)
      }
    }
    tokenStorage.clear()
    setUser(null)
  }, [])

  const hasPermission = useCallback((codename: string): boolean => {
    if (!user) return false
    if (user.is_staff) return true  // Staff bypass (superuser)
    return user.permissions.includes(codename)
  }, [user])

  const hasRole = useCallback((roleName: string): boolean => {
    if (!user) return false
    return user.roles.includes(roleName)
  }, [user])

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      hasPermission,
      hasRole,
      refreshProfile,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
