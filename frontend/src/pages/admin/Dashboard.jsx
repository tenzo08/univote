import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCreateElection, useElections } from '../../hooks/useElections'
import { extractErrorMessage } from '../../lib/api'
import StatusBadge from '../../components/StatusBadge.jsx'

function ElectionCard({ election }) {
  return (
    <Link
      to={`/admin/elections/${election.id}`}
      className="mb-3 block rounded border border-rule p-4 shadow-sm transition-colors hover:border-maroon"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg uppercase tracking-wide text-ink">{election.title}</h3>
        <StatusBadge status={election.status} />
      </div>
      <p className="mt-1 font-data text-xs text-graph">
        {election.candidate_count} candidates · {election.enrolled_count} enrolled · {election.ballot_count} ballots
      </p>
    </Link>
  )
}

function ElectionGroup({ title, elections }) {
  if (elections.length === 0) return null
  return (
    <section className="mb-8">
      <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">{title}</h2>
      {elections.map((election) => (
        <ElectionCard key={election.id} election={election} />
      ))}
    </section>
  )
}

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export default function Dashboard() {
  const { data, isLoading, isError } = useElections()
  const createElection = useCreateElection()
  const navigate = useNavigate()
  const [isCreating, setIsCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [opensAt, setOpensAt] = useState(toLocalInputValue(new Date()))
  const [closesAt, setClosesAt] = useState(toLocalInputValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)))
  const [error, setError] = useState('')

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    try {
      const created = await createElection.mutateAsync({
        title,
        description: '',
        opens_at: new Date(opensAt).toISOString(),
        closes_at: new Date(closesAt).toISOString(),
        positions: [],
      })
      setIsCreating(false)
      setTitle('')
      navigate(`/admin/elections/${created.id}`)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  if (isLoading) {
    return <div className="p-8 font-body text-sm text-graph">Loading elections…</div>
  }
  if (isError) {
    return <div className="p-8 font-body text-sm text-stamp">Couldn&rsquo;t load elections.</div>
  }

  const elections = data ?? []
  const active = elections.filter((election) => election.status === 'published')
  const drafts = elections.filter((election) => election.status === 'draft')
  const archived = elections.filter((election) => election.status === 'archived')

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl uppercase tracking-wide text-ink">Elections</h1>
        <button
          type="button"
          onClick={() => setIsCreating((value) => !value)}
          className="rounded bg-maroon px-4 py-2 text-sm text-sheet transition-colors hover:bg-maroonDark"
        >
          New election
        </button>
      </div>

      {isCreating && (
        <form onSubmit={handleCreate} className="mb-8 rounded border border-rule p-4">
          <label className="mb-3 block">
            <span className="mb-1 block text-sm font-body text-ink">Title</span>
            <input
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="w-full rounded border border-rule px-3 py-2 text-base text-ink"
            />
          </label>
          <div className="mb-3 flex gap-3">
            <label className="flex-1">
              <span className="mb-1 block text-sm font-body text-ink">Opens</span>
              <input
                type="datetime-local"
                required
                value={opensAt}
                onChange={(event) => setOpensAt(event.target.value)}
                className="w-full rounded border border-rule px-3 py-2 text-base text-ink"
              />
            </label>
            <label className="flex-1">
              <span className="mb-1 block text-sm font-body text-ink">Closes</span>
              <input
                type="datetime-local"
                required
                value={closesAt}
                onChange={(event) => setClosesAt(event.target.value)}
                className="w-full rounded border border-rule px-3 py-2 text-base text-ink"
              />
            </label>
          </div>
          {error && (
            <p role="alert" className="mb-3 text-sm text-stamp">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={createElection.isPending}
            className="rounded bg-maroon px-4 py-2 text-sm text-sheet transition-colors hover:bg-maroonDark disabled:opacity-60"
          >
            Create draft
          </button>
        </form>
      )}

      {elections.length === 0 && !isCreating && (
        <p className="font-body text-sm text-graph">No elections yet. Create one to get started.</p>
      )}

      <ElectionGroup title="Active" elections={active} />
      <ElectionGroup title="Drafts" elections={drafts} />
      <ElectionGroup title="Archived" elections={archived} />
    </div>
  )
}
