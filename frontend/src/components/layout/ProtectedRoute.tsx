import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredPermission?: string
  requiredRole?: string
  fallback?: string
}

export default function ProtectedRoute({
  children,
  requiredPermission,
  requiredRole,
  fallback = '/login',
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, hasPermission, hasRole } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to={fallback} state={{ from: location }} replace />
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/403" replace />
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <Navigate to="/403" replace />
  }

  return <>{children}</>
}
