import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, downloadEvidence, EVIDENCE_TYPES, type Control, type Finding, type Review, type Status } from '../api'
import { useAuth } from '../auth'
import { EvidenceInput } from '../EvidenceInput'
import { Button, ErrorNote, Interpretation, Loading, PolicyQuote, ResultBadge, RiskTag, STATUS, Stamp, fmtDate, inputClass } from '../ui'
import { STATE_LABEL } from './Reviews'

const ORDER: Status[] = ['FAIL', 'NEEDS_HUMAN_REVIEW', 'UNKNOWN', 'PASS']
const RISK = { high: 0, medium: 1, low: 2 }

function FindingRow({ f, review }: { f: Finding; review: Review }) {
  const ev = review.evidence.filter((e) => f.evidence_ids.includes(e.id))
  return (
    <li className="border-b border-rule py-6 last:border-0">
      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
        <Stamp status={f.status} />
        <span className="font-semibold">{f.section_heading}</span>
        <RiskTag risk={f.risk} />
        <span className="text-xs text-ink-soft">{f.requirement}</span>
      </div>
      <div className="space-y-3">
        <PolicyQuote citation={f.citation} policy={f.policy}>{f.policy_text}</PolicyQuote>
        <Interpretation source={f.source === 'rules' ? 'rule check' : f.source}>{f.interpretation}</Interpretation>
        <div className="grid grid-cols-[5.5rem_1fr] gap-3 text-sm sm:grid-cols-[7rem_1fr]">
          <span className="text-right text-xs text-ink-soft">Evidence</span>
          <div>
            {ev.length ? ev.map((e) => (
              <span key={e.id} className="mr-2 inline-block rounded bg-vellum px-2 py-0.5">E{e.id} {e.filename}</span>
            )) : <span className="text-ink-soft">None cited. Needs: {f.evidence_types.map((t) => EVIDENCE_TYPES[t] ?? t).join(', ') || 'reviewer judgement'}</span>}
            {f.notes.length > 0 && (
              <ul className="m-0 mt-2 list-none p-0 text-xs text-human">
                {f.notes.map((n) => <li key={n}>Guardrail: {n}</li>)}
              </ul>
            )}
          </div>
        </div>
      </div>
    </li>
  )
}

function DecisionPanel({ review, onDone }: { review: Review; onDone: (r: Review) => void }) {
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  const open = review.findings.filter((f) => f.status !== 'PASS').length

  async function decide(action: 'approve' | 'reject' | 'return') {
    setBusy(action); setError(null)
    try { onDone(await api.decide(review.id, action, comment)) } catch (e) { setError(e) } finally { setBusy(null) }
  }

  return (
    <section className="rounded-lg border-2 border-ink bg-paper p-6" aria-labelledby="decide">
      <h2 id="decide" className="m-0 text-xl font-semibold">Your decision</h2>
      <p className="mt-1 text-sm text-ink-soft">
        {open ? `${open} finding${open > 1 ? 's are' : ' is'} not a pass. Approving anyway requires a written justification.`
          : 'Every requirement passed with cited evidence.'} Sending back or rejecting always needs a comment.
      </p>
      <textarea className={`${inputClass} mt-4 min-h-24`} value={comment} onChange={(e) => setComment(e.target.value)}
        placeholder="Reasoning, conditions, or what the engineer needs to provide" aria-label="Decision comment" />
      <ErrorNote error={error} />
      <div className="mt-4 flex flex-wrap gap-3">
        <Button onClick={() => decide('approve')} busy={busy === 'approve'} disabled={!!busy}>Approve</Button>
        <Button variant="secondary" onClick={() => decide('return')} busy={busy === 'return'} disabled={!!busy}>Send back for evidence</Button>
        <Button variant="danger" onClick={() => decide('reject')} busy={busy === 'reject'} disabled={!!busy}>Reject</Button>
      </div>
    </section>
  )
}

