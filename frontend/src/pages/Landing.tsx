import { Link } from 'react-router-dom'
import { Interpretation, PolicyQuote, STATUS, Stamp } from '../ui'
import type { Status } from '../api'

const SPECIMEN: { finding: string; citation: string; status: Status }[] = [
  { finding: 'Data retention period not specified', citation: 'DATA-RET §2', status: 'UNKNOWN' },
  { finding: 'Encryption at rest with managed keys', citation: 'SEC-CRYPTO §1', status: 'PASS' },
  { finding: 'Access-control evidence missing', citation: 'SEC-ACCESS §2.1', status: 'UNKNOWN' },
  { finding: 'Audit logging of record access', citation: 'SEC-LOG §1', status: 'PASS' },
]

const STEPS = [
  { name: 'Submit', body: 'Describe the change and attach what you already have: configs, API specs, architecture docs, screenshots.' },
  { name: 'Match', body: 'PolicyLens finds the policies that apply and pulls the exact sections, each with its citation.' },
  { name: 'Evaluate', body: 'Every requirement is checked against your evidence. Gaps turn into a specific list of what to provide.' },
  { name: 'Approve', body: 'A reviewer reads the findings and approves, rejects, or sends the request back with a note.' },
  { name: 'Package', body: 'The audit package is assembled: summary, control matrix, evidence, open questions, risks, checklist.' },
]

const GUARDRAILS = [
  ['No compliance without evidence', 'A requirement can only pass when a specific piece of attached evidence supports it.'],
  ['Policy text stays policy text', 'Quotes are verbatim from the cited section. The model’s reading is shown separately and labelled.'],
  ['Every finding is cited', 'Each status points to the policy, section and requirement it was judged against.'],
  ['Uncertain means Unknown', 'If the evidence doesn’t settle it, the answer is Unknown, not a guess.'],
  ['People decide high-risk calls', 'High-risk requirements without strong evidence are routed to a human reviewer.'],
  ['Read-only by design', 'The agent reads policies and evidence. It has no way to change production systems.'],
]

function SpecimenSheet() {
  return (
    <div className="relative">
      <div aria-hidden className="absolute inset-0 translate-x-3 translate-y-3 rounded-lg border border-rule bg-paper/60" />
      <article className="relative rounded-lg border border-rule bg-paper p-6 shadow-[0_1px_0_#d5dbe3] sm:p-8" aria-label="Example review">
        <header className="flex items-start justify-between gap-4 border-b border-rule pb-4">
          <div>
            <p className="m-0 text-xs text-ink-soft">Review #1042, submitted by alice</p>
            <p className="mt-2 mb-0 font-serif text-xl leading-snug">
              “We are deploying a new API that stores customer information.”
            </p>
          </div>
        </header>
        <p className="mt-4 mb-1 text-sm text-ink-soft">Policies checked</p>
        <p className="m-0 text-sm">Data classification, retention, access control, logging, deployment</p>
        <ul className="m-0 mt-5 list-none divide-y divide-rule p-0">
          {SPECIMEN.map((f, i) => (
            <li key={f.finding} className="flex items-center justify-between gap-4 py-3">
              <div>
                <p className="m-0 text-[0.95rem]">{f.finding}</p>
                <p className="m-0 font-serif text-sm text-pen">{f.citation}</p>
              </div>
              <Stamp status={f.status} animate delay={500 + i * 380} />
            </li>
          ))}
        </ul>
        <footer className="mt-4 rounded-md bg-vellum p-4 text-sm">
          <p className="m-0"><span className="font-semibold text-human">Needs review.</span> Evidence requested: IAM configuration, retention configuration, logging configuration.</p>
        </footer>
      </article>
    </div>
  )
}

export default function Landing() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-10 pb-20 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:pt-16">
        <div>
          <h1 className="m-0 text-4xl leading-[1.08] font-semibold tracking-tight sm:text-5xl">
            Know which policies a change touches, and what proves it complies.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">
            PolicyLens reads your security, privacy, retention and deployment policies, checks each requirement
            against the evidence an engineer attaches, and hands a reviewer a cited, decision-ready package.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/reviews/new" className="rounded-md bg-pen px-5 py-3 font-semibold text-white hover:bg-pen-dark">Start a review</Link>
            <Link to="/policies" className="rounded-md border border-rule bg-paper px-5 py-3 font-semibold text-ink hover:border-ink-soft">Browse the policy library</Link>
          </div>
        </div>
        <SpecimenSheet />
      </section>

      <section id="how-it-works" className="border-y border-rule bg-paper">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="m-0 max-w-xl text-3xl font-semibold tracking-tight">From change request to audit package in five steps</h2>
          <ol className="m-0 mt-12 grid list-none gap-8 p-0 sm:grid-cols-2 lg:grid-cols-5 lg:gap-6">
            {STEPS.map((s, i) => (
              <li key={s.name} className="border-t-2 border-ink pt-4">
                <span className="font-serif text-3xl text-pen">{i + 1}</span>
                <h3 className="mt-2 mb-0 text-lg font-semibold">{s.name}</h3>
                <p className="mt-2 mb-0 text-[0.95rem] leading-relaxed text-ink-soft">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="guardrails" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="grid gap-14 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <h2 className="m-0 text-3xl font-semibold tracking-tight">What the agent will and won’t do</h2>
            <dl className="mt-10 grid gap-x-8 gap-y-7 sm:grid-cols-2">
              {GUARDRAILS.map(([t, d]) => (
                <div key={t}>
                  <dt className="font-semibold">{t}</dt>
                  <dd className="m-0 mt-1 text-[0.95rem] leading-relaxed text-ink-soft">{d}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="self-start rounded-lg border border-rule bg-paper p-6 sm:p-8">
            <p className="m-0 mb-5 text-sm text-ink-soft">How a finding reads</p>
            <div className="space-y-5">
              <PolicyQuote citation="DATA-RET §2" policy="Data Retention Policy">
                Systems that store customer information must define a retention period and enforce it with an automated
                deletion or lifecycle rule.
              </PolicyQuote>
              <Interpretation source="qwen2.5:3b">
                No retention configuration was attached, so there is nothing to show a period is defined or enforced.
              </Interpretation>
              <div className="grid grid-cols-[5.5rem_1fr] gap-3 sm:grid-cols-[7rem_1fr]">
                <span />
                <div><Stamp status="UNKNOWN" /></div>
              </div>
            </div>
            <dl className="mt-8 grid gap-3 border-t border-rule pt-6">
              {(Object.keys(STATUS) as Status[]).map((s) => (
                <div key={s} className="flex items-start gap-3">
                  <dt className="w-36 shrink-0"><Stamp status={s} size="sm" /></dt>
                  <dd className="m-0 text-sm text-ink-soft">{STATUS[s].meaning}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-6 rounded-lg bg-ink px-8 py-10 text-vellum">
          <div className="max-w-xl">
            <h2 className="m-0 text-2xl font-semibold">Have a change going out this week?</h2>
            <p className="mt-2 mb-0 text-vellum/75">Describe it, attach what you have, and see which requirements still need evidence.</p>
          </div>
          <Link to="/reviews/new" className="rounded-md bg-vellum px-5 py-3 font-semibold text-ink hover:bg-white">Start a review</Link>
        </div>
      </section>
    </>
  )
}
