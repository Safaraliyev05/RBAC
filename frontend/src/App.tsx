import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/layout/ProtectedRoute'
import AppLayout from '@/components/layout/AppLayout'

import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import ProfilePage from '@/pages/ProfilePage'
import ForbiddenPage from '@/pages/ForbiddenPage'
import UsersPage from '@/pages/admin/UsersPage'
import RolesPage from '@/pages/admin/RolesPage'
import PermissionsPage from '@/pages/admin/PermissionsPage'
import AuditLogsPage from '@/pages/audit/AuditLogsPage'
import AuditReportsPage from '@/pages/audit/AuditReportsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/403" element={<ForbiddenPage />} />

          {/* Authenticated routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />

            {/* Admin routes */}
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute requiredPermission="users.read">
                  <UsersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/roles"
              element={
                <ProtectedRoute requiredPermission="roles.read">
                  <RolesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/permissions"
              element={
                <ProtectedRoute requiredPermission="permissions.read">
                  <PermissionsPage />
                </ProtectedRoute>
              }
            />

            {/* Audit routes */}
            <Route
              path="/audit/logs"
              element={
                <ProtectedRoute requiredPermission="audit.read">
                  <AuditLogsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit/reports"
              element={
                <ProtectedRoute requiredPermission="reports.view">
                  <AuditReportsPage />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
