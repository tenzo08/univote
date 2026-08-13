import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useTimeline } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'

export default function TimelineChart({ electionId }) {
  const { data, isLoading, isError, error } = useTimeline(electionId)

  if (isLoading) {
    return <p className="font-body text-sm text-graph">Loading timeline…</p>
  }
  if (isError) {
    return <p className="font-body text-sm text-graph">{extractErrorMessage(error)}</p>
  }

  return (
    <section>
      <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">Timeline</h2>
      {!data || data.length === 0 ? (
        <p className="font-body text-sm text-graph">No ballots recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#D8D4CA" />
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Area type="monotone" dataKey="count" stroke="#141B2D" fill="#657388" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </section>
  )
}
