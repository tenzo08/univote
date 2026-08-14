const STATUS_STYLES = {
  published: 'border-gold bg-gold/20 text-maroon',
}

const DEFAULT_STYLE = 'border-rule text-graph'

export default function StatusBadge({ status }) {
  return (
    <span
      className={`rounded border px-2 py-0.5 font-data text-xs uppercase ${STATUS_STYLES[status] ?? DEFAULT_STYLE}`}
    >
      {status}
    </span>
  )
}
