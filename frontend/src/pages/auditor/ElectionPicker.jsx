import { Link } from 'react-router-dom'
import { useElections } from '../../hooks/useElections'

export default function ElectionPicker() {
  const { data, isLoading, isError } = useElections()

  if (isLoading) {
    return <div className="p-8 font-body text-sm text-graph">Loading elections…</div>
  }
  if (isError) {
    return <div className="p-8 font-body text-sm text-stamp">Couldn&rsquo;t load elections.</div>
  }

  const elections = data ?? []

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 font-display text-2xl uppercase tracking-wide text-ink">Audit</h1>
      {elections.length === 0 && <p className="font-body text-sm text-graph">No elections yet.</p>}
      {elections.map((election) => (
        <Link
          key={election.id}
          to={`/audit/${election.id}`}
          className="mb-3 block rounded border border-rule p-4 hover:border-ink"
        >
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg uppercase tracking-wide text-ink">{election.title}</h2>
            <span className="rounded border border-rule px-2 py-0.5 font-data text-xs uppercase text-graph">
              {election.status}
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
