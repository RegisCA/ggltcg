/**
 * Games tab — recent games list. JSX moved verbatim from AdminDataViewer.tsx.
 */

import React from 'react';
import type { AdminGamesResponse } from '../../../api/adminService';
import type { Game } from '../types';
import { formatDate } from '../utils';

interface GamesTabProps {
  gamesData: AdminGamesResponse | undefined;
}

const GamesTab: React.FC<GamesTabProps> = ({ gamesData }) => (
  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
    <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
      <p className="text-[var(--ink-faint)] text-sm">
        Showing {gamesData?.count || 0} most recent games
      </p>
    </div>
    {gamesData?.games.map((game: Game) => (
      <div key={game.id} className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-xl font-semibold">
              {game.player1_name} vs {game.player2_name}
              <span className={`text-xs rounded ${
                game.status === 'active' ? 'bg-green-600' :
                game.status === 'completed' ? 'bg-blue-600' :
                'bg-white/10'
              }`} style={{ marginLeft: 'var(--spacing-component-sm)', padding: '4px var(--spacing-component-xs)' }}>
                {game.status}
              </span>
            </h3>
            <p className="text-sm text-[var(--ink-faint)] font-mono" style={{ marginTop: '4px' }}>
              Game ID: {game.id}
              {game.game_code && ` · Code: ${game.game_code}`}
            </p>
            <p className="text-sm text-[var(--ink-faint)]">
              Turn {game.turn_number} · {game.phase} Phase
            </p>
            <p className="text-sm text-[var(--ink-faint)]">
              Created: {formatDate(game.created_at)} · Updated: {formatDate(game.updated_at)}
            </p>
            {game.winner_id && (
              <p className="text-sm text-green-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                Winner: {game.winner_id === game.player1_id ? game.player1_name : game.player2_name}
              </p>
            )}
          </div>
        </div>
      </div>
    ))}
  </div>
);

export default GamesTab;
