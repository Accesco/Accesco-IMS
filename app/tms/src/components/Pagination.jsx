import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import styles from '../styles/components.module.css';

export default function Pagination({
  currentPage = 1,
  totalPages = 1,
  totalItems = 0,
  pageSize = 10,
  onPageChange,
  onPageSizeChange,
}) {
  const startIdx = (currentPage - 1) * pageSize + 1;
  const endIdx = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className={styles.paginationContainer}>
      <div className={styles.paginationInfo}>
        Showing {totalItems > 0 ? startIdx : 0} to {endIdx} of {totalItems} records
      </div>

      <div className={styles.paginationRight}>
        {onPageSizeChange && (
          <div className={styles.pageSizeGroup}>
            <span>Rows:</span>
            <select
              className="tms-select"
              style={{ height: '28px', fontSize: '12px' }}
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        )}

        <div className={styles.pageButtons}>
          <button
            className={styles.pageNavBtn}
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
            aria-label="Previous Page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className={styles.pageIndicator}>
            Page {currentPage} of {totalPages || 1}
          </span>
          <button
            className={styles.pageNavBtn}
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
            aria-label="Next Page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
