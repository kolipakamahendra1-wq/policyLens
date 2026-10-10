import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider } from './auth'
import { AppLayout, PublicLayout } from './layout'
import Activity from './pages/Activity'
import AuditPackage from './pages/AuditPackage'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import NewReview from './pages/NewReview'
import { Policies, PolicyView } from './pages/Policies'
import ReviewDetail from './pages/ReviewDetail'
import Reviews from './pages/Reviews'
import Settings from './pages/Settings'
import Signup from './pages/Signup'
import Users from './pages/Users'

function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <h1 className="m-0 text-3xl font-semibold">This page doesn’t exist</h1>
      <p className="mt-2 text-ink-soft">Check the address, or go back to your dashboard.</p>
      <Link to="/dashboard" className="mt-6 inline-block rounded-md bg-pen px-4 py-2 font-semibold text-white">Go to dashboard</Link>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route index element={<Landing />} />
            <Route path="login" element={<Login />} />
            <Route path="signup" element={<Signup />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          <Route element={<AppLayout />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="reviews" element={<Reviews />} />
            <Route path="reviews/new" element={<NewReview />} />
            <Route path="reviews/:id" element={<ReviewDetail />} />
            <Route path="reviews/:id/audit" element={<AuditPackage />} />
            <Route path="policies" element={<Policies />} />
            <Route path="policies/:id" element={<PolicyView />} />
            <Route path="activity" element={<Activity />} />
            <Route path="settings" element={<Navigate to="/settings/profile" replace />} />
            <Route path="settings/:section" element={<Settings />} />
            <Route path="admin/users" element={<Users />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
