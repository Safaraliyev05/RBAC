import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import Alert from '@/components/ui/Alert'
import { extractErrors } from '@/utils/errors'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
  })
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErrors([])
    setLoading(true)
    try {
      await register(form)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setErrors(extractErrors(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Create Account</h1>
          <p className="mt-2 text-gray-500">Register for RBAC System access</p>
        </div>
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {errors.length > 0 && <Alert type="error" message={errors} />}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">First Name</label>
                <input name="first_name" type="text" className="input" value={form.first_name}
                  onChange={handleChange} required />
              </div>
              <div>
                <label className="label">Last Name</label>
                <input name="last_name" type="text" className="input" value={form.last_name}
                  onChange={handleChange} required />
              </div>
            </div>
            <div>
              <label className="label">Email address</label>
              <input name="email" type="email" className="input" value={form.email}
                onChange={handleChange} autoComplete="email" required />
            </div>
            <div>
              <label className="label">Password</label>
              <input name="password" type="password" className="input" value={form.password}
                onChange={handleChange} autoComplete="new-password" required />
              <p className="text-xs text-gray-400 mt-1">At least 8 characters, not too common.</p>
            </div>
            <div>
              <label className="label">Confirm Password</label>
              <input name="password_confirm" type="password" className="input" value={form.password_confirm}
                onChange={handleChange} autoComplete="new-password" required />
            </div>
            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-600 font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
