/**
 * Users tab — registered-users table. JSX moved verbatim from AdminDataViewer.tsx.
 */

import React from 'react';
import type { AdminUsersResponse } from '../../../api/adminService';
import type { User } from '../types';
import { formatRelativeTime } from '../utils';

interface UsersTabProps {
  usersData: AdminUsersResponse | undefined;
}

const UsersTab: React.FC<UsersTabProps> = ({ usersData }) => (
  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
    <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
      <p className="text-[var(--ink-faint)] text-sm">
        Showing {usersData?.count || 0} registered users
      </p>
    </div>
    <div className="bg-panel rounded-lg overflow-hidden border border-white/10">
      <table className="w-full text-sm">
        <thead className="bg-black/30">
          <tr>
            <th className="px-4 py-3 text-left">Display Name</th>
            <th className="px-4 py-3 text-left">First Name</th>
            <th className="px-4 py-3 text-right">Games</th>
            <th className="px-4 py-3 text-right">Wins</th>
            <th className="px-4 py-3 text-right">Win Rate</th>
            <th className="px-4 py-3 text-right">Avg Turns</th>
            <th className="px-4 py-3 text-right">Avg Game</th>
            <th className="px-4 py-3 text-left">Deck 1</th>
            <th className="px-4 py-3 text-left">Deck 2</th>
            <th className="px-4 py-3 text-left">Deck 3</th>
            <th className="px-4 py-3 text-left">Last Game</th>
            <th className="px-4 py-3 text-left">Joined</th>
          </tr>
        </thead>
        <tbody>
          {usersData?.users.map((user: User) => (
            <tr key={user.google_id} className="border-t border-white/10 hover:bg-white/5">
              <td className="px-4 py-3 font-semibold">{user.display_name}</td>
              <td className="px-4 py-3 text-[var(--ink-faint)]">{user.first_name}</td>
              <td className="px-4 py-3 text-right">{user.games_played}</td>
              <td className="px-4 py-3 text-right">{user.games_won}</td>
              <td className="px-4 py-3 text-right">
                {user.games_played > 0 ? (
                  <span className={user.win_rate >= 50 ? 'text-green-400' : 'text-[var(--ink-muted)]'}>
                    {user.win_rate.toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-[var(--ink-faint)]">-</span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {user.games_played > 0 && user.avg_turns ? (
                  <span className="text-orange-400">{user.avg_turns.toFixed(1)}</span>
                ) : (
                  <span className="text-[var(--ink-faint)]">-</span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {user.games_played > 0 && user.avg_game_duration_seconds ? (
                  <span className="text-cyan-400">
                    {user.avg_game_duration_seconds < 60
                      ? `${Math.round(user.avg_game_duration_seconds)}s`
                      : `${Math.floor(user.avg_game_duration_seconds / 60)}m ${Math.round(user.avg_game_duration_seconds % 60)}s`
                    }
                  </span>
                ) : (
                  <span className="text-[var(--ink-faint)]">-</span>
                )}
              </td>
              <td className="px-4 py-3 text-xs text-[var(--ink-muted)]">
                {user.favorite_decks?.[0]?.length > 0 ? user.favorite_decks[0].join(', ') : '-'}
              </td>
              <td className="px-4 py-3 text-xs text-[var(--ink-muted)]">
                {user.favorite_decks?.[1]?.length > 0 ? user.favorite_decks[1].join(', ') : '-'}
              </td>
              <td className="px-4 py-3 text-xs text-[var(--ink-muted)]">
                {user.favorite_decks?.[2]?.length > 0 ? user.favorite_decks[2].join(', ') : '-'}
              </td>
              <td className="px-4 py-3">
                {user.last_game_at ? (
                  <div>
                    <div className="text-[var(--ink-muted)]">{formatRelativeTime(user.last_game_at)}</div>
                    {user.last_game_status && (
                      <div className={`text-xs ${
                        user.last_game_status === 'completed' ? 'text-blue-400' :
                        user.last_game_status === 'active' ? 'text-green-400' :
                        'text-[var(--ink-faint)]'
                      }`}>
                        {user.last_game_status}
                      </div>
                    )}
                  </div>
                ) : (
                  <span className="text-[var(--ink-faint)]">Never</span>
                )}
              </td>
              <td className="px-4 py-3 text-[var(--ink-faint)] text-xs">{formatRelativeTime(user.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export default UsersTab;
