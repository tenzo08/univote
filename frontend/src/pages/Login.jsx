import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import upSeal from '../assets/UP-Seal.png'
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
    <div className="flex min-h-svh items-center justify-center bg-gradient-to-br from-maroon to-maroonDark px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-rule bg-sheet p-8 shadow-card"
      >
        <img src={upSeal} alt="University of the Philippines seal" className="mx-auto mb-4 h-20 w-20" />
        <h1 className="mb-1 text-center font-display text-xl uppercase tracking-wide text-ink">UniVote</h1>
        <p className="mb-6 text-center font-body text-xs uppercase tracking-wide text-graph">
          University of the Philippines
        </p>
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
          className="w-full rounded-lg bg-gold py-2 font-body text-base font-bold text-ink shadow-gold transition-all hover:brightness-105 motion-safe:hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:brightness-100"
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
