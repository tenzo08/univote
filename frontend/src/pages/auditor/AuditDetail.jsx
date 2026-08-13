import { useParams } from 'react-router-dom'
import { useElection } from '../../hooks/useElections'
import IntegritySection from './IntegritySection'
import ResultsSection from './ResultsSection'
import TimelineChart from './TimelineChart'
import TurnoutSection from './TurnoutSection'

export default function AuditDetail() {
  const { id } = useParams()
  const electionId = Number(id)
  const { data: election, isLoading } = useElection(electionId)

  if (isLoading) {
    return <div className="p-8 font-body text-sm text-graph">Loading…</div>
  }
  if (!election) {
    return <div className="p-8 font-body text-sm text-stamp">Election not found.</div>
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-1 font-display text-2xl uppercase tracking-wide text-ink">{election.title}</h1>
      <p className="mb-6 font-data text-xs uppercase text-graph">{election.status}</p>

      <div className="mb-8">
        <ResultsSection electionId={electionId} />
      </div>
      <div className="mb-8">
        <TurnoutSection electionId={electionId} />
      </div>
      <div className="mb-8">
        <TimelineChart electionId={electionId} />
      </div>
      <IntegritySection electionId={electionId} />
    </div>
  )
}
