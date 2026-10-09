import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ReviewSummary } from '../api'
import { useAuth } from '../auth'
import { ErrorNote, Loading, PageTitle, ResultBadge, fmtDate } from '../ui'

const STATE_LABEL: Record<string, string> = {
  submitted: 'Awaiting evaluation', evaluated: 'Awaiting decision', approved: 'Approved',
  rejected: 'Rejected', returned: 'Sent back',
}

export default function Reviews() {
  const { session } = useAuth()
  const [rows, setRows] = useState<ReviewSummary[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.reviews().then(setRows, setError) }, [])
  const canSubmit = session?.role !== 'reviewer'

  return (
    <>
      <PageTitle title="Reviews" lead="Change requests, their findings, and where each one stands.">
        {canSubmit && <Link to="/reviews/new" className="rounded-md bg-pen px-4 py-2 text-sm font-semibold text-white hover:bg-pen-dark">Start a review</Link>}
      </PageTitle>
      <ErrorNote error={error} />
      {!rows && !error && <Loading />}
      {rows && rows.length === 0 && (
        <div className="rounded-lg border border-dashed border-rule bg-paper px-6 py-14 text-center">
          <p className="m-0 font-semibold">No reviews yet</p>
          <p className="mt-1 text-ink-soft">{canSubmit ? 'Start one by describing a change you plan to ship.' : 'Reviews appear here when engineers submit changes.'}</p>
        </div>
      )}
      {rows && rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-rule bg-paper">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead className="border-b border-rule text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">Change</th>
                <th className="px-4 py-3 font-medium">Stage</th>
                <th className="px-4 py-3 font-medium">Result</th>
                <th className="px-4 py-3 text-right font-medium">Open findings</th>
                <th className="px-4 py-3 font-medium">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-rule last:border-0 hover:bg-vellum/60">
                  <td className="px-4 py-3">
                    <Link to={`/reviews/${r.id}`} className="font-semibold text-ink hover:text-pen">{r.title}</Link>
                    <span className="block text-xs text-ink-soft">#{r.id} by {r.submitted_by}</span>
                  </td>
                  <td className="px-4 py-3">{STATE_LABEL[r.status] ?? r.status}</td>
                  <td className="px-4 py-3"><ResultBadge result={r.result} /></td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.findings ? `${r.open} of ${r.findings}` : '—'}</td>
                  <td className="px-4 py-3 text-ink-soft">{fmtDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export { STATE_LABEL }
