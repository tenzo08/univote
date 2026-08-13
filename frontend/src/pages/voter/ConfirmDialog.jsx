export default function ConfirmDialog({ positions, selections, isSubmitting, onConfirm, onCancel }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-ballot-title"
      className="fixed inset-0 z-10 flex items-center justify-center bg-ink/40 px-4"
    >
      <div className="w-full max-w-md rounded bg-sheet p-6 shadow-lg">
        <h2 id="confirm-ballot-title" className="mb-4 font-display text-lg uppercase tracking-wide text-ink">
          Confirm your ballot
        </h2>
        <ul className="mb-4 space-y-2 text-sm font-body text-ink">
          {positions.map((position) => {
            const ids = selections[position.id] || []
            const names = position.candidates.filter((candidate) => ids.includes(candidate.id)).map((c) => c.full_name)
            return (
              <li key={position.id}>
                <span className="font-medium">{position.title}</span> — {names.length > 0 ? names.join(', ') : 'no selection'}
              </li>
            )
          })}
        </ul>
        <p className="mb-6 font-body text-sm text-ink">Once you cast your ballot, it can&rsquo;t be changed.</p>
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onCancel} className="rounded border border-rule px-4 py-2 text-sm text-ink">
            Go back
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="rounded bg-stamp px-4 py-2 text-sm text-sheet disabled:opacity-60"
          >
            {isSubmitting ? 'Casting…' : 'Cast ballot'}
          </button>
        </div>
      </div>
    </div>
  )
}
