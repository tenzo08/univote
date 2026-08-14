import TallyMarks from '../../components/TallyMarks.jsx'
import initials from '../../lib/initials.js'

/**
 * @param {{
 *   position: { id: number, title: string, max_votes: number, candidates: Array<{ id: number, full_name: string, student_number: string, platform: string }> },
 *   selectedIds: number[],
 *   onChange: (ids: number[]) => void,
 * }} props
 */
export default function PositionCard({ position, selectedIds, onChange }) {
  const { id, title, max_votes: maxVotes, candidates } = position
  const isSingleChoice = maxVotes === 1
  const atLimit = selectedIds.length >= maxVotes

  function toggle(candidateId) {
    if (isSingleChoice) {
      onChange([candidateId])
      return
    }
    if (selectedIds.includes(candidateId)) {
      onChange(selectedIds.filter((existing) => existing !== candidateId))
      return
    }
    if (atLimit) return
    onChange([...selectedIds, candidateId])
  }

  return (
    <fieldset className="mb-6 rounded-xl border border-rule bg-sheet p-4 shadow-card">
      <legend className="px-1 font-display text-lg uppercase tracking-wide text-ink">{title}</legend>
      <p className="mb-3 text-sm font-body text-graph">
        {isSingleChoice ? 'Choose one.' : `Choose up to ${maxVotes}.`}
      </p>
      {candidates.map((candidate) => {
        const checked = selectedIds.includes(candidate.id)
        const disabled = !isSingleChoice && !checked && atLimit
        return (
          <label
            key={candidate.id}
            className={`mb-2 flex items-start gap-3 rounded-lg p-2 transition-colors ${checked ? 'bg-gold/15' : 'hover:bg-rule/30'}`}
          >
            <input
              type={isSingleChoice ? 'radio' : 'checkbox'}
              name={`position-${id}`}
              checked={checked}
              disabled={disabled}
              onChange={() => toggle(candidate.id)}
              className="mt-1 accent-maroon"
            />
            <span
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-maroon font-display text-xs text-sheet"
            >
              {initials(candidate.full_name)}
            </span>
            <span>
              <span className="block font-body text-base text-ink">{candidate.full_name}</span>
              <span className="block font-data text-xs text-graph">{candidate.student_number}</span>
              {disabled && (
                <span className="block text-xs text-graph">
                  You&rsquo;ve selected the maximum of {maxVotes} for this position.
                </span>
              )}
            </span>
          </label>
        )
      })}
      {isSingleChoice && selectedIds.length > 0 && (
        <button type="button" onClick={() => onChange([])} className="mt-1 text-sm text-maroon underline">
          Clear selection
        </button>
      )}
      <p className="mt-3 flex items-center gap-2 font-data text-sm text-ink" aria-live="polite">
        <TallyMarks count={selectedIds.length} />
        <span>
          {selectedIds.length}/{maxVotes}
        </span>
      </p>
    </fieldset>
  )
}
