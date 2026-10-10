import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import { Button, ErrorNote, Field, inputClass } from '../ui'

const DEMO = [
  { username: 'alice', role: 'Engineer', does: 'submits changes and evidence' },
  { username: 'rita', role: 'Reviewer', does: 'approves, rejects or returns' },
  { username: 'admin', role: 'Admin', does: 'everything, including policies' },
]

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(username, password)
      navigate(params.get('next') || '/dashboard', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-12 px-4 py-12 sm:px-6 md:grid-cols-2">
      <div>
        <h1 className="m-0 text-3xl font-semibold tracking-tight">Sign in</h1>
        {params.get('expired') && <p className="mt-3 text-sm text-unknown">Your session expired. Sign in again to continue.</p>}
        <form onSubmit={submit} className="mt-8 space-y-5">
          <Field label="Username">
            <input className={inputClass} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </Field>
          <Field label="Password">
            <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </Field>
          <ErrorNote error={error} />
          <Button type="submit" busy={busy} className="w-full">Sign in</Button>
          <p className="text-center text-sm text-ink-soft">
            New to PolicyLens? <Link to="/signup" className="font-semibold text-pen hover:underline">Create an account</Link>
          </p>
          <p className="text-center text-xs text-ink-soft">Forgot your password? Ask an administrator to reset it from the Users page.</p>
        </form>
      </div>
      <aside className="rounded-lg border border-rule bg-paper p-6">
        <h2 className="m-0 text-base font-semibold">Demo accounts</h2>
        <p className="mt-1 text-sm text-ink-soft">Shared accounts for trying PolicyLens. The password for each is <code className="rounded bg-vellum px-1">policylens</code>; demo passwords can’t be changed.</p>
        <ul className="m-0 mt-4 list-none space-y-2 p-0">
          {DEMO.map((d) => (
            <li key={d.username}>
              <button
                type="button"
                onClick={() => { setUsername(d.username); setPassword('policylens') }}
                className="w-full rounded-md border border-rule px-3 py-2 text-left hover:border-pen"
              >
                <span className="font-semibold">{d.username}</span>
                <span className="text-ink-soft">, {d.role.toLowerCase()}: {d.does}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
