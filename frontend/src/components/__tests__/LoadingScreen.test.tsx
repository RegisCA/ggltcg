/**
 * Smoke test for LoadingScreen's cold-start expectation: after the short
 * quick-path window elapses with no health response, the screen switches to
 * the honest "waking up, about a minute" message and shows a progress bar.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoadingScreen } from '../LoadingScreen';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(() => new Promise(() => {})), // never resolves — stays "checking"/"waking"
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('LoadingScreen', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows the quick-path connecting message initially', () => {
    renderWithClient(<LoadingScreen onReady={vi.fn()} />);
    expect(screen.getByText(/Connecting to game server/)).toBeInTheDocument();
    expect(screen.queryByTestId('cold-start-info')).not.toBeInTheDocument();
  });

  it('switches to the waking message after the quick-path window elapses', () => {
    renderWithClient(<LoadingScreen onReady={vi.fn()} />);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText(/Waking up the game server/)).toBeInTheDocument();
    expect(screen.getByTestId('cold-start-info')).toBeInTheDocument();
    expect(screen.getByText(/takes about a minute/)).toBeInTheDocument();
  });

  it('renders the forced waking state immediately via coldStartOverride', () => {
    renderWithClient(<LoadingScreen onReady={vi.fn()} coldStartOverride />);
    expect(screen.getByText(/Waking up the game server/)).toBeInTheDocument();
    expect(screen.getByTestId('cold-start-info')).toBeInTheDocument();
  });
});
