import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'

export function Logo({ to = '/' }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2 text-ink no-underline">
      <span aria-hidden className="grid h-8 w-8 place-items-center rounded-md bg-ink font-serif text-xl text-vellum">§</span>
      <span className="text-lg font-semibold tracking-tight">PolicyLens</span>
    </Link>
  )
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-6 px-4 py-10 text-sm text-ink-soft sm:px-6">
        <div className="max-w-sm">
          <Logo />
          <p className="mt-3">
            Checks engineering changes against your policies and prepares the evidence. A person always makes the final call.
          </p>
        </div>
        <nav className="flex gap-10" aria-label="Footer">
          <ul className="m-0 list-none space-y-2 p-0">
            <li><Link className="text-ink-soft hover:text-ink" to="/#how-it-works">How it works</Link></li>
            <li><Link className="text-ink-soft hover:text-ink" to="/#guardrails">Guardrails</Link></li>
          </ul>
          <ul className="m-0 list-none space-y-2 p-0">
            <li><Link className="text-ink-soft hover:text-ink" to="/dashboard">Dashboard</Link></li>
            <li><Link className="text-ink-soft hover:text-ink" to="/reviews">Reviews</Link></li>
            <li><Link className="text-ink-soft hover:text-ink" to="/policies">Policy library</Link></li>
            <li><Link className="text-ink-soft hover:text-ink" to="/settings/profile">Account settings</Link></li>
          </ul>
        </nav>
      </div>
    </footer>
  )
}

export function PublicLayout() {
  const { session } = useAuth()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-1 text-sm sm:gap-4" aria-label="Main">
          <a href="/#how-it-works" className="hidden px-2 py-1 text-ink-soft hover:text-ink sm:inline">How it works</a>
          <a href="/#guardrails" className="hidden px-2 py-1 text-ink-soft hover:text-ink sm:inline">Guardrails</a>
          {session ? (
            <Link to="/dashboard" className="rounded-md bg-ink px-3.5 py-2 font-semibold text-vellum hover:bg-ink/90">Go to dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="px-2 py-1 font-medium text-ink hover:text-pen">Sign in</Link>
              <Link to="/signup" className="rounded-md bg-ink px-3.5 py-2 font-semibold text-vellum hover:bg-ink/90">Create account</Link>
            </>
          )}
        </nav>
      </header>
      <main className="flex-1"><Outlet /></main>
      <Footer />
    </div>
  )
}

const navCls = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-ink text-vellum' : 'text-ink-soft hover:bg-rule/50 hover:text-ink'}`

function UserMenu() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close) }
  }, [open])

  if (!session) return null
  const initials = session.username.slice(0, 2).toUpperCase()
  const item = 'block w-full rounded px-3 py-2 text-left text-sm text-ink hover:bg-vellum'
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full py-1 pr-3 pl-1 text-sm hover:bg-rule/50"
      >
        <span aria-hidden className="grid h-8 w-8 place-items-center rounded-full bg-pen text-xs font-semibold text-white">{initials}</span>
        <span className="hidden text-left leading-tight sm:block">
          <span className="block font-semibold">{session.username}</span>
          <span className="block text-xs text-ink-soft capitalize">{session.role}</span>
        </span>
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-20 mt-2 w-56 rounded-lg border border-rule bg-paper p-1 shadow-lg">
          <Link role="menuitem" to="/dashboard" className={item} onClick={() => setOpen(false)}>Dashboard</Link>
          <Link role="menuitem" to="/settings/profile" className={item} onClick={() => setOpen(false)}>Account settings</Link>
          <Link role="menuitem" to="/settings/password" className={item} onClick={() => setOpen(false)}>Change password</Link>
          <div className="my-1 border-t border-rule" />
          <button role="menuitem" className={`${item} text-fail`} onClick={() => { signOut(); navigate('/login') }}>Sign out</button>
        </div>
      )}
    </div>
  )
}

export function AppLayout() {
  const { session } = useAuth()
  const location = useLocation()
  if (!session) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-rule bg-vellum/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Logo to="/dashboard" />
            <nav className="flex flex-wrap gap-1" aria-label="App">
              <NavLink to="/dashboard" className={navCls}>Dashboard</NavLink>
              <NavLink to="/reviews" className={navCls}>Reviews</NavLink>
              <NavLink to="/policies" className={navCls}>Policies</NavLink>
              {session.role !== 'engineer' && <NavLink to="/activity" className={navCls}>Activity</NavLink>}
              {session.role === 'admin' && <NavLink to="/admin/users" className={navCls}>Users</NavLink>}
            </nav>
          </div>
          <UserMenu />
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pt-10 sm:px-6"><Outlet /></main>
      <Footer />
    </div>
  )
}
