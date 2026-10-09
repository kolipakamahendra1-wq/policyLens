import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, saveBlob, type AuditPackage as Pkg } from '../api'
import { Button, ErrorNote, Loading, ResultBadge, RiskTag, Stamp, fmtDate } from '../ui'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-rule pt-8">
      <h2 className="m-0 mb-4 text-xl font-semibold">{title}</h2>
      {children}
    </section>
  )
}

export default function AuditPackage() {
  const id = Number(useParams().id)
  const [pkg, setPkg] = useState<Pkg | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.audit(id).then(setPkg, setError) }, [id])

  async function download(kind: 'md' | 'json') {
    try {
      if (kind === 'md') saveBlob(new Blob([await api.auditMarkdown(id)], { type: 'text/markdown' }), `audit-review-${id}.md`)
      else saveBlob(new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' }), `audit-review-${id}.json`)
    } catch (e) { setError(e) }
  }

  if (error && !pkg) return <ErrorNote error={error} />
  if (!pkg) return <Loading label="Assembling package" />
  const es = pkg.executive_summary

  return (
    <article className="space-y-10">
      <header>
        <p className="m-0 text-sm text-ink-soft">
          <Link to="/reviews" className="text-pen hover:underline">Reviews</Link> /{' '}
          <Link to={`/reviews/${id}`} className="text-pen hover:underline">#{id}</Link> / Audit package
        </p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="m-0 text-3xl font-semibold tracking-tight">Audit package: {pkg.title}</h1>
            <p className="mt-1 mb-0 text-sm text-ink-soft">Generated {fmtDate(pkg.generated_at)}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => download('md')}>Download Markdown</Button>
            <Button variant="secondary" onClick={() => download('json')}>Download JSON</Button>
          </div>
        </div>
        <p className="mt-6 max-w-3xl rounded-md bg-paper px-4 py-3 text-sm text-ink-soft ring-1 ring-rule">{pkg.disclaimer}</p>
      </header>

      <Section title="Executive summary">
        <blockquote className="m-0 border-l-4 border-ink pl-5 font-serif text-lg">{es.request}</blockquote>
        <dl className="mt-5 grid max-w-3xl grid-cols-[9rem_1fr] gap-y-2 text-sm">
          <dt className="text-ink-soft">Submitted by</dt><dd className="m-0">{es.submitted_by}</dd>
          <dt className="text-ink-soft">Result</dt><dd className="m-0"><ResultBadge result={es.result} /></dd>
          <dt className="text-ink-soft">Status</dt><dd className="m-0 capitalize">{es.status}</dd>
          {es.final_decision && <><dt className="text-ink-soft">Final decision</dt>
            <dd className="m-0">{es.final_decision.action} by {es.final_decision.reviewer}: {es.final_decision.comment || 'no comment'}</dd></>}
        </dl>
        <p className="mt-4 mb-0 max-w-3xl">{es.summary}</p>
      </Section>

      <Section title="Control matrix">
        <div className="overflow-x-auto rounded-lg bg-paper ring-1 ring-rule">
          <table className="w-full min-w-[860px] border-collapse text-left text-sm">
            <thead className="border-b border-rule text-ink-soft">
              <tr>{['Status', 'Citation', 'Policy text', 'Interpretation', 'Evidence'].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {pkg.control_matrix.map((m) => (
                <tr key={m.requirement} className="border-b border-rule align-top last:border-0">
                  <td className="px-4 py-3"><Stamp status={m.status} size="sm" /><span className="mt-2 block"><RiskTag risk={m.risk} /></span></td>
                  <td className="px-4 py-3 font-serif text-pen">{m.citation}<span className="block font-sans text-xs text-ink-soft">{m.requirement}</span></td>
                  <td className="policy-text max-w-xs px-4 py-3 !text-[0.95rem]">{m.policy_text}</td>
                  <td className="max-w-xs px-4 py-3 text-ink-soft">{m.interpretation}</td>
                  <td className="px-4 py-3">{m.evidence.join(', ') || <span className="text-ink-soft">none</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-10 lg:grid-cols-2">
        <Section title="Evidence references">
          {pkg.evidence_references.length ? (
            <ul className="m-0 list-none space-y-2 p-0 text-sm">
              {pkg.evidence_references.map((e) => (
                <li key={e.id}><span className="font-semibold">{e.id}</span> {e.filename} <span className="text-ink-soft">({e.type}, sha256 {e.sha256.slice(0, 16)})</span></li>
              ))}
            </ul>
          ) : <p className="m-0 text-ink-soft">No evidence was attached.</p>}
        </Section>
        <Section title="Open questions">
          {pkg.open_questions.length ? (
            <ul className="m-0 list-disc space-y-2 pl-5 text-sm">{pkg.open_questions.map((q) => <li key={q}>{q}</li>)}</ul>
          ) : <p className="m-0 text-ink-soft">None.</p>}
          {pkg.evidence_requested.length > 0 && <p className="mt-4 mb-0 text-sm"><span className="font-semibold">Evidence requested:</span> {pkg.evidence_requested.join(', ')}</p>}
        </Section>
      </div>

      <Section title="Risk register">
        {pkg.risk_register.length ? (
          <ul className="m-0 list-none divide-y divide-rule rounded-lg bg-paper p-0 ring-1 ring-rule">
            {pkg.risk_register.map((r) => (
              <li key={r.requirement} className="flex flex-wrap items-start gap-x-4 gap-y-1 px-4 py-3 text-sm">
                <Stamp status={r.status} size="sm" />
                <RiskTag risk={r.risk} />
                <span className="font-serif text-pen">{r.citation}</span>
                <span className="basis-full text-ink-soft">{r.issue}</span>
              </li>
            ))}
          </ul>
        ) : <p className="m-0 text-ink-soft">No open risks.</p>}
      </Section>

      <div className="grid gap-10 lg:grid-cols-2">
        <Section title="Reviewer checklist">
          <ul className="m-0 list-none space-y-2 p-0 text-sm">
            {pkg.reviewer_checklist.map((c) => (
              <li key={c.item} className="flex gap-3">
                <span aria-hidden className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-sm border ${c.done ? 'border-pass bg-pass text-white' : 'border-ink-soft'}`}>{c.done ? '✓' : ''}</span>
                <span>{c.item}<span className="sr-only">{c.done ? ' (done)' : ' (not done)'}</span></span>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="Decision history">
          {pkg.decision_history.length ? (
            <ol className="m-0 list-none space-y-2 p-0 text-sm">
              {pkg.decision_history.map((d) => <li key={d.at}><span className="font-semibold">{d.action}</span> by {d.reviewer}, {fmtDate(d.at)}{d.comment && `: ${d.comment}`}</li>)}
            </ol>
          ) : <p className="m-0 text-ink-soft">No decision recorded yet.</p>}
        </Section>
      </div>
    </article>
  )
}
