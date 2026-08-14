import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../../components/ChartTooltip.jsx'
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
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="timelineFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#891437" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#891437" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#D8D4CA" vertical={false} />
            <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#657388' }} axisLine={{ stroke: '#D8D4CA' }} tickLine={false} />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 12, fill: '#657388' }}
              axisLine={{ stroke: '#D8D4CA' }}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#891437', strokeWidth: 1 }} />
            <Area
              type="monotone"
              dataKey="count"
              name="Ballots"
              stroke="#891437"
              strokeWidth={2}
              fill="url(#timelineFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </section>
  )
}
