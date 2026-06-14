import { Link } from 'react-router-dom'

export default function ForbiddenPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-red-400">403</h1>
        <h2 className="text-2xl font-semibold text-gray-700 mt-2">Access Denied</h2>
        <p className="text-gray-500 mt-2">You don't have permission to view this page.</p>
        <Link to="/dashboard" className="btn-primary mt-6 inline-block">Back to Dashboard</Link>
      </div>
    </div>
  )
}
