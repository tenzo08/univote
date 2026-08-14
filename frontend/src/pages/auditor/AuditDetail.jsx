import { useParams } from 'react-router-dom'
import StatusBadge from '../../components/StatusBadge.jsx'
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
      <div className="mb-6 flex items-center gap-3">
        <h1 className="font-display text-2xl uppercase tracking-wide text-ink">{election.title}</h1>
        <StatusBadge status={election.status} />
      </div>

      <div className="mb-6 rounded-xl border border-rule bg-sheet p-6 shadow-card">
        <ResultsSection electionId={electionId} />
      </div>
      <div className="mb-6 rounded-xl border border-rule bg-sheet p-6 shadow-card">
        <TurnoutSection electionId={electionId} />
      </div>
      <div className="mb-6 rounded-xl border border-rule bg-sheet p-6 shadow-card">
        <TimelineChart electionId={electionId} />
      </div>
      <IntegritySection electionId={electionId} />
    </div>
  )
}
