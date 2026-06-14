interface PaginationProps {
  count: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
}

export default function Pagination({ count, page, pageSize, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(count / pageSize)
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-white">
      <div className="text-sm text-gray-500">
        Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)} of {count}
      </div>
      <div className="flex gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="btn-secondary btn-sm"
        >
          Previous
        </button>
        {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
          const p = i + 1
          return (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`btn btn-sm ${p === page ? 'bg-brand-600 text-white' : 'btn-secondary'}`}
            >
              {p}
            </button>
          )
        })}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="btn-secondary btn-sm"
        >
          Next
        </button>
      </div>
    </div>
  )
}
