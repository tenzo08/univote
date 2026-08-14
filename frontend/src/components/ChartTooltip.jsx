export default function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="rounded-lg border border-rule bg-sheet px-3 py-2 text-xs shadow-card">
      {label && <p className="mb-1 font-body font-semibold text-ink">{label}</p>}
      {payload.map((entry) => (
        <p key={entry.dataKey} className="font-data text-ink" style={{ color: entry.color }}>
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  )
}
