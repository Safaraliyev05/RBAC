import { useEffect, useState } from 'react'
import { auditApi } from '@/api/audit'
import type { AuditSummaryReport } from '@/types'
import Alert from '@/components/ui/Alert'
import { extractErrors } from '@/utils/errors'

export default function AuditReportsPage() {
  const [report, setReport] = useState<AuditSummaryReport | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  const fetchReport = async () => {
    setLoading(true)
    setErrors([])
    try {
      const { data } = await auditApi.getSummaryReport(days)
      setReport(data)
    } catch (err) { setErrors(extractErrors(err)) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchReport() }, [days])

  const resultColor = (result: string) => {
    const map: Record<string, string> = {
      success: 'text-green-600',
      failure: 'text-red-600',
      denied: 'text-yellow-600',
      locked: 'text-orange-600',
    }
    return map[result] ?? 'text-gray-600'
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Security Reports</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-500">Period:</label>
          <select className="input w-32" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      {errors.length > 0 && <Alert type="error" message={errors} className="mb-4" />}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading report...</div>
      ) : !report ? null : (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card p-5 text-center">
              <div className="text-3xl font-bold text-brand-600">{report.total_events.toLocaleString()}</div>
              <div className="text-sm text-gray-500 mt-1">Total Events</div>
            </div>
            {Object.entries(report.by_result).map(([result, count]) => (
              <div key={result} className="card p-5 text-center">
                <div className={`text-3xl font-bold ${resultColor(result)}`}>{count.toLocaleString()}</div>
                <div className="text-sm text-gray-500 mt-1 capitalize">{result}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Actions */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 mb-4">Top Actions</h2>
              <div className="space-y-2">
                {report.top_actions.map((item) => (
                  <div key={item.action} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-700">{item.action}</span>
                    <span className="badge-gray">{item.count}</span>
                  </div>
                ))}
                {report.top_actions.length === 0 && <p className="text-gray-400 text-sm">No data</p>}
              </div>
            </div>

            {/* Denied by User */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 mb-4">Top Denied Access (by User)</h2>
              <div className="space-y-2">
                {report.denied_access_by_user.map((item) => (
                  <div key={item.user_email} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{item.user_email || 'Anonymous'}</span>
                    <span className="badge-yellow">{item.count} denied</span>
                  </div>
                ))}
                {report.denied_access_by_user.length === 0 && <p className="text-gray-400 text-sm">No denied access events</p>}
              </div>
            </div>

            {/* Login Failures by Day */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 mb-4">Login Failures by Day</h2>
              <div className="space-y-2">
                {report.login_failures_by_day.map((item) => (
                  <div key={item.day} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{item.day}</span>
                    <div className="flex items-center gap-2">
                      <div className="bg-red-200 h-2 rounded" style={{ width: `${Math.min(item.count * 10, 120)}px` }} />
                      <span className="badge-red text-xs">{item.count}</span>
                    </div>
                  </div>
                ))}
                {report.login_failures_by_day.length === 0 && <p className="text-gray-400 text-sm">No login failures in this period</p>}
              </div>
            </div>

            {/* Suspicious IPs */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 mb-4">Top Suspicious IPs</h2>
              <div className="space-y-2">
                {report.top_suspicious_ips.map((item) => (
                  <div key={item.ip_address} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-700">{item.ip_address || 'Unknown'}</span>
                    <span className="badge-red">{item.count} failures/denials</span>
                  </div>
                ))}
                {report.top_suspicious_ips.length === 0 && <p className="text-gray-400 text-sm">No suspicious IPs detected</p>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
