import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'
import type { Status } from './api'

export const STATUS: Record<Status, { label: string; color: string; meaning: string }> = {
  PASS: { label: 'Pass', color: 'var(--color-pass)', meaning: 'Evidence shows the requirement is met.' },
  FAIL: { label: 'Fail', color: 'var(--color-fail)', meaning: 'Evidence shows the requirement is not met.' },
  UNKNOWN: { label: 'Unknown', color: 'var(--color-unknown)', meaning: 'Not enough evidence to decide.' },
  NEEDS_HUMAN_REVIEW: { label: 'Needs human review', color: 'var(--color-human)', meaning: 'High-risk or ambiguous; a reviewer must decide.' },
}

export function Stamp({ status, animate, delay = 0, size = 'md' }: { status: Status; animate?: boolean; delay?: number; size?: 'sm' | 'md' }) {
  const s = STATUS[status]
  const style: CSSProperties = { color: s.color, borderColor: s.color, animationDelay: `${delay}ms` }
  return (
    <span
      title={s.meaning}
      style={style}
      className={`inline-block whitespace-nowrap rounded-[4px] border-2 font-semibold tracking-wide [box-shadow:inset_0_0_0_1px_currentColor] ${
        size === 'sm' ? 'px-1.5 py-0 text-xs' : 'px-2.5 py-0.5 text-sm'
      } ${animate ? 'stamp-in' : '-rotate-2'}`}
    >
      {s.label}
    </span>
  )
}

export function ResultBadge({ result }: { result: string | null }) {
  if (!result) return <span className="text-sm text-ink-soft">Not evaluated</span>
  const ok = result === 'Compliant'
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${ok ? 'text-pass' : 'text-human'}`}>
      <span aria-hidden className={`h-2 w-2 rounded-full ${ok ? 'bg-pass' : 'bg-human'}`} />
      {result}
    </span>
  )
}

/** Verbatim policy text: serif, with its citation hung in the margin. */
export function PolicyQuote({ citation, children, policy }: { citation: string; policy?: string; children: ReactNode }) {
  return (
    <figure className="m-0 grid grid-cols-[5.5rem_1fr] gap-3 sm:grid-cols-[7rem_1fr]">
      <figcaption className="pt-1 text-right font-serif text-sm leading-tight text-pen">
        {citation}
        {policy && <span className="mt-1 block font-sans text-xs text-ink-soft">{policy}</span>}
      </figcaption>
      <blockquote className="policy-text m-0 border-l-2 border-pen/40 pl-4">{children}</blockquote>
    </figure>
  )
}

/** Model-generated reading, visually distinct from policy text. */
export function Interpretation({ children, source }: { children: ReactNode; source?: string }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-3 sm:grid-cols-[7rem_1fr]">
      <div className="pt-0.5 text-right text-xs text-ink-soft">PolicyLens reading{source ? <span className="block">{source}</span> : null}</div>
      <p className="m-0 text-[0.95rem] leading-relaxed text-ink-soft">{children}</p>
    </div>
  )
}

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
export function Button({ variant = 'primary', busy, children, className = '', ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: 'bg-pen text-white hover:bg-pen-dark',
    secondary: 'bg-paper text-ink border border-rule hover:border-ink-soft',
    ghost: 'text-pen hover:bg-pen/10',
    danger: 'bg-paper text-fail border border-fail/40 hover:bg-fail/5',
  }
  return (
    <button
      {...rest}
      disabled={rest.disabled || busy}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
    >
      {busy && <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm font-semibold">{label}</span>
      {hint && <span className="mt-0.5 block text-sm text-ink-soft">{hint}</span>}
      <span className="mt-1.5 block">{children}</span>
    </label>
  )
}

export const inputClass =
  'w-full rounded-md border border-rule bg-paper px-3 py-2 text-[0.95rem] text-ink placeholder:text-ink-soft/60 focus:border-pen focus:outline-none'

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  const msg = error instanceof Error ? error.message : String(error)
  return <p role="alert" className="rounded-md border border-fail/30 bg-fail/5 px-3 py-2 text-sm text-fail">{msg}</p>
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return <p className="py-10 text-center text-sm text-ink-soft" aria-live="polite">{label}…</p>
}

export function PageTitle({ title, children, lead }: { title: string; lead?: string; children?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="m-0 text-3xl font-semibold tracking-tight">{title}</h1>
        {lead && <p className="mt-2 text-ink-soft">{lead}</p>}
      </div>
      {children}
    </div>
  )
}

export function RiskTag({ risk }: { risk: string }) {
  const cls = risk === 'high' ? 'text-fail' : risk === 'medium' ? 'text-unknown' : 'text-ink-soft'
  return <span className={`text-xs font-semibold ${cls}`}>{risk} risk</span>
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
