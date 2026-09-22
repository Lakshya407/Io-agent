/**
 * Server-side pagination control.
 *
 * Walks `?page=N&page_size=M` against the backend — the current page's rows
 * are the only records fetched. Uses existing button styles.
 */

import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  loading,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);

  return (
    <div className="pagination">
      <span className="pagination-info">
        {total === 0
          ? "No records"
          : `${from}–${to} of ${total.toLocaleString()}`}
      </span>
      <span className="pagination-buttons">
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1 || loading}
          aria-label="Previous page"
        >
          <ChevronLeft size={14} />
          Prev
        </button>
        <span className="pagination-page">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages || loading}
          aria-label="Next page"
        >
          Next
          <ChevronRight size={14} />
        </button>
      </span>
    </div>
  );
}