export default function ReviewDetail() {
  const { id } = useParams()
  const reviewId = Number(id)
  const { session } = useAuth()
  const [review, setReview] = useState<Review | null>(null)
  const [controls, setControls] = useState<Control[] | null>(null)
  const [filter, setFilter] = useState<Status | 'ALL'>('ALL')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(() => api.review(reviewId).then(setReview, setError), [reviewId])
  useEffect(() => { load() }, [load])

  if (error && !review) return <ErrorNote error={error} />
  if (!review) return <Loading />

  const decided = review.status === 'approved' || review.status === 'rejected'
  const isAuthor = review.submitted_by === session?.username
  const canAddEvidence = session?.role !== 'reviewer' && !decided
  const canDecide = session?.role !== 'engineer' && review.status === 'evaluated' && !isAuthor
  const findings = [...review.findings]
    .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || RISK[a.risk] - RISK[b.risk])
    .filter((f) => filter === 'ALL' || f.status === filter)
  const counts = Object.fromEntries(ORDER.map((s) => [s, review.findings.filter((f) => f.status === s).length])) as Record<Status, number>

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label); setError(null)
    try { await fn() } catch (e) { setError(e) } finally { setBusy(null) }
  }

  return (
    <div className="space-y-12">
      <header>
        <p className="m-0 text-sm text-ink-soft">
          <Link to="/reviews" className="text-pen hover:underline">Reviews</Link> / #{review.id}
        </p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="m-0 text-3xl font-semibold tracking-tight">{review.title}</h1>
            <p className="mt-1 mb-0 text-sm text-ink-soft">Submitted by {review.submitted_by}, {fmtDate(review.created_at)}</p>
          </div>
          <div className="text-right">
            <p className="m-0 text-sm font-semibold">{STATE_LABEL[review.status] ?? review.status}</p>
            <ResultBadge result={review.result} />
          </div>
        </div>
        <blockquote className="m-0 mt-6 max-w-3xl border-l-4 border-ink pl-5 font-serif text-xl leading-relaxed">
          {review.description}
        </blockquote>
      </header>

      <section aria-labelledby="evidence">
        <h2 id="evidence" className="m-0 text-xl font-semibold">Evidence</h2>
        {review.evidence.length === 0 ? (
          <p className="mt-2 text-ink-soft">Nothing attached yet. Without evidence, every requirement will come back Unknown.</p>
        ) : (
          <ul className="m-0 mt-4 grid list-none gap-3 p-0 md:grid-cols-2">
            {review.evidence.map((e) => (
              <li key={e.id} className="rounded-md border border-rule bg-paper p-4">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-semibold">E{e.id} {e.filename}</span>
                  <button className="text-sm text-pen hover:underline" onClick={() => downloadEvidence(e.id, e.filename)}>Download</button>
                </div>
                <p className="m-0 text-xs text-ink-soft">{EVIDENCE_TYPES[e.evidence_type] ?? e.evidence_type}, sha256 {e.sha256.slice(0, 12)}</p>
                {e.excerpt && <pre className="mt-2 mb-0 max-h-24 overflow-hidden text-xs whitespace-pre-wrap text-ink-soft">{e.excerpt}</pre>}
              </li>
            ))}
          </ul>
        )}
        {canAddEvidence && (
          <div className="mt-4">
            <EvidenceInput busy={busy === 'evidence'} onAdd={(ev) => run('evidence', async () => {
              await api.addEvidence(review.id, ev.file, ev.type, ev.note); await load()
            })} />
          </div>
        )}
      </section>

      {!decided && (
        <section className="flex flex-wrap items-center gap-3 rounded-lg bg-paper p-5 ring-1 ring-rule">
          <div className="mr-auto max-w-xl">
            <p className="m-0 font-semibold">{review.findings.length ? 'Evidence changed? Evaluate again.' : 'Ready when your evidence is.'}</p>
            <p className="m-0 text-sm text-ink-soft">Evaluation runs on a local free model and can take a few minutes.</p>
          </div>
          <Button variant="secondary" busy={busy === 'controls'} onClick={() => run('controls', async () => setControls(await api.controls(review.id)))}>
            Preview matched policies
          </Button>
          <Button busy={busy === 'evaluate'} onClick={() => run('evaluate', async () => { setReview(await api.evaluate(review.id)); setControls(null) })}>
            {review.findings.length ? 'Re-evaluate' : 'Evaluate against policies'}
          </Button>
        </section>
      )}
      <ErrorNote error={error} />

      {controls && (
        <section aria-labelledby="matched">
          <h2 id="matched" className="m-0 text-xl font-semibold">Applicable requirements ({controls.length})</h2>
          <p className="mt-1 text-sm text-ink-soft">Found by keyword and semantic search across the policy library, before any evaluation.</p>
          <ul className="m-0 mt-4 list-none space-y-4 p-0">
            {controls.map((c) => (
              <li key={c.id}><PolicyQuote citation={c.citation} policy={c.policy_title}>{c.text}</PolicyQuote></li>
            ))}
          </ul>
        </section>
      )}

      {review.findings.length > 0 && (
        <section aria-labelledby="findings">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 id="findings" className="m-0 text-xl font-semibold">Findings</h2>
              {review.summary && <p className="mt-1 mb-0 max-w-3xl text-ink-soft">{review.summary}</p>}
            </div>
            <Link to={`/reviews/${review.id}/audit`} className="rounded-md border border-rule bg-paper px-4 py-2 text-sm font-semibold text-ink hover:border-ink-soft">
              Open audit package
            </Link>
          </div>
          {review.evidence_requested.length > 0 && (
            <div className="mt-5 rounded-md border-l-4 border-unknown bg-unknown/5 px-4 py-3">
              <p className="m-0 text-sm font-semibold">Evidence requested</p>
              <p className="m-0 text-sm">{review.evidence_requested.join(', ')}</p>
            </div>
          )}
          <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Filter findings">
            {(['ALL', ...ORDER] as const).map((s) => (
              <button key={s} onClick={() => setFilter(s)} aria-pressed={filter === s}
                className={`rounded-full border px-3 py-1 text-sm ${filter === s ? 'border-ink bg-ink text-vellum' : 'border-rule bg-paper text-ink-soft hover:border-ink-soft'}`}>
                {s === 'ALL' ? `All ${review.findings.length}` : `${STATUS[s].label} ${counts[s]}`}
              </button>
            ))}
          </div>
          <ul className="m-0 mt-2 list-none rounded-lg bg-paper px-5 ring-1 ring-rule sm:px-8">
            {findings.map((f) => <FindingRow key={f.id} f={f} review={review} />)}
            {findings.length === 0 && <li className="py-8 text-center text-ink-soft">No findings with this status.</li>}
          </ul>
        </section>
      )}

      {canDecide && <DecisionPanel review={review} onDone={setReview} />}
      {session?.role !== 'engineer' && review.status === 'evaluated' && isAuthor && (
        <p className="text-sm text-ink-soft">You submitted this change, so another reviewer has to decide on it.</p>
      )}

      {review.decisions.length > 0 && (
        <section aria-labelledby="history">
          <h2 id="history" className="m-0 text-xl font-semibold">Decisions</h2>
          <ol className="m-0 mt-4 list-none space-y-3 p-0">
            {review.decisions.map((d, i) => (
              <li key={i} className="rounded-md border border-rule bg-paper p-4">
                <p className="m-0 text-sm"><span className="font-semibold">{({ approve: 'Approved', reject: 'Rejected', return: 'Sent back' } as Record<string, string>)[d.action] ?? d.action}</span> by {d.reviewer}, {fmtDate(d.created_at)}</p>
                {d.comment && <p className="mt-1 mb-0 text-ink-soft">{d.comment}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}
