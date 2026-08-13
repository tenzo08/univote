import { useState } from 'react'
import { useIntegrityReport } from '../../hooks/useAudit'
import { extractErrorMessage } from '../../lib/api'

export default function IntegritySection({ electionId }) {
  const [isOpen, setIsOpen] = useState(false)
  const { data, isLoading, isError, error } = useIntegrityReport(electionId)

  return (
    <section className="rounded border border-rule">
      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between px-4 py-3 font-display text-sm uppercase tracking-wide text-ink"
      >
        Integrity signals
        <span aria-hidden="true">{isOpen ? '−' : '+'}</span>
      </button>
      {isOpen && (
        <div className="border-t border-rule px-4 py-4">
          {isLoading && <p className="font-body text-sm text-graph">Loading…</p>}
          {isError && <p className="font-body text-sm text-graph">{extractErrorMessage(error)}</p>}
          {data && (
            <>
              <p className="mb-4 font-body text-sm text-ink">{data.note}</p>
              <p className="mb-3 font-body text-sm text-ink">{data.total_ballots} total ballots.</p>
              <div className="mb-4">
                <h4 className="mb-1 font-body text-xs uppercase text-graph">Rapid-succession pairs</h4>
                {data.rapid_succession_pairs.length === 0 ? (
                  <p className="font-body text-sm text-graph">None.</p>
                ) : (
                  <ul className="space-y-1 font-data text-xs text-ink">
                    {data.rapid_succession_pairs.map((pair) => (
                      <li key={`${pair.timestamp}-${pair.gap_seconds}`}>
                        {pair.timestamp} — {pair.gap_seconds}s gap
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4 className="mb-1 font-body text-xs uppercase text-graph">Velocity bursts</h4>
                {data.velocity_bursts.length === 0 ? (
                  <p className="font-body text-sm text-graph">None.</p>
                ) : (
                  <ul className="space-y-1 font-data text-xs text-ink">
                    {data.velocity_bursts.map((burst) => (
                      <li key={burst.window_end}>
                        {burst.window_end} — {burst.ballots_in_window} ballots
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  )
}
