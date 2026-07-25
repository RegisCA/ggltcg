/**
 * Users tab — registered-users table, rendered with the shared DataTable
 * (sticky header, zebra rows, click-to-sort headers) and StatusBadge for the
 * last-game status.
 *
 * Every column is sortable: `sortValue` mirrors what each cell renders, and
 * returns null for the "-"/"Never" placeholders so users with no games sink
 * to the bottom instead of dominating a descending sort.
 */

import React from 'react';
import type { AdminUsersResponse } from '../../../api/adminService';
import type { User } from '../types';
import { formatRelativeTime } from '../utils';
import DataTable, { type DataTableColumn } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

interface UsersTabProps {
  usersData: AdminUsersResponse | undefined;
}

/** Sort timestamps chronologically; unparseable/absent dates sort last. */
const timestampValue = (value: string | null): number | null => {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
};

/** A deck slot sorts on its card list as rendered, or null when empty. */
const deckValue = (user: User, slot: number): string | null => {
  const deck = user.favorite_decks?.[slot];
  return deck?.length > 0 ? deck.join(', ') : null;
};

const columns: DataTableColumn<User>[] = [
  {
    key: 'name',
    header: 'Display Name',
    render: (user) => <span className="font-semibold">{user.display_name}</span>,
    sortValue: (user) => user.display_name,
  },
  {
    key: 'first_name',
    header: 'First Name',
    render: (user) => <span className="text-[var(--ink-faint)]">{user.first_name}</span>,
    sortValue: (user) => user.first_name,
  },
  {
    key: 'games',
    header: 'Games',
    align: 'right',
    render: (user) => user.games_played,
    sortValue: (user) => user.games_played,
  },
  {
    key: 'wins',
    header: 'Wins',
    align: 'right',
    render: (user) => user.games_won,
    sortValue: (user) => user.games_won,
  },
  {
    key: 'win_rate',
    header: 'Win Rate',
    align: 'right',
    sortValue: (user) => (user.games_played > 0 ? user.win_rate : null),
    render: (user) =>
      user.games_played > 0 ? (
        <span className={user.win_rate >= 50 ? 'text-green-400' : 'text-[var(--ink-muted)]'}>
          {user.win_rate.toFixed(1)}%
        </span>
      ) : (
        <span className="text-[var(--ink-faint)]">-</span>
      ),
  },
  {
    key: 'avg_turns',
    header: 'Avg Turns',
    align: 'right',
    sortValue: (user) => (user.games_played > 0 && user.avg_turns ? user.avg_turns : null),
    render: (user) =>
      user.games_played > 0 && user.avg_turns ? (
        <span className="text-orange-400">{user.avg_turns.toFixed(1)}</span>
      ) : (
        <span className="text-[var(--ink-faint)]">-</span>
      ),
  },
  {
    key: 'avg_game',
    header: 'Avg Game',
    align: 'right',
    sortValue: (user) =>
      user.games_played > 0 && user.avg_game_duration_seconds ? user.avg_game_duration_seconds : null,
    render: (user) =>
      user.games_played > 0 && user.avg_game_duration_seconds ? (
        <span className="text-cyan-400">
          {user.avg_game_duration_seconds < 60
            ? `${Math.round(user.avg_game_duration_seconds)}s`
            : `${Math.floor(user.avg_game_duration_seconds / 60)}m ${Math.round(user.avg_game_duration_seconds % 60)}s`}
        </span>
      ) : (
        <span className="text-[var(--ink-faint)]">-</span>
      ),
  },
  {
    key: 'deck1',
    header: 'Deck 1',
    sortValue: (user) => deckValue(user, 0),
    render: (user) => <span className="text-xs text-[var(--ink-muted)]">{deckValue(user, 0) ?? '-'}</span>,
  },
  {
    key: 'deck2',
    header: 'Deck 2',
    sortValue: (user) => deckValue(user, 1),
    render: (user) => <span className="text-xs text-[var(--ink-muted)]">{deckValue(user, 1) ?? '-'}</span>,
  },
  {
    key: 'deck3',
    header: 'Deck 3',
    sortValue: (user) => deckValue(user, 2),
    render: (user) => <span className="text-xs text-[var(--ink-muted)]">{deckValue(user, 2) ?? '-'}</span>,
  },
  {
    key: 'last_game',
    header: 'Last Game',
    sortValue: (user) => timestampValue(user.last_game_at),
    render: (user) =>
      user.last_game_at ? (
        <div>
          <div className="text-[var(--ink-muted)]">{formatRelativeTime(user.last_game_at)}</div>
          {user.last_game_status && <StatusBadge status={user.last_game_status} />}
        </div>
      ) : (
        <span className="text-[var(--ink-faint)]">Never</span>
      ),
  },
  {
    key: 'joined',
    header: 'Joined',
    sortValue: (user) => timestampValue(user.created_at),
    render: (user) => <span className="text-[var(--ink-faint)] text-xs">{formatRelativeTime(user.created_at)}</span>,
  },
];

const UsersTab: React.FC<UsersTabProps> = ({ usersData }) => (
  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
    <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
      <p className="text-[var(--ink-faint)] text-sm">
        Showing {usersData?.count || 0} registered users
      </p>
    </div>
    <DataTable
      columns={columns}
      rows={usersData?.users || []}
      rowKey={(user) => user.google_id}
      emptyMessage="No users to display."
    />
  </div>
);

export default UsersTab;
