/**
 * Shared list table for the admin viewer — sticky header, zebra rows,
 * styled exclusively with Paper & Ink CSS custom properties (spacing +
 * ink color tokens, no hardcoded pixel values). Used by the Games, Users,
 * and Playbacks tabs so those list views share one implementation instead
 * of hand-rolled markup per tab.
 *
 * Sorting is opt-in per column: give a column a `sortValue` and its header
 * becomes a sort toggle. Columns without one stay plain text, so tabs that
 * haven't opted in render exactly as before.
 */

import React from 'react';

/** Comparable value a column sorts on. `null`/`undefined` always sort last. */
export type SortValue = string | number | null | undefined;

export interface DataTableColumn<T> {
  /** Unique key for the column (also used as the React key for cells). */
  key: string;
  header: React.ReactNode;
  render: (row: T) => React.ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
  /**
   * Sort key for this column. Providing it makes the header clickable.
   * Return null/undefined for "no value" rows (they sink to the bottom in
   * both directions rather than crowding the top of a descending sort).
   */
  sortValue?: (row: T) => SortValue;
}

export interface SortState {
  key: string;
  direction: 'asc' | 'desc';
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  /** Extracts a stable React key for each row. */
  rowKey: (row: T) => string | number;
  emptyMessage?: string;
  /** Initial sort. Omit to render rows in the order they arrive. */
  defaultSort?: SortState;
}

const alignClass = (align: DataTableColumn<unknown>['align']): string => {
  if (align === 'right') return 'text-right';
  if (align === 'center') return 'text-center';
  return 'text-left';
};

const isEmptyValue = (value: SortValue): boolean => value === null || value === undefined || value === '';

/** Compares two sort values; empties sink last, strings compare case-insensitively. */
const compareValues = (a: SortValue, b: SortValue, direction: 'asc' | 'desc'): number => {
  const aEmpty = isEmptyValue(a);
  const bEmpty = isEmptyValue(b);
  if (aEmpty || bEmpty) {
    if (aEmpty && bEmpty) return 0;
    return aEmpty ? 1 : -1; // empties last regardless of direction
  }

  let result: number;
  if (typeof a === 'number' && typeof b === 'number') {
    result = a - b;
  } else {
    result = String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
  }
  return direction === 'asc' ? result : -result;
};

/**
 * First click on a column picks the direction that's most useful for its data:
 * text reads best A→Z, numbers (counts, rates, timestamps) best highest-first.
 */
const initialDirection = <T,>(column: DataTableColumn<T>, rows: T[]): 'asc' | 'desc' => {
  const sample = rows.map(row => column.sortValue?.(row)).find(value => !isEmptyValue(value));
  return typeof sample === 'number' ? 'desc' : 'asc';
};

const sortIndicator = (state: 'asc' | 'desc' | null): string => {
  if (state === 'asc') return '▲';
  if (state === 'desc') return '▼';
  return '↕';
};

function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyMessage = 'No data to display.',
  defaultSort,
}: DataTableProps<T>) {
  const [sort, setSort] = React.useState<SortState | null>(defaultSort ?? null);

  const activeColumn = sort ? columns.find(col => col.key === sort.key && col.sortValue) : undefined;

  const sortedRows = React.useMemo(() => {
    if (!activeColumn?.sortValue || !sort) return rows;
    const sortValue = activeColumn.sortValue;
    // Array.prototype.sort is stable, so ties keep their incoming order.
    return [...rows].sort((a, b) => compareValues(sortValue(a), sortValue(b), sort.direction));
  }, [rows, activeColumn, sort]);

  const toggleSort = (column: DataTableColumn<T>) => {
    setSort(current =>
      current?.key === column.key
        ? { key: column.key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
        : { key: column.key, direction: initialDirection(column, rows) }
    );
  };

  return (
    <div
      className="bg-panel rounded-lg overflow-auto border border-white/10"
      style={{ maxHeight: '70vh' }}
    >
      <table className="w-full text-sm">
        <thead className="bg-black/30" style={{ position: 'sticky', top: 0, zIndex: 1 }}>
          <tr>
            {columns.map(col => {
              const direction = sort?.key === col.key && col.sortValue ? sort.direction : null;
              return (
                <th
                  key={col.key}
                  className={`${alignClass(col.align)} ${col.className ?? ''}`}
                  style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
                  aria-sort={direction ? (direction === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  {col.sortValue ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col)}
                      className={`inline-flex items-center w-full whitespace-nowrap cursor-pointer hover:text-[var(--gold)] ${
                        col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : ''
                      } ${direction ? 'text-[var(--gold)]' : ''}`}
                      style={{ gap: 'var(--spacing-component-xs)' }}
                      title={`Sort by ${typeof col.header === 'string' ? col.header : col.key}`}
                    >
                      {col.header}
                      <span
                        aria-hidden="true"
                        className={`text-[10px] ${direction ? '' : 'text-[var(--ink-faint)]'}`}
                      >
                        {sortIndicator(direction)}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="text-center text-[var(--ink-faint)]"
                style={{ padding: 'var(--spacing-component-lg)' }}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedRows.map((row, idx) => (
              <tr
                key={rowKey(row)}
                className={`border-t border-white/10 hover:bg-white/5 ${idx % 2 === 1 ? 'bg-white/5' : ''}`}
              >
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={alignClass(col.align)}
                    style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
