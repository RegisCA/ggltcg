/**
 * Render tests for the shared admin components introduced in PR A3:
 * DataTable (sticky header, zebra rows) and StatusBadge.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DataTable, { type DataTableColumn } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

interface Row {
  id: number;
  name: string;
}

const columns: DataTableColumn<Row>[] = [
  { key: 'id', header: 'ID', render: (row) => row.id },
  { key: 'name', header: 'Name', render: (row) => row.name },
];

describe('DataTable', () => {
  it('renders column headers and row cells', () => {
    const rows: Row[] = [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }];
    render(<DataTable columns={columns} rows={rows} rowKey={(row) => row.id} />);
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('shows an empty message when there are no rows', () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(row) => row.id} emptyMessage="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('applies zebra striping to alternate rows', () => {
    const rows: Row[] = [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }];
    render(<DataTable columns={columns} rows={rows} rowKey={(row) => row.id} />);
    const bodyRows = screen.getAllByRole('row').slice(1); // skip header row
    const classesOf = (el: Element) => el.className.split(/\s+/);
    expect(classesOf(bodyRows[0])).not.toContain('bg-white/5');
    expect(classesOf(bodyRows[1])).toContain('bg-white/5');
  });
});

describe('StatusBadge', () => {
  it('renders the status text', () => {
    render(<StatusBadge status="active" />);
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('uses theme tokens for known statuses (no saturated palette colors)', () => {
    render(<StatusBadge status="active" />);
    const badge = screen.getByText('active');
    expect(badge.style.color).toBe('var(--gold)');
    expect(badge.className).not.toMatch(/bg-(green|blue|yellow|red)-\d/);
  });

  it('falls back to a neutral ink tone for unknown statuses', () => {
    render(<StatusBadge status="mystery" />);
    expect(screen.getByText('mystery').style.color).toBe('var(--ink-faint)');
  });
});
