import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useBallotSession from '../../hooks/useBallotSession'
import useCastBallot from '../../hooks/useCastBallot'
import { extractErrorMessage } from '../../lib/api'
import ConfirmDialog from './ConfirmDialog'
import PositionCard from './PositionCard'
import ReceiptCard from './ReceiptCard'

function formatCloseTime(iso) {
  if (!iso) return ''
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(iso))
}

function StatusScreen({ children }) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-sheet px-4 text-center">
      <div className="max-w-sm">{children}</div>
    </div>
  )
}

function BallotSkeleton() {
  return (
    <div className="mx-auto max-w-xl px-4 pt-8">
      <div className="mb-6 h-8 w-2/3 animate-pulse rounded bg-rule" />
      <div className="mb-6 h-40 animate-pulse rounded bg-rule" />
      <div className="h-40 animate-pulse rounded bg-rule" />
    </div>
  )
}

export default function Ballot() {
  const { data, isLoading, isError, refetch } = useBallotSession()
  const castBallot = useCastBallot()
  const navigate = useNavigate()
  const [selections, setSelections] = useState({})
  const [isConfirming, setIsConfirming] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const positions = data?.positions ?? []
  const filledCount = positions.filter((position) => (selections[position.id] || []).length > 0).length

  function updateSelection(positionId, ids) {
    setSelections((previous) => ({ ...previous, [positionId]: ids }))
  }

  async function handleConfirm() {
    setSubmitError('')
    const payload = positions.map((position) => ({
      position_id: position.id,
      candidate_ids: selections[position.id] || [],
    }))
    try {
      const result = await castBallot.mutateAsync(payload)
      navigate('/vote/receipt', { state: { receiptCode: result.receipt_code }, replace: true })
    } catch (err) {
      setSubmitError(extractErrorMessage(err))
      setIsConfirming(false)
    }
  }

  if (isLoading) {
    return <BallotSkeleton />
  }

  if (isError) {
    return (
      <StatusScreen>
        <p className="font-body text-base text-ink">Something went wrong loading your ballot.</p>
        <button type="button" onClick={() => refetch()} className="mt-4 rounded bg-ink px-4 py-2 text-sm text-sheet">
          Try again
        </button>
      </StatusScreen>
    )
  }

  if (!data.election) {
    return (
      <StatusScreen>
        <p className="font-body text-base text-ink">No election is currently open for voting.</p>
      </StatusScreen>
    )
  }

  if (!data.is_enrolled) {
    return (
      <StatusScreen>
        <p className="font-body text-base text-ink">
          You&rsquo;re not enrolled to vote in this election. Contact your election committee if you believe this is a
          mistake.
        </p>
      </StatusScreen>
    )
  }

  if (data.has_voted) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <ReceiptCard receiptCode={data.receipt_code} />
      </div>
    )
  }

  if (!data.election.is_open_for_voting) {
    return (
      <StatusScreen>
        <p className="font-body text-base text-ink">Voting isn&rsquo;t open right now.</p>
        {data.election.closes_at && (
          <p className="mt-2 font-body text-sm text-graph">Voting closes {formatCloseTime(data.election.closes_at)}.</p>
        )}
      </StatusScreen>
    )
  }

  return (
    <div className="mx-auto max-w-xl px-4 pb-28 pt-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl uppercase tracking-wide text-ink">{data.election.title}</h1>
        <p className="mt-1 font-body text-sm text-graph">Voting closes {formatCloseTime(data.election.closes_at)}.</p>
      </header>

      {positions.map((position) => (
        <PositionCard
          key={position.id}
          position={position}
          selectedIds={selections[position.id] || []}
          onChange={(ids) => updateSelection(position.id, ids)}
        />
      ))}

      {submitError && (
        <p role="alert" className="mb-4 text-sm text-stamp">
          {submitError}
        </p>
      )}

      <div className="fixed inset-x-0 bottom-0 border-t border-rule bg-sheet px-4 py-4 shadow-[0_-2px_8px_rgba(0,0,0,0.06)]">
        <div className="mx-auto flex max-w-xl items-center justify-between">
          <span className="font-body text-sm text-ink">
            {filledCount} of {positions.length} positions selected
          </span>
          <button
            type="button"
            onClick={() => setIsConfirming(true)}
            className="rounded bg-stamp px-6 py-2 font-body text-base text-sheet"
          >
            Cast ballot
          </button>
        </div>
      </div>

      {isConfirming && (
        <ConfirmDialog
          positions={positions}
          selections={selections}
          isSubmitting={castBallot.isPending}
          onCancel={() => setIsConfirming(false)}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  )
}
