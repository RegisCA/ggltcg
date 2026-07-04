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
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <DesignPreview />
    </QueryClientProvider>
  </React.StrictMode>
);
