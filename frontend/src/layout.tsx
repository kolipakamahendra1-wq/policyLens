import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './auth'

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-ink no-underline">
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
            <li><Link className="text-ink-soft hover:text-ink" to="/reviews">Reviews</Link></li>
            <li><Link className="text-ink-soft hover:text-ink" to="/policies">Policy library</Link></li>
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
            <Link to="/reviews" className="rounded-md bg-ink px-3.5 py-2 font-semibold text-vellum hover:bg-ink/90">Open reviews</Link>
          ) : (
            <Link to="/login" className="rounded-md bg-ink px-3.5 py-2 font-semibold text-vellum hover:bg-ink/90">Sign in</Link>
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

export function AppLayout() {
  const { session, signOut } = useAuth()
  const location = useLocation()
  if (!session) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-rule bg-vellum/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-6">
            <Logo />
            <nav className="flex gap-1" aria-label="App">
              <NavLink to="/reviews" className={navCls}>Reviews</NavLink>
              <NavLink to="/policies" className={navCls}>Policies</NavLink>
              {session.role !== 'engineer' && <NavLink to="/activity" className={navCls}>Activity</NavLink>}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-ink-soft">
              <span className="font-semibold text-ink">{session.username}</span>, {session.role}
            </span>
            <button onClick={signOut} className="rounded-md px-2 py-1 text-pen hover:bg-pen/10">Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pt-10 sm:px-6"><Outlet /></main>
      <Footer />
    </div>
  )
}
