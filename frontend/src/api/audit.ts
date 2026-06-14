import api from './axios'
import type { AccessLog, AuditSummaryReport, PaginatedResponse } from '@/types'

export const auditApi = {
  getLogs: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<AccessLog>>('/audit/logs/', { params }),

  getExportUrl: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return `/api/audit/logs/export/${qs}`
  },

  getSummaryReport: (days?: number) =>
    api.get<AuditSummaryReport>('/audit/reports/summary/', { params: days ? { days } : undefined }),

  getLoginFailures: (days?: number) =>
    api.get('/audit/reports/login-failures/', { params: days ? { days } : undefined }),
}
