import TallyMarks from '../../components/TallyMarks.jsx'
import { useResults } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'

function ResultsPosition({ position }) {
  const maxVotes = Math.max(1, ...position.candidates.map((candidate) => candidate.votes))
  return (
    <div className="mb-6">
      <h3 className="mb-2 flex items-center gap-2 font-display text-base uppercase tracking-wide text-ink">
        {position.position}
        {position.is_tied && (
          <span className="rounded border border-rule px-2 py-0.5 font-body text-xs normal-case text-graph">Tie</span>
        )}
      </h3>
      <ul className="space-y-3">
        {position.candidates.map((candidate) => (
          <li key={candidate.candidate_id}>
            <div className="mb-1 flex items-center justify-between font-body text-sm text-ink">
              <span>{candidate.name}</span>
              <span className="flex items-center gap-2 font-data text-xs">
                <TallyMarks count={candidate.votes} />
                {candidate.votes}
              </span>
            </div>
            <div className="h-2 rounded bg-rule">
              <div className="h-2 rounded bg-graph" style={{ width: `${(candidate.votes / maxVotes) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ResultsSection({ electionId }) {
  const { data, isLoading, isError, error } = useResults(electionId)

  if (isLoading) {
    return <p className="font-body text-sm text-graph">Loading results…</p>
  }
  if (isError) {
    return <p className="font-body text-sm text-graph">{extractErrorMessage(error)}</p>
  }

  return (
    <section>
      <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">Results</h2>
      <div className="mb-4 rounded border border-rule p-3 font-body text-sm text-ink">
        <span className="font-data text-lg">{data.turnout.turnout_pct}%</span> turnout — {data.turnout.voted} of{' '}
        {data.turnout.enrolled} enrolled voters
      </div>
      {data.results.map((position) => (
        <ResultsPosition key={position.position} position={position} />
      ))}
    </section>
  )
}
