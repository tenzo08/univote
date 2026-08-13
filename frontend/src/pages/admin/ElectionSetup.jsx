import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDeleteCandidate, useCandidates, useRegisterCandidate } from '../../hooks/useCandidates'
import { useArchiveElection, useElection, useAddPosition, usePublishElection } from '../../hooks/useElections'
import { extractErrorMessage } from '../../lib/api'

function AddPositionForm({ electionId, disabled }) {
  const addPosition = useAddPosition(electionId)
  const [title, setTitle] = useState('')
  const [maxVotes, setMaxVotes] = useState(1)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    try {
      await addPosition.mutateAsync({ title, max_votes: Number(maxVotes), order: 0 })
      setTitle('')
      setMaxVotes(1)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  if (disabled) {
    return <p className="mb-4 font-body text-sm text-graph">Positions lock once the election is published.</p>
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 flex flex-wrap items-end gap-3">
      <label className="flex-1">
        <span className="mb-1 block text-sm font-body text-ink">Position title</span>
        <input
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="w-full rounded border border-rule px-3 py-2 text-base text-ink"
        />
      </label>
      <label>
        <span className="mb-1 block text-sm font-body text-ink">Seats</span>
        <input
          type="number"
          min="1"
          required
          value={maxVotes}
          onChange={(event) => setMaxVotes(event.target.value)}
          className="w-20 rounded border border-rule px-3 py-2 text-base text-ink"
        />
      </label>
      <button type="submit" className="rounded bg-ink px-4 py-2 text-sm text-sheet">
        Add position
      </button>
      {error && (
        <p role="alert" className="w-full text-sm text-stamp">
          {error}
        </p>
      )}
    </form>
  )
}

function RegisterCandidateForm({ electionId, positionId, disabled }) {
  const registerCandidate = useRegisterCandidate(electionId)
  const [studentNumber, setStudentNumber] = useState('')
  const [platform, setPlatform] = useState('')
  const [error, setError] = useState('')

  if (disabled) return null

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    try {
      await registerCandidate.mutateAsync({ student_number: studentNumber, position: positionId, platform })
      setStudentNumber('')
      setPlatform('')
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 flex flex-wrap items-end gap-2">
      <label className="flex-1">
        <span className="mb-1 block text-xs font-body text-graph">Student number</span>
        <input
          required
          value={studentNumber}
          onChange={(event) => setStudentNumber(event.target.value)}
          className="w-full rounded border border-rule px-2 py-1 font-data text-sm text-ink"
        />
      </label>
      <label className="flex-1">
        <span className="mb-1 block text-xs font-body text-graph">Platform</span>
        <input
          value={platform}
          onChange={(event) => setPlatform(event.target.value)}
          className="w-full rounded border border-rule px-2 py-1 text-sm text-ink"
        />
      </label>
      <button type="submit" className="rounded border border-rule px-3 py-1 text-sm text-ink">
        Register
      </button>
      {error && (
        <p role="alert" className="w-full text-xs text-stamp">
          {error}
        </p>
      )}
    </form>
  )
}

export default function ElectionSetup() {
  const { id } = useParams()
  const electionId = Number(id)
  const { data: election, isLoading: electionLoading } = useElection(electionId)
  const { data: positions, isLoading: candidatesLoading } = useCandidates(electionId)
  const deleteCandidate = useDeleteCandidate(electionId)
  const publishElection = usePublishElection(electionId)
  const archiveElection = useArchiveElection(electionId)
  const [publishError, setPublishError] = useState('')
  const [actionError, setActionError] = useState('')

  if (electionLoading || candidatesLoading) {
    return <div className="p-8 font-body text-sm text-graph">Loading…</div>
  }
  if (!election) {
    return <div className="p-8 font-body text-sm text-stamp">Election not found.</div>
  }

  const isPublished = election.status === 'published'
  const positionList = positions ?? []
  const readinessReasons = []
  if (positionList.length === 0) readinessReasons.push('Add at least one position.')
  positionList
    .filter((position) => position.candidates.length === 0)
    .forEach((position) => readinessReasons.push(`${position.title} has no candidates.`))
  const canPublish = election.status === 'draft' && readinessReasons.length === 0

  async function handlePublish() {
    setPublishError('')
    const confirmed = window.confirm(
      "Publishing archives any other published election and locks this election's candidates. Continue?",
    )
    if (!confirmed) return
    try {
      await publishElection.mutateAsync()
    } catch (err) {
      setPublishError(extractErrorMessage(err))
    }
  }

  async function handleDeleteCandidate(candidateId) {
    setActionError('')
    try {
      await deleteCandidate.mutateAsync(candidateId)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  async function handleArchive() {
    setActionError('')
    try {
      await archiveElection.mutateAsync()
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl uppercase tracking-wide text-ink">{election.title}</h1>
          <span className="mt-1 inline-block rounded border border-rule px-2 py-0.5 font-data text-xs uppercase text-graph">
            {election.status}
          </span>
        </div>
        <Link to={`/admin/elections/${electionId}/roster`} className="rounded border border-rule px-4 py-2 text-sm text-ink">
          Voter roster
        </Link>
      </div>

      <section className="mb-8">
        <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">Positions &amp; candidates</h2>
        {actionError && (
          <p role="alert" className="mb-3 text-sm text-stamp">
            {actionError}
          </p>
        )}
        <AddPositionForm electionId={electionId} disabled={isPublished} />
        {positionList.map((position) => (
          <div key={position.id} className="mb-4 rounded border border-rule p-4">
            <h3 className="font-display text-base uppercase tracking-wide text-ink">
              {position.title}{' '}
              <span className="font-body text-xs normal-case text-graph">
                ({position.max_votes} seat{position.max_votes > 1 ? 's' : ''})
              </span>
            </h3>
            {position.candidates.length === 0 && <p className="mt-1 text-sm text-graph">No candidates yet.</p>}
            <ul className="mt-2 space-y-1">
              {position.candidates.map((candidate) => (
                <li key={candidate.id} className="flex items-center justify-between text-sm font-body text-ink">
                  <span>
                    {candidate.full_name} <span className="font-data text-xs text-graph">{candidate.student_number}</span>
                  </span>
                  {!isPublished && (
                    <button
                      type="button"
                      onClick={() => handleDeleteCandidate(candidate.id)}
                      className="text-xs text-stamp underline"
                    >
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <RegisterCandidateForm electionId={electionId} positionId={position.id} disabled={isPublished} />
          </div>
        ))}
      </section>

      <section className="rounded border border-rule p-4">
        <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">Publish</h2>
        {election.status === 'draft' && readinessReasons.length > 0 && (
          <ul className="mb-3 list-inside list-disc text-sm text-graph">
            {readinessReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        {publishError && (
          <p role="alert" className="mb-3 text-sm text-stamp">
            {publishError}
          </p>
        )}
        {election.status === 'draft' && (
          <button
            type="button"
            onClick={handlePublish}
            disabled={!canPublish || publishElection.isPending}
            className="rounded bg-stamp px-4 py-2 text-sm text-sheet disabled:opacity-50"
          >
            Publish
          </button>
        )}
        {election.status === 'published' && (
          <button
            type="button"
            onClick={handleArchive}
            disabled={archiveElection.isPending}
            className="rounded border border-rule px-4 py-2 text-sm text-ink"
          >
            Archive
          </button>
        )}
      </section>
    </div>
  )
}
