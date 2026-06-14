import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = '/api'

// Token storage helpers
export const tokenStorage = {
  getAccess: (): string | null => localStorage.getItem('access_token'),
  getRefresh: (): string | null => localStorage.getItem('refresh_token'),
  setTokens: (access: string, refresh: string): void => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  clear: (): void => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Request interceptor: attach access token ─────────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccess()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ─── Response interceptor: refresh on 401 ─────────────────────────────────────
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

function processQueue(error: AxiosError | null, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryConfig

    // Skip retry for the refresh endpoint itself to avoid infinite loops
    const isRefreshEndpoint = originalRequest?.url?.includes('/auth/token/refresh/')
    const isLoginEndpoint = originalRequest?.url?.includes('/auth/login/')

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isRefreshEndpoint &&
      !isLoginEndpoint
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = tokenStorage.getRefresh()
      if (!refreshToken) {
        tokenStorage.clear()
        processQueue(error, null)
        isRefreshing = false
        window.dispatchEvent(new Event('auth:logout'))
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        })
        const newAccess: string = data.access
        const newRefresh: string = data.refresh ?? refreshToken
        tokenStorage.setTokens(newAccess, newRefresh)
        api.defaults.headers.common.Authorization = `Bearer ${newAccess}`
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        processQueue(null, newAccess)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as AxiosError, null)
        tokenStorage.clear()
        window.dispatchEvent(new Event('auth:logout'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default api
