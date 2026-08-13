import axios from 'axios'

const ACCESS_KEY = 'univote_access'
const REFRESH_KEY = 'univote_refresh'
const BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api`

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

let onAuthExpired = () => {}
export function setOnAuthExpired(handler) {
  onAuthExpired = handler
}

/**
 * @param {unknown} error
 * @returns {string}
 */
export function extractErrorMessage(error) {
  const data = error?.response?.data
  if (!data) return 'Something went wrong. Please try again.'
  if (typeof data.detail === 'string') return data.detail
  const firstFieldErrors = Object.values(data).find((value) => Array.isArray(value) && value.length)
  if (firstFieldErrors) return String(firstFieldErrors[0])
  return 'Something went wrong. Please try again.'
}

const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

async function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) {
    throw new Error('No refresh token available')
  }
  const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
  setTokens({ access: data.access, refresh: data.refresh ?? refresh })
  return data.access
}

async function handleResponseError(error) {
  const { config, response } = error
  const isUnauthorized = response?.status === 401
  const canRetry = isUnauthorized && config && !config._retried && getRefreshToken()

  if (!canRetry) {
    if (isUnauthorized) {
      clearTokens()
      onAuthExpired()
    }
    return Promise.reject(error)
  }

  config._retried = true
  try {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null
      })
    }
    const access = await refreshPromise
    config.headers.Authorization = `Bearer ${access}`
    return api(config)
  } catch (refreshError) {
    clearTokens()
    onAuthExpired()
    return Promise.reject(refreshError)
  }
}

api.interceptors.response.use((response) => response, handleResponseError)

export default api
