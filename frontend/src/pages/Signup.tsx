import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { PasswordRules, passwordOk } from '../PasswordRules'
import { Button, ErrorNote, Field, inputClass } from '../ui'

export default function Signup() {
  const { adopt } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ display_name: '', username: '', email: '', password: '', confirm: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })
  const mismatch = form.confirm.length > 0 && form.confirm !== form.password

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (form.password !== form.confirm) return setError(new Error('The two passwords don’t match.'))
    setBusy(true)
    setError(null)
    try {
      adopt(await api.register({ username: form.username.trim().toLowerCase(), password: form.password,
        display_name: form.display_name, email: form.email }))
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-12 sm:px-6">
      <h1 className="m-0 text-3xl font-semibold tracking-tight">Create your account</h1>
      <p className="mt-2 text-ink-soft">
        New accounts can submit changes for review. An administrator can make you a reviewer.
      </p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Full name">
          <input className={inputClass} value={form.display_name} onChange={set('display_name')} autoComplete="name" />
        </Field>
        <Field label="Username" hint="3–32 characters: lowercase letters, numbers, dots, dashes or underscores.">
          <input className={inputClass} value={form.username} onChange={set('username')} autoComplete="username"
            required minLength={3} maxLength={32} pattern="[a-zA-Z0-9][a-zA-Z0-9._\-]{2,31}" />
        </Field>
        <Field label="Work email" hint="Optional.">
          <input className={inputClass} type="email" value={form.email} onChange={set('email')} autoComplete="email" />
        </Field>
        <Field label="Password">
          <input className={inputClass} type="password" value={form.password} onChange={set('password')}
            autoComplete="new-password" required />
          <PasswordRules password={form.password} username={form.username} />
        </Field>
        <Field label="Confirm password">
          <input className={inputClass} type="password" value={form.confirm} onChange={set('confirm')}
            autoComplete="new-password" required aria-invalid={mismatch} />
          {mismatch && <span className="mt-1 block text-sm text-fail">Passwords don’t match yet.</span>}
        </Field>
        <ErrorNote error={error} />
        <Button type="submit" busy={busy} className="w-full"
          disabled={!passwordOk(form.password, form.username) || form.password !== form.confirm}>
          Create account
        </Button>
        <p className="text-center text-sm text-ink-soft">
          Already have an account? <Link to="/login" className="font-semibold text-pen hover:underline">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
