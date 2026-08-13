import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useTurnout } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'

function GroupedBarChart({ title, rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="mb-6">
        <h3 className="mb-2 font-display text-sm uppercase tracking-wide text-graph">{title}</h3>
        <p className="font-body text-sm text-graph">No data yet.</p>
      </div>
    )
  }
  return (
    <div className="mb-6">
      <h3 className="mb-2 font-display text-sm uppercase tracking-wide text-graph">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="#D8D4CA" />
          <XAxis dataKey="group" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="enrolled" fill="#D8D4CA" name="Enrolled" />
          <Bar dataKey="voted" fill="#657388" name="Voted" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function TurnoutSection({ electionId }) {
  const { data, isLoading, isError, error } = useTurnout(electionId)

  if (isLoading) {
    return <p className="font-body text-sm text-graph">Loading turnout…</p>
  }
  if (isError) {
    return <p className="font-body text-sm text-graph">{extractErrorMessage(error)}</p>
  }

  return (
    <section>
      <h2 className="mb-3 font-display text-sm uppercase tracking-wide text-graph">Turnout</h2>
      <GroupedBarChart title="By year level" rows={data.by_year_level} />
      <GroupedBarChart title="By degree program" rows={data.by_degree_program} />
    </section>
  )
}
