import { useAuth } from '@/contexts/AuthContext'
import { Link } from 'react-router-dom'

interface QuickLinkProps {
  to: string
  title: string
  description: string
  permission?: string
}

function QuickLink({ to, title, description, permission }: QuickLinkProps) {
  const { hasPermission } = useAuth()
  if (permission && !hasPermission(permission)) return null
  return (
    <Link to={to} className="card p-6 hover:shadow-md transition-shadow block group">
      <h3 className="font-semibold text-gray-900 group-hover:text-brand-600">{title}</h3>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
    </Link>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Welcome, {user?.first_name || user?.email}</h1>
        <p className="text-gray-500 mt-1">
          You are signed in as{' '}
          <span className="font-medium">{user?.email}</span>{' '}
          {user?.roles.length ? (
            <>with roles: {user.roles.map((r) => (
              <span key={r} className="badge-blue mx-0.5">{r}</span>
            ))}</>
          ) : 'with no roles assigned'}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <QuickLink to="/profile" title="My Profile" description="View and update your personal information" />
        <QuickLink
          to="/admin/users"
          title="User Management"
          description="Manage users, roles, and access"
          permission="users.read"
        />
        <QuickLink
          to="/admin/roles"
          title="Role Management"
          description="Define roles and assign permissions"
          permission="roles.read"
        />
        <QuickLink
          to="/audit/logs"
          title="Audit Logs"
          description="Review all system access events"
          permission="audit.read"
        />
        <QuickLink
          to="/audit/reports"
          title="Security Reports"
          description="Summary statistics and login failure analysis"
          permission="reports.view"
        />
      </div>

      <div className="mt-10 card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Your Permissions</h2>
        {user?.permissions.length ? (
          <div className="flex flex-wrap gap-2">
            {[...user.permissions].sort().map((p) => (
              <span key={p} className="badge-gray font-mono">{p}</span>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No permissions assigned.</p>
        )}
      </div>
    </div>
  )
}
