import { Navigate, useLocation } from 'react-router-dom'
import useBallotSession from '../../hooks/useBallotSession'
import ReceiptCard from './ReceiptCard'

export default function Receipt() {
  const location = useLocation()
  const stateReceiptCode = location.state?.receiptCode
  const { data, isLoading } = useBallotSession({ enabled: !stateReceiptCode })

  if (stateReceiptCode) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <ReceiptCard receiptCode={stateReceiptCode} />
      </div>
    )
  }

  if (isLoading) return null

  if (!data?.has_voted) {
    return <Navigate to="/vote" replace />
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <ReceiptCard receiptCode={data.receipt_code} />
    </div>
  )
}
