import TallyMarks from '../../components/TallyMarks.jsx'
import { useResults } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'
import initials from '../../lib/initials.js'

function ResultsPosition({ position }) {
  const maxVotes = Math.max(1, ...position.candidates.map((candidate) => candidate.votes))
  const totalVotes = position.candidates.reduce((sum, candidate) => sum + candidate.votes, 0)
  return (
    <div className="mb-6 last:mb-0">
      <h3 className="mb-3 flex items-center gap-2 font-display text-base uppercase tracking-wide text-ink">
        {position.position}
        {position.is_tied && (
          <span className="rounded border border-gold bg-gold/20 px-2 py-0.5 font-body text-xs normal-case text-maroon">
            Tie
          </span>
        )}
      </h3>
      <ul className="space-y-4">
        {position.candidates.map((candidate) => {
          const isLeading = !position.is_tied && candidate.votes === maxVotes && maxVotes > 0
          const pct = totalVotes > 0 ? Math.round((candidate.votes / totalVotes) * 100) : 0
          return (
            <li key={candidate.candidate_id}>
              <div className="mb-1 flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-maroon font-display text-[10px] text-sheet"
                >
                  {initials(candidate.name)}
                </span>
                <span className={`font-body text-sm ${isLeading ? 'font-semibold text-ink' : 'text-ink'}`}>
                  {candidate.name}
                </span>
                {isLeading && (
                  <span className="rounded border border-gold bg-gold/20 px-1.5 py-0.5 font-body text-[10px] uppercase text-maroon">
                    Leading
                  </span>
                )}
                <span className="ml-auto flex items-center gap-2 font-data text-xs text-graph">
                  <TallyMarks count={candidate.votes} />
                  {candidate.votes} ({pct}%)
                </span>
              </div>
              <div className="h-3 rounded-full bg-rule">
                <div
                  className={`h-3 rounded-full transition-all ${isLeading ? 'bg-gold' : 'bg-graph'}`}
                  style={{ width: `${(candidate.votes / maxVotes) * 100}%` }}
                />
              </div>
            </li>
          )
        })}
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
      <div className="mb-4 rounded-xl border border-rule bg-gradient-to-br from-maroon to-maroonDark p-4 text-sheet shadow-card">
        <span className="font-display text-2xl">{data.turnout.turnout_pct}%</span>{' '}
        <span className="font-body text-sm">
          turnout — {data.turnout.voted} of {data.turnout.enrolled} enrolled voters
        </span>
      </div>
      {data.results.map((position) => (
        <ResultsPosition key={position.position} position={position} />
      ))}
    </section>
  )
}
