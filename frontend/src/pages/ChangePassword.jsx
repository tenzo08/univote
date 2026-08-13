import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { extractErrorMessage } from '../lib/api'
import { useAuth } from '../lib/auth.jsx'

function checkRules(password) {
  return [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'Not made up of only numbers', met: password.length > 0 && !/^\d+$/.test(password) },
  ]
}

export default function ChangePassword() {
  const { markPasswordChanged } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const rules = useMemo(() => checkRules(password), [password])
  const allRulesMet = rules.every((rule) => rule.met)
  const passwordsMatch = password.length > 0 && password === confirm

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!passwordsMatch) {
      setError("Passwords don't match.")
      return
    }
    setIsSubmitting(true)
    try {
      await api.post('/change-password/', { new_password: password })
      markPasswordChanged()
      navigate('/', { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-sheet px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded border border-rule bg-sheet p-8">
        <h1 className="mb-2 font-display text-xl uppercase tracking-wide text-ink">Set your password</h1>
        <p className="mb-6 text-sm font-body text-ink">
          Your initial password was your student number. Choose a password only you know before you vote.
        </p>
        <label className="mb-2 block">
          <span className="mb-1 block text-sm font-body text-ink">New password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded border border-rule bg-sheet px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-ink"
          />
        </label>
        <ul className="mb-4 space-y-1 text-sm font-body" aria-live="polite">
          {rules.map((rule) => (
            <li key={rule.label} className={rule.met ? 'text-seal' : 'text-graph'}>
              {rule.met ? '✓' : '·'} {rule.label}
            </li>
          ))}
        </ul>
        <label className="mb-6 block">
          <span className="mb-1 block text-sm font-body text-ink">Confirm password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            className="w-full rounded border border-rule bg-sheet px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-ink"
          />
        </label>
        {error && (
          <p role="alert" className="mb-4 text-sm text-stamp">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={isSubmitting || !allRulesMet || !passwordsMatch}
          className="w-full rounded bg-ink py-2 font-body text-base text-sheet disabled:opacity-60"
        >
          {isSubmitting ? 'Saving…' : 'Save password'}
        </button>
      </form>
    </div>
  )
}
