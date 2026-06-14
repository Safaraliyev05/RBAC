import { useEffect, useState } from 'react'
import { permissionsApi, rolesApi } from '@/api/rbac'
import type { Permission, Role } from '@/types'
import Alert from '@/components/ui/Alert'
import { extractErrors } from '@/utils/errors'
import { useAuth } from '@/contexts/AuthContext'

export default function RolesPage() {
  const { hasPermission } = useAuth()
  const [roles, setRoles] = useState<Role[]>([])
  const [allPermissions, setAllPermissions] = useState<Permission[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)

  const [showModal, setShowModal] = useState<null | 'create' | Role>(null)
  const [formData, setFormData] = useState({ name: '', description: '', permission_ids: [] as number[] })
  const [formErrors, setFormErrors] = useState<string[]>([])
  const [formLoading, setFormLoading] = useState(false)

  const fetchRoles = async () => {
    setLoading(true)
    try {
      const { data } = await rolesApi.list({ page_size: 100 })
      setRoles(data.results)
    } catch (err) { setErrors(extractErrors(err)) }
    finally { setLoading(false) }
  }

  const fetchPermissions = async () => {
    try {
      const { data } = await permissionsApi.list({ page_size: 200 })
      setAllPermissions(data.results)
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchRoles(); fetchPermissions() }, [])

  const openCreate = () => {
    setFormData({ name: '', description: '', permission_ids: [] })
    setFormErrors([])
    setShowModal('create')
  }

  const openEdit = (role: Role) => {
    setFormData({
      name: role.name,
      description: role.description,
      permission_ids: role.permissions.map((p) => p.id),
    })
    setFormErrors([])
    setShowModal(role)
  }

  const handleSave = async () => {
    setFormErrors([])
    setFormLoading(true)
    try {
      if (showModal === 'create') {
        await rolesApi.create(formData)
      } else if (showModal) {
        await rolesApi.update((showModal as Role).id, formData)
      }
      setShowModal(null)
      fetchRoles()
    } catch (err) { setFormErrors(extractErrors(err)) }
    finally { setFormLoading(false) }
  }

  const handleDelete = async (role: Role) => {
    if (!confirm(`Delete role "${role.name}"? This cannot be undone.`)) return
    try {
      await rolesApi.delete(role.id)
      fetchRoles()
    } catch (err) { setErrors(extractErrors(err)) }
  }

  // Group permissions by resource for display
  const permsByResource = allPermissions.reduce<Record<string, Permission[]>>((acc, p) => {
    if (!acc[p.resource]) acc[p.resource] = []
    acc[p.resource].push(p)
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Role Management</h1>
        {hasPermission('roles.create') && (
          <button className="btn-primary" onClick={openCreate}>Create Role</button>
        )}
      </div>

      {errors.length > 0 && <Alert type="error" message={errors} className="mb-4" />}

      {loading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : (
        <div className="space-y-3">
          {roles.map((role) => (
            <div key={role.id} className="card">
              <div className="p-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{role.name}</h3>
                    <span className="badge-gray">{role.permissions.length} permissions</span>
                    <span className="badge-blue">{role.user_count} users</span>
                  </div>
                  {role.description && <p className="text-sm text-gray-500 mt-1">{role.description}</p>}
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary btn-sm"
                    onClick={() => setExpanded(expanded === role.id ? null : role.id)}>
                    {expanded === role.id ? 'Collapse' : 'Permissions'}
                  </button>
                  {hasPermission('roles.update') && (
                    <button className="btn-secondary btn-sm" onClick={() => openEdit(role)}>Edit</button>
                  )}
                  {hasPermission('roles.delete') && (
                    <button className="btn-danger btn-sm" onClick={() => handleDelete(role)}>Delete</button>
                  )}
                </div>
              </div>
              {expanded === role.id && (
                <div className="border-t border-gray-100 p-4">
                  <div className="flex flex-wrap gap-2">
                    {role.permissions.length === 0 ? (
                      <span className="text-gray-400 text-sm">No permissions assigned.</span>
                    ) : role.permissions.map((p) => (
                      <span key={p.id} className="badge-gray font-mono">{p.codename}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit modal */}
      {showModal !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">
              {showModal === 'create' ? 'Create Role' : `Edit Role: ${(showModal as Role).name}`}
            </h2>
            {formErrors.length > 0 && <Alert type="error" message={formErrors} className="mb-4" />}
            <div className="space-y-4">
              <div>
                <label className="label">Role Name</label>
                <input className="input" value={formData.name}
                  onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))} />
              </div>
              <div>
                <label className="label">Description</label>
                <input className="input" value={formData.description}
                  onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))} />
              </div>
              <div>
                <label className="label mb-2">Permissions</label>
                <div className="space-y-3">
                  {Object.entries(permsByResource).map(([resource, perms]) => (
                    <div key={resource}>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{resource}</p>
                      <div className="flex flex-wrap gap-3">
                        {perms.map((p) => (
                          <label key={p.id} className="flex items-center gap-1.5 text-sm cursor-pointer">
                            <input type="checkbox"
                              checked={formData.permission_ids.includes(p.id)}
                              onChange={(e) => setFormData((prev) => ({
                                ...prev,
                                permission_ids: e.target.checked
                                  ? [...prev.permission_ids, p.id]
                                  : prev.permission_ids.filter((id) => id !== p.id)
                              }))} />
                            <span className="font-mono text-xs">{p.action}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button className="btn-primary flex-1" onClick={handleSave} disabled={formLoading}>
                {formLoading ? 'Saving...' : 'Save'}
              </button>
              <button className="btn-secondary" onClick={() => setShowModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
