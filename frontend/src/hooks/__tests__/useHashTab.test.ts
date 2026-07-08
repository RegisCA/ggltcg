/**
 * Unit tests for useHashTab's pure parse/serialize helpers plus a round-trip
 * check through the hook itself (tab + filter -> hash -> restored state).
 */
import { describe, it, expect, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { parseHash, serializeHash, useHashTab } from '../useHashTab';

type Tab = 'summary' | 'ai-logs' | 'games';
const TABS: readonly Tab[] = ['summary', 'ai-logs', 'games'];

describe('parseHash', () => {
  it('returns the default tab and no filter for an empty hash', () => {
    expect(parseHash('', TABS, 'summary', 'game_id')).toEqual({ tab: 'summary', filter: null });
  });

  it('parses a bare tab hash', () => {
    expect(parseHash('#ai-logs', TABS, 'summary', 'game_id')).toEqual({ tab: 'ai-logs', filter: null });
  });

  it('parses a tab with a filter query param', () => {
    expect(parseHash('#ai-logs?game_id=abc123', TABS, 'summary', 'game_id')).toEqual({
      tab: 'ai-logs',
      filter: 'abc123',
    });
  });

  it('falls back to the default tab for an unknown tab name', () => {
    expect(parseHash('#nonsense', TABS, 'summary', 'game_id')).toEqual({ tab: 'summary', filter: null });
  });

  it('ignores unrelated query params', () => {
    expect(parseHash('#games?other=1', TABS, 'summary', 'game_id')).toEqual({ tab: 'games', filter: null });
  });
});

describe('serializeHash', () => {
  it('serializes a tab with no filter as a bare hash', () => {
    expect(serializeHash('summary', null, 'game_id')).toBe('#summary');
  });

  it('serializes a tab with a filter as a query string', () => {
    expect(serializeHash('ai-logs', 'abc123', 'game_id')).toBe('#ai-logs?game_id=abc123');
  });

  it('includes the filter only when the active tab is the filter tab', () => {
    expect(serializeHash('ai-logs', 'abc123', 'game_id', 'ai-logs')).toBe('#ai-logs?game_id=abc123');
    expect(serializeHash('games', 'abc123', 'game_id', 'ai-logs')).toBe('#games');
    expect(serializeHash('summary', 'abc123', 'game_id', 'ai-logs')).toBe('#summary');
  });
});

describe('parseHash / serializeHash round trip', () => {
  it('round-trips tab + filter through serialize then parse', () => {
    const hash = serializeHash('ai-logs', 'game-xyz', 'game_id');
    expect(parseHash(hash, TABS, 'summary', 'game_id')).toEqual({ tab: 'ai-logs', filter: 'game-xyz' });
  });

  it('round-trips a bare tab with no filter', () => {
    const hash = serializeHash('games', null, 'game_id');
    expect(parseHash(hash, TABS, 'summary', 'game_id')).toEqual({ tab: 'games', filter: null });
  });
});

describe('useHashTab', () => {
  afterEach(() => {
    window.location.hash = '';
  });

  it('restores tab and filter from the hash on mount', () => {
    window.location.hash = '#ai-logs?game_id=game-1';
    const { result } = renderHook(() => useHashTab(TABS, 'summary'));
    expect(result.current.tab).toBe('ai-logs');
    expect(result.current.filter).toBe('game-1');
  });

  it('updates the hash when setTab is called', () => {
    window.location.hash = '';
    const { result } = renderHook(() => useHashTab(TABS, 'summary'));
    act(() => result.current.setTab('games'));
    expect(window.location.hash).toBe('#games');
  });

  it('updates the hash with a filter when setTabAndFilter is called', () => {
    window.location.hash = '';
    const { result } = renderHook(() => useHashTab(TABS, 'summary'));
    act(() => result.current.setTabAndFilter('ai-logs', 'game-42'));
    expect(window.location.hash).toBe('#ai-logs?game_id=game-42');
    expect(result.current.tab).toBe('ai-logs');
    expect(result.current.filter).toBe('game-42');
  });

  it('drops the filter param from the hash when switching away from the filter tab', () => {
    window.location.hash = '#ai-logs?game_id=game-42';
    const { result } = renderHook(() => useHashTab(TABS, 'summary', 'game_id', 'ai-logs'));
    act(() => result.current.setTab('games'));
    expect(window.location.hash).toBe('#games');
    // The filter itself stays in memory so returning to the tab restores it.
    expect(result.current.filter).toBe('game-42');
    act(() => result.current.setTab('ai-logs'));
    expect(window.location.hash).toBe('#ai-logs?game_id=game-42');
  });
});
