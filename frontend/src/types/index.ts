// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenPair {
  access: string
  refresh: string
}

export interface AuthUser {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  is_staff: boolean
  date_joined: string
  last_login: string | null
  roles: string[]
  permissions: string[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  first_name: string
  last_name: string
  password: string
  password_confirm: string
}

export interface LoginResponse {
  access: string
  refresh: string
}

export interface RegisterResponse {
  user: AuthUser
  tokens: TokenPair
}

// ─── RBAC ─────────────────────────────────────────────────────────────────────
export interface Permission {
  id: number
  codename: string
  name: string
  resource: string
  action: string
  managed: boolean
}

export interface SyncResult {
  created: number
  updated: number
  pruned: number
  granted: number
  total: number
}

export interface Role {
  id: number
  name: string
  description: string
  permissions: Permission[]
  user_count: number
  created_at: string
  updated_at: string
}

export interface UserRoleEntry {
  id: number
  role: number
  role_name: string
  assigned_at: string
  assigned_by: number | null
}

export interface AdminUser {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  is_staff: boolean
  date_joined: string
  last_login: string | null
  failed_login_count: number
  lockout_until: string | null
  roles: Array<{ role__id: number; role__name: string }>
}

// ─── Audit ────────────────────────────────────────────────────────────────────
export type AuditResult = 'success' | 'failure' | 'denied' | 'locked'

export interface AccessLog {
  id: number
  user: number | null
  user_display: string
  user_email: string
  timestamp: string
  ip_address: string | null
  http_method: string
  path: string
  action: string
  resource: string
  result: AuditResult
  status_code: number | null
  details: string
}

export interface AuditSummaryReport {
  period_days: number
  since: string
  total_events: number
  by_result: Record<string, number>
  top_actions: Array<{ action: string; count: number }>
  denied_access_by_user: Array<{ user_email: string; count: number }>
  login_failures_by_day: Array<{ day: string; count: number }>
  top_suspicious_ips: Array<{ ip_address: string; count: number }>
}

// ─── Pagination ───────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ─── API Errors ───────────────────────────────────────────────────────────────
export interface ApiError {
  detail?: string
  [key: string]: unknown
}
