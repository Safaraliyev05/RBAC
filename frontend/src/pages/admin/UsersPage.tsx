import { useEffect, useState } from 'react'
import { adminUsersApi, rolesApi } from '@/api/rbac'
import type { AdminUser, Role } from '@/types'
import Alert from '@/components/ui/Alert'
import Pagination from '@/components/ui/Pagination'
import { extractErrors } from '@/utils/errors'
import { useAuth } from '@/contexts/AuthContext'

const PAGE_SIZE = 20

export default function UsersPage() {
  const { hasPermission } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState<AdminUser | null>(null)
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([])

  const [newUser, setNewUser] = useState({
    email: '', first_name: '', last_name: '', password: '',
    is_active: true, is_staff: false, role_ids: [] as number[]
  })
  const [createErrors, setCreateErrors] = useState<string[]>([])
  const [createLoading, setCreateLoading] = useState(false)

  const fetchUsers = async () => {
    setLoading(true)
    setErrors([])
    try {
      const { data } = await adminUsersApi.list({ page, search, page_size: PAGE_SIZE })
      setUsers(data.results)
      setCount(data.count)
    } catch (err) {
      setErrors(extractErrors(err))
    } finally {
      setLoading(false)
    }
  }

  const fetchRoles = async () => {
    try {
      const { data } = await rolesApi.list({ page_size: 100 })
      setRoles(data.results)
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchUsers() }, [page, search])
  useEffect(() => { fetchRoles() }, [])

  const handleToggleActive = async (user: AdminUser) => {
    try {
      await adminUsersApi.update(user.id, { is_active: !user.is_active })
      fetchUsers()
    } catch (err) { setErrors(extractErrors(err)) }
  }

  const handleDelete = async (user: AdminUser) => {
    if (!confirm(`Delete user ${user.email}? This cannot be undone.`)) return
    try {
      await adminUsersApi.delete(user.id)
      fetchUsers()
    } catch (err) { setErrors(extractErrors(err)) }
  }

  const handleCreateUser = async () => {
    setCreateErrors([])
    setCreateLoading(true)
    try {
      await adminUsersApi.create(newUser)
      setShowCreateModal(false)
      setNewUser({ email: '', first_name: '', last_name: '', password: '', is_active: true, is_staff: false, role_ids: [] })
      fetchUsers()
    } catch (err) { setCreateErrors(extractErrors(err)) }
    finally { setCreateLoading(false) }
  }

  const handleAssignRoles = async () => {
    if (!showAssignModal) return
    try {
      await adminUsersApi.assignRoles(showAssignModal.id, selectedRoleIds, true)
      setShowAssignModal(null)
      fetchUsers()
    } catch (err) { setErrors(extractErrors(err)) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        {hasPermission('users.create') && (
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            Add User
          </button>
        )}
      </div>

      {errors.length > 0 && <Alert type="error" message={errors} className="mb-4" />}

      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <input
            className="input max-w-sm"
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">User</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Roles</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Joined</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No users found.</td></tr>
              ) : users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{u.full_name || u.email}</div>
                    <div className="text-gray-400 text-xs">{u.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {u.roles.map((r) => (
                        <span key={r.role__id} className="badge-blue">{r.role__name}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? <span className="badge-green">Active</span> : <span className="badge-red">Inactive</span>}
                    {u.lockout_until && new Date(u.lockout_until) > new Date() && (
                      <span className="badge-yellow ml-1">Locked</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{new Date(u.date_joined).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {hasPermission('roles.update') && (
                        <button className="btn-secondary btn-sm"
                          onClick={() => { setShowAssignModal(u); setSelectedRoleIds(u.roles.map((r) => r.role__id)) }}>
                          Roles
                        </button>
                      )}
                      {hasPermission('users.update') && (
                        <button className="btn-secondary btn-sm" onClick={() => handleToggleActive(u)}>
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      )}
                      {hasPermission('users.delete') && (
                        <button className="btn-danger btn-sm" onClick={() => handleDelete(u)}>
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination count={count} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>

      {/* Create user modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Create User</h2>
            {createErrors.length > 0 && <Alert type="error" message={createErrors} className="mb-4" />}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">First Name</label>
                  <input className="input" value={newUser.first_name}
                    onChange={(e) => setNewUser((p) => ({ ...p, first_name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Last Name</label>
                  <input className="input" value={newUser.last_name}
                    onChange={(e) => setNewUser((p) => ({ ...p, last_name: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">Email</label>
                <input className="input" type="email" value={newUser.email}
                  onChange={(e) => setNewUser((p) => ({ ...p, email: e.target.value }))} />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" value={newUser.password}
                  onChange={(e) => setNewUser((p) => ({ ...p, password: e.target.value }))} />
              </div>
              <div>
                <label className="label">Roles</label>
                <div className="flex flex-wrap gap-2">
                  {roles.map((r) => (
                    <label key={r.id} className="flex items-center gap-1 text-sm cursor-pointer">
                      <input type="checkbox"
                        checked={newUser.role_ids.includes(r.id)}
                        onChange={(e) => setNewUser((p) => ({
                          ...p,
                          role_ids: e.target.checked
                            ? [...p.role_ids, r.id]
                            : p.role_ids.filter((id) => id !== r.id)
                        }))} />
                      {r.name}
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={newUser.is_active}
                    onChange={(e) => setNewUser((p) => ({ ...p, is_active: e.target.checked }))} />
                  Active
                </label>
                <label className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={newUser.is_staff}
                    onChange={(e) => setNewUser((p) => ({ ...p, is_staff: e.target.checked }))} />
                  Staff
                </label>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button className="btn-primary flex-1" onClick={handleCreateUser} disabled={createLoading}>
                {createLoading ? 'Creating...' : 'Create User'}
              </button>
              <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Assign roles modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Assign Roles</h2>
            <p className="text-sm text-gray-500 mb-4">{showAssignModal.email}</p>
            <div className="space-y-2">
              {roles.map((r) => (
                <label key={r.id} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox"
                    checked={selectedRoleIds.includes(r.id)}
                    onChange={(e) => setSelectedRoleIds((prev) =>
                      e.target.checked ? [...prev, r.id] : prev.filter((id) => id !== r.id)
                    )} />
                  <span className="font-medium">{r.name}</span>
                  <span className="text-xs text-gray-400">{r.description}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-2 mt-6">
              <button className="btn-primary flex-1" onClick={handleAssignRoles}>Save</button>
              <button className="btn-secondary" onClick={() => setShowAssignModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
