import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch {
      setError("That email and password don't match an account.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-sheet px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded border border-rule bg-sheet p-8">
        <h1 className="mb-6 font-display text-xl uppercase tracking-wide text-ink">UniVote</h1>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-body text-ink">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded border border-rule bg-sheet px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-maroon"
          />
        </label>
        <label className="mb-6 block">
          <span className="mb-1 block text-sm font-body text-ink">Password</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded border border-rule bg-sheet px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-maroon"
          />
        </label>
        {error && (
          <p role="alert" className="mb-4 text-sm text-stamp">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded bg-maroon py-2 font-body text-base text-sheet transition-colors hover:bg-maroonDark disabled:opacity-60"
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
