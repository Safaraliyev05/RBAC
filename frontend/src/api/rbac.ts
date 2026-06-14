import api from './axios'
import type { AdminUser, PaginatedResponse, Permission, Role, SyncResult, UserRoleEntry } from '@/types'

// ─── Permissions ──────────────────────────────────────────────────────────────
export const permissionsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Permission>>('/rbac/permissions/', { params }),

  sync: (prune = false) =>
    api.post<SyncResult>('/rbac/permissions/sync/', { prune }),
}

// ─── Roles ────────────────────────────────────────────────────────────────────
export const rolesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Role>>('/rbac/roles/', { params }),

  get: (id: number) =>
    api.get<Role>(`/rbac/roles/${id}/`),

  create: (data: { name: string; description?: string; permission_ids?: number[] }) =>
    api.post<Role>('/rbac/roles/', data),

  update: (id: number, data: Partial<{ name: string; description: string; permission_ids: number[] }>) =>
    api.patch<Role>(`/rbac/roles/${id}/`, data),

  delete: (id: number) =>
    api.delete(`/rbac/roles/${id}/`),
}

// ─── Admin Users ──────────────────────────────────────────────────────────────
export const adminUsersApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<AdminUser>>('/rbac/users/', { params }),

  get: (id: number) =>
    api.get<AdminUser>(`/rbac/users/${id}/`),

  create: (data: {
    email: string
    first_name: string
    last_name: string
    password: string
    is_active?: boolean
    is_staff?: boolean
    role_ids?: number[]
  }) => api.post<AdminUser>('/rbac/users/', data),

  update: (id: number, data: Partial<{ first_name: string; last_name: string; is_active: boolean; is_staff: boolean }>) =>
    api.patch<AdminUser>(`/rbac/users/${id}/`, data),

  delete: (id: number) =>
    api.delete(`/rbac/users/${id}/`),

  assignRoles: (id: number, role_ids: number[], replace = false) =>
    api.post(`/rbac/users/${id}/assign-roles/`, { role_ids, replace }),

  getRoles: (id: number) =>
    api.get<UserRoleEntry[]>(`/rbac/users/${id}/roles/`),

  removeRole: (userId: number, roleId: number) =>
    api.delete(`/rbac/users/${userId}/roles/${roleId}/remove/`),
}
