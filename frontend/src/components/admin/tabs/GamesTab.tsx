/**
 * Games tab — recent games list, rendered with the shared DataTable
 * (sticky header, zebra rows) and StatusBadge for the game status pill.
 */

import React from 'react';
import type { AdminGamesResponse } from '../../../api/adminService';
import type { Game } from '../types';
import { formatDate } from '../utils';
import DataTable, { type DataTableColumn } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

interface GamesTabProps {
  gamesData: AdminGamesResponse | undefined;
}

const columns: DataTableColumn<Game>[] = [
  {
    key: 'players',
    header: 'Players',
    render: (game) => (
      <div>
        <span className="font-semibold">{game.player1_name} vs {game.player2_name}</span>
        {game.winner_id && (
          <div className="text-xs text-green-400">
            Winner: {game.winner_id === game.player1_id ? game.player1_name : game.player2_name}
          </div>
        )}
      </div>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (game) => <StatusBadge status={game.status} />,
  },
  {
    key: 'progress',
    header: 'Progress',
    render: (game) => (
      <span className="text-[var(--ink-faint)] text-xs">Turn {game.turn_number} · {game.phase} Phase</span>
    ),
  },
  {
    key: 'game_id',
    header: 'Game ID',
    render: (game) => (
      <span className="text-xs font-mono text-[var(--ink-faint)]">
        {game.id}
        {game.game_code && ` · ${game.game_code}`}
      </span>
    ),
  },
  {
    key: 'timestamps',
    header: 'Created / Updated',
    render: (game) => (
      <span className="text-xs text-[var(--ink-faint)]">
        {formatDate(game.created_at)} · {formatDate(game.updated_at)}
      </span>
    ),
  },
];

const GamesTab: React.FC<GamesTabProps> = ({ gamesData }) => (
  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
    <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
      <p className="text-[var(--ink-faint)] text-sm">
        Showing {gamesData?.count || 0} most recent games
      </p>
    </div>
    <DataTable
      columns={columns}
      rows={gamesData?.games || []}
      rowKey={(game) => game.id}
      emptyMessage="No games to display."
    />
  </div>
);

export default GamesTab;
