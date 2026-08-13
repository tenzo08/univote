import axios from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('axios', () => {
  const instance = vi.fn()
  instance.interceptors = {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  }
  instance.get = vi.fn()
  instance.post = vi.fn()
  return {
    default: {
      create: vi.fn(() => instance),
      post: vi.fn(),
    },
  }
})

function getResponseErrorHandler() {
  const instance = axios.create.mock.results[0].value
  return instance.interceptors.response.use.mock.calls[0][1]
}

function getInstance() {
  return axios.create.mock.results[0].value
}

function make401Error(overrides = {}) {
  return {
    response: { status: 401 },
    config: { headers: {}, ...overrides },
  }
}

describe('lib/api response interceptor', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetModules()
  })

  it('refreshes the access token once and retries the original request when a refresh token is available', async () => {
    const { setTokens, getAccessToken } = await import('./api')
    setTokens({ access: 'stale-access', refresh: 'valid-refresh' })

    axios.post.mockResolvedValueOnce({ data: { access: 'fresh-access', refresh: 'valid-refresh' } })
    const retriedResponse = { data: { ok: true } }
    getInstance().mockResolvedValueOnce(retriedResponse)

    const errorHandler = getResponseErrorHandler()
    const result = await errorHandler(make401Error())

    expect(axios.post).toHaveBeenCalledTimes(1)
    expect(axios.post.mock.calls[0][1]).toEqual({ refresh: 'valid-refresh' })
    expect(getInstance()).toHaveBeenCalledTimes(1)
    expect(getInstance().mock.calls[0][0].headers.Authorization).toBe('Bearer fresh-access')
    expect(result).toBe(retriedResponse)
    expect(getAccessToken()).toBe('fresh-access')
  })

  it('clears tokens and calls the expiry handler without retrying when there is no refresh token', async () => {
    const { setOnAuthExpired, getAccessToken } = await import('./api')
    const onExpired = vi.fn()
    setOnAuthExpired(onExpired)

    const errorHandler = getResponseErrorHandler()
    await expect(errorHandler(make401Error())).rejects.toBeTruthy()

    expect(axios.post).not.toHaveBeenCalled()
    expect(getInstance()).not.toHaveBeenCalled()
    expect(onExpired).toHaveBeenCalledTimes(1)
    expect(getAccessToken()).toBeNull()
  })

  it('logs out without a second refresh attempt when the refresh call itself fails', async () => {
    const { setTokens, setOnAuthExpired, getAccessToken, getRefreshToken } = await import('./api')
    setTokens({ access: 'stale-access', refresh: 'expired-refresh' })
    const onExpired = vi.fn()
    setOnAuthExpired(onExpired)

    axios.post.mockRejectedValueOnce(new Error('refresh rejected'))

    const errorHandler = getResponseErrorHandler()
    await expect(errorHandler(make401Error())).rejects.toBeTruthy()

    expect(axios.post).toHaveBeenCalledTimes(1)
    expect(onExpired).toHaveBeenCalledTimes(1)
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('does not attempt a second refresh for a request that already retried once', async () => {
    const { setTokens, setOnAuthExpired } = await import('./api')
    setTokens({ access: 'stale-access', refresh: 'valid-refresh' })
    const onExpired = vi.fn()
    setOnAuthExpired(onExpired)

    const errorHandler = getResponseErrorHandler()
    await expect(errorHandler(make401Error({ _retried: true }))).rejects.toBeTruthy()

    expect(axios.post).not.toHaveBeenCalled()
    expect(onExpired).toHaveBeenCalledTimes(1)
  })
})
