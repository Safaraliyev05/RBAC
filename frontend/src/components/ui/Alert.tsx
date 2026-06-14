interface AlertProps {
  type: 'error' | 'success' | 'warning' | 'info'
  message: string | string[]
  className?: string
}

const styles = {
  error: 'bg-red-50 border border-red-200 text-red-800',
  success: 'bg-green-50 border border-green-200 text-green-800',
  warning: 'bg-yellow-50 border border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border border-blue-200 text-blue-800',
}

export default function Alert({ type, message, className = '' }: AlertProps) {
  const messages = Array.isArray(message) ? message : [message]
  return (
    <div className={`rounded-md px-4 py-3 text-sm ${styles[type]} ${className}`}>
      {messages.length === 1 ? (
        <p>{messages[0]}</p>
      ) : (
        <ul className="list-disc list-inside space-y-1">
          {messages.map((m, i) => <li key={i}>{m}</li>)}
        </ul>
      )}
    </div>
  )
}
