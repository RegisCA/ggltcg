/**
 * Shared list table for the admin viewer — sticky header, zebra rows,
 * styled exclusively with Paper & Ink CSS custom properties (spacing +
 * ink color tokens, no hardcoded pixel values). Used by the Games, Users,
 * and Playbacks tabs so those list views share one implementation instead
 * of hand-rolled markup per tab.
 */

import React from 'react';

export interface DataTableColumn<T> {
  /** Unique key for the column (also used as the React key for cells). */
  key: string;
  header: React.ReactNode;
  render: (row: T) => React.ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  /** Extracts a stable React key for each row. */
  rowKey: (row: T) => string | number;
  emptyMessage?: string;
}

const alignClass = (align: DataTableColumn<unknown>['align']): string => {
  if (align === 'right') return 'text-right';
  if (align === 'center') return 'text-center';
  return 'text-left';
};

function DataTable<T>({ columns, rows, rowKey, emptyMessage = 'No data to display.' }: DataTableProps<T>) {
  return (
    <div
      className="bg-panel rounded-lg overflow-auto border border-white/10"
      style={{ maxHeight: '70vh' }}
    >
      <table className="w-full text-sm">
        <thead className="bg-black/30" style={{ position: 'sticky', top: 0, zIndex: 1 }}>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className={`${alignClass(col.align)} ${col.className ?? ''}`}
                style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
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
            rows.map((row, idx) => (
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
