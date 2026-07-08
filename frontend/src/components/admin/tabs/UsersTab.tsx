/**
 * Users tab — registered-users table, rendered with the shared DataTable
 * (sticky header, zebra rows) and StatusBadge for the last-game status.
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

const columns: DataTableColumn<User>[] = [
  {
    key: 'name',
    header: 'Display Name',
    render: (user) => <span className="font-semibold">{user.display_name}</span>,
  },
  {
    key: 'first_name',
    header: 'First Name',
    render: (user) => <span className="text-[var(--ink-faint)]">{user.first_name}</span>,
  },
  { key: 'games', header: 'Games', align: 'right', render: (user) => user.games_played },
  { key: 'wins', header: 'Wins', align: 'right', render: (user) => user.games_won },
  {
    key: 'win_rate',
    header: 'Win Rate',
    align: 'right',
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
    render: (user) => (
      <span className="text-xs text-[var(--ink-muted)]">
        {user.favorite_decks?.[0]?.length > 0 ? user.favorite_decks[0].join(', ') : '-'}
      </span>
    ),
  },
  {
    key: 'deck2',
    header: 'Deck 2',
    render: (user) => (
      <span className="text-xs text-[var(--ink-muted)]">
        {user.favorite_decks?.[1]?.length > 0 ? user.favorite_decks[1].join(', ') : '-'}
      </span>
    ),
  },
  {
    key: 'deck3',
    header: 'Deck 3',
    render: (user) => (
      <span className="text-xs text-[var(--ink-muted)]">
        {user.favorite_decks?.[2]?.length > 0 ? user.favorite_decks[2].join(', ') : '-'}
      </span>
    ),
  },
  {
    key: 'last_game',
    header: 'Last Game',
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
