import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../../components/ChartTooltip.jsx'
import { useTurnout } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'

function GroupedBarChart({ title, rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="mb-6 last:mb-0">
        <h3 className="mb-2 font-display text-sm uppercase tracking-wide text-graph">{title}</h3>
        <p className="font-body text-sm text-graph">No data yet.</p>
      </div>
    )
  }
  return (
    <div className="mb-6 last:mb-0">
      <h3 className="mb-2 font-display text-sm uppercase tracking-wide text-graph">{title}</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#D8D4CA" vertical={false} />
          <XAxis dataKey="group" tick={{ fontSize: 12, fill: '#657388' }} axisLine={{ stroke: '#D8D4CA' }} tickLine={false} />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12, fill: '#657388' }}
            axisLine={{ stroke: '#D8D4CA' }}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(137, 20, 55, 0.06)' }} />
          <Legend wrapperStyle={{ fontSize: 12, fontFamily: 'Source Sans 3, sans-serif' }} />
          <Bar dataKey="enrolled" fill="#D8D4CA" name="Enrolled" radius={[4, 4, 0, 0]} />
          <Bar dataKey="voted" fill="#891437" name="Voted" radius={[4, 4, 0, 0]} />
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
