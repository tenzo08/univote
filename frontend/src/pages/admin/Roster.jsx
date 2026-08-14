import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useClearRoster,
  useEnrollVoters,
  useRoster,
  useUnenrollVoters,
  useUploadRosterCsv,
} from '../../hooks/useRoster'
import { extractErrorMessage } from '../../lib/api'

const PAGE_SIZE = 20

function CsvUpload({ electionId }) {
  const uploadCsv = useUploadRosterCsv(electionId)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setError('')
    setSummary(null)
    try {
      const result = await uploadCsv.mutateAsync(file)
      setSummary(result)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  return (
    <div className="mb-6 rounded-xl border border-rule bg-sheet p-4 shadow-card">
      <label className="block">
        <span className="mb-1 block text-sm font-body text-ink">Upload voter roster CSV</span>
        <input type="file" accept=".csv" onChange={handleFileChange} className="text-sm font-body text-ink" />
      </label>
      {error && (
        <p role="alert" className="mt-2 text-sm text-stamp">
          {error}
        </p>
      )}
      {summary && (
        <div className="mt-3 text-sm font-body text-ink">
          <p>
            <span className="text-seal">{summary.created} created</span> · {summary.skipped} skipped (already on the
            roster)
          </p>
          {summary.errors.length > 0 && (
            <ul className="mt-2 list-inside list-disc text-stamp">
              {summary.errors.map((error) => (
                <li key={error.row}>
                  Row {error.row}: {error.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function Roster() {
  const { id } = useParams()
  const electionId = Number(id)
  const [q, setQ] = useState('')
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState(() => new Set())

  const { data, isLoading, isError } = useRoster(electionId, { q, limit: PAGE_SIZE, offset })
  const enrollVoters = useEnrollVoters(electionId)
  const unenrollVoters = useUnenrollVoters(electionId)
  const clearRoster = useClearRoster(electionId)

  const results = data?.results ?? []
  const count = data?.count ?? 0
  const [actionMessage, setActionMessage] = useState('')
  const [actionError, setActionError] = useState('')

  function toggleSelected(voterId) {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(voterId)) next.delete(voterId)
      else next.add(voterId)
      return next
    })
  }

  function handleSearch(event) {
    setQ(event.target.value)
    setOffset(0)
    setSelected(new Set())
  }

  async function handleBulkEnroll() {
    setActionMessage('')
    setActionError('')
    try {
      const result = await enrollVoters.mutateAsync(Array.from(selected))
      setSelected(new Set())
      const parts = [`${result.added} enrolled`]
      if (result.unknown_voter_ids?.length > 0) {
        parts.push(`${result.unknown_voter_ids.length} not found`)
      }
      setActionMessage(parts.join(' · '))
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  async function handleBulkUnenroll() {
    setActionMessage('')
    setActionError('')
    try {
      const result = await unenrollVoters.mutateAsync(Array.from(selected))
      setSelected(new Set())
      const parts = [`${result.removed} unenrolled`]
      if (result.blocked_has_ballot?.length > 0) {
        parts.push(`${result.blocked_has_ballot.length} kept enrolled — already voted`)
      }
      setActionMessage(parts.join(' · '))
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  async function handleClearRoster() {
    setActionMessage('')
    setActionError('')
    const confirmed = window.confirm("Remove every non-candidate voter from this election's roster?")
    if (!confirmed) return
    try {
      await clearRoster.mutateAsync()
      setActionMessage('Roster cleared.')
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 font-display text-2xl uppercase tracking-wide text-ink">Voter roster</h1>

      <CsvUpload electionId={electionId} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search by name or student number"
          value={q}
          onChange={handleSearch}
          className="flex-1 rounded border border-rule px-3 py-2 text-base text-ink"
        />
        <button
          type="button"
          disabled={selected.size === 0}
          onClick={handleBulkEnroll}
          className="rounded border border-rule px-3 py-2 text-sm text-ink transition-colors hover:border-maroon hover:text-maroon disabled:opacity-50 disabled:hover:border-rule disabled:hover:text-ink"
        >
          Enroll selected
        </button>
        <button
          type="button"
          disabled={selected.size === 0}
          onClick={handleBulkUnenroll}
          className="rounded border border-rule px-3 py-2 text-sm text-ink transition-colors hover:border-maroon hover:text-maroon disabled:opacity-50 disabled:hover:border-rule disabled:hover:text-ink"
        >
          Unenroll selected
        </button>
        <button
          type="button"
          onClick={handleClearRoster}
          className="rounded border border-rule px-3 py-2 text-sm text-stamp"
        >
          Clear roster
        </button>
      </div>

      {actionMessage && <p className="mb-4 font-body text-sm text-seal">{actionMessage}</p>}
      {actionError && (
        <p role="alert" className="mb-4 font-body text-sm text-stamp">
          {actionError}
        </p>
      )}

      {isLoading && <p className="font-body text-sm text-graph">Loading roster…</p>}
      {isError && <p className="font-body text-sm text-stamp">Couldn&rsquo;t load the roster.</p>}

      {!isLoading && !isError && results.length === 0 && (
        <p className="font-body text-sm text-graph">No voters match this search.</p>
      )}

      {!isLoading && !isError && results.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-rule bg-sheet shadow-card">
        <table className="w-full border-collapse text-sm font-body text-ink">
          <thead>
            <tr className="border-b border-rule text-left font-data text-xs uppercase text-graph">
              <th className="py-2 pl-4 pr-2"></th>
              <th className="py-2 pr-2">Student number</th>
              <th className="py-2 pr-2">Name</th>
              <th className="py-2 pr-2">Year</th>
              <th className="py-2 pr-2">Program</th>
              <th className="py-2 pr-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {results.map((voter) => (
              <tr key={voter.id} className="border-b border-rule transition-colors hover:bg-gold/10">
                <td className="py-2 pl-4 pr-2">
                  <input
                    type="checkbox"
                    disabled={voter.has_ballot}
                    checked={selected.has(voter.id)}
                    onChange={() => toggleSelected(voter.id)}
                    className="accent-maroon"
                  />
                </td>
                <td className="py-2 pr-2 font-data">{voter.student_number}</td>
                <td className="py-2 pr-2">
                  {voter.first_name} {voter.last_name}
                </td>
                <td className="py-2 pr-2">{voter.year_level}</td>
                <td className="py-2 pr-2">{voter.degree_program}</td>
                <td className="py-2 pr-2">
                  {voter.has_ballot ? (
                    <span title="Already voted — can't be removed from the roster" className="text-graph">
                      🔒 Voted
                    </span>
                  ) : voter.enrolled ? (
                    <span className="text-seal">Enrolled</span>
                  ) : (
                    <span className="text-graph">Not enrolled</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {count > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm font-body text-ink">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
            className="rounded border border-rule px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="font-data text-xs text-graph">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, count)} of {count}
          </span>
          <button
            type="button"
            disabled={offset + PAGE_SIZE >= count}
            onClick={() => setOffset((value) => value + PAGE_SIZE)}
            className="rounded border border-rule px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
