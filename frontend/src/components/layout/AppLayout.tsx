import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export default function AppLayout() {
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-brand-700 text-white'
        : 'text-blue-100 hover:bg-brand-700 hover:text-white'
    }`

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav */}
      <header className="bg-brand-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link to="/dashboard" className="text-xl font-bold tracking-tight">
                RBAC System
              </Link>
              <nav className="flex items-center gap-1">
                <NavLink to="/dashboard" className={navLinkClass}>
                  Dashboard
                </NavLink>
                <NavLink to="/profile" className={navLinkClass}>
                  Profile
                </NavLink>
                {hasPermission('users.read') && (
                  <NavLink to="/admin/users" className={navLinkClass}>
                    Users
                  </NavLink>
                )}
                {hasPermission('roles.read') && (
                  <NavLink to="/admin/roles" className={navLinkClass}>
                    Roles
                  </NavLink>
                )}
                {hasPermission('permissions.read') && (
                  <NavLink to="/admin/permissions" className={navLinkClass}>
                    Permissions
                  </NavLink>
                )}
                {hasPermission('audit.read') && (
                  <NavLink to="/audit/logs" className={navLinkClass}>
                    Audit Logs
                  </NavLink>
                )}
                {hasPermission('reports.view') && (
                  <NavLink to="/audit/reports" className={navLinkClass}>
                    Reports
                  </NavLink>
                )}
              </nav>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-blue-200 text-sm">{user?.email}</span>
              <div className="flex gap-1">
                {user?.roles.map((r) => (
                  <span key={r} className="badge bg-brand-600 text-blue-100 text-xs">
                    {r}
                  </span>
                ))}
              </div>
              <button
                onClick={handleLogout}
                className="btn-secondary btn-sm text-gray-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        RBAC System — Secured with JWT + Role-Based Access Control
      </footer>
    </div>
  )
}
