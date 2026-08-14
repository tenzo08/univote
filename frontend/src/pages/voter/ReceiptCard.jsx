import { useState } from 'react'

export default function ReceiptCard({ receiptCode }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(receiptCode)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard access can be denied by the browser; the code is still visible to copy by hand.
    }
  }

  return (
    <div className="rounded border border-rule bg-sheet p-8 text-center">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-seal text-sheet">
        <span aria-hidden="true" className="font-display text-2xl">
          ✓
        </span>
      </div>
      <h1 className="mb-2 font-display text-xl uppercase tracking-wide text-ink">Ballot recorded</h1>
      <p className="mb-6 font-body text-sm text-ink">This code confirms your ballot was recorded.</p>
      <p className="mb-4 break-all font-data text-lg text-ink">{receiptCode}</p>
      <button
        type="button"
        onClick={handleCopy}
        className="rounded border border-rule px-4 py-2 text-sm text-ink transition-colors hover:border-maroon hover:text-maroon"
      >
        {copied ? 'Copied' : 'Copy code'}
      </button>
    </div>
  )
}
