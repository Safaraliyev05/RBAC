import { useEffect, useMemo, useState } from 'react'
import { permissionsApi } from '@/api/rbac'
import type { Permission, SyncResult } from '@/types'
import Alert from '@/components/ui/Alert'
import { extractErrors } from '@/utils/errors'
import { useAuth } from '@/contexts/AuthContext'

export default function PermissionsPage() {
  const { hasPermission } = useAuth()
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [notice, setNotice] = useState<string>('')

  const canSync = hasPermission('permissions.sync')

  const fetchPermissions = async () => {
    setLoading(true)
    try {
      const { data } = await permissionsApi.list({ page_size: 500, ordering: 'resource' })
      setPermissions(data.results)
    } catch (err) { setErrors(extractErrors(err)) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchPermissions() }, [])

  const handleSync = async () => {
    setSyncing(true)
    setErrors([])
    setNotice('')
    try {
      const { data } = await permissionsApi.sync()
      setNotice(syncSummary(data))
      await fetchPermissions()
    } catch (err) { setErrors(extractErrors(err)) }
    finally { setSyncing(false) }
  }

  // Group permissions by resource for display.
  const grouped = useMemo(() => {
    const acc: Record<string, Permission[]> = {}
    for (const p of permissions) {
      ;(acc[p.resource] ??= []).push(p)
    }
    return Object.entries(acc).sort(([a], [b]) => a.localeCompare(b))
  }, [permissions])

  const managedCount = permissions.filter((p) => p.managed).length

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-gray-900">Permissions</h1>
        {canSync && (
          <button className="btn-primary" onClick={handleSync} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync from models'}
          </button>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-6">
        {permissions.length} total · {managedCount} auto-generated from models · {permissions.length - managedCount} custom.
        {' '}Add a model and migrate (or click <span className="font-medium">Sync from models</span>) to register its permissions.
      </p>

      {errors.length > 0 && <Alert type="error" message={errors} className="mb-4" />}
      {notice && <Alert type="success" message={notice} className="mb-4" />}

      {loading ? (
        <div className="text-center py-8 text-gray-400">Loading…</div>
      ) : (
        <div className="space-y-3">
          {grouped.map(([resource, perms]) => (
            <div key={resource} className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <h3 className="font-mono font-semibold text-gray-900">{resource}</h3>
                {perms[0]?.managed ? (
                  <span className="badge-blue text-xs">auto</span>
                ) : (
                  <span className="badge-gray text-xs">custom</span>
                )}
                <span className="badge-gray text-xs">{perms.length}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {perms
                  .slice()
                  .sort((a, b) => a.action.localeCompare(b.action))
                  .map((p) => (
                    <span
                      key={p.id}
                      title={p.codename}
                      className="badge-gray font-mono text-xs"
                    >
                      {p.action}
                    </span>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function syncSummary(r: SyncResult): string {
  return `Sync complete — ${r.total} permissions (${r.created} new, ${r.updated} updated, ${r.pruned} pruned, ${r.granted} granted to admin).`
}
