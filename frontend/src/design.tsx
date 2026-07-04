/**
 * Standalone Design Preview entry
 * Access via /design.html
 *
 * No auth, analytics, or Sentry — this page renders fixture game states only
 * (see src/fixtures/designFixtures.ts) and never talks to the backend.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DesignPreview } from './pages/DesignPreview';
import { gameKeys } from './hooks/useGame';
import { DESIGN_FIXTURES, FIXTURE_HUMAN_ID } from './fixtures/designFixtures';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Pre-seed every fixture into the query cache so GameBoard renders on the
// first frame — no "Loading game..." flash on cold deep-links like
// /design.html#opponent-turn. The fixtures module is already a static import
// of this entry (via DesignPreview), so this costs nothing extra to load.
for (const fixture of DESIGN_FIXTURES) {
  queryClient.setQueryData(gameKeys.gameState(fixture.id, FIXTURE_HUMAN_ID), fixture.state);
  queryClient.setQueryData(gameKeys.validActions(fixture.id, FIXTURE_HUMAN_ID), {
    game_id: fixture.id,
    player_id: FIXTURE_HUMAN_ID,
    valid_actions: fixture.validActions,
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <DesignPreview />
    </QueryClientProvider>
  </React.StrictMode>
);
