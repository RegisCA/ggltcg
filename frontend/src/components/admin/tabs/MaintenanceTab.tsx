/**
 * Maintenance tab — surfaces the /maintenance/stats and /maintenance/cleanup
 * backend endpoints (the same ones the scheduled GitHub Actions job hits).
 *
 * Both endpoints require an X-API-Key header — a separate secret from the
 * admin-page sign-in gate (AdminAuthGate), since /maintenance/* is also hit
 * unattended by the scheduled cleanup GitHub Action. The key is entered in
 * the browser and held only in sessionStorage for this tab (cleared on tab
 * close) — never hardcoded, never persisted to localStorage or a cookie.
 */

import React, { useState } from 'react';
import { useMaintenanceStats, useRunCleanup } from '../../../hooks/useMaintenance';
import { Modal } from '../../ui/Modal';
import type { CleanupResult } from '../../../api/maintenanceService';

const STORAGE_KEY = 'ggltcg_maintenance_key';

const isAuthError = (error: unknown): boolean => {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return status === 401 || status === 403;
};

const MaintenanceTab: React.FC = () => {
  const [apiKey, setApiKey] = useState<string | null>(() => sessionStorage.getItem(STORAGE_KEY));
  const [keyInput, setKeyInput] = useState('');
  const [invalidKey, setInvalidKey] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [lastResult, setLastResult] = useState<CleanupResult | null>(null);

  const statsQuery = useMaintenanceStats(apiKey);
  const cleanupMutation = useRunCleanup(apiKey);

  // Whenever a request against the current key comes back 401/403, drop it
  // and prompt for re-entry.
  React.useEffect(() => {
    if (statsQuery.error && isAuthError(statsQuery.error)) {
      handleInvalidKey();
    }
  }, [statsQuery.error]);

  const handleInvalidKey = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setApiKey(null);
    setInvalidKey(true);
    setLastResult(null);
  };

  const handleSubmitKey = (event: React.FormEvent) => {
    event.preventDefault();
    if (!keyInput.trim()) return;
    sessionStorage.setItem(STORAGE_KEY, keyInput.trim());
    setApiKey(keyInput.trim());
    setKeyInput('');
    setInvalidKey(false);
  };

  const handleCleanup = () => {
    setConfirmOpen(false);
    cleanupMutation.mutate(undefined, {
      onSuccess: (result) => setLastResult(result),
      onError: (error) => {
        if (isAuthError(error)) {
          handleInvalidKey();
        }
      },
    });
  };

  if (!apiKey) {
    return (
      <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
        <h2
          className="text-2xl font-bold"
          style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}
        >
          Maintenance
        </h2>
        <p className="text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-md)' }}>
          Enter the maintenance API key to view cleanup stats and run cleanup. The key is
          kept only in this browser tab&apos;s session storage.
        </p>
        {invalidKey && (
          <p className="text-red-400" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
            Invalid API key. Please try again.
          </p>
        )}
        <form onSubmit={handleSubmitKey} className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Maintenance API key"
            aria-label="Maintenance API key"
            className="flex-1 bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
            style={{ padding: 'var(--spacing-component-sm)' }}
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 rounded font-semibold"
            style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
          >
            Submit
          </button>
        </form>
      </div>
    );
  }

  const stats = statsQuery.data;

  return (
    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-lg)' }}>
      <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
        <div
          className="flex justify-between items-center"
          style={{ marginBottom: 'var(--spacing-component-md)' }}
        >
          <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-card-name)' }}>
            Maintenance
          </h2>
          <button
            onClick={() => setConfirmOpen(true)}
            disabled={cleanupMutation.isPending}
            className="bg-red-600 hover:bg-red-700 rounded font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
          >
            {cleanupMutation.isPending ? 'Running cleanup...' : 'Run Cleanup'}
          </button>
        </div>

        {statsQuery.isLoading && <p className="text-[var(--ink-faint)]">Loading stats...</p>}

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 'var(--spacing-component-sm)' }}>
            <div className="bg-black/20 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>
                Active Games
              </h3>
              <p className="text-2xl font-bold">{stats.active_games_total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {stats.active_games_stale} stale (&gt; 24h)
              </p>
            </div>
            <div className="bg-black/20 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>
                AI Logs
              </h3>
              <p className="text-2xl font-bold">{stats.ai_logs_total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {stats.ai_logs_stale} stale (&gt; 6h)
              </p>
            </div>
            <div className="bg-black/20 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>
                Playbacks
              </h3>
              <p className="text-2xl font-bold">{stats.playback_total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {stats.playback_stale} stale (&gt; 24h)
              </p>
            </div>
            <div className="bg-black/20 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-[var(--ink-faint)] text-xs" style={{ marginBottom: '4px' }}>
                Simulations
              </h3>
              <p className="text-2xl font-bold">{stats.simulations_total}</p>
              <p className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                {stats.simulations_stale} stale (&gt; 7d)
              </p>
            </div>
          </div>
        )}

        {lastResult && (
          <div
            className="bg-green-900/30 border border-green-500 rounded"
            style={{ marginTop: 'var(--spacing-component-md)', padding: 'var(--spacing-component-md)' }}
          >
            <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
              Cleanup complete
            </h3>
            <div className="text-sm text-[var(--ink-faint)]">
              <div>{lastResult.games_abandoned} games marked abandoned</div>
              <div>{lastResult.ai_logs_deleted} AI logs deleted</div>
              <div>{lastResult.playback_deleted} playbacks deleted</div>
              <div>{lastResult.simulations_deleted} simulation runs deleted</div>
              <div>Completed in {lastResult.execution_time_ms}ms</div>
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Confirm cleanup"
      >
        <div style={{ padding: 'var(--spacing-component-lg)' }}>
          <h3 className="text-xl font-bold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
            Run cleanup now?
          </h3>
          <p className="text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
            This will mark stale active games as abandoned and permanently delete stale AI
            logs, playbacks, and simulation runs. This cannot be undone.
          </p>
          <div className="flex justify-end" style={{ gap: 'var(--spacing-component-sm)' }}>
            <button
              onClick={() => setConfirmOpen(false)}
              className="bg-white/10 hover:bg-white/20 rounded font-semibold"
              style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
            >
              Cancel
            </button>
            <button
              onClick={handleCleanup}
              className="bg-red-600 hover:bg-red-700 rounded font-semibold"
              style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-md)' }}
            >
              Run Cleanup
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MaintenanceTab;
