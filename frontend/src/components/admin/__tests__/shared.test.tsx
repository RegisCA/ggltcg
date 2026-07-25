/**
 * Render tests for the shared admin components introduced in PR A3:
 * DataTable (sticky header, zebra rows) and StatusBadge.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

interface SortableRow {
  id: number;
  name: string;
  score: number | null;
}

const sortableColumns: DataTableColumn<SortableRow>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name, sortValue: (row) => row.name },
  {
    key: 'score',
    header: 'Score',
    align: 'right',
    render: (row) => row.score ?? '-',
    sortValue: (row) => row.score,
  },
  { key: 'note', header: 'Note', render: () => 'n/a' },
];

const SORTABLE_ROWS: SortableRow[] = [
  { id: 1, name: 'Bob', score: 5 },
  { id: 2, name: 'alice', score: null },
  { id: 3, name: 'Carol', score: 12 },
];

/** Reads the first cell of each body row, in render order. */
const firstCells = (): string[] =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelectorAll('td')[0].textContent ?? '');

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

describe('DataTable sorting', () => {
  it('only makes columns with a sortValue clickable', () => {
    render(<DataTable columns={sortableColumns} rows={SORTABLE_ROWS} rowKey={(row) => row.id} />);
    expect(screen.getByRole('button', { name: /Name/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Score/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Note/ })).not.toBeInTheDocument();
  });

  it('leaves rows in their incoming order until a header is clicked', () => {
    render(<DataTable columns={sortableColumns} rows={SORTABLE_ROWS} rowKey={(row) => row.id} />);
    expect(firstCells()).toEqual(['Bob', 'alice', 'Carol']);
  });

  it('sorts text ascending on first click, case-insensitively', async () => {
    render(<DataTable columns={sortableColumns} rows={SORTABLE_ROWS} rowKey={(row) => row.id} />);
    await userEvent.click(screen.getByRole('button', { name: /Name/ }));
    expect(firstCells()).toEqual(['alice', 'Bob', 'Carol']);
  });

  it('sorts numbers descending on first click and toggles on the second', async () => {
    render(<DataTable columns={sortableColumns} rows={SORTABLE_ROWS} rowKey={(row) => row.id} />);
    const scoreHeader = screen.getByRole('button', { name: /Score/ });

    await userEvent.click(scoreHeader);
    expect(firstCells()).toEqual(['Carol', 'Bob', 'alice']);

    await userEvent.click(scoreHeader);
    // Ascending, but the null score still sorts last.
    expect(firstCells()).toEqual(['Bob', 'Carol', 'alice']);
  });

  it('reports the active direction via aria-sort', async () => {
    render(<DataTable columns={sortableColumns} rows={SORTABLE_ROWS} rowKey={(row) => row.id} />);
    const nameHeader = () => screen.getByRole('columnheader', { name: /Name/ });
    expect(nameHeader()).not.toHaveAttribute('aria-sort');

    await userEvent.click(screen.getByRole('button', { name: /Name/ }));
    expect(nameHeader()).toHaveAttribute('aria-sort', 'ascending');

    await userEvent.click(screen.getByRole('button', { name: /Name/ }));
    expect(nameHeader()).toHaveAttribute('aria-sort', 'descending');
  });

  it('applies defaultSort on first render', () => {
    render(
      <DataTable
        columns={sortableColumns}
        rows={SORTABLE_ROWS}
        rowKey={(row) => row.id}
        defaultSort={{ key: 'name', direction: 'desc' }}
      />
    );
    expect(firstCells()).toEqual(['Carol', 'Bob', 'alice']);
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute('aria-sort', 'descending');
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
