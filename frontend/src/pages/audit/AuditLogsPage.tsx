import { useEffect, useState } from 'react'
import { auditApi } from '@/api/audit'
import { tokenStorage } from '@/api/axios'
import type { AccessLog, AuditResult } from '@/types'
import Alert from '@/components/ui/Alert'
import Pagination from '@/components/ui/Pagination'
import { extractErrors } from '@/utils/errors'

const PAGE_SIZE = 20

const resultBadge = (result: AuditResult) => {
  const map = { success: 'badge-green', failure: 'badge-red', denied: 'badge-yellow', locked: 'badge-yellow' }
  return <span className={map[result] ?? 'badge-gray'}>{result}</span>
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AccessLog[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  const [filters, setFilters] = useState({
    user_email: '', action: '', result: '' as AuditResult | '',
    date_from: '', date_to: '', ip_address: '', path: '',
  })

  const fetchLogs = async () => {
    setLoading(true)
    setErrors([])
    try {
      const params: Record<string, unknown> = { page, page_size: PAGE_SIZE }
      for (const [k, v] of Object.entries(filters)) {
        if (v) params[k] = v
      }
      const { data } = await auditApi.getLogs(params)
      setLogs(data.results)
      setCount(data.count)
    } catch (err) { setErrors(extractErrors(err)) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchLogs() }, [page, filters])

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const handleExport = () => {
    const params: Record<string, string> = {}
    for (const [k, v] of Object.entries(filters)) {
      if (v) params[k] = v
    }
    const token = tokenStorage.getAccess()
    // Build URL with access token as query param for download link
    const qs = new URLSearchParams(params).toString()
    const url = `/api/audit/logs/export/${qs ? '?' + qs : ''}`
    // Create a temporary link with Authorization header workaround via fetch
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`
        a.click()
      })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <button className="btn-secondary" onClick={handleExport}>Export CSV</button>
      </div>

      {errors.length > 0 && <Alert type="error" message={errors} className="mb-4" />}

      {/* Filters */}
      <div className="card p-4 mb-4">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <div>
            <label className="label">User Email</label>
            <input className="input" value={filters.user_email}
              onChange={(e) => handleFilterChange('user_email', e.target.value)}
              placeholder="Filter by email..." />
          </div>
          <div>
            <label className="label">Action</label>
            <input className="input" value={filters.action}
              onChange={(e) => handleFilterChange('action', e.target.value)}
              placeholder="e.g. login, users.read" />
          </div>
          <div>
            <label className="label">Result</label>
            <select className="input" value={filters.result}
              onChange={(e) => handleFilterChange('result', e.target.value)}>
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="denied">Denied</option>
              <option value="locked">Locked</option>
            </select>
          </div>
          <div>
            <label className="label">IP Address</label>
            <input className="input" value={filters.ip_address}
              onChange={(e) => handleFilterChange('ip_address', e.target.value)}
              placeholder="Filter by IP..." />
          </div>
          <div>
            <label className="label">From</label>
            <input className="input" type="datetime-local" value={filters.date_from}
              onChange={(e) => handleFilterChange('date_from', e.target.value)} />
          </div>
          <div>
            <label className="label">To</label>
            <input className="input" type="datetime-local" value={filters.date_to}
              onChange={(e) => handleFilterChange('date_to', e.target.value)} />
          </div>
          <div>
            <label className="label">Path</label>
            <input className="input" value={filters.path}
              onChange={(e) => handleFilterChange('path', e.target.value)}
              placeholder="e.g. /api/rbac/" />
          </div>
          <div className="flex items-end">
            <button className="btn-secondary w-full"
              onClick={() => { setFilters({ user_email: '', action: '', result: '', date_from: '', date_to: '', ip_address: '', path: '' }); setPage(1) }}>
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-3 py-3 text-left font-medium text-gray-500">Timestamp</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">User</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">Action</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">Resource</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">Result</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">IP</th>
                <th className="px-3 py-3 text-left font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No logs found.</td></tr>
              ) : logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-xs">{log.user_email || log.user_display || '—'}</div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{log.action}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{log.resource || '—'}</td>
                  <td className="px-3 py-2">{resultBadge(log.result)}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{log.ip_address || '—'}</td>
                  <td className="px-3 py-2 text-xs">{log.status_code || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination count={count} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>
    </div>
  )
}
