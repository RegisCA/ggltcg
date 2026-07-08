/**
 * Syncs the admin viewer's active tab (and an optional key filter) with the
 * URL hash, so deep links like /admin.html#ai-logs?game_id=... survive a
 * refresh. No react-router — the admin entry is a single small page, so a
 * hash string is parsed/serialized by hand.
 *
 * Hash shape: `#<tab>` or `#<tab>?<key>=<value>` (single filter param only —
 * that's all the admin viewer currently needs).
 */

import { useCallback, useEffect, useState } from 'react';

export interface HashTabState<Tab extends string> {
  tab: Tab;
  filter: string | null;
}

export const parseHash = <Tab extends string>(
  hash: string,
  validTabs: readonly Tab[],
  defaultTab: Tab,
  filterKey: string
): HashTabState<Tab> => {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  const [tabPart, queryPart] = raw.split('?');
  const tab = validTabs.includes(tabPart as Tab) ? (tabPart as Tab) : defaultTab;

  let filter: string | null = null;
  if (queryPart) {
    const params = new URLSearchParams(queryPart);
    const value = params.get(filterKey);
    if (value) filter = value;
  }

  return { tab, filter };
};

export const serializeHash = <Tab extends string>(
  tab: Tab,
  filter: string | null,
  filterKey: string
): string => {
  if (filter) {
    const params = new URLSearchParams({ [filterKey]: filter });
    return `#${tab}?${params.toString()}`;
  }
  return `#${tab}`;
};

/**
 * Hook wiring: reads the initial tab/filter from `window.location.hash` on
 * mount, and keeps the hash updated whenever `tab` or `filter` change.
 * Does not listen for external hash changes (e.g. back/forward) — the admin
 * viewer only needs load-time restoration and forward updates.
 */
export function useHashTab<Tab extends string>(
  validTabs: readonly Tab[],
  defaultTab: Tab,
  filterKey: string = 'game_id'
): {
  tab: Tab;
  filter: string | null;
  setTab: (tab: Tab) => void;
  setFilter: (filter: string | null) => void;
  setTabAndFilter: (tab: Tab, filter: string | null) => void;
} {
  const [state, setState] = useState<HashTabState<Tab>>(() => {
    if (typeof window === 'undefined') return { tab: defaultTab, filter: null };
    return parseHash(window.location.hash, validTabs, defaultTab, filterKey);
  });

  useEffect(() => {
    const hash = serializeHash(state.tab, state.filter, filterKey);
    if (typeof window !== 'undefined' && window.location.hash !== hash) {
      window.location.hash = hash;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.tab, state.filter]);

  const setTab = useCallback((tab: Tab) => {
    setState(prev => ({ tab, filter: prev.filter }));
  }, []);

  const setFilter = useCallback((filter: string | null) => {
    setState(prev => ({ ...prev, filter }));
  }, []);

  const setTabAndFilter = useCallback((tab: Tab, filter: string | null) => {
    setState({ tab, filter });
  }, []);

  return { tab: state.tab, filter: state.filter, setTab, setFilter, setTabAndFilter };
}
