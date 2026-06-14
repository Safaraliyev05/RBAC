import { useState, type FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { authApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import { extractErrors } from '@/utils/errors'

export default function ProfilePage() {
  const { user, refreshProfile } = useAuth()

  const [editMode, setEditMode] = useState(false)
  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [profileErrors, setProfileErrors] = useState<string[]>([])
  const [profileSuccess, setProfileSuccess] = useState('')
  const [profileLoading, setProfileLoading] = useState(false)

  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', new_password_confirm: '' })
  const [pwErrors, setPwErrors] = useState<string[]>([])
  const [pwSuccess, setPwSuccess] = useState('')
  const [pwLoading, setPwLoading] = useState(false)

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault()
    setProfileErrors([])
    setProfileSuccess('')
    setProfileLoading(true)
    try {
      await authApi.updateProfile({ first_name: firstName, last_name: lastName })
      await refreshProfile()
      setProfileSuccess('Profile updated successfully.')
      setEditMode(false)
    } catch (err) {
      setProfileErrors(extractErrors(err))
    } finally {
      setProfileLoading(false)
    }
  }

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault()
    setPwErrors([])
    setPwSuccess('')
    setPwLoading(true)
    try {
      await authApi.changePassword(pwForm)
      setPwSuccess('Password changed successfully.')
      setPwForm({ old_password: '', new_password: '', new_password_confirm: '' })
    } catch (err) {
      setPwErrors(extractErrors(err))
    } finally {
      setPwLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>

      {/* Profile card */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Personal Information</h2>
          {!editMode && (
            <button className="btn-secondary btn-sm" onClick={() => setEditMode(true)}>
              Edit
            </button>
          )}
        </div>

        {profileErrors.length > 0 && <Alert type="error" message={profileErrors} className="mb-4" />}
        {profileSuccess && <Alert type="success" message={profileSuccess} className="mb-4" />}

        {editMode ? (
          <form onSubmit={handleProfileSave} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">First Name</label>
                <input className="input" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              </div>
              <div>
                <label className="label">Last Name</label>
                <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary" disabled={profileLoading}>Save</button>
              <button type="button" className="btn-secondary" onClick={() => setEditMode(false)}>Cancel</button>
            </div>
          </form>
        ) : (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-gray-500">Email</dt><dd className="font-medium">{user?.email}</dd></div>
            <div><dt className="text-gray-500">Full Name</dt><dd className="font-medium">{user?.full_name || '—'}</dd></div>
            <div><dt className="text-gray-500">Member Since</dt><dd>{user?.date_joined ? new Date(user.date_joined).toLocaleDateString() : '—'}</dd></div>
            <div><dt className="text-gray-500">Last Login</dt><dd>{user?.last_login ? new Date(user.last_login).toLocaleString() : '—'}</dd></div>
            <div>
              <dt className="text-gray-500">Roles</dt>
              <dd className="flex flex-wrap gap-1 mt-1">
                {user?.roles.map((r) => <span key={r} className="badge-blue">{r}</span>)}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Account Status</dt>
              <dd>{user?.is_active ? <span className="badge-green">Active</span> : <span className="badge-red">Inactive</span>}</dd>
            </div>
          </dl>
        )}
      </div>

      {/* Change password */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">Change Password</h2>
        {pwErrors.length > 0 && <Alert type="error" message={pwErrors} className="mb-4" />}
        {pwSuccess && <Alert type="success" message={pwSuccess} className="mb-4" />}
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label className="label">Current Password</label>
            <input type="password" className="input" value={pwForm.old_password}
              onChange={(e) => setPwForm((p) => ({ ...p, old_password: e.target.value }))} required />
          </div>
          <div>
            <label className="label">New Password</label>
            <input type="password" className="input" value={pwForm.new_password}
              onChange={(e) => setPwForm((p) => ({ ...p, new_password: e.target.value }))} required />
          </div>
          <div>
            <label className="label">Confirm New Password</label>
            <input type="password" className="input" value={pwForm.new_password_confirm}
              onChange={(e) => setPwForm((p) => ({ ...p, new_password_confirm: e.target.value }))} required />
          </div>
          <button type="submit" className="btn-primary" disabled={pwLoading}>
            {pwLoading ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
